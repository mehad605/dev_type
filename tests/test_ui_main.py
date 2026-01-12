"""Tests for ui_main.py - Main window and UI components."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt


@pytest.fixture(scope="module")
def app():
    """Create QApplication instance for tests."""
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    yield instance


class TestFolderCardWidget:
    """Test FolderCardWidget."""
    
    def test_widget_initialization(self, app):
        """Test FolderCardWidget initializes correctly."""
        from app.ui_main import FolderCardWidget
        
        widget = FolderCardWidget("/path/to/folder")
        
        assert widget is not None
        assert widget.folder_path == "/path/to/folder"
    
    def test_widget_has_name_label(self, app):
        """Test widget has name label."""
        from app.ui_main import FolderCardWidget
        
        widget = FolderCardWidget("/home/user/project")
        
        assert hasattr(widget, 'name_label')
        assert widget.name_label.text() == "project"
    
    def test_widget_shows_not_found_for_missing_folder(self, app):
        """Test widget shows 'not found' message for missing folders."""
        from app.ui_main import FolderCardWidget
        
        path = "/nonexistent/folder/path"
        widget = FolderCardWidget(path)
        
        assert hasattr(widget, 'path_label')
        assert "not found" in widget.path_label.text().lower()
        # Verify pixmap is set (since we use SVGs now)
        assert not widget.icon_label.pixmap().isNull()
        assert widget._folder_exists is False
    
    def test_set_selected(self, app):
        """Test set_selected method."""
        from app.ui_main import FolderCardWidget
        
        widget = FolderCardWidget("/path")
        widget.set_selected(True)
        assert widget._selected is True
    
    def test_set_remove_mode(self, app):
        """Test set_remove_mode method."""
        from app.ui_main import FolderCardWidget
        
        widget = FolderCardWidget("/path")
        widget.set_remove_mode(True)
        assert widget._remove_mode is True
        assert not widget.remove_btn.isHidden()


class TestMainWindow:
    """Test MainWindow."""
    
    def test_window_initialization(self, app):
        """Test MainWindow initializes correctly."""
        from app.ui_main import MainWindow
        window = MainWindow()
        assert window is not None
        assert window.windowTitle() == "Dev Typing App"
    
    def test_window_has_tabs(self, app):
        """Test window has tab widget."""
        from app.ui_main import MainWindow
        window = MainWindow()
        assert hasattr(window, 'tabs')
        assert hasattr(window, 'folders_tab')
        assert hasattr(window, 'languages_tab')
        assert hasattr(window, 'editor_tab')
    
    def test_window_has_signals(self, app):
        """Test window has dynamic settings signals."""
        from app.ui_main import MainWindow
        window = MainWindow()
        assert hasattr(window, 'font_changed')
        assert hasattr(window, 'colors_changed')


class TestMainWindowMethods:
    """Test MainWindow methods."""
    
    def test_start_profile_transition_triggers_overlay(self, app, tmp_path):
        """Test that start_profile_transition triggers the visual transition overlay."""
        from app.ui_main import MainWindow
        from unittest.mock import patch, MagicMock
        
        with patch('app.ui_main.get_profile_manager') as mock_pm_getter:
            mock_pm = MagicMock()
            mock_pm.get_active_profile.return_value = "Old"
            mock_pm.get_all_profiles.return_value = [
                {"name": "NewUser", "image": None, "is_active": False},
                {"name": "Old", "image": None, "is_active": True}
            ]
            mock_pm_getter.return_value = mock_pm
            
            # Mock settings to return valid values for different keys
            def mock_get_setting(key, default=None):
                defaults = {
                    "dark_scheme": "dracula",
                    "sound_enabled": "1",
                    "sound_profile": "default_1",
                    "sound_volume": "50",
                    "pause_delay": "7",
                }
                return defaults.get(key, default)

            with patch('app.settings.get_setting', side_effect=mock_get_setting):
                window = MainWindow()
                
                # Mock the transition overlay
                with patch.object(window.transition_overlay, 'start_transition') as mock_start:
                    window.start_profile_transition("NewUser")
                    
                    # Verify transition was started
                    mock_start.assert_called_once()
                    args, _ = mock_start.call_args
                    assert args[0] == "NewUser"
                    
                    # The proxy label should be shown immediately
                    assert not window.proxy_label.isHidden()
