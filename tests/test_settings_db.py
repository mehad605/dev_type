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
    folders = [f['path'] for f in settings.get_folders()]
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
    
    retrieved = [f['path'] for f in settings.get_folders()]
    for folder in folders:
        assert folder in retrieved


def test_duplicate_folder_not_added_twice(tmp_path: Path):
    """Test that duplicate folders aren't added."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    folder = "/same/folder"
    settings.add_folder(folder)
    settings.add_folder(folder)
    
    folders = [f['path'] for f in settings.get_folders()]
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
        "dark_scheme", "font_family", "font_size",
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


def test_get_setting_int_default(tmp_path: Path):
    """Test get_setting_int returns default for missing key."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    result = settings.get_setting_int("nonexistent_key_xyz", 42)
    assert result == 42


def test_get_setting_int_valid(tmp_path: Path):
    """Test get_setting_int parses valid integer."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    settings.set_setting("test_int_key", "123")
    result = settings.get_setting_int("test_int_key", 0)
    assert result == 123


def test_get_setting_int_invalid_returns_default(tmp_path: Path):
    """Test get_setting_int returns default for invalid value."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    settings.set_setting("test_int_invalid", "not_a_number")
    result = settings.get_setting_int("test_int_invalid", 99)
    assert result == 99


def test_get_setting_int_clamping(tmp_path: Path):
    """Test get_setting_int clamps to min/max range."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    settings.set_setting("test_int_clamp", "200")
    result = settings.get_setting_int("test_int_clamp", 50, min_val=0, max_val=100)
    assert result == 100
    
    settings.set_setting("test_int_clamp", "-50")
    result = settings.get_setting_int("test_int_clamp", 50, min_val=0, max_val=100)
    assert result == 0


def test_get_setting_float_default(tmp_path: Path):
    """Test get_setting_float returns default for missing key."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    result = settings.get_setting_float("nonexistent_float_xyz", 3.14)
    assert result == 3.14


def test_get_setting_float_valid(tmp_path: Path):
    """Test get_setting_float parses valid float."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    settings.set_setting("test_float_key", "7.5")
    result = settings.get_setting_float("test_float_key", 0.0)
    assert result == 7.5


def test_get_setting_float_clamping(tmp_path: Path):
    """Test get_setting_float clamps to min/max range."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    settings.set_setting("test_float_clamp", "100.0")
    result = settings.get_setting_float("test_float_clamp", 5.0, min_val=0.0, max_val=60.0)
    assert result == 60.0


def test_get_setting_bool_true_values(tmp_path: Path):
    """Test get_setting_bool recognizes true values."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    for val in ["true", "True", "TRUE", "1", "yes", "YES", "on", "ON"]:
        settings.set_setting("test_bool_typed", val)
        assert settings.get_setting_bool("test_bool_typed", False) is True


def test_get_setting_bool_false_values(tmp_path: Path):
    """Test get_setting_bool returns False for other values."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    for val in ["false", "False", "0", "no", "off", "random", ""]:
        settings.set_setting("test_bool_typed", val)
        assert settings.get_setting_bool("test_bool_typed", True) is False


def test_get_setting_bool_missing_returns_default(tmp_path: Path):
    """Test get_setting_bool returns default for missing key."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    assert settings.get_setting_bool("nonexistent_bool_xyz", True) is True
    assert settings.get_setting_bool("nonexistent_bool_xyz", False) is False


def test_get_setting_color_valid(tmp_path: Path):
    """Test get_setting_color returns valid hex color."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    settings.set_setting("test_color", "#FF0000")
    result = settings.get_setting_color("test_color", "#FFFFFF")
    assert result == "#FF0000"


def test_get_setting_color_valid_short(tmp_path: Path):
    """Test get_setting_color accepts 3-char hex colors."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    settings.set_setting("test_color", "#F00")
    result = settings.get_setting_color("test_color", "#FFFFFF")
    assert result == "#F00"


def test_get_setting_color_invalid_returns_default(tmp_path: Path):
    """Test get_setting_color returns default for invalid color."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    settings.set_setting("test_color", "not-a-color")
    result = settings.get_setting_color("test_color", "#00FF00")
    assert result == "#00FF00"


def test_get_setting_color_invalid_hex_returns_default(tmp_path: Path):
    """Test get_setting_color returns default for invalid hex chars."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    settings.set_setting("test_color", "#GGGGGG")
    result = settings.get_setting_color("test_color", "#0000FF")
    assert result == "#0000FF"


def test_get_setting_color_missing_returns_default(tmp_path: Path):
    """Test get_setting_color returns default for missing key."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    
    result = settings.get_setting_color("nonexistent_color_xyz", "#AABBCC")
    assert result == "#AABBCC"


def test_init_db_points_to_active_profile(tmp_path):
    """Test that init_db() without path uses the active profile's database."""
    from unittest.mock import patch, MagicMock
    
    data_dir = tmp_path / "Dev_Type_Data"
    data_dir.mkdir()
    (data_dir / "profiles" / "SpecialUser").mkdir(parents=True)
    special_db = data_dir / "profiles" / "SpecialUser" / "typing_stats.db"
    
    with patch('app.portable_data._portable_data_manager') as mock_pdm:
        mock_pdm.get_database_path.return_value = special_db
        
        # Reset current db path in settings to force re-evaluation
        settings._current_db_path = None
        settings._db_initialized = False
        
        settings.init_db()
        
        assert settings.get_current_db_path() == special_db
        assert special_db.exists()
