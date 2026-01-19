import pytest
from pathlib import Path
from app import settings

@pytest.fixture
def db_setup(tmp_path):
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    return db_file


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
    assert settings.get_setting("cursor_type", "") == "blinking"
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
    assert settings.get_setting("ui_font_family", "") == "Segoe UI"
    
    # Test changing settings
    settings.set_setting("font_family", "Fira Code")
    assert settings.get_setting("font_family") == "Fira Code"
    
    settings.set_setting("font_size", "14")
    assert settings.get_setting("font_size") == "14"


def test_typing_settings(tmp_path: Path):
    """Test typing-related settings."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    # Test defaults
    assert settings.get_setting("space_char", "") == "\u2423"
    assert settings.get_setting("pause_delay", "") == "8"
    assert settings.get_setting("tab_width", "") == "4"
    assert settings.get_setting("auto_indent", "") == "1"
    assert settings.get_setting("instant_death_mode", "") == "0"
    
    # Test changing settings
    settings.set_setting("space_char", "·")
    assert settings.get_setting("space_char") == "·"
    
    settings.set_setting("pause_delay", "10")
    assert settings.get_setting("pause_delay") == "10"
    
    settings.set_setting("tab_width", "8")
    assert settings.get_setting("tab_width") == "8"
    
    settings.set_setting("auto_indent", "1")
    assert settings.get_setting("auto_indent") == "1"
    
    settings.set_setting("instant_death_mode", "1")
    assert settings.get_setting("instant_death_mode") == "1"


def test_all_new_settings_exist(db_setup):
    """Test that all default settings are correctly initialized in the database."""
    import app.settings as settings
    from app.settings import SETTING_DEFAULTS
    
    for key in SETTING_DEFAULTS:
        val = settings.get_setting(key)
        assert val is not None, f"Setting '{key}' should have been initialized."


def test_setting_typed_getters(db_setup):
    """Test typed setting retrieval with validation and clamping."""
    import app.settings as settings
    
    # Test Int
    settings.set_setting("test_int", "42")
    assert settings.get_setting_int("test_int", 0) == 42
    assert settings.get_setting_int("test_int_missing", 10) == 10
    assert settings.get_setting_int("test_int", 0, min_val=50) == 50
    assert settings.get_setting_int("test_int", 0, max_val=30) == 30
    settings.set_setting("test_int_invalid", "abc")
    assert settings.get_setting_int("test_int_invalid", 5) == 5
    
    # Test Float
    settings.set_setting("test_float", "3.14")
    assert settings.get_setting_float("test_float", 0.0) == 3.14
    assert settings.get_setting_float("test_float_missing", 1.0) == 1.0
    assert settings.get_setting_float("test_float", 0.0, min_val=5.0) == 5.0
    assert settings.get_setting_float("test_float", 0.0, max_val=1.0) == 1.0
    settings.set_setting("test_float_invalid", "abc")
    assert settings.get_setting_float("test_float_invalid", 0.5) == 0.5
    
    # Test Bool
    settings.set_setting("test_bool_true", "true")
    settings.set_setting("test_bool_1", "1")
    settings.set_setting("test_bool_false", "false")
    assert settings.get_setting_bool("test_bool_true", False) is True
    assert settings.get_setting_bool("test_bool_1", False) is True
    assert settings.get_setting_bool("test_bool_false", True) is False
    assert settings.get_setting_bool("missing_bool", True) is True
    
    # Test Color
    settings.set_setting("test_color", "#ff0000")
    settings.set_setting("invalid_color", "blue")
    assert settings.get_setting_color("test_color") == "#ff0000"
    assert settings.get_setting_color("invalid_color", "#000000") == "#000000"
    assert settings.get_setting_color("missing_color", "#123456") == "#123456"


def test_remove_setting(db_setup):
    """Test removing a setting from DB and cache."""
    import app.settings as settings
    settings.set_setting("to_remove", "value")
    assert settings.get_setting("to_remove") == "value"
    settings.remove_setting("to_remove")
    assert settings.get_setting("to_remove") is None


def test_folder_management(db_setup):
    """Test adding, listing and removing folders."""
    import app.settings as settings
    # Clear any existing folders from setup if necessary
    for f in settings.get_folders():
        settings.remove_folder(f['path'])
        
    settings.add_folder("C:/Path1")
    settings.add_folder("C:/Path1") # Dupe insertion OR IGNORE
    assert "C:/Path1" in [f['path'] for f in settings.get_folders()]
    assert len(settings.get_folders()) == 1
    
    settings.add_folder("C:/Path2")
    assert "C:/Path2" in [f['path'] for f in settings.get_folders()]
    assert len(settings.get_folders()) == 2
    
    settings.remove_folder("C:/Path1")
    assert "C:/Path1" not in [f['path'] for f in settings.get_folders()]
    assert len(settings.get_folders()) == 1


def test_data_dirs(db_setup):
    """Test directory path resolution."""
    import app.settings as settings
    assert settings.get_data_dir() is not None
    assert settings.get_icons_dir() is not None
    assert settings.get_current_db_path() is not None
    
    # Coverage for get_default
    assert settings.get_default("dark_scheme") == "nord"
    assert settings.get_default("non_existent") == ""
