"""Component providing support for OpenSprinkler select entities."""

import logging
from typing import Callable

from homeassistant.components.select import SelectEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from . import OpenSprinklerProgramEntity, OpenSprinklerSelect
from .const import (
    DOMAIN,
    START_TIME_DISABLED,
    START_TIME_MIDNIGHT,
    START_TIME_SUNRISE,
    START_TIME_SUNSET,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: dict,
    async_add_entities: Callable,
):
    """Set up the OpenSprinkler selects."""
    entities = _create_entities(hass, entry)
    async_add_entities(entities)


def _create_entities(hass: HomeAssistant, entry: dict):
    entities = []

    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name = entry.data[CONF_NAME]

    for _, program in controller.programs.items():
        entities.append(ProgramRestrictionsSelect(entry, name, program, coordinator))
        entities.append(ProgramTypeSelect(entry, name, program, coordinator))
        entities.append(
            ProgramAdditionalStartTimeTypeSelect(entry, name, program, coordinator)
        )
        for start_index in range(4):
            entities.append(
                ProgramStartTimeOffsetTypeSelect(
                    entry, name, program, start_index, coordinator
                )
            )

    return entities


class ProgramRestrictionsSelect(
    OpenSprinklerProgramEntity, OpenSprinklerSelect, SelectEntity
):
    """Represent select for the odd/even restrictions of a program."""

    def __init__(self, entry, name, program, coordinator):
        """Set up a new OpenSprinkler program select for restrictions."""
        self._program = program
        self._entity_type = "select"
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this select."""
        return f"{self._program.name} Restrictions"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_restrictions_{self._program.index}"
        )

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:calendar-cursor"

    @property
    def options(self) -> list[str]:
        """A list of available options as strings"""
        return ["None", "Odd Days Only", "Even Days Only"]

    @property
    def current_option(self) -> str:
        """The current select option"""
        match self._program.odd_even_restriction:
            case 0:
                return "None"
            case 1:
                return "Odd Days Only"
            case 2:
                return "Even Days Only"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        match option:
            case "None":
                value = 0
            case "Odd Days Only":
                value = 1
            case "Even Days Only":
                value = 2
        await self._program.set_odd_even_restriction(value)
        await self._coordinator.async_request_refresh()


class ProgramTypeSelect(OpenSprinklerProgramEntity, OpenSprinklerSelect, SelectEntity):
    """Represent select for the type of a program."""

    def __init__(self, entry, name, program, coordinator):
        """Set up a new OpenSprinkler program select for program type."""
        self._program = program
        self._entity_type = "select"
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this select."""
        return f"{self._program.name} Type"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_type_{self._program.index}"
        )

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:calendar-range"

    @property
    def options(self) -> list[str]:
        """A list of available options as strings"""
        return ["Weekly", "Interval"]

    @property
    def current_option(self) -> str:
        """The current select option"""
        match self._program.program_schedule_type:
            case 0:
                return "Weekly"
            case 3:
                return "Interval"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        match option:
            case "Weekly":
                value = 0
            case "Interval":
                value = 3
        await self._program.set_program_schedule_type(value)
        await self._coordinator.async_request_refresh()


class ProgramAdditionalStartTimeTypeSelect(
    OpenSprinklerProgramEntity, OpenSprinklerSelect, SelectEntity
):
    """Represent select for additional start time type of a program."""

    def __init__(self, entry, name, program, coordinator):
        """Set up a new OpenSprinkler program select for start time type."""
        self._program = program
        self._entity_type = "select"
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this select."""
        return f"{self._program.name} Additional Start Time Type"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_start_time_type_{self._program.index}"
        )

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:clock-start"

    @property
    def options(self) -> list[str]:
        """A list of available options as strings"""
        return ["Repeating", "Fixed"]

    @property
    def current_option(self) -> str:
        """The current select option"""
        match self._program.start_time_type:
            case 0:
                return "Repeating"
            case 1:
                return "Fixed"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        match option:
            case "Repeating":
                value = 0
            case "Fixed":
                value = 1
        await self._program.set_start_time_type(value)
        await self._coordinator.async_request_refresh()


class ProgramStartTimeOffsetTypeSelect(
    OpenSprinklerProgramEntity, OpenSprinklerSelect, SelectEntity
):
    """Represent select for the start time offset type of a program."""

    def __init__(self, entry, name, program, start_index, coordinator):
        """Set up a new OpenSprinkler program select for start time offset type."""
        self._program = program
        self._start_index = start_index
        self._entity_type = "select"
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this select."""
        start = str(self._start_index) if self._start_index > 0 else ""
        return f"{self._program.name} Start{start} Time Offset Type"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        start = str(self._start_index) if self._start_index > 0 else ""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_start{start}_time_offset_type_{self._program.index}"
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
    def options(self) -> list[str]:
        """A list of available options as strings"""
        # start0 is never disabled directly
        if self._start_index == 0:
            return ["Midnight", "Sunset", "Sunrise"]
        else:
            return ["Disabled", "Midnight", "Sunset", "Sunrise"]

    @property
    def current_option(self) -> str:
        """The current select option"""
        offset_type = self._program.get_program_start_time_offset_type(
            self._start_index
        )

        if offset_type == START_TIME_DISABLED:
            return "Disabled"
        if offset_type == START_TIME_MIDNIGHT:
            return "Midnight"
        if offset_type == START_TIME_SUNRISE:
            return "Sunrise"
        if offset_type == START_TIME_SUNSET:
            return "Sunset"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        match option:
            case "Disabled":
                value = START_TIME_DISABLED
            case "Midnight":
                value = START_TIME_MIDNIGHT
            case "Sunrise":
                value = START_TIME_SUNRISE
            case "Sunset":
                value = START_TIME_SUNSET

        await self._program.set_program_start_time_offset_type(self._start_index, value)
        await self._coordinator.async_request_refresh()
