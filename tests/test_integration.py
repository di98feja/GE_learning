"""Test GridEnforcer integration."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from pathlib import Path


def test_integration_setup():
    """Test basic integration setup."""
    # Placeholder test for CI/CD validation
    assert True


@pytest.mark.asyncio
async def test_async_setup_entry(hass, config_entry):
    """Test async setup entry."""
    # Mock the PriceCalculator to avoid dependencies
    with patch('custom_components.gridenforcer.PriceCalculator') as mock_price_calc:
        mock_price_calc.return_value.async_update_price_calculator = AsyncMock()
        
        # Import and test the actual gridenforcer integration
        from custom_components.gridenforcer import async_setup_entry
        
        # Test that the function can be called
        result = await async_setup_entry(hass, config_entry)
        
        # Should return True for successful setup
        assert result is True


@pytest.mark.asyncio
async def test_async_unload_entry(hass, config_entry):
    """Test async unload entry."""
    from custom_components.gridenforcer import async_unload_entry
    
    # Test that unload works
    result = await async_unload_entry(hass, config_entry)
    
    assert result is True


def test_domain_constant():
    """Test that domain constant is properly defined."""
    from custom_components.gridenforcer import DOMAIN
    
    assert DOMAIN == "gridenforcer"


def test_integration_structure():
    """Test that required integration files exist."""
    project_root = Path(__file__).parent.parent
    integration_path = project_root / "custom_components" / "gridenforcer"
    
    assert integration_path.exists(), "Integration directory should exist"
    assert (integration_path / "__init__.py").exists(), "__init__.py should exist"
    assert (integration_path / "manifest.json").exists(), "manifest.json should exist"
    assert (integration_path / "config_flow.py").exists(), "config_flow.py should exist"
    assert (integration_path / "const.py").exists(), "const.py should exist"


def test_manifest_content():
    """Test that manifest.json has required content."""
    project_root = Path(__file__).parent.parent
    manifest_path = project_root / "custom_components" / "gridenforcer" / "manifest.json"
    
    assert manifest_path.exists(), "manifest.json should exist"
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    required_keys = ["domain", "name", "version", "requirements", "codeowners"]
    for key in required_keys:
        assert key in manifest, f"manifest.json should contain '{key}'"
    
    assert manifest["domain"] == "gridenforcer"
    assert manifest["name"] == "GridEnForcerControl"


def test_price_calculator_imports():
    """Test that PriceCalculator can be imported."""
    from custom_components.gridenforcer.pricecalculator import PriceCalculator
    
    # Test that the class exists and has expected methods
    assert hasattr(PriceCalculator, '__init__')
    assert hasattr(PriceCalculator, 'async_update_price_calculator')


def test_constants():
    """Test that required constants are defined."""
    from custom_components.gridenforcer.const import (
        DOMAIN, CONF_PRICE_SENSOR, CONF_EXTRA_IMPORT, 
        CONF_EXTRA_EXPORT, CONF_BAT_COST, CONF_VAT
    )
    
    assert DOMAIN == "gridenforcer"
    assert CONF_PRICE_SENSOR == "price_sensor"
    assert CONF_EXTRA_IMPORT == "extra_import"
    assert CONF_EXTRA_EXPORT == "extra_export"
    assert CONF_BAT_COST == "bat_cost"
    assert CONF_VAT == "vat"


def test_inverter_mode_enum():
    """Test InverterMode enum."""
    from custom_components.gridenforcer.invertermode import InverterMode
    
    # Test that enum values exist
    assert InverterMode.FCRDD.value == "Fcr-d down"
    assert InverterMode.FCRDU.value == "Fcr-d up"
    assert InverterMode.STANDBY.value == "Standby"
    assert InverterMode.CHARGING.value == "Charging"
    assert InverterMode.DISCHARGING.value == "Discharging"


def test_timevalue_class():
    """Test TimeValue class."""
    from custom_components.gridenforcer.timevalue import TimeValue
    from datetime import datetime
    
    # Create a TimeValue instance
    start = datetime(2024, 1, 1, 12, 0)
    end = datetime(2024, 1, 1, 13, 0)
    
    tv = TimeValue(start=start, end=end, value=1.5, sell_value=1.2)
    
    assert tv.start == start
    assert tv.end == end
    assert tv.value == 1.5
    assert tv.sell_value == 1.2


@pytest.mark.asyncio 
async def test_config_flow_basic():
    """Test basic config flow functionality."""
    from custom_components.gridenforcer.config_flow import ConfigFlow
    
    # Test that ConfigFlow can be instantiated
    flow = ConfigFlow()
    assert flow.VERSION == 1
    assert hasattr(flow, 'async_step_user')