"""Tests for file tree widget and random file selection."""
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from app.file_tree import FileTreeWidget, InternalFileTree
from app import settings


@pytest.fixture
def qt_app():
    """Create QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def setup_db(tmp_path):
    """Setup test database."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    yield tmp_path


@pytest.fixture
def file_tree(qt_app, setup_db):
    """Create FileTreeWidget instance."""
    tree = FileTreeWidget()
    yield tree
    tree.deleteLater()


@pytest.fixture
def internal_tree(qt_app, setup_db):
    """Create InternalFileTree instance."""
    tree = InternalFileTree()
    yield tree
    tree.deleteLater()


def test_file_tree_widget_initialization(file_tree):
    """Test that FileTreeWidget initializes correctly."""
    assert file_tree is not None
    assert file_tree.search_bar is not None
    assert file_tree.random_button is not None
    assert file_tree.tree is not None


def test_get_all_file_items_empty(internal_tree):
    """Test getting file items from empty tree."""
    file_items = internal_tree.get_all_file_items()
    assert file_items == []


def test_get_all_file_items_single_folder(internal_tree, tmp_path):
    """Test getting file items from single folder view."""
    # Create test files
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()
    
    (test_dir / "file1.py").write_text("print('test1')")
    (test_dir / "file2.py").write_text("print('test2')")
    (test_dir / "file3.js").write_text("console.log('test')")
    
    # Load folder
    internal_tree.load_folder(str(test_dir))
    
    # Get all file items
    file_items = internal_tree.get_all_file_items()
    
    # Should have 3 files
    assert len(file_items) == 3
    
    # All items should be files
    for item in file_items:
        file_path = item.data(0, 0x0100)  # Qt.UserRole
        assert file_path is not None
        assert Path(file_path).is_file()


def test_get_all_file_items_nested_folders(internal_tree, tmp_path):
    """Test getting file items from nested folder structure."""
    # Create nested structure
    test_dir = tmp_path / "project"
    test_dir.mkdir()
    
    (test_dir / "main.py").write_text("print('main')")
    
    src_dir = test_dir / "src"
    src_dir.mkdir()
    (src_dir / "app.py").write_text("print('app')")
    
    utils_dir = src_dir / "utils"
    utils_dir.mkdir()
    (utils_dir / "helper.py").write_text("print('helper')")
    
    # Load folder
    internal_tree.load_folder(str(test_dir))
    
    # Get all file items (should find files at all levels)
    file_items = internal_tree.get_all_file_items()
    
    # Should have 3 files total
    assert len(file_items) >= 3


def test_get_all_file_items_multiple_folders(internal_tree, tmp_path):
    """Test getting file items from multiple folder view (languages tab scenario)."""
    # Create two separate folders
    folder1 = tmp_path / "folder1"
    folder1.mkdir()
    (folder1 / "file1.py").write_text("print('1')")
    (folder1 / "file2.py").write_text("print('2')")
    
    folder2 = tmp_path / "folder2"
    folder2.mkdir()
    (folder2 / "file3.py").write_text("print('3')")
    
    # Load multiple folders
    internal_tree.load_folders([str(folder1), str(folder2)])
    
    # Get all file items
    file_items = internal_tree.get_all_file_items()
    
    # Should have files from both folders
    assert len(file_items) == 3


def test_open_random_file_empty_tree(internal_tree):
    """Test that opening random file on empty tree doesn't crash."""
    # Should not raise any exception
    internal_tree.open_random_file()


def test_open_random_file_single_file(internal_tree, tmp_path, qt_app):
    """Test opening random file when only one file exists."""
    # Create single file
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    test_file = test_dir / "only.py"
    test_file.write_text("print('only')")
    
    # Load folder
    internal_tree.load_folder(str(test_dir))
    
    # Track signal emission
    emitted_paths = []
    internal_tree.file_selected.connect(lambda path: emitted_paths.append(path))
    
    # Open random (should select the only file)
    internal_tree.open_random_file()
    qt_app.processEvents()
    
    # Should emit the only file's path
    assert len(emitted_paths) == 1
    assert "only.py" in emitted_paths[0]


