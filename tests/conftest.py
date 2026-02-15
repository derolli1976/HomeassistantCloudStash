"""Shared fixtures for CloudStash tests."""

from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub out C-extension modules that may not have wheels for the
# current Python version (e.g. lru-dict on 3.14).  These stubs are
# injected into sys.modules BEFORE any Home Assistant import so the
# import chain never fails.
# ---------------------------------------------------------------------------

if "lru" not in sys.modules:
    _lru = types.ModuleType("lru")

    class _LRU(dict):
        """Minimal stand-in for lru.LRU used by HA template helpers."""

        def __init__(self, maxsize: int = 128, *a, **kw):
            super().__init__(*a, **kw)
            self._maxsize = maxsize

        def get_size(self):
            return self._maxsize

    _lru.LRU = _LRU  # type: ignore[attr-defined]
    sys.modules["lru"] = _lru

# ---------------------------------------------------------------------------
# Compatibility shim: BackupNotFound / suggested_filename may be
# absent in older HA releases.
# ---------------------------------------------------------------------------

try:
    from homeassistant.components.backup import BackupNotFound  # noqa: F401
except ImportError:
    import homeassistant.components.backup as _backup_mod

    class _BackupNotFound(Exception):
        """Placeholder for older HA versions."""

    _backup_mod.BackupNotFound = _BackupNotFound  # type: ignore[attr-defined]

try:
    from homeassistant.components.backup import suggested_filename  # noqa: F401
except ImportError:
    import homeassistant.components.backup as _backup_mod2

    def _suggested_filename(backup):  # type: ignore[override]
        return f"{backup.backup_id}.tar"

    _backup_mod2.suggested_filename = _suggested_filename  # type: ignore[attr-defined]


@pytest.fixture
def mock_gateway():
    """Return a fully-mocked ObjectStorageGateway."""
    gw = MagicMock()
    gw.launch = MagicMock()
    gw.shutdown = MagicMock()
    gw.head_bucket = AsyncMock(return_value={})
    gw.list_objects_v2 = AsyncMock(return_value={"Contents": [], "IsTruncated": False})
    gw.get_object = AsyncMock()
    gw.put_object = AsyncMock()
    gw.delete_object = AsyncMock()
    gw.create_multipart_upload = AsyncMock(return_value={"UploadId": "test-uid"})
    gw.upload_part = AsyncMock(return_value={"ETag": '"abc123"'})
    gw.complete_multipart_upload = AsyncMock()
    gw.abort_multipart_upload = AsyncMock()
    return gw


@pytest.fixture
def sample_config():
    """Return a sample configuration dict for a config entry."""
    return {
        "access_key_id": "AKIAIOSFODNN7EXAMPLE",
        "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "endpoint_url": "https://s3.eu-central-1.example.com",
        "bucket": "my-backups",
        "region": "eu-central-1",
        "prefix": "homeassistant",
    }


@pytest.fixture
def mock_probe_connection():
    """Patch _probe_connection so it always succeeds."""
    with patch(
        "custom_components.cloudstash.config_flow._probe_connection"
    ) as mocked:
        mocked.return_value = None
        yield mocked
