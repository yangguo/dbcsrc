"""Basic test to verify test environment setup."""

import pytest


def test_basic_functionality():
    """Test basic functionality is working."""
    assert True


def test_imports():
    """Test that core modules can be imported."""
    try:
        # Test basic Python imports
        import os
        import sys

        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import required modules: {e}")


def test_environment():
    """Test that the test environment is properly set up."""
    import os

    # Check if we're in the correct directory
    assert os.path.exists("requirements.txt")
    assert os.path.exists("validate_requirements.py")
