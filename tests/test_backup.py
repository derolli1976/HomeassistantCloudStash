#
# Tests for CloudStash – backup.py
#
# Unit tests for the backup agent: listing, downloading, uploading, deleting
# backups, cache behaviour, and the error-handling decorator.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
#
# To run: pytest tests/test_backup.py
#

import json
from time import monotonic
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import BotoCoreError

from custom_components.cloudstash.backup import (
    CHUNK_THRESHOLD_BYTES,
    LISTING_CACHE_SECONDS,
    CloudStashAgent,
    _derive_object_names,
    _wrap_storage_errors,
    async_get_backup_agents,
    async_register_backup_agents_listener,
)
from custom_components.cloudstash.const import (
    AGENT_LISTENER_KEY,
    DOMAIN,
    FALLBACK_PREFIX,
    OPT_BUCKET,
    OPT_OBJECT_PREFIX,
    STORAGE_DIR,
)


# ---------------------------------------------------------------------------
# _derive_object_names
# ---------------------------------------------------------------------------


class TestDeriveObjectNames:
    """Tests for the (tar_name, meta_name) derivation helper."""

    def test_standard_backup(self):
        backup = MagicMock()
        backup.backup_id = "abc123"
        backup.name = "Test Backup"
        backup.date = "2025-01-15T10:00:00Z"

        with patch(
            "custom_components.cloudstash.backup.suggested_filename",
            return_value="abc123.tar",
        ):
            tar, meta = _derive_object_names(backup)

        assert tar == "abc123.tar"
        assert meta == "abc123.metadata.json"

    def test_filename_with_dots(self):
        """Filenames with extra dots should still split correctly."""
        backup = MagicMock()
        with patch(
            "custom_components.cloudstash.backup.suggested_filename",
            return_value="backup.2025.01.tar",
        ):
            tar, meta = _derive_object_names(backup)
        assert tar == "backup.2025.01.tar"
        assert meta == "backup.2025.01.metadata.json"


# ---------------------------------------------------------------------------
# CloudStashAgent._resolve_root
# ---------------------------------------------------------------------------


class TestResolveRoot:
    """Tests for the object-key prefix normalisation."""

    def test_normal_prefix(self):
        assert CloudStashAgent._resolve_root("myprefix") == f"myprefix/{STORAGE_DIR}/"

    def test_prefix_with_slashes(self):
        assert CloudStashAgent._resolve_root("/myprefix/") == f"myprefix/{STORAGE_DIR}/"

    def test_empty_prefix(self):
        assert CloudStashAgent._resolve_root("") == f"{STORAGE_DIR}/"

    def test_default_prefix(self):
        assert (
            CloudStashAgent._resolve_root(FALLBACK_PREFIX)
            == f"{FALLBACK_PREFIX}/{STORAGE_DIR}/"
        )

    def test_nested_prefix(self):
        assert (
            CloudStashAgent._resolve_root("org/team")
            == f"org/team/{STORAGE_DIR}/"
        )


# ---------------------------------------------------------------------------
# _wrap_storage_errors decorator
# ---------------------------------------------------------------------------


class TestWrapStorageErrors:
    """Tests for the BotoCoreError → BackupAgentError translator."""

    async def test_success_passes_through(self):
        @_wrap_storage_errors
        async def fn():
            return 42

        assert await fn() == 42

    async def test_boto_error_translated(self):
        from homeassistant.components.backup import BackupAgentError

        @_wrap_storage_errors
        async def fn():
            raise BotoCoreError()

        with pytest.raises(BackupAgentError):
            await fn()

    async def test_non_boto_error_propagates(self):
        @_wrap_storage_errors
        async def fn():
            raise ValueError("unrelated")

        with pytest.raises(ValueError):
            await fn()


# ---------------------------------------------------------------------------
# CloudStashAgent – construction
# ---------------------------------------------------------------------------


