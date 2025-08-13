"""Pytest configuration for Grid Enforcer tests."""
import sys
from pathlib import Path

# Add the project root to Python path so custom_components can be imported
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Also add custom_components to the path
custom_components_path = project_root / "custom_components"
sys.path.insert(0, str(custom_components_path))

import pytest
from unittest.mock import AsyncMock, MagicMock

# Mock Home Assistant core for testing
@pytest.fixture
def hass():
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock()
    hass.async_create_task = AsyncMock()
    return hass

@pytest.fixture
def config_entry():
    """Mock config entry."""
    entry = MagicMock()
    entry.data = {}
    entry.options = {}
    entry.title = "Grid Enforcer Test"
    entry.domain = "grid_enforcer"
    return entry