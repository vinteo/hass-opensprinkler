"""OpenSprinkler integration."""
import logging
from typing import Callable

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from . import OpenSprinklerBinarySensor
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: dict, async_add_entities: Callable,
):
    """Set up the OpenSprinkler binary sensors."""
    entities = _create_entities(hass, entry)
    async_add_entities(entities)


def _create_entities(hass: HomeAssistant, entry: dict):
    entities = []

    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name = entry.data[CONF_NAME]

    for _, program in controller.programs.items():
        entities.append(
            ProgramIsRunningBinarySensor(entry.entry_id, name, program, coordinator)
        )

    for _, station in controller.stations.items():
        entities.append(
            StationIsRunningBinarySensor(entry.entry_id, name, station, coordinator)
        )

    return entities


class ProgramIsRunningBinarySensor(OpenSprinklerBinarySensor, BinarySensorEntity):
    """Represent a binary_sensor for is_running of a program."""

    def __init__(self, entry_id, name, program, coordinator):
        """Set up a new OpenSprinkler station sensor."""
        self._program = program
        self._entity_type = "binary_sensor"
        super().__init__(entry_id, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this sensor."""
        return self._program.name + " Program Running"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._entry_id}_{self._entity_type}_program_running_{self._program.index}"

    def _get_state(self) -> bool:
        """Retrieve latest state."""
        return bool(self._program.is_running)


class StationIsRunningBinarySensor(OpenSprinklerBinarySensor, BinarySensorEntity):
    """Represent a binary_sensor for is_running of a station."""

    def __init__(self, entry_id, name, station, coordinator):
        """Set up a new OpenSprinkler station sensor."""
        self._station = station
        self._entity_type = "binary_sensor"
        super().__init__(entry_id, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this sensor."""
        return self._station.name + " Station Running"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._entry_id}_{self._entity_type}_station_running_{self._station.index}"

    def _get_state(self) -> bool:
        """Retrieve latest state."""
        return bool(self._station.is_running)
