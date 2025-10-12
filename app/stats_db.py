"""Database module for tracking typing statistics and session progress."""
import sqlite3
from typing import Optional, Dict, List
from pathlib import Path
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
