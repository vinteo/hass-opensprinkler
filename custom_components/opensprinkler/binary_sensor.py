"""OpenSprinkler integration."""
import logging
from typing import Callable

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.util import slugify

from . import (
    OpenSprinklerBinarySensor,
    OpenSprinklerControllerEntity,
    OpenSprinklerProgramEntity,
    OpenSprinklerStationEntity,
)
from .const import (
    DOMAIN,
    SCHEMA_SERVICE_RUN,
    SCHEMA_SERVICE_STOP,
    SERVICE_RUN,
    SERVICE_STOP,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: dict, async_add_entities: Callable,
):
    """Set up the OpenSprinkler binary sensors."""
    entities = _create_entities(hass, entry)
    async_add_entities(entities)

    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(
        SERVICE_RUN, SCHEMA_SERVICE_RUN, "run",
    )
    platform.async_register_entity_service(
        SERVICE_STOP, SCHEMA_SERVICE_STOP, "stop",
    )


def _create_entities(hass: HomeAssistant, entry: dict):
    entities = []

    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    name = entry.data[CONF_NAME]

    entities.append(ControllerSensorActive(entry, name, "sensor_1_active"))
    entities.append(ControllerSensorActive(entry, name, "sensor_2_active"))
    entities.append(ControllerSensorActive(entry, name, "rain_delay_active"))

    for _, program in controller.programs.items():
        entities.append(ProgramIsRunningBinarySensor(entry, name, program))

    for _, station in controller.stations.items():
        entities.append(StationIsRunningBinarySensor(entry, name, station))

    return entities


class ControllerSensorActive(
    OpenSprinklerControllerEntity, OpenSprinklerBinarySensor, BinarySensorEntity
):
    """Represent a sensor that for water level."""

    def __init__(self, entry, name, attr):
        """Set up a new opensprinkler water level sensor."""
        self._name = name
        self._entity_type = "binary_sensor"
        self._attr = attr
        super().__init__(entry, name)

    @property
    def name(self) -> str:
        """Return the name of this sensor including the controller name."""
        return f"{self._name} {self._attr.replace('_', ' ').title()}"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(f"{self._entry.unique_id}_{self._entity_type}_{self._attr}")

    def _get_state(self) -> int:
        """Retrieve latest state."""
        controller = self.hass.data[DOMAIN][self._entry.entry_id]["controller"]
        return bool(getattr(controller, self._attr))


class ProgramIsRunningBinarySensor(
    OpenSprinklerProgramEntity, OpenSprinklerBinarySensor, BinarySensorEntity
):
    """Represent a binary_sensor for is_running of a program."""

    def __init__(self, entry, name, program):
        """Set up a new OpenSprinkler station sensor."""
        self._program = program
        self._entity_type = "binary_sensor"
        super().__init__(entry, name)

    @property
    def name(self) -> str:
        """Return the name of this sensor."""
        return self._program.name + " Program Running"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_program_running_{self._program.index}"
        )

    @property
    def icon(self) -> str:
        """Return icon."""
        if self._program.is_running:
            return "mdi:timer"

        return "mdi:timer-off"

    def _get_state(self) -> bool:
        """Retrieve latest state."""
        return bool(self._program.is_running)


class StationIsRunningBinarySensor(
    OpenSprinklerStationEntity, OpenSprinklerBinarySensor, BinarySensorEntity
):
    """Represent a binary_sensor for is_running of a station."""

    def __init__(self, entry, name, station):
        """Set up a new OpenSprinkler station sensor."""
        self._station = station
        self._entity_type = "binary_sensor"
        super().__init__(entry, name)

    @property
    def name(self) -> str:
        """Return the name of this sensor."""
        return self._station.name + " Station Running"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_station_running_{self._station.index}"
        )

    @property
    def icon(self) -> str:
        """Return icon."""
        if self._station.is_master:
            if self._station.is_running:
                return "mdi:water-pump"
            else:
                return "mdi:water-pump-off"

        if self._station.is_running:
            return "mdi:valve-open"

        return "mdi:valve-closed"

    def _get_state(self) -> bool:
        """Retrieve latest state."""
        return bool(self._station.is_running)
