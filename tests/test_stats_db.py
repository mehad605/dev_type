"""Tests for typing statistics database module."""
from pathlib import Path
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
