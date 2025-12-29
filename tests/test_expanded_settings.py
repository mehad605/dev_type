"""Tests for expanded settings functionality."""
from pathlib import Path
from app import settings


def test_color_settings(tmp_path: Path):
    """Test color settings persistence."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    # Test default colors
    assert settings.get_setting("color_untyped", "") == "#6272a4"
    assert settings.get_setting("color_correct", "") == "#50fa7b"
    assert settings.get_setting("color_incorrect", "") == "#ff5555"
    
    # Test setting custom colors
    settings.set_setting("color_untyped", "#aaaaaa")
    assert settings.get_setting("color_untyped") == "#aaaaaa"
    
    settings.set_setting("color_correct", "#00aa00")
    assert settings.get_setting("color_correct") == "#00aa00"


def test_cursor_settings(tmp_path: Path):
    """Test cursor settings persistence."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    # Test defaults
    assert settings.get_setting("cursor_type", "") == "static"
    assert settings.get_setting("cursor_style", "") == "underscore"
    
    # Test changing settings
    settings.set_setting("cursor_type", "static")
    assert settings.get_setting("cursor_type") == "static"
    
    settings.set_setting("cursor_style", "underscore")
    assert settings.get_setting("cursor_style") == "underscore"


def test_font_settings(tmp_path: Path):
    """Test font settings persistence."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    # Test defaults
    assert settings.get_setting("font_family", "") == "JetBrains Mono"
    assert settings.get_setting("font_size", "") == "12"
    assert settings.get_setting("font_ligatures", "") == "0"
    
    # Test changing settings
    settings.set_setting("font_family", "Fira Code")
    assert settings.get_setting("font_family") == "Fira Code"
    
    settings.set_setting("font_size", "14")
    assert settings.get_setting("font_size") == "14"
    
    settings.set_setting("font_ligatures", "1")
    assert settings.get_setting("font_ligatures") == "1"


def test_typing_settings(tmp_path: Path):
    """Test typing-related settings."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    # Test defaults
    assert settings.get_setting("space_char", "") == "␣"
    assert settings.get_setting("pause_delay", "") == "4"
    
    # Test changing settings
    settings.set_setting("space_char", "·")
    assert settings.get_setting("space_char") == "·"
    
    settings.set_setting("pause_delay", "10")
    assert settings.get_setting("pause_delay") == "10"


def test_all_new_settings_exist(tmp_path: Path):
    """Test that all new settings have defaults after init."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    expected_settings = [
        "theme", "dark_scheme", "delete_confirm", "pause_delay",
        "color_untyped", "color_correct", "color_incorrect", 
        "color_paused_highlight", "color_cursor",
        "cursor_type", "cursor_style",
        "font_family", "font_size", "font_ligatures",
        "space_char"
    ]
    
    for setting_key in expected_settings:
        value = settings.get_setting(setting_key)
        assert value is not None, f"Setting '{setting_key}' should have a default value"
        assert value != "", f"Setting '{setting_key}' should not be empty"
