from typing import Callable

import voluptuous as vol

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.util import slugify

from . import OpenSprinklerBinarySensor
from .const import (
    CONF_RUN_SECONDS,
    DOMAIN,
    SERVICE_RUN,
    SERVICE_STOP,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: dict, async_add_entities: Callable,
):
    """Set up the OpenSprinkler switches."""
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

    entities.append(ControllerOperationSwitch(entry, name, controller, coordinator))

    for _, program in controller.programs.items():
        entities.append(ProgramEnabledSwitch(entry, name, program, coordinator))

    for _, station in controller.stations.items():
        entities.append(StationEnabledSwitch(entry, name, station, coordinator))

    return entities


class ControllerOperationSwitch(OpenSprinklerBinarySensor, SwitchEntity):
    def __init__(self, entry, name, controller, coordinator):
        """Set up a new OpenSprinkler controller switch."""
        self._controller = controller
        self._entity_type = "switch"
        super().__init__(entry, name, coordinator)

    @property
    def name(self):
        """Return the name of controller switch."""
        return f"{self._name} Enabled"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_controller_enabled"
        )

    @property
    def icon(self) -> str:
        """Return icon."""
        if self._controller.enabled:
            return "mdi:barley"

        return "mdi:barley-off"

    def _get_state(self) -> str:
        """Retrieve latest state."""
        return bool(self._controller.enabled)

    def turn_on(self, **kwargs):
        """Enable the controller operation."""
        self._controller.enable()
        self._state = True

    def turn_off(self, **kwargs):
        """Disable the device operation."""
        self._controller.disable()
        self._state = False


class ProgramEnabledSwitch(OpenSprinklerBinarySensor, SwitchEntity):
    def __init__(self, entry, name, program, coordinator):
        """Set up a new OpenSprinkler program switch."""
        self._program = program
        self._entity_type = "switch"
        super().__init__(entry, name, coordinator)

    @property
    def name(self):
        """Return the name of the switch."""
        return self._program.name + " Program Enabled"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_program_enabled_{self._program.index}"
        )

    @property
    def icon(self) -> str:
        """Return icon."""
        if self._program.enabled:
            return "mdi:calendar-clock"

        return "mdi:calendar-remove"

    def _get_state(self) -> str:
        """Retrieve latest state."""
        return bool(self._program.enabled)

    def turn_on(self, **kwargs):
        """Enable the program."""
        self._program.enable()
        self._state = True

    def turn_off(self, **kwargs):
        """Disable the program."""
        self._program.disable()
        self._state = False

    def run(self):
        """Runs the program."""
        self._program.run()


class StationEnabledSwitch(OpenSprinklerBinarySensor, SwitchEntity):
    def __init__(self, entry, name, station, coordinator):
        """Set up a new OpenSprinkler station switch."""
        self._station = station
        self._entity_type = "switch"
        super().__init__(entry, name, coordinator)

    @property
    def name(self):
        """Return the name of the switch."""
        return self._station.name + " Station Enabled"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_station_enabled_{self._station.index}"
        )

    @property
    def icon(self) -> str:
        """Return icon."""
        if self._station.is_master:
            if self._station.enabled:
                return "mdi:water-pump"
            else:
                return "mdi:water-pump-off"

        if self._station.enabled:
            return "mdi:water"

        return "mdi:water-off"

    def _get_state(self) -> bool:
        """Retrieve latest state."""
        return bool(self._station.enabled)

    def turn_on(self, **kwargs):
        """Enable the station."""
        self._station.enable()
        self._state = True

    def turn_off(self, **kwargs):
        """Disable the station."""
        self._station.disable()
        self._state = False

    def run(self, run_seconds):
        """Run station."""
        return self._station.run(run_seconds)

    def stop(self):
        """Stop station."""
        return self._station.stop()
