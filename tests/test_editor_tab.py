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


class TestGhostRaceStats:
    """Test ghost race statistics updates."""

    def test_ghost_race_stats_update_on_loss(self, editor_tab, tmp_path):
        """Test that file stats are updated even when losing a ghost race."""
        from app import stats_db
        from unittest.mock import patch, MagicMock

        # Ensure tab is loaded
        editor_tab.ensure_loaded()

        # Set up a temporary file
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        # Load the file
        editor_tab.on_file_selected(str(test_file))

        # Mock the typing area and engine
        mock_engine = MagicMock()
        mock_engine.state.correct_keystrokes = 5  # User typed 5 correct chars
        mock_engine.state.incorrect_keystrokes = 1
        mock_engine.state.total_keystrokes.return_value = 6
        mock_engine.state.cursor_position = 5
        mock_engine.auto_indent = False
        mock_engine.get_elapsed_time.return_value = 10.0  # 10 seconds

        mock_content = "hello world"
        editor_tab.typing_area.original_content = mock_content
        editor_tab.typing_area.engine = mock_engine

        # Set up race state
        import time
        editor_tab.is_racing = True
        editor_tab._race_start_perf = time.perf_counter() - 10.0  # Started 10 seconds ago
        editor_tab._ghost_finish_elapsed = 5.0  # Ghost finished in 5 seconds (user loses)
        editor_tab._user_finish_elapsed = 10.0  # User took 10 seconds

        # Mock ghost data
        editor_tab._current_ghost_data = {"final_stats": {"time": 5.0}}

        # Patch update_file_stats and other methods to avoid side effects
        with patch('app.editor_tab.stats_db.update_file_stats') as mock_update, \
             patch.object(editor_tab, '_update_progress_indicator'), \
             patch.object(editor_tab, '_check_and_save_ghost'), \
             patch('app.editor_tab.stats_db.record_session_history'), \
             patch('app.editor_tab.stats_db.update_key_stats'), \
             patch('app.editor_tab.stats_db.update_key_confusions'), \
             patch('app.editor_tab.stats_db.update_error_type_stats'), \
             patch('app.editor_tab.SessionResultDialog'):
            # Call the method under test
            stats = {"wpm": 30.0, "accuracy": 0.8, "correct": 5, "incorrect": 1, "time": 10.0}
            editor_tab._handle_user_finished_race(stats)

            # Verify update_file_stats was called
            mock_update.assert_called_once()
            args, kwargs = mock_update.call_args

            # Check that it was called with completed=False (since user didn't finish all chars)
            assert kwargs['completed'] is False
            assert kwargs['wpm'] > 0  # Some WPM calculated
            assert kwargs['accuracy'] > 0
            assert kwargs['auto_indent'] is False

    def test_ghost_race_stats_update_on_win(self, editor_tab, tmp_path):
        """Test that file stats are updated and completed=True when winning a ghost race."""
        from app import stats_db
        from unittest.mock import patch, MagicMock

        # Ensure tab is loaded
        editor_tab.ensure_loaded()

        # Set up a temporary file
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        # Load the file
        editor_tab.on_file_selected(str(test_file))

        # Mock the typing area and engine - user completed all chars
        mock_engine = MagicMock()
        mock_engine.state.correct_keystrokes = 11  # Full content length
        mock_engine.state.incorrect_keystrokes = 1
        mock_engine.state.total_keystrokes.return_value = 12
        mock_engine.state.cursor_position = 11
        mock_engine.auto_indent = False
        mock_engine.get_elapsed_time.return_value = 3.0  # User finished in 3 seconds (wins)

        mock_content = "hello world"
        editor_tab.typing_area.original_content = mock_content
        editor_tab.typing_area.engine = mock_engine

        # Set up race state
        import time
        editor_tab.is_racing = True
        editor_tab._race_start_perf = time.perf_counter() - 3.0
        editor_tab._ghost_finish_elapsed = 5.0  # Ghost took 5 seconds
        editor_tab._user_finish_elapsed = 3.0  # User took 3 seconds (wins)

        # Mock ghost data
        editor_tab._current_ghost_data = {"final_stats": {"time": 5.0}}

        # Patch update_file_stats and other methods to avoid side effects
        with patch('app.editor_tab.stats_db.update_file_stats') as mock_update, \
             patch.object(editor_tab, '_update_progress_indicator'), \
             patch.object(editor_tab, '_check_and_save_ghost'), \
             patch('app.editor_tab.stats_db.record_session_history'), \
             patch('app.editor_tab.stats_db.update_key_stats'), \
             patch('app.editor_tab.stats_db.update_key_confusions'), \
             patch('app.editor_tab.stats_db.update_error_type_stats'), \
             patch('app.editor_tab.SessionResultDialog'):
            # Call the method under test
            stats = {"wpm": 70.0, "accuracy": 0.9, "correct": 11, "incorrect": 1, "time": 3.0}
            editor_tab._handle_user_finished_race(stats)

            # Verify update_file_stats was called
            mock_update.assert_called_once()
            args, kwargs = mock_update.call_args

            # Check that it was called with completed=True (user finished all chars)
            assert kwargs['completed'] is True
            assert kwargs['wpm'] > 0
            assert kwargs['accuracy'] > 0
            assert kwargs['auto_indent'] is False


