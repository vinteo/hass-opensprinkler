"""Pytest configuration for hass-opensprinkler tests."""

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "custom_components"))

if importlib.util.find_spec("pytest_homeassistant_custom_component"):
    pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(scope="session", autouse=True)
def _allow_pycares_shutdown_thread():
    """Start pycares' daemon before HA teardown snapshots threads.

    Closing an aiohttp session can create Thread(_run_safe_shutdown_loop).
    If that happens mid-test, pytest-homeassistant treats it as a leak.
    """
    try:
        import pycares

        pycares._shutdown_manager.start()
    except Exception:
        pass
    yield
