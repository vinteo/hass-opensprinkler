"""Tests for uwt, qo, and ssta parameter support."""

from unittest.mock import AsyncMock, call

import pytest


class MockStation:
    """Mock station for testing."""

    def __init__(self, index):
        self.index = index
        self.seconds_remaining = 0


class MockController:
    """Mock controller for testing."""

    def __init__(self, num_stations=3):
        self.stations = {i: MockStation(i) for i in range(num_stations)}
        self.run_once_program = AsyncMock()

    async def refresh(self):
        pass


class MockStationAPI:
    """Mock station API for testing."""

    def __init__(self):
        self.run = AsyncMock()
        self.stop = AsyncMock()


class MockProgramAPI:
    """Mock program API for testing."""

    def __init__(self):
        self.run = AsyncMock()


class MockCoordinator:
    """Mock coordinator for testing."""

    async def async_request_refresh(self):
        pass


def make_controller_entity(controller, coordinator):
    import sys

    sys.path.insert(0, "custom_components")
    from opensprinkler import OpenSprinklerControllerEntity

    class TestEntity(OpenSprinklerControllerEntity):
        def __init__(self, controller, coordinator):
            self._controller = controller
            self._coordinator = coordinator

    return TestEntity(controller, coordinator)


def make_program_entity(program, coordinator):
    import sys

    sys.path.insert(0, "custom_components")
    from opensprinkler import OpenSprinklerProgramEntity

    class TestEntity(OpenSprinklerProgramEntity):
        def __init__(self, program, coordinator):
            self._program = program
            self._coordinator = coordinator

    return TestEntity(program, coordinator)


def make_station_entity(station, coordinator):
    import sys

    sys.path.insert(0, "custom_components")
    from opensprinkler import OpenSprinklerStationEntity

    class TestEntity(OpenSprinklerStationEntity):
        def __init__(self, station, coordinator):
            self._station = station
            self._coordinator = coordinator

    return TestEntity(station, coordinator)


class TestRunOnceQueueOption:
    @pytest.mark.asyncio
    async def test_run_once_no_queue_option_passes_no_kwarg(self):
        controller = MockController()
        entity = make_controller_entity(controller, MockCoordinator())
        await entity.run_once(run_seconds=[60, 0, 30])
        controller.run_once_program.assert_called_once_with([60, 0, 30])

    @pytest.mark.asyncio
    async def test_run_once_append(self):
        controller = MockController()
        entity = make_controller_entity(controller, MockCoordinator())
        await entity.run_once(run_seconds=[60, 0, 30], queue_option="append")
        controller.run_once_program.assert_called_once_with([60, 0, 30], qo=0)

    @pytest.mark.asyncio
    async def test_run_once_preempt(self):
        controller = MockController()
        entity = make_controller_entity(controller, MockCoordinator())
        await entity.run_once(run_seconds=[60, 0, 30], queue_option="preempt")
        controller.run_once_program.assert_called_once_with([60, 0, 30], qo=1)

    @pytest.mark.asyncio
    async def test_run_once_replace(self):
        controller = MockController()
        entity = make_controller_entity(controller, MockCoordinator())
        await entity.run_once(run_seconds=[60, 0, 30], queue_option="replace")
        controller.run_once_program.assert_called_once_with([60, 0, 30], qo=2)

    @pytest.mark.asyncio
    async def test_run_once_use_weather_adjustment_true(self):
        controller = MockController()
        entity = make_controller_entity(controller, MockCoordinator())
        await entity.run_once(run_seconds=[60, 0, 30], use_weather_adjustment=True)
        controller.run_once_program.assert_called_once_with([60, 0, 30], uwt=1)

    @pytest.mark.asyncio
    async def test_run_once_use_weather_adjustment_false(self):
        controller = MockController()
        entity = make_controller_entity(controller, MockCoordinator())
        await entity.run_once(run_seconds=[60, 0, 30], use_weather_adjustment=False)
        controller.run_once_program.assert_called_once_with([60, 0, 30], uwt=0)

    @pytest.mark.asyncio
    async def test_run_once_all_params(self):
        controller = MockController()
        entity = make_controller_entity(controller, MockCoordinator())
        await entity.run_once(
            run_seconds=[60, 0, 30],
            use_weather_adjustment=True,
            queue_option="preempt",
        )
        controller.run_once_program.assert_called_once_with(
            [60, 0, 30], uwt=1, qo=1
        )


class TestRunProgramParams:
    @pytest.mark.asyncio
    async def test_run_program_no_params(self):
        program = MockProgramAPI()
        entity = make_program_entity(program, MockCoordinator())
        await entity.run_program()
        program.run.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_run_program_use_weather_adjustment(self):
        program = MockProgramAPI()
        entity = make_program_entity(program, MockCoordinator())
        await entity.run_program(use_weather_adjustment=True)
        program.run.assert_called_once_with(uwt=1)

    @pytest.mark.asyncio
    async def test_run_program_queue_option_append(self):
        program = MockProgramAPI()
        entity = make_program_entity(program, MockCoordinator())
        await entity.run_program(queue_option="append")
        program.run.assert_called_once_with(qo=0)

    @pytest.mark.asyncio
    async def test_run_program_queue_option_replace(self):
        program = MockProgramAPI()
        entity = make_program_entity(program, MockCoordinator())
        await entity.run_program(queue_option="replace")
        program.run.assert_called_once_with(qo=2)

    @pytest.mark.asyncio
    async def test_run_program_all_params(self):
        program = MockProgramAPI()
        entity = make_program_entity(program, MockCoordinator())
        await entity.run_program(use_weather_adjustment=False, queue_option="preempt")
        program.run.assert_called_once_with(uwt=0, qo=1)


class TestRunStationQueueOption:
    @pytest.mark.asyncio
    async def test_run_station_no_queue_option(self):
        station = MockStationAPI()
        entity = make_station_entity(station, MockCoordinator())
        await entity.run_station(run_seconds=60)
        station.run.assert_called_once_with(60)

    @pytest.mark.asyncio
    async def test_run_station_append(self):
        station = MockStationAPI()
        entity = make_station_entity(station, MockCoordinator())
        await entity.run_station(run_seconds=60, queue_option="append")
        station.run.assert_called_once_with(60, qo=0)

    @pytest.mark.asyncio
    async def test_run_station_preempt(self):
        station = MockStationAPI()
        entity = make_station_entity(station, MockCoordinator())
        await entity.run_station(run_seconds=60, queue_option="preempt")
        station.run.assert_called_once_with(60, qo=1)


class TestStopShiftSequentialStations:
    @pytest.mark.asyncio
    async def test_stop_no_param(self):
        station = MockStationAPI()
        entity = make_station_entity(station, MockCoordinator())
        await entity.stop()
        station.stop.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_stop_shift_true(self):
        station = MockStationAPI()
        entity = make_station_entity(station, MockCoordinator())
        await entity.stop(shift_sequential_stations=True)
        station.stop.assert_called_once_with(ssta=1)

    @pytest.mark.asyncio
    async def test_stop_shift_false(self):
        station = MockStationAPI()
        entity = make_station_entity(station, MockCoordinator())
        await entity.stop(shift_sequential_stations=False)
        station.stop.assert_called_once_with(ssta=0)
