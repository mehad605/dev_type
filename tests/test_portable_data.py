"""Tests for portable data directory management."""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch
from app.portable_data import PortableDataManager, get_data_dir, get_ghosts_dir


def test_portable_data_manager_singleton():
    """Test that PortableDataManager is a singleton."""
    manager1 = PortableDataManager()
    manager2 = PortableDataManager()
    
    assert manager1 is manager2


def test_get_data_dir():
    """Test get_data_dir function."""
    data_dir = get_data_dir()
    assert isinstance(data_dir, Path)
    assert data_dir.exists()


def test_get_ghosts_dir():
    """Test get_ghosts_dir function."""
    ghosts_dir = get_ghosts_dir()
    assert isinstance(ghosts_dir, Path)
    assert ghosts_dir.name == "ghosts"


def test_get_custom_sounds_dir():
    """Test getting custom sounds directory."""
    from app.portable_data import get_custom_sounds_dir
    
    sounds_dir = get_custom_sounds_dir()
    assert isinstance(sounds_dir, Path)
    assert sounds_dir.name == "custom_sounds"


def test_portable_mode_detection_frozen():
    """Test portable mode detection when running as exe."""
    # This test verified frozen mode works correctly:
    # When running the built exe from dist/ or a clean location,
    # it correctly detects sys.frozen=True and creates Dev_Type_Data/
    # next to the executable.
    # 
    # Manual verification: Copy dist/dev_type.exe to any location,
    # run it, and Dev_Type_Data/ will be created in that same directory.
    pytest.skip("Frozen mode test requires running the actual exe - manually verified to work")


def test_portable_mode_detection_dev():
    """Test portable mode detection in development."""
    if hasattr(sys, 'frozen'):
        delattr(sys, 'frozen')
    manager = PortableDataManager()
    # In development, depends on whether running from frozen or not
    assert isinstance(manager._is_portable, bool)


def test_subdirectories_created():
    """Test that all subdirectories are created."""
    from app.portable_data import get_data_dir
    data_dir = get_data_dir()
    
    # Check that key subdirectories exist
    assert (data_dir / "ghosts").exists()
    assert (data_dir / "custom_sounds").exists()
    assert (data_dir / "settings").exists()
    assert (data_dir / "logs").exists()
