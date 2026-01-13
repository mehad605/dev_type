"""Database module for tracking typing statistics and session progress."""
import sqlite3
from datetime import datetime
from typing import Any, Optional, Dict, List, Iterable
from app.settings import _connect
import app.settings as settings


def _use_demo_mode() -> bool:
    """Check if demo mode is enabled via --demo flag."""
    try:
        from app.demo_data import is_demo_mode
        return is_demo_mode()
    except ImportError:
        return False


def _connect_for_stats() -> sqlite3.Connection:
    """Get database connection - uses demo DB if demo mode enabled, else normal DB."""
    if _use_demo_mode():
        from app.demo_data import connect_demo, ensure_demo_data
        ensure_demo_data()
        return connect_demo()
    return _connect()


def _get_global_ignore_sql() -> str:
    """Return SQL WHERE clause snippet to exclude ignored files, folders and patterns."""
    # 1. Loading patterns from settings
    raw_files = settings.get_setting("ignored_files", settings.get_default("ignored_files"))
    raw_folders = settings.get_setting("ignored_folders", settings.get_default("ignored_folders"))
    
    ignored_files = [p.strip() for p in raw_files.split('\n') if p.strip()]
    ignored_folders = [p.strip() for p in raw_folders.split('\n') if p.strip()]
    
    clauses = []
    
    # File Patterns: use GLOB (supports * and ?)
    for pattern in ignored_files:
        # Remove quotes used for case-insensitivity in the UI
        p = pattern[1:-1] if pattern.startswith('"') and pattern.endswith('"') else pattern
        
        # If it's a simple name, match it anywhere in the path or as a suffix
        if '/' not in p and '\\' not in p:
            clauses.append(f"file_path NOT GLOB '*/{p}'")
            clauses.append(f"file_path NOT GLOB '{p}'")
        else:
            clauses.append(f"file_path NOT GLOB '{p}'")
            
    # Folder Patterns:
    for pattern in ignored_folders:
        p = pattern[1:-1] if pattern.startswith('"') and pattern.endswith('"') else pattern
        if '/' not in p and '\\' not in p:
            clauses.append(f"file_path NOT GLOB '*/{p}/*'")
            clauses.append(f"file_path NOT GLOB '{p}/*'")
        else:
            clauses.append(f"file_path NOT GLOB '{p}/*'")
            
    if not clauses:
        return ""
        
    return " AND (" + " AND ".join(clauses) + ")"


