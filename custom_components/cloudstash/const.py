"""CloudStash integration constants."""

from collections.abc import Callable
from typing import Final

from homeassistant.util.hass_dict import HassKey

DOMAIN: Final = "cloudstash"

# --- Config entry keys ---
OPT_KEY_ID = "access_key_id"
OPT_SECRET = "secret_access_key"
OPT_ENDPOINT = "endpoint_url"
OPT_BUCKET = "bucket"
OPT_REGION = "region"
OPT_OBJECT_PREFIX = "prefix"

# --- Defaults ---
FALLBACK_REGION = "us-east-1"
FALLBACK_PREFIX = "homeassistant"
STORAGE_DIR = "backups"

# --- Internal keys ---
AGENT_LISTENER_KEY: HassKey[list[Callable[[], None]]] = HassKey(
    f"{DOMAIN}.agent_listeners"
)
