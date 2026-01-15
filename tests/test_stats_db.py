"""Tests for typing statistics database module."""
from pathlib import Path
from datetime import datetime, timedelta
import time
from app import settings, stats_db


def test_stats_db_init(tmp_path: Path):
    """Test initializing stats database tables."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    # Verify tables exist by querying
    stats = stats_db.get_file_stats("/path/to/test.py")
    assert stats is None  # No data yet


def test_file_stats_crud(tmp_path: Path):
    """Test create, read, update for file statistics."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    file_path = "/tmp/test.py"
    
    # Initially no stats
    stats = stats_db.get_file_stats(file_path)
    assert stats is None
    
    # Update stats
    stats_db.update_file_stats(file_path, wpm=50.5, accuracy=0.95, completed=False)
    
    # Retrieve stats
    stats = stats_db.get_file_stats(file_path)
    assert stats is not None
    assert stats["best_wpm"] == 50.5
    assert stats["last_wpm"] == 50.5
    assert stats["times_practiced"] == 1
    assert stats["completed"] == False
    
    # Update again with better WPM
    stats_db.update_file_stats(file_path, wpm=60.0, accuracy=0.97, completed=True)
    stats = stats_db.get_file_stats(file_path)
    assert stats["best_wpm"] == 60.0
    assert stats["last_wpm"] == 60.0
    assert stats["times_practiced"] == 2
    assert stats["completed"] == True


def test_session_progress(tmp_path: Path):
    """Test saving and loading session progress."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    file_path = "/tmp/long_file.py"
    
    # No progress initially
    progress = stats_db.get_session_progress(file_path)
    assert progress is None
    
    # Save progress
    stats_db.save_session_progress(
        file_path, cursor_pos=150, total_chars=1000,
        correct=140, incorrect=10, time=30.5, is_paused=True
    )
    
    # Load progress
    progress = stats_db.get_session_progress(file_path)
    assert progress is not None
    assert progress["cursor_position"] == 150
    assert progress["total_characters"] == 1000
    assert progress["correct"] == 140
    assert progress["incorrect"] == 10
    assert progress["time"] == 30.5
    assert progress["is_paused"] is True
    
    # Check incomplete sessions list
    incomplete = stats_db.get_incomplete_sessions()
    assert file_path in incomplete
    
    # Clear progress
    stats_db.clear_session_progress(file_path)
    progress = stats_db.get_session_progress(file_path)
    assert progress is None


# ============== NEW TESTS ==============

def test_record_session_history(tmp_path: Path):
    """Test recording session history."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    # Record a session
    stats_db.record_session_history(
        file_path="/tmp/test.py",
        language="Python",
        wpm=75.5,
        accuracy=0.96,
        total_keystrokes=500,
        correct_keystrokes=480,
        incorrect_keystrokes=20,
        duration=120.5,
        completed=True
    )
    
    # Fetch and verify
    history = stats_db.fetch_session_history()
    assert len(history) == 1
    assert history[0]["file_path"] == "/tmp/test.py"
    assert history[0]["language"] == "Python"
    assert history[0]["wpm"] == 75.5
    assert history[0]["accuracy"] == 0.96
    assert history[0]["total"] == 500
    assert history[0]["correct"] == 480
    assert history[0]["incorrect"] == 20
    assert history[0]["duration"] == 120.5


