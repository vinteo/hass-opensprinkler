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
CONF_ENABLE_OPERATION = 'enable_operation'
CONF_RAIN_DELAY = 'rain_delay'
CONF_RAIN_DELAY_STOP_TIME = 'rain_delay_stop_time'
CONF_RAIN_SENSOR = 'rain_sensor'
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


def call_api(url, timeout = 10)
  try:
    response = requests.get(url, timeout)
    response.encoding = response.apparent_encoding
  except requests.exceptions.ConnectionError:
    _LOGGER.error("No route to device '%s'", url)

  return response.json()


class Opensprinkler(object):
  """ API interface to OpenSprinkler

  For firmware API details, see
  https://openthings.freshdesk.com/support/solutions/articles/5000716363-os-api-documents
  """

  def __init__(self, host, password):
    self._host = host
    self._password = password
    self.data = {}

  def _get_controller_variable(self, key, variable):
    url = 'http://{}/jc?pw={}'.format(self._host, self._password)
    response = call_api(url)
    self.data[key] = response[variable]

    return self.data[key]

  def stations(self):
    url = 'http://{}/jn?pw={}'.format(self._host, self._password)
    response = call_api(url)

    self.data[CONF_STATIONS] = []

    for i, name in enumerate(response['snames']):
      self.data[CONF_STATIONS].append(OpensprinklerStation(self._host, self._password, name, i))

    return self.data[CONF_STATIONS]

  def programs(self):
    url = 'http://{}/jp?pw={}'.format(self._host, self._password)
    response = call_api(url)

    self.data[CONF_PROGRAMS] = []

    for i, data in enumerate(response['pd']):
      self.data[CONF_PROGRAMS].append(OpensprinklerProgram(self._host, self._password, data[5], i))

    return self.data[CONF_PROGRAMS]

  def water_level(self):
    url = 'http://{}/jo?pw={}'.format(self._host, self._password)
    response = call_api(url)
    self.data[CONF_WATER_LEVEL] = response['wl']

    return self.data[CONF_WATER_LEVEL]

  def last_run(self):
    return self._get_controller_variable(CONF_LAST_RUN, 'lrun')

  def enable_operation(self):
    return self._get_controller_variable(CONF_ENABLE_OPERATION, 'en')

  def rain_delay(self):
    return self._get_controller_variable(CONF_RAIN_DELAY, 'rd')

  def rain_delay_stop_time(self):
    return self._get_controller_variable(CONF_RAIN_DELAY, 'rdst')

  def rain_sensor(self):
    return self._get_controller_variable(CONF_RAIN_SENSOR, 'rs')


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
    url = 'http://{}/js?pw={}'.format(self._host, self._password)
    response = call_api(url)
    return response['sn'][self._index]

  def p_status(self):
    url = 'http://{}/jc?pw={}'.format(self._host, self._password)
    response = call_api(url)
    return response['ps'][self._index]

  def turn_on(self, minutes):
    url = 'http://{}/cm?pw={}&sid={}&en=1&t={}'.format(self._host, self._password, self._index, minutes * 60)
    call_api(url)

  def turn_off(self):
    url = 'http://{}/cm?pw={}&sid={}&en=0'.format(self._host, self._password, self._index)
    call_api(url)


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
    url = 'http://{}/mp?pw={}&pid={}&uwt=0'.format(self._host, self._password, self._index)
    call_api(url)