def init_stats_tables():
    """Initialize database tables for typing statistics."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    
    # File statistics table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS file_stats (
            file_path TEXT PRIMARY KEY,
            best_wpm REAL DEFAULT 0,
            last_wpm REAL DEFAULT 0,
            best_accuracy REAL DEFAULT 0,
            last_accuracy REAL DEFAULT 0,
            times_practiced INTEGER DEFAULT 0,
            last_practiced TIMESTAMP,
            completed BOOLEAN DEFAULT 0
        )
    """)
    
    # Session progress table (for resuming incomplete sessions)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS session_progress (
            file_path TEXT PRIMARY KEY,
            cursor_position INTEGER DEFAULT 0,
            total_characters INTEGER DEFAULT 0,
            correct_keystrokes INTEGER DEFAULT 0,
            incorrect_keystrokes INTEGER DEFAULT 0,
            session_time REAL DEFAULT 0,
            is_paused BOOLEAN DEFAULT 1,
            keystrokes_json TEXT,
            wpm_history_json TEXT,
            error_history_json TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Ensure keystrokes_json column exists for older databases
    cur.execute("PRAGMA table_info(session_progress)")
    progress_columns = {row[1] for row in cur.fetchall()}
    if "keystrokes_json" not in progress_columns:
        cur.execute("ALTER TABLE session_progress ADD COLUMN keystrokes_json TEXT")
    if "wpm_history_json" not in progress_columns:
        cur.execute("ALTER TABLE session_progress ADD COLUMN wpm_history_json TEXT")
    if "error_history_json" not in progress_columns:
        cur.execute("ALTER TABLE session_progress ADD COLUMN error_history_json TEXT")

    # Historical session table for aggregations
    cur.execute("""
        CREATE TABLE IF NOT EXISTS session_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            language TEXT DEFAULT '',
            wpm REAL NOT NULL,
            accuracy REAL NOT NULL,
            total_keystrokes INTEGER DEFAULT 0,
            correct_keystrokes INTEGER DEFAULT 0,
            incorrect_keystrokes INTEGER DEFAULT 0,
            duration REAL DEFAULT 0,
            completed BOOLEAN DEFAULT 0,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Ensure newer columns exist for older databases
    cur.execute("PRAGMA table_info(session_history)")
    existing_columns = {row[1] for row in cur.fetchall()}
    if "language" not in existing_columns:
        cur.execute("ALTER TABLE session_history ADD COLUMN language TEXT DEFAULT ''")
    if "total_keystrokes" not in existing_columns:
        cur.execute("ALTER TABLE session_history ADD COLUMN total_keystrokes INTEGER DEFAULT 0")
    if "correct_keystrokes" not in existing_columns:
        cur.execute("ALTER TABLE session_history ADD COLUMN correct_keystrokes INTEGER DEFAULT 0")
    if "incorrect_keystrokes" not in existing_columns:
        cur.execute("ALTER TABLE session_history ADD COLUMN incorrect_keystrokes INTEGER DEFAULT 0")
    if "duration" not in existing_columns:
        cur.execute("ALTER TABLE session_history ADD COLUMN duration REAL DEFAULT 0")

    # Create indexes after ensuring columns exist
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_session_history_file_path
                   ON session_history(file_path, recorded_at DESC)""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_session_history_language
                   ON session_history(language)""")
    
    # Key statistics table for heatmap - updated to include language
    cur.execute("""
        CREATE TABLE IF NOT EXISTS key_stats (
            char TEXT,
            language TEXT,
            correct_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (char, language)
        )
    """)
    # Migration: check if language column exists in older (very recent) version
    cur.execute("PRAGMA table_info(key_stats)")
    columns = [row[1] for row in cur.fetchall()]
    if columns and "language" not in columns:
        # If we have the old version without language, just drop and recreate as it's brand new
        cur.execute("DROP TABLE key_stats")
        cur.execute("""
            CREATE TABLE key_stats (
                char TEXT,
                language TEXT,
                correct_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (char, language)
            )
        """)
    
    # Key confusions table (what was typed instead of what was expected)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS key_confusions (
            expected_char TEXT,
            actual_char TEXT,
            language TEXT,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (expected_char, actual_char, language)
        )
    """)

    # Error type statistics (Missed, Extra, Swapped)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS error_type_stats (
            language TEXT PRIMARY KEY,
            omissions INTEGER DEFAULT 0,
            insertions INTEGER DEFAULT 0,
            transpositions INTEGER DEFAULT 0,
            substitutions INTEGER DEFAULT 0
        )
    """)

    # Bigram performance table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bigram_stats (
            char1 TEXT,
            char2 TEXT,
            language TEXT,
            total_time REAL DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            PRIMARY KEY (char1, char2, language)
        )
    """)
    
    conn.commit()
    conn.close()


def get_file_stats(file_path: str) -> Optional[Dict]:
    """Get statistics for a specific file."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    cur.execute("""
        SELECT best_wpm, last_wpm, best_accuracy, last_accuracy, 
               times_practiced, completed
        FROM file_stats 
        WHERE file_path = ?
    """, (file_path,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "best_wpm": row[0],
            "last_wpm": row[1],
            "best_accuracy": row[2],
            "last_accuracy": row[3],
            "times_practiced": row[4],
            "completed": row[5],
        }
    return None


def get_file_stats_for_files(file_paths: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """Fetch stats for multiple files with a single query, chunked to avoid SQLite limits."""
    paths = list({path for path in file_paths if path})
    if not paths:
        return {}

    conn = _connect_for_stats()
    cur = conn.cursor()
    stats_map: Dict[str, Dict[str, Any]] = {}
    
    # SQLite parameter limit is usually 999. Use 500 for safety.
    CHUNK_SIZE = 500
    for i in range(0, len(paths), CHUNK_SIZE):
        chunk = paths[i:i + CHUNK_SIZE]
        placeholders = ",".join(["?"] * len(chunk))
        cur.execute(
            f"""
            SELECT file_path, best_wpm, last_wpm, best_accuracy, last_accuracy,
                   times_practiced, completed
            FROM file_stats
            WHERE file_path IN ({placeholders})
            """,
            chunk,
        )
        rows = cur.fetchall()
        for row in rows:
            stats_map[row[0]] = {
                "best_wpm": row[1],
                "last_wpm": row[2],
                "best_accuracy": row[3],
                "last_accuracy": row[4],
                "times_practiced": row[5],
                "completed": row[6],
            }
            
    conn.close()
    return stats_map


def update_file_stats(file_path: str, wpm: float, accuracy: float, completed: bool = False):
    """Update statistics for a file after a typing session."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    
    # Minimum accuracy required to update best WPM
    try:
        min_accuracy_raw = settings.get_setting("best_wpm_min_accuracy", settings.get_default("best_wpm_min_accuracy"))
        min_accuracy = float(min_accuracy_raw) if min_accuracy_raw is not None else 0.9
    except (TypeError, ValueError):
        min_accuracy = 0.9
    min_accuracy = max(0.0, min(1.0, min_accuracy))
    meets_threshold = accuracy >= min_accuracy

    # Get current stats
    cur.execute("SELECT best_wpm, times_practiced FROM file_stats WHERE file_path = ?", (file_path,))
    row = cur.fetchone()
    
    if row:
        current_best = row[0] or 0.0
        best_wpm = current_best
        if meets_threshold and wpm > current_best:
            best_wpm = wpm
        times = row[1] + 1
        cur.execute("""
            UPDATE file_stats 
            SET last_wpm = ?, best_wpm = ?, last_accuracy = ?, 
                times_practiced = ?, completed = ?,
                last_practiced = CURRENT_TIMESTAMP
            WHERE file_path = ?
        """, (wpm, best_wpm, accuracy, times, completed, file_path))
    else:
        initial_best = wpm if meets_threshold else 0.0
        cur.execute("""
            INSERT INTO file_stats 
            (file_path, best_wpm, last_wpm, best_accuracy, last_accuracy, 
             times_practiced, completed, last_practiced)
            VALUES (?, ?, ?, ?, ?, 1, ?, CURRENT_TIMESTAMP)
        """, (file_path, initial_best, wpm, accuracy, accuracy, completed))
    
    conn.commit()
    conn.close()


