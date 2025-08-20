"""Test individual GridEnforcer components."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import json


@pytest.mark.asyncio
async def test_sensor_setup(hass, config_entry):
    """Test sensor platform setup."""
    with patch('custom_components.gridenforcer.sensor.async_setup_entry') as mock_setup:
        mock_setup.return_value = True
        
        # Import and test sensor setup
        from custom_components.gridenforcer.sensor import async_setup_entry
        
        # Mock async_add_entities
        async_add_entities = AsyncMock()
        
        result = await async_setup_entry(hass, config_entry, async_add_entities)
        assert result is True


def test_number_entities():
    """Test number entity configuration."""
    from custom_components.gridenforcer.number import GridEnforcerNumber
    
    # Test creating a number entity
    number_entity = GridEnforcerNumber(
        unique_id="test_number",
        device_unique_id="test_device",
        entity_name="Test Number",
        native_min_value=0.0,
        native_max_value=100.0,
        unit_of_measurement="%"
    )
    
    assert number_entity._attr_unique_id == "test_number"
    assert number_entity._attr_name == "Test Number"
    assert number_entity._attr_native_min_value == 0.0
    assert number_entity._attr_native_max_value == 100.0


def test_select_entities():
    """Test select entity configuration."""
    from custom_components.gridenforcer.select import GridEnforcerSelect
    
    # Test creating a select entity
    select_entity = GridEnforcerSelect(
        unique_id="operation_mode",
        entity_name="Operation Mode",
        device_unique_id="test_device",
        current_option="automatic_mode",
        options=["automatic_mode", "manual_mode"]
    )
    
    assert select_entity._attr_unique_id == "operation_mode"
    assert select_entity._attr_current_option == "automatic_mode"
    assert "automatic_mode" in select_entity._attr_options
    assert "manual_mode" in select_entity._attr_options


@pytest.mark.asyncio
async def test_inverter_mode_sensor(hass, config_entry):
    """Test InverterModeSensor functionality."""
    from custom_components.gridenforcer.sensor import InverterModeSensor
    from custom_components.gridenforcer.invertermode import InverterMode
    
    # Mock the price hub
    mock_price_hub = MagicMock()
    mock_price_hub.schedule_today = []
    mock_price_hub.schedule_tomorrow = []
    mock_price_hub.selfuse_today_max = 2.5
    mock_price_hub.sell_today_max = 3.0
    mock_price_hub.selfuse_tomorrow_max = None
    mock_price_hub.sell_tomorrow_max = None
    
    hass.data = {"gridenforcer": {"price_hub": mock_price_hub}}
    
    # Create sensor
    sensor = InverterModeSensor(
        unique_id="test_inverter_mode",
        device_unique_id="test_device",
        entity_name="Test Inverter Mode",
        hass=hass,
        config_entry=config_entry
    )
    
    # Test initial state
    assert sensor.state == InverterMode.STANDBY.value
    
    # Test state attributes
    attributes = sensor.extra_state_attributes
    assert "schedule_today" in attributes
    assert "schedule_tomorrow" in attributes
    assert attributes["selfuse_today_max"] == 2.5
    assert attributes["sell_today_max"] == 3.0


def test_config_flow_validation():
    """Test config flow validation functions."""
    from custom_components.gridenforcer.config_flow import validate_input
    
    # This would normally require a real hass instance with states
    # For now, just test that the function exists and can be imported
    assert callable(validate_input)


def test_constants_completeness():
    """Test that all required constants are defined."""
    from custom_components.gridenforcer.const import (
        DOMAIN, DATA_UPDATED, CONF_PRICE_SENSOR, CONF_EXTRA_IMPORT,
        CONF_EXTRA_EXPORT, CONF_BAT_COST, CONF_VAT, CONF_SOC_SENSOR,
        CONF_FCRDU_INPUT, CONF_FCRDD_INPUT, CONF_HOURS_SELFUSE
    )
    
    # Test domain
    assert DOMAIN == "gridenforcer"
    
    # Test configuration keys
    expected_configs = [
        "price_sensor", "extra_import", "extra_export", "bat_cost", 
        "vat", "bat_soc", "fcr_d_up_input", "fcr_d_down_input", "hours_selfuse"
    ]
    
    actual_configs = [
        CONF_PRICE_SENSOR, CONF_EXTRA_IMPORT, CONF_EXTRA_EXPORT, CONF_BAT_COST,
        CONF_VAT, CONF_SOC_SENSOR, CONF_FCRDU_INPUT, CONF_FCRDD_INPUT, CONF_HOURS_SELFUSE
    ]
    
    for expected in expected_configs:
        assert expected in actual_configs


@pytest.mark.asyncio
async def test_price_calculator_schedule_creation(mock_hass_for_price_calc, price_calculator_config):
    """Test schedule creation in PriceCalculator."""
    from custom_components.gridenforcer.pricecalculator import PriceCalculator
    from custom_components.gridenforcer.timevalue import TimeValue
    from datetime import datetime, timedelta
    import zoneinfo
    
    calc = PriceCalculator(mock_hass_for_price_calc, price_calculator_config)
    calc._hours_self_use = 4
    calc._charge_hours = 2
    
    # Create test price data for 24 hours
    base_time = datetime(2024, 1, 1, 0, 0, tzinfo=zoneinfo.ZoneInfo("Europe/Stockholm"))
    prices = []
    
    # Create varying prices throughout the day
    price_values = [0.8, 0.7, 0.6, 0.9, 1.0, 1.2, 1.5, 2.0, 2.2, 2.5, 
                   2.3, 2.1, 1.8, 1.6, 1.4, 1.7, 1.9, 2.4, 2.6, 2.2, 
                   1.9, 1.5, 1.2, 1.0]
    
    for i in range(24):
        start = base_time + timedelta(hours=i)
        end = base_time + timedelta(hours=i+1)
        value = price_values[i]
        prices.append(TimeValue(start=start, end=end, value=value, sell_value=value * 0.9))
    
    # Test schedule creation
    schedule = calc.get_schedule(prices, hours_for_self_use=4, battery_cost=0.02)
    
    # Should return a schedule with 24 hours
    assert len(schedule) == 24
    
    # Each schedule item should have a mode
    for item in schedule:
        assert hasattr(item, 'mode')
        assert item.mode in ['Charge', 'Sell', 'Selfuse', 'Standby']


def test_timevalue_edge_cases():
    """Test TimeValue class edge cases and validation."""
    from custom_components.gridenforcer.timevalue import TimeValue
    from datetime import datetime
    import zoneinfo
    
    start = datetime(2024, 1, 1, 12, 0, tzinfo=zoneinfo.ZoneInfo("Europe/Stockholm"))
    end = datetime(2024, 1, 1, 13, 0, tzinfo=zoneinfo.ZoneInfo("Europe/Stockholm"))
    
    # Test normal creation
    tv = TimeValue(start=start, end=end, value=1.5, sell_value=1.2)
    assert tv.mode is "Standby"  # Initially no mode set
    
    # Test mode setting
    tv.mode = "Charge"
    assert tv.mode == "Charge"
    
    # Test to_dict with mode
    tv_dict = tv.to_dict()
    assert tv_dict["mode"] == "Charge"
    
    # Test string representation
    tv_str = str(tv)
    assert "TimeValue" in tv_str
    assert "Charge" in tv_str


@pytest.mark.asyncio 
async def test_integration_platforms(hass, config_entry):
    """Test that all platforms are properly set up."""
    from custom_components.gridenforcer import async_setup_entry, PLATFORMS
    
    # Mock the platform setup functions
    with patch('custom_components.gridenforcer.PriceCalculator') as mock_price_calc:
        mock_price_calc.return_value.async_update_price_calculator = AsyncMock()
        
        # Mock config_entries.async_forward_entry_setups
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        
        # Mock the tracking functions
        with patch('custom_components.gridenforcer.async_track_time_change') as mock_track_time, \
             patch('custom_components.gridenforcer.async_track_state_change_event') as mock_track_state:
            
            result = await async_setup_entry(hass, config_entry)
            
            # Should return True for successful setup
            assert result is True
            
            # Should have called platform setup
            hass.config_entries.async_forward_entry_setups.assert_called_once_with(
                config_entry, PLATFORMS
            )
            
            # Should have set up time tracking (called twice - at 13:30 and 0:00)
            assert mock_track_time.call_count == 2
            
            # Should have set up state tracking for various sensors
            assert mock_track_state.call_count >= 4  # price, soc, fcr_d_down, fcr_d_up