"""SQLite-backed settings and folder persistence.

APIs:
 - init_db(path=None)
 - get_setting(key, default=None)
 - get_default(key) - Get the canonical default for a setting
 - set_setting(key, value)
 - get_folders()
 - add_folder(path)
 - remove_folder(path)
"""
import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict

# Import portable data manager for exe/AppImage builds
try:
    from app.portable_data import get_data_dir as get_portable_data_dir, get_database_path, is_portable, get_icons_dir as get_portable_icons_dir
    _PORTABLE_MODE_AVAILABLE = True
except ImportError:
    _PORTABLE_MODE_AVAILABLE = False
    def get_database_path():
        return None
    def is_portable():
        return False

# =============================================================================
# SINGLE SOURCE OF TRUTH FOR ALL SETTING DEFAULTS
# =============================================================================
# When adding a new setting, add it here first. All get_setting() calls should
# use get_default() to retrieve the canonical default value.
# =============================================================================
SETTING_DEFAULTS: Dict[str, str] = {
    # Theme settings
    "dark_scheme": "dracula",
    "custom_themes": "{}",
    
    # Confirmation dialogs
    "delete_confirm": "1",
    
    # Typing behavior
    "pause_delay": "7",
    "allow_continue_mistakes": "0",
    "show_typed_characters": "0",
    "show_ghost_text": "1",
    "instant_death_mode": "0",
    
    # Color settings (Dracula theme colors)
    "color_untyped": "#6272a4",
    "color_correct": "#50fa7b",
    "color_incorrect": "#ff5555",
    "color_paused_highlight": "#f1fa8c",
    "color_cursor": "#8be9fd",
    
    # Cursor settings
    "cursor_type": "static",
    "cursor_style": "underscore",
    
    # Font settings
    "font_family": "JetBrains Mono",
    "font_size": "12",
    "ui_font_family": "Segoe UI",
    "ui_font_size": "10",
    "custom_fonts": "[]",
    
    # Display characters
    "space_char": "␣",
    "tab_width": "4",
    
    # Sound settings
    "sound_enabled": "1",
    "sound_profile": "default_1",
    "sound_volume": "50",
    "custom_sound_profiles": "{}",
    
    # Progress bar colors
    "progress_bar_color": "#4CAF50",
    "user_progress_bar_color": "#4CAF50",
    "ghost_progress_bar_color": "#ff557f",
    "ghost_text_color": "#ffaaff",
    
    # Stats settings
    "best_wpm_min_accuracy": "0.9",
    "stats_heatmap_metric": "total_chars",
    
    # History settings
    "history_retention_days": "90",
    
    # State persistence (not user-configurable)
    "expanded_folders": "[]",
    
    # Global Exclusions (user-configurable)
    "ignored_files": (
        # Binaries & Executables
        "*.exe\n*.dll\n*.so\n*.dylib\n*.bin\n*.obj\n*.o\n*.a\n*.lib\n"
        # Caches & Temp files
        "*.pyc\n*.pyo\n*.pyd\n*.class\n*.log\n*.tmp\n"
        # Archives
        "*.zip\n*.tar\n*.gz\n*.7z\n*.rar\n*.iso\n"
        # Media & Documents
        "*.pdf\n*.png\n*.jpg\n*.jpeg\n*.gif\n*.svg\n*.ico\n*.mp3\n*.mp4\n"
        "*.doc\n*.docx\n*.xls\n*.xlsx\n*.ppt\n*.pptx"
    ),
    "ignored_folders": (
        ".git\n.github\n.vscode\n.idea\n"
        "node_modules\n__pycache__\n"
        ".venv\nvenv\nenv\n"
        "build\ndist\ntarget\nout\n"
        "bin\nobj\n.pytest_cache\n.mypy_cache"
    ),
}


def get_default(key: str) -> str:
    """Get the canonical default value for a setting.
    
    This is the single source of truth for all setting defaults.
    Use this instead of hardcoding defaults at call sites.
    """
    return SETTING_DEFAULTS.get(key, "")


# Module-level variable to store the current DB path
_current_db_path: Optional[Path] = None
_db_initialized: bool = False
_settings_cache: Dict[str, Optional[str]] = {}
_settings_cache_loaded: bool = False
_db_error_shown: bool = False


def _reset_settings_cache():
    """Clear the in-memory settings cache."""
    global _settings_cache_loaded
    _settings_cache.clear()
    _settings_cache_loaded = False


def _ensure_settings_cache_loaded():
    """Populate the settings cache on first access."""
    global _settings_cache_loaded
    if _settings_cache_loaded:
        return

    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM settings")
    rows = cur.fetchall()
    conn.close()

    for key, value in rows:
        _settings_cache[key] = value

    _settings_cache_loaded = True


