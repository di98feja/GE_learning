"""The GridEnForcerControl integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)

from .const import (
    CONF_BAT_COST,
    CONF_EXTRA_EXPORT,
    CONF_EXTRA_IMPORT,
    CONF_FCRDD_INPUT,
    CONF_FCRDU_INPUT,
    CONF_PRICE_SENSOR,
    CONF_SOC_SENSOR,
    CONF_VAT,
)
from .pricecalculator import PriceCalculator

DOMAIN = "gridenforcer"

PLATFORMS: list[Platform] = [Platform.NUMBER, Platform.SENSOR, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GridEnForcerControl from a config entry."""

    price_hub = PriceCalculator(hass, entry)
    hass.data[DOMAIN] = {"price_hub": price_hub}
    await price_hub.async_update_price_calculator()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Schedule the sensor update at 13:30 when new prices have arrived
    async_track_time_change(
        hass, price_hub.async_update_from_schedule, hour=13, minute=30, second=00
    )
    async_track_time_change(
        hass, price_hub.async_update_from_schedule, hour=0, minute=0, second=10
    )
    async_track_state_change_event(
        hass, entry.data[CONF_PRICE_SENSOR], price_hub.async_update_from_state_prices
    )
    async_track_state_change_event(
        hass, entry.data[CONF_SOC_SENSOR], price_hub.async_update_from_state_soc
    )

    async_track_state_change_event(
        hass, entry.data[CONF_FCRDD_INPUT], price_hub.async_update_from_state_fcrddown
    )

    async_track_state_change_event(
        hass, entry.data[CONF_FCRDU_INPUT], price_hub.async_update_from_state_fcrdup
    )
    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_START, price_hub.async_update_from_schedule
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
