"""Pytest configuration for GridEnforcer tests."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add the project root to Python path so custom_components can be imported
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Also add custom_components to the path
custom_components_path = project_root / "custom_components"
sys.path.insert(0, str(custom_components_path))

import pytest

# Mock Home Assistant core for testing
@pytest.fixture
def hass():
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock()
    hass.async_create_task = AsyncMock()
    hass.data = {}
    
    # Mock states for testing
    hass.states = MagicMock()
    hass.states.get = MagicMock(return_value=None)
    
    # Mock config entries
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    
    # Mock bus for event handling
    hass.bus = MagicMock()
    hass.bus.async_listen_once = MagicMock()
    
    return hass

@pytest.fixture
def config_entry():
    """Mock config entry for gridenforcer."""
    entry = MagicMock()
    entry.data = {
        "price_sensor": "sensor.electricity_price",
        "extra_import": 0.15,
        "extra_export": 0.05,
        "vat": 25.0,
        "bat_cost": 0.02,
        "bat_soc": "sensor.battery_soc",
        "fcr_d_up_input": "binary_sensor.fcr_d_up",
        "fcr_d_down_input": "binary_sensor.fcr_d_down",
        "hours_selfuse": 4.0
    }
    entry.options = {}
    entry.title = "GridEnforcerControl"
    entry.domain = "gridenforcer"
    entry.entry_id = "test_entry_id"
    return entry

@pytest.fixture
def mock_price_sensor_state():
    """Mock price sensor state."""
    state = MagicMock()
    state.state = "1.25"
    state.attributes = {
        "raw_today": [
            {
                "start": "2024-01-01T00:00:00+01:00",
                "end": "2024-01-01T01:00:00+01:00", 
                "value": 1.0
            }
        ],
        "raw_tomorrow": []
    }
    return state

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
        return None
    
    hass.states.get.side_effect = get_state_side_effect
    return hass

@pytest.fixture
def price_calculator_config():
    """Mock config entry for PriceCalculator."""
    config = MagicMock()
    config.data = {
        "price_sensor": "sensor.electricity_price",
        "extra_import": 0.15,
        "extra_export": 0.05,
        "vat": 25.0,
        "bat_cost": 0.02,
        "hours_selfuse": 4.0
    }
    return config
