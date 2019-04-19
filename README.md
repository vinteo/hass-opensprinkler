## hass-opensprinkler

Opensprinkler custom component for Home Assistant

Last tested on OS API `2.1.8` and Home Assistant `0.88.1`

![image](https://user-images.githubusercontent.com/819711/36068687-086820ce-0f2f-11e8-81de-de53c94124f0.png)

### Features

- Binary sensors for each station to show on/off status
- Binary sensors for OpenSprinkler operation, rain sensor and rain delay
- Sensors for each station to show status
- Sensors for water level, last run time and rain delay stop time
- Programs as scenes which can be "activated"
- Stations as switches with individual timers

### Installation

1. Copy `hass_opensprinkler` folder into `<config_dir>/custom_components`
2. Add the following into your `configuration.yaml`
    ```yaml
    hass_opensprinkler:
      host: <host>
      password: <md5-password>
    ```
    - Replace `<host>` with the IP address or hostname of your Opensprinkler controller.
    - Replace `<password>` with the MD5 encrypted version of your password to your Opensprinkler interface.

3. Restart Home Assistant

### Configuration

- `stations` - by default the component will retrieve all stations but you can limit which stations to show by providing a list of station indexes (starting from 0)
    ```yaml
    hass_opensprinkler:
      ...
      stations:
        - 0
        - 3
        - 4
    ```

- `programs` - by default the component will retrieve all programs but you can limit which programs to show by providing a list of program indexes (starting from 0)
    ```yaml
    hass_opensprinkler:
      ...
      programs:
        - 0
        - 3
    ```

## Support for Custom Updater

You can use [Custom Updater](https://github.com/custom-components/custom_updater) to track versions of this component. Once you have installed it, add the following to your configuration.

```yaml
custom_updater:
  track:
    - components
  component_urls:
    - https://raw.githubusercontent.com/vinteo/hass-opensprinkler/master/custom_components.json

```