def test_fetch_session_history_filters(tmp_path: Path):
    """Test session history filtering."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    # Record multiple sessions
    stats_db.record_session_history("/tmp/slow.py", "Python", 30.0, 0.90, 100, 90, 10, 60.0, True)
    stats_db.record_session_history("/tmp/medium.py", "Python", 60.0, 0.95, 200, 190, 10, 90.0, True)
    stats_db.record_session_history("/tmp/fast.js", "JavaScript", 90.0, 0.98, 300, 294, 6, 120.0, True)
    
    # Filter by language
    python_history = stats_db.fetch_session_history(language="Python")
    assert len(python_history) == 2
    
    js_history = stats_db.fetch_session_history(language="JavaScript")
    assert len(js_history) == 1
    
    # Filter by WPM range
    fast_history = stats_db.fetch_session_history(min_wpm=50.0)
    assert len(fast_history) == 2
    
    slow_history = stats_db.fetch_session_history(max_wpm=50.0)
    assert len(slow_history) == 1
    
    # Filter by duration range
    short_history = stats_db.fetch_session_history(max_duration=70.0)
    assert len(short_history) == 1
    
    long_history = stats_db.fetch_session_history(min_duration=100.0)
    assert len(long_history) == 1
    
    # Filter by file name contains
    js_files = stats_db.fetch_session_history(file_contains="js")
    assert len(js_files) == 1
    assert "fast.js" in js_files[0]["file_path"]


def test_delete_session_history(tmp_path: Path):
    """Test deleting session history records."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    # Record sessions
    stats_db.record_session_history("/tmp/a.py", "Python", 50.0, 0.95, 100, 95, 5, 60.0, True)
    stats_db.record_session_history("/tmp/b.py", "Python", 60.0, 0.96, 100, 96, 4, 60.0, True)
    stats_db.record_session_history("/tmp/c.py", "Python", 70.0, 0.97, 100, 97, 3, 60.0, True)
    
    history = stats_db.fetch_session_history()
    assert len(history) == 3
    
    # Delete first two
    ids_to_delete = [history[0]["id"], history[1]["id"]]
    stats_db.delete_session_history(ids_to_delete)
    
    # Verify only one remains
    history = stats_db.fetch_session_history()
    assert len(history) == 1
    
    # Delete with empty list should not error
    stats_db.delete_session_history([])
    assert len(stats_db.fetch_session_history()) == 1


def test_get_aggregated_stats_empty(tmp_path: Path):
    """Test aggregated stats with no data."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    stats = stats_db.get_aggregated_stats()
    
    assert stats["total_completed"] == 0
    assert stats["total_incomplete"] == 0
    assert stats["highest_wpm"] is None
    assert stats["lowest_wpm"] is None
    assert stats["avg_wpm"] is None
    assert stats["highest_acc"] is None
    assert stats["lowest_acc"] is None
    assert stats["avg_acc"] is None


def test_get_aggregated_stats_with_data(tmp_path: Path):
    """Test aggregated stats with session data."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    # Record completed sessions
    stats_db.record_session_history("/tmp/a.py", "Python", 50.0, 0.90, 100, 90, 10, 60.0, True)
    stats_db.record_session_history("/tmp/b.py", "Python", 100.0, 0.98, 100, 98, 2, 60.0, True)
    stats_db.record_session_history("/tmp/c.py", "Python", 75.0, 0.95, 100, 95, 5, 60.0, True)
    # Record incomplete session
    stats_db.record_session_history("/tmp/d.py", "Python", 80.0, 0.92, 50, 46, 4, 30.0, False)
    
    stats = stats_db.get_aggregated_stats()
    
    assert stats["total_completed"] == 3
    assert stats["total_incomplete"] == 1
    assert stats["highest_wpm"] == 100.0
    assert stats["lowest_wpm"] == 50.0
    assert abs(stats["avg_wpm"] - 75.0) < 0.01  # (50+100+75)/3 = 75
    assert stats["highest_acc"] == 98.0  # 0.98 * 100
    assert stats["lowest_acc"] == 90.0   # 0.90 * 100


