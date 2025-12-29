"""Tests for language cache module."""
import pytest
from pathlib import Path
from app import language_cache, settings


@pytest.fixture
def setup_db(tmp_path):
    """Setup test database."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    yield tmp_path


def test_build_signature_empty(setup_db):
    """Test building signature with empty folder list."""
    sig = language_cache.build_signature([])
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA256 hex digest


def test_build_signature_consistent(setup_db, tmp_path):
    """Test that signature is consistent for same folders."""
    folder = tmp_path / "test_folder"
    folder.mkdir()
    (folder / "test.py").write_text("print('hello')")
    
    sig1 = language_cache.build_signature([str(folder)])
    sig2 = language_cache.build_signature([str(folder)])
    
    assert sig1 == sig2


def test_build_signature_changes_on_modification(setup_db, tmp_path):
    """Test that signature changes when folder contents change."""
    folder = tmp_path / "test_folder"
    folder.mkdir()
    file = folder / "test.py"
    
    file.write_text("print('hello')")
    sig1 = language_cache.build_signature([str(folder)])
    
    # Modify file and touch folder to update mtime
    import time
    time.sleep(0.01)  # Ensure time difference
    file.write_text("print('hello world')")
    folder.touch()  # Update folder mtime
    sig2 = language_cache.build_signature([str(folder)])
    
    assert sig1 != sig2


def test_save_and_load_snapshot(setup_db, tmp_path):
    """Test saving and loading cached snapshot."""
    signature = "test_signature_hash"
    language_files = {"Python": [str(tmp_path / "test.py")]}
    
    # Save snapshot
    language_cache.save_snapshot(signature, language_files)
    
    # Load snapshot
    result = language_cache.load_cached_snapshot()
    
    assert result is not None
    signature, loaded_files = result
    assert isinstance(signature, str)
    assert "Python" in loaded_files


def test_load_snapshot_nonexistent(setup_db):
    """Test loading snapshot when cache doesn't exist."""
    # Use a completely isolated settings environment
    from pathlib import Path
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize a fresh database with a different path
        db_file = Path(tmpdir) / "test_nonexistent.db"
        settings.init_db(str(db_file))
        
        # Ensure cache file doesn't exist
        cache_file = language_cache._cache_path()
        if cache_file.exists():
            os.remove(cache_file)
        
        # Don't save anything - cache file shouldn't exist
        result = language_cache.load_cached_snapshot()
        
        # Should return None for nonexistent cache
        assert result is None


def test_snapshot_invalidated_on_change(setup_db, tmp_path):
    """Test that snapshot is invalidated when folders change."""
    folder = tmp_path / "test_folder"
    folder.mkdir()
    file = folder / "test.py"
    file.write_text("print('hello')")
    
    folders = [str(folder)]
    language_files = {"Python": [str(file)]}
    
    # Build initial signature and save snapshot
    old_sig = language_cache.build_signature(folders)
    language_cache.save_snapshot(old_sig, language_files)
    
    # Verify signature matches
    loaded = language_cache.load_cached_snapshot()
    assert loaded is not None
    assert loaded[0] == old_sig
    
    # Modify file and touch folder to update mtime
    import time
    time.sleep(0.01)  # Ensure time difference
    file.write_text("print('modified')")
    folder.touch()  # Update folder mtime
    
    # New signature should be different
    new_sig = language_cache.build_signature(folders)
    assert new_sig != old_sig
