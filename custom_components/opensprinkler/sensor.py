"""OpenSprinkler integration."""
import logging
from typing import Callable

from homeassistant.const import CONF_NAME, DEVICE_CLASS_TIMESTAMP
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.util.dt import utc_from_timestamp

from . import OpenSprinklerSensor
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: dict, async_add_entities: Callable,
):
    """Set up the opensprinkler sensors."""
    entities = _create_entities(hass, entry)
    async_add_entities(entities)


def _create_entities(hass: HomeAssistant, entry: dict):
    entities = []

    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name = entry.data[CONF_NAME]

    entities.append(LastRunSensor(entry.entry_id, name, controller, coordinator))
    entities.append(
        RainDelayStopTimeSensor(entry.entry_id, name, controller, coordinator)
    )
    entities.append(WaterLevelSensor(entry.entry_id, name, controller, coordinator))

    for _, station in controller.stations.items():
        entities.append(
            StationSensor(entry.entry_id, name, station, controller, coordinator)
        )

    return entities


class WaterLevelSensor(OpenSprinklerSensor, Entity):
    """Represent a sensor that for water level."""

    def __init__(self, entry_id, name, controller, coordinator):
        """Set up a new opensprinkler water level sensor."""
        self._name = name
        self._controller = controller
        self._entity_type = "sensor"
        super().__init__(entry_id, name, coordinator)

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:water"

    @property
    def name(self) -> str:
        """Return the name of this sensor including the controller name."""
        return f"{self._name} Water Level"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._entry_id}_{self._entity_type}_water_level"

    @property
    def unit_of_measurement(self) -> str:
        """Return the units of measurement."""
        return "%"

    def _get_state(self) -> int:
        """Retrieve latest state."""
        return self._controller.water_level


class LastRunSensor(OpenSprinklerSensor, Entity):
    """Represent a sensor that for last run time."""

    def __init__(self, entry_id, name, controller, coordinator):
        """Set up a new opensprinkler last run sensor."""
        self._controller = controller
        self._entity_type = "sensor"
        super().__init__(entry_id, name, coordinator)

    @property
    def device_class(self):
        """Return the device class."""
        return DEVICE_CLASS_TIMESTAMP

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:history"

    @property
    def name(self) -> str:
        """Return the name of this sensor including the controller name."""
        return f"{self._name} Last Run"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._entry_id}_{self._entity_type}_last_run"

    def _get_state(self):
        """Retrieve latest state."""
        last_run = self._controller.last_run_end_time
        return utc_from_timestamp(last_run).isoformat()


class RainDelayStopTimeSensor(OpenSprinklerSensor, Entity):
    """Represent a sensor that for rain delay stop time."""

    def __init__(self, entry_id, name, controller, coordinator):
        """Set up a new opensprinkler rain delay stop time sensor."""
        self._controller = controller
        self._entity_type = "sensor"
        super().__init__(entry_id, name, coordinator)

    @property
    def device_class(self):
        """Return the device class."""
        return DEVICE_CLASS_TIMESTAMP

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:weather-rainy"

    @property
    def name(self) -> str:
        """Return the name of this sensor including the controller name."""
        return f"{self._name} Rain Delay Stop Time"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._entry_id}_{self._entity_type}_rdst"

    def _get_state(self):
        """Retrieve latest state."""
        rdst = self._controller.rain_delay_stop_time
        if rdst == 0:
            return None

        return utc_from_timestamp(rdst).isoformat()


class StationSensor(OpenSprinklerSensor, Entity):
    """Represent a sensor for status of station."""

    def __init__(self, entry_id, name, station, controller, coordinator):
        """Set up a new OpenSprinkler station sensor."""
        self._station = station
        self._controller = controller
        self._entity_type = "sensor"
        super().__init__(entry_id, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this sensor."""
        return self._station.name

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._entry_id}_{self._entity_type}_station_{self._station.index}"

    def _get_state(self) -> str:
        """Retrieve latest state."""
        return self._station.status
