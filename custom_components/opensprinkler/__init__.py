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

from homeassistant.components import mqtt
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
    CONF_MQTT,
    CONF_INDEX,
    CONF_RUN_SECONDS,
    DEFAULT_PORT,
    DOMAIN,
    DEFAULT_MQTT,
    DEFAULT_SCAN_INTERVAL,
    MQTT_TOPIC,
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
    mqtt_option = entry.data.get(CONF_MQTT, DEFAULT_MQTT)

    try:
        controller = OpenSprinkler(url, password)
        controller.refresh_on_update = False

        if mqtt_option:

            async def on_message(message):
                try:
                    await hass.async_add_executor_job(controller.refresh)
                except Exception as exc:
                    raise UpdateFailed("Error fetching OpenSprinkler state") from exc

            await mqtt.async_subscribe(hass, MQTT_TOPIC, on_message)

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

        scan_interval = (
            300
            if mqtt_option
            else entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="OpenSprinkler resource status",
            update_method=async_update_data,
            update_interval=timedelta(seconds=scan_interval),
        )

        # initial load before loading platforms
        await hass.async_add_executor_job(controller.refresh)

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

    def __init__(self, entry, name):
        """Initialize."""
        self._entry = entry
        self._name = name

    def _get_state(self):
        """Retrieve the state."""
        raise NotImplementedError

    def _get_controller(self):
        return self.hass.data[DOMAIN][self._entry.entry_id]["controller"]

    def _get_coordinator(self):
        return self.hass.data[DOMAIN][self._entry.entry_id]["coordinator"]

    @property
    def device_info(self):
        """Return device information about Opensprinkler Controller."""

        controller = self._get_controller()
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
        return self._get_coordinator().last_update_success

    async def async_added_to_hass(self):
        self.async_on_remove(
            self._get_coordinator().async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update latest state."""
        await self.hass.async_add_executor_job(self._get_controller().refresh)
        self.async_write_ha_state()


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

        await self.async_update()

        if isinstance(run_seconds, dict):
            run_seconds_list = []
            for _, station in self._get_controller().stations.items():
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
                self._get_controller().run_once_program, run_seconds_list
            )
            await self.async_update()
            return

        if not isinstance(run_seconds[0], int):
            run_seconds_by_index = {}
            for run_seconds_config in run_seconds:
                run_seconds_by_index[
                    run_seconds_config[CONF_INDEX]
                ] = run_seconds_config[CONF_RUN_SECONDS]

            run_seconds_list = []
            for _, station in self._get_controller().stations.items():
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
                self._get_controller().run_once_program, run_seconds_list
            )
            await self.async_update()
            return

        await self.hass.async_add_executor_job(
            self._get_controller().run_once_program, run_seconds
        )
        await self.async_update()
        return

    async def stop(self):
        """Stops all stations."""
        await self.hass.async_add_executor_job(self._get_controller().stop_all_stations)
        await self.async_update()


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
        await self.async_update()


class OpenSprinklerStationEntity:
    @property
    def device_state_attributes(self):
        attributes = {"opensprinkler_type": "station"}
        for attr in [
            "name",
            "index",
            "is_master",
            "running_program_id",
        ]:
            try:
                attributes[attr] = getattr(self._station, attr)
            except:
                pass

        for attr in ["start_time", "end_time"]:
            timestamp = getattr(self._station, attr, 0)
            if not timestamp:
                attributes[attr] = None
            else:
                attributes[attr] = utc_from_timestamp(timestamp).isoformat()

        return attributes

    async def run(self, run_seconds=None):
        """Run station."""
        if run_seconds is not None and not isinstance(run_seconds, int):
            raise Exception("Run seconds should be an integer value for station")

        await self.hass.async_add_executor_job(self._station.run, run_seconds)
        await self.async_update()

    async def stop(self):
        """Stop station."""
        await self.hass.async_add_executor_job(self._station.stop)
        await self.async_update()
