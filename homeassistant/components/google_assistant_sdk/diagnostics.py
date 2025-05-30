"""Diagnostics support for Google Assistant SDK."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .helpers import GoogleAssistantSDKConfigEntry

TO_REDACT = {"access_token", "refresh_token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GoogleAssistantSDKConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return async_redact_data(
        {
            "data": entry.data,
            "options": entry.options,
        },
        TO_REDACT,
    )
