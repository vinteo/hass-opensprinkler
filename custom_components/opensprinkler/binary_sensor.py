"""OpenSprinkler integration."""

import logging
from typing import Callable

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from . import (
    OpenSprinklerBinarySensor,
    OpenSprinklerControllerEntity,
    OpenSprinklerProgramEntity,
    OpenSprinklerStationEntity,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: dict,
    async_add_entities: Callable,
):
    """Set up the OpenSprinkler binary sensors."""
    entities = _create_entities(hass, entry)
    async_add_entities(entities)


def _create_entities(hass: HomeAssistant, entry: dict):
    entities = []

    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name = entry.data[CONF_NAME]

    entities.append(
        ControllerSensorActive(entry, name, "sensor_1", controller, coordinator)
    )
    entities.append(
        ControllerSensorActive(entry, name, "sensor_2", controller, coordinator)
    )
    entities.append(
        ControllerSensorActive(entry, name, "rain_delay", controller, coordinator)
    )

    entities.append(PauseActiveBinarySensor(entry, name, controller, coordinator))

    for _, program in controller.programs.items():
        entities.append(ProgramIsRunningBinarySensor(entry, name, program, coordinator))

    for _, station in controller.stations.items():
        entities.append(StationIsRunningBinarySensor(entry, name, station, coordinator))

    return entities


class ControllerSensorActive(
    OpenSprinklerControllerEntity, OpenSprinklerBinarySensor, BinarySensorEntity
):
    """Represent a sensor that for water level."""

    def __init__(self, entry, name, sensor, controller, coordinator):
        """Set up a new opensprinkler water level sensor."""
        self._name = name
        self._controller = controller
        self._entity_type = "binary_sensor"
        self._sensor = sensor
        self._attr = sensor + "_active"
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this sensor including the controller name."""
        return f"{self._name} {self._attr.replace('_', ' ').title()}"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(f"{self._entry.unique_id}_{self._entity_type}_{self._attr}")

    @property
    def extra_state_attributes(self):
        controller = self._controller
        attributes = {}
        try:
            attributes[self._sensor + "_enabled"] = getattr(
                controller, self._sensor + "_enabled"
            )
        except:  # noqa: E722
            pass

        return attributes

    def _get_state(self) -> int:
        """Retrieve latest state."""
        return bool(getattr(self._controller, self._attr))


class ProgramIsRunningBinarySensor(
    OpenSprinklerProgramEntity, OpenSprinklerBinarySensor, BinarySensorEntity
):
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
            return "mdi:timer-outline"

        return "mdi:timer-off-outline"

    def _get_state(self) -> bool:
        """Retrieve latest state."""
        return bool(self._program.is_running)


class StationIsRunningBinarySensor(
    OpenSprinklerStationEntity, OpenSprinklerBinarySensor, BinarySensorEntity
):
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


class PauseActiveBinarySensor(
    OpenSprinklerControllerEntity, OpenSprinklerBinarySensor, BinarySensorEntity
):
    """Represent a binary_sensor for whether pause is active."""

    def __init__(self, entry, name, controller, coordinator):
        """Set up a new OpenSprinkler pause active sensor."""
        self._entity_type = "binary_sensor"
        self._controller = controller
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this sensor."""
        return f"{self._name} Paused"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(f"{self._entry.unique_id}_{self._entity_type}_paused")

    @property
    def icon(self) -> str:
        """Return icon."""
        if self._controller.pause_active:
            return "mdi:pause"
        else:
            return "mdi:play"

    def _get_state(self) -> bool:
        """Retrieve latest state."""
        return bool(self._controller.pause_active)