def record_session_history(
    file_path: str,
    language: str,
    wpm: float,
    accuracy: float,
    total_keystrokes: int,
    correct_keystrokes: int,
    incorrect_keystrokes: int,
    duration: float,
    completed: bool = False,
):
    """Append a session result to the historical log."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO session_history (
            file_path,
            language,
            wpm,
            accuracy,
            total_keystrokes,
            correct_keystrokes,
            incorrect_keystrokes,
            duration,
            completed
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            file_path,
            language or "",
            wpm,
            accuracy,
            total_keystrokes,
            correct_keystrokes,
            incorrect_keystrokes,
            duration,
            int(bool(completed)),
        )
    )
    conn.commit()
    conn.close()


def update_key_stats(language: str, key_hits: Dict[str, int], key_misses: Dict[str, int]):
    """Update language-specific key statistics using batch operations."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    lang = language or ""
    
    # Batch hits
    hits_data = [(char, lang, count) for char, count in key_hits.items()]
    if hits_data:
        cur.executemany("""
            INSERT INTO key_stats (char, language, correct_count) 
            VALUES (?, ?, ?)
            ON CONFLICT(char, language) DO UPDATE SET 
                correct_count = correct_count + excluded.correct_count,
                last_updated = CURRENT_TIMESTAMP
        """, hits_data)
        
    # Batch misses
    misses_data = [(char, lang, count) for char, count in key_misses.items()]
    if misses_data:
        cur.executemany("""
            INSERT INTO key_stats (char, language, error_count) 
            VALUES (?, ?, ?)
            ON CONFLICT(char, language) DO UPDATE SET 
                error_count = error_count + excluded.error_count,
                last_updated = CURRENT_TIMESTAMP
        """, misses_data)
        
    conn.commit()
    conn.close()


def update_key_confusions(language: str, key_confusions: Dict[str, Dict[str, int]]):
    """Update language-specific key confusion statistics using batch operations."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    lang = language or ""
    
    conf_data = []
    for expected, actuals in key_confusions.items():
        for actual, count in actuals.items():
            conf_data.append((expected, actual, lang, count))
            
    if conf_data:
        cur.executemany("""
            INSERT INTO key_confusions (expected_char, actual_char, language, count) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(expected_char, actual_char, language) DO UPDATE SET 
                count = count + excluded.count
        """, conf_data)
            
    conn.commit()
    conn.close()


def update_error_type_stats(language: str, errors: Dict[str, int]):
    """Update language-specific error type statistics."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    lang = language or ""
    
    cur.execute("""
        INSERT INTO error_type_stats (language, omissions, insertions, transpositions, substitutions)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(language) DO UPDATE SET
            omissions = omissions + excluded.omissions,
            insertions = insertions + excluded.insertions,
            transpositions = transpositions + excluded.transpositions,
            substitutions = substitutions + excluded.substitutions
    """, (lang, errors.get('omission', 0), errors.get('insertion', 0), 
          errors.get('transposition', 0), errors.get('substitution', 0)))
            
    conn.commit()
    conn.close()


def get_error_type_stats(languages: Optional[List[str]] = None) -> Dict[str, int]:
    """Get aggregated error type statistics."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    
    query = "SELECT SUM(omissions), SUM(insertions), SUM(transpositions), SUM(substitutions) FROM error_type_stats"
    params = []
    if languages:
        placeholders = ",".join(["?"] * len(languages))
        query += f" WHERE language IN ({placeholders})"
        params = languages
        
    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()
    
    if not row or row[0] is None:
        return {'omission': 0, 'insertion': 0, 'transposition': 0, 'substitution': 0}
        
    return {
        'omission': row[0],
        'insertion': row[1],
        'transposition': row[2],
        'substitution': row[3]
    }





def get_key_stats(languages: Optional[List[str]] = None) -> Dict[str, Dict[str, int]]:
    """Get key statistics for the heatmap, optionally filtered by language."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    
    if languages:
        placeholders = ",".join(["?"] * len(languages))
        cur.execute(f"""
            SELECT char, SUM(correct_count), SUM(error_count) 
            FROM key_stats 
            WHERE language IN ({placeholders})
            GROUP BY char
        """, languages)
    else:
        # Sum across all languages
        cur.execute("""
            SELECT char, SUM(correct_count), SUM(error_count) 
            FROM key_stats 
            GROUP BY char
        """)
        
    rows = cur.fetchall()
    conn.close()
    
    return {row[0]: {"correct": row[1], "error": row[2]} for row in rows}


