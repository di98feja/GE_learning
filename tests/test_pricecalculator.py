"""Test PriceCalculator functionality."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import zoneinfo


@pytest.fixture
def mock_hass_for_price_calc():
    """Mock Home Assistant for PriceCalculator tests."""
    hass = MagicMock()
    hass.states = MagicMock()
    
    # Mock number entities that PriceCalculator reads
    mock_selfuse_state = MagicMock()
    mock_selfuse_state.state = "4"
    
    mock_charge_state = MagicMock()
    mock_charge_state.state = "2"
    
    def get_state_side_effect(entity_id):
        if entity_id == "number.gridenforcer_selfuse_hours":
            return mock_selfuse_state
        elif entity_id == "number.gridenforcer_charge_hours":
            return mock_charge_state
        elif entity_id == "number.gridenforcer_soc_backup":
            mock_soc_backup = MagicMock()
            mock_soc_backup.state = "20.0"
            return mock_soc_backup
        elif entity_id == "number.gridenforcer_soc_max":
            mock_soc_max = MagicMock()
            mock_soc_max.state = "80.0" 
            return mock_soc_max
        elif entity_id == "sensor.electricity_price":
            mock_price_sensor = MagicMock()
            mock_price_sensor.state = "1.25"
            mock_price_sensor.attributes = {
                "raw_today": [
                    {
                        "start": "2024-01-01T00:00:00+01:00",
                        "end": "2024-01-01T01:00:00+01:00",
                        "value": 1.0
                    }
                ],
                "raw_tomorrow": []
            }
            return mock_price_sensor
        return None
    
    hass.states.get.side_effect = get_state_side_effect
    return hass


def test_price_calculator_init(mock_hass_for_price_calc, price_calculator_config):
    """Test PriceCalculator initialization."""
    from custom_components.gridenforcer.pricecalculator import PriceCalculator
    
    calc = PriceCalculator(mock_hass_for_price_calc, price_calculator_config)
    
    assert calc._config == price_calculator_config
    assert calc._hass == mock_hass_for_price_calc
    assert calc._battery_use == 0.02


def test_calc_buy_price(mock_hass_for_price_calc, price_calculator_config):
    """Test buy price calculation with VAT and import fees."""
    from custom_components.gridenforcer.pricecalculator import PriceCalculator
    
    calc = PriceCalculator(mock_hass_for_price_calc, price_calculator_config)
    
    # Test calculation: price * (1 + VAT/100) + import_fee
    # 1.0 * (1 + 25/100) + 0.15 = 1.0 * 1.25 + 0.15 = 1.40
    buy_price = calc.calc_buy_price(1.0)
    expected = round(1.0 * 1.25 + 0.15, 3)
    
    assert buy_price == expected


def test_calc_sell_price(mock_hass_for_price_calc, price_calculator_config):
    """Test sell price calculation with export compensation."""
    from custom_components.gridenforcer.pricecalculator import PriceCalculator
    
    calc = PriceCalculator(mock_hass_for_price_calc, price_calculator_config)
    
    # Test calculation: price + export_compensation
    # 1.0 + 0.05 = 1.05
    sell_price = calc.calc_sell_price(1.0)
    expected = round(1.0 + 0.05, 3)
    
    assert sell_price == expected


def test_time_value_creation():
    """Test TimeValue class functionality."""
    from custom_components.gridenforcer.timevalue import TimeValue
    from datetime import datetime
    
    start = datetime(2024, 1, 1, 12, 0, tzinfo=zoneinfo.ZoneInfo("Europe/Stockholm"))
    end = datetime(2024, 1, 1, 13, 0, tzinfo=zoneinfo.ZoneInfo("Europe/Stockholm"))
    
    tv = TimeValue(start=start, end=end, value=1.5, sell_value=1.2)
    
    assert tv.start == start
    assert tv.end == end
    assert tv.value == 1.5
    assert tv.sell_value == 1.2
    
    # Test to_dict method
    tv_dict = tv.to_dict()
    assert tv_dict["start"] == start
    assert tv_dict["end"] == end
    assert tv_dict["value"] == 1.5
    assert tv_dict["sell_value"] == 1.2


@pytest.mark.asyncio
async def test_async_update_price_calculator(mock_hass_for_price_calc, price_calculator_config):
    """Test async price calculator update."""
    from custom_components.gridenforcer.pricecalculator import PriceCalculator
    
    calc = PriceCalculator(mock_hass_for_price_calc, price_calculator_config)
    
    # Mock the price sensor state - ADD THIS SECTION
    mock_price_state = MagicMock()
    mock_price_state.state = "1.25"
    mock_price_state.attributes = {
        "raw_today": [{"start": "2024-01-01T00:00:00+01:00", "end": "2024-01-01T01:00:00+01:00", "value": 1.0}],
        "raw_tomorrow": []
    }
    mock_hass_for_price_calc.states.get.return_value = mock_price_state
        
    # Test that the method can be called without errors
    with patch.object(calc, 'update_timevalues_from_dict', new_callable=AsyncMock) as mock_update:
        await calc.async_update_price_calculator()
        
        # Verify that update_timevalues_from_dict was called
        assert mock_update.called, "update_timevalues_from_dict should have been called"


def test_inverter_mode_enum_values():
    """Test all InverterMode enum values."""
    from custom_components.gridenforcer.invertermode import InverterMode
    
    # Test all enum values from the actual file
    assert InverterMode.FCRDD.value == "Fcr-d down"
    assert InverterMode.FCRDU.value == "Fcr-d up"
    assert InverterMode.FULLYCHARGED.value == "Standby fully charged"
    assert InverterMode.STANDBY.value == "Standby"
    assert InverterMode.BACKUPSOC.value == "Standby backup soc"
    assert InverterMode.CHARGING.value == "Charging"
    assert InverterMode.DISCHARGING.value == "Discharging"
    assert InverterMode.CHARGESOC.value == "Charging to keep backup soc"
    assert InverterMode.FAULT.value == "Fault"
    assert InverterMode.SELFUSE.value == "Selfuse"


def test_n_high_val_calculation(mock_hass_for_price_calc, price_calculator_config):
    """Test get_n_high_val method for price ranking."""
    from custom_components.gridenforcer.pricecalculator import PriceCalculator
    from custom_components.gridenforcer.timevalue import TimeValue
    from datetime import datetime
    
    calc = PriceCalculator(mock_hass_for_price_calc, price_calculator_config)
    
    # Create test price data
    base_time = datetime(2024, 1, 1, 0, 0, tzinfo=zoneinfo.ZoneInfo("Europe/Stockholm"))
    prices = []
    
    # Create 5 TimeValue objects with different prices
    for i in range(5):
        start = base_time.replace(hour=i)
        end = base_time.replace(hour=i+1)
        value = float(i + 1)  # Prices: 1.0, 2.0, 3.0, 4.0, 5.0
        prices.append(TimeValue(start=start, end=end, value=value, sell_value=value))
    
    # Test getting the 3rd highest price (should be 3.0 when sorted high to low)
    third_highest = calc.get_n_high_val(prices, 3)
    assert third_highest == 3.0
    
    # Test getting the highest price
    highest = calc.get_n_high_val(prices, 1)
    assert highest == 5.0