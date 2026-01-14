"""Tests for the main UI window."""
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from unittest.mock import patch, MagicMock

@pytest.fixture(scope="module")
def app():
    """Ensure a QApplication is running."""
    yield QApplication.instance() or QApplication([])

@pytest.fixture
def mock_icon_manager():
    """Mock for IconManager to avoid network/graphics issues."""
    with patch('app.languages_tab._get_icon_manager') as mock_getter:
        mock_im = MagicMock()
        # Ensure get_icon returns None so fallback logic is used
        mock_im.get_icon.return_value = None
        # Ensure get_download_error returns None
        mock_im.get_download_error.return_value = None
        mock_getter.return_value = mock_im
        yield mock_im

@pytest.fixture
def mock_sound_manager():
    """Mock for SoundManager."""
    with patch('app.sound_manager.get_sound_manager') as mock_getter:
        mock_sm = MagicMock()
        mock_getter.return_value = mock_sm
        yield mock_sm


# Mock Widget Helper for testing FolderCardWidget interactions
class SafeFolderCardWidget(QWidget):
    """Safe mock of FolderCardWidget for testing."""
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.remove_requested = MagicMock()
        self.set_remove_mode = MagicMock()
        self.set_selected = MagicMock()
        self.attach = MagicMock()
        self.folder_exists = MagicMock(return_value=False)
        self.update_stats = MagicMock()
        self.adjustSize = MagicMock()


class TestMainWindow:
    """Test MainWindow."""
    
    def test_window_initialization(self, app, mock_icon_manager, mock_sound_manager):
        """Test MainWindow initializes correctly with mocks."""
        from app.ui_main import MainWindow
        
        window = MainWindow()
        assert window is not None
        assert window.windowTitle() == "Dev Typing App"
        assert hasattr(window, 'tabs')
        # Check if tabs were added
        assert window.tabs.count() >= 5
    
    def test_window_has_tabs(self, app, mock_icon_manager, mock_sound_manager):
        """Test window has tab widget and expected tabs."""
        from app.ui_main import MainWindow
        window = MainWindow()
        assert hasattr(window, 'tabs')
        assert hasattr(window, 'folders_tab')
        assert hasattr(window, 'languages_tab')
        assert hasattr(window, 'editor_tab')
        assert hasattr(window, 'history_tab')
        assert hasattr(window, 'stats_tab')
        assert hasattr(window, 'shortcuts_tab')
        assert hasattr(window, 'settings_tab')
    
    def test_window_has_signals(self, app, mock_icon_manager, mock_sound_manager):
        """Test window has dynamic settings signals."""
        from app.ui_main import MainWindow
        window = MainWindow()
        assert hasattr(window, 'font_changed')
        assert hasattr(window, 'colors_changed')
        assert hasattr(window, 'cursor_changed')


class TestMainWindowMethods:
    """Test MainWindow methods."""
    
    def test_start_profile_transition_triggers_overlay(self, app, mock_icon_manager, mock_sound_manager, tmp_path):
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


class TestFolderCardWidget:
    """Test FolderCardWidget."""
    
    def test_folder_card_init(self, app):
        from app.ui_main import FolderCardWidget
        card = FolderCardWidget("C:/Dummy")
        assert card.folder_path == "C:/Dummy"
        assert not card.folder_exists()
        
    def test_folder_card_selected(self, app):
        from app.ui_main import FolderCardWidget
        card = FolderCardWidget("C:/Dummy")
        # Just check it runs without crash
        card.set_selected(True)
        assert card._selected is True
        card.set_selected(False)
        assert card._selected is False
        
    def test_folder_card_remove_mode(self, app):
        from app.ui_main import FolderCardWidget
        card = FolderCardWidget("C:/Dummy")
        card.set_remove_mode(True)
        assert not card.remove_btn.isHidden()
        card.set_remove_mode(False)
        assert card.remove_btn.isHidden()


