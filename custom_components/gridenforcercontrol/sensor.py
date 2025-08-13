"""GridenforcerControl sensor entities."""

from datetime import datetime, timedelta
import logging
import random
import zoneinfo

from homeassistant.components.sensor import RestoreSensor, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.condition import SensorDeviceClass
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_state_change,
    async_track_time_change,
    async_track_time_interval,
)

from .const import CONF_PRICE_SENSOR, DOMAIN
from .invertermode import InverterMode
from .pricecalculator import PriceCalculator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the sensors."""

    price_hub: PriceCalculator = hass.data[DOMAIN]["price_hub"]

    inverter_mode_sensor = InverterModeSensor(
        "inverter_mode", config_entry.entry_id, "Inverter Mode", hass, config_entry
    )
    # next_charge_slot_1 = ChargeDateTimeSensor(
    #     "next_charge_slot_1",
    #     config_entry.entry_id,
    #     "Next Charge Slot 1",
    #     hass,
    #     config_entry,
    #     "next_charge_slot1",
    #     True,
    #     inverter_mode_sensor,
    # )
    # next_discharge_slot_1 = ChargeDateTimeSensor(
    #     "next_discharge_slot_1",
    #     config_entry.entry_id,
    #     "Next Discharge Slot 1",
    #     hass,
    #     config_entry,
    #     "next_discharge_slot1",
    #     False,
    #     inverter_mode_sensor,
    # )
    # next_charge_slot_2 = ChargeDateTimeSensor(
    #     "next_charge_slot_2",
    #     config_entry.entry_id,
    #     "Next Charge Slot 2",
    #     hass,
    #     config_entry,
    #     "next_charge_slot2",
    #     True,
    #     inverter_mode_sensor,
    # )
    # next_discharge_slot_2 = ChargeDateTimeSensor(
    #     "next_discharge_slot_2",
    #     config_entry.entry_id,
    #     "Next Discharge Slot 2",
    #     hass,
    #     config_entry,
    #     "next_discharge_slot2",
    #     False,
    #     inverter_mode_sensor,
    # )

    # Register the sensor with Home Assistant
    async_add_entities(
        [
            inverter_mode_sensor,
            # next_charge_slot_1,
            # next_discharge_slot_1,
            # next_charge_slot_2,
            # next_discharge_slot_2,
        ]
    )
    await price_hub.async_check_inital_sensor_values(
        inverter_mode_sensor,
        None,
        None,
        None,
        None,
        # next_charge_slot_1,
        # next_discharge_slot_1,
        # next_charge_slot_2,
        # next_discharge_slot_2,
    )

    return True


# Define possible inverter modes


class InverterModeSensor(SensorEntity):
    """Representation of the inverter mode sensor."""

    def __init__(
        self,
        unique_id: str,
        device_unique_id: str,
        entity_name: str,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ):
        """Initialize the sensor."""

        self._attr_unique_id = unique_id
        self._attr_name = entity_name
        self._attr_translation_key = unique_id
        self._state = InverterMode.STANDBY  # Default state
        self._mode_before_fcr = InverterMode.STANDBY
        self.should_poll = False
        self._attr_device_info = DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, device_unique_id)
            },
            name="GridEnforcer",
        )
        self._nextChargeTime = None
        self._nextDischargeTime = None
        self._price_hub = hass.data[DOMAIN]["price_hub"]
        self._lowest_avail_price = None
        self._highest_avail_price = None
        self._next_charge_slot = None
        self._next_discharge_slot = None
        self._config = config_entry
        # pricesensor = hass.states.get(config_entry.data[CONF_PRICE_SENSOR])
        # self.update_price_calculator(pricesensor)

    @property
    def state(self):
        """Return the current mode of the inverter."""
        # self.get_state_from_schedule()
        if not self._state:
            self.set_state_from_schedule()
        return self._state.value

    def set_state_from_schedule(self):
        now = datetime.now(zoneinfo.ZoneInfo(key="Europe/Stockholm"))
        if len(self._price_hub.schedule_today) > 0:
            cur_sched = next(
                filter(
                    lambda x: x.start <= now and x.end >= now,
                    self._price_hub.schedule_today,
                )
            )
            if cur_sched:
                match cur_sched.mode:
                    case "Standby":
                        self._state = InverterMode.STANDBY
                    case "Charge":
                        self._state = InverterMode.CHARGING
                    case "Selfuse":
                        self._state = InverterMode.SELFUSE
                    case "Sell":
                        self._state = InverterMode.DISCHARGING
            else:
                self._state = InverterMode.STANDBY
        else:
            self._state = InverterMode.STANDBY

    @property
    def extra_state_attributes(self) -> dict:
        next_charge_slot_price = None
        next_charge_slot_start = None
        next_discharge_slot_price = None
        next_discharge_slot_start = None
        if self._next_charge_slot:
            next_charge_slot_price = self._next_charge_slot.value
            next_charge_slot_start = self._next_charge_slot.start

        if self._next_discharge_slot:
            next_discharge_slot_price = self._next_discharge_slot.sell_value
            next_discharge_slot_start = self._next_discharge_slot.start

        sched = []
        if self._price_hub.schedule_today:
            for i in self._price_hub.schedule_today:
                sched.append(i.to_dict())
        sched_tomorrow = []
        if self._price_hub.schedule_tomorrow:
            for i in self._price_hub.schedule_tomorrow:
                sched_tomorrow.append(i.to_dict())

        return {
            # "next_charge_time": self._nextChargeTime,
            # "next_discharge_time": self._nextDischargeTime,
            # "lowest_avail_price": self._lowest_avail_price,
            # "highest_avail_price": self._highest_avail_price,
            # "next_charge_slot": next_charge_slot_start,
            # "next_discharge_slot": next_discharge_slot_start,
            # "next_charge_slot_price": next_charge_slot_price,
            # "next_discharge_slot_price": next_discharge_slot_price,
            # "raw_buy_today": self._price_hub.raw_buy_today,
            # "raw_sell_today": self._price_hub.raw_sell_today,
            # "raw_buy_tomorrow": self._price_hub.raw_buy_tomorrow,
            # "raw_sell_tomorrow": self._price_hub.raw_sell_tomorrow,
            "schedule_today": sched,
            "schedule_tomorrow": sched_tomorrow,
            "selfuse_today_max": self._price_hub.selfuse_today_max,
            "sell_today_max": self._price_hub.sell_today_max,
            "selfuse_tomorrow_max": self._price_hub.selfuse_tomorrow_max,
            "sell_tomorrow_max": self._price_hub.sell_tomorrow_max,
        }

    async def set_state(self, mode: InverterMode):
        """Set the inverter mode"""
        self._state = mode
        # self.async_write_ha_state()

    async def async_update(self):
        """Update the inverter mode state."""
        # In a real scenario, you'd fetch this data from an inverter or API.
        # For demo purposes, we'll randomly select an inverter mode.
        self._state = self.set_state_from_schedule()
        # _LOGGER.info(f"Inverter mode updated: {self._state}")
        self.async_write_ha_state()

    # async def async_update_from_state_price(
    #     self, entity_id: str, old_state: State | None, new_state: State | None
    # ):
    #     """Update schedule we got new prices"""
    #     _LOGGER.info(f"Inverter mode updated state: {self._state}")
    #     if entity_id == self._config.data[CONF_PRICE_SENSOR]:
    #         self.update_price_calculator(new_state)

    #     await self.async_update()


class ChargeDateTimeSensor(RestoreSensor):
    """Representation of the datetime sensor."""

    def __init__(
        self,
        unique_id: str,
        device_unique_id: str,
        entity_name: str,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        date_prop_name: str,
        is_charge_sensor: bool,
        inverter_sensor: InverterModeSensor,
    ):
        """Initialize the sensor."""

        self._attr_unique_id = unique_id
        self._attr_name = entity_name
        self._attr_translation_key = unique_id
        self._state = None  # Default state
        self.device_class = SensorDeviceClass.DATE
        self.should_poll = False
        self._attr_device_info = DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, device_unique_id)
            },
            name="GridEnforcer",
        )

        self._price_hub: PriceCalculator = hass.data[DOMAIN]["price_hub"]
        self._date_time_value = None
        self._date_prop_name = date_prop_name
        self._is_charge_sensor = is_charge_sensor
        self._work_handle = None
        self._hass = hass
        self._invertermode_sensor = inverter_sensor

    @property
    def state(self):
        """Return the current value of the sensor."""
        return self._date_time_value

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        date_time_value = await self.async_get_last_sensor_data()
        if not date_time_value:
            return
        self._date_time_value = date_time_value.native_value
        self.native_value = date_time_value.native_value
        self.native_unit_of_measurement = date_time_value.native_unit_of_measurement

    # async def async_charge_start(self, now):
    #     """Callback for charing start"""
    #     await self._invertermode_sensor.set_state(InverterMode.CHARGING)
    #     self._date_time_value = None
    #     self.async_write_ha_state()

    # async def async_discharge_start(self, now):
    #     """Callback for discharing start"""
    #     await self._invertermode_sensor.set_state(InverterMode.DISCHARGING)
    #     self._date_time_value = None
    #     self.async_write_ha_state()

    async def async_update(self):
        """Update the sensor state."""
        value = getattr(self._price_hub, self._date_prop_name)
        if value:
            self._date_time_value = value.start
            # if self._work_handle:
            #     await self._hass.async_add_executor_job(self._work_handle)
            # if self._is_charge_sensor:
            #     self._work_handle = async_track_point_in_time(
            #         self._hass, self.async_charge_start, value.start
            #     )
            # else:
            #     self._work_handle = async_track_point_in_time(
            #         self._hass, self.async_discharge_start, value.start
            #     )
        else:
            self._date_time_value = None

        _LOGGER.info(f"Price updated: {self._state}")
        self.async_write_ha_state()


#    @property
#    def extra_state_attributes(self) -> dict:
#        return {
#            "slot_price": getattr(self._price_hub, self._date_prop_name).value,
#        }
