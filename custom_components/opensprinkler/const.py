"""Define constants for the OpenSprinkler component."""

from datetime import timedelta

CONF_RUN_SECONDS = "run_seconds"

DOMAIN = "opensprinkler"

DEFAULT_NAME = "OpenSprinkler"
DEFAULT_PORT = 8080

SCAN_INTERVAL = timedelta(seconds=5)

SERVICE_RUN_PROGRAM = "run_program"
SERVICE_RUN_STATION = "run_station"
SERVICE_STOP_STATION = "stop_station"
