import logging
import requests
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.helpers.discovery import load_platform

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

  hass.data[DOMAIN] = {
    DOMAIN: Opensprinkler(host, password),
    CONF_CONFIG: {
      CONF_STATIONS: config[DOMAIN].get(CONF_STATIONS),
    },
  }

  load_platform(hass, 'binary_sensor', DOMAIN)

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
