"""Component providing support for OpenSprinkler number entities."""
import logging
from typing import Callable

from homeassistant.components.number import NumberEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from . import OpenSprinklerNumber, OpenSprinklerProgramEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: dict,
    async_add_entities: Callable,
):
    """Set up the OpenSprinkler numbers."""
    entities = _create_entities(hass, entry)
    async_add_entities(entities)


def _create_entities(hass: HomeAssistant, entry: dict):
    entities = []

    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name = entry.data[CONF_NAME]

    for _, program in controller.programs.items():
        for _, station in controller.stations.items():
            entities.append(
                ProgramDurationNumber(entry, name, program, station, coordinator)
            )

    return entities


class ProgramDurationNumber(
    OpenSprinklerProgramEntity, OpenSprinklerNumber, NumberEntity
):
    """Represent a number for duration of a station in a program."""

    def __init__(self, entry, name, program, station, coordinator):
        """Set up a new OpenSprinkler program/station sensor."""
        self._program = program
        self._station = station
        self._entity_type = "number"
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this sensor."""
        return f"{self._program.name} {self._station.name} Station Duration"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_station_duration_{self._program.index}_{self._station.index}"
        )

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the units of measurement."""
        return "min"

    @property
    def mode(self) -> str:
        """Return the units of measurement."""
        return "auto"

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:timer-sand"

    @property
    def native_value(self) -> float:
        """Retrieve latest duration in minutes."""
        return round(self._program.station_durations[self._station.index] / 60.0)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._program.set_station_duration(
            self._station.index, round(value * 60.0)
        )
        await self._coordinator.async_request_refresh()