def _make_agent(
    mock_gateway,
    bucket="test-bucket",
    prefix=FALLBACK_PREFIX,
) -> CloudStashAgent:
    """Build a CloudStashAgent with a mocked entry."""
    entry = MagicMock()
    entry.runtime_data = mock_gateway
    entry.data = {
        OPT_BUCKET: bucket,
        OPT_OBJECT_PREFIX: prefix,
    }
    entry.title = bucket
    entry.entry_id = "entry_123"

    hass = MagicMock()
    return CloudStashAgent(hass, entry)


class TestAgentConstruction:
    """Tests for CloudStashAgent initialisation."""

    def test_domain(self, mock_gateway):
        agent = _make_agent(mock_gateway)
        assert agent.domain == DOMAIN

    def test_unique_id(self, mock_gateway):
        agent = _make_agent(mock_gateway)
        assert agent.unique_id == "entry_123"

    def test_root_with_prefix(self, mock_gateway):
        agent = _make_agent(mock_gateway, prefix="custom")
        assert agent._root == f"custom/{STORAGE_DIR}/"

    def test_root_default_prefix(self, mock_gateway):
        agent = _make_agent(mock_gateway)
        assert agent._root == f"{FALLBACK_PREFIX}/{STORAGE_DIR}/"


# ---------------------------------------------------------------------------
# CloudStashAgent – listing
# ---------------------------------------------------------------------------


def _backup_dict(backup_id="abc-def", name="Daily Backup"):
    """Return a minimal AgentBackup-compatible dict."""
    return {
        "backup_id": backup_id,
        "name": name,
        "date": "2025-06-15T08:30:00.000000+00:00",
        "size": 1024,
        "protected": False,
        "extra_metadata": {},
        "addons": [],
        "agents": {},
        "database_included": True,
        "folders": [],
        "homeassistant_included": True,
        "homeassistant_version": "2025.6.0",
    }


class TestAsyncListBackups:
    """Tests for listing backups from object storage."""

    async def test_empty_listing(self, mock_gateway):
        agent = _make_agent(mock_gateway)
        mock_gateway.list_objects_v2.return_value = {
            "Contents": [],
            "IsTruncated": False,
        }
        result = await agent.async_list_backups()
        assert result == []

    async def test_lists_metadata_files(self, mock_gateway):
        agent = _make_agent(mock_gateway)
        bd = _backup_dict()

        body_mock = AsyncMock()
        body_mock.read = AsyncMock(return_value=json.dumps(bd).encode())

        mock_gateway.list_objects_v2.return_value = {
            "Contents": [
                {"Key": f"{agent._root}backup1.tar"},
                {"Key": f"{agent._root}backup1.metadata.json"},
            ],
            "IsTruncated": False,
        }
        mock_gateway.get_object.return_value = {"Body": body_mock}

        result = await agent.async_list_backups()
        assert len(result) == 1
        assert result[0].backup_id == "abc-def"

    async def test_cache_prevents_refetch(self, mock_gateway):
        agent = _make_agent(mock_gateway)
        mock_gateway.list_objects_v2.return_value = {
            "Contents": [],
            "IsTruncated": False,
        }

        await agent.async_list_backups()
        await agent.async_list_backups()

        # Second call should use cache, so list_objects_v2 is called only once
        assert mock_gateway.list_objects_v2.call_count == 1

    async def test_drop_cache_forces_refetch(self, mock_gateway):
        agent = _make_agent(mock_gateway)
        mock_gateway.list_objects_v2.return_value = {
            "Contents": [],
            "IsTruncated": False,
        }

        await agent.async_list_backups()
        agent._drop_cache()
        await agent.async_list_backups()

        assert mock_gateway.list_objects_v2.call_count == 2

    async def test_skips_corrupt_metadata(self, mock_gateway):
        """Metadata files with invalid JSON should be skipped, not crash."""
        agent = _make_agent(mock_gateway)

        body_mock = AsyncMock()
        body_mock.read = AsyncMock(return_value=b"not-valid-json")

        mock_gateway.list_objects_v2.return_value = {
            "Contents": [
                {"Key": f"{agent._root}broken.metadata.json"},
            ],
            "IsTruncated": False,
        }
        mock_gateway.get_object.return_value = {"Body": body_mock}

        result = await agent.async_list_backups()
        assert result == []


