"""Tests for sound_manager.py"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication
from app.sound_manager import SoundManager, get_sound_manager
import app.sound_manager as sound_manager_mod

@pytest.fixture(scope="module")
def qapp():
    """Ensure a QApplication is running."""
    yield QApplication.instance() or QApplication([])

@pytest.fixture
def temp_sounds_env(tmp_path):
    """Setup a mock environment for sounds."""
    data_dir = tmp_path / "Dev_Type_Data"
    shared_dir = data_dir / "shared"
    sounds_dir = shared_dir / "sounds"
    custom_sounds_dir = sounds_dir / "custom"
    
    sounds_dir.mkdir(parents=True)
    custom_sounds_dir.mkdir(parents=True)
    
    # Create a dummy built-in sound
    (sounds_dir / "keystrokes.wav").touch()
    
    return {
        "data": data_dir,
        "shared": shared_dir,
        "sounds": sounds_dir,
        "custom": custom_sounds_dir
    }

def test_sound_manager_init(qapp, temp_sounds_env):
    """Test SoundManager initialization and profile discovery."""
    sound_manager_mod._sound_manager = None
    
    with patch("app.portable_data.get_data_manager") as mock_gdm:
        mock_dm = MagicMock()
        mock_dm.get_sounds_dir.return_value = temp_sounds_env["sounds"]
        mock_gdm.return_value = mock_dm
        
        manager = SoundManager()
        
        # Should discover default_1 because keystrokes.wav exists
        assert "default_1" in manager.builtin_profiles
        assert manager.sounds_dir == temp_sounds_env["sounds"]

def test_create_custom_profile(qapp, temp_sounds_env, tmp_path):
    """Test creating a custom sound profile."""
    sound_manager_mod._sound_manager = None
    
    # Create a source wav file
    src_wav = tmp_path / "source.wav"
    src_wav.touch()
    
    with patch("app.portable_data.get_data_manager") as mock_gdm, \
         patch("app.settings.get_setting", return_value="{}"), \
         patch("app.settings.set_setting") as mock_set_setting:
        
        mock_dm = MagicMock()
        mock_dm.get_sounds_dir.return_value = temp_sounds_env["sounds"]
        mock_dm.get_shared_dir.return_value = temp_sounds_env["shared"]
        mock_gdm.return_value = mock_dm
        
        manager = SoundManager()
        
        success = manager.create_custom_profile("my_profile", "My Profile", str(src_wav))
        
        assert success is True
        assert "my_profile" in manager.custom_profiles
        
        # Verify file was copied to shared/sounds/custom/my_profile/
        expected_path = temp_sounds_env["custom"] / "my_profile" / "keypress.wav"
        assert expected_path.exists()
        
        # Verify metadata was saved to DB
        mock_set_setting.assert_called()

def test_sound_manager_singleton():
    """Test the singleton behavior."""
    sound_manager_mod._sound_manager = None
    s1 = get_sound_manager()
    s2 = get_sound_manager()
    assert s1 is s2

def test_set_profile_loads_effect(qapp, temp_sounds_env):
    """Test that setting a profile initializes the QSoundEffect."""
    sound_manager_mod._sound_manager = None
    
    with patch("app.portable_data.get_data_manager") as mock_gdm, \
         patch("PySide6.QtMultimedia.QSoundEffect.setSource") as mock_set_source:
        
        mock_dm = MagicMock()
        mock_dm.get_sounds_dir.return_value = temp_sounds_env["sounds"]
        mock_gdm.return_value = mock_dm
        
        manager = SoundManager()
        manager.set_profile("default_1")
        
        assert manager.current_profile == "default_1"
        assert manager.sound_effect is not None
        mock_set_source.assert_called()
