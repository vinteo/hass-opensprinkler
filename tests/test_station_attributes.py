"""Tests for the station group and controller station delay attributes."""

import sys


class FirmwareNotSupportedError(Exception):
    """Stand in for the library error raised by unsupported properties."""


class MockStation:
    """Mock station for testing."""

    def __init__(self, group=0, group_supported=True):
        self.name = "Front Lawn"
        self.index = 0
        self.is_master = False
        self.running_program_id = 0
        self.start_time = 0
        self.end_time = 0
        self._group = group
        self._group_supported = group_supported

    @property
    def group(self):
        if not self._group_supported:
            raise FirmwareNotSupportedError("Feature requires firmware v2.2.0(1)")
        return self._group


class MockController:
    """Mock controller for testing."""

    def __init__(self, station_delay=0):
        self.firmware_version = 220
        self.firmware_minor_version = 1
        self.last_reboot_cause = 99
        self.last_reboot_cause_name = "Reset button"
        self.last_reboot_time = 0
        self.station_delay = station_delay


class MockCoordinator:
    """Mock coordinator for testing."""

    async def async_request_refresh(self):
        pass


def make_station_entity(station, coordinator):
    sys.path.insert(0, "custom_components")
    from opensprinkler import OpenSprinklerStationEntity

    class TestEntity(OpenSprinklerStationEntity):
        def __init__(self, station, coordinator):
            self._station = station
            self._coordinator = coordinator

    return TestEntity(station, coordinator)


def get_controller_switch_attributes(controller):
    sys.path.insert(0, "custom_components")
    from opensprinkler.switch import ControllerOperationSwitch

    class Stub:
        pass

    stub = Stub()
    stub._controller = controller

    return ControllerOperationSwitch.extra_state_attributes.fget(stub)


class TestStationGroupAttribute:
    def test_group_is_exposed(self):
        entity = make_station_entity(MockStation(group=3), MockCoordinator())
        assert entity.extra_state_attributes["group"] == 3

    def test_parallel_group_is_passed_through_unchanged(self):
        entity = make_station_entity(MockStation(group=255), MockCoordinator())
        assert entity.extra_state_attributes["group"] == 255

    def test_group_omitted_on_unsupported_firmware(self):
        """Older firmware raises, which must not take the other attributes with it."""
        entity = make_station_entity(
            MockStation(group_supported=False), MockCoordinator()
        )
        attributes = entity.extra_state_attributes
        assert "group" not in attributes
        assert attributes["index"] == 0
        assert attributes["opensprinkler_type"] == "station"

    def test_group_follows_the_station(self):
        """Read per state write, not cached at setup, so a change is picked up."""
        station = MockStation(group=0)
        entity = make_station_entity(station, MockCoordinator())
        assert entity.extra_state_attributes["group"] == 0
        station._group = 1
        assert entity.extra_state_attributes["group"] == 1


class TestControllerStationDelayAttribute:
    def test_station_delay_is_exposed(self):
        attributes = get_controller_switch_attributes(MockController(station_delay=30))
        assert attributes["station_delay"] == 30

    def test_negative_station_delay_is_passed_through(self):
        """Negative values mean stations overlap, and must not be clamped."""
        attributes = get_controller_switch_attributes(MockController(station_delay=-15))
        assert attributes["station_delay"] == -15