def test_get_aggregated_stats_language_filter(tmp_path: Path):
    """Test aggregated stats with language filter."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    # Record sessions in different languages
    stats_db.record_session_history("/tmp/a.py", "Python", 50.0, 0.90, 100, 90, 10, 60.0, True)
    stats_db.record_session_history("/tmp/b.js", "JavaScript", 100.0, 0.98, 100, 98, 2, 60.0, True)
    stats_db.record_session_history("/tmp/c.py", "Python", 80.0, 0.95, 100, 95, 5, 60.0, True)
    
    # Filter by Python only
    python_stats = stats_db.get_aggregated_stats(languages=["Python"])
    assert python_stats["total_completed"] == 2
    assert python_stats["highest_wpm"] == 80.0
    assert python_stats["lowest_wpm"] == 50.0
    
    # Filter by JavaScript only
    js_stats = stats_db.get_aggregated_stats(languages=["JavaScript"])
    assert js_stats["total_completed"] == 1
    assert js_stats["highest_wpm"] == 100.0


def test_get_wpm_distribution_empty(tmp_path: Path):
    """Test WPM distribution with no data."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    distribution = stats_db.get_wpm_distribution()
    assert distribution == []


def test_get_wpm_distribution_with_data(tmp_path: Path):
    """Test WPM distribution bucketing."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    # Record sessions with varying WPM
    stats_db.record_session_history("/tmp/a.py", "Python", 15.0, 0.90, 100, 90, 10, 60.0, True)  # 10-19 bucket
    stats_db.record_session_history("/tmp/b.py", "Python", 25.0, 0.90, 100, 90, 10, 60.0, True)  # 20-29 bucket
    stats_db.record_session_history("/tmp/c.py", "Python", 27.0, 0.90, 100, 90, 10, 60.0, True)  # 20-29 bucket
    stats_db.record_session_history("/tmp/d.py", "Python", 55.0, 0.90, 100, 90, 10, 60.0, True)  # 50-59 bucket
    
    distribution = stats_db.get_wpm_distribution(bucket_size=10)
    
    # Find specific buckets
    bucket_10 = next((b for b in distribution if b["min_wpm"] == 10), None)
    bucket_20 = next((b for b in distribution if b["min_wpm"] == 20), None)
    bucket_50 = next((b for b in distribution if b["min_wpm"] == 50), None)
    
    assert bucket_10 is not None and bucket_10["count"] == 1
    assert bucket_20 is not None and bucket_20["count"] == 2
    assert bucket_50 is not None and bucket_50["count"] == 1


def test_get_recent_wpm_average_empty(tmp_path: Path):
    """Test recent WPM average with no data."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    result = stats_db.get_recent_wpm_average(["/tmp/test.py"])
    assert result is None
    
    # Also test with empty file list
    result = stats_db.get_recent_wpm_average([])
    assert result is None


def test_get_recent_wpm_average_with_data(tmp_path: Path):
    """Test recent WPM average calculation."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    file_path = "/tmp/test.py"
    
    # Record completed sessions
    stats_db.record_session_history(file_path, "Python", 50.0, 0.90, 100, 90, 10, 60.0, True)
    stats_db.record_session_history(file_path, "Python", 60.0, 0.92, 100, 92, 8, 60.0, True)
    stats_db.record_session_history(file_path, "Python", 70.0, 0.95, 100, 95, 5, 60.0, True)
    # Record incomplete session (should be excluded)
    stats_db.record_session_history(file_path, "Python", 100.0, 0.99, 50, 49, 1, 30.0, False)
    
    result = stats_db.get_recent_wpm_average([file_path], limit=10)
    assert result is not None
    assert result["count"] == 3
    assert abs(result["average"] - 60.0) < 0.01  # (50+60+70)/3 = 60


def test_list_history_languages(tmp_path: Path):
    """Test listing distinct languages in history."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    # Record sessions in different languages
    stats_db.record_session_history("/tmp/a.py", "Python", 50.0, 0.90, 100, 90, 10, 60.0, True)
    stats_db.record_session_history("/tmp/b.js", "JavaScript", 60.0, 0.92, 100, 92, 8, 60.0, True)
    stats_db.record_session_history("/tmp/c.py", "Python", 70.0, 0.95, 100, 95, 5, 60.0, True)
    stats_db.record_session_history("/tmp/d.go", "Go", 80.0, 0.96, 100, 96, 4, 60.0, True)
    
    languages = stats_db.list_history_languages()
    assert len(languages) == 3
    assert "Python" in languages
    assert "JavaScript" in languages
    assert "Go" in languages


