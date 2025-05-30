"""ZHA repairs for common environmental and device problems."""

from __future__ import annotations

import enum
import logging

from homeassistant.components.homeassistant_hardware.util import (
    ApplicationType,
    probe_silabs_firmware_type,
)
from homeassistant.components.homeassistant_sky_connect import (
    hardware as skyconnect_hardware,
)
from homeassistant.components.homeassistant_yellow import (
    RADIO_DEVICE as YELLOW_RADIO_DEVICE,
    hardware as yellow_hardware,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AlreadyRunningEZSP(Exception):
    """The device is already running EZSP firmware."""


class HardwareType(enum.StrEnum):
    """Detected Zigbee hardware type."""

    SKYCONNECT = "skyconnect"
    YELLOW = "yellow"
    OTHER = "other"


ISSUE_WRONG_SILABS_FIRMWARE_INSTALLED = "wrong_silabs_firmware_installed"


def _detect_radio_hardware(hass: HomeAssistant, device: str) -> HardwareType:
    """Identify the radio hardware with the given serial port."""
    try:
        yellow_hardware.async_info(hass)
    except HomeAssistantError:
        pass
    else:
        if device == YELLOW_RADIO_DEVICE:
            return HardwareType.YELLOW

    try:
        info = skyconnect_hardware.async_info(hass)
    except HomeAssistantError:
        pass
    else:
        for hardware_info in info:
            for entry_id in hardware_info.config_entries or []:
                entry = hass.config_entries.async_get_entry(entry_id)

                if entry is not None and entry.data["device"] == device:
                    return HardwareType.SKYCONNECT

    return HardwareType.OTHER


async def warn_on_wrong_silabs_firmware(hass: HomeAssistant, device: str) -> bool:
    """Create a repair issue if the wrong type of SiLabs firmware is detected."""
    # Only consider actual serial ports
    if device.startswith("socket://"):
        return False

    app_type = await probe_silabs_firmware_type(device)

    if app_type is None:
        # Failed to probe, we can't tell if the wrong firmware is installed
        return False

    if app_type == ApplicationType.EZSP:
        # If connecting fails but we somehow probe EZSP (e.g. stuck in bootloader),
        # reconnect, it should work
        raise AlreadyRunningEZSP

    hardware_type = _detect_radio_hardware(hass, device)
    ir.async_create_issue(
        hass,
        domain=DOMAIN,
        issue_id=ISSUE_WRONG_SILABS_FIRMWARE_INSTALLED,
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key=(
            ISSUE_WRONG_SILABS_FIRMWARE_INSTALLED
            + ("_nabucasa" if hardware_type != HardwareType.OTHER else "_other")
        ),
        translation_placeholders={"firmware_type": app_type.name},
    )

    return True
