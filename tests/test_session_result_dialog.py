"""Tests for session result dialog components."""
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication

from app import settings
from app.session_result_dialog import InteractiveWPMGraph, SessionResultDialog


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


def test_graph_initialization_basic(app, db_setup):
    """Test graph initializes with basic data."""
    times = [1.0, 2.0, 3.0]
    wpms = [50.0, 55.0, 60.0]
    
    graph = InteractiveWPMGraph(
        times=times,
        wpms=wpms,
        total_time=3.0,
        line_color="#4CAF50",
        theme_colors={}
    )
    
    assert graph.total_time == 3
    assert graph.x_min == 1
    assert graph.x_max == 3
    assert len(graph.second_markers) == 3


def test_graph_initialization_empty_data(app, db_setup):
    """Test graph handles empty data gracefully."""
    graph = InteractiveWPMGraph(
        times=[],
        wpms=[],
        total_time=0.0,
        line_color="#4CAF50",
        theme_colors={}
    )
    
    assert graph.total_time == 1  # Minimum 1 second
    assert graph.x_min == 1
    assert len(graph.second_markers) == 0


def test_graph_initialization_sub_second_times(app, db_setup):
    """Test graph handles sub-1-second times correctly (should be filtered)."""
    times = [0.5, 0.8, 1.0, 2.0]
    wpms = [30.0, 40.0, 50.0, 60.0]
    
    graph = InteractiveWPMGraph(
        times=times,
        wpms=wpms,
        total_time=2.0,
        line_color="#4CAF50",
        theme_colors={}
    )
    
    # Sub-1-second markers should be filtered out
    assert len(graph.second_markers) == 2  # Only 1.0 and 2.0


def test_graph_wpm_axis_scaling_low(app, db_setup):
    """Test WPM axis scaling for low values."""
    times = [1.0, 2.0]
    wpms = [20.0, 30.0]
    
    graph = InteractiveWPMGraph(
        times=times,
        wpms=wpms,
        total_time=2.0,
        line_color="#4CAF50",
        theme_colors={}
    )
    
    # For max WPM 30, y_max should be rounded up to 40
    assert graph.y_max >= 30
    assert graph.y_max <= 50


def test_graph_wpm_axis_scaling_high(app, db_setup):
    """Test WPM axis scaling for high values."""
    times = [1.0, 2.0]
    wpms = [150.0, 180.0]
    
    graph = InteractiveWPMGraph(
        times=times,
        wpms=wpms,
        total_time=2.0,
        line_color="#4CAF50",
        theme_colors={}
    )
    
    # For max WPM 180, y_max should be rounded up appropriately
    assert graph.y_max >= 180
    assert graph.y_max <= 250


def test_graph_with_ghost_data(app, db_setup):
    """Test graph with ghost WPM history."""
    times = [1.0, 2.0]
    wpms = [50.0, 60.0]
    ghost_wpm_history = [(1, 55.0), (2, 65.0)]
    
    graph = InteractiveWPMGraph(
        times=times,
        wpms=wpms,
        total_time=2.0,
        line_color="#4CAF50",
        theme_colors={},
        is_race=True,
        ghost_wpm_history=ghost_wpm_history
    )
    
    assert graph.is_race is True
    assert len(graph.ghost_second_markers) == 2
    # Y max should consider ghost WPM too
    assert graph.y_max >= 65


def test_graph_with_error_history(app, db_setup):
    """Test graph with error history."""
    times = [1.0, 2.0, 3.0]
    wpms = [50.0, 55.0, 60.0]
    error_history = [(1, 2), (2, 0), (3, 1)]
    
    graph = InteractiveWPMGraph(
        times=times,
        wpms=wpms,
        total_time=3.0,
        line_color="#4CAF50",
        theme_colors={},
        error_history=error_history
    )
    
    assert len(graph.error_history) == 3
    assert graph.error_max >= 2  # At least covers max errors


def test_graph_zero_errors(app, db_setup):
    """Test graph with no errors."""
    times = [1.0, 2.0]
    wpms = [50.0, 60.0]
    
    graph = InteractiveWPMGraph(
        times=times,
        wpms=wpms,
        total_time=2.0,
        line_color="#4CAF50",
        theme_colors={},
        error_history=[]
    )
    
    # Should still have a default error axis
    assert graph.error_max == 5  # Default when no errors


def test_graph_visibility_toggles(app, db_setup):
    """Test visibility toggle initialization."""
    times = [1.0, 2.0]
    wpms = [50.0, 60.0]
    
    graph = InteractiveWPMGraph(
        times=times,
        wpms=wpms,
        total_time=2.0,
        line_color="#4CAF50",
        theme_colors={},
        is_race=True
    )
    
    # All should be visible by default
    assert graph.user_visible is True
    assert graph.user_wpm_visible is True
    assert graph.user_errors_visible is True
    assert graph.ghost_visible is True
    assert graph.ghost_wpm_visible is True
    assert graph.ghost_errors_visible is True


