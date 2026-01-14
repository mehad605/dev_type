"""Generate demo data for testing the Stats page.

This module creates realistic fake typing session data spanning one year.
"""
import sqlite3
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
import calendar

# Runtime flag for demo mode (set via command line --demo)
_demo_mode_enabled: bool = False


def set_demo_mode(enabled: bool):
    """Enable or disable demo mode at runtime."""
    global _demo_mode_enabled
    _demo_mode_enabled = enabled


def is_demo_mode() -> bool:
    """Check if demo mode is enabled."""
    return _demo_mode_enabled


# Demo database path
_demo_db_path: Optional[Path] = None


def get_demo_db_path() -> Path:
    """Get the path to the demo database."""
    global _demo_db_path
    if _demo_db_path is None:
        # Store in the Dev_Type_Data folder
        from app.portable_data import get_data_dir
        data_dir = get_data_dir()
        if data_dir is None:
            # Fallback to user home if portable data dir is not available
            import os
            data_dir = Path.home() / "Dev_Type_Data"
        _demo_db_path = data_dir / "demo_stats.db"
    return _demo_db_path


def demo_db_exists() -> bool:
    """Check if the demo database exists."""
    return get_demo_db_path().exists()


def connect_demo() -> sqlite3.Connection:
    """Connect to the demo database."""
    db_path = get_demo_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(db_path))