def get_data_dir() -> Path:
    """Get the data directory for the application.
    
    Always uses portable data directory for consistency:
    - In portable mode (exe/AppImage): Dev_Type_Data/ folder next to executable
    - In development mode: Dev_Type_Data/ folder in project root
    """
    # Always use portable data directory for consistency
    if _PORTABLE_MODE_AVAILABLE:
        from app.portable_data import get_data_dir as get_portable_data_dir
        return get_portable_data_dir()
    
    # Fallback if portable_data module not available (should never happen)
    d = Path(__file__).parent.parent / "Dev_Type_Data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_icons_dir() -> Path:
    """Get the directory where shared language icons are stored."""
    if _PORTABLE_MODE_AVAILABLE:
        return get_portable_icons_dir()
    
    # Fallback
    d = get_data_dir() / "shared" / "icons"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_current_db_path() -> Optional[Path]:
    return _current_db_path


def init_db(path: Optional[str] = None):
    """
    Initialize the database at the given path.
    If path is None, it tries to use the existing _current_db_path.
    If that is also None, it falls back to the default location.
    """
    global _db_initialized, _current_db_path
    
    if path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        _current_db_path = p
    elif _current_db_path is None:
        # Resolve path from portable data manager (Profile aware)
        _current_db_path = get_database_path()

    conn = sqlite3.connect(_current_db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS folders (
            path TEXT PRIMARY KEY,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    # Insert all defaults from SETTING_DEFAULTS (single source of truth)
    for key, value in SETTING_DEFAULTS.items():
        cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", (key, value))
    
    conn.commit()
    conn.close()

    # Also initialize stats tables
    from app import stats_db
    stats_db.init_stats_tables()

    _db_initialized = True
    _reset_settings_cache()


def _connect():
    global _db_error_shown, _current_db_path
    
    if _current_db_path is None:
        # Determine path if not set (first run implicit init)
        init_db()
        
    try:
        conn = sqlite3.connect(_current_db_path, timeout=10.0)
        # Apply pragmatic defaults tuned for interactive desktop apps.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA cache_size=-64000")  # ~64MB cache, negative => KB units in memory
        return conn
    except sqlite3.Error as e:
        if not _db_error_shown:
            _db_error_shown = True
            _show_db_error(e)
        raise


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    if key in _settings_cache:
        cached = _settings_cache[key]
        return cached if cached is not None else default

    _ensure_settings_cache_loaded()

    if key in _settings_cache:
        cached = _settings_cache[key]
        return cached if cached is not None else default

    return default


def get_setting_int(key: str, default: int, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    """Get a setting as an integer with validation and clamping.
    
    Args:
        key: The setting key
        default: Default value if setting doesn't exist or is invalid
        min_val: Optional minimum value (clamps if below)
        max_val: Optional maximum value (clamps if above)
    
    Returns:
        The setting value as an integer, or default if invalid
    """
    value = get_setting(key)
    if value is None:
        return default
    
    try:
        result = int(value)
        if min_val is not None:
            result = max(min_val, result)
        if max_val is not None:
            result = min(max_val, result)
        return result
    except (ValueError, TypeError):
        return default


def get_setting_float(key: str, default: float, min_val: Optional[float] = None, max_val: Optional[float] = None) -> float:
    """Get a setting as a float with validation and clamping.
    
    Args:
        key: The setting key
        default: Default value if setting doesn't exist or is invalid
        min_val: Optional minimum value (clamps if below)
        max_val: Optional maximum value (clamps if above)
    
    Returns:
        The setting value as a float, or default if invalid
    """
    value = get_setting(key)
    if value is None:
        return default
    
    try:
        result = float(value)
        if min_val is not None:
            result = max(min_val, result)
        if max_val is not None:
            result = min(max_val, result)
        return result
    except (ValueError, TypeError):
        return default


def get_setting_bool(key: str, default: bool) -> bool:
    """Get a setting as a boolean.
    
    Interprets "true", "1", "yes", "on" as True (case-insensitive).
    All other values return False, except None which returns default.
    
    Args:
        key: The setting key
        default: Default value if setting doesn't exist
    
    Returns:
        The setting value as a boolean
    """
    value = get_setting(key)
    if value is None:
        return default
    
    return value.lower() in ("true", "1", "yes", "on")


def get_setting_color(key: str, default: str = "#FFFFFF") -> str:
    """Get a setting as a validated hex color.
    
    Args:
        key: The setting key
        default: Default color if setting doesn't exist or is invalid
    
    Returns:
        A valid hex color string
    """
    import re
    
    value = get_setting(key)
    if value is None:
        return default
    
    # Validate hex color format (#RGB or #RRGGBB)
    hex_pattern = re.compile(r'^#(?:[0-9a-fA-F]{3}){1,2}$')
    if hex_pattern.match(value):
        return value
    
    return default


def set_setting(key: str, value: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)", (key, value))
    conn.commit()
    conn.close()

    _settings_cache[key] = value


def remove_setting(key: str):
    """Remove a setting from the database and cache."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM settings WHERE key=?", (key,))
    conn.commit()
    conn.close()

    if key in _settings_cache:
        del _settings_cache[key]


def get_folders() -> List[str]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT path FROM folders ORDER BY added_at")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows


def add_folder(path: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO folders(path) VALUES(?)", (path,))
    conn.commit()
    conn.close()


def remove_folder(path: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM folders WHERE path=?", (path,))
    conn.commit()
    conn.close()

