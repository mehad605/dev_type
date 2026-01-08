"""Tests for LanguagesTab and LanguageCard widgets."""
import sys
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


class TestLanguageCard:
    """Test LanguageCard widget."""
    
    def test_language_card_initialization(self, app, db_setup):
        """Test LanguageCard initializes correctly."""
        from app.languages_tab import LanguageCard
        
        card = LanguageCard(
            language="Python",
            files=["/path/test.py", "/path/other.py"],
            average_wpm=75.5,
            sample_size=10,
            completed_count=1
        )
        
        assert card is not None
        assert card.language == "Python"
        assert len(card.files) == 2
    
    def test_language_card_no_stats(self, app, db_setup):
        """Test LanguageCard with no average WPM."""
        from app.languages_tab import LanguageCard
        
        card = LanguageCard(
            language="JavaScript",
            files=["/path/test.js"],
            average_wpm=None,
            sample_size=0,
            completed_count=0
        )
        
        assert card.language == "JavaScript"
        assert "No sessions" in card.wpm_label.text()
    
    def test_language_card_with_wpm(self, app, db_setup):
        """Test LanguageCard displays WPM correctly."""
        from app.languages_tab import LanguageCard
        
        card = LanguageCard(
            language="Rust",
            files=["/path/test.rs"],
            average_wpm=85.3,
            sample_size=5,
            completed_count=1
        )
        
        assert "85" in card.wpm_label.text()
        assert "WPM" in card.wpm_label.text()
    
    def test_language_card_click_signal(self, app, db_setup):
        """Test that clicking card emits signal."""
        from app.languages_tab import LanguageCard
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        
        card = LanguageCard(
            language="Go",
            files=["/path/test.go"],
            average_wpm=60.0,
            sample_size=3,
            completed_count=0
        )
        
        signals_received = []
        card.clicked.connect(lambda lang, files: signals_received.append((lang, files)))
        
        # Simulate click
        QTest.mouseClick(card, Qt.LeftButton)
        
        assert len(signals_received) == 1
        assert signals_received[0][0] == "Go"
    
    def test_language_card_completion_display(self, app, db_setup):
        """Test that completion percentage is displayed."""
        from app.languages_tab import LanguageCard
        
        card = LanguageCard(
            language="Python",
            files=["/a.py", "/b.py", "/c.py", "/d.py"],  # 4 files
            average_wpm=None,
            sample_size=0,
            completed_count=2  # 2 completed = 50%
        )
        
        # Card should show completion info
        assert card is not None


class TestLanguagesTab:
    """Test LanguagesTab widget."""
    
    def test_languages_tab_initialization(self, app, db_setup):
        """Test LanguagesTab initializes correctly."""
        from app.languages_tab import LanguagesTab
        
        tab = LanguagesTab()
        
        assert tab is not None
        assert tab._loaded is False
        assert tab._loading is False
        # _cached_language_files may have data from cache file
        assert isinstance(tab._cached_language_files, dict)
    
    def test_languages_tab_has_card_container(self, app, db_setup):
        """Test that tab has card container."""
        from app.languages_tab import LanguagesTab
        
        tab = LanguagesTab()
        
        assert hasattr(tab, 'card_container')
        assert hasattr(tab, 'card_layout')
    
    def test_show_message(self, app, db_setup):
        """Test _show_message displays correctly."""
        from app.languages_tab import LanguagesTab
        
        tab = LanguagesTab()
        tab._show_message("Test message")
        
        assert tab._status_label is not None
        assert "Test message" in tab._status_label.text()
    
    def test_clear_cards(self, app, db_setup):
        """Test _clear_cards removes all widgets."""
        from app.languages_tab import LanguagesTab
        
        tab = LanguagesTab()
        tab._show_message("First message")
        
        assert tab.card_layout.count() > 0
        
        tab._clear_cards()
        
        assert tab.card_layout.count() == 0
        assert tab._status_label is None
    
    def test_mark_dirty(self, app, db_setup):
        """Test mark_dirty resets loaded state."""
        from app.languages_tab import LanguagesTab
        
        tab = LanguagesTab()
        tab._loaded = True
        tab._cached_language_files = {"Python": ["/test.py"]}
        
        tab.mark_dirty()
        
        assert tab._loaded is False
        assert tab._cached_language_files == {}
    
    @patch('app.languages_tab.settings')
    def test_ensure_loaded_no_folders(self, mock_settings, app, db_setup):
        """Test ensure_loaded with no folders."""
        from app.languages_tab import LanguagesTab
        
        mock_settings.get_folders.return_value = []
        
        tab = LanguagesTab()
        tab.ensure_loaded()
        
        assert tab._loaded is True
        assert "No folders" in tab._status_label.text()
    
    def test_populate_cards_empty(self, app, db_setup):
        """Test _populate_cards with empty data."""
        from app.languages_tab import LanguagesTab
        
        tab = LanguagesTab()
        tab._populate_cards({})
        
        assert "No code files" in tab._status_label.text()
    
    @patch('app.languages_tab.stats_db')
    @patch('app.languages_tab._get_icon_manager')
    def test_populate_cards_with_data(self, mock_icon_mgr, mock_stats_db, app, db_setup):
        """Test _populate_cards with language data."""
        from app.languages_tab import LanguagesTab
        
        # Setup mocks
        mock_icon = MagicMock()
        mock_icon.get_icon.return_value = None
        mock_icon.get_emoji_fallback.return_value = "🐍"
        mock_icon_mgr.return_value = mock_icon
        
        mock_stats_db.get_file_stats_for_files.return_value = {}
        mock_stats_db.get_recent_wpm_average.return_value = {"average": 70.0, "count": 5}
        
        tab = LanguagesTab()
        tab._populate_cards({
            "Python": ["/test.py", "/main.py"],
            "JavaScript": ["/app.js"]
        })
        
        # Should have cards (not just status message)
        assert tab._status_label is None
        assert tab.card_layout.count() >= 2


class TestLanguageScanTask:
    """Test background scan task."""
    
    def test_scan_task_signals_exist(self, app):
        """Test that scan task has completed signal."""
        from app.languages_tab import _LanguageScanTask
        
        task = _LanguageScanTask(
            folders_snapshot=("/folder1", "/folder2"),
            scanner=lambda folders: {}
        )
        
        assert hasattr(task.signals, 'completed')
    
    def test_scan_task_runs_scanner(self, app):
        """Test that scan task calls the scanner function."""
        from app.languages_tab import _LanguageScanTask
        
        scanner_called = []
        def mock_scanner(folders):
            scanner_called.append(folders)
            return {"Python": ["/test.py"]}
        
        task = _LanguageScanTask(
            folders_snapshot=("/folder1",),
            scanner=mock_scanner
        )
        
        # Run synchronously for testing
        task.run()
        
        assert len(scanner_called) == 1
        assert "/folder1" in scanner_called[0]
