"""Define constants for the OpenSprinkler component."""

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

CONF_INDEX = "index"
CONF_RUN_SECONDS = "run_seconds"
CONF_CONTINUE_RUNNING_STATIONS = "continue_running_stations"
CONF_WATER_LEVEL = "water_level"
CONF_RAIN_DELAY = "rain_delay"
CONF_PAUSE_SECONDS = "pause_duration"

DOMAIN = "opensprinkler"

DEFAULT_NAME = "OpenSprinkler"
DEFAULT_VERIFY_SSL = True

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

SCHEMA_SERVICE_RUN_ONCE = {
    vol.Required(CONF_RUN_SECONDS): vol.Or(
        cv.ensure_list(cv.positive_int),
        cv.ensure_list(SCHEMA_SERVICE_RUN_SECONDS),
        vol.Schema({}, extra=vol.ALLOW_EXTRA),
    ),
    vol.Optional(CONF_CONTINUE_RUNNING_STATIONS): cv.boolean,
}

SCHEMA_SERVICE_RUN_PROGRAM = {}

SCHEMA_SERVICE_RUN_STATION = {vol.Optional(CONF_RUN_SECONDS): cv.positive_int}

SCHEMA_SERVICE_STOP = {}

SCHEMA_SERVICE_SET_RAIN_DELAY = {
    vol.Required(CONF_RAIN_DELAY): vol.All(
        vol.Coerce(int), vol.Range(min=0, max=32767)
    ),
}

SCHEMA_SERVICE_SET_WATER_LEVEL = {
    vol.Required(CONF_WATER_LEVEL): vol.All(vol.Coerce(int), vol.Range(min=0, max=250)),
}

SCHEMA_SERVICE_PAUSE_STATIONS = {
    vol.Required(CONF_PAUSE_SECONDS): vol.All(
        vol.Coerce(int), vol.Range(min=0, max=86400)
    ),
}

SCHEMA_SERVICE_REBOOT = {}

SERVICE_RUN = "run"
SERVICE_RUN_ONCE = "run_once"
SERVICE_RUN_PROGRAM = "run_program"
SERVICE_RUN_STATION = "run_station"
SERVICE_STOP = "stop"
SERVICE_SET_WATER_LEVEL = "set_water_level"
SERVICE_REBOOT = "reboot"
SERVICE_SET_RAIN_DELAY = "set_rain_delay"
SERVICE_PAUSE_STATIONS = "pause_stations"

START_TIME_DISABLED = "disabled"
START_TIME_MIDNIGHT = "midnight"
START_TIME_SUNRISE = "sunrise"
START_TIME_SUNSET = "sunset"
