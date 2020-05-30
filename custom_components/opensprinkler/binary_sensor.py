"""OpenSprinkler integration."""
import logging
from typing import Callable

import voluptuous as vol

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.util import slugify

from . import OpenSprinklerBinarySensor
from .const import (
    CONF_RUN_SECONDS,
    DOMAIN,
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
        SERVICE_RUN, {vol.Optional(CONF_RUN_SECONDS): cv.positive_int}, "run",
    )
    platform.async_register_entity_service(
        SERVICE_STOP, {}, "stop",
    )


def _create_entities(hass: HomeAssistant, entry: dict):
    entities = []

    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name = entry.data[CONF_NAME]

    for _, program in controller.programs.items():
        entities.append(ProgramIsRunningBinarySensor(entry, name, program, coordinator))

    for _, station in controller.stations.items():
        entities.append(StationIsRunningBinarySensor(entry, name, station, coordinator))

    return entities


class ProgramIsRunningBinarySensor(OpenSprinklerBinarySensor, BinarySensorEntity):
    """Represent a binary_sensor for is_running of a program."""

    def __init__(self, entry, name, program, coordinator):
        """Set up a new OpenSprinkler station sensor."""
        self._program = program
        self._entity_type = "binary_sensor"
        super().__init__(entry, name, coordinator)

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

    def run(self):
        """Runs the program."""
        self._program.run()


class StationIsRunningBinarySensor(OpenSprinklerBinarySensor, BinarySensorEntity):
    """Represent a binary_sensor for is_running of a station."""

    def __init__(self, entry, name, station, coordinator):
        """Set up a new OpenSprinkler station sensor."""
        self._station = station
        self._entity_type = "binary_sensor"
        super().__init__(entry, name, coordinator)

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

    def run(self, run_seconds):
        """Run station."""
        return self._station.run(run_seconds)

    def stop(self):
        """Stop station."""
        return self._station.stop()
