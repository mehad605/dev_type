"""Tests for language_cache.py"""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.language_cache import build_signature, load_cached_snapshot, save_snapshot

@pytest.fixture
def mock_pdm(tmp_path):
    profile_dir = tmp_path / "profiles" / "User1"
    profile_dir.mkdir(parents=True)
    with patch("app.portable_data.get_data_manager") as mock_gdm:
        mock_dm = MagicMock()
        mock_dm.get_active_profile_dir.return_value = profile_dir
        mock_gdm.return_value = mock_dm
        yield profile_dir

def test_save_and_load_snapshot(mock_pdm):
    signature = "test_sig"
    data = {"Python": ["a.py", "b.py"]}
    
    save_snapshot(signature, data)
    
    # Verify file existence in profile dir
    cache_file = mock_pdm / "language_snapshot.json"
    assert cache_file.exists()
    
    # Reload
    loaded = load_cached_snapshot()
    assert loaded is not None
    loaded_sig, loaded_data = loaded
    assert loaded_sig == signature
    assert loaded_data == data

def test_build_signature_consistency():
    folders = ["/tmp/a", "/tmp/b"]
    with patch("app.settings.get_setting", return_value="*.log"), \
         patch("os.stat") as mock_stat:
        
        mock_stat.return_value.st_mtime_ns = 12345
        mock_stat.return_value.st_size = 100
        
        sig1 = build_signature(folders)
        sig2 = build_signature(folders)
        assert sig1 == sig2
        
    with patch("app.settings.get_setting", return_value="*.txt"), \
         patch("os.stat") as mock_stat:
        mock_stat.return_value.st_mtime_ns = 12345
        mock_stat.return_value.st_size = 100
        
        sig3 = build_signature(folders)
        assert sig3 != sig1 # Changed settings should change sig

def test_load_nonexistent_snapshot(mock_pdm):
    assert load_cached_snapshot() is None
