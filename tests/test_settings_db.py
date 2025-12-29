"""Tests for settings database module."""
import tempfile
from pathlib import Path
import app.settings as settings


def test_settings_db_roundtrip(tmp_path: Path):
    """Test basic database operations."""
    db_file = tmp_path / "data.db"
    # init
    settings.init_db(str(db_file))
    # default setting exists
    val = settings.get_setting("theme", "")
    assert val in ("dark", "")
    # set and get
    settings.set_setting("test_key", "value1")
    assert settings.get_setting("test_key") == "value1"
    # folders
    settings.add_folder("/tmp/foo")
    settings.add_folder("/tmp/bar")
    folders = settings.get_folders()
    assert "/tmp/foo" in folders
    assert "/tmp/bar" in folders
    # remove
    settings.remove_folder("/tmp/foo")
    folders = settings.get_folders()
    assert "/tmp/foo" not in folders


def test_settings_db_initialization(tmp_path: Path):
    """Test database initialization."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    # Should create database file
    assert db_file.exists()


def test_default_settings_created(tmp_path: Path):
    """Test that default settings are created on init."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    # Check some default settings exist
    theme = settings.get_setting("theme", "")
    assert theme in ("dark", "light", "")
    
    assert settings.get_setting("font_family", "") != ""
    assert settings.get_setting("font_size", "") != ""


def test_get_setting_default(tmp_path: Path):
    """Test getting setting with default value."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    value = settings.get_setting("nonexistent_key", "default_value")
    assert value == "default_value"


def test_update_existing_setting(tmp_path: Path):
    """Test updating an existing setting."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    settings.set_setting("test_key", "value1")
    settings.set_setting("test_key", "value2")
    
    value = settings.get_setting("test_key")
    assert value == "value2"


def test_get_folders_empty(tmp_path: Path):
    """Test getting folders when none added."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    folders = settings.get_folders()
    assert isinstance(folders, list)


def test_multiple_folders(tmp_path: Path):
    """Test managing multiple folders."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    folders = ["/folder1", "/folder2", "/folder3"]
    for folder in folders:
        settings.add_folder(folder)
    
    retrieved = settings.get_folders()
    for folder in folders:
        assert folder in retrieved


def test_duplicate_folder_not_added_twice(tmp_path: Path):
    """Test that duplicate folders aren't added."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    folder = "/same/folder"
    settings.add_folder(folder)
    settings.add_folder(folder)
    
    folders = settings.get_folders()
    assert folders.count(folder) == 1


def test_settings_persist_across_init(tmp_path: Path):
    """Test that settings persist across database reinitializations."""
    db_file = tmp_path / "test.db"
    
    # First init
    settings.init_db(str(db_file))
    settings.set_setting("persist_test", "value123")
    
    # Second init (simulating app restart)
    settings.init_db(str(db_file))
    value = settings.get_setting("persist_test")
    
    assert value == "value123"


def test_all_default_settings_exist(tmp_path: Path):
    """Test that all expected default settings are created."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    expected_settings = [
        "theme", "dark_scheme", "font_family", "font_size",
        "color_untyped", "color_correct", "color_incorrect",
        "cursor_type", "cursor_style", "pause_delay",
        "allow_continue_mistakes"
    ]
    
    for setting_key in expected_settings:
        value = settings.get_setting(setting_key)
        assert value is not None, f"Setting '{setting_key}' should exist"


def test_boolean_settings(tmp_path: Path):
    """Test boolean settings stored as strings."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    settings.set_setting("test_bool", "1")
    assert settings.get_setting("test_bool") == "1"
    
    settings.set_setting("test_bool", "0")
    assert settings.get_setting("test_bool") == "0"


def test_numeric_settings(tmp_path: Path):
    """Test numeric settings stored as strings."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    settings.set_setting("test_num", "42")
    assert settings.get_setting("test_num") == "42"
    
    settings.set_setting("test_float", "3.14")
    assert settings.get_setting("test_float") == "3.14"
