"""Tests for Tankerkoenig config flow."""
from unittest.mock import patch

from pytankerkoenig import customException

from homeassistant.components.tankerkoenig.const import (
    CONF_FUEL_TYPES,
    CONF_STATIONS,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LOCATION,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_RADIUS,
    CONF_SHOW_ON_MAP,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

MOCK_USER_DATA = {
    CONF_NAME: "Home",
    CONF_API_KEY: "269534f6-xxxx-xxxx-xxxx-yyyyzzzzxxxx",
    CONF_FUEL_TYPES: ["e5"],
    CONF_LOCATION: {CONF_LATITUDE: 51.0, CONF_LONGITUDE: 13.0},
    CONF_RADIUS: 2.0,
}

MOCK_STATIONS_DATA = {
    CONF_STATIONS: [
        "3bcd61da-xxxx-xxxx-xxxx-19d5523a7ae8",
        "36b4b812-xxxx-xxxx-xxxx-c51735325858",
    ],
}

MOCK_OPTIONS_DATA = {
    **MOCK_USER_DATA,
    CONF_STATIONS: [
        "3bcd61da-xxxx-xxxx-xxxx-19d5523a7ae8",
        "36b4b812-xxxx-xxxx-xxxx-c51735325858",
        "54e2b642-xxxx-xxxx-xxxx-87cd4e9867f1",
    ],
}

MOCK_NEARVY_STATIONS_OK = {
    "ok": True,
    "stations": [
        {
            "id": "3bcd61da-xxxx-xxxx-xxxx-19d5523a7ae8",
            "brand": "BrandA",
            "place": "CityA",
            "street": "Main",
            "houseNumber": "1",
            "dist": 1,
        },
        {
            "id": "36b4b812-xxxx-xxxx-xxxx-c51735325858",
            "brand": "BrandB",
            "place": "CityB",
            "street": "School",
            "houseNumber": "2",
            "dist": 2,
        },
    ],
}


async def test_user(hass: HomeAssistant):
    """Test starting a flow by user."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "homeassistant.components.tankerkoenig.async_setup_entry", return_value=True
    ) as mock_setup_entry, patch(
        "homeassistant.components.tankerkoenig.config_flow.getNearbyStations",
        return_value=MOCK_NEARVY_STATIONS_OK,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_USER_DATA
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "select_station"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_STATIONS_DATA
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_NAME] == "Home"
        assert result["data"][CONF_API_KEY] == "269534f6-xxxx-xxxx-xxxx-yyyyzzzzxxxx"
        assert result["data"][CONF_FUEL_TYPES] == ["e5"]
        assert result["data"][CONF_LOCATION] == {"latitude": 51.0, "longitude": 13.0}
        assert result["data"][CONF_RADIUS] == 2.0
        assert result["data"][CONF_STATIONS] == [
            "3bcd61da-xxxx-xxxx-xxxx-19d5523a7ae8",
            "36b4b812-xxxx-xxxx-xxxx-c51735325858",
        ]
        assert result["options"][CONF_SHOW_ON_MAP]

        await hass.async_block_till_done()

    assert mock_setup_entry.called


async def test_user_already_configured(hass: HomeAssistant):
    """Test starting a flow by user with an already configured region."""

    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={**MOCK_USER_DATA, **MOCK_STATIONS_DATA},
        unique_id=f"{MOCK_USER_DATA[CONF_LOCATION][CONF_LATITUDE]}_{MOCK_USER_DATA[CONF_LOCATION][CONF_LONGITUDE]}",
    )
    mock_config.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_USER_DATA
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_exception_security(hass: HomeAssistant):
    """Test starting a flow by user with invalid api key."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "homeassistant.components.tankerkoenig.config_flow.getNearbyStations",
        side_effect=customException,
    ):

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_USER_DATA
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"][CONF_API_KEY] == "invalid_auth"


async def test_user_no_stations(hass: HomeAssistant):
    """Test starting a flow by user which does not find any station."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "homeassistant.components.tankerkoenig.config_flow.getNearbyStations",
        return_value={"ok": True, "stations": []},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_USER_DATA
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"][CONF_RADIUS] == "no_stations"


async def test_reauth(hass: HomeAssistant):
    """Test starting a flow by user to re-auth."""

    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={**MOCK_USER_DATA, **MOCK_STATIONS_DATA},
        unique_id=f"{MOCK_USER_DATA[CONF_LOCATION][CONF_LATITUDE]}_{MOCK_USER_DATA[CONF_LOCATION][CONF_LONGITUDE]}",
    )
    mock_config.add_to_hass(hass)

    with patch(
        "homeassistant.components.tankerkoenig.async_setup_entry", return_value=True
    ) as mock_setup_entry, patch(
        "homeassistant.components.tankerkoenig.config_flow.getNearbyStations",
    ) as mock_nearby_stations:
        # re-auth initialized
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH, "entry_id": mock_config.entry_id},
            data=mock_config.data,
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        # re-auth unsuccessful
        mock_nearby_stations.return_value = {"ok": False}
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_API_KEY: "269534f6-aaaa-bbbb-cccc-yyyyzzzzxxxx",
            },
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"
        assert result["errors"] == {CONF_API_KEY: "invalid_auth"}

        # re-auth successful
        mock_nearby_stations.return_value = MOCK_NEARVY_STATIONS_OK
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_API_KEY: "269534f6-aaaa-bbbb-cccc-yyyyzzzzxxxx",
            },
        )
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"

    mock_setup_entry.assert_called()

    entry = hass.config_entries.async_get_entry(mock_config.entry_id)
    assert entry.data[CONF_API_KEY] == "269534f6-aaaa-bbbb-cccc-yyyyzzzzxxxx"


async def test_options_flow(hass: HomeAssistant):
    """Test options flow."""

    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_OPTIONS_DATA,
        options={CONF_SHOW_ON_MAP: True},
        unique_id=f"{DOMAIN}_{MOCK_USER_DATA[CONF_LOCATION][CONF_LATITUDE]}_{MOCK_USER_DATA[CONF_LOCATION][CONF_LONGITUDE]}",
    )
    mock_config.add_to_hass(hass)

    with patch(
        "homeassistant.components.tankerkoenig.async_setup_entry", return_value=True
    ) as mock_setup_entry, patch(
        "homeassistant.components.tankerkoenig.config_flow.getNearbyStations",
        return_value=MOCK_NEARVY_STATIONS_OK,
    ):
        await hass.config_entries.async_setup(mock_config.entry_id)
        await hass.async_block_till_done()
        assert mock_setup_entry.called

        result = await hass.config_entries.options.async_init(mock_config.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SHOW_ON_MAP: False,
            CONF_STATIONS: MOCK_OPTIONS_DATA[CONF_STATIONS],
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert not mock_config.options[CONF_SHOW_ON_MAP]
