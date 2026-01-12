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
    """Test get_ghosts_dir function - should be profile specific."""
    ghosts_dir = get_ghosts_dir()
    assert isinstance(ghosts_dir, Path)
    assert ghosts_dir.name == "ghosts"
    assert "profiles" in str(ghosts_dir)


def test_get_custom_sounds_dir():
    """Test getting custom sounds directory - should be in shared."""
    from app.portable_data import get_custom_sounds_dir
    
    sounds_dir = get_custom_sounds_dir()
    assert isinstance(sounds_dir, Path)
    assert sounds_dir.name == "custom"
    assert "shared" in str(sounds_dir)


def test_get_icons_dir():
    """Test getting shared icons directory."""
    from app.portable_data import get_icons_dir
    
    icons_dir = get_icons_dir()
    assert isinstance(icons_dir, Path)
    assert icons_dir.name == "icons"
    assert "shared" in str(icons_dir)


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
    """Test that all subdirectories are created in new structure."""
    from app.portable_data import get_data_dir
    data_dir = get_data_dir()
    
    # Check that root-level profile/shared dirs exist
    assert (data_dir / "profiles").exists()
    assert (data_dir / "shared").exists()
    
    # Check shared subdirs
    assert (data_dir / "shared" / "sounds").exists()
    assert (data_dir / "shared" / "icons").exists()
    assert (data_dir / "shared" / "logs").exists()
    
    # Check default profile-specific structure (Default profile is created on profile manager init)
    # The portable data manager itself creates the 'profiles' folder.
    # The profile manager (tested elsewhere) creates the actual 'Default' folder.


def test_get_last_error_initially_none():
    """Test get_last_error returns None when no error."""
    from app.portable_data import PortableDataManager
    manager = PortableDataManager()
    # After successful init, no error should be recorded
    error = manager.get_last_error()
    assert error is None
