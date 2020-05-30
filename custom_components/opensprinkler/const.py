"""Define constants for the OpenSprinkler component."""

from datetime import timedelta

CONF_RUN_SECONDS = "run_seconds"

DOMAIN = "opensprinkler"

DEFAULT_NAME = "OpenSprinkler"
DEFAULT_PORT = 8080

SCAN_INTERVAL = timedelta(seconds=5)

SERVICE_RUN = "run"
SERVICE_STOP = "stop"
