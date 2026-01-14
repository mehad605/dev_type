"""Tests for stats display widgets."""
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from unittest.mock import patch, MagicMock

from app import settings
from app.stats_display import StatsBox, KeystrokeBox, InteractiveStatusBox, StatsDisplayWidget


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


# ============== STATS BOX TESTS ==============

def test_stats_box_initialization(app, db_setup):
    """Test StatsBox initializes correctly."""
    box = StatsBox(title="WPM", value_key="wpm")
    
    assert box.value_key == "wpm"
    assert box.title_label.text() == "WPM"
    assert box.value_label.text() == "--"


def test_stats_box_set_value_string(app, db_setup):
    """Test setting value as string."""
    box = StatsBox(title="WPM", value_key="wpm")
    
    box.set_value("65.5")
    
    assert box.value_label.text() == "65.5"


def test_stats_box_set_value_with_raw(app, db_setup):
    """Test setting value with raw value (checking it doesn't crash)."""
    box = StatsBox(title="WPM", value_key="wpm")
    
    box.set_value("50", raw_value=50.0)
    assert box.value_label.text() == "50"


# ============== KEYSTROKE BOX TESTS ==============

def test_keystroke_box_initialization(app, db_setup):
    """Test KeystrokeBox initializes correctly."""
    box = KeystrokeBox()
    
    # Just verify it initializes without error
    assert box is not None


def test_keystroke_box_update_stats(app, db_setup):
    """Test updating keystroke stats."""
    box = KeystrokeBox()
    
    box.update_stats(correct=100, incorrect=5, total=105)
    
    # Check values are updated
    assert hasattr(box, 'correct_count')
    assert box.correct_count.text() == "100"
    assert box.incorrect_count.text() == "5"
    assert box.total_count.text() == "105"


def test_keystroke_box_update_stats_zero(app, db_setup):
    """Test updating keystroke stats with zeros."""
    box = KeystrokeBox()
    
    box.update_stats(correct=0, incorrect=0, total=0)
    
    assert box.correct_count.text() == "0"
    assert box.incorrect_count.text() == "0"
    assert box.total_count.text() == "0"
    # Percentages should still work or show 0%
    assert "0%" in box.correct_pct.text()


# ============== INTERACTIVE STATUS BOX TESTS ==============

def test_status_box_initialization(app, db_setup):
    """Test InteractiveStatusBox initializes correctly."""
    box = InteractiveStatusBox()
    
    assert box is not None


def test_status_box_update_active(app, db_setup):
    """Test InteractiveStatusBox in active state."""
    box = InteractiveStatusBox()
    
    box.update_status(is_paused=False, is_finished=False)
    
    assert box.status_text.text() != ""


def test_status_box_update_paused(app, db_setup):
    """Test InteractiveStatusBox in paused state."""
    box = InteractiveStatusBox()
    
    box.update_status(is_paused=True, is_finished=False)
    assert box.status_text.text() != ""

def test_status_box_update_finished(app, db_setup):
    """Test InteractiveStatusBox in finished state."""
    box = InteractiveStatusBox()
    
    box.update_status(is_paused=False, is_finished=True)
    assert "FINISHED" in box.status_text.text() or box.status_text.text() != ""


def test_status_box_mouse_press(app, db_setup):
    """Test clicking the status box."""
    box = InteractiveStatusBox()
    clicked = False
    def on_click(): nonlocal clicked; clicked = True
    box.pause_clicked.connect(on_click)
    
    # Mock left mouse event
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import QPoint
    event = QMouseEvent(QMouseEvent.MouseButtonPress, QPoint(10, 10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    box.mousePressEvent(event)
    assert clicked is True

    # Mock right mouse event for coverage of else branch
    event_right = QMouseEvent(QMouseEvent.MouseButtonPress, QPoint(10, 10), Qt.RightButton, Qt.RightButton, Qt.NoModifier)
    box.mousePressEvent(event_right)


# ============== STATS DISPLAY WIDGET TESTS ==============

def test_stats_display_widget_initialization(app, db_setup):
    """Test StatsDisplayWidget initializes correctly."""
    widget = StatsDisplayWidget()
    
    assert widget is not None
    # Verify main components exist
    assert hasattr(widget, 'wpm_box')
    assert hasattr(widget, 'accuracy_box')
    assert hasattr(widget, 'time_box')


def test_stats_display_widget_update_stats(app, db_setup):
    """Test updating stats in display widget."""
    widget = StatsDisplayWidget()
    
    # Test accuracy=0 case
    widget.update_stats({"total": 0})
    assert "0.0%" in widget.accuracy_box.value_label.text()

    # Test stat coloring else case
    other_box = StatsBox("Other", value_key="unknown")
    other_box.apply_theme()

    stats = {
        "wpm": 65.5,
        "accuracy": 0.95,
        "time": 60.0,
        "correct": 100,
        "incorrect": 5,
        "total": 105,
        "is_finished": False,
        "is_paused": False
    }
    
    widget.update_stats(stats)
    
    # Values should be updated
    assert "65.5" in widget.wpm_box.value_label.text()


def test_stats_display_widget_history_management(app, db_setup):
    """Test history recording, getting, and clearing."""
    widget = StatsDisplayWidget()
    widget.clear_wpm_history()
    
    # Update stats to record history
    widget.update_stats({"wpm": 50.0, "time": 1.0, "incorrect": 1})
    widget.update_stats({"wpm": 60.0, "time": 2.0, "incorrect": 3})
    
    assert len(widget.get_wpm_history()) == 2
    assert len(widget.get_error_history()) == 2
    
    # Test get_history (returns tuple of lists)
    wpm_hist, err_hist = widget.get_history()
    assert len(wpm_hist) == 2
    assert len(err_hist) == 2
    
    # Test clear
    widget.clear_wpm_history()
    assert len(widget.get_wpm_history()) == 0
    assert len(widget.get_error_history()) == 0


def test_stats_display_widget_load_history(app, db_setup):
    """Test loading history from a file/database."""
    widget = StatsDisplayWidget()
    
    wpm_hist = [(1, 50.0), (2, 55.0)]
    err_hist = [(1, 1), (2, 0)]
    
    widget.load_history(wpm_hist, err_hist, initial_incorrect=5)
    
    assert widget.get_wpm_history() == wpm_hist
    assert widget.get_error_history() == err_hist
    assert widget._last_recorded_incorrect == 5


def test_stats_display_widget_on_status_action(app, db_setup):
    """Test the status action handler."""
    widget = StatsDisplayWidget()
    
    # Test pause request
    widget.is_finished = False
    mock_pause = MagicMock()
    widget.pause_requested.connect(mock_pause)
    widget.on_status_action()
    mock_pause.assert_called_once()
        
    # Test reset request
    widget.is_finished = True
    mock_reset = MagicMock()
    widget.reset_requested.connect(mock_reset)
    widget.on_status_action()
    mock_reset.assert_called_once()


def test_stats_display_widget_horizontal_init(app, db_setup):
    """Test initialization with horizontal settings."""
    with patch('app.settings.get_setting', return_value="top"):
        widget = StatsDisplayWidget()
        # Should hit the else branch on line 402
        assert widget is not None

def test_stats_display_widget_orientation(app, db_setup):
    """Test changing orientation."""
    widget = StatsDisplayWidget()
    widget.set_orientation("horizontal")
    widget.set_orientation("vertical")
    # Should not crash
