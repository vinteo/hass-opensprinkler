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
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
)

from .const import DEFAULT_NAME, DEFAULT_PORT, DOMAIN  # pylint: disable=unused-import

_LOGGER = logging.getLogger(__name__)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_MAC): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_SSL, default=False): bool,
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
                host = user_input[CONF_HOST]
                password = user_input[CONF_PASSWORD]
                port = user_input.get(CONF_PORT, DEFAULT_PORT)
                ssl = user_input.get(CONF_SSL, False)
                protocol = "https" if ssl else "http"
                url = f"{protocol}://{host}:{port}"
                name = user_input.get(CONF_NAME, DEFAULT_NAME)
                controller = OpenSprinkler(url, password)
                await self.hass.async_add_executor_job(controller.refresh)
                await self.async_set_unique_id(user_input[CONF_MAC])

                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_HOST: host,
                        CONF_PASSWORD: password,
                        CONF_PORT: port,
                        CONF_NAME: name,
                        CONF_SSL: ssl,
                    },
                )
            except OpenSprinklerConnectionError:
                errors["base"] = "cannot_connect"
            except OpenSprinklerAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DEVICE_SCHEMA, errors=errors
        )

    async def async_step_import(self, user_input):
        """Handle import."""
        return await self.async_step_user(user_input)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
