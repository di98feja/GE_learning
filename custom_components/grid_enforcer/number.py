"""Demo platform that offers a fake Number entity."""

from __future__ import annotations

from homeassistant.components.number import (NumberDeviceClass, NumberEntity,
                                             NumberMode, RestoreNumber)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the demo number platform."""
    async_add_entities(
        [
            # GridEnforcerNumber(
            #     "kwh_use_battery",
            #     config_entry.entry_id,
            #     "kWh Use Battery",
            #     native_min_value=0.0,
            #     mode=NumberMode.BOX,
            #     icon="mdi:cash",
            #     unit_of_measurement="SEK/kWh",
            # ),
            # GridEnforcerNumber(
            #     "vat",
            #     config_entry.entry_id,
            #     "VAT %",
            #     native_min_value=0.0,
            #     mode=NumberMode.BOX,
            #     icon="mdi:cash",
            #     unit_of_measurement="%",
            # ),
            # GridEnforcerNumber(
            #     "kwh_extra_import",
            #     config_entry.entry_id,
            #     "kWh Extra import",
            #     native_min_value=0.0,
            #     mode=NumberMode.BOX,
            #     icon="mdi:cash",
            #     unit_of_measurement="SEK/kWh",
            # ),
            # GridEnforcerNumber(
            #     "kwh_extra_export",
            #     config_entry.entry_id,
            #     "kWh Extra export",
            #     native_min_value=0.0,
            #     mode=NumberMode.BOX,
            #     icon="mdi:cash",
            #     unit_of_measurement="SEK/kWh",
            # ),
            GridEnforcerNumber(
                "soc_backup",
                config_entry.entry_id,
                "SoC Backup",
                native_min_value=0.0,
                mode=NumberMode.BOX,
                icon="mdi:battery-charging-low",
                unit_of_measurement="%",
            ),
            GridEnforcerNumber(
                "soc_max",
                config_entry.entry_id,
                "SoC Max",
                native_min_value=0.0,
                mode=NumberMode.BOX,
                icon="mdi:battery-charging-high",
                unit_of_measurement="%",
            ),
            GridEnforcerNumber(
                "selfuse_hours",
                config_entry.entry_id,
                "Selfuse Hours",
                native_min_value=0.0,
                mode=NumberMode.BOX,
                icon="mdi:clock",
                unit_of_measurement="h",
            ),
            GridEnforcerNumber(
                "charge_hours",
                config_entry.entry_id,
                "Charge Hours",
                native_min_value=0.0,
                mode=NumberMode.BOX,
                icon="mdi:lightning-bolt",
                unit_of_measurement="h",
            ),
        ]
    )


class GridEnforcerNumber(RestoreNumber):
    """Representation of a GridEnforcer Number entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False

    def __init__(
        self,
        unique_id: str,
        device_unique_id: str,
        entity_name: str,
        *,
        device_class: NumberDeviceClass | None = None,
        mode: NumberMode = NumberMode.AUTO,
        native_min_value: float | None = None,
        native_max_value: float | None = None,
        native_step: float | None = None,
        unit_of_measurement: str | None = None,
        icon: str | None = None,
    ) -> None:
        """Initialize the GridEnforcer Number entity."""
        self._attr_assumed_state = False
        self._attr_device_class = device_class
        self._attr_translation_key = unique_id
        self._attr_mode = mode
        self._attr_native_unit_of_measurement = unit_of_measurement
        # self._attr_native_value = state
        self._attr_unique_id = unique_id
        self._attr_name = entity_name

        if native_min_value is not None:
            self._attr_native_min_value = native_min_value
        if native_max_value is not None:
            self._attr_native_max_value = native_max_value
        if native_step is not None:
            self._attr_native_step = native_step
        if icon is not None:
            self._attr_icon = icon

        self._attr_device_info = DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, device_unique_id)
            },
            name="GridEnforcer",
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        number_data = await self.async_get_last_number_data()
        if not number_data:
            return
        self._attr_native_value = number_data.native_value
