"""Tests for incomplete file highlighting in file tree."""
import pytest
from pathlib import Path
from app import settings
from app.stats_db import (
    init_stats_tables,
    save_session_progress,
    is_session_incomplete,
    get_incomplete_sessions,
    clear_session_progress
)


def test_is_session_incomplete_paused(tmp_path):
    """Test detecting incomplete session for paused file."""
    db_path = tmp_path / "test.db"
    settings.init_db(str(db_path))
    init_stats_tables()
    
    file_path = str(tmp_path / "test.py")
    
    # Save paused session
    save_session_progress(
        file_path=file_path,
        cursor_pos=50,
        total_chars=100,
        correct=45,
        incorrect=5,
        time=30.0,
        is_paused=True
    )
    
    assert is_session_incomplete(file_path) is True


def test_is_session_incomplete_not_finished(tmp_path):
    """Test detecting incomplete session for unfinished file."""
    db_path = tmp_path / "test.db"
    settings.init_db(str(db_path))
    init_stats_tables()
    
    file_path = str(tmp_path / "test.py")
    
    # Save session that's not at the end
    save_session_progress(
        file_path=file_path,
        cursor_pos=50,
        total_chars=100,
        correct=45,
        incorrect=5,
        time=30.0,
        is_paused=False
    )
    
    assert is_session_incomplete(file_path) is True


def test_is_session_incomplete_completed(tmp_path):
    """Test that completed session is not marked as incomplete."""
    db_path = tmp_path / "test.db"
    settings.init_db(str(db_path))
    init_stats_tables()
    
    file_path = str(tmp_path / "test.py")
    
    # Save completed session
    save_session_progress(
        file_path=file_path,
        cursor_pos=100,
        total_chars=100,
        correct=95,
        incorrect=5,
        time=60.0,
        is_paused=False
    )
    
    assert is_session_incomplete(file_path) is False


def test_is_session_incomplete_no_session(tmp_path):
    """Test that file with no session is not marked as incomplete."""
    db_path = tmp_path / "test.db"
    settings.init_db(str(db_path))
    init_stats_tables()
    
    file_path = str(tmp_path / "test.py")
    
    assert is_session_incomplete(file_path) is False


def test_get_incomplete_sessions_multiple(tmp_path):
    """Test getting multiple incomplete sessions."""
    db_path = tmp_path / "test.db"
    settings.init_db(str(db_path))
    init_stats_tables()
    
    file1 = str(tmp_path / "test1.py")
    file2 = str(tmp_path / "test2.py")
    file3 = str(tmp_path / "test3.py")
    
    # File 1: Paused
    save_session_progress(file1, 50, 100, 45, 5, 30.0, is_paused=True)
    
    # File 2: Not finished
    save_session_progress(file2, 30, 100, 28, 2, 20.0, is_paused=False)
    
    # File 3: Completed
    save_session_progress(file3, 100, 100, 95, 5, 60.0, is_paused=False)
    
    incomplete = get_incomplete_sessions()
    
    assert len(incomplete) == 2
    assert file1 in incomplete
    assert file2 in incomplete
    assert file3 not in incomplete


def test_get_incomplete_sessions_empty(tmp_path):
    """Test getting incomplete sessions when there are none."""
    db_path = tmp_path / "test.db"
    settings.init_db(str(db_path))
    init_stats_tables()
    
    incomplete = get_incomplete_sessions()
    assert incomplete == []


def test_incomplete_session_cleared(tmp_path):
    """Test that cleared session is no longer marked as incomplete."""
    db_path = tmp_path / "test.db"
    settings.init_db(str(db_path))
    init_stats_tables()
    
    file_path = str(tmp_path / "test.py")
    
    # Save incomplete session
    save_session_progress(file_path, 50, 100, 45, 5, 30.0, is_paused=True)
    assert is_session_incomplete(file_path) is True
    
    # Clear session
    clear_session_progress(file_path)
    assert is_session_incomplete(file_path) is False


def test_incomplete_session_updated_to_complete(tmp_path):
    """Test that updating session to complete removes incomplete status."""
    db_path = tmp_path / "test.db"
    settings.init_db(str(db_path))
    init_stats_tables()
    
    file_path = str(tmp_path / "test.py")
    
    # Save incomplete session
    save_session_progress(file_path, 50, 100, 45, 5, 30.0, is_paused=True)
    assert is_session_incomplete(file_path) is True
    
    # Update to complete
    save_session_progress(file_path, 100, 100, 95, 5, 60.0, is_paused=False)
    assert is_session_incomplete(file_path) is False


def test_get_incomplete_sessions_after_clear(tmp_path):
    """Test get_incomplete_sessions after clearing some sessions."""
    db_path = tmp_path / "test.db"
    settings.init_db(str(db_path))
    init_stats_tables()
    
    file1 = str(tmp_path / "test1.py")
    file2 = str(tmp_path / "test2.py")
    
    # Both incomplete
    save_session_progress(file1, 50, 100, 45, 5, 30.0, is_paused=True)
    save_session_progress(file2, 30, 100, 28, 2, 20.0, is_paused=True)
    
    incomplete = get_incomplete_sessions()
    assert len(incomplete) == 2
    
    # Clear one
    clear_session_progress(file1)
    
    incomplete = get_incomplete_sessions()
    assert len(incomplete) == 1
    assert file2 in incomplete
    assert file1 not in incomplete
