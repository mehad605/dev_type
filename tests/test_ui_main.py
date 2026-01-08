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
    
    def test_widget_stores_path(self, app):
        """Test widget stores folder path."""
        from app.ui_main import FolderCardWidget
        
        path = "C:\\Users\\Test\\Project"
        widget = FolderCardWidget(path)
        
        assert widget.folder_path == path
    
    def test_widget_has_name_label(self, app):
        """Test widget has name label."""
        from app.ui_main import FolderCardWidget
        
        widget = FolderCardWidget("/home/user/project")
        
        assert hasattr(widget, 'name_label')
        assert widget.name_label.text() == "project"
    
    def test_widget_has_path_label(self, app):
        """Test widget has path label."""
        from app.ui_main import FolderCardWidget
        
        path = "/home/user/project"
        widget = FolderCardWidget(path)
        
        assert hasattr(widget, 'path_label')
        assert widget.path_label.text() == path
    
    def test_initial_selected_state(self, app):
        """Test initial selected state is False."""
        from app.ui_main import FolderCardWidget
        
        widget = FolderCardWidget("/path")
        
        assert widget._selected is False
    
    def test_initial_remove_mode(self, app):
        """Test initial remove mode is False."""
        from app.ui_main import FolderCardWidget
        
        widget = FolderCardWidget("/path")
        
        assert widget._remove_mode is False
    
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
    
    def test_remove_button_hidden_initially(self, app):
        """Test remove button is hidden initially."""
        from app.ui_main import FolderCardWidget
        
        widget = FolderCardWidget("/path")
        
        assert widget.remove_btn.isHidden()
    
    def test_remove_button_shown_in_remove_mode(self, app):
        """Test remove button shown when in remove mode."""
        from app.ui_main import FolderCardWidget
        
        widget = FolderCardWidget("/path")
        widget.set_remove_mode(True)
        
        # Button is shown (not hidden) when in remove mode
        assert not widget.remove_btn.isHidden()


class TestFoldersTab:
    """Test FoldersTab widget."""
    
    def test_tab_initialization(self, app):
        """Test FoldersTab initializes correctly."""
        from app.ui_main import FoldersTab
        
        tab = FoldersTab()
        
        assert tab is not None
    
    def test_tab_has_add_button(self, app):
        """Test tab has add button."""
        from app.ui_main import FoldersTab
        
        tab = FoldersTab()
        
        assert hasattr(tab, 'add_btn')
    
    def test_tab_has_edit_button(self, app):
        """Test tab has edit/remove button."""
        from app.ui_main import FoldersTab
        
        tab = FoldersTab()
        
        assert hasattr(tab, 'edit_btn')
    
    def test_tab_has_list(self, app):
        """Test tab has list widget."""
        from app.ui_main import FoldersTab
        
        tab = FoldersTab()
        
        assert hasattr(tab, 'list')
    
    def test_edit_button_is_checkable(self, app):
        """Test edit button is checkable."""
        from app.ui_main import FoldersTab
        
        tab = FoldersTab()
        
        assert tab.edit_btn.isCheckable()


class TestMainWindow:
    """Test MainWindow."""
    
    def test_window_initialization(self, app):
        """Test MainWindow initializes correctly."""
        from app.ui_main import MainWindow
        
        window = MainWindow()
        
        assert window is not None
    
    def test_window_title(self, app):
        """Test window title is set."""
        from app.ui_main import MainWindow
        
        window = MainWindow()
        
        assert window.windowTitle() == "Dev Typing App"
    
    def test_window_has_tabs(self, app):
        """Test window has tab widget."""
        from app.ui_main import MainWindow
        
        window = MainWindow()
        
        assert hasattr(window, 'tabs')
    
    def test_window_has_folders_tab(self, app):
        """Test window has folders tab."""
        from app.ui_main import MainWindow
        
        window = MainWindow()
        
        assert hasattr(window, 'folders_tab')
    
    def test_window_has_languages_tab(self, app):
        """Test window has languages tab."""
        from app.ui_main import MainWindow
        
        window = MainWindow()
        
        assert hasattr(window, 'languages_tab')
    
    def test_window_has_editor_tab(self, app):
        """Test window has editor tab."""
        from app.ui_main import MainWindow
        
        window = MainWindow()
        
        assert hasattr(window, 'editor_tab')
    
    def test_window_has_signals(self, app):
        """Test window has dynamic settings signals."""
        from app.ui_main import MainWindow
        
        window = MainWindow()
        
        assert hasattr(window, 'font_changed')
        assert hasattr(window, 'colors_changed')
        assert hasattr(window, 'cursor_changed')
    
    def test_window_initial_size(self, app):
        """Test window initial size."""
        from app.ui_main import MainWindow
        
        window = MainWindow()
        
        assert window.width() >= 900
        assert window.height() >= 600


class TestMainWindowMethods:
    """Test MainWindow methods."""
    
    def test_has_apply_current_theme_method(self, app):
        """Test window has apply_current_theme method."""
        from app.ui_main import MainWindow
        
        window = MainWindow()
        
        assert hasattr(window, 'apply_current_theme')
        assert callable(window.apply_current_theme)
    
    def test_has_refresh_languages_tab_method(self, app):
        """Test window has refresh_languages_tab method."""
        from app.ui_main import MainWindow
        
        window = MainWindow()
        
        assert hasattr(window, 'refresh_languages_tab')
        assert callable(window.refresh_languages_tab)
