"""Config flow for GridEnForcerControl integration."""

from __future__ import annotations

import logging
from typing import Any, cast

import voluptuous as vol
from homeassistant.config_entries import (ConfigEntry, ConfigFlow,
                                          ConfigFlowResult, OptionsFlow)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (CONF_BAT_COST, CONF_EXTRA_EXPORT, CONF_EXTRA_IMPORT,
                    CONF_FCRDD_INPUT, CONF_FCRDU_INPUT, CONF_HOURS_SELFUSE,
                    CONF_PRICE_SENSOR, CONF_SOC_SENSOR, CONF_VAT, DOMAIN)

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PRICE_SENSOR): cv.string,
        vol.Required(CONF_EXTRA_IMPORT): vol.All(cv.string, vol.Coerce(float)),
        vol.Required(CONF_EXTRA_EXPORT): vol.All(cv.string, vol.Coerce(float)),
        vol.Required(CONF_VAT): vol.All(cv.string, vol.Coerce(float)),
        vol.Required(CONF_BAT_COST): vol.All(cv.string, vol.Coerce(float)),
        vol.Required(CONF_SOC_SENSOR): cv.string,
        vol.Required(CONF_FCRDU_INPUT): cv.string,
        vol.Required(CONF_FCRDD_INPUT): cv.string,
        vol.Required(CONF_HOURS_SELFUSE): vol.All(cv.string, vol.Coerce(float)),
    }
)


class PlaceholderHub:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, host: str) -> None:
        """Initialize."""
        self.host = host

    async def authenticate(self, username: str, password: str) -> bool:
        """Test if we can authenticate with the host."""
        return True


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data[CONF_USERNAME], data[CONF_PASSWORD]
    # )

    # hub = PlaceholderHub(data[CONF_HOST])

    # if not await hub.authenticate(data[CONF_USERNAME], data[CONF_PASSWORD]):
    #     raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth
    if not hass.states.get(data[CONF_PRICE_SENSOR]):
        raise InvalidSensor

    # Return info that you want to store in the config entry.
    return {"title": "GridEnforcerControl"}


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GridEnForcerControl."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        # options_flow = OPTIONS_FLOW

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(OptionsFlow):  # type: ignore[misc]
    """GridEnforcer options flow."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize a GridEnforcer options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Manage the options."""
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=user_input, options=self._config_entry.options
            )
            return self.async_create_entry(title="", data={})

        schema: dict[Any, Any] = {
            vol.Required(
                CONF_PRICE_SENSOR,
                default=self._config_entry.data.get(CONF_PRICE_SENSOR),
            ): cv.string,
            vol.Required(
                CONF_EXTRA_IMPORT,
                default=self._config_entry.data.get(CONF_EXTRA_IMPORT),
            ): vol.All(cv.string, vol.Coerce(float)),
            vol.Required(
                CONF_EXTRA_EXPORT,
                default=self._config_entry.data.get(CONF_EXTRA_EXPORT),
            ): vol.All(cv.string, vol.Coerce(float)),
            vol.Required(
                CONF_VAT, default=self._config_entry.data.get(CONF_VAT)
            ): vol.All(cv.string, vol.Coerce(float)),
            vol.Required(
                CONF_BAT_COST, default=self._config_entry.data.get(CONF_BAT_COST)
            ): vol.All(cv.string, vol.Coerce(float)),
            vol.Required(
                CONF_SOC_SENSOR,
                default=self._config_entry.data.get(CONF_SOC_SENSOR),
            ): cv.string,
            vol.Required(
                CONF_FCRDD_INPUT,
                default=self._config_entry.data.get(CONF_FCRDD_INPUT),
            ): cv.string,
            vol.Required(
                CONF_FCRDU_INPUT,
                default=self._config_entry.data.get(CONF_FCRDU_INPUT),
            ): cv.string,
            vol.Required(
                CONF_HOURS_SELFUSE,
                default=self._config_entry.data.get(CONF_HOURS_SELFUSE),
            ): vol.All(cv.string, vol.Coerce(float)),
        }

        return cast(
            dict[str, Any],
            self.async_show_form(step_id="init", data_schema=vol.Schema(schema)),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidSensor(HomeAssistantError):
    """Error to indicate there is invalid auth."""
