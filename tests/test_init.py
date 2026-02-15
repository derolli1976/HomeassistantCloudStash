#
# Tests for CloudStash – __init__.py
#
# Unit tests for entry setup, teardown, and the ObjectStorageGateway proxy.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
#
# To run: pytest tests/test_init.py
#

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from botocore.exceptions import (
    ClientError,
    ConnectionError as BotoConnectionError,
    ParamValidationError,
)
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)

from custom_components.cloudstash import (
    ObjectStorageGateway,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.cloudstash.const import (
    AGENT_LISTENER_KEY,
    DOMAIN,
    FALLBACK_REGION,
    OPT_BUCKET,
    OPT_ENDPOINT,
    OPT_KEY_ID,
    OPT_REGION,
    OPT_SECRET,
)


# ---------------------------------------------------------------------------
# ObjectStorageGateway construction
# ---------------------------------------------------------------------------


class TestObjectStorageGatewayInit:
    """Tests for ObjectStorageGateway construction and attribute storage."""

    def test_stores_parameters(self):
        gw = ObjectStorageGateway(
            endpoint="https://s3.example.com",
            key_id="AKIA...",
            secret="secret",
            region="eu-central-1",
            bucket="backups",
        )
        assert gw._endpoint == "https://s3.example.com"
        assert gw._key_id == "AKIA..."
        assert gw._secret == "secret"
        assert gw._region == "eu-central-1"
        assert gw._bucket == "backups"

    def test_initial_state(self):
        gw = ObjectStorageGateway(
            endpoint=None,
            key_id="K",
            secret="S",
            region="us-east-1",
            bucket="b",
        )
        assert gw._running is False
        assert gw._loop is None
        assert gw._worker is None
        assert gw._handle is None

    def test_endpoint_none_accepted(self):
        """AWS default endpoint (None) should be accepted."""
        gw = ObjectStorageGateway(
            endpoint=None,
            key_id="K",
            secret="S",
            region="us-east-1",
            bucket="b",
        )
        assert gw._endpoint is None


# ---------------------------------------------------------------------------
# ObjectStorageGateway._run raises when not started
# ---------------------------------------------------------------------------


class TestGatewayNotStarted:
    """Calling proxy methods on an un-started gateway must raise."""

    async def test_run_raises_runtime_error(self):
        gw = ObjectStorageGateway(
            endpoint=None,
            key_id="K",
            secret="S",
            region="us-east-1",
            bucket="b",
        )
        with pytest.raises(RuntimeError, match="Gateway not started"):
            await gw._run(AsyncMock()())


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------


def _make_entry(data: dict) -> MagicMock:
    entry = MagicMock()
    entry.data = data
    entry.title = data.get(OPT_BUCKET, "test")
    entry.entry_id = "test_entry_id"
    entry.async_on_unload = MagicMock()
    entry.async_on_state_change = MagicMock(return_value=lambda: None)
    return entry


def _make_hass() -> MagicMock:
    hass = MagicMock()
    hass.data = {}
    hass.async_add_executor_job = AsyncMock()
    return hass


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    async def test_success(self, sample_config):
        """A valid config entry should set runtime_data to a gateway."""
        hass = _make_hass()
        entry = _make_entry(sample_config)
        hass.async_add_executor_job.return_value = None

        with patch(
            "custom_components.cloudstash.ObjectStorageGateway"
        ) as MockGW:
            mock_gw = MagicMock()
            MockGW.return_value = mock_gw
            result = await async_setup_entry(hass, entry)

        assert result is True
        assert entry.runtime_data == mock_gw

    async def test_auth_failure_raises_config_entry_auth_failed(self, sample_config):
        """ClientError during launch should raise ConfigEntryAuthFailed."""
        hass = _make_hass()
        entry = _make_entry(sample_config)
        error_response = {"Error": {"Code": "403", "Message": "Forbidden"}}
        hass.async_add_executor_job.side_effect = ClientError(
            error_response, "HeadBucket"
        )

        with patch("custom_components.cloudstash.ObjectStorageGateway"):
            with pytest.raises(ConfigEntryAuthFailed):
                await async_setup_entry(hass, entry)

    async def test_invalid_bucket_raises_config_entry_error(self, sample_config):
        """ParamValidationError with 'Invalid bucket name' raises ConfigEntryError."""
        hass = _make_hass()
        entry = _make_entry(sample_config)
        hass.async_add_executor_job.side_effect = ParamValidationError(
            report="Invalid bucket name 'foo bar'"
        )

        with patch("custom_components.cloudstash.ObjectStorageGateway"):
            with pytest.raises(ConfigEntryError):
                await async_setup_entry(hass, entry)

    async def test_invalid_endpoint_raises_config_entry_error(self, sample_config):
        """ValueError during launch raises ConfigEntryError."""
        hass = _make_hass()
        entry = _make_entry(sample_config)
        hass.async_add_executor_job.side_effect = ValueError("bad endpoint")

        with patch("custom_components.cloudstash.ObjectStorageGateway"):
            with pytest.raises(ConfigEntryError):
                await async_setup_entry(hass, entry)

    async def test_connection_error_raises_config_entry_not_ready(self, sample_config):
        """BotoConnectionError during launch raises ConfigEntryNotReady."""
        hass = _make_hass()
        entry = _make_entry(sample_config)
        hass.async_add_executor_job.side_effect = BotoConnectionError(
            error="unreachable"
        )

        with patch("custom_components.cloudstash.ObjectStorageGateway"):
            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(hass, entry)


# ---------------------------------------------------------------------------
# async_unload_entry
# ---------------------------------------------------------------------------


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry."""

    async def test_calls_shutdown(self, sample_config):
        """Unloading should invoke shutdown on the gateway."""
        hass = _make_hass()
        entry = _make_entry(sample_config)
        mock_gw = MagicMock()
        entry.runtime_data = mock_gw
        hass.async_add_executor_job.return_value = None

        result = await async_unload_entry(hass, entry)
        assert result is True
        hass.async_add_executor_job.assert_called_once_with(mock_gw.shutdown)
