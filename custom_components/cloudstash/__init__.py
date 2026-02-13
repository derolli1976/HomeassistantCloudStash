"""CloudStash – object-storage backup integration for Home Assistant."""

from __future__ import annotations

import asyncio
import logging
from threading import Event, Thread
from typing import Any, cast

from aiobotocore.session import AioSession
from botocore.exceptions import (
    ClientError,
    ConnectionError as BotoConnectionError,
    ParamValidationError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)

from .const import (
    AGENT_LISTENER_KEY,
    DOMAIN,
    FALLBACK_REGION,
    OPT_BUCKET,
    OPT_ENDPOINT,
    OPT_KEY_ID,
    OPT_REGION,
    OPT_SECRET,
)

_LOG = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config-entry type alias
# ---------------------------------------------------------------------------

type CloudStashEntry = ConfigEntry[ObjectStorageGateway]


# ---------------------------------------------------------------------------
# Thin S3-client proxy – offloads all I/O to a private worker thread
# ---------------------------------------------------------------------------


class ObjectStorageGateway:
    """Proxy that forwards every S3 call to a worker thread with its own loop.

    Botocore performs blocking filesystem reads (data model files, CA bundle)
    during client creation; running it in a separate thread keeps the HA
    event loop responsive.
    """

    _loop: asyncio.AbstractEventLoop | None
    _worker: Thread | None
    _ready: Event
    _running: bool
    _session_ctx: Any  # the async-context-manager returned by create_client

    def __init__(
        self,
        *,
        endpoint: str | None,
        key_id: str,
        secret: str,
        region: str,
        bucket: str,
    ) -> None:
        self._endpoint = endpoint
        self._key_id = key_id
        self._secret = secret
        self._region = region
        self._bucket = bucket
        self._handle: Any = None
        self._loop = None
        self._worker = None
        self._ready = Event()
        self._running = False

    # -- lifecycle -----------------------------------------------------------

    def _thread_main(self) -> None:
        """Entry point for the worker thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()

    async def _open(self) -> None:
        session = AioSession()
        # pylint: disable-next=unnecessary-dunder-call
        self._handle = await session.create_client(
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=self._key_id,
            aws_secret_access_key=self._secret,
            region_name=self._region,
        ).__aenter__()
        await self._handle.head_bucket(Bucket=self._bucket)

    async def _close(self) -> None:
        if self._handle is not None:
            await self._handle.__aexit__(None, None, None)
            self._handle = None

    def launch(self) -> None:
        """Spin up worker thread and create the client (blocking)."""
        if self._running:
            return
        self._worker = Thread(target=self._thread_main, daemon=True)
        self._worker.start()
        self._ready.wait(timeout=10)
        if self._loop is None:
            raise RuntimeError("Worker loop did not start in time")
        asyncio.run_coroutine_threadsafe(self._open(), self._loop).result()
        self._running = True

    def shutdown(self) -> None:
        """Tear down the worker thread (blocking)."""
        if not self._running or self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._close(), self._loop).result()
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._worker is not None:
            self._worker.join(timeout=5)
        self._running = False

    # -- dispatch helper -----------------------------------------------------

    async def _run[T](self, coro: Any) -> T:
        """Submit *coro* to the worker loop and bridge the result back."""
        if self._loop is None:
            raise RuntimeError("Gateway not started")
        return await asyncio.wrap_future(
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        )

    # -- proxied S3 operations -----------------------------------------------

    async def head_bucket(self, **kw: Any) -> dict[str, Any]:
        """Proxy: HeadBucket."""
        return await self._run(self._handle.head_bucket(**kw))

    async def list_objects_v2(self, **kw: Any) -> dict[str, Any]:
        """Proxy: ListObjectsV2."""
        return await self._run(self._handle.list_objects_v2(**kw))

    async def get_object(self, **kw: Any) -> dict[str, Any]:
        """Proxy: GetObject."""
        return await self._run(self._handle.get_object(**kw))

    async def put_object(self, **kw: Any) -> dict[str, Any]:
        """Proxy: PutObject."""
        return await self._run(self._handle.put_object(**kw))

    async def delete_object(self, **kw: Any) -> dict[str, Any]:
        """Proxy: DeleteObject."""
        return await self._run(self._handle.delete_object(**kw))

    async def create_multipart_upload(self, **kw: Any) -> dict[str, Any]:
        """Proxy: CreateMultipartUpload."""
        return await self._run(self._handle.create_multipart_upload(**kw))

    async def upload_part(self, **kw: Any) -> dict[str, Any]:
        """Proxy: UploadPart."""
        return await self._run(self._handle.upload_part(**kw))

    async def complete_multipart_upload(self, **kw: Any) -> dict[str, Any]:
        """Proxy: CompleteMultipartUpload."""
        return await self._run(self._handle.complete_multipart_upload(**kw))

    async def abort_multipart_upload(self, **kw: Any) -> dict[str, Any]:
        """Proxy: AbortMultipartUpload."""
        return await self._run(self._handle.abort_multipart_upload(**kw))


# ---------------------------------------------------------------------------
# Entry setup / teardown
# ---------------------------------------------------------------------------


async def async_setup_entry(hass: HomeAssistant, entry: CloudStashEntry) -> bool:
    """Initialise a CloudStash config entry."""
    cfg = cast(dict, entry.data)

    gateway = ObjectStorageGateway(
        endpoint=cfg.get(OPT_ENDPOINT),
        key_id=cfg[OPT_KEY_ID],
        secret=cfg[OPT_SECRET],
        region=cfg.get(OPT_REGION, FALLBACK_REGION),
        bucket=cfg[OPT_BUCKET],
    )

    try:
        await hass.async_add_executor_job(gateway.launch)
    except ClientError as exc:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN,
            translation_key="invalid_credentials",
        ) from exc
    except ParamValidationError as exc:
        if "Invalid bucket name" in str(exc):
            raise ConfigEntryError(
                translation_domain=DOMAIN,
                translation_key="invalid_bucket_name",
            ) from exc
        raise
    except ValueError as exc:
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="invalid_endpoint_url",
        ) from exc
    except BotoConnectionError as exc:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="cannot_connect",
        ) from exc

    entry.runtime_data = gateway

    def _propagate_state_change() -> None:
        for cb in hass.data.get(AGENT_LISTENER_KEY, []):
            cb()

    entry.async_on_unload(entry.async_on_state_change(_propagate_state_change))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CloudStashEntry) -> bool:
    """Tear down a CloudStash config entry."""
    await hass.async_add_executor_job(entry.runtime_data.shutdown)
    return True
