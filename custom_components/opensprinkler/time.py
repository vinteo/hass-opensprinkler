"""Component providing support for OpenSprinkler time entities."""
import datetime
import logging
from datetime import time
from typing import Callable

from homeassistant.components.time import TimeEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from . import OpenSprinklerProgramEntity, OpenSprinklerTime
from .const import DOMAIN, START_TIME_SUNRISE_BIT, START_TIME_SUNSET_BIT

_LOGGER = logging.getLogger(__name__)


@staticmethod
def is_set(x, n):
    return x & 1 << n != 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: dict,
    async_add_entities: Callable,
):
    """Set up the OpenSprinkler times."""
    entities = _create_entities(hass, entry)
    async_add_entities(entities)


def _create_entities(hass: HomeAssistant, entry: dict):
    entities = []

    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name = entry.data[CONF_NAME]

    for _, program in controller.programs.items():
        entities.append(ProgramStartTime(entry, name, program, coordinator))

    return entities


class ProgramStartTime(OpenSprinklerProgramEntity, OpenSprinklerTime, TimeEntity):
    """Represent time for the start time of a program."""

    def __init__(self, entry, name, program, coordinator):
        """Set up a new OpenSprinkler program time for program start time."""
        self._program = program
        self._entity_type = "time"
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this time."""
        return f"{self._program.name} Start Time"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_start_time_{self._program.index}"
        )

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:clock-start"

    @property
    def native_value(self) -> time:
        """The value of the time."""
        start_index = 0
        minutes = self._program.program_start_times[start_index]
        # Temporary patch until sunset/sunrise times supported by pyopensprinkler
        if is_set(minutes, START_TIME_SUNSET_BIT) or is_set(
            minutes, START_TIME_SUNRISE_BIT
        ):
            the_time = datetime.time(0, 0)
        else:
            the_time = datetime.time(round(minutes / 60), minutes % 60, 0)
        return the_time

    async def async_set_value(self, value: time) -> None:
        """Update the current value."""
        minutes = value.hour * 60 + value.minute
        start_index = 0
        await self._program.set_program_start_time(start_index, minutes)
        await self._coordinator.async_request_refresh()