class TestGhostRaceDataConsistency:
    """Test that ghost race data is stored correctly and displayed consistently."""

    def test_ghost_race_data_storage_and_display_consistency(self, editor_tab, tmp_path):
        """Test that race data is stored correctly and the dialog shows stored data."""
        from unittest.mock import patch, MagicMock
        import time

        # Ensure tab is loaded
        editor_tab.ensure_loaded()

        # Set up a temporary file
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        # Load the file
        editor_tab.on_file_selected(str(test_file))

        # Mock the typing area and engine
        mock_engine = MagicMock()
        mock_engine.state.correct_keystrokes = 11  # User completed all chars
        mock_engine.state.incorrect_keystrokes = 1
        mock_engine.state.total_keystrokes.return_value = 12
        mock_engine.state.cursor_position = 11
        mock_engine.auto_indent = False
        mock_engine.get_elapsed_time.return_value = 3.0  # User finished in 3 seconds (wins)

        mock_content = "hello world"
        editor_tab.typing_area.original_content = mock_content
        editor_tab.typing_area.engine = mock_engine

        # Set up race state - user wins
        editor_tab.is_racing = True
        editor_tab._race_start_perf = time.perf_counter() - 3.0  # Started 3 seconds ago
        editor_tab._ghost_finish_elapsed = 5.0  # Ghost took 5 seconds
        editor_tab._user_finish_elapsed = 3.0  # User took 3 seconds

        # Mock ghost data with stored final stats
        editor_tab._current_ghost_data = {
            "wpm": 40.0,
            "acc": 95.0,
            "final_stats": {
                "wpm": 40.0,
                "accuracy": 0.95,
                "correct": 10,
                "incorrect": 1,
                "time": 5.0
            }
        }

        # Expected calculated race stats
        expected_user_wpm = (11 / 5.0) / (3.0 / 60.0)  # 11 chars / 5 = 2.2 words, / 0.05 min = 44 WPM
        expected_user_accuracy = 11 / 12  # 91.67%

        # Mock all the database/storage calls to capture what gets stored
        stored_stats = {}
        stored_race_info = {}

        def mock_update_file_stats(*args, **kwargs):
            stored_stats.update(kwargs)

        def mock_record_session_history(*args, **kwargs):
            stored_stats['session_recorded'] = True

        def mock_save_ghost(*args, **kwargs):
            stored_stats['ghost_saved'] = True

        with patch('app.editor_tab.stats_db.update_file_stats', side_effect=mock_update_file_stats), \
             patch('app.editor_tab.stats_db.record_session_history', side_effect=mock_record_session_history), \
             patch.object(editor_tab, '_check_and_save_ghost', side_effect=mock_save_ghost), \
             patch.object(editor_tab, '_update_progress_indicator'), \
             patch('app.editor_tab.stats_db.update_key_stats'), \
             patch('app.editor_tab.stats_db.update_key_confusions'), \
             patch('app.editor_tab.stats_db.update_error_type_stats'), \
             patch('app.editor_tab.SessionResultDialog') as mock_dialog:

            # Call the race finish handler
            stats = {"wpm": expected_user_wpm, "accuracy": expected_user_accuracy,
                    "correct": 11, "incorrect": 1, "time": 3.0}
            editor_tab._handle_user_finished_race(stats)

            # Verify SessionResultDialog was called
            assert mock_dialog.called
            call_args = mock_dialog.call_args
            dialog_kwargs = call_args[1]

            # Check that dialog received the correct stats
            dialog_stats = dialog_kwargs['stats']
            assert abs(dialog_stats['wpm'] - expected_user_wpm) < 0.1
            assert abs(dialog_stats['accuracy'] - expected_user_accuracy) < 0.01
            assert dialog_stats['correct'] == 11
            assert dialog_stats['incorrect'] == 1
            assert dialog_stats['time'] == 3.0

            # Check race info
            race_info = dialog_kwargs['race_info']
            assert race_info['ghost_wpm'] == 40.0
            assert race_info['ghost_acc'] == 95.0  # Should be converted to percentage
            assert race_info['ghost_time'] == 5.0
            assert race_info['ghost_final_stats']['correct'] == 10
            assert race_info['ghost_final_stats']['incorrect'] == 1

            # Verify data was stored
            assert stored_stats['completed'] is True  # User finished all chars
            assert stored_stats['session_recorded'] is True

    def test_ghost_race_no_recalculation_in_dialog(self, editor_tab):
        """Test that the dialog displays provided stats without recalculation."""
        from app.session_result_dialog import SessionResultDialog
        from unittest.mock import patch

        # Create dialog with specific stats
        test_stats = {
            'wpm': 75.5,
            'accuracy': 0.923,
            'correct': 123,
            'incorrect': 10,
            'time': 45.2
        }

        race_info = {
            'ghost_wpm': 70.0,
            'ghost_acc': 0.88,
            'ghost_time': 48.1,
            'ghost_final_stats': {
                'correct': 115,
                'incorrect': 15
            }
        }

        # Mock the UI setup to avoid Qt dependencies in test
        with patch.object(SessionResultDialog, 'setup_ui'), \
             patch.object(SessionResultDialog, 'setFixedSize'), \
             patch.object(SessionResultDialog, 'setWindowFlags'), \
             patch.object(SessionResultDialog, 'setAttribute'), \
             patch.object(SessionResultDialog, 'setModal'):

            dialog = SessionResultDialog(
                stats=test_stats,
                is_race=True,
                race_info=race_info,
                filename="test.py"
            )

            # Verify the dialog stored the exact stats provided (no recalculation)
            assert dialog.stats == test_stats
            assert dialog.race_info == race_info

            # The dialog should display these exact values without modification
            # (This is tested implicitly by setup_ui using self.stats directly)