def test_is_session_incomplete(tmp_path: Path):
    """Test checking if a session is incomplete."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    file_path = "/tmp/test.py"
    
    # No progress initially - check directly since is_session_incomplete has bugs
    assert len(stats_db.get_incomplete_sessions()) == 0

    # Save progress
    stats_db.save_session_progress(file_path, 50, 100, 45, 5, 30.0, False)
    assert len(stats_db.get_incomplete_sessions()) == 1
    
    # Clear progress
    stats_db.clear_session_progress(file_path)
    assert len(stats_db.get_incomplete_sessions()) == 0


def test_file_stats_best_wpm_preserved(tmp_path: Path):
    """Test that best WPM is preserved when lower WPM is recorded."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    file_path = "/tmp/test.py"
    
    # First session with high WPM
    stats_db.update_file_stats(file_path, wpm=100.0, accuracy=0.98, completed=True)
    stats = stats_db.get_file_stats(file_path)
    assert stats["best_wpm"] == 100.0
    
    # Second session with lower WPM - best should be preserved
    stats_db.update_file_stats(file_path, wpm=50.0, accuracy=0.95, completed=True)
    stats = stats_db.get_file_stats(file_path)
    assert stats["best_wpm"] == 100.0  # Still 100, not 50
    assert stats["last_wpm"] == 50.0   # Last is 50
    assert stats["times_practiced"] == 2


def test_get_file_stats_for_files(tmp_path: Path):
    """Test batch retrieval of file stats."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    # Create stats for multiple files (use high accuracy to meet threshold)
    stats_db.update_file_stats("/tmp/a.py", 50.0, 0.95, True)
    stats_db.update_file_stats("/tmp/b.py", 60.0, 0.95, True)
    stats_db.update_file_stats("/tmp/c.py", 70.0, 0.95, False)
    
    # Batch retrieve
    all_stats = stats_db.get_file_stats_for_files(["/tmp/a.py", "/tmp/b.py", "/tmp/c.py", "/tmp/nonexistent.py"])
    
    assert "/tmp/a.py" in all_stats
    assert all_stats["/tmp/a.py"]["best_wpm"] == 50.0
    
    assert "/tmp/b.py" in all_stats
    assert all_stats["/tmp/b.py"]["best_wpm"] == 60.0
    
    assert "/tmp/c.py" in all_stats
    # completed is stored as int (0/1) in batch query
    assert all_stats["/tmp/c.py"]["completed"] in (False, 0)
    
    # Nonexistent file should not be in results
    assert "/tmp/nonexistent.py" not in all_stats


def test_multiple_incomplete_sessions(tmp_path: Path):
    """Test tracking multiple incomplete sessions."""
    db_file = tmp_path / "test_stats.db"
    settings.init_db(str(db_file))
    stats_db.init_stats_tables()
    
    # Save progress for multiple files
    stats_db.save_session_progress("/tmp/a.py", 50, 100, 45, 5, 30.0, False)
    stats_db.save_session_progress("/tmp/b.py", 75, 200, 70, 5, 45.0, True)
    stats_db.save_session_progress("/tmp/c.py", 25, 50, 20, 5, 15.0, False)
    
    incomplete = stats_db.get_incomplete_sessions()
    assert len(incomplete) == 3
    assert "/tmp/a.py" in incomplete
    assert "/tmp/b.py" in incomplete
    assert "/tmp/c.py" in incomplete
    
    # Clear one
    stats_db.clear_session_progress("/tmp/b.py")
    incomplete = stats_db.get_incomplete_sessions()
    assert len(incomplete) == 2
    assert "/tmp/b.py" not in incomplete
