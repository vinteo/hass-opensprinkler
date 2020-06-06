[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
![](https://github.com/vinteo/hass-opensprinkler/workflows/HACS/badge.svg)
![](https://github.com/vinteo/hass-opensprinkler/workflows/hassfest/badge.svg)
![](https://github.com/vinteo/hass-opensprinkler/workflows/Linting/badge.svg)

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

Available services are `opensprinkler.run` for programs, stations and controllers (for running once program), and `opensprinkler.stop` for stations or controller (to stop all stations).

### Run Examples

#### Run Program Example

```yaml
service: opensprinkler.run
data:
  entity_id: switch.program_name # Switches or sensors for programs
```

#### Run Station Example

```yaml
service: opensprinkler.run
data:
  entity_id: switch.station_name # Switches or sensors for stations
  run_seconds: 60 # Seconds to run (optional, defaults to 60 seconds)
```

#### Run Once Program Example

To run an once program, the run seconds can either be a list of seconds per station or a list of index and second pairs.
The following two examples are equivalent.

```yaml
service: opensprinkler.run
data:
  entity_id: switch.controller_name # Switches or sensors for controller
  run_seconds: # Seconds to run for each station (required)
    - 60
    - 0
    - 30
```

```yaml
service: opensprinkler.run
data:
  entity_id: switch.controller_name # Switches or sensors for controller
  run_seconds: # Station and index and seconds pairs (required)
    - index: 0
      run_seconds: 60
    - index: 2
      run_seconds: 30
```

### Stop Examples

#### Stop Station Example

```yaml
service: opensprinkler.stop
data:
  entity_id: switch.station_name # Switches or sensors for stations
```

#### Stop All Stations Example

```yaml
service: opensprinkler.stop
data:
  entity_id: switch.controller_name # Switches or sensors for controller
```

## Creating a Station Switch

If you wish to have a switch for your stations, here is an example using the switch template and input number.
Add the following to your YAML configuration (`configuration.yaml`).

```yaml
switch:
  - platform: template
    switches:
      fruits_station:
        value_template: "{{ is_state('binary_sensor.s01_station_running', 'on') }}"
        turn_on:
          service: opensprinkler.run
          data_template:
            entity_id: binary_sensor.s01_station_running
            # Run seconds uses the input_number below.
            run_seconds: "{{ ((states('input_number.s01_station_minutes') | float) * 60) | int }}"
        turn_off:
          service: opensprinkler.stop
          data:
            entity_id: binary_sensor.s01_station_running
​
input_number:
  s01_station_minutes:
    initial: 1
    min: 1
    max: 10
    step: 1
```
