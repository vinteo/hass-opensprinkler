"""Component providing support for OpenSprinkler text entities."""

import logging
from typing import Callable

from homeassistant.components.text import TextEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from . import OpenSprinklerProgramEntity, OpenSprinklerText
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: dict,
    async_add_entities: Callable,
):
    """Set up the OpenSprinkler texts."""
    entities = _create_entities(hass, entry)
    async_add_entities(entities)


def _create_entities(hass: HomeAssistant, entry: dict):
    entities = []

    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name = entry.data[CONF_NAME]

    for _, program in controller.programs.items():
        entities.append(ProgramNameText(entry, name, program, coordinator))

    return entities


class ProgramNameText(OpenSprinklerProgramEntity, OpenSprinklerText, TextEntity):
    """Represent text for the name of a program."""

    def __init__(self, entry, name, program, coordinator):
        """Set up a new OpenSprinkler program text."""
        self._program = program
        self._entity_type = "text"
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of this sensor."""
        return f"{self._program.name} Program Name"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return slugify(
            f"{self._entry.unique_id}_{self._entity_type}_program_name_{self._program.index}"
        )

    @property
    def mode(self) -> str:
        """Defines how the text should be displayed in the UI. Can be text or password."""
        return "text"

    @property
    def native_max(self) -> int:
        """The maximum number of characters in the text value (inclusive)."""
        return 32

    @property
    def native_min(self) -> int:
        """The minimum number of characters in the text value (inclusive)."""
        return 1

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:rename"

    @property
    def native_value(self) -> str:
        """The value of the text."""
        return self._program.name

    async def async_set_value(self, value: str) -> None:
        """Set the text value."""
        await self._program.set_name(value)
        await self._coordinator.async_request_refresh()
