"""Pytest configuration for hass-opensprinkler tests."""

import sys
from pathlib import Path

# Add custom_components to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components"))
