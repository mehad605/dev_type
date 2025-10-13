"""Database module for tracking typing statistics and session progress."""
import sqlite3
from typing import Any, Optional, Dict, List
from app.settings import _db_file, _connect


def init_stats_tables():
    """Initialize database tables for typing statistics."""
    conn = _connect()
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
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

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
    
    conn.commit()
    conn.close()


def get_file_stats(file_path: str) -> Optional[Dict]:
    """Get statistics for a specific file."""
    conn = _connect()
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


def update_file_stats(file_path: str, wpm: float, accuracy: float, completed: bool = False):
    """Update statistics for a file after a typing session."""
    conn = _connect()
    cur = conn.cursor()
    
    # Get current stats
    cur.execute("SELECT best_wpm, times_practiced FROM file_stats WHERE file_path = ?", (file_path,))
    row = cur.fetchone()
    
    if row:
        best_wpm = max(row[0], wpm)
        times = row[1] + 1
        cur.execute("""
            UPDATE file_stats 
            SET last_wpm = ?, best_wpm = ?, last_accuracy = ?, 
                times_practiced = ?, completed = ?,
                last_practiced = CURRENT_TIMESTAMP
            WHERE file_path = ?
        """, (wpm, best_wpm, accuracy, times, completed, file_path))
    else:
        cur.execute("""
            INSERT INTO file_stats 
            (file_path, best_wpm, last_wpm, best_accuracy, last_accuracy, 
             times_practiced, completed, last_practiced)
            VALUES (?, ?, ?, ?, ?, 1, ?, CURRENT_TIMESTAMP)
        """, (file_path, wpm, wpm, accuracy, accuracy, completed))
    
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
    conn = _connect()
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


def get_recent_wpm_average(file_paths: List[str], limit: int = 10) -> Optional[Dict[str, float]]:
    """Return average WPM and sample size for the most recent sessions across given files."""
    if not file_paths:
        return None

    conn = _connect()
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


def list_history_languages() -> List[str]:
    """Return distinct languages present in the session history."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT language FROM session_history
        WHERE language IS NOT NULL AND language != ''
        ORDER BY language COLLATE NOCASE
        """
    )
    languages = [row[0] for row in cur.fetchall()]
    conn.close()
    return languages


def fetch_session_history(
    language: Optional[str] = None,
    min_wpm: Optional[float] = None,
    max_wpm: Optional[float] = None,
    min_duration: Optional[float] = None,
    max_duration: Optional[float] = None,
) -> List[Dict]:
    """Retrieve session history rows matching the supplied filters."""
    conn = _connect()
    cur = conn.cursor()
    query = [
        "SELECT id, file_path, language, wpm, accuracy, total_keystrokes,",
        "       correct_keystrokes, incorrect_keystrokes, duration, recorded_at",
        "FROM session_history WHERE 1=1",
    ]
    params: List[Any] = []

    if language:
        query.append("AND language = ?")
        params.append(language)
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

    conn = _connect()
    cur = conn.cursor()
    placeholders = ",".join(["?"] * len(record_ids))
    cur.execute(f"DELETE FROM session_history WHERE id IN ({placeholders})", record_ids)
    conn.commit()
    conn.close()


def get_session_progress(file_path: str) -> Optional[Dict]:
    """Get saved progress for a file session."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT cursor_position, total_characters, correct_keystrokes,
               incorrect_keystrokes, session_time, is_paused
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
        }
    return None


def save_session_progress(file_path: str, cursor_pos: int, total_chars: int,
                          correct: int, incorrect: int, time: float, is_paused: bool = True):
    """Save progress of an incomplete typing session."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO session_progress
        (file_path, cursor_position, total_characters, correct_keystrokes,
         incorrect_keystrokes, session_time, is_paused, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (file_path, cursor_pos, total_chars, correct, incorrect, time, is_paused))
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
