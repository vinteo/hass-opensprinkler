import logging
import requests
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components.input_number import InputNumber
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.util import slugify

DOMAIN = 'opensprinkler'

CONF_STATIONS = 'stations'
CONF_CONFIG = 'config'

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
  DOMAIN: vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_STATIONS, default=[]):
      vol.All(cv.ensure_list, [vol.Coerce(int)]),
  })
}, extra=vol.ALLOW_EXTRA)

def setup(hass, config):
  host = config[DOMAIN].get(CONF_HOST)
  password = config[DOMAIN].get(CONF_PASSWORD)
  opensprinkler = Opensprinkler(host, password)
  stationIndexes = config[DOMAIN].get(CONF_STATIONS)

  hass.data[DOMAIN] = {
    DOMAIN: opensprinkler,
    CONF_CONFIG: {
      CONF_STATIONS: stationIndexes,
    },
  }

  component = EntityComponent(_LOGGER, 'input_number', hass)
  entities = []
  for station in opensprinkler.stations():
    if len(stationIndexes) == 0 or (station.index in stationIndexes):
      object_id = '{}_timer'.format(slugify(station.name))
      name = station.name
      minimum = 1
      maximum = 10
      initial = 1
      step = 1
      unit = 'minutes'

      inputNumber = InputNumber(object_id, name, initial, minimum, maximum, step, None, unit, 'slider')
      entities.append(inputNumber)

  component.add_entities(entities)

  load_platform(hass, 'binary_sensor', DOMAIN)
  load_platform(hass, 'switch', DOMAIN)

  return True


class Opensprinkler(object):

  def __init__(self, host, password):
    self._host = host
    self._password = password
    self.data = {}

  def stations(self):
    try:
      url = 'http://{}/jn?pw={}'.format(self._host, self._password)
      response = requests.get(url, timeout=10)
    except requests.exceptions.ConnectionError:
      _LOGGER.error("No route to device '%s'", self._resource)

    self.data['stations'] = []

    for i, name in enumerate(response.json()['snames']):
      self.data['stations'].append(OpensprinklerStation(self._host, self._password, name, i))

    return self.data['stations']


class OpensprinklerStation(object):

  def __init__(self, host, password, name, index):
    self._host = host
    self._password = password
    self._name = name
    self._index = index

  @property
  def name(self):
    return self._name

  @property
  def index(self):
    return self._index

  def status(self):
    try:
      url = 'http://{}/js?pw={}'.format(self._host, self._password)
      response = requests.get(url, timeout=10)
    except requests.exceptions.ConnectionError:
      _LOGGER.error("No route to device '%s'", self._resource)

    return response.json()['sn'][self._index]

  def turn_on(self, minutes):
    try:
      url = 'http://{}/cm?pw={}&sid={}&en=1&t={}'.format(self._host, self._password, self._index, minutes * 60)
      response = requests.get(url, timeout=10)
    except requests.exceptions.ConnectionError:
      _LOGGER.error("No route to device '%s'", self._resource)

  def turn_off(self):
    try:
      url = 'http://{}/cm?pw={}&sid={}&en=0'.format(self._host, self._password, self._index)
      response = requests.get(url, timeout=10)
    except requests.exceptions.ConnectionError:
      _LOGGER.error("No route to device '%s'", self._resource)
