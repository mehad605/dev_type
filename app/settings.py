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
from typing import Optional, List

# Module-level variable to store the current DB path
_current_db_path: Optional[Path] = None
_db_initialized: bool = False


def get_data_dir() -> Path:
    if os.name == "nt":
        base = os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming"
    else:
        base = Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    d = Path(base) / "dev_typing_app"
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
    return get_data_dir() / "data.db"


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
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("dark_scheme", "nord"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("delete_confirm", "1"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("pause_delay", "7"))
    
    # Color settings
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("color_untyped", "#555555"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("color_correct", "#00ff00"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("color_incorrect", "#ff0000"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("color_paused_highlight", "#ffaa00"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("color_cursor", "#ffffff"))
    
    # Cursor settings
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("cursor_type", "blinking"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("cursor_style", "block"))
    
    # Font settings
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("font_family", "Consolas"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("font_size", "12"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("font_ligatures", "0"))
    
    # Space character setting
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("space_char", "␣"))
    
    # Typing behavior setting
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("allow_continue_mistakes", "0"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("show_typed_characters", "0"))
    cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", ("best_wpm_min_accuracy", "0.9"))
    
    conn.commit()
    conn.close()

    # Also initialize stats tables
    from app import stats_db
    stats_db.init_stats_tables()

    if path is None:
        _db_initialized = True


def _connect(path: Optional[str] = None):
    conn = sqlite3.connect(_db_file(path))
    # Apply pragmatic defaults tuned for interactive desktop apps.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-64000")  # ~64MB cache, negative => KB units in memory
    return conn


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    r = cur.fetchone()
    conn.close()
    if r:
        return r[0]
    return default


def set_setting(key: str, value: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)", (key, value))
    conn.commit()
    conn.close()


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