def get_key_confusions(languages: Optional[List[str]] = None) -> Dict[str, Dict[str, int]]:
    """Get key confusion statistics, optionally filtered by language."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    
    if languages:
        placeholders = ",".join(["?"] * len(languages))
        cur.execute(f"""
            SELECT expected_char, actual_char, SUM(count) 
            FROM key_confusions 
            WHERE language IN ({placeholders})
            GROUP BY expected_char, actual_char
        """, languages)
    else:
        cur.execute("""
            SELECT expected_char, actual_char, SUM(count) 
            FROM key_confusions 
            GROUP BY expected_char, actual_char
        """)
        
    rows = cur.fetchall()
    conn.close()
    
    result = {}
    for expected, actual, count in rows:
        if expected not in result:
            result[expected] = {}
        result[expected][actual] = count
        
    return result


def get_recent_wpm_average(file_paths: List[str], limit: int = 10) -> Optional[Dict[str, float]]:
    """Return average WPM and sample size for the most recent sessions across given files."""
    if not file_paths:
        return None

    conn = _connect_for_stats()
    cur = conn.cursor()
    placeholders = ",".join(["?"] * len(file_paths))
    query = f"""
        SELECT wpm FROM session_history
        WHERE completed = 1
          AND file_path IN ({placeholders})
        ORDER BY recorded_at DESC
        LIMIT ?
    """
    cur.execute(query, (*file_paths, limit))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return None

    wpms = [row[0] for row in rows if row[0] is not None]
    if not wpms:
        return None

    avg = sum(wpms) / len(wpms)
    return {"average": avg, "count": len(wpms)}


def get_bulk_recent_wpm_averages(languages: List[str], limit_per_lang: int = 10) -> Dict[str, Dict[str, Any]]:
    """Fetch recent WPM averages for multiple languages in a single efficient query."""
    if not languages:
        return {}

    conn = _connect_for_stats()
    cur = conn.cursor()
    
    # We use a window function to get the top N rows per language in one go
    # This is much faster than running 10-100 separate queries.
    placeholders = ",".join(["?"] * len(languages))
    query = f"""
        SELECT language, wpm
        FROM (
            SELECT language, wpm,
                   ROW_NUMBER() OVER (PARTITION BY language ORDER BY recorded_at DESC) as rank
            FROM session_history
            WHERE completed = 1 AND language IN ({placeholders})
        )
        WHERE rank <= ?
    """
    
    try:
        cur.execute(query, (*languages, limit_per_lang))
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        # Fallback if window functions are not supported by the current SQLite version
        conn.close()
        results = {}
        for lang in languages:
            one = get_recent_wpm_average_by_language(lang, limit_per_lang)
            if one: results[lang] = one
        return results
        
    conn.close()

    # Group results by language
    lang_wpms = {}
    for lang, wpm in rows:
        if lang not in lang_wpms:
            lang_wpms[lang] = []
        lang_wpms[lang].append(wpm)

    results = {}
    for lang, wpms in lang_wpms.items():
        if wpms:
            results[lang] = {
                "average": sum(wpms) / len(wpms),
                "count": len(wpms)
            }
    return results


def get_recent_wpm_average_by_language(language: str, limit: int = 10) -> Optional[Dict[str, float]]:
    """Return average WPM for the most recent sessions for a specific language."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    cur.execute("""
        SELECT wpm FROM session_history
        WHERE completed = 1 AND language = ?
        ORDER BY recorded_at DESC
        LIMIT ?
    """, (language, limit))
    rows = cur.fetchall()
    conn.close()
    
    if not rows: return None
    wpms = [r[0] for r in rows if r[0] is not None]
    if not wpms: return None
    return {"average": sum(wpms)/len(wpms), "count": len(wpms)}


def list_history_languages() -> List[str]:
    """Return distinct languages present in the session history."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    ignore_sql = _get_global_ignore_sql()
    cur.execute(
        f"""
        SELECT DISTINCT language FROM session_history
        WHERE language IS NOT NULL AND language != '' {ignore_sql}
        ORDER BY language COLLATE NOCASE
        """
    )
    languages = [row[0] for row in cur.fetchall()]
    conn.close()
    return languages


