import logging
import requests
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.setup import setup_component
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.util import slugify

DOMAIN = 'hass_opensprinkler'

CONF_STATIONS = 'stations'
CONF_PROGRAMS = 'programs'
CONF_WATER_LEVEL = 'water_level'
CONF_LAST_RUN = 'last_run'
CONF_CONFIG = 'config'

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
  DOMAIN: vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_STATIONS, default=[]):
      vol.All(cv.ensure_list, [vol.Coerce(int)]),
    vol.Optional(CONF_PROGRAMS, default=[]):
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
      CONF_PROGRAMS: config[DOMAIN].get(CONF_PROGRAMS),
    },
  }

  component = EntityComponent(_LOGGER, 'input_number', hass)
  inputNumberConfig = {'input_number': {}}
  for station in opensprinkler.stations():
    if len(stationIndexes) == 0 or (station.index in stationIndexes):
      object_id = '{}_timer'.format(slugify(station.name))
      name = station.name
      minimum = 1
      maximum = 10
      initial = 1
      step = 1
      unit = 'minutes'

      inputNumberConfig['input_number'][object_id] = {
        'min': minimum,
        'max': maximum,
        'name': name,
        'step': step,
        'initial': 1,
        'unit_of_measurement': unit,
      }

  setup_component(hass, 'input_number', inputNumberConfig)

  load_platform(hass, 'binary_sensor', DOMAIN, {}, config)
  load_platform(hass, 'sensor', DOMAIN, {}, config)
  load_platform(hass, 'scene', DOMAIN, {}, config)
  load_platform(hass, 'switch', DOMAIN, {}, config)

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

    self.data[CONF_STATIONS] = []

    for i, name in enumerate(response.json()['snames']):
      self.data[CONF_STATIONS].append(OpensprinklerStation(self._host, self._password, name, i))

    return self.data[CONF_STATIONS]

  def programs(self):
    try:
      url = 'http://{}/jp?pw={}'.format(self._host, self._password)
      response = requests.get(url, timeout=10)
    except requests.exceptions.ConnectionError:
      _LOGGER.error("No route to device '%s'", self._resource)

    self.data[CONF_PROGRAMS] = []

    for i, data in enumerate(response.json()['pd']):
      self.data[CONF_PROGRAMS].append(OpensprinklerProgram(self._host, self._password, data[5], i))

    return self.data[CONF_PROGRAMS]

  def water_level(self):
    try:
      url = 'http://{}/jo?pw={}'.format(self._host, self._password)
      response = requests.get(url, timeout=10)
    except requests.exceptions.ConnectionError:
      _LOGGER.error("No route to device '%s'", self._resource)

    self.data[CONF_WATER_LEVEL] = response.json()['wl']

    return self.data[CONF_WATER_LEVEL]

  def last_run(self):
    try:
      url = 'http://{}/jc?pw={}'.format(self._host, self._password)
      response = requests.get(url, timeout=10)
    except requests.exceptions.ConnectionError:
      _LOGGER.error("No route to device '%s'", self._resource)

    self.data[CONF_LAST_RUN] = response.json()['lrun']

    return self.data[CONF_LAST_RUN]


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

  def p_status(self):
    try:
      url = 'http://{}/jc?pw={}'.format(self._host, self._password)
      response = requests.get(url, timeout=10)
    except requests.exceptions.ConnectionError:
      _LOGGER.error("No route to device '%s'", self._resource)

    return response.json()['ps'][self._index]

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


class OpensprinklerProgram(object):

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

  def activate(self):
    try:
      url = 'http://{}/mp?pw={}&pid={}&uwt=0'.format(self._host, self._password, self._index)
      response = requests.get(url, timeout=10)
    except requests.exceptions.ConnectionError:
      _LOGGER.error("No route to device '%s'", self._resource)