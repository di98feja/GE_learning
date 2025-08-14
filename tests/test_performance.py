"""Performance and load tests for GridEnforcer."""
import pytest
import time
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
import zoneinfo


@pytest.mark.asyncio
async def test_price_calculator_performance():
    """Test PriceCalculator performance with large datasets."""
    from custom_components.gridenforcer.pricecalculator import PriceCalculator
    from custom_components.gridenforcer.timevalue import TimeValue
    
    # Mock setup
    hass = MagicMock()
    hass.states.get.return_value = None
    
    config = MagicMock()
    config.data = {
        "price_sensor": "sensor.test",
        "extra_import": 0.15,
        "extra_export": 0.05,
        "vat": 25.0,
        "bat_cost": 0.02,
        "hours_selfuse": 4.0
    }
    
    calc = PriceCalculator(hass, config)
    calc._hours_self_use = 4
    calc._charge_hours = 2
    
    # Create large price dataset (168 hours = 1 week)
    base_time = datetime(2024, 1, 1, 0, 0, tzinfo=zoneinfo.ZoneInfo("Europe/Stockholm"))
    prices = []
    
    start_time = time.time()
    
    # Generate 168 hours of price data
    for i in range(168):
        start = base_time + timedelta(hours=i)
        end = base_time + timedelta(hours=i+1)
        # Simulate realistic price variation
        value = 1.0 + 0.5 * (i % 24) / 24 + 0.2 * (i % 7) / 7
        prices.append(TimeValue(start=start, end=end, value=value, sell_value=value * 0.9))
    
    data_generation_time = time.time() - start_time
    
    # Test schedule generation performance
    start_time = time.time()
    
    # Process in 24-hour chunks (as the real system does)
    for day in range(7):
        daily_prices = prices[day*24:(day+1)*24]
        schedule = calc.get_schedule(daily_prices, hours_for_self_use=4, battery_cost=0.02)
        assert len(schedule) == 24
    
    processing_time = time.time() - start_time
    
    print(f"Data generation time: {data_generation_time:.3f}s")
    print(f"Processing time: {processing_time:.3f}s")
    print(f"Processing rate: {168/processing_time:.1f} hours/second")
    
    # Performance assertions
    assert data_generation_time < 0.1, "Data generation should be fast"
    assert processing_time < 2.0, "Processing 7 days should take less than 2 seconds"


@pytest.mark.asyncio
async def test_concurrent_price_updates():
    """Test concurrent price calculator updates."""
    from custom_components.gridenforcer.pricecalculator import PriceCalculator
    
    # Mock setup
    hass = MagicMock()
    hass.states.get.return_value = None
    
    config = MagicMock()
    config.data = {
        "price_sensor": "sensor.test",
        "extra_import": 0.15,
        "extra_export": 0.05,
        "vat": 25.0,
        "bat_cost": 0.02,
        "hours_selfuse": 4.0
    }
    
    calc = PriceCalculator(hass, config)
    
    # Mock the update method to simulate work
    async def mock_update():
        await asyncio.sleep(0.01)  # Simulate some work
        return True
    
    calc.update_timevalues_from_dict = mock_update
    
    start_time = time.time()
    
    # Run multiple concurrent updates
    tasks = []
    for i in range(10):
        task = asyncio.create_task(calc.async_update_price_calculator())
        tasks.append(task)
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    elapsed_time = time.time() - start_time
    
    # Check that all tasks completed successfully
    assert len(results) == 10
    for result in results:
        assert not isinstance(result, Exception)
    
    # Should complete concurrently, not sequentially
    assert elapsed_time < 0.5, f"Concurrent execution took {elapsed_time:.3f}s"
    
    print(f"10 concurrent updates completed in {elapsed_time:.3f}s")


def test_memory_usage_price_data():
    """Test memory efficiency with large price datasets."""
    from custom_components.gridenforcer.timevalue import TimeValue
    from datetime import datetime, timedelta
    import sys
    import zoneinfo
    
    base_time = datetime(2024, 1, 1, 0, 0, tzinfo=zoneinfo.ZoneInfo("Europe/Stockholm"))
    
    # Measure memory usage of TimeValue objects
    prices = []
    
    # Create 1000 TimeValue objects
    for i in range(1000):
        start = base_time + timedelta(hours=i)
        end = base_time + timedelta(hours=i+1)
        tv = TimeValue(start=start, end=end, value=float(i), sell_value=float(i) * 0.9)
        prices.append(tv)
    
    # Rough memory usage check (TimeValue should be lightweight)
    size_per_object = sys.getsizeof(prices[0])
    total_size = sys.getsizeof(prices) + len(prices) * size_per_object
    
    print(f"Memory per TimeValue: {size_per_object} bytes")
    print(f"Total memory for 1000 objects: {total_size / 1024:.1f} KB")
    
    # TimeValue objects should be memory efficient
    assert size_per_object < 1000, "TimeValue objects should be under 1KB each"
    assert total_size < 100 * 1024, "1000 TimeValue objects should use less than 100KB"


