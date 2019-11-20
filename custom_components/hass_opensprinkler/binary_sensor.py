from custom_components.hass_opensprinkler import CONF_CONFIG, CONF_STATIONS, DOMAIN
from datetime import timedelta
from homeassistant.util import Throttle
from homeassistant.components.binary_sensor import BinarySensorDevice

SCAN_INTERVAL = timedelta(seconds=5)


def setup_platform(hass, config, add_devices, discovery_info=None):
    opensprinkler = hass.data[DOMAIN][DOMAIN]
    opensprinklerConfig = hass.data[DOMAIN][CONF_CONFIG]

    stationIndexes = opensprinklerConfig[CONF_STATIONS] or []
    sensors = []
    for station in opensprinkler.stations():
        if len(stationIndexes) == 0 or (station.index in stationIndexes):
            sensors.append(StationBinarySensor(station))

    fwv = opensprinkler.get_fwv()
    hwv = opensprinkler.get_hwv()
    sensors.append(OpenSprinklerBinarySensor('OpenSprinkler Operation', None, opensprinkler.enable_operation))
    if fwv >= 219:
        sensors.append(OpenSprinklerBinarySensor('Rain Sensor 1', 'moisture', opensprinkler.rain_sensor_1))
        if hwv / 30 >= 1:
            sensors.append(OpenSprinklerBinarySensor('Rain Sensor 2', 'moisture', opensprinkler.rain_sensor_2))
    else:
        sensors.append(OpenSprinklerBinarySensor('Rain Sensor', 'moisture', opensprinkler.rain_sensor))

    sensors.append(OpenSprinklerBinarySensor('Rain Delay', None, opensprinkler.rain_delay))

    add_devices(sensors, True)


class StationBinarySensor(BinarySensorDevice):

    def __init__(self, station):
        self._station = station
        self._is_on = False

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return self._station.name

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return bool(self._is_on)

    @Throttle(SCAN_INTERVAL)
    def update(self):
        """Get the latest data """
        self._is_on = self._station.status()


class OpenSprinklerBinarySensor(BinarySensorDevice):

    def __init__(self, name, device_class, sensor):
        self._name = name
        self._sensor_type = device_class
        self._sensor = sensor
        self._is_on = False

    @property
    def device_class(self):
        return self._sensor_type

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return self._name

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._is_on

    @Throttle(SCAN_INTERVAL)
    def update(self):
        """Get the latest data """
        self._is_on = bool(self._sensor())
