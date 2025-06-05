"""
Integration tests conftest.py - imports shared fixtures from parent
"""

# Import all fixtures from parent conftest.py
import sys
from pathlib import Path

# Add parent directory to path so we can import from parent conftest
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import all fixtures from parent conftest - pytest will auto-discover them

# Note: pytest_plugins is already configured in the parent conftest.py
