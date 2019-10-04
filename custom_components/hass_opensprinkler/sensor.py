import pytz

from custom_components.hass_opensprinkler import CONF_CONFIG, CONF_STATIONS, DOMAIN
from datetime import datetime, timedelta
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity

SCAN_INTERVAL = timedelta(seconds=5)
utc_tz = pytz.timezone('UTC')


def setup_platform(hass, config, add_devices, discovery_info=None):
    opensprinkler = hass.data[DOMAIN][DOMAIN]
    opensprinklerConfig = hass.data[DOMAIN][CONF_CONFIG]

    stationIndexes = opensprinklerConfig[CONF_STATIONS] or []
    sensors = []
    for station in opensprinkler.stations():
        if len(stationIndexes) == 0 or (station.index in stationIndexes):
            sensors.append(StationSensor(station))

    sensors.append(WaterLevelSensor(opensprinkler))
    sensors.append(LastRunSensor(opensprinkler))
    sensors.append(RainDelayStopTimeSensor(opensprinkler))

    add_devices(sensors, True)


class StationSensor(Entity):

    def __init__(self, station):
        self._station = station
        self._state = None
        self._status = None
        self._p_status = None

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return self._station.name

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return None

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @Throttle(SCAN_INTERVAL)
    def update(self):
        """Fetch new state data for the sensor."""
        self._status = self._station.status()
        self._p_status = self._station.p_status()

        if(self._status == 1):
            if(self._p_status[0] == 99):
                self._state = "Running manual"
            elif(self._p_status[0] == 254):
                self._state = "Running once prog."
            elif(self._p_status[0] == 0):
                self._state = "Idle"
            else:
                self._state = "Running schedule"
        else:
            if(self._p_status[0] > 0):
                self._state = "Waiting for run"
            else:
                self._state = "Idle"


class WaterLevelSensor(Entity):

    def __init__(self, opensprinkler):
        self._opensprinkler = opensprinkler
        self._state = None

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return "Water Level"

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return "%"

    @property
    def icon(self):
        """Return icon."""
        return "mdi:water"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @Throttle(SCAN_INTERVAL)
    def update(self):
        """Fetch new state data for the sensor."""
        self._state = self._opensprinkler.water_level()


class LastRunSensor(Entity):

    def __init__(self, opensprinkler):
        self._opensprinkler = opensprinkler
        self._state = None
        self._last_run = None

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return "Last Run"

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return None

    @property
    def icon(self):
        """Return icon."""
        return "mdi:history"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @Throttle(SCAN_INTERVAL)
    def update(self):
        """Fetch new state data for the sensor."""
        self._last_run = self._opensprinkler.last_run()
        utcTime = datetime.fromtimestamp(self._last_run[3], utc_tz)
        self._state = utcTime.strftime("%d/%m %H:%M")


class RainDelayStopTimeSensor(Entity):

    def __init__(self, opensprinkler):
        self._opensprinkler = opensprinkler
        self._state = None
        self._rain_delay_stop_time = None

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return "Rain Delay Stop Time"

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return None

    @property
    def icon(self):
        """Return icon."""
        return "mdi:weather-rainy"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @Throttle(SCAN_INTERVAL)
    def update(self):
        """Fetch new state data for the sensor."""
        self._rain_delay_stop_time = self._opensprinkler.rain_delay_stop_time()
        if self._rain_delay_stop_time == 0:
            self._state = 'Not in effect'
        else:
            utcTime = datetime.fromtimestamp(self._rain_delay_stop_time, utc_tz)
            self._state = utcTime.strftime("%d/%m %H:%M")
