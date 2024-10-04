# OpenSprinkler Integration for Home Assistant

![Version](https://img.shields.io/github/v/release/vinteo/hass-opensprinkler?label=version)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
![HACS Build](https://github.com/vinteo/hass-opensprinkler/workflows/HACS/badge.svg)
![HASS Build](https://github.com/vinteo/hass-opensprinkler/workflows/hassfest/badge.svg)
![Linting](https://github.com/vinteo/hass-opensprinkler/workflows/Linting/badge.svg)
[![CodeQL](https://github.com/vinteo/hass-opensprinkler/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/vinteo/hass-opensprinkler/actions/workflows/codeql-analysis.yml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=vinteo_hass-opensprinkler&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=vinteo_hass-opensprinkler)

Last tested on OS API `2.2.0` and Home Assistant `2024.2.0`

## Features

- Binary sensors for station and programs to show running state
- Sensors for each station to show status
- Sensors for water level, last runtime and rain delay stop time
- Switches for each program and station to enable/disable program or station
- Switch to enable/disable OpenSprinkler controller operation
- Actions to run and stop stations
- Action to run programs
- Actions to pause, set a rain delay, and set the water level.

To have a Lovelace card for the UI, [opensprinkler-card](https://github.com/rianadon/opensprinkler-card) can be used.

## Installation

1. Install using [HACS](https://github.com/custom-components/hacs). Or install manually by copying `custom_components/opensprinkler` folder into `<config_dir>/custom_components`
2. Restart Home Assistant.
3. In the Home Assistant UI, navigate to `Configuration` then `Integrations`. Click on the add integration button at the bottom right and select `OpenSprinkler`. Fill out the options and save.
   - URL - Should be in the form of `http://<ip or host>:<port>`. The port can be omitted unless you have changed it, as the default port for OpenSprinkler is `80`. SSL (HTTPS) is also supported.
   - Password - The OpenSprinkler controller password.
   - Verify SSL Certificate - If the integration should verify the certificate from an HTTPS server. Generally, this should be left checked.
   - MAC Address - MAC address of the device. This is only required for firmware below 2.1.9 (4), otherwise it can be left blank.
   - Controller Name - The name of the device that appears in Home Assistant.

### Upgrading from pre 1.0.0

Note: _1.0.0 has major breaking changes, you will need to update any automations, scripts, etc_

1. Remove YAML configuration.
2. Uninstall using HACS or delete the `hass_opensprinkler` folder in `<config_dir>/custom_components`
3. Restart Home Assistant
4. Follow installation instructions above

#### Breaking Changes

- Program binary sensors now show running state instead of operation state. Please use the program switch states for program operation state.
- Controller binary sensor is removed. Please use controller switch state for controller operation state.
- Station switches now enable/disable instead of run/stop stations. Please use `opensprinkler.run_station` and `opensprinkler.stop` actions to run and stop stations.
- All scenes are removed. Please use the `opensprinkler.run_program` action to run programs.

## Using Actions

Available actions are `opensprinkler.run_program`, `opensprinkler.run_station`, and `opensprinkler.run_once` 
to start a program, station, or controller (multiple stations) respectively, and `opensprinkler.stop` to stop one or all stations.

Note: The action `opensprinkler.run` is deprecated and will be removed in a future release. Please migrate to one of the above actions, 
which use the same parameters.

### Run Examples

Note: If using a version of Home Assistant prior to 2024.8, substitute the keyword `service` for `action` in the following examples.

#### Run Program Example

```yaml
action: opensprinkler.run_program
target:
  entity_id: switch.standard_schedule_program_enabled # Any program enabled switch
data: {}
```

#### Run Station Example

```yaml
action: opensprinkler.run_station
data:
  run_seconds: 600 # Number of seconds to run the station. Optional, defaults to 60 seconds.
target:
  entity_id: switch.front_yard_station_enabled # Any station enabled switch
  ```

#### Run Once Program Example

To run a number of stations at once, use `opensprinkler.run_once`. The run seconds can either be a list of seconds per station 
or a list or dict of index and seconds pairs.
The following examples are all equivalent.

```yaml
action: opensprinkler.run_once
target:
  entity_id: switch.opensprinkler_enabled # Controller enabled switch
data:
  run_seconds: # List of seconds to run for each station (required)
    - 60
    - 0
    - 30
```

```yaml
action: opensprinkler.run_once
target:
  entity_id: switch.opensprinkler_enabled # Controller enabled switch
data:
  run_seconds: # List of station index and run seconds pairs (required)
    - index: 0
      run_seconds: 60
    - index: 2
      run_seconds: 30
```

```yaml
action: opensprinkler.run_once
target:
  entity_id: switch.opensprinkler_enabled # Controller enabled switch
data:
  run_seconds: # Dictionary of station index and run seconds key/value pairs (required)
    "0": 60
    "2": 30
```

Calling `opensprinkler.run_once` or `opensprinkler.run_program` will stop all other stations that are running. 
When using `opensprinkler.run_once`, you can set `continue_running_stations` to true to allow the stations to 
continue running. This only works when specifying the run seconds in index/seconds pairs.

```yaml
action: opensprinkler.run_once
target:
  entity_id: switch.opensprinkler_enabled # Controller enabled switch
data:
  continue_running_stations: true # Keep running stations running (optional, defaults to false)
  run_seconds:
    - index: 0
      run_seconds: 60
    - index: 2
      run_seconds: 30
```

```yaml
action: opensprinkler.run_once
target:
  entity_id: switch.opensprinkler_enabled # Controller enabled switch
data:
  continue_running_stations: true # Keep running stations running (optional, defaults to false)
  run_seconds:
    "0": 60
    "2": 30
```

### Stop Examples

#### Stop Station Example

```yaml
action: opensprinkler.stop
data: {}
target:
  entity_id: switch.drip_station_enabled # Any station enabled switch
```

#### Stop All Stations Example

```yaml
action: opensprinkler.stop
data: {}
target:
  entity_id: switch.opensprinkler_enabled # Controller enabled switch
  ```

### Set Water Level Example

This sets the water level to 50%, i.e. all stations will run half of their normally configured time.

```yaml
action: opensprinkler.set_water_level
data:
  water_level: 50
target:
  entity_id: switch.opensprinkler_enabled # Controller enabled switch
```

### Set Rain Delay Example

This sets the rain delay of the controller to 6 hours, i.e. all stations will stop and programs will not run until the rain delay time is over.

```yaml
action: opensprinkler.set_rain_delay
data:
  rain_delay: 6
target:
  entity_id: switch.opensprinkler_enabled # Controller enabled switch
```

### Pause Example

This pauses the station runs for 10 minutes (600 seconds), resuming afterwards.

```yaml
action: opensprinkler.pause_stations
data:
  pause_duration: 600
target:
  entity_id: switch.opensprinkler_enabled # Controller enabled switch
```

### Reboot Controller Example

This reboots the controller.

```yaml
action: opensprinkler.reboot
data: {}
target:
  entity_id: switch.opensprinkler_enabled # Controller enabled switch
```

## Creating a Station Switch

If you wish to have a switch for your stations, here is an example using the switch template and input number.
Add the following to your YAML configuration (`configuration.yaml`).

```yaml
switch:
  - platform: template
    switches:
      fruits_station:
        value_template: "{{ is_state('binary_sensor.front_yard_station_running', 'on') }}"
        turn_on:
          action: opensprinkler.run_station
          target:
            entity_id: switch.front_yard_station_enabled
            # Run seconds uses the input_number below.
          data:
            run_seconds: "{{ ((states('input_number.front_yard_station_minutes') | float) * 60) | int }}"
        turn_off:
          service: opensprinkler.stop
          target:
            entity_id: switch.front_yard_station_enabled
​
input_number:
  front_yard_station_minutes:
    initial: 1
    min: 1
    max: 10
    step: 1
```
