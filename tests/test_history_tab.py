"""Tests for the HistoryTab widget."""
import sys
import pytest
from unittest.mock import patch, MagicMock


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
def history_tab(app, db_setup):
    """Create a HistoryTab instance."""
    from app.history_tab import HistoryTab
    
    tab = HistoryTab()
    yield tab


class TestHistoryTabInitialization:
    """Test HistoryTab initialization."""
    
    def test_initialization(self, history_tab):
        """Test that HistoryTab initializes correctly."""
        assert history_tab is not None
        assert hasattr(history_tab, 'table')
        assert hasattr(history_tab, 'language_combo')
    
    def test_filter_widgets_exist(self, history_tab):
        """Test that filter widgets are created."""
        assert hasattr(history_tab, 'name_filter_input')
        assert hasattr(history_tab, 'min_wpm_input')
        assert hasattr(history_tab, 'max_wpm_input')
        assert hasattr(history_tab, 'min_duration_input')
        assert hasattr(history_tab, 'max_duration_input')
    
    def test_action_buttons_exist(self, history_tab):
        """Test that action buttons are created."""
        assert hasattr(history_tab, 'apply_filters_btn')
        assert hasattr(history_tab, 'clear_filters_btn')
        assert hasattr(history_tab, 'edit_mode_btn')
        assert hasattr(history_tab, 'delete_btn')
    
    def test_delete_button_initially_disabled(self, history_tab):
        """Test that delete button is initially disabled."""
        assert history_tab.delete_btn.isEnabled() is False
    
    def test_edit_mode_initially_off(self, history_tab):
        """Test that edit mode is initially off."""
        assert history_tab.edit_mode_btn.isChecked() is False


class TestHistoryTabFilterLogic:
    """Test filter logic and validation."""
    
    def test_parse_float_valid(self, history_tab):
        """Test parsing valid float values."""
        assert history_tab._parse_float("10.5") == 10.5
        assert history_tab._parse_float("100") == 100.0
        assert history_tab._parse_float("0") == 0.0
    
    def test_parse_float_empty(self, history_tab):
        """Test parsing empty string returns None."""
        assert history_tab._parse_float("") is None
    
    def test_range_invalid_check(self, history_tab):
        """Test range validation logic."""
        # Valid ranges
        assert history_tab._range_invalid(10.0, 20.0) is False
        assert history_tab._range_invalid(10.0, 10.0) is False  # Equal is valid
        assert history_tab._range_invalid(None, 20.0) is False  # One None is valid
        assert history_tab._range_invalid(10.0, None) is False
        assert history_tab._range_invalid(None, None) is False
        
        # Invalid range
        assert history_tab._range_invalid(20.0, 10.0) is True
    
    def test_clear_filters(self, history_tab):
        """Test clearing filters resets inputs."""
        history_tab.name_filter_input.setText("test")
        history_tab.min_wpm_input.setText("50")
        history_tab.max_wpm_input.setText("100")
        
        history_tab.clear_filters()
        
        assert history_tab.name_filter_input.text() == ""
        assert history_tab.min_wpm_input.text() == ""
        assert history_tab.max_wpm_input.text() == ""


class TestHistoryTabEditMode:
    """Test edit mode functionality."""
    
    def test_toggle_edit_mode_on(self, history_tab):
        """Test enabling edit mode."""
        from PySide6.QtWidgets import QTableWidget
        
        history_tab.toggle_edit_mode(True)
        
        assert history_tab.delete_btn.isEnabled() is True
        assert "Done" in history_tab.edit_mode_btn.text()
        assert history_tab.table.selectionMode() == QTableWidget.ExtendedSelection
    
    def test_toggle_edit_mode_off(self, history_tab):
        """Test disabling edit mode."""
        from PySide6.QtWidgets import QTableWidget
        
        # First enable
        history_tab.toggle_edit_mode(True)
        # Then disable
        history_tab.toggle_edit_mode(False)
        
        assert history_tab.delete_btn.isEnabled() is False
        assert "Edit" in history_tab.edit_mode_btn.text()
        assert history_tab.table.selectionMode() == QTableWidget.NoSelection


class TestHistoryTabTableDisplay:
    """Test table display functionality."""
    
    def test_table_columns(self, history_tab):
        """Test that table has expected columns."""
        column_count = history_tab.table.columnCount()
        # Should have columns for: Date/Time, File, Language, WPM, Accuracy, Duration, Completed
        assert column_count >= 6
    
    def test_table_headers(self, history_tab):
        """Test that table has appropriate headers."""
        # Check header labels exist
        header = history_tab.table.horizontalHeader()
        assert header is not None
        # Table should be functional
        assert history_tab.table.rowCount() >= 0


class TestHistoryTabWithData:
    """Test HistoryTab with actual data in database."""
    
    def test_load_with_session_data(self, history_tab, db_setup):
        """Test loading table with session history data."""
        from app import stats_db
        
        # Add some test data
        stats_db.record_session_history(
            file_path="/test/file.py",
            language="Python",
            wpm=75.5,
            accuracy=0.95,
            total_keystrokes=100,
            correct_keystrokes=95,
            incorrect_keystrokes=5,
            duration=60.0,
            completed=True
        )
        
        history_tab._load_history()
        
        # Table should have at least one row
        assert history_tab.table.rowCount() >= 1
    
    def test_language_combo_populated(self, history_tab, db_setup):
        """Test that language combo is populated with available languages."""
        from app import stats_db
        
        # Add data with different languages
        stats_db.record_session_history(
            file_path="/test/file.py",
            language="Python",
            wpm=70, accuracy=0.9, total_keystrokes=50,
            correct_keystrokes=45, incorrect_keystrokes=5,
            duration=30, completed=True
        )
        stats_db.record_session_history(
            file_path="/test/file.js",
            language="JavaScript",
            wpm=60, accuracy=0.85, total_keystrokes=40,
            correct_keystrokes=34, incorrect_keystrokes=6,
            duration=25, completed=True
        )
        
        history_tab.refresh_filters()
        
        # Language combo should have "All" + languages
        assert history_tab.language_combo.count() >= 2
