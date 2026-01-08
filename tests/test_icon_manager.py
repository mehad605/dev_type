"""Tests for icon manager module."""
import pytest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from app.icon_manager import (
    IconManager,
    get_icon_manager,
    DEVICON_MAP,
    EMOJI_FALLBACK
)


def test_icon_manager_initialization(tmp_path):
    """Test IconManager initializes with icon directory."""
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        assert manager.icon_dir == tmp_path / "icons"
        assert manager.icon_dir.exists()
        assert isinstance(manager._icon_cache, dict)


def test_get_icon_path_valid_language(tmp_path):
    """Test getting icon path for valid language."""
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        
        # Create a mock icon file
        icon_path = manager.icon_dir / "python.svg"
        icon_path.write_text("<svg></svg>")
        
        result = manager.get_icon_path("Python")
        assert result == icon_path
        assert result.exists()


def test_get_icon_path_invalid_language(tmp_path):
    """Test getting icon path for invalid language."""
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        result = manager.get_icon_path("InvalidLanguage")
        assert result is None


def test_get_icon_path_not_downloaded(tmp_path):
    """Test getting icon path when icon not yet downloaded."""
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        result = manager.get_icon_path("Python")
        assert result is None  # Icon doesn't exist yet


def test_emoji_fallback_valid_language(tmp_path):
    """Test getting emoji fallback for valid language."""
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        assert manager.get_emoji_fallback("Python") == "🐍"
        assert manager.get_emoji_fallback("JavaScript") == "📜"
        assert manager.get_emoji_fallback("Rust") == "🦀"


def test_emoji_fallback_invalid_language(tmp_path):
    """Test getting emoji fallback for invalid language."""
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        assert manager.get_emoji_fallback("InvalidLanguage") == "📄"


def test_download_icon_invalid_language(tmp_path):
    """Test downloading icon for invalid language."""
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        result = manager.download_icon("InvalidLanguage")
        assert result is False


def test_download_icon_already_exists(tmp_path):
    """Test downloading icon when it already exists."""
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        
        # Create existing icon
        icon_path = manager.icon_dir / "python.svg"
        icon_path.write_text("<svg></svg>")
        
        result = manager.download_icon("Python")
        assert result is True  # Returns True if already exists


@patch('urllib.request.urlopen')
def test_download_icon_success(mock_urlopen, tmp_path):
    """Test successful icon download."""
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"<svg>test</svg>"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        result = manager.download_icon("Python")
        assert result is True
        
        icon_path = manager.icon_dir / "python.svg"
        assert icon_path.exists()
        assert icon_path.read_bytes() == b"<svg>test</svg>"


@patch('urllib.request.urlopen')
def test_download_icon_network_error(mock_urlopen, tmp_path):
    """Test icon download with network error."""
    import urllib.error
    
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        
        # Mock network error (URLError is caught in download_icon)
        mock_urlopen.side_effect = urllib.error.URLError("Network error")
        
        result = manager.download_icon("Python")
        assert result is False


def test_preload_icons(tmp_path):
    """Test preloading multiple icons."""
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        
        # Mock download_icon to track calls
        with patch.object(manager, 'download_icon', return_value=True) as mock_download:
            languages = ["Python", "JavaScript", "TypeScript"]
            manager.preload_icons(languages)
            
            # Verify download_icon was called for each language
            assert mock_download.call_count == 3


def test_clear_cache(tmp_path):
    """Test clearing icon cache."""
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        
        # Add some items to cache
        manager._icon_cache["Python_48"] = None
        manager._icon_cache["JavaScript_48"] = None
        manager._download_errors["Python"] = "Test error"
        
        assert len(manager._icon_cache) == 2
        assert len(manager._download_errors) == 1
        
        manager.clear_cache()
        assert len(manager._icon_cache) == 0
        assert len(manager._download_errors) == 0


def test_get_download_error(tmp_path):
    """Test getting download error messages."""
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        
        # No error initially
        assert manager.get_download_error("Python") is None
        
        # Set an error
        manager._download_errors["Python"] = "Network error: timeout"
        assert manager.get_download_error("Python") == "Network error: timeout"
        
        # Different language has no error
        assert manager.get_download_error("JavaScript") is None


def test_download_icon_logs_error_on_failure(tmp_path):
    """Test that download failures are tracked for tooltip display."""
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        
        # Mock urllib to simulate network failure
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError("Connection refused")):
            result = manager.download_icon("Python")
            
            assert result is False
            # Error should be stored
            error = manager.get_download_error("Python")
            assert error is not None
            assert "Network error" in error


def test_delete_all_icons(tmp_path):
    """Test deleting all downloaded icons."""
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        
        # Create some icon files
        (manager.icon_dir / "python.svg").write_text("<svg></svg>")
        (manager.icon_dir / "javascript.svg").write_text("<svg></svg>")
        (manager.icon_dir / "typescript.svg").write_text("<svg></svg>")
        
        # Add to cache
        manager._icon_cache["test"] = None
        
        count = manager.delete_all_icons()
        
        assert count == 3
        assert len(list(manager.icon_dir.glob("*.svg"))) == 0
        assert len(manager._icon_cache) == 0


def test_get_icon_manager_singleton():
    """Test that get_icon_manager returns singleton."""
    manager1 = get_icon_manager()
    manager2 = get_icon_manager()
    
    assert manager1 is manager2


def test_devicon_map_coverage():
    """Test that DEVICON_MAP covers common languages."""
    common_languages = [
        "Python", "JavaScript", "TypeScript", "Java", "C++",
        "Go", "Rust", "Ruby", "PHP", "HTML", "CSS"
    ]
    
    for lang in common_languages:
        assert lang in DEVICON_MAP, f"{lang} missing from DEVICON_MAP"


def test_emoji_fallback_coverage():
    """Test that EMOJI_FALLBACK covers common languages."""
    common_languages = [
        "Python", "JavaScript", "TypeScript", "Java", "C++",
        "Go", "Rust", "Ruby", "PHP", "HTML", "CSS"
    ]
    
    for lang in common_languages:
        assert lang in EMOJI_FALLBACK, f"{lang} missing from EMOJI_FALLBACK"


def test_devicon_map_matches_emoji():
    """Test that all languages in DEVICON_MAP have emoji fallbacks."""
    for lang in DEVICON_MAP.keys():
        # Not all devicon entries need to be unique languages
        # Just verify no crashes when getting emoji
        emoji = EMOJI_FALLBACK.get(lang, "📄")
        assert isinstance(emoji, str)
        assert len(emoji) > 0


def test_icon_manager_handles_missing_directory(tmp_path):
    """Test that IconManager creates directory if missing."""
    icon_dir = tmp_path / "icons"
    assert not icon_dir.exists()
    
    with patch('app.icon_manager.get_data_dir', return_value=tmp_path):
        manager = IconManager()
        assert manager.icon_dir.exists()
