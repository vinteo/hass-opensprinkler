"""Define constants for the OpenSprinkler component."""
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

CONF_INDEX = "index"
CONF_RUN_SECONDS = "run_seconds"
CONF_CONTINUE_RUNNING_STATIONS = "continue_running_stations"
CONF_WATER_LEVEL = "water_level"

DOMAIN = "opensprinkler"

DEFAULT_NAME = "OpenSprinkler"

DEFAULT_SCAN_INTERVAL = 5

SCHEMA_SERVICE_RUN_SECONDS = {
    vol.Required(CONF_INDEX): cv.positive_int,
    vol.Required(CONF_RUN_SECONDS): cv.positive_int,
}
SCHEMA_SERVICE_RUN = {
    vol.Optional(CONF_RUN_SECONDS): vol.Or(
        cv.ensure_list(cv.positive_int),
        cv.ensure_list(SCHEMA_SERVICE_RUN_SECONDS),
        cv.positive_int,
        vol.Schema({}, extra=vol.ALLOW_EXTRA),
    ),
    vol.Optional(CONF_CONTINUE_RUNNING_STATIONS): cv.boolean,
}
SCHEMA_SERVICE_STOP = {}

SCHEMA_SERVICE_SET_WATER_LEVEL = {
    vol.Required(CONF_WATER_LEVEL): vol.All(vol.Coerce(int), vol.Range(min=0, max=250)),
}

SERVICE_RUN = "run"
SERVICE_STOP = "stop"
SERVICE_SET_WATER_LEVEL = "set_water_level"
