"""SQLite-backed settings and folder persistence.

APIs:
 - init_db(path=None)
 - get_setting(key, default=None)
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
    from app.portable_data import get_database_path, is_portable
    _PORTABLE_MODE_AVAILABLE = True
except ImportError:
    _PORTABLE_MODE_AVAILABLE = False
    def get_database_path():
        return None
    def is_portable():
        return False

# Module-level variable to store the current DB path
_current_db_path: Optional[Path] = None
_db_initialized: bool = False
_settings_cache: Dict[str, Optional[str]] = {}
_settings_cache_loaded: bool = False
_db_error_shown: bool = False


def _show_db_error(error: Exception):
    """Show a user-friendly database error dialog (only once per session)."""
    from PySide6.QtWidgets import QMessageBox, QApplication
    
    # Only show if there's an active application
    app = QApplication.instance()
    if app is None:
        return
    
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle("Database Error")
    msg.setText("Dev Type encountered a database error.")
    msg.setInformativeText(
        "Your settings and statistics may not be saved. "
        "The app will continue to work, but changes may be lost.\n\n"
        "Try restarting the application. If the problem persists, "
        "check that you have write permissions to the data folder."
    )
    msg.setDetailedText(str(error))
    msg.exec()


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


def _db_file(path: Optional[str] = None) -> Path:
    global _current_db_path
    if path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        _current_db_path = p
        return p
    if _current_db_path:
        return _current_db_path
    
    # Always use portable database path
    if _PORTABLE_MODE_AVAILABLE:
        portable_db = get_database_path()
        if portable_db:
            return portable_db
    
    # Fallback
    return get_data_dir() / "typing_stats.db"


def init_db(path: Optional[str] = None):
    global _db_initialized
    db_path = _db_file(path)

    # Avoid re-running initialization work repeatedly for the default DB.
    if path is None and _db_initialized:
        return

    conn = sqlite3.connect(db_path)
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
    # defaults
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("theme", "dark"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("dark_scheme", "dracula"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("delete_confirm", "1"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("pause_delay", "4"))
    
    # Color settings - Dracula theme colors
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("color_untyped", "#6272a4"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("color_correct", "#50fa7b"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("color_incorrect", "#ff5555"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("color_paused_highlight", "#f1fa8c"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("color_cursor", "#8be9fd"))
    
    # Cursor settings
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("cursor_type", "static"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("cursor_style", "underscore"))
    
    # Font settings
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("font_family", "JetBrains Mono"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("font_size", "12"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("font_ligatures", "0"))
    
    # Space character setting
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("space_char", "␣"))
    
    # Tab width setting
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("tab_width", "4"))
    
    # Typing behavior setting
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("allow_continue_mistakes", "1"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("show_typed_characters", "1"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("best_wpm_min_accuracy", "0.93"))
    
    # Sound settings
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("sound_enabled", "1"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("sound_profile", "brick"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("sound_volume", "50"))
    
    # Progress bar colors
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("progress_bar_color", "#4CAF50"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("user_progress_bar_color", "#4CAF50"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("ghost_progress_bar_color", "#ff557f"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("ghost_text_color", "#ffaaff"))
    
    conn.commit()
    conn.close()

    # Also initialize stats tables
    from app import stats_db
    stats_db.init_stats_tables()

    if path is None:
        _db_initialized = True

    _reset_settings_cache()


def _connect(path: Optional[str] = None):
    global _db_error_shown
    try:
        conn = sqlite3.connect(_db_file(path), timeout=10.0)
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

