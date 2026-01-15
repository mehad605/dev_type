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


def connect_demo(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Connect to the demo database or a specified database."""
    target_path = db_path if db_path else get_demo_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(target_path))


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


def generate_data_for_db(
    db_path: Path,
    year: Optional[int] = None,
    days: int = 365,
    sessions_range: tuple = (3, 10),
    languages: Optional[list] = None
):
    """Core generation logic that writes to a specific DB path."""
    conn = connect_demo(db_path)
    cur = conn.cursor()
    
    # Clear existing data for fresh generation? 
    # Or should we append? The legacy behavior was "delete everything then generate".
    # Let's clean up first to be safe and consistent.
    tables = ["session_history", "key_stats", "file_stats", "error_type_stats", "key_confusions"]
    for table in tables:
        try:
            cur.execute(f"DELETE FROM {table}")
        except sqlite3.OperationalError:
            # Table might not exist yet if initializing fresh
            pass
            
    # Ensure tables exist
    init_demo_tables(conn)
    
    # Configuration
    if not languages:
        languages = ["Python", "JavaScript", "TypeScript", "Rust", "Go", "C++", "Java", "C#"]
        language_weights = [30, 25, 15, 10, 8, 5, 4, 3]
    else:
        # Equal weights if custom list provided
        language_weights = [1] * len(languages)

    # File path templates
    all_file_templates = {
        "Python": ["main.py", "app.py", "utils.py", "models.py", "views.py", "api.py"],
        "JavaScript": ["index.js", "app.js", "utils.js", "components.js", "api.js"],
        "TypeScript": ["index.ts", "app.ts", "types.ts", "utils.ts", "api.ts"],
        "Rust": ["main.rs", "lib.rs", "utils.rs", "mod.rs"],
        "Go": ["main.go", "handler.go", "utils.go", "server.go"],
        "C++": ["main.cpp", "utils.cpp", "app.cpp", "handler.cpp"],
        "Java": ["Main.java", "App.java", "Utils.java", "Service.java"],
        "C#": ["Program.cs", "App.cs", "Utils.cs", "Service.cs"],
        "Markdown": ["README.md", "guide.md", "notes.md"],
        "HTML": ["index.html", "about.html", "contact.html"],
        "CSS": ["style.css", "main.css", "theme.css"],
        "JSON": ["package.json", "config.json", "data.json"],
        "SQL": ["schema.sql", "query.sql", "migrations.sql"],
        "Shell": ["install.sh", "deploy.sh", "run.sh"],
    }
    
    # Params
    base_wpm = 35
    max_wpm_gain = 45
    base_accuracy = 0.85
    max_accuracy_gain = 0.12
    
    if year:
        start_date = datetime(year, 1, 1)
        days = 366 if calendar.isleap(year) else 365
    else:
        today = datetime.now()
        start_date = today - timedelta(days=days)
    
    print(f"Generating data from {start_date.date()} to {start_date.date() + timedelta(days=days-1)}")
    
    records = []
    
    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)
        progress = day_offset / days
        
        is_weekend = current_date.weekday() >= 5
        days_from_end = days - day_offset
        is_break_day = random.random() < 0.15 if days_from_end > 10 else False
        
        if is_break_day:
            num_sessions = 0
        elif is_weekend:
            num_sessions = random.randint(1 if days_from_end <= 10 else 0, max(1, sessions_range[1] // 2))
        else:
            num_sessions = random.randint(sessions_range[0], sessions_range[1])
        
        for _ in range(num_sessions):
            language = random.choices(languages, weights=language_weights, k=1)[0]
            
            # Fallback for templates
            templates = all_file_templates.get(language, ["file.txt", "script" + ("" if language == "Text" else f".{language[:2].lower()}")])
            file_name = random.choice(templates)
            file_path = f"/demo/projects/{language.lower()}/{file_name}"
            
            skill_wpm = base_wpm + (max_wpm_gain * progress)
            daily_variance = random.gauss(0, 8)
            session_variance = random.gauss(0, 5)
            wpm = max(20, skill_wpm + daily_variance + session_variance)
            
            if random.random() < 0.05:
                wpm += random.uniform(10, 25)
            
            skill_accuracy = base_accuracy + (max_accuracy_gain * progress)
            acc_variance = random.gauss(0, 0.03)
            accuracy = min(1.0, max(0.7, skill_accuracy + acc_variance))
            
            duration = random.uniform(30, 900)
            total_chars = int(wpm * (duration / 60) * 5)
            correct_chars = int(total_chars * accuracy)
            incorrect_chars = total_chars - correct_chars
            
            completion_chance = 0.6 + (progress * 0.3) - (duration / 3000)
            completed = random.random() < max(0.3, min(0.95, completion_chance))
            
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
    
    # Write to DB
    cur.executemany("""
        INSERT INTO session_history (
            file_path, language, wpm, accuracy, total_keystrokes,
            correct_keystrokes, incorrect_keystrokes, duration, completed, recorded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, records)
    
    conn.commit()
    
    populate_auxiliary_stats(conn, records, languages)
    conn.close()
    
    print(f"Generated {len(records)} demo sessions in: {db_path}")
    return len(records)


def generate_demo_data(year: Optional[int] = None, days: int = 365, sessions_per_day_range: tuple = (3, 10)):
    """Legacy wrapper: Generate demo data for the sandbox database."""
    db_path = get_demo_db_path()
    generate_data_for_db(db_path, year=year, days=days, sessions_range=sessions_per_day_range)


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
    
    # Cache key stats for confusion generation: (char, language) -> error_count
    key_error_counts = {} 
    
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
    
    # 3. Key Confusions (New)
    print("Generating key confusion data...")
    confusion_records = []
    
    # Simple QWERTY adjacency map for realistic errors
    qwerty_adj = {
        'q': 'wa', 'w': 'qase', 'e': 'wsdr', 'r': 'edft', 't': 'rfgy', 'y': 'tghu', 'u': 'yhji', 'i': 'ujko', 'o': 'iklp', 'p': 'ol',
        'a': 'qwsz', 's': 'qweadzx', 'd': 'wersfxc', 'f': 'ertdgcv', 'g': 'rtyfhvb', 'h': 'tyugjbn', 'j': 'yuihkmn', 'k': 'uiojlm', 'l': 'iopk',
        'z': 'asx', 'x': 'sdzc', 'c': 'dfxv', 'v': 'fgcb', 'b': 'ghvn', 'n': 'hjbm', 'm': 'jkln',
        ' ': 'cvbnm', # Thumbing space might hit bottom row
        '1': '2q', '2': '1q3w', '3': '2w4e', '4': '3e5r', '5': '4r6t', '6': '5t7y', '7': '6y8u', '8': '7u9i', '9': '8i0o', '0': '9op-',
        '-': '0p=', '=': '-[]'
    }
    
    # Process the key stats we just generated to create matching confusions
    # We loop through key_records which is list of (char, lang, correct, error)
    for char, lang, correct, error in key_records:
        if error <= 0:
            continue
            
        # Determine likely confusions
        lower_char = char.lower()
        adj_chars = qwerty_adj.get(lower_char, "")
        
        # If no adjacency known (symbols/caps), pick randoms or use self (as if double typed)
        if not adj_chars:
            pool = "etaoinshrdlcumwfgypbvkjxqz" 
            adj_chars = "".join(random.sample(pool, 3))
            
        # Distribute the total 'error' count among 1-3 confusion candidates
        remaining_errors = error
        
        # Pick 1-3 confusion keys
        num_confusions = min(len(adj_chars), random.randint(1, 3))
        conf_keys = random.sample(list(adj_chars), num_confusions)
        
        for i, conf_key in enumerate(conf_keys):
            if i == len(conf_keys) - 1:
                count = remaining_errors
            else:
                # Give a chunk
                count = random.randint(1, max(1, remaining_errors - (len(conf_keys) - i)))
            
            remaining_errors -= count
            
            # Adjust case to match original if possible (simple heuristic)
            actual_char = conf_key.upper() if char.isupper() else conf_key
            
            confusion_records.append((char, actual_char, lang, count))

    cur.executemany("""
        INSERT INTO key_confusions (expected_char, actual_char, language, count)
        VALUES (?, ?, ?, ?)
    """, confusion_records)

    # 4. File Stats
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


def setup_demo_data(year: Optional[int] = None, persist: bool = False, db_path: Optional[Path] = None):
    """Setup demo data based on flags.
    
    Args:
        year: Specific year to generate data for.
        persist: If True, do not regenerate if exists (only for default demo DB).
        db_path: Target database path. If provided, persist check is skipped (always generates).
    """
    target_path = db_path if db_path else get_demo_db_path()

    if not db_path and persist and target_path.exists():
        print("Demo data persists (skipping regeneration)...")
        return

    print(f"Regenerating data in {target_path}...")
    
    # Only force-delete the file if it's the specific demo DB (sandbox)
    # If targeting a profile DB, we let generate_data_for_db handle the table clearing
    if not db_path:
        if target_path.exists():
            try:
                target_path.unlink()
            except PermissionError:
                print("Warning: Could not delete existing DB. Overwriting tables instead.")
            
    generate_data_for_db(target_path, year=year)


if __name__ == "__main__":
    # Run directly to generate/regenerate demo data
    setup_demo_data()
    print(f"Demo database created at: {get_demo_db_path()}")
