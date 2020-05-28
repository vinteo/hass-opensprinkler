"""OpenSprinkler integration."""
import asyncio
from datetime import timedelta
import logging

from pyopensprinkler import (
    Controller as OpenSprinkler,
    OpenSprinklerAuthError,
    OpenSprinklerConnectionError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_URL
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import Throttle

from .const import DEFAULT_PORT, DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "sensor", "switch"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the openSprinkler component from YAML."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up OpenSprinkler from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    url = entry.data.get(CONF_URL)
    password = entry.data.get(CONF_PASSWORD)
    try:
        controller = OpenSprinkler(url, password)
        await hass.async_add_executor_job(controller.refresh)
        coordinator = OpenSprinklerCoordinator(hass, controller)
        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": coordinator,
            "controller": controller,
        }

    except (OpenSprinklerAuthError, OpenSprinklerConnectionError) as exc:
        _LOGGER.error("Unable to connect to OpenSprinkler controller: %s", str(exc))
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

    def __init__(self, hass, controller):
        """Initialize."""
        self._cancel_time_interval_listener = None
        self._hass = hass
        self._controller = controller

    async def _async_update_listener_action(self, now):
        """Define an async_track_time_interval action to update data."""
        await self._hass.async_add_executor_job(self._controller.refresh)

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

    def _get_controller_attributes(self, controller):
        attributes = {}
        for attr in [
            "firmware_version",
            "hardware_version",
            "last_run_station",
            "last_run_program",
            "last_run_duration",
            "last_run_end_time",
            "master_station_1",
            "master_station_2",
            "rain_delay_enabled",
            "rain_delay_stop_time",
            "rain_sensor_enabled",
            "sensor_1_enabled",
            "sensor_2_enabled",
            "operation_enabled",
            "water_level",
        ]:
            attributes[attr] = getattr(controller, attr)

        # station counts
        attributes["station_total_count"] = len(controller.stations)

        attributes["station_enabled_count"] = len(
            dict(filter(lambda e: e[1].enabled == True, controller.stations.items()))
        )

        attributes["station_is_running_count"] = len(
            dict(filter(lambda e: e[1].is_running == True, controller.stations.items()))
        )

        for status in [
            "manual",
            "once_program",
            "master_engaged",
            "idle",
            "program",
            "waiting",
        ]:
            key = f"station_{status}_count"
            attributes[key] = len(
                dict(
                    filter(lambda e: e[1].status == status, controller.stations.items())
                )
            )

        # program counts
        attributes["program_total_count"] = len(controller.programs)

        attributes["program_enabled_count"] = len(
            dict(filter(lambda e: e[1].enabled == True, controller.programs.items()))
        )

        attributes["program_is_running_count"] = len(
            dict(filter(lambda e: e[1].is_running == True, controller.programs.items()))
        )

        return attributes

    def _get_program_attributes(self, program):
        attributes = {}
        for attr in [
            "name",
            "index",
            "enabled",
            "is_running",
            "use_weather_adjustments",
            "odd_even_restriction",
            "odd_even_restriction_name",
            "program_schedule_type",
            "program_schedule_type_name",
            "start_time_type",
            "start_time_type_name",
        ]:
            attributes[attr] = getattr(program, attr)
        return attributes

    def _get_station_attributes(self, station):
        attributes = {}
        for attr in [
            "name",
            "index",
            "enabled",
            "is_running",
            "is_master",
            "running_program_id",
            "seconds_remaining",
            "start_time",
            "max_name_length",
            "master_1_operation_enabled",
            "master_2_operation_enabled",
            "rain_delay_ignored",
            "sensor_1_ignored",
            "sensor_2_ignored",
            "sequential_operation",
            "special",
            "station_type",
            "status",
        ]:
            attributes[attr] = getattr(station, attr)
        return attributes

    @property
    def device_info(self):
        """Return device information about Opensprinkler Controller."""
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": self._name,
            "manufacturer": "OpenSprinkler",
            "model": self._coordinator._controller.hardware_version,
            "sw_version": self._coordinator._controller.firmware_version,
        }

    @property
    def device_state_attributes(self):
        if hasattr(self, "_program"):
            return self._get_program_attributes(self._program)

        if hasattr(self, "_station"):
            return self._get_station_attributes(self._station)

        if hasattr(self, "_controller"):
            return self._get_controller_attributes(self._controller)

        return None

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(async_dispatcher_connect(self.hass, DOMAIN, self.update))
        await self._coordinator.async_register_time_interval_listener()
        self.update()

    async def async_will_remove_from_hass(self):
        """Disconnect dispatcher listeners and deregister API interest."""
        await super().async_will_remove_from_hass()
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
