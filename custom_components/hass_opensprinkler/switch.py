from custom_components.hass_opensprinkler import CONF_CONFIG, CONF_STATIONS, DOMAIN
from datetime import timedelta
from homeassistant.components.switch import SwitchDevice
from homeassistant.util import Throttle
from homeassistant.util import slugify

SCAN_INTERVAL = timedelta(seconds=5)


def setup_platform(hass, config, add_devices, discovery_info=None):
    opensprinkler = hass.data[DOMAIN][DOMAIN]
    opensprinklerConfig = hass.data[DOMAIN][CONF_CONFIG]

    switches = []
    switches.append(ControllerSwitch(opensprinkler))

    stationIndexes = opensprinklerConfig[CONF_STATIONS] or []
    for station in opensprinkler.stations():
        if len(stationIndexes) == 0 or (station.index in stationIndexes):
            switches.append(StationSwitch(station, hass.states))

    add_devices(switches, True)


class ControllerSwitch(SwitchDevice):

    def __init__(self, controller):
        self._controller = controller
        self._is_on = False

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return 'OpenSprinkler Operation'

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return bool(self._is_on)

    @Throttle(SCAN_INTERVAL)
    def update(self):
        """Get the latest data """
        self._is_on = self._controller.enable_operation()

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self._controller._set_controller_variable('en', '1')
        self._is_on = 1
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._controller._set_controller_variable('en', '0')
        self._is_on = 0
        self.schedule_update_ha_state()


class StationSwitch(SwitchDevice):

    def __init__(self, station, states):
        self._states = states
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

    def turn_on(self, **kwargs):
        """Turn the device on."""
        mins = self._states.get('input_number.{}_timer'.format(slugify(self._station.name)))
        self._station.turn_on(int(float(mins.state)))
        self._is_on = 1
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._station.turn_off()
        self._is_on = 0
        self.schedule_update_ha_state()
