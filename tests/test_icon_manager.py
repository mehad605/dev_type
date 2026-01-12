"""Tests for icon_manager.py"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication
from app.icon_manager import IconManager, get_icon_manager
import app.icon_manager as icon_manager_mod

@pytest.fixture(scope="module")
def qapp():
    """Ensure a QApplication is running."""
    yield QApplication.instance() or QApplication([])

@pytest.fixture
def temp_dirs(tmp_path):
    """Setup temporary directories for testing icon management."""
    data_dir = tmp_path / "Dev_Type_Data"
    shared_icons_dir = data_dir / "shared" / "icons"
    legacy_icons_dir = data_dir / "icons"
    
    shared_icons_dir.mkdir(parents=True)
    legacy_icons_dir.mkdir(parents=True)
    
    return {
        "data": data_dir,
        "shared_icons": shared_icons_dir,
        "legacy_icons": legacy_icons_dir
    }

def test_icon_manager_migration(qapp, temp_dirs):
    """Test that IconManager migrates icons from legacy to shared location."""
    # Reset singleton
    icon_manager_mod._icon_manager = None
    
    # Create a dummy icon file in legacy location
    legacy_file = temp_dirs["legacy_icons"] / "python.svg"
    legacy_file.write_text("<svg>Python</svg>")
    
    # Patch settings to return our temp paths
    with patch("app.settings.get_icons_dir", return_value=temp_dirs["shared_icons"]), \
         patch("app.settings.get_data_dir", return_value=temp_dirs["data"]):
        
        manager = IconManager()
        
        # Verify migration
        dest_file = temp_dirs["shared_icons"] / "python.svg"
        assert dest_file.exists()
        assert dest_file.read_text() == "<svg>Python</svg>"
        
        # Verify legacy file is moved (not copied)
        assert not legacy_file.exists()
        
        # Verify legacy folder is cleaned up if empty
        assert not temp_dirs["legacy_icons"].exists()

def test_icon_manager_migration_skips_existing(qapp, temp_dirs):
    """Test that migration doesn't overwrite existing icons in shared location."""
    icon_manager_mod._icon_manager = None
    
    legacy_file = temp_dirs["legacy_icons"] / "python.svg"
    legacy_file.write_text("<svg>Old</svg>")
    
    shared_file = temp_dirs["shared_icons"] / "python.svg"
    shared_file.write_text("<svg>New</svg>")
    
    with patch("app.settings.get_icons_dir", return_value=temp_dirs["shared_icons"]), \
         patch("app.settings.get_data_dir", return_value=temp_dirs["data"]):
        
        manager = IconManager()
        
        # Shared file should still be new
        assert shared_file.read_text() == "<svg>New</svg>"
        # Legacy file should still exist since it wasn't moved
        assert legacy_file.exists()

def test_get_icon_path(qapp, temp_dirs):
    """Test that get_icon_path returns correct paths."""
    icon_manager_mod._icon_manager = None
    
    with patch("app.settings.get_icons_dir", return_value=temp_dirs["shared_icons"]), \
         patch("app.settings.get_data_dir", return_value=temp_dirs["data"]):
        
        manager = IconManager()
        
        # Mock a file exists
        python_svg = temp_dirs["shared_icons"] / "python.svg"
        python_svg.touch()
        
        path = manager.get_icon_path("Python")
        assert path == python_svg
        
        # Unknown language
        assert manager.get_icon_path("UnknownX") is None

def test_icon_caching(qapp, temp_dirs):
    """Test in-memory caching of pixmaps."""
    icon_manager_mod._icon_manager = None
    
    with patch("app.settings.get_icons_dir", return_value=temp_dirs["shared_icons"]), \
         patch("app.settings.get_data_dir", return_value=temp_dirs["data"]):
        
        manager = IconManager()
        
        # Mock SVG content
        python_svg = temp_dirs["shared_icons"] / "python.svg"
        python_svg.write_text('<svg width="20" height="20"><rect width="20" height="20" fill="red"/></svg>')
        
        # First call loads from disk
        pix1 = manager.get_icon("Python", size=20)
        assert pix1 is not None
        assert not pix1.isNull()
        
        # Second call should come from cache
        pix2 = manager.get_icon("Python", size=20)
        assert pix1 is pix2 # Same object

def test_singleton_get_icon_manager():
    """Test the singleton getter."""
    icon_manager_mod._icon_manager = None
    mgr1 = get_icon_manager()
    mgr2 = get_icon_manager()
    assert mgr1 is mgr2