def test_open_random_file_multiple_files(internal_tree, tmp_path, qt_app):
    """Test opening random file from multiple files."""
    # Create multiple files
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    
    files = ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py"]
    for filename in files:
        (test_dir / filename).write_text(f"print('{filename}')")
    
    # Load folder
    internal_tree.load_folder(str(test_dir))
    
    # Track signal emission
    emitted_paths = []
    internal_tree.file_selected.connect(lambda path: emitted_paths.append(path))
    
    # Open random multiple times to test randomness
    for _ in range(3):
        internal_tree.open_random_file()
        qt_app.processEvents()
    
    # Should emit file paths
    assert len(emitted_paths) == 3
    
    # All emitted paths should be from our files
    for path in emitted_paths:
        assert Path(path).name in files


def test_random_button_click(file_tree, tmp_path, qt_app):
    """Test that clicking random button triggers file selection."""
    # Create test files
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    (test_dir / "test1.py").write_text("print('test1')")
    (test_dir / "test2.py").write_text("print('test2')")
    
    # Load folder
    file_tree.load_folder(str(test_dir))
    
    # Track signal emission
    emitted_paths = []
    file_tree.file_selected.connect(lambda path: emitted_paths.append(path))
    
    # Click random button
    file_tree.random_button.click()
    qt_app.processEvents()
    
    # Should emit a file path
    assert len(emitted_paths) == 1
    assert Path(emitted_paths[0]).exists()


def test_random_clears_search_filter(file_tree, tmp_path, qt_app):
    """Test that random button clears active search filter."""
    # Create test files
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    (test_dir / "test.py").write_text("print('test')")
    
    # Load folder
    file_tree.load_folder(str(test_dir))
    
    # Set search filter
    file_tree.search_bar.setText("something")
    qt_app.processEvents()
    
    assert file_tree.search_bar.text() == "something"
    
    # Click random button
    file_tree.random_button.click()
    qt_app.processEvents()
    
    # Search should be cleared
    assert file_tree.search_bar.text() == ""


def test_ensure_item_visible(internal_tree, tmp_path):
    """Test that _ensure_item_visible expands parent folders."""
    # Create nested structure
    test_dir = tmp_path / "project"
    test_dir.mkdir()
    
    src_dir = test_dir / "src"
    src_dir.mkdir()
    
    nested_dir = src_dir / "nested"
    nested_dir.mkdir()
    
    (nested_dir / "deep.py").write_text("print('deep')")
    
    # Load folder
    internal_tree.load_folder(str(test_dir))
    
    # Find the deeply nested file
    file_items = internal_tree.get_all_file_items()
    assert len(file_items) > 0
    
    deep_item = file_items[0]
    
    # Ensure it's visible (should expand parents)
    internal_tree._ensure_item_visible(deep_item)
    
    # Parent should be expanded
    parent = deep_item.parent()
    while parent:
        assert parent.isExpanded()
        parent = parent.parent()


def test_random_file_language_files_view(internal_tree, tmp_path, qt_app):
    """Test random selection in language files view (multiple folders)."""
    # Create files in different folders (simulating languages tab -> editor)
    folder1 = tmp_path / "project1"
    folder1.mkdir()
    (folder1 / "app1.py").write_text("print('app1')")
    
    folder2 = tmp_path / "project2"
    folder2.mkdir()
    (folder2 / "app2.py").write_text("print('app2')")
    
    # Simulate language files view
    files = [str(folder1 / "app1.py"), str(folder2 / "app2.py")]
    internal_tree.load_language_files("Python", files)
    
    # Track signal emission
    emitted_paths = []
    internal_tree.file_selected.connect(lambda path: emitted_paths.append(path))
    
    # Open random file
    internal_tree.open_random_file()
    qt_app.processEvents()
    
    # Should select one of the files
    assert len(emitted_paths) == 1
    assert emitted_paths[0] in [str(f) for f in files]
