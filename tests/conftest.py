"""Pytest configuration for hass-opensprinkler tests."""

import importlib.util
import sys
from pathlib import Path

import pytest

# Add custom_components to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components"))

if importlib.util.find_spec("pytest_homeassistant_custom_component"):
    pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(scope="session", autouse=True)
def allow_pycares_thread():
    """Avoid HA teardown failing on pycares' shutdown thread."""
    try:
        import pycares

        pycares._shutdown_manager.start()
    except Exception:
        pass
    yield
