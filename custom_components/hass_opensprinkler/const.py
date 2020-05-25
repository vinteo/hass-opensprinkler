"""Define constants for the OpenSprinkler component."""

from datetime import timedelta

DOMAIN = "hass_opensprinkler"

DEFAULT_NAME = "OpenSprinkler"
DEFAULT_PORT = 8080

SCAN_INTERVAL = timedelta(seconds=5)
