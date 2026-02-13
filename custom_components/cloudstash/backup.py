"""CloudStash backup-agent implementation."""

from collections.abc import AsyncIterator, Callable, Coroutine
import functools
import json
import logging
from time import monotonic
from typing import Any

from botocore.exceptions import BotoCoreError

from homeassistant.components.backup import (
    AgentBackup,
    BackupAgent,
    BackupAgentError,
    BackupNotFound,
    suggested_filename,
)
from homeassistant.core import HomeAssistant, callback

from . import CloudStashEntry, ObjectStorageGateway
from .const import (
    AGENT_LISTENER_KEY,
    DOMAIN,
    FALLBACK_PREFIX,
    OPT_BUCKET,
    OPT_OBJECT_PREFIX,
    STORAGE_DIR,
)

_LOG = logging.getLogger(__name__)

# Cache freshness window (seconds).
LISTING_CACHE_SECONDS = 300

# Files below this threshold are uploaded with a single PutObject call;
# larger files use multipart upload.  20 MiB keeps per-part memory bounded
# while staying well above the 5 MiB S3 minimum.
CHUNK_THRESHOLD_BYTES = 20 * 2**20


# ---------------------------------------------------------------------------
# Error-handling decorator
# ---------------------------------------------------------------------------


def _wrap_storage_errors[T](
    fn: Callable[..., Coroutine[Any, Any, T]],
) -> Callable[..., Coroutine[Any, Any, T]]:
    """Translate low-level boto errors into BackupAgentError."""

    @functools.wraps(fn)
    async def _inner(*a: Any, **kw: Any) -> T:
        try:
            return await fn(*a, **kw)
        except BotoCoreError as exc:
            raise BackupAgentError(f"{fn.__name__} failed") from exc

    return _inner


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


async def async_get_backup_agents(hass: HomeAssistant) -> list[BackupAgent]:
    """Return one agent per loaded config entry."""
    entries: list[CloudStashEntry] = hass.config_entries.async_loaded_entries(DOMAIN)
    return [CloudStashAgent(hass, e) for e in entries]


@callback
def async_register_backup_agents_listener(
    hass: HomeAssistant,
    *,
    listener: Callable[[], None],
    **kwargs: Any,
) -> Callable[[], None]:
    """Subscribe to agent add/remove notifications; returns an unsubscribe handle."""
    listeners = hass.data.setdefault(AGENT_LISTENER_KEY, [])
    listeners.append(listener)

    @callback
    def _unsubscribe() -> None:
        listeners.remove(listener)
        if not listeners:
            del hass.data[AGENT_LISTENER_KEY]

    return _unsubscribe


def _derive_object_names(backup: AgentBackup) -> tuple[str, str]:
    """Return *(tar_name, meta_name)* derived from the canonical backup filename."""
    stem = suggested_filename(backup).rsplit(".", 1)[0]
    return f"{stem}.tar", f"{stem}.metadata.json"


# ---------------------------------------------------------------------------
# Backup agent
# ---------------------------------------------------------------------------


