"""Component providing support for OpenSprinkler number entities."""

import logging
from typing import Callable

from homeassistant.components.number import NumberEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from . import OpenSprinklerNumber, OpenSprinklerProgramEntity
from .const import DOMAIN, START_TIME_SUNRISE, START_TIME_SUNSET

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

    for _, program in controller.programs.items():
        entities.append(ProgramIntervalDaysNumber(entry, name, program, coordinator))
        entities.append(ProgramStartingInDaysNumber(entry, name, program, coordinator))
        entities.append(
            ProgramStartTimeRepeatCountNumber(entry, name, program, coordinator)
        )
        entities.append(
            ProgramStartTimeRepeatIntervalNumber(entry, name, program, coordinator)
        )
        for start_index in range(4):
            entities.append(
                ProgramStartTimeOffsetNumber(
                    entry, name, program, start_index, coordinator
                )
            )

    return entities


class ProgramDurationNumber(
    OpenSprinklerProgramEntity, OpenSprinklerNumber, NumberEntity
):
    """Represent a number for duration of a station in a program."""

    def __init__(self, entry, name, program, station, coordinator):
        """Set up a new OpenSprinkler program/station number."""
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
        """The unit of measurement that the sensor's value is expressed in."""
        return "min"

    @property
    def mode(self) -> str:
        """Defines how the number should be displayed in the UI."""
        return "auto"

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:timer-sand"

    @property
    def native_max_value(self) -> float:
        """The maximum accepted value in the number's native_unit_of_measurement."""
        return 1080.0

    @property
    def native_min_value(self) -> float:
        """The minimum accepted value in the number's native_unit_of_measurement."""
        return 0.0

    @property
    def native_value(self) -> float:
        """The value of the number in the number's native_unit_of_measurement."""
        return round(self._program.station_durations[self._station.index] / 60.0)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._program.set_station_duration(
            self._station.index, round(value * 60.0)
        )
        await self._coordinator.async_request_refresh()


class ProgramIntervalDaysNumber(
    OpenSprinklerProgramEntity, OpenSprinklerNumber, NumberEntity
):
    """Represent a number for Interval Days of a program."""

    def __init__(self, entry, name, program, coordinator):
        """Set up a new OpenSprinkler program number for Interval Days."""
        self._program = program
        self._entity_type = "number"
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this number."""
        return f"{self._program.name} Interval Days"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_interval_days_{self._program.index}"
        )

    @property
    def native_unit_of_measurement(self) -> str:
        """The unit of measurement that the sensor's value is expressed in."""
        return "d"

    @property
    def mode(self) -> str:
        """Defines how the number should be displayed in the UI."""
        return "auto"

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:calendar-expand-horizontal"

    @property
    def native_max_value(self) -> float:
        """The maximum accepted value in the number's native_unit_of_measurement."""
        return 128.0

    @property
    def native_min_value(self) -> float:
        """The minimum accepted value in the number's native_unit_of_measurement."""
        return max(1.0, self._program.starting_in_days + 1.0)

    @property
    def native_value(self) -> float:
        """The value of the number in the number's native_unit_of_measurement."""
        return self._program.interval_days

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._program.set_interval_days(round(value))
        await self._coordinator.async_request_refresh()


class ProgramStartingInDaysNumber(
    OpenSprinklerProgramEntity, OpenSprinklerNumber, NumberEntity
):
    """Represent a number for Starting In Days of a program."""

    def __init__(self, entry, name, program, coordinator):
        """Set up a new OpenSprinkler program number for Starting In Days."""
        self._program = program
        self._entity_type = "number"
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this number."""
        return f"{self._program.name} Starting In Days"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_starting_in_days_{self._program.index}"
        )

    @property
    def native_unit_of_measurement(self) -> str:
        """The unit of measurement that the sensor's value is expressed in."""
        return "d"

    @property
    def mode(self) -> str:
        """Defines how the number should be displayed in the UI."""
        return "auto"

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:calendar-start"

    @property
    def native_max_value(self) -> float:
        """The maximum accepted value in the number's native_unit_of_measurement."""
        return self._program.interval_days - 1.0

    @property
    def native_min_value(self) -> float:
        """The minimum accepted value in the number's native_unit_of_measurement."""
        return 0.0

    @property
    def native_value(self) -> float:
        """The value of the number in the number's native_unit_of_measurement."""
        return self._program.starting_in_days

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._program.set_starting_in_days(round(value))
        await self._coordinator.async_request_refresh()


