from typing import Callable

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity

from . import OpenSprinklerBinarySensor
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: dict, async_add_entities: Callable,
):
    """Set up the OpenSprinkler switches."""
    entities = _create_entities(hass, entry)
    async_add_entities(entities)


def _create_entities(hass: HomeAssistant, entry: dict):
    entities = []

    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name = entry.data[CONF_NAME]

    entities.append(
        ControllerOperationSwitch(entry.entry_id, name, controller, coordinator)
    )

    for _, program in controller.programs.items():
        entities.append(
            ProgramEnabledSwitch(entry.entry_id, name, program, coordinator)
        )

    for _, station in controller.stations.items():
        entities.append(
            StationEnabledSwitch(entry.entry_id, name, station, coordinator)
        )

    return entities


class ControllerOperationSwitch(OpenSprinklerBinarySensor, SwitchEntity):
    def __init__(self, entry_id, name, controller, coordinator):
        """Set up a new OpenSprinkler controller switch."""
        self._entry_id = entry_id
        self._controller = controller
        self._entity_type = "switch"
        super().__init__(entry_id, name, coordinator)

    @property
    def name(self):
        """Return the name of controller switch."""
        return f"{self._name} Operation Enabled"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._entry_id}_{self._entity_type}_controller_operation_enabled"

    def _get_state(self) -> str:
        """Retrieve latest state."""
        return bool(self._controller.operation_enabled)

    def turn_on(self, **kwargs):
        """Enable the controller operation."""
        self._controller.enable()
        self._state = True

    def turn_off(self, **kwargs):
        """Disable the device operation."""
        self._controller.disable()
        self._state = False


class ProgramEnabledSwitch(OpenSprinklerBinarySensor, SwitchEntity):
    def __init__(self, entry_id, name, program, coordinator):
        """Set up a new OpenSprinkler program switch."""
        self._entry_id = entry_id
        self._program = program
        self._entity_type = "switch"
        super().__init__(entry_id, name, coordinator)

    @property
    def name(self):
        """Return the name of the switch."""
        return self._program.name + " Enabled"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._entry_id}_{self._entity_type}_program_enabled_{self._program.index}"

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


class StationEnabledSwitch(OpenSprinklerBinarySensor, SwitchEntity):
    def __init__(self, entry_id, name, station, coordinator):
        """Set up a new OpenSprinkler station switch."""
        self._entry_id = entry_id
        self._station = station
        self._entity_type = "switch"
        super().__init__(entry_id, name, coordinator)

    @property
    def name(self):
        """Return the name of the switch."""
        return self._station.name + " Enabled"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._entry_id}_{self._entity_type}_station_enabled_{self._station.index}"

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
