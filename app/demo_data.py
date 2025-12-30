"""Generate demo data for testing the Stats page.

This module creates realistic fake typing session data spanning one year.
Run the app with --demo flag to use demo data: `python main.py --demo`
"""
import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

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
    
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_demo_session_history_language
                   ON session_history(language)""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_demo_session_history_date
                   ON session_history(recorded_at)""")
    
    conn.commit()


def generate_demo_data(days: int = 365, sessions_per_day_range: tuple = (0, 8)):
    """Generate realistic demo data for the stats page.
    
    Args:
        days: Number of days of history to generate (default 365 = 1 year)
        sessions_per_day_range: Tuple of (min, max) sessions per day
    """
    conn = connect_demo()
    cur = conn.cursor()
    
    # Clear existing demo data
    cur.execute("DELETE FROM session_history")
    
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
    
    today = datetime.now()
    start_date = today - timedelta(days=days)
    
    records = []
    
    for day_offset in range(days + 1):
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
    conn.close()
    
    print(f"Generated {len(records)} demo sessions over {days} days")
    return len(records)


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


def regenerate_demo_data():
    """Force regenerate demo data (useful for testing)."""
    db_path = get_demo_db_path()
    if db_path.exists():
        db_path.unlink()
    conn = connect_demo()
    init_demo_tables(conn)
    conn.close()
    generate_demo_data()


if __name__ == "__main__":
    # Run directly to generate/regenerate demo data
    regenerate_demo_data()
    print(f"Demo database created at: {get_demo_db_path()}")
