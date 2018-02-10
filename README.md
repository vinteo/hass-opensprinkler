## hass-opensprinkler

Opensprinkler custom component for Home Assistant

### Installation

1. Copy all files into `<config_dir>/custom_components`
2. Add the following into your `configuration.yaml`
    ```yaml
    opensprinkler:
      host: <host>
      password: <password>
    ```
    - Replace `<host>` with the IP address or hostname of your Opensprinkler controller.
    - Replace `<password>` with the MD5 encrypted version of your password to your Opensprinkler interface.

3. Restart home assistant

### Configuration

- `stations` - by default the component will retrieve all stations but you can limit which stations to show by providing a list of station indexes (starting from 0)
    ```yaml
    opensprinkler:
      ...
      stations:
        - 0
        - 3
        - 4
    ```

 ### TODO

- program switches