def fetch_session_history(
    language: Optional[str] = None,
    file_contains: Optional[str] = None,
    min_wpm: Optional[float] = None,
    max_wpm: Optional[float] = None,
    min_duration: Optional[float] = None,
    max_duration: Optional[float] = None,
) -> List[Dict]:
    """Retrieve session history rows matching the supplied filters."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    ignore_sql = _get_global_ignore_sql()
    query = [
        "SELECT id, file_path, language, wpm, accuracy, total_keystrokes,",
        "       correct_keystrokes, incorrect_keystrokes, duration, recorded_at",
        f"FROM session_history WHERE 1=1 {ignore_sql}",
    ]
    params: List[Any] = []

    if language:
        query.append("AND language = ?")
        params.append(language)
    if file_contains:
        # Create fuzzy pattern such that "pow" will match "power.py" (p%o%w)
        raw = file_contains.lower().strip()
        if raw:
            escaped = raw.replace("%", r"\%").replace("_", r"\_")
            pattern = "%" + "%".join(escaped) + "%"
            query.append("AND LOWER(file_path) LIKE ? ESCAPE '\\'")
            params.append(pattern)
    if min_wpm is not None:
        query.append("AND wpm >= ?")
        params.append(min_wpm)
    if max_wpm is not None:
        query.append("AND wpm <= ?")
        params.append(max_wpm)
    if min_duration is not None:
        query.append("AND duration >= ?")
        params.append(min_duration)
    if max_duration is not None:
        query.append("AND duration <= ?")
        params.append(max_duration)

    query.append("ORDER BY recorded_at DESC")
    cur.execute("\n".join(query), params)
    rows = cur.fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append(
            {
                "id": row[0],
                "file_path": row[1],
                "language": row[2],
                "wpm": row[3],
                "accuracy": row[4],
                "total": row[5],
                "correct": row[6],
                "incorrect": row[7],
                "duration": row[8],
                "recorded_at": row[9],
            }
        )
    return history


def delete_session_history(record_ids: List[int]):
    """Delete session history rows by id."""
    if not record_ids:
        return

    conn = _connect_for_stats()
    cur = conn.cursor()
    placeholders = ",".join(["?"] * len(record_ids))
    cur.execute(f"DELETE FROM session_history WHERE id IN ({placeholders})", record_ids)
    conn.commit()
    conn.close()


def cleanup_old_sessions(retention_days: Optional[int] = None) -> int:
    """Delete session history older than specified days.
    
    Args:
        retention_days: Number of days to retain. None or 0 means keep all.
    
    Returns:
        Number of rows deleted.
    """
    if retention_days is None or retention_days <= 0:
        return 0
    
    conn = _connect_for_stats()
    cur = conn.cursor()
    
    # Delete sessions older than retention_days
    cur.execute("""
        DELETE FROM session_history 
        WHERE recorded_at < datetime('now', '-' || ? || ' days')
    """, (retention_days,))
    
    rows_deleted = cur.rowcount
    conn.commit()
    
    # VACUUM to reclaim space if significant deletions occurred
    if rows_deleted > 100:
        cur.execute("VACUUM")
    
    conn.close()
    return rows_deleted


def get_session_progress(file_path: str) -> Optional[Dict]:
    """Get saved progress for a file session."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    cur.execute("""
        SELECT cursor_position, total_characters, correct_keystrokes,
               incorrect_keystrokes, session_time, is_paused, keystrokes_json,
               wpm_history_json, error_history_json
        FROM session_progress
        WHERE file_path = ?
    """, (file_path,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "cursor_position": row[0],
            "total_characters": row[1],
            "correct": row[2],
            "incorrect": row[3],
            "time": row[4],
            "is_paused": bool(row[5]),
            "keystrokes": row[6],
            "wpm_history": row[7],
            "error_history": row[8]
        }
    return None


def save_session_progress(file_path: str, cursor_pos: int, total_chars: int,
                          correct: int, incorrect: int, time: float, is_paused: bool = True,
                          keystrokes_json: Optional[str] = None,
                          wpm_history_json: Optional[str] = None,
                          error_history_json: Optional[str] = None):
    """Save progress of an incomplete typing session."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO session_progress
        (file_path, cursor_position, total_characters, correct_keystrokes,
         incorrect_keystrokes, session_time, is_paused, keystrokes_json,
         wpm_history_json, error_history_json, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (file_path, cursor_pos, total_chars, correct, incorrect, time, is_paused, 
          keystrokes_json, wpm_history_json, error_history_json))
    conn.commit()
    conn.close()


def clear_session_progress(file_path: str):
    """Clear saved progress for a file (when session is completed or reset)."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM session_progress WHERE file_path = ?", (file_path,))
    conn.commit()
    conn.close()


def get_incomplete_sessions() -> List[str]:
    """Get list of files with incomplete sessions (paused or not finished)."""
    conn = _connect()
    cur = conn.cursor()
    # Get files that are paused OR have not reached the end
    cur.execute("""
        SELECT file_path FROM session_progress 
        WHERE is_paused = 1 OR cursor_position < total_characters
    """)
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows


def is_session_incomplete(file_path: str) -> bool:
    """Check if a file has an incomplete session.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if file has incomplete session, False otherwise
    """
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM session_progress 
        WHERE file_path = ? 
        AND (is_paused = 1 OR cursor_position < total_characters)
    """, (file_path,))
    result = cur.fetchone()
    conn.close()
    return result is not None


