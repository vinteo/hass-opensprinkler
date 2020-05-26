"""OpenSprinkler integration."""
import asyncio
from datetime import timedelta
import logging

from pyopensprinkler import (
    OpenSprinkler,
    OpensprinklerAuthError,
    OpensprinklerConnectionError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import Throttle

from .const import DEFAULT_PORT, DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the openSprinkler component from YAML."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up OpenSprinkler from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    password = entry.data.get(CONF_PASSWORD)
    host = f"{entry.data.get(CONF_HOST)}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}"
    try:
        hass.data[DOMAIN][entry.entry_id] = await hass.async_add_executor_job(
            OpenSprinkler, host, password
        )
    except (OpensprinklerAuthError, OpensprinklerConnectionError) as exc:
        _LOGGER.error("Unable to connect to OpenSprinkler device: %s", str(exc))
        raise ConfigEntryNotReady

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class OpenSprinklerCoordinator:
    """Define a generic OpenSprinkler entity."""

    def __init__(self, hass, device):
        """Initialize."""
        self._cancel_time_interval_listener = None
        self._hass = hass
        self._device = device

    async def _async_update_listener_action(self, now):
        """Define an async_track_time_interval action to update data."""
        await self._hass.async_add_executor_job(self._device.update_state)

    async def async_register_time_interval_listener(self):
        """Register time interval listener."""
        if not self._cancel_time_interval_listener:
            self._cancel_time_interval_listener = async_track_time_interval(
                self._hass, self._async_update_listener_action, timedelta(seconds=15),
            )

    @callback
    def deregister_time_interval_listener(self):
        """Deregister time interval listener."""
        if self._cancel_time_interval_listener:
            self._cancel_time_interval_listener()
            self._cancel_time_interval_listener = None


class OpenSprinklerEntity(RestoreEntity):
    """Define a generic OpenSprinkler entity."""

    def __init__(self, entry_id, name, coordinator):
        """Initialize."""
        self._state = None
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._name = name

    def _get_state(self):
        """Retrieve the state."""
        raise NotImplementedError

    @property
    def device_info(self):
        """Return device information about Opensprinkler Controller."""
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": self._name,
            "manufacturer": "OpenSprinkler",
            "model": self._coordinator._device.device.hardware_version,
            "sw_version": self._coordinator._device.device.firmware_version,
        }

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(async_dispatcher_connect(self.hass, DOMAIN, self.update))
        await self._coordinator.async_register_time_interval_listener()
        self.update()

    async def async_will_remove_from_hass(self):
        """Disconnect dispatcher listeners and deregister API interest."""
        super().async_will_remove_from_hass()
        self._coordinator.deregister_time_interval_listener()

    @Throttle(SCAN_INTERVAL)
    def update(self) -> None:
        """Update latest state."""
        self._state = self._get_state()


class OpenSprinklerBinarySensor(OpenSprinklerEntity):
    """Define a generic OpenSprinkler binary sensor."""

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state


class OpenSprinklerSensor(OpenSprinklerEntity):
    """Define a generic OpenSprinkler sensor."""

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state
