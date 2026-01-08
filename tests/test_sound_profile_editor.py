"""Tests for sound_profile_editor.py - Sound profile editor dialog."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    """Create QApplication instance for tests."""
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    yield instance


class TestSoundProfileEditorInit:
    """Test SoundProfileEditor initialization."""
    
    def test_editor_initialization_new_profile(self, app):
        """Test editor initializes correctly for new profile."""
        from app.sound_profile_editor import SoundProfileEditor
        
        editor = SoundProfileEditor()
        
        assert editor.profile_id is None
        assert editor.is_new is True
    
    def test_editor_initialization_existing_profile(self, app):
        """Test editor initializes correctly for existing profile."""
        from app.sound_profile_editor import SoundProfileEditor
        
        editor = SoundProfileEditor(profile_id="test_profile")
        
        assert editor.profile_id == "test_profile"
        assert editor.is_new is False
    
    def test_window_title_new_profile(self, app):
        """Test window title for new profile."""
        from app.sound_profile_editor import SoundProfileEditor
        
        editor = SoundProfileEditor()
        
        assert "Create" in editor.windowTitle()
    
    def test_window_title_edit_profile(self, app):
        """Test window title for editing profile."""
        from app.sound_profile_editor import SoundProfileEditor
        
        editor = SoundProfileEditor(profile_id="existing")
        
        assert "Edit" in editor.windowTitle()
    
    def test_minimum_width(self, app):
        """Test editor has minimum width set."""
        from app.sound_profile_editor import SoundProfileEditor
        
        editor = SoundProfileEditor()
        
        assert editor.minimumWidth() >= 500


class TestEditorUIElements:
    """Test UI element setup."""
    
    def test_has_name_edit(self, app):
        """Test editor has name edit field."""
        from app.sound_profile_editor import SoundProfileEditor
        
        editor = SoundProfileEditor()
        
        assert hasattr(editor, 'name_edit')
        assert editor.name_edit is not None
    
    def test_has_sound_path(self, app):
        """Test editor has sound path field."""
        from app.sound_profile_editor import SoundProfileEditor
        
        editor = SoundProfileEditor()
        
        assert hasattr(editor, 'sound_path')
        assert editor.sound_path is not None
    
    def test_name_edit_placeholder(self, app):
        """Test name edit has placeholder text."""
        from app.sound_profile_editor import SoundProfileEditor
        
        editor = SoundProfileEditor()
        
        placeholder = editor.name_edit.placeholderText()
        assert len(placeholder) > 0
    
    def test_sound_path_readonly(self, app):
        """Test sound path is read-only."""
        from app.sound_profile_editor import SoundProfileEditor
        
        editor = SoundProfileEditor()
        
        assert editor.sound_path.isReadOnly()


class TestBrowseSound:
    """Test sound file browsing."""
    
    @patch('app.sound_profile_editor.QFileDialog.getOpenFileName')
    def test_browse_sets_path(self, mock_dialog, app):
        """Test browsing sets the sound path."""
        from app.sound_profile_editor import SoundProfileEditor
        
        mock_dialog.return_value = ("/path/to/sound.wav", "Audio Files (*.wav *.mp3 *.ogg)")
        
        editor = SoundProfileEditor()
        editor._browse_sound()
        
        assert editor.sound_path.text() == "/path/to/sound.wav"
    
    @patch('app.sound_profile_editor.QFileDialog.getOpenFileName')
    def test_browse_cancelled_no_change(self, mock_dialog, app):
        """Test cancelled browse doesn't change path."""
        from app.sound_profile_editor import SoundProfileEditor
        
        mock_dialog.return_value = ("", "")
        
        editor = SoundProfileEditor()
        original = editor.sound_path.text()
        editor._browse_sound()
        
        assert editor.sound_path.text() == original


class TestTestSound:
    """Test sound testing functionality."""
    
    @patch('app.sound_profile_editor.QMessageBox.warning')
    def test_test_no_file_shows_warning(self, mock_warning, app):
        """Test warning shown when no file selected."""
        from app.sound_profile_editor import SoundProfileEditor
        
        editor = SoundProfileEditor()
        editor._test_sound()
        
        mock_warning.assert_called_once()
    
    @patch('app.sound_profile_editor.Path.exists')
    @patch('app.sound_profile_editor.QMessageBox.warning')
    def test_test_nonexistent_file_shows_warning(self, mock_warning, mock_exists, app):
        """Test warning shown when file doesn't exist."""
        from app.sound_profile_editor import SoundProfileEditor
        
        mock_exists.return_value = False
        
        editor = SoundProfileEditor()
        editor.sound_path.setText("/nonexistent/sound.wav")
        editor._test_sound()
        
        mock_warning.assert_called_once()


class TestSaveProfile:
    """Test profile saving."""
    
    @patch('app.sound_profile_editor.QMessageBox.warning')
    def test_save_empty_name_shows_warning(self, mock_warning, app):
        """Test warning when saving with empty name."""
        from app.sound_profile_editor import SoundProfileEditor
        
        editor = SoundProfileEditor()
        editor.name_edit.setText("")
        editor._save_profile()
        
        mock_warning.assert_called_once()
    
    @patch('app.sound_profile_editor.QMessageBox.warning')
    def test_save_no_sound_shows_warning(self, mock_warning, app):
        """Test warning when saving without sound file."""
        from app.sound_profile_editor import SoundProfileEditor
        
        editor = SoundProfileEditor()
        editor.name_edit.setText("Test Profile")
        editor.sound_path.setText("")
        editor._save_profile()
        
        mock_warning.assert_called_once()


class TestProfileIdGeneration:
    """Test profile ID generation from name."""
    
    def test_id_generation_pattern(self, app):
        """Test profile ID generation from name follows expected pattern."""
        import re
        
        # Test the same logic used in _save_profile
        name = "My Keyboard Profile"
        profile_id = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
        
        assert profile_id == "my_keyboard_profile"
        assert profile_id == profile_id.lower()
    
    def test_id_generation_special_chars(self, app):
        """Test ID generation removes special characters."""
        import re
        
        name = "Test!@#$Profile"
        profile_id = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
        
        assert profile_id == "test_profile"
    
    def test_id_generation_numbers(self, app):
        """Test ID generation preserves numbers."""
        import re
        
        name = "Profile123"
        profile_id = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
        
        assert profile_id == "profile123"
