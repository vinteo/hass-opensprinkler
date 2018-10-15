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