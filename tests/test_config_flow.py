"""Tests for the OpenSprinkler reconfigure config flow."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp.client_exceptions import InvalidURL
from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.const import (
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_URL,
    CONF_VERIFY_SSL,
)
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import slugify
from pyopensprinkler import OpenSprinklerAuthError, OpenSprinklerConnectionError

pytest.importorskip("pytest_homeassistant_custom_component")

from pytest_homeassistant_custom_component.common import (  # noqa: E402
    MockConfigEntry,
)

from custom_components.opensprinkler.const import DOMAIN  # noqa: E402

OLD_URL = "http://192.168.1.10"
NEW_URL = "http://192.168.1.50"
PASSWORD = "secret"
MAC = "AA:BB:CC:DD:EE:FF"
UNIQUE_ID = slugify(MAC)


@pytest.fixture(scope="module", autouse=True)
def add_custom_component_path():
    """Make HA discover this repo's custom component."""
    import custom_components

    custom_path = str(Path(__file__).resolve().parents[1] / "custom_components")
    if custom_path not in list(custom_components.__path__):
        custom_components.__path__.insert(0, custom_path)


@pytest.fixture(scope="module", autouse=True)
def mock_setup_entry(add_custom_component_path):
    """Keep setup/unload mocked for the whole module so hass teardown stays clean."""
    import custom_components.opensprinkler as ospi

    with (
        patch.object(ospi, "async_setup_entry", AsyncMock(return_value=True)),
        patch.object(ospi, "async_unload_entry", AsyncMock(return_value=True)),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_reload",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.opensprinkler.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        yield


@pytest.fixture(autouse=True)
def enable_custom_integrations_fixture(enable_custom_integrations):
    """Rescan custom integrations after the path is registered."""
    yield


def _mock_controller(mac=MAC):
    controller = MagicMock()
    controller.mac_address = mac
    controller.refresh = AsyncMock()
    return controller


def _mock_entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=UNIQUE_ID,
        title="OpenSprinkler",
        data={
            CONF_URL: OLD_URL,
            CONF_PASSWORD: PASSWORD,
            CONF_NAME: "OpenSprinkler",
            CONF_VERIFY_SSL: True,
        },
    )
    entry.add_to_hass(hass)
    return entry


async def _start_reconfigure(hass, entry):
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
    )


async def test_reconfigure_form_shows_current_url(hass, mock_setup_entry):
    """The first reconfigure form is URL + Verify SSL, prefilled."""
    entry = _mock_entry(hass)

    result = await _start_reconfigure(hass, entry)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert CONF_URL in result["data_schema"].schema
    assert CONF_VERIFY_SSL in result["data_schema"].schema
    assert CONF_PASSWORD not in result["data_schema"].schema
    assert CONF_MAC not in result["data_schema"].schema


async def test_reconfigure_updates_existing_entry(hass, mock_setup_entry):
    """A matching controller updates the same entry in place."""
    entry = _mock_entry(hass)
    controller = _mock_controller()

    result = await _start_reconfigure(hass, entry)
    with patch(
        "custom_components.opensprinkler.config_flow.OpenSprinkler",
        return_value=controller,
    ) as mock_api:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_URL: NEW_URL, CONF_VERIFY_SSL: False},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.data[CONF_URL] == NEW_URL
    assert entry.data[CONF_VERIFY_SSL] is False
    assert entry.data[CONF_PASSWORD] == PASSWORD
    assert entry.unique_id == UNIQUE_ID
    mock_api.assert_called_once()
    assert mock_api.call_args.args[0] == NEW_URL
    assert mock_api.call_args.args[1] == PASSWORD


async def test_reconfigure_cannot_connect(hass, mock_setup_entry):
    """Connection failures stay on the first form and do not update the entry."""
    entry = _mock_entry(hass)
    controller = _mock_controller()
    controller.refresh.side_effect = OpenSprinklerConnectionError

    result = await _start_reconfigure(hass, entry)
    with patch(
        "custom_components.opensprinkler.config_flow.OpenSprinkler",
        return_value=controller,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_URL: NEW_URL, CONF_VERIFY_SSL: True},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"]["base"] == "cannot_connect"
    assert entry.data[CONF_URL] == OLD_URL


