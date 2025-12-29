"""Tests for ghost manager module."""
import pytest
import json
import gzip
from pathlib import Path
from unittest.mock import patch
from datetime import datetime
from app.ghost_manager import GhostManager, get_ghost_manager


@pytest.fixture
def temp_ghost_dir(tmp_path):
    """Create temporary ghost directory."""
    ghost_dir = tmp_path / "ghosts"
    ghost_dir.mkdir()
    return ghost_dir


@pytest.fixture
def sample_file(tmp_path):
    """Create a sample file for testing."""
    file_path = tmp_path / "test.py"
    file_path.write_text("print('hello world')")
    return str(file_path)


@pytest.fixture
def ghost_manager(temp_ghost_dir):
    """Create GhostManager with temporary directory."""
    with patch('app.ghost_manager.get_ghosts_dir', return_value=temp_ghost_dir):
        manager = GhostManager()
        return manager


def test_ghost_manager_initialization(ghost_manager, temp_ghost_dir):
    """Test GhostManager initializes correctly."""
    assert ghost_manager.ghosts_dir == temp_ghost_dir
    assert ghost_manager.ghosts_dir.exists()


def test_file_hash_generation(ghost_manager, sample_file):
    """Test file hash generation."""
    hash1 = ghost_manager._get_file_hash(sample_file)
    hash2 = ghost_manager._get_file_hash(sample_file)
    
    assert hash1 == hash2
    assert len(hash1) == 16  # Truncated to 16 chars


def test_file_hash_changes_with_content(ghost_manager, tmp_path):
    """Test that file hash changes when content changes."""
    file_path = tmp_path / "test.py"
    
    file_path.write_text("content1")
    hash1 = ghost_manager._get_file_hash(str(file_path))
    
    file_path.write_text("content2")
    hash2 = ghost_manager._get_file_hash(str(file_path))
    
    assert hash1 != hash2


def test_save_and_load_ghost(ghost_manager, sample_file):
    """Test saving and loading ghost data."""
    keystrokes = [
        {"t": 0.1, "k": "p", "c": True},
        {"t": 0.2, "k": "r", "c": True},
        {"t": 0.3, "k": "i", "c": True},
    ]
    
    # Save ghost
    result = ghost_manager.save_ghost(
        sample_file,
        wpm=50.5,
        accuracy=0.95,
        keystrokes=keystrokes,
        instant_death=False
    )
    
    assert result is True
    assert ghost_manager.has_ghost(sample_file)
    
    # Load ghost
    ghost_data = ghost_manager.load_ghost(sample_file)
    
    assert ghost_data is not None
    assert ghost_data["file"] == sample_file
    assert ghost_data["wpm"] == 50.5
    assert ghost_data["acc"] == 95.0  # Stored as percentage
    assert len(ghost_data["keys"]) == 3
    assert ghost_data["instant_death_mode"] is False


def test_should_save_ghost_first_time(ghost_manager, sample_file):
    """Test that first ghost should always be saved."""
    assert ghost_manager.should_save_ghost(sample_file, 30.0) is True


def test_should_save_ghost_better_wpm(ghost_manager, sample_file):
    """Test that ghost should be saved if WPM is better."""
    keystrokes = [{"t": 0.1, "k": "p", "c": True}]
    
    # Save initial ghost with 50 WPM
    ghost_manager.save_ghost(sample_file, 50.0, 0.95, keystrokes)
    
    # Should save with better WPM
    assert ghost_manager.should_save_ghost(sample_file, 60.0) is True
    
    # Should not save with worse WPM
    assert ghost_manager.should_save_ghost(sample_file, 40.0) is False


def test_delete_ghost(ghost_manager, sample_file):
    """Test deleting ghost."""
    keystrokes = [{"t": 0.1, "k": "p", "c": True}]
    
    # Save ghost
    ghost_manager.save_ghost(sample_file, 50.0, 0.95, keystrokes)
    assert ghost_manager.has_ghost(sample_file)
    
    # Delete ghost
    result = ghost_manager.delete_ghost(sample_file)
    assert result is True
    assert not ghost_manager.has_ghost(sample_file)


def test_get_ghost_stats(ghost_manager, sample_file):
    """Test getting ghost statistics without full data."""
    keystrokes = [
        {"t": 0.1, "k": "p", "c": True},
        {"t": 0.2, "k": "r", "c": True},
    ]
    
    ghost_manager.save_ghost(sample_file, 55.0, 0.98, keystrokes, instant_death=True)
    
    stats = ghost_manager.get_ghost_stats(sample_file)
    
    assert stats is not None
    assert stats["wpm"] == 55.0
    assert stats["accuracy"] == 98.0
    assert stats["keystroke_count"] == 2
    assert stats["instant_death"] is True
    assert "date" in stats


def test_ghost_compression(ghost_manager, sample_file):
    """Test that ghost files are compressed."""
    keystrokes = [{"t": 0.1, "k": "p", "c": True}] * 100  # Large data
    
    ghost_manager.save_ghost(sample_file, 50.0, 0.95, keystrokes)
    
    ghost_path = ghost_manager._get_ghost_path(sample_file)
    assert ghost_path.exists()
    assert ghost_path.suffix == ".gz"
    
    # Verify it's actually compressed (gzip file)
    with gzip.open(ghost_path, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    assert data is not None


def test_get_ghost_manager_singleton():
    """Test that get_ghost_manager returns singleton."""
    manager1 = get_ghost_manager()
    manager2 = get_ghost_manager()
    
    assert manager1 is manager2


def test_load_ghost_nonexistent_file(ghost_manager, tmp_path):
    """Test loading ghost for non-existent file."""
    fake_file = str(tmp_path / "nonexistent.py")
    ghost_data = ghost_manager.load_ghost(fake_file)
    
    assert ghost_data is None


def test_save_ghost_with_final_stats(ghost_manager, sample_file):
    """Test saving ghost with final stats."""
    keystrokes = [{"t": 0.1, "k": "p", "c": True}]
    final_stats = {
        "correct": 10,
        "incorrect": 2,
        "time": 30.5
    }
    
    ghost_manager.save_ghost(
        sample_file, 45.0, 0.90, keystrokes,
        final_stats=final_stats
    )
    
    ghost_data = ghost_manager.load_ghost(sample_file)
    assert ghost_data["final_stats"] == final_stats


def test_ghost_path_unique_per_content(ghost_manager, tmp_path):
    """Test that ghost paths are unique per file content."""
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"
    
    file1.write_text("content1")
    file2.write_text("content2")
    
    path1 = ghost_manager._get_ghost_path(str(file1))
    path2 = ghost_manager._get_ghost_path(str(file2))
    
    assert path1 != path2