class ProgramStartTimeOffsetNumber(
    OpenSprinklerProgramEntity, OpenSprinklerNumber, NumberEntity
):
    """Represent a number for Start Time Offset from sunset/sunrise in minutes of a program."""

    def __init__(self, entry, name, program, start_index, coordinator):
        """Set up a new OpenSprinkler program number for Start Time Offset."""
        self._program = program
        self._start_index = start_index
        self._entity_type = "number"
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this number."""
        start = str(self._start_index) if self._start_index > 0 else ""
        return f"{self._program.name} Start{start} Time Offset"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        start = str(self._start_index) if self._start_index > 0 else ""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_start{start}_time_offset_{self._program.index}"
        )

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Set all but start0 entity disabled by default."""
        return False if self._start_index > 0 else True

    @property
    def native_unit_of_measurement(self) -> str:
        """The unit of measurement that the sensor's value is expressed in."""
        return "min"

    @property
    def mode(self) -> str:
        """Defines how the number should be displayed in the UI."""
        return "auto"

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:clock-start"

    @property
    def native_max_value(self) -> float:
        """The maximum accepted value in the number's native_unit_of_measurement."""
        offset_type = self._program.get_program_start_time_offset_type(
            self._start_index
        )

        if offset_type in [START_TIME_SUNRISE, START_TIME_SUNSET]:
            max_value = 240.0
        else:
            max_value = 1440.0

        return max_value

    @property
    def native_min_value(self) -> float:
        """The minimum accepted value in the number's native_unit_of_measurement."""
        offset_type = self._program.get_program_start_time_offset_type(
            self._start_index
        )

        if offset_type in [START_TIME_SUNRISE, START_TIME_SUNSET]:
            min_value = -240.0
        else:
            min_value = 0.0

        return min_value

    @property
    def native_value(self) -> float:
        """The value of the number in the number's native_unit_of_measurement."""
        return self._program.get_program_start_time_offset(self._start_index)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._program.set_program_start_time_offset(self._start_index, int(value))
        await self._coordinator.async_request_refresh()


class ProgramStartTimeRepeatCountNumber(
    OpenSprinklerProgramEntity, OpenSprinklerNumber, NumberEntity
):
    """Represent a number for Start Time Repeat Count of a program."""

    def __init__(self, entry, name, program, coordinator):
        """Set up a new OpenSprinkler program number for Start Time Repeat Count."""
        self._program = program
        self._entity_type = "number"
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this number."""
        return f"{self._program.name} Start Time Repeat Count"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_start_time_repeat_count_{self._program.index}"
        )

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Set disabled by default."""
        return False

    @property
    def mode(self) -> str:
        """Defines how the number should be displayed in the UI."""
        return "auto"

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:repeat-variant"

    @property
    def native_max_value(self) -> float:
        """The maximum accepted value."""
        return 1440.0

    @property
    def native_min_value(self) -> float:
        """The minimum accepted value."""
        return 0.0

    @property
    def native_value(self) -> float:
        """The value of the number."""
        return self._program.program_start_repeat_count

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._program.set_program_start_repeat_count(int(value))
        await self._coordinator.async_request_refresh()


class ProgramStartTimeRepeatIntervalNumber(
    OpenSprinklerProgramEntity, OpenSprinklerNumber, NumberEntity
):
    """Represent a number for Start Time Repeat Interval in minutes of a program."""

    def __init__(self, entry, name, program, coordinator):
        """Set up a new OpenSprinkler program number for Start Time Repeat Interval."""
        self._program = program
        self._entity_type = "number"
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this number."""
        return f"{self._program.name} Start Time Repeat Interval"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_start_time_repeat_interval_{self._program.index}"
        )

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Set disabled by default."""
        return False

    @property
    def native_unit_of_measurement(self) -> str:
        """The unit of measurement that the sensor's value is expressed in."""
        return "min"

    @property
    def mode(self) -> str:
        """Defines how the number should be displayed in the UI."""
        return "auto"

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:clock-end"

    @property
    def native_max_value(self) -> float:
        """The maximum accepted value in the number's native_unit_of_measurement."""
        return 32767.0

    @property
    def native_min_value(self) -> float:
        """The minimum accepted value in the number's native_unit_of_measurement."""
        return 0.0

    @property
    def native_value(self) -> float:
        """The value of the number in the number's native_unit_of_measurement."""
        return self._program.program_start_repeat_interval

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._program.set_program_start_repeat_interval(int(value))
        await self._coordinator.async_request_refresh()