async def test_reconfigure_invalid_auth(hass, mock_setup_entry):
    """Auth failures stay on the first form and do not update the entry."""
    entry = _mock_entry(hass)
    controller = _mock_controller()
    controller.refresh.side_effect = OpenSprinklerAuthError

    result = await _start_reconfigure(hass, entry)
    with patch(
        "custom_components.opensprinkler.config_flow.OpenSprinkler",
        return_value=controller,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_URL: NEW_URL, CONF_VERIFY_SSL: True},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"
    assert entry.data[CONF_URL] == OLD_URL


async def test_reconfigure_invalid_url(hass, mock_setup_entry):
    """Malformed URLs stay on the first form."""
    entry = _mock_entry(hass)
    controller = _mock_controller()
    controller.refresh.side_effect = InvalidURL("not-a-url")

    result = await _start_reconfigure(hass, entry)
    with patch(
        "custom_components.opensprinkler.config_flow.OpenSprinkler",
        return_value=controller,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_URL: "not-a-url", CONF_VERIFY_SSL: True},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_url"
    assert entry.data[CONF_URL] == OLD_URL


async def test_reconfigure_wrong_device(hass, mock_setup_entry):
    """A different controller MAC is rejected and the entry is unchanged."""
    entry = _mock_entry(hass)
    controller = _mock_controller(mac="11:22:33:44:55:66")

    result = await _start_reconfigure(hass, entry)
    with patch(
        "custom_components.opensprinkler.config_flow.OpenSprinkler",
        return_value=controller,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_URL: NEW_URL, CONF_VERIFY_SSL: True},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
    assert entry.data[CONF_URL] == OLD_URL
    assert entry.unique_id == UNIQUE_ID
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_reconfigure_without_api_mac_asks_for_mac(hass, mock_setup_entry):
    """Legacy firmware with no API MAC goes to the second step."""
    entry = _mock_entry(hass)
    controller = _mock_controller(mac=None)

    result = await _start_reconfigure(hass, entry)
    with patch(
        "custom_components.opensprinkler.config_flow.OpenSprinkler",
        return_value=controller,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_URL: NEW_URL, CONF_VERIFY_SSL: True},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure_mac"
    assert CONF_MAC in result["data_schema"].schema
    assert entry.data[CONF_URL] == OLD_URL


async def test_reconfigure_mac_matching_updates_entry(hass, mock_setup_entry):
    """A matching manual MAC finishes reconfigure on the same entry."""
    entry = _mock_entry(hass)
    controller = _mock_controller(mac=None)

    result = await _start_reconfigure(hass, entry)
    with patch(
        "custom_components.opensprinkler.config_flow.OpenSprinkler",
        return_value=controller,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_URL: NEW_URL, CONF_VERIFY_SSL: False},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_MAC: MAC},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.data[CONF_URL] == NEW_URL
    assert entry.data[CONF_VERIFY_SSL] is False
    assert entry.data[CONF_PASSWORD] == PASSWORD
    assert entry.unique_id == UNIQUE_ID


async def test_reconfigure_mac_mismatch_aborts(hass, mock_setup_entry):
    """A different manual MAC is rejected and the entry is unchanged."""
    entry = _mock_entry(hass)
    controller = _mock_controller(mac=None)

    result = await _start_reconfigure(hass, entry)
    with patch(
        "custom_components.opensprinkler.config_flow.OpenSprinkler",
        return_value=controller,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_URL: NEW_URL, CONF_VERIFY_SSL: True},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_MAC: "11:22:33:44:55:66"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
    assert entry.data[CONF_URL] == OLD_URL
    assert entry.unique_id == UNIQUE_ID
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
