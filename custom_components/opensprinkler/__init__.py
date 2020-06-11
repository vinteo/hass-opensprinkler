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
                await hass.async_add_executor_job(controller.refresh)
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

    def _get_controller_attributes(self, controller):
        attributes = {"opensprinkler_type": "controller"}
        for attr in [
            "enabled",
            "firmware_version",
            "hardware_version",
            "hardware_type",
            "hardware_type_name",
            "device_id",
            "ignore_password_enabled",
            "special_station_auto_refresh_enabled",
            "detected_expansion_board_count",
            "maximum_expansion_board_count",
            "dhcp_enabled",
            "ip_address",
            "ip_subnet",
            "gateway_address",
            "dns_address",
            "ntp_address",
            "ntp_enabled",
            "last_run_station",
            "last_run_program",
            "last_run_duration",
            "last_run_end_time",
            "rssi",
            "latitude",
            "longitude",
            "current_draw",
            "master_station_1",
            "master_station_1_time_on_adjustment",
            "master_station_1_time_off_adjustment",
            "master_station_2",
            "master_station_2_time_on_adjustment",
            "master_station_2_time_off_adjustment",
            "rain_delay_active",
            "rain_delay_stop_time",
            "rain_sensor_active",
            "sensor_1_active",
            "sensor_1_enabled",
            "sensor_1_type",
            "sensor_1_type_name",
            "sensor_1_option",
            "sensor_1_option_name",
            "sensor_1_delayed_on_time",
            "sensor_1_delayed_off_time",
            "sensor_2_active",
            "sensor_2_enabled",
            "sensor_2_type",
            "sensor_2_type_name",
            "sensor_2_option",
            "sensor_2_option_name",
            "sensor_2_delayed_on_time",
            "sensor_2_delayed_off_time",
            "rain_sensor_enabled",
            "flow_sensor_enabled",
            "soil_sensor_enabled",
            "program_switch_sensor_enabled",
            "flow_rate",
            "flow_count_window",
            "flow_count",
            "last_weather_call",
            "last_successfull_weather_call",
            "last_weather_call_error",
            "last_weather_call_error_name",
            "sunrise",
            "sunset",
            "last_reboot_time",
            "last_reboot_cause",
            "last_reboot_cause_name",
            "water_level",
        ]:
            try:
                attributes[attr] = getattr(controller, attr)
            except:
                pass

        for attr in [
            "last_run_end_time",
            "rain_delay_stop_time",
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
        attributes = {"opensprinkler_type": "program"}
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
            try:
                attributes[attr] = getattr(program, attr)
            except:
                pass

        return attributes

    def _get_station_attributes(self, station):
        attributes = {"opensprinkler_type": "station"}
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
            try:
                attributes[attr] = getattr(station, attr)
            except:
                pass

        for attr in ["start_time"]:
            iso_attr = attr + "_iso"
            timestamp = getattr(station, attr, 0)
            if not timestamp:
                attributes[attr] = None
                attributes[iso_attr] = None
            else:
                attributes[iso_attr] = utc_from_timestamp(timestamp).isoformat()

        return attributes

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
    def device_state_attributes(self):
        if hasattr(self, "_program"):
            return self._get_program_attributes(self._program)

        if hasattr(self, "_station"):
            return self._get_station_attributes(self._station)

        if hasattr(self, "_controller"):
            return self._get_controller_attributes(self._controller)

        return None

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
    def run(self, run_seconds=None):
        """Run once program."""
        if run_seconds == None or (
            not isinstance(run_seconds, list) and not isinstance(run_seconds, dict)
        ):
            raise Exception(
                "List of run seconds or dict of index/second pairs is required for controller"
            )

        if isinstance(run_seconds, dict):
            run_seconds_list = []
            for x in range(max(list(map(int, run_seconds.keys()))) + 1):
                run_seconds_list.append(
                    run_seconds.get(str(x))
                    if run_seconds.get(str(x)) is not None
                    else 0
                )
            return self._controller.run_once_program(run_seconds_list)

        if not isinstance(run_seconds[0], int):
            run_seconds_by_index = {}
            run_seconds_indexes = []
            for run_seconds_config in run_seconds:
                run_seconds_indexes.append(run_seconds_config[CONF_INDEX])
                run_seconds_by_index[
                    run_seconds_config[CONF_INDEX]
                ] = run_seconds_config[CONF_RUN_SECONDS]

            run_seconds_list = []
            for x in range(max(run_seconds_indexes) + 1):
                run_seconds_list.append(
                    run_seconds_by_index.get(x)
                    if run_seconds_by_index.get(x) is not None
                    else 0
                )
            return self._controller.run_once_program(run_seconds_list)

        return self._controller.run_once_program(run_seconds)

    def stop(self):
        """Stops all stations."""
        return self._controller.stop_all_stations()


class OpenSprinklerProgramEntity:
    def run(self):
        """Runs the program."""
        return self._program.run()


class OpenSprinklerStationEntity:
    def run(self, run_seconds=None):
        """Run station."""
        if run_seconds is not None and not isinstance(run_seconds, int):
            raise Exception("Run seconds should be an integer value for station")
        return self._station.run(run_seconds)

    def stop(self):
        """Stop station."""
        return self._station.stop()