# ---------------------------------------------------------------------------
# CloudStashAgent – get backup
# ---------------------------------------------------------------------------


class TestAsyncGetBackup:
    """Tests for retrieving a single backup by ID."""

    async def test_found(self, mock_gateway):
        agent = _make_agent(mock_gateway)
        bd = _backup_dict(backup_id="found-id")

        body_mock = AsyncMock()
        body_mock.read = AsyncMock(return_value=json.dumps(bd).encode())

        mock_gateway.list_objects_v2.return_value = {
            "Contents": [{"Key": f"{agent._root}x.metadata.json"}],
            "IsTruncated": False,
        }
        mock_gateway.get_object.return_value = {"Body": body_mock}

        result = await agent.async_get_backup("found-id")
        assert result.backup_id == "found-id"

    async def test_not_found_raises(self, mock_gateway):
        from homeassistant.components.backup import BackupNotFound

        agent = _make_agent(mock_gateway)
        mock_gateway.list_objects_v2.return_value = {
            "Contents": [],
            "IsTruncated": False,
        }

        with pytest.raises(BackupNotFound):
            await agent.async_get_backup("nonexistent")


# ---------------------------------------------------------------------------
# CloudStashAgent – delete backup
# ---------------------------------------------------------------------------


class TestAsyncDeleteBackup:
    """Tests for deleting a backup and its metadata."""

    async def test_deletes_tar_and_meta(self, mock_gateway):
        agent = _make_agent(mock_gateway)
        bd = _backup_dict(backup_id="del-id")

        body_mock = AsyncMock()
        body_mock.read = AsyncMock(return_value=json.dumps(bd).encode())
        mock_gateway.list_objects_v2.return_value = {
            "Contents": [{"Key": f"{agent._root}x.metadata.json"}],
            "IsTruncated": False,
        }
        mock_gateway.get_object.return_value = {"Body": body_mock}

        with patch(
            "custom_components.cloudstash.backup.suggested_filename",
            return_value="del-id.tar",
        ):
            await agent.async_delete_backup("del-id")

        assert mock_gateway.delete_object.call_count == 2


# ---------------------------------------------------------------------------
# CloudStashAgent – download backup
# ---------------------------------------------------------------------------


class TestAsyncDownloadBackup:
    """Tests for streaming a backup download."""

    async def test_returns_body_iterator(self, mock_gateway):
        agent = _make_agent(mock_gateway)
        bd = _backup_dict(backup_id="dl-id")

        body_mock = AsyncMock()
        body_mock.read = AsyncMock(return_value=json.dumps(bd).encode())
        mock_gateway.list_objects_v2.return_value = {
            "Contents": [{"Key": f"{agent._root}x.metadata.json"}],
            "IsTruncated": False,
        }
        mock_gateway.get_object.return_value = {"Body": body_mock}

        body_iter = MagicMock()
        body_iter.iter_chunks.return_value = iter([b"chunk1", b"chunk2"])

        # First get_object call is for listing metadata, second for download
        mock_gateway.get_object.side_effect = [
            {"Body": body_mock},  # metadata fetch during listing
            {"Body": body_iter},  # the actual download
        ]

        # Need to refetch since we changed side_effect
        agent._drop_cache()

        with patch(
            "custom_components.cloudstash.backup.suggested_filename",
            return_value="dl-id.tar",
        ):
            result = await agent.async_download_backup("dl-id")
        assert result is not None


# ---------------------------------------------------------------------------
# CloudStashAgent – upload backup
# ---------------------------------------------------------------------------


