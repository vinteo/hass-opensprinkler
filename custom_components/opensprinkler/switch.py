from typing import Callable

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify
from homeassistant.util.dt import utc_from_timestamp

from . import (
    OpenSprinklerBinarySensor,
    OpenSprinklerControllerEntity,
    OpenSprinklerProgramEntity,
    OpenSprinklerStationEntity,
)
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: dict,
    async_add_entities: Callable,
):
    """Set up the OpenSprinkler switches."""
    entities = _create_entities(hass, entry)
    async_add_entities(entities)


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


class ControllerOperationSwitch(
    OpenSprinklerControllerEntity, OpenSprinklerBinarySensor, SwitchEntity
):
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

    @property
    def device_state_attributes(self):
        controller = self._controller
        attributes = {"opensprinkler_type": "controller"}
        for attr in [
            "last_reboot_cause",
            "last_reboot_cause_name",
        ]:
            try:
                attributes[attr] = getattr(controller, attr)
            except:  # noqa: E722
                pass

        for attr in [
            "last_reboot_time",
        ]:
            timestamp = getattr(controller, attr)
            if not timestamp:
                attributes[attr] = None
            else:
                attributes[attr] = utc_from_timestamp(timestamp).isoformat()

        return attributes

    def _get_state(self) -> str:
        """Retrieve latest state."""
        return bool(self._controller.enabled)

    async def async_turn_on(self, **kwargs):
        """Enable the controller operation."""
        await self._controller.enable()
        await self._coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Disable the device operation."""
        await self._controller.disable()
        await self._coordinator.async_request_refresh()


class ProgramEnabledSwitch(
    OpenSprinklerProgramEntity, OpenSprinklerBinarySensor, SwitchEntity
):
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

    async def async_turn_on(self, **kwargs):
        """Enable the program."""
        await self._program.enable()
        await self._coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Disable the program."""
        await self._program.disable()
        await self._coordinator.async_request_refresh()


class StationEnabledSwitch(
    OpenSprinklerStationEntity, OpenSprinklerBinarySensor, SwitchEntity
):
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

    async def async_turn_on(self, **kwargs):
        """Enable the station."""
        await self._station.enable()
        await self._coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Disable the station."""
        await self._station.disable()
        await self._coordinator.async_request_refresh()