class CloudStashAgent(BackupAgent):
    """Stores Home Assistant backups in any S3-compatible object store."""

    domain = DOMAIN

    def __init__(self, hass: HomeAssistant, entry: CloudStashEntry) -> None:
        super().__init__()
        self._gw: ObjectStorageGateway = entry.runtime_data
        self._bucket: str = entry.data[OPT_BUCKET]
        self._root: str = self._resolve_root(
            entry.data.get(OPT_OBJECT_PREFIX, FALLBACK_PREFIX)
        )
        self.name = entry.title
        self.unique_id = entry.entry_id
        self._listing: dict[str, AgentBackup] = {}
        self._listing_valid_until: float = 0.0

    # -- key helpers ---------------------------------------------------------

    @staticmethod
    def _resolve_root(raw_prefix: str) -> str:
        """Normalise *raw_prefix* into a key prefix ending with ``/``."""
        segment = raw_prefix.strip("/")
        return f"{segment}/{STORAGE_DIR}/" if segment else f"{STORAGE_DIR}/"

    def _key(self, name: str) -> str:
        """Full object key for *name* inside the backup root."""
        return f"{self._root}{name}"

    # -- public BackupAgent interface ----------------------------------------

    @_wrap_storage_errors
    async def async_download_backup(
        self,
        backup_id: str,
        **kwargs: Any,
    ) -> AsyncIterator[bytes]:
        """Stream a backup archive from object storage."""
        tar_name, _ = _derive_object_names(await self._resolve(backup_id))
        resp = await self._gw.get_object(
            Bucket=self._bucket, Key=self._key(tar_name)
        )
        return resp["Body"].iter_chunks()

    async def async_upload_backup(
        self,
        *,
        open_stream: Callable[[], Coroutine[Any, Any, AsyncIterator[bytes]]],
        backup: AgentBackup,
        **kwargs: Any,
    ) -> None:
        """Upload a backup archive and its sidecar metadata file."""
        tar_name, meta_name = _derive_object_names(backup)

        try:
            if backup.size < CHUNK_THRESHOLD_BYTES:
                await self._put_single(self._key(tar_name), open_stream)
            else:
                await self._put_chunked(self._key(tar_name), open_stream)

            await self._gw.put_object(
                Bucket=self._bucket,
                Key=self._key(meta_name),
                Body=json.dumps(backup.as_dict()),
            )
        except BotoCoreError as exc:
            raise BackupAgentError("Upload failed") from exc
        else:
            self._drop_cache()

    @_wrap_storage_errors
    async def async_delete_backup(self, backup_id: str, **kwargs: Any) -> None:
        """Remove a backup and its metadata from object storage."""
        tar_name, meta_name = _derive_object_names(await self._resolve(backup_id))
        await self._gw.delete_object(Bucket=self._bucket, Key=self._key(tar_name))
        await self._gw.delete_object(Bucket=self._bucket, Key=self._key(meta_name))
        self._drop_cache()

    @_wrap_storage_errors
    async def async_list_backups(self, **kwargs: Any) -> list[AgentBackup]:
        """Return every backup known to the remote store."""
        return list((await self._fetch_listing()).values())

    @_wrap_storage_errors
    async def async_get_backup(self, backup_id: str, **kwargs: Any) -> AgentBackup:
        """Return metadata for a single backup."""
        return await self._resolve(backup_id)

    # -- internal helpers ----------------------------------------------------

    async def _resolve(self, backup_id: str) -> AgentBackup:
        """Look up *backup_id* or raise ``BackupNotFound``."""
        listing = await self._fetch_listing()
        if (entry := listing.get(backup_id)) is not None:
            return entry
        raise BackupNotFound(f"Backup {backup_id} not found")

    def _drop_cache(self) -> None:
        """Force the next listing call to re-fetch from the remote store."""
        self._listing_valid_until = 0.0
        self._listing = {}

    async def _fetch_listing(self) -> dict[str, AgentBackup]:
        """Return all backups, re-fetching from object storage when stale."""
        if monotonic() <= self._listing_valid_until:
            return self._listing

        result: dict[str, AgentBackup] = {}
        token: str | None = None

        while True:
            params: dict[str, Any] = {"Bucket": self._bucket, "Prefix": self._root}
            if token:
                params["ContinuationToken"] = token

            page = await self._gw.list_objects_v2(**params)

            for obj in page.get("Contents", []):
                if not obj["Key"].endswith(".metadata.json"):
                    continue
                try:
                    resp = await self._gw.get_object(
                        Bucket=self._bucket, Key=obj["Key"]
                    )
                    raw = await resp["Body"].read()
                    parsed = AgentBackup.from_dict(json.loads(raw))
                except (BotoCoreError, json.JSONDecodeError) as exc:
                    _LOG.warning("Skipping %s: %s", obj["Key"], exc)
                    continue
                result[parsed.backup_id] = parsed

            if page.get("IsTruncated"):
                token = page.get("NextContinuationToken")
            else:
                break

        self._listing = result
        self._listing_valid_until = monotonic() + LISTING_CACHE_SECONDS
        return self._listing

    # -- upload strategies ---------------------------------------------------

    async def _put_single(
        self,
        key: str,
        open_stream: Callable[[], Coroutine[Any, Any, AsyncIterator[bytes]]],
    ) -> None:
        """PutObject with fully buffered body (small backups)."""
        _LOG.debug("Single-part upload: %s", key)
        buf = bytearray()
        async for chunk in await open_stream():
            buf.extend(chunk)
        await self._gw.put_object(Bucket=self._bucket, Key=key, Body=bytes(buf))

    async def _put_chunked(
        self,
        key: str,
        open_stream: Callable[[], Coroutine[Any, Any, AsyncIterator[bytes]]],
    ) -> None:
        """Multipart upload for large backups.

        Every non-final part is exactly ``CHUNK_THRESHOLD_BYTES`` to satisfy
        providers that enforce equal part sizes (e.g. Cloudflare R2).
        """
        _LOG.debug("Multipart upload: %s", key)
        mpu = await self._gw.create_multipart_upload(Bucket=self._bucket, Key=key)
        uid = mpu["UploadId"]

        try:
            completed_parts: list[dict[str, Any]] = []
            seq = 1
            buf = bytearray()

            async for chunk in await open_stream():
                buf.extend(chunk)
                while len(buf) >= CHUNK_THRESHOLD_BYTES:
                    segment = bytes(buf[:CHUNK_THRESHOLD_BYTES])
                    del buf[:CHUNK_THRESHOLD_BYTES]
                    _LOG.debug("Part %d – %d bytes", seq, len(segment))
                    part = await self._gw.upload_part(
                        Bucket=self._bucket,
                        Key=key,
                        PartNumber=seq,
                        UploadId=uid,
                        Body=segment,
                    )
                    completed_parts.append(
                        {"PartNumber": seq, "ETag": part["ETag"]}
                    )
                    seq += 1

            if buf:
                _LOG.debug("Final part %d – %d bytes", seq, len(buf))
                part = await self._gw.upload_part(
                    Bucket=self._bucket,
                    Key=key,
                    PartNumber=seq,
                    UploadId=uid,
                    Body=bytes(buf),
                )
                completed_parts.append({"PartNumber": seq, "ETag": part["ETag"]})

            await self._gw.complete_multipart_upload(
                Bucket=self._bucket,
                Key=key,
                UploadId=uid,
                MultipartUpload={"Parts": completed_parts},
            )
        except BotoCoreError:
            try:
                await self._gw.abort_multipart_upload(
                    Bucket=self._bucket, Key=key, UploadId=uid
                )
            except BotoCoreError:
                _LOG.exception("Could not abort multipart upload %s", uid)
            raise
