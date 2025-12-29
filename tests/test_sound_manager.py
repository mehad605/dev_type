"""Tests for sound manager module."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from app.sound_manager import SoundManager


@pytest.fixture
def mock_sound_effect():
    """Mock QSoundEffect."""
    with patch('app.sound_manager.QSoundEffect') as mock:
        yield mock


@pytest.fixture
def sound_manager(tmp_path, mock_sound_effect):
    """Create SoundManager with mocked dependencies."""
    sounds_dir = tmp_path / "assets" / "sounds"
    sounds_dir.mkdir(parents=True)
    
    # Create some mock sound files
    (sounds_dir / "keypress_mechanical.wav").write_text("fake sound")
    (sounds_dir / "keypress_soft.wav").write_text("fake sound")
    
    with patch('app.sound_manager.Path') as mock_path:
        mock_path.return_value = sounds_dir
        with patch('app.settings.init_db'):
            with patch('app.settings.get_setting', return_value="{}"):
                manager = SoundManager()
                return manager


def test_sound_manager_initialization(sound_manager):
    """Test SoundManager initializes correctly."""
    assert sound_manager.current_profile == "none"
    assert sound_manager.enabled is True
    assert sound_manager.volume == 0.5
    assert isinstance(sound_manager.builtin_profiles, dict)
    assert "none" in sound_manager.builtin_profiles


def test_get_all_profiles(sound_manager):
    """Test getting all profiles (built-in and custom)."""
    sound_manager.custom_profiles = {
        "custom1": {"name": "Custom 1", "builtin": False, "file": "custom1.wav"}
    }
    
    all_profiles = sound_manager.get_all_profiles()
    
    assert "none" in all_profiles
    assert "custom1" in all_profiles


def test_get_profile_names(sound_manager):
    """Test getting profile names."""
    names = sound_manager.get_profile_names()
    
    assert isinstance(names, dict)
    assert "none" in names
    assert names["none"] == "No Sound"


def test_set_volume(sound_manager):
    """Test setting volume."""
    sound_manager.set_volume(0.75)
    assert sound_manager.volume == 0.75


def test_enable_disable_sound(sound_manager):
    """Test enabling and disabling sound."""
    sound_manager.set_enabled(False)
    assert sound_manager.enabled is False
    
    sound_manager.set_enabled(True)
    assert sound_manager.enabled is True


def test_create_custom_profile_override_builtin_fails(sound_manager):
    """Test that cannot override built-in profile."""
    result = sound_manager.create_custom_profile(
        "none",
        "Override None",
        "/fake/path.wav"
    )
    
    assert result is False


def test_delete_custom_profile(sound_manager):
    """Test deleting custom profile."""
    sound_manager.custom_profiles["test_profile"] = {
        "name": "Test",
        "builtin": False,
        "file": "test.wav"
    }
    
    with patch.object(sound_manager, '_save_custom_profiles'):
        result = sound_manager.delete_custom_profile("test_profile")
    
    assert result is True
    assert "test_profile" not in sound_manager.custom_profiles


def test_cannot_delete_builtin_profile(sound_manager):
    """Test that cannot delete built-in profile."""
    result = sound_manager.delete_custom_profile("none")
    assert result is False
