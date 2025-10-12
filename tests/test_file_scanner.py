"""Tests for file scanner module."""
import tempfile
from pathlib import Path
from app.file_scanner import scan_folders, get_language_for_file, LANGUAGE_MAP


def test_language_map_coverage():
    """Test that language map includes common extensions."""
    assert ".py" in LANGUAGE_MAP
    assert LANGUAGE_MAP[".py"] == "Python"
    assert ".js" in LANGUAGE_MAP
    assert ".c" in LANGUAGE_MAP


def test_get_language_for_file():
    """Test language detection from file path."""
    assert get_language_for_file("/path/to/file.py") == "Python"
    assert get_language_for_file("/path/to/file.js") == "JavaScript"
    assert get_language_for_file("/path/to/file.unknown") == "Unknown"


def test_scan_folders_empty():
    """Test scanning empty folder list."""
    result = scan_folders([])
    assert result == {}


def test_scan_folders_with_files(tmp_path: Path):
    """Test scanning folders with various file types."""
    # Create test structure
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()
    
    (test_dir / "main.py").write_text("print('hello')")
    (test_dir / "script.js").write_text("console.log('hello')")
    (test_dir / "README.md").write_text("# Test")
    
    # Scan
    result = scan_folders([str(test_dir)])
    
    # Verify
    assert "Python" in result
    assert len(result["Python"]) == 1
    assert "main.py" in result["Python"][0]
    
    assert "JavaScript" in result
    assert len(result["JavaScript"]) == 1
    
    assert "Markdown" in result


def test_scan_folders_ignores_venv(tmp_path: Path):
    """Test that .venv and other ignored dirs are skipped."""
    test_dir = tmp_path / "project"
    test_dir.mkdir()
    venv_dir = test_dir / ".venv"
    venv_dir.mkdir()
    
    (test_dir / "main.py").write_text("# main")
    (venv_dir / "lib.py").write_text("# should be ignored")
    
    result = scan_folders([str(test_dir)])
    
    assert "Python" in result
    assert len(result["Python"]) == 1
    assert ".venv" not in result["Python"][0]
