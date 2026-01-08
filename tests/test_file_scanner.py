"""Tests for file scanner module."""
import pytest
import tempfile
from pathlib import Path
from app.file_scanner import (
    scan_folders, 
    get_language_for_file, 
    LANGUAGE_MAP,
    validate_file_path,
    MAX_SCAN_DEPTH,
)


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


def test_validate_file_path_valid(tmp_path):
    """Test file path validation with valid path."""
    test_file = tmp_path / "test.py"
    test_file.write_text("print('test')")
    
    is_valid, error = validate_file_path(str(test_file), str(tmp_path))
    assert is_valid is True
    assert error is None


def test_validate_file_path_nonexistent(tmp_path):
    """Test file path validation with nonexistent file."""
    is_valid, error = validate_file_path(str(tmp_path / "nonexistent.py"))
    assert is_valid is False
    assert "exist" in error.lower()


def test_validate_file_path_outside_root(tmp_path):
    """Test file path validation rejects paths outside root."""
    # Create a file outside tmp_path
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
        f.write("# outside")
        outside_file = f.name
    
    try:
        is_valid, error = validate_file_path(outside_file, str(tmp_path))
        assert is_valid is False
        assert "outside" in error.lower()
    finally:
        Path(outside_file).unlink()


def test_validate_file_path_directory(tmp_path):
    """Test file path validation rejects directories."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    
    is_valid, error = validate_file_path(str(subdir))
    assert is_valid is False
    assert "not a file" in error.lower()


def test_symlink_files_skipped(tmp_path):
    """Test that symlinked files are skipped."""
    # Create a real file
    real_file = tmp_path / "real.py"
    real_file.write_text("# real")
    
    # Create a symlink to it
    try:
        link = tmp_path / "link.py"
        link.symlink_to(real_file)
    except OSError:
        pytest.skip("Symlinks not supported on this platform")
    
    result = scan_folders([str(tmp_path)])
    
    # Should only find the real file, not the symlink
    assert "Python" in result
    assert len(result["Python"]) == 1
    assert "real.py" in result["Python"][0]


def test_symlink_directories_skipped(tmp_path):
    """Test that symlinked directories are not followed."""
    # Create a subdirectory with a file
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "file.py").write_text("# in subdir")
    
    # Create a symlink to the subdirectory
    try:
        link = tmp_path / "link_dir"
        link.symlink_to(subdir)
    except OSError:
        pytest.skip("Symlinks not supported on this platform")
    
    result = scan_folders([str(tmp_path)])
    
    # Should only find file once (via real path, not via symlink)
    assert "Python" in result
    assert len(result["Python"]) == 1


def test_max_depth_enforced(tmp_path):
    """Test that max scan depth is enforced."""
    # Create nested structure up to MAX_SCAN_DEPTH + a few more
    current = tmp_path
    for i in range(min(MAX_SCAN_DEPTH + 5, 60)):  # Cap at 60 for test speed
        current = current / f"d{i}"
        current.mkdir()
    
    # Add file at deepest level
    (current / "deep.py").write_text("# deep")
    
    # Scan should not hang and should complete
    result = scan_folders([str(tmp_path)])
    
    # The file beyond max depth should not be found
    if "Python" in result:
        for path in result["Python"]:
            parts = Path(path).relative_to(tmp_path).parts
            assert len(parts) <= MAX_SCAN_DEPTH + 1  # +1 for file itself
