"""GridenforcerControl select entities."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the demo select platform."""
    async_add_entities(
        [
            GridEnforcerSelect(
                unique_id="operation_mode",
                entity_name="Operation Mode",
                device_unique_id=config_entry.entry_id,
                current_option="automatic_mode",
                options=[
                    "automatic_mode",
                    "manual_mode",
                ],
            ),
        ]
    )


class GridEnforcerSelect(SelectEntity, RestoreEntity):
    """Representation of a GridEnforcer select entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False

    def __init__(
        self,
        unique_id: str,
        entity_name: str,
        device_unique_id: str,
        current_option: str | None,
        options: list[str],
    ) -> None:
        """Initialize the GridEnforcer select entity."""
        self._attr_unique_id = unique_id
        self._attr_current_option = current_option
        self._attr_options = options
        self._attr_translation_key = unique_id
        self._attr_name = entity_name
        self._attr_device_info = DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, device_unique_id)
            },
            name="GridEnforcer",
        )

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""
        self._attr_current_option = option
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if not state:
            return
        self._attr_current_option = state.state
