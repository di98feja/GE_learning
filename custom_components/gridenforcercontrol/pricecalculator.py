from collections import namedtuple
from datetime import datetime, timedelta
import logging
import math
import zoneinfo

# import numpy as np
# from scipy.signal import find_peaks
from typing import List, Tuple

from dateutil import parser

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)

from .const import (
    CONF_BAT_COST,
    CONF_EXTRA_EXPORT,
    CONF_EXTRA_IMPORT,
    CONF_HOURS_SELFUSE,
    CONF_PRICE_SENSOR,
    CONF_VAT,
)
from .invertermode import InverterMode
from .timevalue import TimeValue

_LOGGER = logging.getLogger(__name__)


class PriceCalculator:
    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        # price_sensor_state: State,
    ):
        self._config = config
        self._hass = hass
        # self._price_sensor_data = price_sensor_state
        self._price_sensor_data = None
        self._price_sensor_name = self._config.data[CONF_PRICE_SENSOR]
        self._battery_use = config.data[CONF_BAT_COST]
        # self._hours_self_use = (int)(config.data[CONF_HOURS_SELFUSE])
        self._hours_self_use = None
        self._inverter_mode_sonsor = None

        self._next_charge_slot1 = None
        self._next_discharge_slot1 = None
        self._next_charge_slot_1_sensor = None
        self._next_discharge_slot_1_sensor = None
        self._next_charge_slot2 = None
        self._next_discharge_slot2 = None
        self._next_charge_slot_2_sensor = None
        self._next_discharge_slot_2_sensor = None
        self._bat_soc_backup = None
        self._bat_soc_max = None
        self._raw_buy_today = []
        self._raw_sell_today = []
        self._raw_buy_tomorrow = []
        self._raw_sell_tomorrow = []
        self._schedule_today = []
        self._schedule_tomorrow = []
        self._selfuse_today_max = None
        self._sell_today_max = None
        self._selfuse_tomorrow_max = None
        self._sell_tomorrow_max = None
        self._charge_hours = None

    @property
    def today_lowest_price(self) -> TimeValue:
        return self._today_lowest_price

    @property
    def today_highest_price(self) -> TimeValue:
        return self._today_highest_price

    @property
    def tomorrow_lowest_price(self) -> TimeValue:
        return self._tomorrow_lowest_price

    @property
    def tomorrow_highest_price(self) -> TimeValue:
        return self._tomorrow_highest_price

    @property
    def all_avail_lowest_price(self) -> TimeValue:
        return self._all_avail_lowest_price

    @property
    def all_avail_highest_price(self) -> TimeValue:
        return self._all_avail_highest_price

    @property
    def next_charge_slot1(self) -> TimeValue:
        return self._next_charge_slot1

    @property
    def next_discharge_slot1(self) -> TimeValue:
        return self._next_discharge_slot1

    @property
    def next_charge_slot2(self) -> TimeValue:
        return self._next_charge_slot2

    @property
    def next_discharge_slot2(self) -> TimeValue:
        return self._next_discharge_slot2

    @property
    def raw_buy_today(self) -> list:
        return self._raw_buy_today

    @property
    def raw_sell_today(self) -> list:
        return self._raw_sell_today

    @property
    def raw_buy_tomorrow(self) -> list:
        return self._raw_buy_tomorrow

    @property
    def raw_sell_tomorrow(self) -> list:
        return self._raw_sell_tomorrow

    @property
    def schedule_today(self) -> list:
        return self._schedule_today

    @property
    def schedule_tomorrow(self) -> list:
        return self._schedule_tomorrow

    @property
    def selfuse_today_max(self) -> float:
        return self._selfuse_today_max

    @property
    def sell_today_max(self) -> float:
        return self._sell_today_max

    @property
    def selfuse_tomorrow_max(self) -> float:
        return self._selfuse_tomorrow_max

    @property
    def sell_tomorrow_max(self) -> float:
        return self._sell_tomorrow_max

    async def async_update_price_calculator(self, force_update: bool = False):
        if not self._hours_self_use:
            state = self._hass.states.get("number.gridenforcer_selfuse_hours")
            if state and state.state != "unavailable":
                self._hours_self_use = int(float(state.state))
        if not self._charge_hours:
            state = self._hass.states.get("number.gridenforcer_charge_hours")
            if state and state.state != "unavailable":
                self._charge_hours = int(float(state.state))

        if (
            not self._price_sensor_data
            or self._price_sensor_data.state == "unknown"
            or force_update
        ):
            self._price_sensor_data = self._hass.states.get(self._price_sensor_name)

        if self._price_sensor_data and self._price_sensor_data.state != "unknown":
            _LOGGER.info("Update prices (async_update_price_calculator)")
            await self.update_timevalues_from_dict(
                self._price_sensor_data.attributes["raw_today"],
                self._price_sensor_data.attributes["raw_tomorrow"],
            )

    @callback
    async def async_update_from_state_fcrddown(
        self, event: Event[EventStateChangedData]
    ) -> None:
        entity_id = event.data["entity_id"]
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        _LOGGER.info(f"FCRD Down changed {old_state} {new_state}")
        # await self.async_update_price_calculator(True)

    @callback
    async def async_update_from_state_fcrdup(
        self, event: Event[EventStateChangedData]
    ) -> None:
        entity_id = event.data["entity_id"]
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        _LOGGER.info(f"FCRD Up changed {old_state} {new_state}")

    @callback
    async def async_update_from_state_soc(
        self, event: Event[EventStateChangedData]
    ) -> None:
        entity_id = event.data["entity_id"]
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        _LOGGER.info(f"Soc changed {old_state} {new_state}")
        if not self._bat_soc_backup:
            state = self._hass.states.get("number.gridenforcer_soc_backup")
            self._bat_soc_backup = float(state.state) if state and state.state not in ('unknown', 'unavailable') else 20.0
            
        if not self._bat_soc_max:
            state = self._hass.states.get("number.gridenforcer_soc_max")
            self._bat_soc_max = float(state.state) if state and state.state not in ('unknown', 'unavailable') else 80.0

        if self._inverter_mode_sonsor.state == InverterMode.CHARGING.value:
            if float(new_state.state) < self._bat_soc_max:
                return

        if self._inverter_mode_sonsor.state == InverterMode.DISCHARGING.value:
            if float(new_state.state) > self._bat_soc_backup:
                return

        if float(new_state.state) < self._bat_soc_backup:
            await self._inverter_mode_sonsor.set_state(InverterMode.CHARGESOC)
            return

        if (
            float(new_state.state) >= self._bat_soc_backup
            and float(new_state.state) < self._bat_soc_max
        ):
            await self._inverter_mode_sonsor.set_state(InverterMode.STANDBY)
            return

        if float(new_state.state) == self._bat_soc_max:
            await self._inverter_mode_sonsor.set_state(InverterMode.FULLYCHARGED)

    async def async_update_from_state_prices(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Update the inverter mode state."""
        entity_id = event.data["entity_id"]
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        _LOGGER.info(f"Price updated from entity_id= {entity_id}")
        if not self._price_sensor_data or self._price_sensor_data.state == "unknown":
            self._price_sensor_data = new_state
        if self._price_sensor_data and self._price_sensor_data.state != "unknown":
            _LOGGER.info("Update prices")
            await self.update_timevalues_from_dict(
                self._price_sensor_data.attributes["raw_today"],
                self._price_sensor_data.attributes["raw_tomorrow"],
            )

    async def async_update_from_schedule(self, time):
        """Update the sensors."""
        _LOGGER.info(f"Price update from schedule ")
        await self.async_update_price_calculator(True)

    async def async_check_inital_sensor_values(
        self,
        mode_sensor: any,
        next_charge_slot_1: any,
        next_discharge_slot_1: any,
        next_charge_slot_2: any,
        next_discharge_slot_2: any,
    ):
        """Recalc sensor values if not already set"""
        self._inverter_mode_sonsor = mode_sensor
        # self._next_charge_slot_1_sensor = next_charge_slot_1
        # self._next_discharge_slot_1_sensor = next_discharge_slot_1
        # self._next_charge_slot_2_sensor = next_charge_slot_2
        # self._next_discharge_slot_2_sensor = next_discharge_slot_2

        # if (
        #     not self._next_charge_slot_1_sensor._date_time_value
        #     and not self._next_discharge_slot_1_sensor._date_time_value
        # ):
        #     await self.async_update_price_calculator()
        #     await self._next_charge_slot_1_sensor.async_update()
        #     await self._next_discharge_slot_1_sensor.async_update()
        #     await self._next_charge_slot_2_sensor.async_update()
        #     await self._next_discharge_slot_2_sensor.async_update()

    def calc_buy_price(self, buy_val: float) -> float:
        return round(
            buy_val * (1 + (self._config.data[CONF_VAT] / 100))
            + self._config.data[CONF_EXTRA_IMPORT],
            3,
        )

    def calc_sell_price(self, sell_val: float) -> float:
        return round(sell_val + self._config.data[CONF_EXTRA_EXPORT], 3)

    async def update_timevalues_from_dict(self, today_data: list, tomorrow_data: list):
        today_values = []
        self._raw_buy_today = []
        self._raw_sell_today = []

        for entry in today_data:
            if isinstance(entry["start"], str):
                start = parser.parse(entry["start"])
            else:
                start = entry["start"]

            if isinstance(entry["end"], str):
                end = parser.parse(entry["end"])
            else:
                end = entry["end"]
            value_raw = entry["value"]
            today_values.append(
                TimeValue(
                    start=start,
                    end=end,
                    value=self.calc_buy_price(value_raw),
                    sell_value=self.calc_sell_price(value_raw),
                )
            )
            self._raw_buy_today.append(
                {
                    "start": start,
                    "end": end,
                    "value": self.calc_buy_price(value_raw),
                }
            )
            self._raw_sell_today.append(
                {
                    "start": start,
                    "end": end,
                    "value": self.calc_sell_price(value_raw),
                }
            )
        tomorrow_values = []
        self._raw_buy_tomorrow = []
        self._raw_sell_tomorrow = []
        for entry in tomorrow_data:
            if isinstance(entry["start"], str):
                start = parser.parse(entry["start"])
            else:
                start = entry["start"]

            if isinstance(entry["end"], str):
                end = parser.parse(entry["end"])
            else:
                end = entry["end"]
            value_raw = entry["value"]
            tomorrow_values.append(
                TimeValue(
                    start=start,
                    end=end,
                    value=self.calc_buy_price(value_raw),
                    sell_value=self.calc_sell_price(value_raw),
                )
            )
            self._raw_buy_tomorrow.append(
                {
                    "start": start,
                    "end": end,
                    "value": self.calc_buy_price(value_raw),
                }
            )
            self._raw_sell_tomorrow.append(
                {
                    "start": start,
                    "end": end,
                    "value": self.calc_sell_price(value_raw),
                }
            )

        # await self.update_prices(today_values, tomorrow_values)
        self._schedule_today = self.get_schedule(
            today_values, self._hours_self_use, self._battery_use
        )
        if len(tomorrow_values) > 0:
            self._schedule_tomorrow = self.get_schedule(
                tomorrow_values, self._hours_self_use, self._battery_use, True
            )
        if self._inverter_mode_sonsor:
            await self._inverter_mode_sonsor.async_update()

    async def update_prices(
        self, today_prices: list[TimeValue], tomorrow_prices: list[TimeValue]
    ):
        beginning_of_hour = datetime.now(
            zoneinfo.ZoneInfo(key="Europe/Stockholm")
        ).replace(minute=0, second=0, microsecond=0) - timedelta(seconds=10)
        self._today_prices = today_prices
        self._tomorrow_prices = tomorrow_prices
        self._today_lowest_price = min(today_prices, key=lambda tv: tv.value)
        self._today_highest_price = max(today_prices, key=lambda tv: tv.value)
        if tomorrow_prices:
            all_avail_prices = [
                tv
                for tv in today_prices.__add__(tomorrow_prices)
                if tv.start > beginning_of_hour
            ]
            self._tomorrow_lowest_price = min(tomorrow_prices, key=lambda tv: tv.value)
            self._tomorrow_highest_price = min(tomorrow_prices, key=lambda tv: tv.value)
        else:
            all_avail_prices = [
                tv for tv in today_prices if tv.start > beginning_of_hour
            ]
            self._tomorrow_lowest_price = None
            self._tomorrow_highest_price = None
        ## TODO fix reading sensor values here.
        buy = self._battery_use
        charge_slot = None
        all_price_sorted = sorted(
            all_avail_prices, key=lambda tv: tv.value, reverse=True
        )
        charge_slots = []

        for tv in all_price_sorted:
            dis_charge_slot = tv
            ## Look for chargeslot before dischageslot.
            posible_charges = filter(
                lambda ch: (ch.value) < (dis_charge_slot.value + buy)
                and ch.start < dis_charge_slot.start,
                all_avail_prices,
            )
            if posible_charges:
                charge_slot = min(
                    posible_charges, key=lambda tv: tv.value, default=None
                )
                if charge_slot:
                    charge_slots.append(
                        {"dis_charge_slot": dis_charge_slot, "charge_slot": charge_slot}
                    )
            else:
                charge_slot = None
            # if charge_slot:
            #    break

        # charge_slot = min(
        #     filter(
        #         lambda ch: (ch.value + sell) < (dis_charge_slot.value + buy)
        #         and ch.start < dis_charge_slot.start,
        #         all_avail_prices,
        #     ),
        #     key=lambda tv: tv.value,
        # )
        charge_slots.sort(
            key=lambda cs: cs["dis_charge_slot"].sell_value - cs["charge_slot"].value,
            reverse=True,
        )

        best_charge_slot = charge_slots.pop(0)
        bcs = best_charge_slot["charge_slot"]
        bds = best_charge_slot["dis_charge_slot"]
        _LOGGER.info(
            f"Best Charge: {bcs.start} Discharge {bds.start} Buy {bcs.value} Sell {bds.sell_value} Diff {bds.sell_value - bcs.value}"
        )
        avail_charge_slots = []
        avail_charge_slots.append(best_charge_slot)
        for c in charge_slots:
            cs = c["charge_slot"]
            ds = c["dis_charge_slot"]
            # _LOGGER.info(
            #    f"Charge: {cs.start} Discharge {ds.start} Buy {cs.value} Sell {ds.sell_value} Diff {ds.sell_value - cs.value}"
            # )
            if cs.start >= bcs.start or cs.start <= bds.start:
                # _LOGGER.info("Skipping 1")
                continue
            if ds.start <= bcs.start or ds.start <= bds.start:
                # _LOGGER.info("Skipping 2")
                continue
            # _LOGGER.info("Adding")
            avail_charge_slots.append(c)

        for c in avail_charge_slots:
            cs = c["charge_slot"]
            ds = c["dis_charge_slot"]
            _LOGGER.info(
                f"Charge: {cs.start} Discharge {ds.start} Buy {cs.value} Sell {ds.sell_value} Diff {ds.sell_value - cs.value}"
            )

        if best_charge_slot:
            self._next_charge_slot1 = best_charge_slot["charge_slot"]
            self._next_discharge_slot1 = best_charge_slot["dis_charge_slot"]
            if self._next_charge_slot_1_sensor:
                await self._next_charge_slot_1_sensor.async_update()
            if self._next_discharge_slot_1_sensor:
                await self._next_discharge_slot_1_sensor.async_update()

        look_for_2_slots = False

        if len(avail_charge_slots) >= 2 and look_for_2_slots:
            second_charge = avail_charge_slots.pop(1)
            self._next_charge_slot2 = second_charge["charge_slot"]
            self._next_discharge_slot2 = second_charge["dis_charge_slot"]
            await self._next_charge_slot_2_sensor.async_update()
            await self._next_discharge_slot_2_sensor.async_update()

        self._all_avail_lowest_price = min(
            all_avail_prices,
            key=lambda tv: tv.value,
        )
        self._all_avail_highest_price = max(
            all_avail_prices,
            key=lambda tv: tv.value,
        )

    MinMaxValue = namedtuple("MinMaxValue", ["start", "value", "sell_value", "t"])

    def find_min_max(self, prices: list[TimeValue], DELTA):
        mn, mx = math.inf, -math.inf
        minpeaks = []
        maxpeaks = []
        lookformax = True
        start = True
        # Iterate over items in series
        for time in prices:
            value = time.value
            time_pos = time.start
            if value > mx:
                mx = value
                mx_sell = time.sell_value
                mxpos = time_pos
            if value < mn:
                mn = value
                mn_sell = time.sell_value
                mnpos = time_pos
            if lookformax:
                if value < mx - DELTA:
                    # a local maxima
                    if prices[0].start != mxpos:
                        maxpeaks.append(self.MinMaxValue(mxpos, mx, mx_sell, "max"))
                    mn = value
                    mn_sell = time.sell_value
                    mnpos = time_pos
                    lookformax = False
                elif start:
                    # a local minima at beginning
                    # minpeaks.append((mnpos, mn))
                    mx = value
                    mx_sell = time.sell_value
                    mxpos = time_pos
                    start = False
            else:
                if value > mn + DELTA:
                    # a local minima
                    minpeaks.append(self.MinMaxValue(mnpos, mn, mn_sell, "min"))
                    mx = value
                    mx_sell = time.sell_value
                    mxpos = time_pos
                    lookformax = True
        # check for extrema at end
        # if value > mn+DELTA:
        # maxpeaks.append((mxpos, mx))
        # elif value < mx-DELTA:
        # minpeaks.append((mnpos, mn))
        if not any(minpeaks):
            minval = self.get_value_min(prices)
            minpeaks.append(
                self.MinMaxValue(minval.start, minval.value, minval.sell_value, "min")
            )
        return minpeaks, maxpeaks

    def filter_min_max(
        self,
        minpeaks: list,
        maxpeaks: list,
        batterycost: float,
        prices: list[TimeValue],
    ):
        peaks = []
        valid_peaks = []
        peaks.extend(minpeaks)
        peaks.extend(maxpeaks)
        prev_peak = None
        next_min = True
        for peak in sorted(peaks, key=lambda t: t.start, reverse=False):
            if peak.t == "min" and next_min:
                next_min = False
                prev_peak = peak
            elif peak.t == "max" and not next_min:
                if peak.sell_value > (prev_peak.value + batterycost):
                    valid_peaks.append(prev_peak)
                    valid_peaks.append(peak)
                next_min = True
                prev_peak = peak
            elif peak.t == "max" and next_min:
                # Vi har en topp utan en dal före kolla om det finns en dal före
                # som är tillräckligt låg
                pricesfiltered = filter(lambda x: x.start < peak.start, prices)
                minval = self.get_value_min(pricesfiltered)
                if peak.sell_value > (minval.value + batterycost):
                    valid_peaks.append(
                        self.MinMaxValue(
                            minval.start, minval.value, minval.sell_value, "min"
                        )
                    )
                    valid_peaks.append(peak)
        # Om vi inte hittat en dal/topp så tar
        # vi bara ut högsta priset och lägsta som topp/dal om det finns tillräcklig skillnad
        if len(valid_peaks) == 0:
            valid_peaks = []
            maxval = self.get_value_max(prices)
            maxpeak = self.MinMaxValue(
                maxval.start, maxval.value, maxval.sell_value, "max"
            )
            pricesfiltered = filter(lambda x: x.start < maxval.start, prices)
            minval = self.get_value_min(pricesfiltered)
            if minval:
                minpeak = self.MinMaxValue(
                    minval.start, minval.value, minval.sell_value, "min"
                )

                if maxpeak.sell_value > (minpeak.value + batterycost):
                    valid_peaks.append(minpeak)
                    valid_peaks.append(maxpeak)
        return valid_peaks

    def get_sell_max(self, prices: list[TimeValue]):
        return max(prices, key=lambda tv: tv.sell_value)

    def get_value_min(self, prices: list[TimeValue]):
        return min(prices, key=lambda tv: tv.value)

    def get_value_max(self, prices: list[TimeValue]):
        return max(prices, key=lambda tv: tv.value)

    def get_n_high_val(self, prices: list[TimeValue], nvalue: int):
        sorted_prices = sorted(prices, key=lambda pr: pr.value, reverse=True)
        return sorted_prices[nvalue - 1].value

    class no_matching_min_max_slots_error(Exception):
        def __init__(self, message):
            super().__init__(message)

    def chunk_list(self, lst, chunk_size):
        return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]

    def create_schedule(
        self,
        prices: list[TimeValue],
        validpeaks: list,
        selfuse_hours: int,
        is_tomorrow=False,
    ):
        _selfuse_hours = selfuse_hours
        _charge_hours = self._charge_hours
        if not _selfuse_hours:
            _selfuse_hours = 1
        # Loop throw prices per day and create a schedule
        for chunk in self.chunk_list(prices, 24):
            sell_max = self.get_sell_max(chunk).sell_value
            if is_tomorrow:
                self._sell_tomorrow_max = sell_max
            else:
                self._sell_today_max = sell_max
            _LOGGER.info(f"Sell Max = {sell_max}")

            selfuse_max = self.get_n_high_val(chunk, _selfuse_hours)
            selfuse_peak = self.get_value_max(chunk).value
            if is_tomorrow:
                self._selfuse_tomorrow_max = selfuse_max
            else:
                self._selfuse_today_max = selfuse_max
            _LOGGER.info(f"Selfuse Max = {selfuse_max} Selfuse Peak = {selfuse_peak}")

            next_midnight = chunk[0].start.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)
            schedule = []
            sel_prices = []
            # Vi tillåter 2 cyklingar på batteriet
            # Kolla så var min och max efter varandra i rätt följd
            prev_peak = None
            cycle_no = 1
            next_min = True
            peaks = sorted(
                filter(lambda x: x.start < next_midnight, validpeaks),
                key=lambda t: t.start,
                reverse=False,
            )
            if len(peaks) > 2:
                limit_search = peaks[2].start
                _selfuse_hours = _selfuse_hours * 2
                selfuse_max = self.get_n_high_val(chunk, _selfuse_hours)
                if is_tomorrow:
                    self._selfuse_tomorrow_max = selfuse_max
                else:
                    self._selfuse_today_max = selfuse_max
                _LOGGER.info(
                    f"More than 2 peaks found Limit search = {limit_search} Selfuse hours = {_selfuse_hours} Selfuse Max = {selfuse_max} Selfuse Peak = {selfuse_peak}"
                )
            else:
                limit_search = next_midnight
                _LOGGER.info(f"2 or less peaks found Limit search = {limit_search}")

            for peak in peaks:
                if peak.t == "min" and next_min:
                    next_min = False
                    prev_peak = peak
                    sel_prices = []
                elif peak.t == "max" and not next_min:
                    next_min = True
                    sel_prices = [
                        tv
                        for tv in chunk
                        # TODO: Kika på om vi skall titta priser in på nästa dygn också för att hitta nästa dal
                        if tv.start >= prev_peak.start
                        and tv.start <= limit_search  # and tv.start <= peak.start
                    ]
                    cycle_no = cycle_no + 1
                    prev_peak = peak

                limit_search = next_midnight
                if len(sel_prices) > 0:
                    # Första priset = det längsta eftersom vi sorterat
                    # används för Laddning
                    selfuse_counter = 0
                    charge = sel_prices[0]
                    charge.mode = "Charge"
                    sel_prices.remove(sel_prices[0])
                    if not any(x.start == charge.start for x in schedule):
                        schedule.append(charge)

                    sorted_sel_prices = sorted(
                        sel_prices, key=lambda tv: tv.value, reverse=True
                    )

                    if selfuse_max > sell_max:
                        _LOGGER.info("Selfuse max is higher than sell max")
                        for p in sorted_sel_prices:
                            if p.value > sell_max and selfuse_counter < _selfuse_hours:
                                p.mode = "Selfuse"
                                selfuse_counter = selfuse_counter + 1
                            else:
                                p.mode = "Standby"
                            if not any(x.start == p.start for x in schedule):
                                schedule.append(p)
                    else:
                        _LOGGER.info("Sell max is higher than selfuse max")
                        sell = sorted_sel_prices[0]
                        sorted_sel_prices.remove(sorted_sel_prices[0])
                        sell.mode = "Sell"
                        if not any(x.start == sell.start for x in schedule):
                            schedule.append(sell)
                        for p in sorted_sel_prices:
                            if p.value > sell_max and selfuse_counter < _selfuse_hours:
                                p.mode = "Selfuse"
                                selfuse_counter = selfuse_counter + 1
                            else:
                                p.mode = "Standby"
                            # Check if value already exsists
                            if not any(x.start == p.start for x in schedule):
                                schedule.append(p)

            schedule = self.fill_empty_schedule(prices, schedule)

            # Add additional charging hours if charge hours are more than 1

            if _charge_hours and _charge_hours > 1:
                # Get charge hour from schedule
                charges = [tv for tv in schedule if tv.mode == "Charge"]
                use_hours = sorted(
                    [
                        tv
                        for tv in schedule
                        if tv.mode == "Selfuse" or tv.mode == "Sell"
                    ],
                    key=lambda tv: tv.start,
                )
                for i in sorted(charges, key=lambda c: c.start):
                    # Get next selfuse or sell hour
                    _LOGGER.info(f"Charge hour {i.start}")
                    # Get prev hour for sell och selfuse if any
                    sorted_usehours = sorted(use_hours, key=lambda s: s.start)
                    prev_use_hour = next(
                        (tv for tv in sorted_usehours if tv.start < i.start),
                        None,
                    )
                    next_use_hour = next(
                        (tv for tv in sorted_usehours if tv.start > i.start),
                        None,
                    )
                    if prev_use_hour:
                        _LOGGER.info(
                            f"Prev hour {prev_use_hour.start} {prev_use_hour.mode}"
                        )
                        min_charges = sorted(
                            [
                                tv
                                for tv in schedule
                                if tv.start > prev_use_hour.start
                                and tv.start < next_use_hour.start
                                and tv.mode != "Charge"
                            ],
                            key=lambda tv: tv.value,
                            reverse=False,
                        )
                    else:
                        _LOGGER.info(
                            f"Next hour {next_use_hour.start} {next_use_hour.mode}"
                        )
                        min_charges = sorted(
                            [
                                tv
                                for tv in schedule
                                if tv.start < next_use_hour.start
                                and tv.mode != "Charge"
                            ],
                            key=lambda tv: tv.value,
                            reverse=False,
                        )
                    # Log schedule
                    counter = _charge_hours - 1
                    _LOGGER.info(f"Charge counter {counter}")
                    # change standby to charge for correct amount of hours
                    for tv in min_charges:
                        if counter >= 1:
                            _LOGGER.info(f"Charge hour {tv.start}")
                            tv.mode = "Charge"
                            counter = counter - 1
                            if counter == 0:
                                break
        # for tv in sorted(schedule, key=lambda s: s.start):
        #    _LOGGER.info(f"Scedule: {tv.start} {tv.mode} {tv.value} {tv.sell_value}")
        return schedule

    def fill_empty_schedule(self, prices: list[TimeValue], schedule: list[TimeValue]):
        for p in prices:
            if not any(x.start == p.start for x in schedule):
                p.mode = "Standby"
                schedule.append(p)
        return schedule

    def get_schedule(
        self,
        prices: list[TimeValue],
        hours_for_self_use: int,
        battery_cost: float,
        is_tomorrow=False,
    ):
        # Hitta alla toppar och dalar
        minpeaks, maxpeaks = self.find_min_max(prices, DELTA=0.1)
        _LOGGER.info(f"Own Minima: {len(minpeaks)}, Maxima: {len(maxpeaks)}")
        for max_point in maxpeaks:
            _LOGGER.info(f"Max Time: {max_point.start}, Value: {max_point.value:.2f}")
        for min_point in minpeaks:
            _LOGGER.info(f"Min Time: {min_point.start}, Value: {min_point.value:.2f}")
        # maxima, minima = self.find_timevalue_extrema(prices, prominence=0.2)
        # _LOGGER.info(f"SciPy Maxima: {len(maxima)}, Minima: {len(minima)}")
        # for max_point in maxima:
        #     _LOGGER.info(f"Max Time: {max_point.start}, Value: {max_point.value:.2f}")
        # for min_point in minima:
        #     _LOGGER.info(f"Min Time: {min_point.start}, Value: {min_point.value:.2f}")
        # Filtrera resultatet så vi bara har giltliga toppar/dalar dvs en topp
        # föregås av en dal som ger "tillräcklig besparing" och verifiera att
        # vi verkligen hittat en topp/dal
        validpeaks = self.filter_min_max(minpeaks, maxpeaks, battery_cost, prices)
        # Leta upp sälj max timmen dvs högsta timmen för att sälja.
        # sellmax = self.get_sell_max(prices)
        # self._sell_today_max = sellmax.sell_value
        # _LOGGER.info(f"Sell Max = {sellmax}")
        # Leta upp ett antal timmar (enligt parametern hours_for_self_use) där
        # priset ligger som högst
        # selfuse_max = self.get_n_high_val(prices, hours_for_self_use)
        # self._selfuse_today_max = selfuse_max
        # _LOGGER.info(f"Selfuse Max = {selfuse_max}")
        # Börja med att kontrollera att vi har peak värden som matchar
        # varandra (dal följs av topp)
        #
        schedule = self.create_schedule(
            prices,
            validpeaks,  # sellmax.sell_value, selfuse_max,
            hours_for_self_use,
            is_tomorrow,
        )
        # Fyll på med Standby på alla timmar som inte har något annat state
        # schedule = self.fill_empty_schedule(prices, schedule)
        return sorted(schedule, key=lambda s: s.start)

    # def find_timevalue_extrema(
    #     self, data: List[TimeValue], prominence: float = None, distance: int = None
    # ) -> Tuple[List[TimeValue], List[TimeValue]]:
    #     """
    #     Find local maxima and minima in a list of TimeValue objects.

    #     Parameters:
    #     -----------
    #     data : List[TimeValue]
    #         List of TimeValue objects
    #     prominence : float, optional
    #         Required prominence of peaks
    #     distance : int, optional
    #         Minimum number of samples between peaks

    #     Returns:
    #     --------
    #     Tuple[List[TimeValue], List[TimeValue]]:
    #         (maxima_timevalues, minima_timevalues)
    #     """
    #     # Extract values for analysis
    #     values = np.array([tv.value for tv in data])

    #     # Find maxima
    #     maxima_indices, _ = find_peaks(values, prominence=prominence, distance=distance)

    #     # Find minima by inverting the signal
    #     minima_indices, _ = find_peaks(
    #         -values, prominence=prominence, distance=distance
    #     )

    #     # Get TimeValue objects for maxima and minima
    #     maxima = [data[i] for i in maxima_indices]
    #     minima = [data[i] for i in minima_indices]

    #     return maxima, minima
