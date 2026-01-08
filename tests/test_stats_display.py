"""Tests for stats display widgets."""
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication

from app import settings
from app.stats_display import SparklineWidget, StatsBox, KeystrokeBox, InteractiveStatusBox, StatsDisplayWidget


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


# ============== SPARKLINE WIDGET TESTS ==============

def test_sparkline_initialization(app, db_setup):
    """Test SparklineWidget initializes correctly."""
    widget = SparklineWidget()
    
    assert widget.values == []
    assert widget.color_hex == "#88c0d0"


def test_sparkline_add_value(app, db_setup):
    """Test adding values to sparkline."""
    widget = SparklineWidget()
    
    widget.add_value(10.0)
    widget.add_value(20.0)
    widget.add_value(30.0)
    
    assert len(widget.values) == 3
    assert widget.values == [10.0, 20.0, 30.0]


def test_sparkline_max_values(app, db_setup):
    """Test sparkline limits to 50 values."""
    widget = SparklineWidget()
    
    # Add 60 values
    for i in range(60):
        widget.add_value(float(i))
    
    # Should only keep last 50
    assert len(widget.values) == 50
    assert widget.values[0] == 10.0  # First 10 removed
    assert widget.values[-1] == 59.0


def test_sparkline_set_color(app, db_setup):
    """Test setting sparkline color."""
    widget = SparklineWidget()
    
    widget.set_color("#FF0000")
    
    assert widget.color_hex == "#FF0000"


def test_sparkline_custom_initial_color(app, db_setup):
    """Test sparkline with custom initial color."""
    widget = SparklineWidget(color_hex="#00FF00")
    
    assert widget.color_hex == "#00FF00"


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
    """Test setting value with raw value for sparkline."""
    box = StatsBox(title="WPM", value_key="wpm")
    
    box.set_value("50", raw_value=50.0)
    box.set_value("60", raw_value=60.0)
    box.set_value("70", raw_value=70.0)
    
    assert box.value_label.text() == "70"
    assert len(box.sparkline.values) == 3


def test_stats_box_different_types(app, db_setup):
    """Test StatsBox with different value types."""
    wpm_box = StatsBox(title="WPM", value_key="wpm")
    acc_box = StatsBox(title="Accuracy", value_key="accuracy")
    time_box = StatsBox(title="Time", value_key="time")
    other_box = StatsBox(title="Other")
    
    assert wpm_box.value_key == "wpm"
    assert acc_box.value_key == "accuracy"
    assert time_box.value_key == "time"
    assert other_box.value_key is None


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
    
    # Check values are updated (uses correct_count, not correct_label)
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
    # Percentages should still work
    assert box.correct_pct.text() == "0%"


def test_keystroke_box_update_stats_large_numbers(app, db_setup):
    """Test keystroke stats with large numbers."""
    box = KeystrokeBox()
    
    box.update_stats(correct=10000, incorrect=500, total=10500)
    
    assert box.correct_count.text() == "10000"
    assert box.incorrect_count.text() == "500"
    assert box.total_count.text() == "10500"


def test_keystroke_box_percentages(app, db_setup):
    """Test keystroke percentage calculations."""
    box = KeystrokeBox()
    
    box.update_stats(correct=80, incorrect=20, total=100)
    
    assert box.correct_pct.text() == "80%"
    assert box.incorrect_pct.text() == "20%"
    assert box.total_pct.text() == "100%"


# ============== INTERACTIVE STATUS BOX TESTS ==============

def test_status_box_initialization(app, db_setup):
    """Test InteractiveStatusBox initializes correctly."""
    box = InteractiveStatusBox()
    
    assert box is not None


def test_status_box_update_active(app, db_setup):
    """Test InteractiveStatusBox in active state."""
    box = InteractiveStatusBox()
    
    box.update_status(is_paused=False, is_finished=False)
    
    # Check the status_text shows "ACTIVE"
    assert "ACTIVE" in box.status_text.text()


def test_status_box_update_paused(app, db_setup):
    """Test InteractiveStatusBox in paused state."""
    box = InteractiveStatusBox()
    
    box.update_status(is_paused=True, is_finished=False)
    
    assert "PAUSED" in box.status_text.text()


def test_status_box_update_finished(app, db_setup):
    """Test InteractiveStatusBox in finished state."""
    box = InteractiveStatusBox()
    
    box.update_status(is_paused=False, is_finished=True)
    
    assert "FINISHED" in box.status_text.text()


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
    
    stats = {
        "wpm": 65.5,
        "accuracy": 95.0,
        "time": 60.0,
        "correct": 100,
        "incorrect": 5,
        "total": 105
    }
    
    widget.update_stats(stats)
    
    # Values should be updated
    assert "65" in widget.wpm_box.value_label.text()


def test_stats_display_widget_update_stats_empty(app, db_setup):
    """Test updating stats with empty dict."""
    widget = StatsDisplayWidget()
    
    # Should not raise exception
    widget.update_stats({})


def test_stats_display_widget_update_stats_partial(app, db_setup):
    """Test updating stats with partial data."""
    widget = StatsDisplayWidget()
    
    stats = {
        "wpm": 50.0
    }
    
    # Should not raise exception
    widget.update_stats(stats)


def test_stats_display_widget_wpm_history(app, db_setup):
    """Test getting WPM history from widget."""
    widget = StatsDisplayWidget()
    widget.clear_wpm_history()  # Reset
    
    # WPM history is populated via update_stats when time crosses whole seconds
    widget.update_stats({"wpm": 50.0, "time": 1.0, "correct": 10, "incorrect": 0, "total": 10})
    widget.update_stats({"wpm": 60.0, "time": 2.0, "correct": 20, "incorrect": 0, "total": 20})
    widget.update_stats({"wpm": 70.0, "time": 3.0, "correct": 30, "incorrect": 0, "total": 30})
    
    history = widget.get_wpm_history()
    assert len(history) == 3
    # History is list of (second, wpm) tuples
    assert history[0] == (1, 50.0)
    assert history[1] == (2, 60.0)
    assert history[2] == (3, 70.0)


def test_stats_display_widget_clear_history(app, db_setup):
    """Test clearing WPM history."""
    widget = StatsDisplayWidget()
    
    # Add some history via update_stats
    widget.update_stats({"wpm": 50.0, "time": 1.0, "correct": 10, "incorrect": 0, "total": 10})
    widget.update_stats({"wpm": 60.0, "time": 2.0, "correct": 20, "incorrect": 0, "total": 20})
    
    assert len(widget.get_wpm_history()) > 0
    
    widget.clear_wpm_history()
    
    assert len(widget.get_wpm_history()) == 0
