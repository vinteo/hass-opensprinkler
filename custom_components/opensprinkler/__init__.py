"""OpenSprinkler integration."""
import asyncio
import async_timeout
import logging

from datetime import timedelta

from pyopensprinkler import (
    Controller as OpenSprinkler,
    OpenSprinklerAuthError,
    OpenSprinklerConnectionError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_URL
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import slugify
from homeassistant.util.dt import utc_from_timestamp

from .const import (
    CONF_INDEX,
    CONF_RUN_SECONDS,
    DEFAULT_PORT,
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "sensor", "switch"]
TIMEOUT = 10


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
        controller.refresh_on_update = False

        async def async_update_data():
            """Fetch data from OpenSprinkler."""
            _LOGGER.debug("refreshing data")
            async with async_timeout.timeout(TIMEOUT):
                try:
                    await hass.async_add_executor_job(controller.refresh)
                except Exception as exc:
                    raise UpdateFailed("Error fetching OpenSprinkler state") from exc

                if not controller._state:
                    raise UpdateFailed("Error fetching OpenSprinkler state")

                return controller._state

        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="OpenSprinkler resource status",
            update_method=async_update_data,
            update_interval=timedelta(seconds=scan_interval),
        )

        # initial load before loading platforms
        await coordinator.async_refresh()

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


class OpenSprinklerEntity(RestoreEntity):
    """Define a generic OpenSprinkler entity."""

    def __init__(self, entry, name, coordinator):
        """Initialize."""
        self._coordinator = coordinator
        self._entry = entry
        self._name = name

    def _get_state(self):
        """Retrieve the state."""
        raise NotImplementedError

    @property
    def device_info(self):
        """Return device information about Opensprinkler Controller."""

        controller = self.hass.data[DOMAIN][self._entry.entry_id]["controller"]

        return {
            "identifiers": {(DOMAIN, slugify(self._entry.unique_id))},
            "name": self._name,
            "manufacturer": "OpenSprinkler",
            "model": controller.hardware_version,
            "sw_version": controller.firmware_version,
        }

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self):
        """Return if entity is available."""
        return self._coordinator.last_update_success

    async def async_added_to_hass(self):
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update latest state."""
        await self._coordinator.async_request_refresh()


class OpenSprinklerBinarySensor(OpenSprinklerEntity):
    """Define a generic OpenSprinkler binary sensor."""

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._get_state()


class OpenSprinklerSensor(OpenSprinklerEntity):
    """Define a generic OpenSprinkler sensor."""

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._get_state()


class OpenSprinklerControllerEntity:
    @property
    def device_state_attributes(self):
        controller = self._controller
        attributes = {"opensprinkler_type": "controller"}
        for attr in [
            "firmware_version",
            "hardware_version",
            "hardware_type",
            "last_run_station",
            "last_run_program",
            "last_run_duration",
            "rain_sensor_active",
            "sensor_1_enabled",
            "sensor_2_enabled",
            "rain_sensor_enabled",
            "flow_sensor_enabled",
            "soil_sensor_enabled",
            "last_weather_call",
            "last_successfull_weather_call",
            "last_weather_call_error",
            "last_weather_call_error_name",
            "last_reboot_time",
            "last_reboot_cause",
            "last_reboot_cause_name",
        ]:
            try:
                attributes[attr] = getattr(controller, attr)
            except:
                pass

        for attr in [
            "last_weather_call",
            "last_successfull_weather_call",
            "last_reboot_time",
        ]:
            iso_attr = attr + "_iso"
            timestamp = getattr(controller, attr)
            if not timestamp:
                attributes[attr] = None
                attributes[iso_attr] = None
            else:
                attributes[iso_attr] = utc_from_timestamp(timestamp).isoformat()

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
                    filter(
                        lambda e: e[1].status == status, controller.stations.items(),
                    )
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

    async def run(self, run_seconds=None, continue_running_stations=None):
        """Run once program."""
        if run_seconds == None or (
            not isinstance(run_seconds, list) and not isinstance(run_seconds, dict)
        ):
            raise Exception(
                "List of run seconds or dict of index/second pairs is required for controller"
            )

        if continue_running_stations == None:
            continue_running_stations = False

        await self.hass.async_add_executor_job(self._controller.refresh)

        if isinstance(run_seconds, dict):
            run_seconds_list = []
            for _, station in self._controller.stations.items():
                run_seconds_list.append(
                    run_seconds.get(str(station.index))
                    if run_seconds.get(str(station.index)) is not None
                    else (
                        0
                        if continue_running_stations == True
                        else station.seconds_remaining
                    )
                )
            await self.hass.async_add_executor_job(
                self._controller.run_once_program, run_seconds_list
            )
            await self._coordinator.async_request_refresh()
            return

        if not isinstance(run_seconds[0], int):
            run_seconds_by_index = {}
            for run_seconds_config in run_seconds:
                run_seconds_by_index[
                    run_seconds_config[CONF_INDEX]
                ] = run_seconds_config[CONF_RUN_SECONDS]

            run_seconds_list = []
            for _, station in self._controller.stations.items():
                run_seconds_list.append(
                    run_seconds_by_index.get(station.index)
                    if run_seconds_by_index.get(station.index) is not None
                    else (
                        0
                        if continue_running_stations == True
                        else station.seconds_remaining
                    )
                )

            await self.hass.async_add_executor_job(
                self._controller.run_once_program, run_seconds_list
            )
            await self._coordinator.async_request_refresh()
            return

        await self.hass.async_add_executor_job(
            self._controller.run_once_program, run_seconds
        )
        await self._coordinator.async_request_refresh()
        return

    async def stop(self):
        """Stops all stations."""
        await self.hass.async_add_executor_job(self._controller.stop_all_stations)
        await self._coordinator.async_request_refresh()


class OpenSprinklerProgramEntity:
    @property
    def device_state_attributes(self):
        attributes = {"opensprinkler_type": "program"}
        for attr in [
            "name",
            "index",
        ]:
            try:
                attributes[attr] = getattr(self._program, attr)
            except:
                pass

        return attributes

    async def run(self):
        """Runs the program."""
        await self.hass.async_add_executor_job(self._program.run)
        await self._coordinator.async_request_refresh()


class OpenSprinklerStationEntity:
    @property
    def device_state_attributes(self):
        attributes = {"opensprinkler_type": "station"}
        for attr in [
            "name",
            "index",
            "is_master",
            "running_program_id",
            "seconds_remaining",
            "start_time",
            "rain_delay_ignored",
            "sensor_1_ignored",
            "sensor_2_ignored",
            "sequential_operation",
        ]:
            try:
                attributes[attr] = getattr(self._station, attr)
            except:
                pass

        for attr in ["start_time"]:
            iso_attr = attr + "_iso"
            timestamp = getattr(self._station, attr, 0)
            if not timestamp:
                attributes[attr] = None
                attributes[iso_attr] = None
            else:
                attributes[iso_attr] = utc_from_timestamp(timestamp).isoformat()

        return attributes

    async def run(self, run_seconds=None):
        """Run station."""
        if run_seconds is not None and not isinstance(run_seconds, int):
            raise Exception("Run seconds should be an integer value for station")

        await self.hass.async_add_executor_job(self._station.run, run_seconds)
        await self._coordinator.async_request_refresh()

    async def stop(self):
        """Stop station."""
        await self.hass.async_add_executor_job(self._station.stop)
        await self._coordinator.async_request_refresh()
