"""Config flow for OpenSprinkler integration."""
import logging

from pyopensprinkler import (
    Controller as OpenSprinkler,
    OpenSprinklerAuthError,
    OpenSprinklerConnectionError,
)
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import (
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_URL,
)
from homeassistant.util import slugify

from .const import DEFAULT_NAME, DEFAULT_PORT, DOMAIN  # pylint: disable=unused-import

_LOGGER = logging.getLogger(__name__)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_PASSWORD): str,
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
                name = user_input.get(CONF_NAME, DEFAULT_NAME)
                mac_address = user_input.get(CONF_MAC)

                controller = OpenSprinkler(url, password)
                await controller.refresh()

                if controller.mac_address is None:
                    if not mac_address:
                        raise MacAddressRequiredError

                    await self.async_set_unique_id(slugify(mac_address))
                else:
                    await self.async_set_unique_id(slugify(controller.mac_address))

                await controller.session_close()

                return self.async_create_entry(
                    title=name,
                    data={CONF_URL: url, CONF_PASSWORD: password, CONF_NAME: name,},
                )
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