class TestAsyncUploadBackup:
    """Tests for uploading a backup."""

    async def test_small_file_uses_put_object(self, mock_gateway):
        """Files below CHUNK_THRESHOLD_BYTES should use single PutObject."""
        agent = _make_agent(mock_gateway)
        backup = MagicMock()
        backup.size = 100  # well below threshold
        backup.as_dict.return_value = _backup_dict()

        async def _stream():
            async def _gen():
                yield b"small backup data"
            return _gen()

        with patch(
            "custom_components.cloudstash.backup.suggested_filename",
            return_value="small.tar",
        ):
            await agent.async_upload_backup(
                open_stream=_stream, backup=backup
            )

        mock_gateway.put_object.assert_called()
        mock_gateway.create_multipart_upload.assert_not_called()

    async def test_large_file_uses_multipart(self, mock_gateway):
        """Files at or above CHUNK_THRESHOLD_BYTES should use multipart upload."""
        agent = _make_agent(mock_gateway)
        backup = MagicMock()
        backup.size = CHUNK_THRESHOLD_BYTES + 1
        backup.as_dict.return_value = _backup_dict()

        data = b"x" * (CHUNK_THRESHOLD_BYTES + 100)

        async def _stream():
            async def _gen():
                yield data
            return _gen()

        with patch(
            "custom_components.cloudstash.backup.suggested_filename",
            return_value="large.tar",
        ):
            await agent.async_upload_backup(
                open_stream=_stream, backup=backup
            )

        mock_gateway.create_multipart_upload.assert_called_once()
        mock_gateway.upload_part.assert_called()
        mock_gateway.complete_multipart_upload.assert_called_once()

    async def test_multipart_abort_on_error(self, mock_gateway):
        """If upload_part fails, multipart upload should be aborted."""
        from homeassistant.components.backup import BackupAgentError

        agent = _make_agent(mock_gateway)
        backup = MagicMock()
        backup.size = CHUNK_THRESHOLD_BYTES + 1
        backup.as_dict.return_value = _backup_dict()

        data = b"x" * (CHUNK_THRESHOLD_BYTES + 100)
        mock_gateway.upload_part.side_effect = BotoCoreError()

        async def _stream():
            async def _gen():
                yield data
            return _gen()

        with (
            patch(
                "custom_components.cloudstash.backup.suggested_filename",
                return_value="fail.tar",
            ),
            pytest.raises(BackupAgentError),
        ):
            await agent.async_upload_backup(
                open_stream=_stream, backup=backup
            )

        mock_gateway.abort_multipart_upload.assert_called_once()


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


class TestModuleHelpers:
    """Tests for async_get_backup_agents and listener registration."""

    async def test_get_backup_agents_returns_agents(self):
        hass = MagicMock()
        entry = MagicMock()
        entry.runtime_data = MagicMock()
        entry.data = {OPT_BUCKET: "b", OPT_OBJECT_PREFIX: "p"}
        entry.title = "b"
        entry.entry_id = "e1"
        hass.config_entries.async_loaded_entries.return_value = [entry]

        agents = await async_get_backup_agents(hass)
        assert len(agents) == 1
        assert isinstance(agents[0], CloudStashAgent)

    def test_register_listener_returns_unsubscribe(self):
        hass = MagicMock()
        hass.data = {}
        listener = MagicMock()

        unsub = async_register_backup_agents_listener(hass, listener=listener)
        assert callable(unsub)
        assert listener in hass.data[AGENT_LISTENER_KEY]

        unsub()
        assert listener not in hass.data.get(AGENT_LISTENER_KEY, [])

    def test_unsubscribe_cleans_up_empty_list(self):
        hass = MagicMock()
        hass.data = {}
        listener = MagicMock()

        unsub = async_register_backup_agents_listener(hass, listener=listener)
        unsub()
        assert AGENT_LISTENER_KEY not in hass.data
