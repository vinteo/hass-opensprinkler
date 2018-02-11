from custom_components.opensprinkler import CONF_CONFIG, CONF_PROGRAMS, DOMAIN
from homeassistant.components.scene import Scene
from homeassistant.util import slugify

def setup_platform(hass, config, add_devices, discovery_info=None):
  opensprinkler = hass.data[DOMAIN][DOMAIN]
  opensprinklerConfig = hass.data[DOMAIN][CONF_CONFIG]

  programIndexes = opensprinklerConfig[CONF_PROGRAMS] or []
  scenes = []
  for program in opensprinkler.programs():
    if len(programIndexes) == 0 or (program.index in programIndexes):
      scenes.append(ProgramScene(program, hass.states))

  add_devices(scenes, True)


class ProgramScene(Scene):

  def __init__(self, program, states):
    self._states = states
    self._program = program
    self._is_on = False

  @property
  def name(self):
    """Return the name of the binary sensor."""
    return self._program.name

  @property
  def should_poll(self):
    """Return that polling is not necessary."""
    return False

  # def update(self):
  #   """Get the latest data """
  #   self._is_on = self._station.status()

  def activate(self, **kwargs):
    """Turn the device on."""
    # mins = self._states.get('input_number.{}_timer'.format(slugify(self._station.name)))
    # self._program.turn_on(int(mins.state))
    self._program.activate()
    # self._is_on = 1
    # self.schedule_update_ha_state()

  # def turn_off(self, **kwargs):
  #   """Turn the device off."""
  #   self._station.turn_off()
  #   self._is_on = 0
  #   self.schedule_update_ha_state()