def get_aggregated_stats(languages: Optional[List[str]] = None) -> Dict[str, Any]:
    """Get aggregated statistics for the stats tab.
    
    Args:
        languages: Optional list of languages to filter by. If None or empty, all languages.
        
    Returns:
        Dictionary with aggregated stats including:
        - total_completed: Number of completed sessions
        - total_incomplete: Number of incomplete sessions  
        - highest_wpm, lowest_wpm, avg_wpm: WPM statistics
        - highest_acc, lowest_acc, avg_acc: Accuracy statistics (as percentages)
        - most_chars_day: Most characters typed in a single day
        - most_sessions_day: Most sessions completed in a single day
    """
    conn = _connect_for_stats()
    cur = conn.cursor()
    
    # Build WHERE clause for language filter
    where_clause = ""
    params: List[Any] = []
    if languages:
        placeholders = ",".join(["?"] * len(languages))
        where_clause = f"AND language IN ({placeholders})"
        params = list(languages)
    
    ignore_sql = _get_global_ignore_sql()
    
    # Get session counts
    cur.execute(f"""
        SELECT 
            SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN completed = 0 THEN 1 ELSE 0 END) as incomplete
        FROM session_history
        WHERE 1=1 {where_clause} {ignore_sql}
    """, params)
    row = cur.fetchone()
    total_completed = row[0] or 0
    total_incomplete = row[1] or 0
    
    # Get WPM and accuracy stats (only from completed sessions)
    cur.execute(f"""
        SELECT 
            MAX(wpm) as highest_wpm,
            MIN(wpm) as lowest_wpm,
            AVG(wpm) as avg_wpm,
            MAX(accuracy * 100) as highest_acc,
            MIN(accuracy * 100) as lowest_acc,
            AVG(accuracy * 100) as avg_acc
        FROM session_history
        WHERE completed = 1 {where_clause} {ignore_sql}
    """, params)
    row = cur.fetchone()
    highest_wpm = row[0]
    lowest_wpm = row[1]
    avg_wpm = row[2]
    highest_acc = row[3]
    lowest_acc = row[4]
    avg_acc = row[5]
    
    # Get most characters typed in a single day
    cur.execute(f"""
        SELECT DATE(recorded_at) as day, SUM(correct_keystrokes + incorrect_keystrokes) as total_chars
        FROM session_history
        WHERE completed = 1 {where_clause} {ignore_sql}
        GROUP BY DATE(recorded_at)
        ORDER BY total_chars DESC
        LIMIT 1
    """, params)
    row = cur.fetchone()
    most_chars_day = row[1] if row else 0
    
    # Get most sessions completed in a single day
    cur.execute(f"""
        SELECT DATE(recorded_at) as day, COUNT(*) as session_count
        FROM session_history
        WHERE completed = 1 {where_clause} {ignore_sql}
        GROUP BY DATE(recorded_at)
        ORDER BY session_count DESC
        LIMIT 1
    """, params)
    row = cur.fetchone()
    most_sessions_day = row[1] if row else 0
    
    conn.close()
    
    return {
        "total_completed": total_completed,
        "total_incomplete": total_incomplete,
        "highest_wpm": highest_wpm,
        "lowest_wpm": lowest_wpm,
        "avg_wpm": avg_wpm,
        "highest_acc": highest_acc,
        "lowest_acc": lowest_acc,
        "avg_acc": avg_acc,
        "most_chars_day": most_chars_day,
        "most_sessions_day": most_sessions_day,
    }


