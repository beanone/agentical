"""Configure pytest for all tests."""

import sys
from pathlib import Path
import pytest

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "asyncio: mark test as requiring asyncio")


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Add asyncio marker to all async tests
    for item in items:
        if item.get_closest_marker("asyncio") is None and "async" in item.name:
            item.add_marker(pytest.mark.asyncio)
