[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

# OpenSprinkler Integration for Home Assistant

Last tested on OS API `2.1.9` and Home Assistant `0.110.0`

## Features

- Binary sensors for station and programs to show running state
- Sensors for each station to show status
- Sensors for water level, last run time and rain delay stop time
- Switches for each program and station to enable/disable program or station
- Switch to enable/disable OpenSprinkler controller operation
- Services to run and stop stations
- Service to run programs

## Installation

1. Install using [HACS](https://github.com/custom-components/hacs). Or install manually by copying `custom_components/opensprinkler` folder into `<config_dir>/custom_components`
2. Restart Home Assistant.
3. In the Home Assistant UI, navigate to `Configuration` then `Integrations`. Click on the add integration button at the bottom right and select `OpenSprinkler`. Fill out the options and save.

### Upgrading from pre 1.0.0

Note: *1.0.0 has major breaking changes, you will need to update any automations, scripts, etc*

1. Remove yaml configuration.
2. Uninstall using HACS or delete the `hass_opensprinkler` folder in `<config_dir>/custom_components`
3. Restart Home Assistant
4. Follow installation instructions above

#### Breaking Changes

- Program binary sensors now show running state instead of operation state. Please use the program switch states for program operation state.
- Controller binary sensor is removed. Please use controller switch state for controller operation state.
- Station switches now enable/disable instead of run/stop stations. Please use `opensprinkler.run` and `opensprinkler.stop` services to run and stop stations.
- All scenes are removed. Please use the `opensprinkler.run` service to run programs.

## Using Services

Available services are `opensprinkler.run` for programs and stations, and `opensprinkler.stop` for stations or controller (to stop all stations).

```yaml
service: opensprinkler.run
data:
  entity_id: switch.station_name # Switches or sensors for programs or stations
  run_seconds: 60 # Seconds to run for (optional, stations only)
```

```yaml
service: opensprinkler.stop
data:
  entity_id: switch.station_name # Switches or sensors for stations or controller
```