def get_wpm_distribution(languages: Optional[List[str]] = None, bucket_size: int = 10) -> List[Dict[str, Any]]:
    """Get WPM distribution for bar chart.
    
    Args:
        languages: Optional list of languages to filter by.
        bucket_size: Size of each WPM bucket (default 10).
        
    Returns:
        List of dicts with 'range_label', 'min_wpm', 'max_wpm', 'count'
    """
    conn = _connect_for_stats()
    cur = conn.cursor()
    
    # Build WHERE clause for language filter
    where_clause = ""
    params: List[Any] = []
    if languages:
        placeholders = ",".join(["?"] * len(languages))
        where_clause = f"AND language IN ({placeholders})"
        params = list(languages)
    
    ignore_sql = _get_global_ignore_sql()
    # Get all WPM values from completed sessions
    cur.execute(f"""
        SELECT wpm FROM session_history
        WHERE completed = 1 {where_clause} {ignore_sql}
    """, params)
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        return []
    
    wpms = [row[0] for row in rows if row[0] is not None]
    if not wpms:
        return []
    
    # Calculate bucket distribution
    max_wpm = max(wpms)
    num_buckets = int(max_wpm // bucket_size) + 1
    
    # Create buckets
    buckets = []
    for i in range(num_buckets):
        min_wpm = i * bucket_size
        max_wpm_bucket = (i + 1) * bucket_size - 1
        count = sum(1 for w in wpms if min_wpm <= w < (i + 1) * bucket_size)
        
        if count > 0 or i < 10:  # Always show first 10 buckets even if empty
            buckets.append({
                "range_label": f"{min_wpm}-{max_wpm_bucket}",
                "min_wpm": min_wpm,
                "max_wpm": max_wpm_bucket,
                "count": count
            })
    
    # Trim trailing empty buckets
    while buckets and buckets[-1]["count"] == 0:
        buckets.pop()
    
    return buckets


def get_sessions_over_time(languages: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Get session data over time for scatter plot.
    
    Args:
        languages: Optional list of languages to filter by.
        
    Returns:
        List of dicts with 'date', 'wpm', 'accuracy', 'file_path', 'correct', 'incorrect', 'total'
    """
    conn = _connect_for_stats()
    cur = conn.cursor()
    
    # Build WHERE clause for language filter
    where_clause = ""
    params: List[Any] = []
    if languages:
        placeholders = ",".join(["?"] * len(languages))
        where_clause = f"AND language IN ({placeholders})"
        params = list(languages)
    
    ignore_sql = _get_global_ignore_sql()
    cur.execute(f"""
        SELECT DATE(recorded_at) as date, wpm, accuracy, file_path,
               correct_keystrokes, incorrect_keystrokes, total_keystrokes
        FROM session_history
        WHERE completed = 1 {where_clause} {ignore_sql}
        ORDER BY recorded_at ASC
    """, params)
    rows = cur.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            "date": row[0],
            "wpm": row[1],
            "accuracy": row[2] * 100 if row[2] is not None else 0,  # Convert to percentage
            "file_path": row[3],
            "correct": row[4] or 0,
            "incorrect": row[5] or 0,
            "total": row[6] or 0
        })
    
    return result


def get_trend_data(
    languages: Optional[List[str]] = None,
    days: Optional[int] = None,
    aggregation: str = "day"
) -> List[Dict[str, Any]]:
    """Get aggregated trend data over time.
    
    Args:
        languages: Optional list of languages to filter by.
        days: Number of days to look back (None for all time).
        aggregation: How to group data - 'day', 'week', or 'month'.
        
    Returns:
        List of dicts with 'period', 'avg_wpm', 'avg_accuracy', 'session_count'
    """
    conn = _connect()
    cur = conn.cursor()
    
    # Build WHERE clauses
    where_parts = ["completed = 1"]
    params: List[Any] = []
    
    if languages:
        placeholders = ",".join(["?"] * len(languages))
        where_parts.append(f"language IN ({placeholders})")
        params.extend(languages)
    
    if days is not None:
        where_parts.append("recorded_at >= datetime('now', ?)")
        params.append(f"-{days} days")
    
    where_clause = " AND ".join(where_parts)
    
    # Build GROUP BY based on aggregation
    if aggregation == "week":
        # Group by year and week number
        date_expr = "strftime('%Y-W%W', recorded_at)"
    elif aggregation == "month":
        # Group by year and month
        date_expr = "strftime('%Y-%m', recorded_at)"
    else:
        # Default to day
        date_expr = "DATE(recorded_at)"
    
    ignore_sql = _get_global_ignore_sql()
    cur.execute(f"""
        SELECT {date_expr} as period,
               AVG(wpm) as avg_wpm,
               AVG(accuracy) * 100 as avg_accuracy,
               COUNT(*) as session_count
        FROM session_history
        WHERE {where_clause} {ignore_sql}
        GROUP BY period
        ORDER BY period ASC
    """, params)
    rows = cur.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            "period": row[0],
            "avg_wpm": row[1] if row[1] is not None else 0,
            "avg_accuracy": row[2] if row[2] is not None else 0,
            "session_count": row[3]
        })
    
    return result


def get_daily_metrics(
    languages: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get comprehensive daily metrics for the date range chart.
    
    Args:
        languages: Optional list of languages to filter by.
        start_date: Start date in YYYY-MM-DD format (None for earliest).
        end_date: End date in YYYY-MM-DD format (None for today).
        
    Returns:
        List of dicts with daily metrics including:
        - date, total_chars, completed_sessions,
        - avg_wpm, highest_wpm, lowest_wpm,
        - avg_accuracy, highest_accuracy, lowest_accuracy
    """
    conn = _connect_for_stats()
    cur = conn.cursor()
    
    # Build WHERE clauses
    where_parts = ["completed = 1"]
    params: List[Any] = []
    
    if languages:
        placeholders = ",".join(["?"] * len(languages))
        where_parts.append(f"language IN ({placeholders})")
        params.extend(languages)
    
    if start_date:
        where_parts.append("DATE(recorded_at) >= ?")
        params.append(start_date)
    
    if end_date:
        where_parts.append("DATE(recorded_at) <= ?")
        params.append(end_date)
    
    ignore_sql = _get_global_ignore_sql()
    where_clause = " AND ".join(where_parts) + ignore_sql
    
    cur.execute(f"""
        SELECT DATE(recorded_at) as date,
               SUM(total_keystrokes) as total_chars,
               COUNT(*) as completed_sessions,
               AVG(wpm) as avg_wpm,
               MAX(wpm) as highest_wpm,
               MIN(wpm) as lowest_wpm,
               AVG(accuracy) * 100 as avg_accuracy,
               MAX(accuracy) * 100 as highest_accuracy,
               MIN(accuracy) * 100 as lowest_accuracy
        FROM session_history
        WHERE {where_clause}
        GROUP BY DATE(recorded_at)
        ORDER BY date ASC
    """, params)
    rows = cur.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            "date": row[0],
            "total_chars": row[1] or 0,
            "completed_sessions": row[2] or 0,
            "avg_wpm": row[3] if row[3] is not None else 0,
            "highest_wpm": row[4] if row[4] is not None else 0,
            "lowest_wpm": row[5] if row[5] is not None else 0,
            "avg_accuracy": row[6] if row[6] is not None else 0,
            "highest_accuracy": row[7] if row[7] is not None else 0,
            "lowest_accuracy": row[8] if row[8] is not None else 0,
        })
    
    return result


def get_first_session_date() -> Optional[str]:
    """Get the date of the first recorded session.
    
    Returns:
        Date string in YYYY-MM-DD format, or None if no sessions.
    """
    conn = _connect_for_stats()
    cur = conn.cursor()
    ignore_sql = _get_global_ignore_sql()
    cur.execute(f"SELECT MIN(DATE(recorded_at)) FROM session_history WHERE completed = 1 {ignore_sql}")
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else None