def init_demo_tables(conn: sqlite3.Connection):
    """Initialize the demo database tables."""
    cur = conn.cursor()
    
    # Session history table (main table for stats)
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
    
    # File statistics
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
    
    # Key statistics for heatmaps
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
    
    # Error type statistics
    cur.execute("""
        CREATE TABLE IF NOT EXISTS error_type_stats (
            language TEXT PRIMARY KEY,
            omissions INTEGER DEFAULT 0,
            insertions INTEGER DEFAULT 0,
            transpositions INTEGER DEFAULT 0,
            substitutions INTEGER DEFAULT 0
        )
    """)
    
    # Key confusions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS key_confusions (
            expected_char TEXT,
            actual_char TEXT,
            language TEXT,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (expected_char, actual_char, language)
        )
    """)

    cur.execute("""CREATE INDEX IF NOT EXISTS idx_demo_session_history_language
                   ON session_history(language)""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_demo_session_history_date
                   ON session_history(recorded_at)""")
    
    conn.commit()


def generate_demo_data(year: Optional[int] = None, days: int = 365, sessions_per_day_range: tuple = (3, 10)):
    """Generate realistic demo data for the stats page.
    
    Args:
        year: Optional specific year to generate data for (e.g. 2025). If set, 'days' is ignored.
        days: Number of days of history to generate (default 365 = 1 year). Ignored if year is set.
        sessions_per_day_range: Tuple of (min, max) sessions per day
    """
    conn = connect_demo()
    cur = conn.cursor()
    
    # Clear existing demo data
    cur.execute("DELETE FROM session_history")
    cur.execute("DELETE FROM key_stats")
    cur.execute("DELETE FROM file_stats")
    cur.execute("DELETE FROM error_type_stats")
    cur.execute("DELETE FROM key_confusions")
    
    # Languages to simulate
    languages = ["Python", "JavaScript", "TypeScript", "Rust", "Go", "C++", "Java", "C#"]
    language_weights = [30, 25, 15, 10, 8, 5, 4, 3]  # Python most common
    
    # File path templates per language
    file_templates = {
        "Python": ["main.py", "app.py", "utils.py", "models.py", "views.py", "api.py"],
        "JavaScript": ["index.js", "app.js", "utils.js", "components.js", "api.js"],
        "TypeScript": ["index.ts", "app.ts", "types.ts", "utils.ts", "api.ts"],
        "Rust": ["main.rs", "lib.rs", "utils.rs", "mod.rs"],
        "Go": ["main.go", "handler.go", "utils.go", "server.go"],
        "C++": ["main.cpp", "utils.cpp", "app.cpp", "handler.cpp"],
        "Java": ["Main.java", "App.java", "Utils.java", "Service.java"],
        "C#": ["Program.cs", "App.cs", "Utils.cs", "Service.cs"],
    }
    
    # Simulate skill progression over time
    # Start with lower WPM/accuracy, improve over time with some variance
    base_wpm = 35  # Starting WPM
    max_wpm_gain = 45  # Max WPM improvement over the year
    base_accuracy = 0.85  # Starting accuracy (85%)
    max_accuracy_gain = 0.12  # Max accuracy improvement
    
    if year:
        start_date = datetime(year, 1, 1)
        if calendar.isleap(year):
            days = 366
        else:
            days = 365
    else:
        today = datetime.now()
        start_date = today - timedelta(days=days)
    
    print(f"Generating data from {start_date.date()} to {start_date.date() + timedelta(days=days-1)}")
    
    records = []
    
    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)
        
        # Progress factor (0 to 1 over the year)
        progress = day_offset / days
        
        # Simulate varying activity levels
        # More sessions on weekdays, fewer on weekends
        is_weekend = current_date.weekday() >= 5
        
        # Random "break" days (vacation, busy, etc.) - but not in the last 10 days
        # to ensure a streak for demo purposes
        days_from_end = days - day_offset
        is_break_day = random.random() < 0.15 if days_from_end > 10 else False
        
        if is_break_day:
            num_sessions = 0
        elif is_weekend:
            num_sessions = random.randint(1 if days_from_end <= 10 else 0, max(1, sessions_per_day_range[1] // 2))
        else:
            num_sessions = random.randint(sessions_per_day_range[0], sessions_per_day_range[1])
        
        # Generate sessions for this day
        for session_idx in range(num_sessions):
            # Pick a language (weighted random)
            language = random.choices(languages, weights=language_weights, k=1)[0]
            
            # Pick a file
            file_name = random.choice(file_templates[language])
            file_path = f"/demo/projects/{language.lower()}/{file_name}"
            
            # Calculate WPM with progression and daily variance
            skill_wpm = base_wpm + (max_wpm_gain * progress)
            # Add daily variance (good days, bad days)
            daily_variance = random.gauss(0, 8)
            # Add per-session variance
            session_variance = random.gauss(0, 5)
            wpm = max(20, skill_wpm + daily_variance + session_variance)
            
            # Sometimes have exceptional sessions
            if random.random() < 0.05:  # 5% chance of "in the zone" session
                wpm += random.uniform(10, 25)
            
            # Calculate accuracy with progression
            skill_accuracy = base_accuracy + (max_accuracy_gain * progress)
            acc_variance = random.gauss(0, 0.03)
            accuracy = min(1.0, max(0.7, skill_accuracy + acc_variance))
            
            # Session duration (30 seconds to 15 minutes)
            duration = random.uniform(30, 900)
            
            # Calculate keystrokes based on WPM and duration
            # Approximate: 5 characters per word, WPM * (duration / 60) * 5
            total_chars = int(wpm * (duration / 60) * 5)
            correct_chars = int(total_chars * accuracy)
            incorrect_chars = total_chars - correct_chars
            
            # Completion rate higher for shorter sessions and more skilled users
            completion_chance = 0.6 + (progress * 0.3) - (duration / 3000)
            completed = random.random() < max(0.3, min(0.95, completion_chance))
            
            # Generate timestamp within the day
            hour = random.choices(
                range(24),
                weights=[1,1,1,1,1,2,3,5,8,10,10,8,6,5,6,8,10,12,10,8,6,4,2,1],
                k=1
            )[0]
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            timestamp = current_date.replace(hour=hour, minute=minute, second=second)
            
            records.append((
                file_path,
                language,
                round(wpm, 1),
                round(accuracy, 4),
                total_chars,
                correct_chars,
                incorrect_chars,
                round(duration, 1),
                int(completed),
                timestamp.strftime("%Y-%m-%d %H:%M:%S")
            ))
    
    # Batch insert for performance
    cur.executemany("""
        INSERT INTO session_history (
            file_path, language, wpm, accuracy, total_keystrokes,
            correct_keystrokes, incorrect_keystrokes, duration, completed, recorded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, records)
    
    conn.commit()
    
    populate_auxiliary_stats(conn, records, languages)
    
    conn.close()
    
    print(f"Generated {len(records)} demo sessions over {days} days")
    return len(records)


