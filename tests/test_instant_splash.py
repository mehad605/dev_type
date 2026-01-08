"""Tests for instant_splash.py - Tkinter splash screen."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sqlite3


@pytest.fixture
def db_setup(tmp_path):
    """Create test database with settings."""
    db_path = tmp_path / "typing_stats.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("INSERT INTO settings (key, value) VALUES ('theme', 'dark')")
    cur.execute("INSERT INTO settings (key, value) VALUES ('dark_scheme', 'dracula')")
    conn.commit()
    conn.close()
    return db_path


class TestInstantSplashInit:
    """Test InstantSplash initialization."""
    
    def test_splash_initialization(self):
        """Test InstantSplash initializes with default values."""
        from app.instant_splash import InstantSplash
        
        splash = InstantSplash()
        
        assert splash._root is None
        assert splash._progress_canvas is None
        assert splash._progress_rect is None
        assert splash._status_label is None
        assert splash._bar_width == 360
        assert splash._bar_height == 8
        assert splash._progress == 0
    
    def test_splash_bar_dimensions(self):
        """Test default progress bar dimensions."""
        from app.instant_splash import InstantSplash
        
        splash = InstantSplash()
        
        assert splash._bar_width > 0
        assert splash._bar_height > 0


class TestGetThemeColors:
    """Test _get_theme_colors method."""
    
    def test_returns_dict(self):
        """Test that _get_theme_colors returns a dict."""
        from app.instant_splash import InstantSplash
        
        splash = InstantSplash()
        colors = splash._get_theme_colors()
        
        assert isinstance(colors, dict)
    
    def test_has_required_keys(self):
        """Test that returned dict has all required color keys."""
        from app.instant_splash import InstantSplash
        
        splash = InstantSplash()
        colors = splash._get_theme_colors()
        
        required_keys = ["bg", "border", "title", "subtitle", "status", "progress_bg", "progress_fill"]
        for key in required_keys:
            assert key in colors
    
    def test_colors_are_strings(self):
        """Test that color values are strings."""
        from app.instant_splash import InstantSplash
        
        splash = InstantSplash()
        colors = splash._get_theme_colors()
        
        for key, value in colors.items():
            assert isinstance(value, str)
    
    def test_colors_are_hex(self):
        """Test that colors are hex format."""
        from app.instant_splash import InstantSplash
        
        splash = InstantSplash()
        colors = splash._get_theme_colors()
        
        for key, value in colors.items():
            assert value.startswith("#")


class TestSplashUpdate:
    """Test splash update method."""
    
    def test_update_without_root_does_nothing(self):
        """Test update when _root is None does nothing."""
        from app.instant_splash import InstantSplash
        
        splash = InstantSplash()
        # Should not raise
        splash.update("Loading...", 50)
        
        assert splash._progress == 0  # Not updated since no root
    
    def test_update_progress_clamped(self):
        """Test that progress is clamped to 0-100."""
        from app.instant_splash import InstantSplash
        
        splash = InstantSplash()
        # Mock the root and components
        splash._root = MagicMock()
        splash._status_label = MagicMock()
        splash._progress_canvas = MagicMock()
        splash._progress_rect = MagicMock()
        
        # Test over 100
        splash.update("Test", 150)
        assert splash._progress == 100
        
        # Test under 0
        splash.update("Test", -50)
        assert splash._progress == 0


class TestSplashClose:
    """Test splash close method."""
    
    def test_close_without_root(self):
        """Test close when _root is None."""
        from app.instant_splash import InstantSplash
        
        splash = InstantSplash()
        # Should not raise
        splash.close()
        
        assert splash._root is None
    
    def test_close_with_root(self):
        """Test close destroys root."""
        from app.instant_splash import InstantSplash
        
        splash = InstantSplash()
        mock_root = MagicMock()
        splash._root = mock_root
        
        splash.close()
        
        # Root is set to None after destroy, so we check the mock directly
        mock_root.destroy.assert_called_once()
    
    def test_close_sets_root_none(self):
        """Test close sets _root to None."""
        from app.instant_splash import InstantSplash
        
        splash = InstantSplash()
        splash._root = MagicMock()
        
        splash.close()
        
        assert splash._root is None


class TestCreateInstantSplash:
    """Test create_instant_splash factory function."""
    
    def test_function_exists(self):
        """Test create_instant_splash function is importable."""
        from app.instant_splash import create_instant_splash
        
        assert callable(create_instant_splash)
    
    @patch('app.instant_splash.InstantSplash')
    def test_returns_splash_on_success(self, mock_class):
        """Test returns splash instance when show() succeeds."""
        from app.instant_splash import create_instant_splash
        
        mock_splash = MagicMock()
        mock_splash.show.return_value = True
        mock_class.return_value = mock_splash
        
        result = create_instant_splash()
        
        assert result == mock_splash
    
    @patch('app.instant_splash.InstantSplash')
    def test_returns_none_on_failure(self, mock_class):
        """Test returns None when show() fails."""
        from app.instant_splash import create_instant_splash
        
        mock_splash = MagicMock()
        mock_splash.show.return_value = False
        mock_class.return_value = mock_splash
        
        result = create_instant_splash()
        
        assert result is None


class TestSplashThemeSchemes:
    """Test theme scheme mappings in splash."""
    
    def test_default_dracula_colors(self):
        """Test default colors match Dracula theme."""
        from app.instant_splash import InstantSplash
        
        splash = InstantSplash()
        colors = splash._get_theme_colors()
        
        # Dracula defaults
        assert colors["bg"] == "#282a36"
        assert colors["border"] == "#bd93f9"
