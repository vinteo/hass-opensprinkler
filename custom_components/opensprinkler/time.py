"""Component providing support for OpenSprinkler time entities."""

import datetime
import logging
from datetime import time
from math import trunc
from typing import Callable

from homeassistant.components.time import TimeEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from . import OpenSprinklerProgramEntity, OpenSprinklerTime
from .const import DOMAIN, START_TIME_MIDNIGHT, START_TIME_SUNRISE, START_TIME_SUNSET

_LOGGER = logging.getLogger(__name__)


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
        for start_index in range(4):
            entities.append(
                ProgramStartTime(
                    entry, name, controller, program, start_index, coordinator
                )
            )

    return entities


class ProgramStartTime(OpenSprinklerProgramEntity, OpenSprinklerTime, TimeEntity):
    """Represent time for the start time of a program."""

    def __init__(self, entry, name, controller, program, start_index, coordinator):
        """Set up a new OpenSprinkler program time for program start time."""
        self._controller = controller
        self._program = program
        self._start_index = start_index
        self._entity_type = "time"
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this time."""
        start = str(self._start_index) if self._start_index > 0 else ""
        return f"{self._program.name} Start{start} Time"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        start = str(self._start_index) if self._start_index > 0 else ""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_start{start}_time_{self._program.index}"
        )

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Set all but start0 entity disabled by default."""
        return False if self._start_index > 0 else True

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:clock-start"

    @property
    def native_value(self) -> time:
        """The value of the time."""
        minutes = self._program.get_program_start_time_offset(self._start_index)
        offset_type = self._program.get_program_start_time_offset_type(
            self._start_index
        )

        if offset_type == START_TIME_SUNRISE:
            minutes += self._controller.sunrise
        elif offset_type == START_TIME_SUNSET:
            minutes += self._controller.sunset

        return datetime.time(trunc(minutes / 60), minutes % 60, 0)

    async def async_set_value(self, value: time) -> None:
        """Update the current value."""
        minutes = value.hour * 60 + value.minute
        await self._program.set_program_start_time_offset_type(
            self._start_index, START_TIME_MIDNIGHT
        )
        await self._program.set_program_start_time_offset(self._start_index, minutes)
        await self._coordinator.async_request_refresh()
