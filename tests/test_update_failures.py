"""Tests for transient OpenSprinkler update failures."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from aiohttp.client_exceptions import InvalidURL
from homeassistant.helpers.update_coordinator import (
    ConfigEntryAuthFailed,
    UpdateFailed,
)
from opensprinkler import (
    MAX_CONSECUTIVE_UPDATE_FAILURES,
    OpenSprinklerDataUpdater,
)
from pyopensprinkler import OpenSprinklerAuthError, OpenSprinklerConnectionError


class MockController:
    """Mock OpenSprinkler controller."""

    def __init__(self, state=None):
        self._state = state
        self.refresh = AsyncMock()


@pytest.mark.asyncio
async def test_successful_update_returns_current_state():
    """A successful refresh returns the current controller state."""
    state = {"status": "current"}
    controller = MockController(state)
    updater = OpenSprinklerDataUpdater(controller)

    assert await updater.async_update_data() is state


@pytest.mark.asyncio
async def test_timeout_without_cached_state_fails_immediately():
    """The initial refresh must not hide a timeout when no state exists."""
    controller = MockController()
    controller.refresh.side_effect = asyncio.TimeoutError
    updater = OpenSprinklerDataUpdater(controller)

    with pytest.raises(asyncio.TimeoutError):
        await updater.async_update_data()


@pytest.mark.asyncio
async def test_cached_state_is_used_until_third_consecutive_timeout():
    """Two timeouts keep cached data available and the third is propagated."""
    state = {"status": "cached"}
    controller = MockController(state)
    controller.refresh.side_effect = asyncio.TimeoutError
    updater = OpenSprinklerDataUpdater(controller)

    for _ in range(MAX_CONSECUTIVE_UPDATE_FAILURES - 1):
        assert await updater.async_update_data() is state

    with pytest.raises(asyncio.TimeoutError):
        await updater.async_update_data()


@pytest.mark.asyncio
async def test_successful_update_resets_failure_counter():
    """A success makes the next transient timeout the first failure again."""
    state = {"status": "cached"}
    controller = MockController(state)
    controller.refresh.side_effect = [asyncio.TimeoutError, None, asyncio.TimeoutError]
    updater = OpenSprinklerDataUpdater(controller)

    assert await updater.async_update_data() is state
    assert await updater.async_update_data() is state
    assert await updater.async_update_data() is state


@pytest.mark.asyncio
async def test_connection_errors_use_same_failure_threshold():
    """Transient connection errors also keep cached data for two attempts."""
    state = {"status": "cached"}
    controller = MockController(state)
    controller.refresh.side_effect = OpenSprinklerConnectionError(
        "Cannot connect to controller"
    )
    updater = OpenSprinklerDataUpdater(controller)

    for _ in range(MAX_CONSECUTIVE_UPDATE_FAILURES - 1):
        assert await updater.async_update_data() is state

    with pytest.raises(UpdateFailed):
        await updater.async_update_data()


@pytest.mark.asyncio
async def test_authentication_error_is_never_suppressed():
    """Authentication errors trigger reauthentication even with cached state."""
    controller = MockController({"status": "cached"})
    controller.refresh.side_effect = OpenSprinklerAuthError("Invalid password")
    updater = OpenSprinklerDataUpdater(controller)

    with pytest.raises(ConfigEntryAuthFailed):
        await updater.async_update_data()


@pytest.mark.asyncio
async def test_invalid_url_is_never_suppressed():
    """Configuration errors are reported immediately."""
    controller = MockController({"status": "cached"})
    controller.refresh.side_effect = InvalidURL("Invalid URL")
    updater = OpenSprinklerDataUpdater(controller)

    with pytest.raises(UpdateFailed):
        await updater.async_update_data()
