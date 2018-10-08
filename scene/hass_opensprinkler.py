from custom_components.hass_opensprinkler import CONF_CONFIG, CONF_PROGRAMS, DOMAIN
from homeassistant.components.scene import Scene

def setup_platform(hass, config, add_devices, discovery_info=None):
  opensprinkler = hass.data[DOMAIN][DOMAIN]
  opensprinklerConfig = hass.data[DOMAIN][CONF_CONFIG]

  programIndexes = opensprinklerConfig[CONF_PROGRAMS] or []
  scenes = []
  for program in opensprinkler.programs():
    if len(programIndexes) == 0 or (program.index in programIndexes):
      scenes.append(ProgramScene(program))

  add_devices(scenes, True)


class ProgramScene(Scene):

  def __init__(self, program):
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

  def activate(self, **kwargs):
    """Turn the program on."""
    self._program.activate()
