"""Config flow for OpenSprinkler integration."""

import logging

import voluptuous as vol
from aiohttp.client_exceptions import InvalidURL
from homeassistant import config_entries
from homeassistant.const import (
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_URL,
    CONF_VERIFY_SSL,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import slugify
from pyopensprinkler import Controller as OpenSprinkler
from pyopensprinkler import OpenSprinklerAuthError, OpenSprinklerConnectionError

from .const import DEFAULT_NAME, DEFAULT_VERIFY_SSL, DOMAIN

_LOGGER = logging.getLogger(__name__)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
        vol.Optional(CONF_MAC): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenSprinkler."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                url = user_input[CONF_URL]
                password = user_input[CONF_PASSWORD]
                verify_ssl = user_input[CONF_VERIFY_SSL]
                name = user_input.get(CONF_NAME, DEFAULT_NAME)
                mac_address = user_input.get(CONF_MAC)

                opts = {
                    "session": async_get_clientsession(self.hass),
                    "verify_ssl": verify_ssl,
                }
                controller = OpenSprinkler(url, password, opts)
                await controller.refresh()

                if controller.mac_address is None:
                    if not mac_address:
                        raise MacAddressRequiredError

                    await self.async_set_unique_id(slugify(mac_address))
                else:
                    await self.async_set_unique_id(slugify(controller.mac_address))

                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_URL: url,
                        CONF_PASSWORD: password,
                        CONF_NAME: name,
                        CONF_VERIFY_SSL: verify_ssl,
                    },
                )
            except InvalidURL:
                errors["base"] = "invalid_url"
            except OpenSprinklerConnectionError:
                errors["base"] = "cannot_connect"
            except OpenSprinklerAuthError:
                errors["base"] = "invalid_auth"
            except MacAddressRequiredError:
                errors[CONF_MAC] = "mac_address_required"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DEVICE_SCHEMA, errors=errors
        )

    async def async_step_import(self, user_input):
        """Handle import."""
        return await self.async_step_user(user_input)


class MacAddressRequiredError(Exception):
    """Error to mac address required."""