class TestFoldersTab:
    """Test FoldersTab."""
    
    def test_folders_tab_init(self, app):
        from app.ui_main import FoldersTab
        tab = FoldersTab()
        assert tab.list is not None
        
    def test_folders_tab_selection_changed(self, app):
        from app.ui_main import FoldersTab, FolderCardWidget
        from PySide6.QtWidgets import QListWidgetItem
        tab = FoldersTab()
        
        # Manually add an item
        item = QListWidgetItem(tab.list)
        card = FolderCardWidget("C:/Dummy")
        card.attach(tab.list, item)
        tab.list.setItemWidget(item, card)
        
        tab._on_selection_changed(item, None)
        assert card._selected is True


class TestMainWindowShortcuts:
    """Test keyboard shortcuts in MainWindow."""
    
    def test_behavioral_shortcuts(self, app, mock_icon_manager, mock_sound_manager):
        from app.ui_main import MainWindow
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtCore import Qt
        
        window = MainWindow()
        
        # Mock methods that are called by shortcuts
        window._handle_allow_continue_button = MagicMock()
        window._handle_show_ghost_text_button = MagicMock()
        window._handle_sound_enabled_button = MagicMock()
        window._handle_show_typed_button = MagicMock()
        window._handle_instant_death_button = MagicMock()
        window._handle_auto_indent_button = MagicMock()
        
        # Ctrl+L: Lenient Mode
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_L, Qt.ControlModifier, text="l")
        window.keyPressEvent(event)
        window._handle_allow_continue_button.assert_called()
        
        # Ctrl+G: Ghost
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_G, Qt.ControlModifier, text="g")
        window.keyPressEvent(event)
        window._handle_show_ghost_text_button.assert_called()
        
        # Ctrl+M: Mute
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_M, Qt.ControlModifier, text="m")
        window.keyPressEvent(event)
        window._handle_sound_enabled_button.assert_called()
        
        # Ctrl+S: Show typed
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_S, Qt.ControlModifier, text="s")
        window.keyPressEvent(event)
        window._handle_show_typed_button.assert_called()
        
        # Ctrl+D: Instant Death
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_D, Qt.ControlModifier, text="d")
        window.keyPressEvent(event)
        window._handle_instant_death_button.assert_called()

        # Ctrl+I: Auto Indent
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_I, Qt.ControlModifier, text="i")
        window.keyPressEvent(event)
        window._handle_auto_indent_button.assert_called()

    def test_tab_navigation_shortcuts(self, app, mock_icon_manager, mock_sound_manager):
        from app.ui_main import MainWindow
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtCore import Qt
        
        window = MainWindow()
        window.tabs.setCurrentIndex(0)
        
        # Alt+2: Switch to tab 1
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_2, Qt.AltModifier)
        window.keyPressEvent(event)
        assert window.tabs.currentIndex() == 1
        
        # Alt+1: Switch to tab 0
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_1, Qt.AltModifier)
        window.keyPressEvent(event)
        assert window.tabs.currentIndex() == 0

    def test_folder_card_mouse_events(self, app):
        from app.ui_main import FolderCardWidget
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QPoint
        card = FolderCardWidget("C:/Dummy")
        
        # Mock dependencies for mouse events
        card._list_widget = MagicMock()
        card._list_item = MagicMock()
        
        # Left click
        event = QMouseEvent(QMouseEvent.MouseButtonPress, QPoint(10, 10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        card.mousePressEvent(event)
        card._list_widget.setCurrentItem.assert_called_with(card._list_item)

        # Double click
        event = QMouseEvent(QMouseEvent.MouseButtonDblClick, QPoint(10, 10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        card.mouseDoubleClickEvent(event)
        card._list_widget.itemDoubleClicked.emit.assert_called()


class TestMainWindowLifecycle:
    """Test MainWindow life cycle and lazy loading."""

    def test_lazy_loading(self, app, mock_icon_manager, mock_sound_manager):
        from app.ui_main import MainWindow
        from PySide6.QtWidgets import QLabel
        window = MainWindow()
        
        # Placeholder should be QLabel
        assert isinstance(window.history_tab, QLabel)
        
        window._start_background_loading()
        window._load_history_tab_lazy()
        window._load_stats_tab_lazy()
        window._load_editor_tab_lazy()
        window._load_settings_tab_lazy()
        
        # Check if tabs are replaced with real widgets
        from app.history_tab import HistoryTab
        from app.stats_tab import StatsTab
        assert isinstance(window.history_tab, HistoryTab)
        assert isinstance(window.stats_tab, StatsTab)

    def test_on_tab_changed_persistence(self, app, mock_icon_manager, mock_sound_manager):
        from app.ui_main import MainWindow
        from PySide6.QtWidgets import QMessageBox
        window = MainWindow()
        window._load_settings_tab_lazy() # Load real settings tab
        
        # Mock dirty colors state
        window._colors_dirty = True
        settings_idx = window.tabs.indexOf(window.settings_tab)
        window._last_tab_index = settings_idx
        
        # Simulate switching away and discarding
        with patch('PySide6.QtWidgets.QMessageBox.question', return_value=QMessageBox.Discard):
            window._on_tab_changed(0)
            assert window._colors_dirty is False

    @patch('app.themes.THEMES', {"dark": {"dracula": MagicMock(), "monokai": MagicMock()}})
    @patch('app.themes._get_custom_themes', return_value={})
    def test_cycle_themes(self, mock_custom, app, mock_icon_manager, mock_sound_manager):
        from app.ui_main import MainWindow
        
        # Avoid full theme application which needs real ColorScheme objects
        with patch('app.ui_main.MainWindow.apply_current_theme'):
            window = MainWindow()
            
            # Mock THEMES again inside to be sure settings.get_default works
            with patch('app.settings.get_setting', return_value="dracula"):
                with patch('app.settings.set_setting') as mock_set:
                    window._cycle_themes()
                    # Should set to next theme (monokai)
                    mock_set.assert_called_with("dark_scheme", "monokai")

    def test_on_add_folder(self, app, mock_icon_manager, mock_sound_manager):
        from app.ui_main import MainWindow
        window = MainWindow()
        
        with patch('PySide6.QtWidgets.QFileDialog.exec', return_value=True):
            with patch('PySide6.QtWidgets.QFileDialog.selectedFiles', return_value=["C:/NewFolder"]):
                with patch('app.settings.add_folder') as mock_add:
                    window.folders_tab.on_add()
                    mock_add.assert_called_with("C:/NewFolder")

    def test_maybe_remove_item(self, app, mock_icon_manager, mock_sound_manager):
        from app.ui_main import MainWindow
        from PySide6.QtWidgets import QDialog
        
        def mock_get_setting(key, default=None):
            if key == "delete_confirm": return "1"
            if key == "dark_scheme": return "dracula"
            return default
            
        with patch('app.settings.get_setting', side_effect=mock_get_setting):
            window = MainWindow()
            # Patch QDialog.exec to return Accepted (1)
            with patch('PySide6.QtWidgets.QDialog.exec', return_value=QDialog.Accepted):
                # We also need to patch check state or just not rely on it.
                # The code checks `if cb.isChecked():`. We can patch that too if we want to cover 'Don't ask again'
                # But for now let's just assert removal.
                with patch('app.settings.remove_folder') as mock_remove:
                    window.folders_tab._maybe_remove_item("C:/Folder")
                    mock_remove.assert_called_with("C:/Folder")

    def test_folders_tab_selection_changed_with_previous(self, app):
        from app.ui_main import FoldersTab
        from PySide6.QtWidgets import QListWidgetItem
        from unittest.mock import MagicMock
        
        # Patch the real FolderCardWidget with our safe dummy
        with patch('app.ui_main.FolderCardWidget', SafeFolderCardWidget):
            tab = FoldersTab()
            
            # The MockCard now acts as our test instance
            class MockCard(SafeFolderCardWidget):
                pass

            item1 = QListWidgetItem(tab.list)
            card1 = MockCard()
            tab.list.setItemWidget(item1, card1)
            
            item2 = QListWidgetItem(tab.list)
            card2 = MockCard()
            tab.list.setItemWidget(item2, card2)
            
            # Switch from 1 to 2
            tab._on_selection_changed(item2, item1)
            
            card1.set_selected.assert_called_with(False)
            card2.set_selected.assert_called_with(True)

    def test_on_folder_double_clicked(self, app, mock_icon_manager, mock_sound_manager):
        from app.ui_main import MainWindow, FoldersTab
        from PySide6.QtWidgets import QListWidgetItem
        from PySide6.QtCore import Qt
        
        window = MainWindow()
        window.open_typing_tab = MagicMock()
        
        item = QListWidgetItem()
        item.setData(Qt.UserRole, "C:/Path")
        
        # Normal case
        window.folders_tab.on_folder_double_clicked(item)
        window.open_typing_tab.assert_called_with("C:/Path")
        
        # Edit mode case (should not open)
        window.folders_tab.edit_btn.setChecked(True)
        window.open_typing_tab.reset_mock()
        window.folders_tab.on_folder_double_clicked(item)
        window.open_typing_tab.assert_not_called()

    def test_on_edit_toggled(self, app):
        from app.ui_main import FoldersTab
        from PySide6.QtWidgets import QListWidgetItem
        from unittest.mock import MagicMock
        
        with patch('app.ui_main.FolderCardWidget', SafeFolderCardWidget):
            tab = FoldersTab()
            
            class MockCard(SafeFolderCardWidget):
                pass

            item = QListWidgetItem(tab.list)
            card = MockCard()
            tab.list.setItemWidget(item, card)
            
            tab.on_edit_toggled(True)
            card.set_remove_mode.assert_called_with(True)
            
            tab.on_edit_toggled(False)
            card.set_remove_mode.assert_called_with(False)

    def test_settings_filtering(self, app, mock_icon_manager, mock_sound_manager):
        from app.ui_main import MainWindow
        window = MainWindow()
        window._load_settings_tab_lazy()
        
        # Search for "Confirm"
        window._filter_settings("Confirm")
        # Just check it runs without crash. 
        # Deep inspection of widget visibility is hard with QStackedLayout/Lazy tabs.
        
        # Clear search
        window._filter_settings("")

    def test_profile_management(self, app, mock_icon_manager, mock_sound_manager):
        from app.ui_main import MainWindow
        window = MainWindow()
        
        with patch('app.ui_profile_selector.ProfileManagerDialog.exec'):
             window.open_profile_manager()
             
    def test_open_typing_tab(self, app, mock_icon_manager, mock_sound_manager):
        from app.ui_main import MainWindow
        window = MainWindow()
        window.open_typing_tab("C:/Test")
        assert window.tabs.currentWidget() == window.editor_tab

    def test_open_typing_tab_for_language(self, app, mock_icon_manager, mock_sound_manager):
        from app.ui_main import MainWindow
        window = MainWindow()
        window.open_typing_tab_for_language("Python", ["C:/test.py"])
        assert window.tabs.currentWidget() == window.editor_tab

    def test_scheme_combo_updates_on_profile_switch(self, app, mock_icon_manager, mock_sound_manager, tmp_path):
        """Test that the theme combo box updates when switching profiles."""
        from app.ui_main import MainWindow
        from app.profile_manager import ProfileManager
        from unittest.mock import patch
        import app.settings as settings

        # Setup profile manager with two profiles
        with patch('app.portable_data.get_data_manager') as mock_gdm:
            from app.portable_data import PortableDataManager
            pdm = PortableDataManager()
            pdm._data_dir = tmp_path / "Dev_Type_Data"
            pdm._data_dir.mkdir()
            mock_gdm.return_value = pdm

            pm = ProfileManager()
            pm.create_profile("Profile1")
            pm.create_profile("Profile2")

            # Create DB files for each profile
            pm.switch_profile("Profile1")
            settings.init_db(str(pm.get_current_db_path()))
            settings.set_setting("dark_scheme", "dracula")

            pm.switch_profile("Profile2")
            settings.init_db(str(pm.get_current_db_path()))
            settings.set_setting("dark_scheme", "cyberpunk")

            with patch('app.ui_main.MainWindow.apply_current_theme'), \
                 patch('app.ui_main.MainWindow._emit_initial_settings'):

                window = MainWindow()
                # Load settings tab
                window._load_settings_tab_lazy()

                # Initially on Profile2, switch to Profile1
                window.switch_profile("Profile1")

                # Check that combo shows Profile1's theme
                assert window.scheme_combo.currentText() == "dracula"

                # Switch back to Profile2
                window.switch_profile("Profile2")

                # Check that combo shows Profile2's theme
                assert window.scheme_combo.currentText() == "cyberpunk"
