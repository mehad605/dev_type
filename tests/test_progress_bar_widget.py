"""Tests for progress bar widget."""
import pytest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication

from app import settings
from app.progress_bar_widget import ProgressBarWidget


@pytest.fixture(scope="module")
def app():
    """Create QApplication instance for Qt widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def db_setup(tmp_path: Path):
    """Set up test database."""
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    yield


def test_progress_bar_initialization(app, db_setup):
    """Test progress bar initializes with default values."""
    bar = ProgressBarWidget()
    
    assert bar.progress == 0.0
    assert bar.ghost_progress == 0.0
    assert bar.total_chars == 0
    assert bar.current_pos == 0
    assert bar.ghost_pos == 0
    assert bar.display_ghost is False
    assert bar.bar_type == "user"


def test_progress_bar_ghost_type(app, db_setup):
    """Test ghost bar type initialization."""
    bar = ProgressBarWidget(bar_type="ghost")
    assert bar.bar_type == "ghost"


def test_set_progress_basic(app, db_setup):
    """Test setting basic progress."""
    bar = ProgressBarWidget()
    
    bar.set_progress(current_pos=50, total_chars=100)
    
    assert bar.progress == 0.5
    assert bar.current_pos == 50
    assert bar.total_chars == 100


def test_set_progress_zero_total(app, db_setup):
    """Test setting progress with zero total characters (edge case)."""
    bar = ProgressBarWidget()
    
    # This should not raise an exception (no division by zero)
    bar.set_progress(current_pos=50, total_chars=0)
    
    assert bar.progress == 0.0
    assert bar.total_chars == 0


def test_set_progress_negative_values(app, db_setup):
    """Test setting progress with negative values (edge case)."""
    bar = ProgressBarWidget()
    
    bar.set_progress(current_pos=-10, total_chars=-5)
    
    # Negative values should be clamped to 0
    assert bar.current_pos == 0
    assert bar.total_chars == 0
    assert bar.progress == 0.0


def test_set_progress_exceeds_total(app, db_setup):
    """Test setting progress that exceeds total."""
    bar = ProgressBarWidget()
    
    bar.set_progress(current_pos=150, total_chars=100)
    
    # Progress should be clamped to 1.0
    assert bar.progress == 1.0
    assert bar.current_pos == 150  # Current pos is kept as-is


def test_set_progress_with_ghost(app, db_setup):
    """Test setting progress with ghost position."""
    bar = ProgressBarWidget()
    
    bar.set_progress(current_pos=50, total_chars=100, ghost_pos=75)
    
    assert bar.progress == 0.5
    assert bar.ghost_progress == 0.75
    assert bar.display_ghost is True
    assert bar.ghost_pos == 75


def test_set_progress_ghost_exceeds_total(app, db_setup):
    """Test ghost position clamped to total."""
    bar = ProgressBarWidget()
    
    bar.set_progress(current_pos=50, total_chars=100, ghost_pos=150)
    
    # Ghost should be clamped to total
    assert bar.ghost_pos == 100
    assert bar.ghost_progress == 1.0


def test_show_ghost_progress_toggle(app, db_setup):
    """Test toggling ghost progress visibility."""
    bar = ProgressBarWidget()
    
    # Set up with ghost
    bar.set_progress(current_pos=50, total_chars=100, ghost_pos=75)
    assert bar.display_ghost is True
    
    # Disable ghost
    bar.show_ghost_progress(False)
    assert bar.display_ghost is False
    assert bar.ghost_pos == 0
    assert bar.ghost_progress == 0.0
    
    # Re-enable ghost
    bar.show_ghost_progress(True)
    assert bar.display_ghost is True


def test_reset(app, db_setup):
    """Test resetting progress bar."""
    bar = ProgressBarWidget()
    
    # Set up progress
    bar.set_progress(current_pos=50, total_chars=100, ghost_pos=75)
    assert bar.progress == 0.5
    
    # Reset
    bar.reset()
    
    assert bar.progress == 0.0
    assert bar.ghost_progress == 0.0
    assert bar.current_pos == 0
    assert bar.ghost_pos == 0
    assert bar.total_chars == 0
    assert bar.display_ghost is False


def test_get_progress_text_user_only(app, db_setup):
    """Test progress text without ghost."""
    bar = ProgressBarWidget()
    bar.set_progress(current_pos=75, total_chars=100)
    
    text = bar.get_progress_text()
    assert text == "75%"


def test_get_progress_text_with_ghost(app, db_setup):
    """Test progress text with ghost."""
    bar = ProgressBarWidget()
    bar.set_progress(current_pos=50, total_chars=100, ghost_pos=75)
    
    text = bar.get_progress_text()
    assert text == "You 50% | Ghost 75%"


def test_get_progress_text_zero(app, db_setup):
    """Test progress text at zero."""
    bar = ProgressBarWidget()
    
    text = bar.get_progress_text()
    assert text == "0%"


def test_get_progress_text_100_percent(app, db_setup):
    """Test progress text at 100%."""
    bar = ProgressBarWidget()
    bar.set_progress(current_pos=100, total_chars=100)
    
    text = bar.get_progress_text()
    assert text == "100%"


def test_progress_update_maintains_ghost_when_not_provided(app, db_setup):
    """Test that ghost progress is maintained when not provided in update."""
    bar = ProgressBarWidget()
    
    # Initial setup with ghost
    bar.set_progress(current_pos=25, total_chars=100, ghost_pos=50)
    assert bar.ghost_progress == 0.5
    assert bar.display_ghost is True
    
    # Update user position without specifying ghost
    bar.set_progress(current_pos=50, total_chars=100)
    
    # Ghost should still be displayed (display_ghost was True)
    assert bar.display_ghost is True
    # Ghost progress maintained
    assert bar.ghost_pos == 50


def test_progress_with_small_total(app, db_setup):
    """Test progress with very small total characters."""
    bar = ProgressBarWidget()
    
    bar.set_progress(current_pos=1, total_chars=2)
    assert bar.progress == 0.5
    
    bar.set_progress(current_pos=1, total_chars=1)
    assert bar.progress == 1.0


def test_multiple_progress_updates(app, db_setup):
    """Test multiple sequential progress updates."""
    bar = ProgressBarWidget()
    
    for i in range(0, 101, 10):
        bar.set_progress(current_pos=i, total_chars=100)
        assert bar.progress == i / 100
        assert bar.current_pos == i