def get_per_language_stats() -> List[Dict[str, Any]]:
    """Get aggregated stats per programming language.
    
    Returns:
        List of dicts with language, session_count, avg_wpm, avg_accuracy, total_chars
    """
    conn = _connect_for_stats()
    cur = conn.cursor()
    
    ignore_sql = _get_global_ignore_sql()
    cur.execute(f"""
        SELECT 
            language,
            COUNT(*) as session_count,
            AVG(wpm) as avg_wpm,
            AVG(accuracy) * 100 as avg_accuracy,
            SUM(total_keystrokes) as total_chars,
            MAX(wpm) as best_wpm
        FROM session_history
        WHERE completed = 1 AND language IS NOT NULL AND language != '' {ignore_sql}
        GROUP BY language
        ORDER BY session_count DESC
    """)
    
    rows = cur.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            "language": row[0],
            "session_count": row[1],
            "avg_wpm": row[2] if row[2] else 0,
            "avg_accuracy": row[3] if row[3] else 0,
            "total_chars": row[4] if row[4] else 0,
            "best_wpm": row[5] if row[5] else 0,
        })
    
    return result


def get_available_years() -> List[int]:
    """Get list of years that have recorded sessions."""
    conn = _connect_for_stats()
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT STRFTIME('%Y', recorded_at) as year FROM session_history WHERE year IS NOT NULL ORDER BY year DESC")
        rows = cur.fetchall()
        years = [int(row[0]) for row in rows if row[0]]
    except Exception:
        years = []
    conn.close()
    
    current_year = datetime.now().year
    if current_year not in years:
        years.append(current_year)
    return sorted(list(set(years)), reverse=True)


def get_current_streak() -> int:
    """Calculate current practice streak (consecutive days with completed sessions).
    
    Returns:
        Number of consecutive days with at least one completed session, ending today or yesterday.
    """
    conn = _connect_for_stats()
    cur = conn.cursor()
    
    ignore_sql = _get_global_ignore_sql()
    # Get all unique dates with completed sessions, ordered descending
    cur.execute(f"""
        SELECT DISTINCT DATE(recorded_at) as date
        FROM session_history
        WHERE completed = 1 {ignore_sql}
        ORDER BY date DESC
    """)
    
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        return 0
    
    from datetime import datetime, timedelta
    
    dates = [datetime.strptime(row[0], "%Y-%m-%d").date() for row in rows]
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # Streak must start from today or yesterday
    if dates[0] != today and dates[0] != yesterday:
        return 0
    
    streak = 1
    for i in range(1, len(dates)):
        expected_date = dates[i-1] - timedelta(days=1)
        if dates[i] == expected_date:
            streak += 1
        else:
            break
    
    return streak


def get_trend_comparison(days: int = 30, languages: Optional[List[str]] = None) -> Dict[str, Any]:
    """Compare recent performance vs previous period.
    
    Args:
        days: Number of days for each period (default 30).
        languages: Optional list of languages to filter by.
        
    Returns:
        Dict with current period stats, previous period stats, and deltas.
    """
    conn = _connect_for_stats()
    cur = conn.cursor()
    
    from datetime import datetime, timedelta
    
    today = datetime.now().date()
    period1_end = today
    period1_start = today - timedelta(days=days)
    period2_end = period1_start - timedelta(days=1)
    period2_start = period2_end - timedelta(days=days)
    
    # Build language filter clause
    lang_clause = ""
    lang_params: List[Any] = []
    if languages:
        placeholders = ",".join(["?"] * len(languages))
        lang_clause = f"AND language IN ({placeholders})"
        lang_params = list(languages)
    
    def get_period_stats(start_date, end_date):
        params = [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")] + lang_params
        ignore_sql = _get_global_ignore_sql()
        cur.execute(f"""
            SELECT 
                COUNT(*) as sessions,
                AVG(wpm) as avg_wpm,
                AVG(accuracy) * 100 as avg_accuracy,
                SUM(total_keystrokes) as total_chars
            FROM session_history
            WHERE completed = 1 
              AND DATE(recorded_at) >= ? 
              AND DATE(recorded_at) <= ?
              {lang_clause} {ignore_sql}
        """, params)
        row = cur.fetchone()
        return {
            "sessions": row[0] or 0,
            "avg_wpm": row[1] if row[1] else 0,
            "avg_accuracy": row[2] if row[2] else 0,
            "total_chars": row[3] or 0,
        }
    
    current = get_period_stats(period1_start, period1_end)
    previous = get_period_stats(period2_start, period2_end)
    
    conn.close()
    
    # Calculate deltas
    wpm_delta = current["avg_wpm"] - previous["avg_wpm"] if previous["avg_wpm"] else 0
    acc_delta = current["avg_accuracy"] - previous["avg_accuracy"] if previous["avg_accuracy"] else 0
    
    return {
        "current": current,
        "previous": previous,
        "wpm_delta": wpm_delta,
        "acc_delta": acc_delta,
        "period_days": days,
    }