def populate_auxiliary_stats(conn: sqlite3.Connection, sessions: list, languages: list):
    """Populate auxiliary stats like key heatmaps based on session data."""
    cur = conn.cursor()
    
    print("Generating heatmap and error stats...")
    
    # 1. Key Stats (Heatmap)
    # Include all standard keyboard keys (lower and upper)
    # Based on the layouts in KeyboardHeatmap
    rows_lower = "`1234567890-=" + "qwertyuiop[]\\" + "asdfghjkl;'" + "zxcvbnm,./"
    rows_upper = "~!@#$%^&*()_+" + "QWERTYUIOP{}|" + "ASDFGHJKL:\"" + "ZXCVBNM<>?"
    
    all_chars = rows_lower + rows_upper + " " # Add space
    
    key_records = []
    
    for lang in languages:
        # Check if language has any sessions
        # But even if not, we want some base "global" stats if possible, or just skip
        # The demo usually generates data for all languages in the list
        
        # Base multiplier based on language popularity (simulated)
        # But ensuring minimum activity for valid heatmap
        activity_multiplier = 1000 
        
        for char in all_chars:
            # Generate "balanced" stats
            # We want every key to have hits and some errors
            
            # Base frequency logic (common chars happen more)
            if char.lower() in "eiaorsntlcdupmhgbfywkvxzjq ":
                freq_factor = 2.0  # Common
            elif char in string.digits:
                freq_factor = 0.8
            else:
                freq_factor = 0.5  # Symbols/Upper rare
            
            # Randomize frequency a bit
            hits = int(activity_multiplier * freq_factor * random.uniform(0.5, 1.5))
            hits = max(15, hits) # Ensure at least 15 hits per key per language
            
            # Calculate accuracy - ensure it's not perfect
            # Random accuracy between 75% and 98%
            accuracy = random.uniform(0.75, 0.98)
            
            # Specific keys might have worse accuracy (e.g. number row, symbols)
            if char in "~!@#$%^&*()_+{}|:\"<>?":
                accuracy -= random.uniform(0.05, 0.15)
            
            correct = int(hits * accuracy)
            error = hits - correct
            
            # Ensure at least some errors
            if error == 0 and hits > 10:
                error = random.randint(1, int(hits * 0.1) + 1)
                correct = hits - error
            
            key_records.append((char, lang, correct, error))
            
    cur.executemany("INSERT INTO key_stats (char, language, correct_count, error_count) VALUES (?, ?, ?, ?)", key_records)
    
    # 2. Error Type Stats
    error_records = []
    for lang in languages:
        total_sessions = sum(1 for s in sessions if s[1] == lang)
        base_errors = total_sessions * 50
        
        omissions = int(base_errors * 0.4)
        insertions = int(base_errors * 0.2)
        transpositions = int(base_errors * 0.1)
        substitutions = int(base_errors * 0.3)
        
        error_records.append((lang, omissions, insertions, transpositions, substitutions))
        
    cur.executemany("""
        INSERT INTO error_type_stats (language, omissions, insertions, transpositions, substitutions)
        VALUES (?, ?, ?, ?, ?)
    """, error_records)
    
    # 3. File Stats
    # Aggregate from sessions
    file_map = {}
    for s in sessions:
        # s = (file_path, language, wpm, accuracy, total_chars, correct, incorrect, duration, completed, timestamp)
        fpath = s[0]
        wpm = s[2]
        acc = s[3]
        
        if fpath not in file_map:
            file_map[fpath] = {
                "best_wpm": 0, "last_wpm": 0, 
                "best_acc": 0, "last_acc": 0, 
                "times": 0, "completed": 0
            }
        
        fm = file_map[fpath]
        fm["last_wpm"] = wpm
        if wpm > fm["best_wpm"]: fm["best_wpm"] = wpm
        fm["last_acc"] = acc
        if acc > fm["best_acc"]: fm["best_acc"] = acc
        fm["times"] += 1
        if s[8]: fm["completed"] = 1 # Just mark if ever moved
    
    file_records = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for fpath, data in file_map.items():
        file_records.append((
            fpath, data["best_wpm"], data["last_wpm"], 
            data["best_acc"], data["last_acc"], 
            data["times"], now_str, data["completed"]
        ))
        
    cur.executemany("""
        INSERT INTO file_stats (file_path, best_wpm, last_wpm, best_accuracy, last_accuracy, times_practiced, last_practiced, completed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, file_records)
    
    conn.commit()


def ensure_demo_data():
    """Ensure demo data exists, generate if not."""
    if not demo_db_exists():
        print("Generating demo data for stats page...")
        conn = connect_demo()
        init_demo_tables(conn)
        conn.close()
        generate_demo_data()
    else:
        # Check if it has data
        conn = connect_demo()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM session_history")
        count = cur.fetchone()[0]
        conn.close()
        if count == 0:
            print("Demo database empty, regenerating...")
            conn = connect_demo()
            init_demo_tables(conn)
            conn.close()
            generate_demo_data()


def setup_demo_data(year: Optional[int] = None, persist: bool = False):
    """Setup demo data based on flags.
    
    Args:
        year: Specific year to generate data for.
        persist: If True, do not regenerate if exists.
    """
    if persist and demo_db_exists():
        print("Demo data persists (skipping regeneration)...")
        return

    print("Regenerating demo data...")
    # Force regenerate
    db_path = get_demo_db_path()
    if db_path.exists():
        try:
            db_path.unlink()
        except PermissionError:
            print("Warning: Could not delete existing demo DB (file might be in use). Appending/Updating instead.")
            
    conn = connect_demo()
    init_demo_tables(conn)
    conn.close()
    generate_demo_data(year=year)


if __name__ == "__main__":
    # Run directly to generate/regenerate demo data
    setup_demo_data()
    print(f"Demo database created at: {get_demo_db_path()}")
