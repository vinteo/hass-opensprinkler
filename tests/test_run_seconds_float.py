"""Tests for run_seconds float to int conversion (Issue #294)."""

from unittest.mock import AsyncMock

import pytest


class MockStation:
    """Mock station for testing."""

    def __init__(self, index):
        self.index = index
        self.seconds_remaining = 0


class MockController:
    """Mock controller for testing."""

    def __init__(self, num_stations=8):
        self.stations = {i: MockStation(i) for i in range(num_stations)}
        self.run_once_program = AsyncMock()

    async def refresh(self):
        pass


class MockCoordinator:
    """Mock coordinator for testing."""

    async def async_request_refresh(self):
        pass


class TestControllerRunSecondsConversion:
    """Test that float values in run_seconds are converted to int."""

    def _create_controller_entity(self, controller, coordinator):
        """Create a mock controller entity for testing."""
        # Import here to avoid import errors during collection
        import sys

        sys.path.insert(0, "custom_components")

        from opensprinkler import OpenSprinklerControllerEntity

        class TestableControllerEntity(OpenSprinklerControllerEntity):
            def __init__(self, controller, coordinator):
                self._controller = controller
                self._coordinator = coordinator

        return TestableControllerEntity(controller, coordinator)

    @pytest.mark.asyncio
    async def test_run_with_float_list_converts_to_int(self):
        """Test that a list of floats is converted to ints.

        This is the main issue from #294:
        run_seconds = [0, 480.0, 540.0] should work like [0, 480, 540]
        """
        controller = MockController(num_stations=3)
        coordinator = MockCoordinator()
        entity = self._create_controller_entity(controller, coordinator)

        # Pass float values like the issue describes
        await entity.run(run_seconds=[0, 480.0, 540.0])

        # Verify the API was called with integers
        controller.run_once_program.assert_called_once()
        call_args = controller.run_once_program.call_args[0][0]
        assert call_args == [0, 480, 540], f"Expected [0, 480, 540], got {call_args}"
        assert all(isinstance(x, int) for x in call_args), "All values should be int"

    @pytest.mark.asyncio
    async def test_run_with_float_dict_converts_to_int(self):
        """Test that dict values with floats are converted to ints."""
        controller = MockController(num_stations=3)
        coordinator = MockCoordinator()
        entity = self._create_controller_entity(controller, coordinator)

        # Pass dict with float values
        await entity.run(run_seconds={0: 0, 1: 480.0, 2: 540.0})

        controller.run_once_program.assert_called_once()
        call_args = controller.run_once_program.call_args[0][0]
        assert call_args == [0, 480, 540], f"Expected [0, 480, 540], got {call_args}"
        assert all(isinstance(x, int) for x in call_args), "All values should be int"

    @pytest.mark.asyncio
    async def test_run_with_int_list_still_works(self):
        """Test that int values still work correctly."""
        controller = MockController(num_stations=3)
        coordinator = MockCoordinator()
        entity = self._create_controller_entity(controller, coordinator)

        await entity.run(run_seconds=[0, 480, 540])

        controller.run_once_program.assert_called_once()
        call_args = controller.run_once_program.call_args[0][0]
        assert call_args == [0, 480, 540]

    @pytest.mark.asyncio
    async def test_run_with_mixed_int_float_converts_to_int(self):
        """Test that mixed int/float values are all converted to int."""
        controller = MockController(num_stations=4)
        coordinator = MockCoordinator()
        entity = self._create_controller_entity(controller, coordinator)

        await entity.run(run_seconds=[0, 480.0, 540, 600.5])

        controller.run_once_program.assert_called_once()
        call_args = controller.run_once_program.call_args[0][0]
        assert call_args == [
            0,
            480,
            540,
            600,
        ], f"Expected [0, 480, 540, 600], got {call_args}"
        assert all(isinstance(x, int) for x in call_args), "All values should be int"


class MockStationAPI:
    """Mock station API for testing."""

    def __init__(self):
        self.run = AsyncMock()

    async def stop(self):
        pass


class TestStationRunSecondsConversion:
    """Test that float values in station run_seconds are converted to int."""

    def _create_station_entity(self, station, coordinator):
        """Create a mock station entity for testing."""
        import sys

        sys.path.insert(0, "custom_components")

        from opensprinkler import OpenSprinklerStationEntity

        class TestableStationEntity(OpenSprinklerStationEntity):
            def __init__(self, station, coordinator):
                self._station = station
                self._coordinator = coordinator

        return TestableStationEntity(station, coordinator)

    @pytest.mark.asyncio
    async def test_station_run_with_float_converts_to_int(self):
        """Test that float run_seconds is converted to int for station."""
        station = MockStationAPI()
        coordinator = MockCoordinator()
        entity = self._create_station_entity(station, coordinator)

        await entity.run(run_seconds=480.0)

        station.run.assert_called_once_with(480)

    @pytest.mark.asyncio
    async def test_station_run_with_int_still_works(self):
        """Test that int run_seconds still works for station."""
        station = MockStationAPI()
        coordinator = MockCoordinator()
        entity = self._create_station_entity(station, coordinator)

        await entity.run(run_seconds=480)

        station.run.assert_called_once_with(480)

    @pytest.mark.asyncio
    async def test_station_run_with_none_passes_none(self):
        """Test that None run_seconds passes None to station."""
        station = MockStationAPI()
        coordinator = MockCoordinator()
        entity = self._create_station_entity(station, coordinator)

        await entity.run(run_seconds=None)

        station.run.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_station_run_with_invalid_type_raises(self):
        """Test that invalid type raises exception."""
        station = MockStationAPI()
        coordinator = MockCoordinator()
        entity = self._create_station_entity(station, coordinator)

        with pytest.raises(Exception, match="numeric value"):
            await entity.run(run_seconds="invalid")