@pytest.mark.asyncio
async def test_sensor_update_performance():
    """Test sensor update performance."""
    from custom_components.gridenforcer.sensor import InverterModeSensor
    from custom_components.gridenforcer.invertermode import InverterMode
    
    # Mock setup
    hass = MagicMock()
    mock_price_hub = MagicMock()
    mock_price_hub.schedule_today = []
    mock_price_hub.schedule_tomorrow = []
    mock_price_hub.selfuse_today_max = 2.5
    mock_price_hub.sell_today_max = 3.0
    
    hass.data = {"gridenforcer": {"price_hub": mock_price_hub}}
    
    config_entry = MagicMock()
    
    # Create sensor
    sensor = InverterModeSensor(
        unique_id="test_sensor",
        device_unique_id="test_device", 
        entity_name="Test Sensor",
        hass=hass,
        config_entry=config_entry
    )
    
    # Initialize sensor state
    sensor._state = InverterMode.STANDBY
    
    # Test multiple rapid updates
    start_time = time.time()
    
    for i in range(100):
        await sensor.async_update()
        # Verify state is consistent
        assert sensor.state == InverterMode.STANDBY.value
    
    elapsed_time = time.time() - start_time
    
    print(f"100 sensor updates completed in {elapsed_time:.3f}s")
    print(f"Update rate: {100/elapsed_time:.1f} updates/second")
    
    # Should handle rapid updates efficiently
    assert elapsed_time < 1.0, "100 sensor updates should complete in under 1 second"


def test_price_calculation_accuracy():
    """Test price calculation accuracy with edge cases."""
    from custom_components.gridenforcer.pricecalculator import PriceCalculator
    
    # Mock setup
    hass = MagicMock()
    config = MagicMock()
    config.data = {
        "extra_import": 0.15,
        "extra_export": 0.05,
        "vat": 25.0,
        "bat_cost": 0.02
    }
    
    calc = PriceCalculator(hass, config)
    
    # Test edge cases
    test_cases = [
        (0.0, 0.15),      # Zero price
        (0.001, 0.151),   # Very small price
        (10.0, 12.65),    # High price
        (-0.1, 0.025),    # Negative price (can happen in markets)
    ]
    
    for input_price, expected_buy in test_cases:
        buy_price = calc.calc_buy_price(input_price)
        
        # Calculate expected: price * 1.25 + 0.15, rounded to 3 decimals
        expected = round(input_price * 1.25 + 0.15, 3)
        
        assert abs(buy_price - expected) < 0.001, f"Price calculation failed for {input_price}"
        
        # Test sell price (no VAT, just add export compensation)
        sell_price = calc.calc_sell_price(input_price)
        expected_sell = round(input_price + 0.05, 3)
        
        assert abs(sell_price - expected_sell) < 0.001, f"Sell price calculation failed for {input_price}"


@pytest.mark.asyncio
async def test_integration_startup_time():
    """Test integration startup performance."""
    with patch('custom_components.gridenforcer.PriceCalculator') as mock_calc, \
         patch('custom_components.gridenforcer.async_track_time_change'), \
         patch('custom_components.gridenforcer.async_track_state_change_event'):
        
        from custom_components.gridenforcer import async_setup_entry
        
        # Mock dependencies
        hass = MagicMock()
        hass.data = {}
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        hass.bus.async_listen_once = MagicMock()
        
        config_entry = MagicMock()
        config_entry.data = {
            "price_sensor": "sensor.test",
            "extra_import": 0.15,
            "extra_export": 0.05,
            "vat": 25.0,
            "bat_cost": 0.02,
            "bat_soc": "sensor.battery_soc",
            "fcr_d_up_input": "binary_sensor.fcr_d_up",
            "fcr_d_down_input": "binary_sensor.fcr_d_down",
            "hours_selfuse": 4.0
        }
        
        # Mock price calculator setup
        mock_instance = MagicMock()
        mock_instance.async_update_price_calculator = AsyncMock()
        mock_calc.return_value = mock_instance
        
        start_time = time.time()
        
        result = await async_setup_entry(hass, config_entry)
        
        startup_time = time.time() - start_time
    
    print(f"Integration startup time: {startup_time:.3f}s")
    
    # Startup should be fast
    assert result is True
    assert startup_time < 1.0, "Integration startup should complete in under 1 second"
    assert "gridenforcer" in hass.data, "Integration should register its data"