def test_graph_time_step_calculation_short(app, db_setup):
    """Test time step calculation for short sessions."""
    times = [1.0, 2.0, 3.0, 4.0, 5.0]
    wpms = [50.0] * 5
    
    graph = InteractiveWPMGraph(
        times=times,
        wpms=wpms,
        total_time=5.0,
        line_color="#4CAF50",
        theme_colors={}
    )
    
    # For short sessions, x_step should be 1 or 2
    assert graph.x_step >= 1
    assert graph.x_step <= 5


def test_graph_time_step_calculation_long(app, db_setup):
    """Test time step calculation for long sessions."""
    times = [float(i) for i in range(1, 121)]  # 120 seconds
    wpms = [50.0] * 120
    
    graph = InteractiveWPMGraph(
        times=times,
        wpms=wpms,
        total_time=120.0,
        line_color="#4CAF50",
        theme_colors={}
    )
    
    # For 2-minute session, step should be larger
    assert graph.x_step >= 10


def test_graph_coordinate_conversions(app, db_setup):
    """Test coordinate conversion functions."""
    times = [1.0, 5.0, 10.0]
    wpms = [0.0, 50.0, 100.0]
    
    graph = InteractiveWPMGraph(
        times=times,
        wpms=wpms,
        total_time=10.0,
        line_color="#4CAF50",
        theme_colors={}
    )
    
    # _time_to_x should return increasing values for increasing times
    x1 = graph._time_to_x(1)
    x5 = graph._time_to_x(5)
    x10 = graph._time_to_x(10)
    assert x1 < x5 < x10
    
    # _wpm_to_y should return decreasing values for increasing WPM (Y is inverted)
    y0 = graph._wpm_to_y(0)
    y50 = graph._wpm_to_y(50)
    y100 = graph._wpm_to_y(100)
    assert y0 > y50 > y100  # Y axis is inverted (0 at top)


def test_graph_error_coordinate_conversion(app, db_setup):
    """Test error count to Y coordinate conversion."""
    times = [1.0, 2.0]
    wpms = [50.0, 60.0]
    error_history = [(1, 5), (2, 10)]
    
    graph = InteractiveWPMGraph(
        times=times,
        wpms=wpms,
        total_time=2.0,
        line_color="#4CAF50",
        theme_colors={},
        error_history=error_history
    )
    
    # _error_to_y should return decreasing values for increasing errors
    y0 = graph._error_to_y(0)
    y5 = graph._error_to_y(5)
    assert y0 > y5  # More errors = higher on graph (lower Y coordinate)


# ============== SESSION RESULT DIALOG TESTS ==============

def test_session_result_dialog_initialization(app, db_setup):
    """Test SessionResultDialog initializes correctly."""
    stats = {
        "wpm": 65.5,
        "accuracy": 0.95,
        "correct": 100,
        "incorrect": 5,
        "time": 60.0,
        "total_chars": 105
    }
    
    dialog = SessionResultDialog(stats=stats)
    
    assert dialog.stats == stats
    assert dialog.is_race is False


def test_session_result_dialog_race_mode(app, db_setup):
    """Test SessionResultDialog in race mode."""
    stats = {
        "wpm": 65.5,
        "accuracy": 0.95,
        "correct": 100,
        "incorrect": 5,
        "time": 60.0,
        "total_chars": 105
    }
    race_info = {
        "wpm": 60.0,
        "accuracy": 0.92,
        "correct": 95,
        "incorrect": 8,
        "time": 62.0
    }
    
    dialog = SessionResultDialog(
        stats=stats,
        is_race=True,
        race_info=race_info
    )
    
    assert dialog.is_race is True
    assert dialog.race_info == race_info


def test_session_result_dialog_with_wpm_history(app, db_setup):
    """Test SessionResultDialog with WPM history for graph."""
    stats = {
        "wpm": 100.0,
        "accuracy": 0.98,
        "correct": 200,
        "incorrect": 4,
        "time": 120.0,
        "total_chars": 204
    }
    wpm_history = [(1, 50.0), (2, 60.0), (3, 70.0)]
    
    dialog = SessionResultDialog(
        stats=stats,
        wpm_history=wpm_history
    )
    
    assert len(dialog.wpm_history) == 3


def test_session_result_dialog_zero_time(app, db_setup):
    """Test SessionResultDialog handles zero time edge case."""
    stats = {
        "wpm": 0.0,
        "accuracy": 0.0,
        "correct": 0,
        "incorrect": 0,
        "time": 0.0,
        "total_chars": 0
    }
    
    # Should not raise exception
    dialog = SessionResultDialog(stats=stats)
    assert dialog is not None
