"""Tests for the EditorTab widget."""
import os
import sys
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def app():
    """Create QApplication for testing."""
    from PySide6.QtWidgets import QApplication
    
    _app = QApplication.instance()
    if _app is None:
        _app = QApplication(sys.argv)
    yield _app


@pytest.fixture
def db_setup(tmp_path):
    """Set up temporary database for testing."""
    from app import settings
    from app import stats_db
    
    db_path = str(tmp_path / "test_stats.db")
    settings.init_db(db_path)
    stats_db.init_stats_tables()
    yield db_path


@pytest.fixture
def editor_tab(app, db_setup):
    """Create an EditorTab instance."""
    from app.editor_tab import EditorTab
    
    tab = EditorTab()
    yield tab


class TestEditorTabLazyLoading:
    """Test EditorTab lazy loading behavior."""
    
    def test_initial_state_not_loaded(self, editor_tab):
        """Test that EditorTab starts in unloaded state."""
        assert editor_tab._loaded is False
        assert editor_tab.current_file is None
    
    def test_ensure_loaded_sets_flag(self, editor_tab):
        """Test that ensure_loaded sets the loaded flag."""
        editor_tab.ensure_loaded()
        assert editor_tab._loaded is True
    
    def test_ensure_loaded_idempotent(self, editor_tab):
        """Test that ensure_loaded can be called multiple times safely."""
        editor_tab.ensure_loaded()
        editor_tab.ensure_loaded()
        editor_tab.ensure_loaded()
        assert editor_tab._loaded is True
    
    def test_widgets_created_after_load(self, editor_tab):
        """Test that widgets are created after ensure_loaded."""
        editor_tab.ensure_loaded()
        
        assert hasattr(editor_tab, 'file_tree')
        assert hasattr(editor_tab, 'typing_area')
        assert hasattr(editor_tab, 'stats_display')
        assert hasattr(editor_tab, 'reset_btn')


class TestEditorTabRaceState:
    """Test race-related state management."""
    
    def test_initial_race_state(self, editor_tab):
        """Test initial race state is inactive."""
        assert editor_tab.is_racing is False
        assert editor_tab._race_pending_start is False
        assert editor_tab._current_ghost_data is None
    
    def test_ghost_engine_initial_state(self, editor_tab):
        """Test ghost engine initial state."""
        assert editor_tab._ghost_engine is None
        assert editor_tab._ghost_keystrokes == []
        assert editor_tab._ghost_index == 0
        assert editor_tab._ghost_cursor_position == 0


class TestEditorTabInstantDeath:
    """Test instant death mode functionality."""
    
    def test_set_instant_death_mode_enabled(self, editor_tab):
        """Test enabling instant death mode."""
        editor_tab.ensure_loaded()
        
        editor_tab._set_instant_death_mode(True, persist=False)
        
        assert editor_tab.instant_death_btn.isChecked() is True
        assert "ON" in editor_tab.instant_death_btn.text()
    
    def test_set_instant_death_mode_disabled(self, editor_tab):
        """Test disabling instant death mode."""
        editor_tab.ensure_loaded()
        
        editor_tab._set_instant_death_mode(False, persist=False)
        
        assert editor_tab.instant_death_btn.isChecked() is False
        assert "OFF" in editor_tab.instant_death_btn.text()
    
    def test_instant_death_button_signal_blocked(self, editor_tab):
        """Test that _set_instant_death_mode blocks signals during update."""
        editor_tab.ensure_loaded()
        
        # Setting mode shouldn't trigger toggle callback
        callback_called = []
        original = editor_tab.on_instant_death_toggled
        editor_tab.on_instant_death_toggled = lambda e: callback_called.append(e)
        
        # This should NOT trigger the callback
        editor_tab._set_instant_death_mode(True, persist=False)
        
        assert len(callback_called) == 0
        editor_tab.on_instant_death_toggled = original


class TestEditorTabFileOperations:
    """Test file loading and operations."""
    
    def test_load_file(self, editor_tab, tmp_path):
        """Test loading a file."""
        editor_tab.ensure_loaded()
        
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')", encoding='utf-8')
        
        editor_tab.on_file_selected(str(test_file))
        
        assert editor_tab.current_file == str(test_file)
        assert editor_tab.typing_area.original_content == "print('hello')"
    
    def test_reset_without_file(self, editor_tab):
        """Test reset when no file is loaded."""
        editor_tab.ensure_loaded()
        
        # Should not raise exception
        editor_tab.on_reset_clicked()
        
        assert editor_tab.current_file is None
    
    def test_reset_clears_race_state(self, editor_tab, tmp_path):
        """Test that reset clears race state."""
        editor_tab.ensure_loaded()
        
        # Load a file
        test_file = tmp_path / "test.py"
        test_file.write_text("test", encoding='utf-8')
        editor_tab.on_file_selected(str(test_file))
        
        # Simulate race state
        editor_tab.is_racing = True
        editor_tab._race_pending_start = True
        
        editor_tab.on_reset_clicked()
        
        # Race should be cancelled
        assert editor_tab.is_racing is False
        assert editor_tab._race_pending_start is False


class TestEditorTabProgressIndicator:
    """Test progress indicator functionality."""
    
    def test_progress_widgets_exist(self, editor_tab):
        """Test that progress widgets are created."""
        editor_tab.ensure_loaded()
        
        assert hasattr(editor_tab, 'user_progress_bar')
        assert hasattr(editor_tab, 'ghost_progress_bar')
        assert hasattr(editor_tab, 'user_progress_label')
        assert hasattr(editor_tab, 'ghost_progress_label')
    
    def test_ghost_progress_initially_hidden(self, editor_tab):
        """Test that ghost progress widget is initially hidden."""
        editor_tab.ensure_loaded()
        
        assert editor_tab.ghost_progress_widget.isVisible() is False


class TestEditorTabStatsUpdate:
    """Test stats update functionality."""
    
    def test_stats_display_update(self, editor_tab, tmp_path):
        """Test that stats display gets updated."""
        editor_tab.ensure_loaded()
        
        # Load a file
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello", encoding='utf-8')
        editor_tab.on_file_selected(str(test_file))
        
        # Trigger stats update
        editor_tab.on_stats_updated()
        
        # Should not raise exception
        assert editor_tab.stats_display is not None
