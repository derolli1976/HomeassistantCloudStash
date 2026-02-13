"""CloudStash config-flow – setup, re-auth, and reconfigure wizards."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from aiobotocore.session import AioSession
from botocore.exceptions import (
    ClientError,
    ConnectionError as BotoConnectionError,
    ParamValidationError,
)
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    DOMAIN,
    FALLBACK_PREFIX,
    FALLBACK_REGION,
    OPT_BUCKET,
    OPT_ENDPOINT,
    OPT_KEY_ID,
    OPT_OBJECT_PREFIX,
    OPT_REGION,
    OPT_SECRET,
)

# ---------------------------------------------------------------------------
# Credential probe – runs in executor to keep the HA loop free
# ---------------------------------------------------------------------------

_PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
_URL = TextSelector(TextSelectorConfig(type=TextSelectorType.URL))


def _probe_connection(
    endpoint: str,
    key_id: str,
    secret: str,
    region: str,
    bucket: str,
) -> None:
    """Attempt a HeadBucket call in a throw-away event loop.

    Raises on auth failure, bad bucket name, unreachable endpoint, etc.
    """

    async def _check() -> None:
        session = AioSession()
        async with session.create_client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
            region_name=region,
        ) as client:
            await client.head_bucket(Bucket=bucket)

    asyncio.run(_check())


# ---------------------------------------------------------------------------
# Form schemas
# ---------------------------------------------------------------------------

SCHEMA_SETUP = vol.Schema(
    {
        vol.Required(OPT_KEY_ID): cv.string,
        vol.Required(OPT_SECRET): _PASSWORD,
        vol.Required(OPT_BUCKET): cv.string,
        vol.Required(OPT_ENDPOINT): _URL,
        vol.Required(OPT_REGION, default=FALLBACK_REGION): cv.string,
        vol.Optional(OPT_OBJECT_PREFIX, default=FALLBACK_PREFIX): cv.string,
    }
)

SCHEMA_CREDENTIALS = vol.Schema(
    {
        vol.Required(OPT_KEY_ID): cv.string,
        vol.Required(OPT_SECRET): _PASSWORD,
    }
)

SCHEMA_FULL_EDIT = vol.Schema(
    {
        vol.Required(OPT_KEY_ID): cv.string,
        vol.Required(OPT_SECRET): _PASSWORD,
        vol.Required(OPT_BUCKET): cv.string,
        vol.Required(OPT_ENDPOINT): _URL,
        vol.Required(OPT_REGION): cv.string,
        vol.Optional(OPT_OBJECT_PREFIX): cv.string,
    }
)


# ---------------------------------------------------------------------------
# Config flow
# ---------------------------------------------------------------------------


class CloudStashConfigFlow(ConfigFlow, domain=DOMAIN):
    """Guide the user through initial setup, re-auth, and reconfiguration."""

    VERSION = 1

    # -- initial setup -------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """First-time setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._async_abort_entries_match(
                {OPT_BUCKET: user_input[OPT_BUCKET], OPT_ENDPOINT: user_input[OPT_ENDPOINT]}
            )
            errors = await self._try_connect(user_input)
            if not errors:
                return self.async_create_entry(
                    title=user_input[OPT_BUCKET], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(SCHEMA_SETUP, user_input),
            errors=errors,
        )

    # -- re-authentication ---------------------------------------------------

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Entry point for the re-auth flow."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user for fresh credentials."""
        errors: dict[str, str] = {}
        target = self._get_reauth_entry()

        if user_input is not None:
            merged = {**target.data, **user_input}
            errors = await self._try_connect(merged)
            if not errors:
                return self.async_update_reload_and_abort(
                    target,
                    data_updates={
                        OPT_KEY_ID: user_input[OPT_KEY_ID],
                        OPT_SECRET: user_input[OPT_SECRET],
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                SCHEMA_CREDENTIALS, {OPT_KEY_ID: target.data[OPT_KEY_ID]}
            ),
            errors=errors,
        )

    # -- reconfigure ---------------------------------------------------------

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user change all settings except the domain."""
        errors: dict[str, str] = {}
        target = self._get_reconfigure_entry()

        if user_input is not None:
            self._async_abort_entries_match(
                {OPT_BUCKET: user_input[OPT_BUCKET], OPT_ENDPOINT: user_input[OPT_ENDPOINT]}
            )
            errors = await self._try_connect(user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    target,
                    data_updates=user_input,
                    title=user_input[OPT_BUCKET],
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                SCHEMA_FULL_EDIT, target.data
            ),
            errors=errors,
        )

    # -- shared validation ---------------------------------------------------

    async def _try_connect(self, data: dict[str, Any]) -> dict[str, str]:
        """Probe the remote endpoint; return a (possibly empty) error dict."""
        try:
            await self.hass.async_add_executor_job(
                _probe_connection,
                data[OPT_ENDPOINT],
                data[OPT_KEY_ID],
                data[OPT_SECRET],
                data.get(OPT_REGION, FALLBACK_REGION),
                data[OPT_BUCKET],
            )
        except ClientError:
            return {"base": "invalid_credentials"}
        except ParamValidationError as exc:
            if "Invalid bucket name" in str(exc):
                return {OPT_BUCKET: "invalid_bucket_name"}
        except ValueError:
            return {OPT_ENDPOINT: "invalid_endpoint_url"}
        except BotoConnectionError:
            return {OPT_ENDPOINT: "cannot_connect"}
        return {}
