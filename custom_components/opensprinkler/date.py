"""Component providing support for OpenSprinkler date entities."""

import logging
from datetime import date, timedelta
from typing import Callable

from homeassistant.components.date import DateEntity
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from . import OpenSprinklerDate, OpenSprinklerProgramEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: dict,
    async_add_entities: Callable,
):
    """Set up the OpenSprinkler dates."""
    entities = _create_entities(hass, entry)
    async_add_entities(entities)


def _create_entities(hass: HomeAssistant, entry: dict):
    entities = []

    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name = entry.data[CONF_NAME]

    for _, program in controller.programs.items():
        entities.append(ProgramSingleRunStartDate(entry, name, program, coordinator))
        entities.append(ProgramDateRangeFrom(entry, name, program, coordinator))
        entities.append(ProgramDateRangeTo(entry, name, program, coordinator))

    return entities


class ProgramSingleRunStartDate(
    OpenSprinklerProgramEntity, OpenSprinklerDate, DateEntity
):
    """Represent date for the start date of a Single-run program."""

    def __init__(self, entry, name, program, coordinator):
        """Set up a new OpenSprinkler program date for a Single-run program start day."""
        self._program = program
        self._entity_type = "date"
        super().__init__(entry, name, coordinator)

    @property
    def entity_category(self):
        """Return the entity category."""
        return EntityCategory.CONFIG

    @property
    def name(self) -> str:
        """Return the name of this date."""
        return f"{self._program.name} Single-run Start Date"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_single_run_start_date_{self._program.index}"
        )

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:calendar"

    @property
    def native_value(self) -> date:
        """The value of the date."""
        epoch_start = date(1970, 1, 1)
        if self._program.program_schedule_type == 1:  # Single-run program
            return epoch_start + timedelta(days=self._program.single_run_day)
        else:
            return epoch_start

    async def async_set_value(self, value: date) -> None:
        """Update the current value."""
        epoch_start = date(1970, 1, 1)
        days_since_epoch = (value - epoch_start).days
        await self._program.set_single_run_day(days_since_epoch)
        await self._coordinator.async_request_refresh()


class ProgramDateRangeFrom(OpenSprinklerProgramEntity, OpenSprinklerDate, DateEntity):
    """Represent date for the date range start date of a program."""

    def __init__(self, entry, name, program, coordinator):
        """Set up a new OpenSprinkler program date for a program date range start date."""
        self._program = program
        self._entity_type = "date"
        super().__init__(entry, name, coordinator)

    @property
    def entity_category(self):
        """Return the entity category."""
        return EntityCategory.CONFIG

    @property
    def name(self) -> str:
        """Return the name of this date."""
        return f"{self._program.name} Date Range From Date"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_date_range_from_date_{self._program.index}"
        )

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:calendar-start"

    @property
    def native_value(self) -> date:
        """The value of the date."""
        from_date = self._program.date_range_from
        return date.today().replace(month=from_date[0], day=from_date[1])

    async def async_set_value(self, value: date) -> None:
        """Update the current value."""
        await self._program.set_date_range_from(value.month, value.day)
        await self._coordinator.async_request_refresh()


class ProgramDateRangeTo(OpenSprinklerProgramEntity, OpenSprinklerDate, DateEntity):
    """Represent date for the date range end date of a program."""

    def __init__(self, entry, name, program, coordinator):
        """Set up a new OpenSprinkler program date for a program date range end date."""
        self._program = program
        self._entity_type = "date"
        super().__init__(entry, name, coordinator)

    @property
    def entity_category(self):
        """Return the entity category."""
        return EntityCategory.CONFIG

    @property
    def name(self) -> str:
        """Return the name of this date."""
        return f"{self._program.name} Date Range To Date"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_date_range_to_date_{self._program.index}"
        )

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:calendar-end"

    @property
    def native_value(self) -> date:
        """The value of the date."""
        to_date = self._program.date_range_to
        return date.today().replace(month=to_date[0], day=to_date[1])

    async def async_set_value(self, value: date) -> None:
        """Update the current value."""
        await self._program.set_date_range_to(value.month, value.day)
        await self._coordinator.async_request_refresh()
