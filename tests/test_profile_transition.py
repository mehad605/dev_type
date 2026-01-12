"""Tests for profile transition overlay and animations."""
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.profile_transition import ProfileTransitionOverlay, LoadingCenterWidget
from unittest.mock import MagicMock, patch

@pytest.fixture(scope="module")
def qapp():
    """Ensure a QApplication is running."""
    yield QApplication.instance() or QApplication([])

def test_transition_overlay_initial_state(qapp):
    """Test that overlay starts hidden and uninitialized."""
    overlay = ProfileTransitionOverlay()
    assert overlay.isHidden()
    assert overlay.target_name == ""
    assert overlay._progress == 0.0

def test_start_transition_state(qapp):
    """Test that starting a transition sets correct initial state."""
    overlay = ProfileTransitionOverlay()
    mock_finished = MagicMock()
    
    # Mock time to have stable start
    with patch('time.time', return_value=100.0):
        overlay.start_transition("Zoof", "path/to/avatar.png", mock_finished)
        
    assert overlay.target_name == "Zoof"
    assert overlay.target_image == "path/to/avatar.png"
    assert overlay._on_finished == mock_finished
    assert not overlay.isHidden()
    assert overlay.timer.isActive()

def test_progress_animation_math(qapp):
    """Test the progress calculation with easing."""
    overlay = ProfileTransitionOverlay()
    overlay.timer.stop() # Control updates manually
    overlay._anim_duration = 1000 # 1 second
    
    # Start at t=100.0 (seconds)
    with patch('time.time', return_value=100.0):
        overlay.start_transition("User", None, None)
        
    # At t=100.5 (50% duration)
    # EaseOutQuad at 0.5: t * (2 - t) = 0.5 * 1.5 = 0.75
    with patch('time.time', return_value=100.5):
        overlay._update_progress()
        assert overlay._progress == 0.75
        assert overlay.center_widget._progress == 0.75

def test_transition_completion(qapp):
    """Test that callback is fired when animation completes."""
    overlay = ProfileTransitionOverlay()
    overlay._anim_duration = 100
    mock_finished = MagicMock()
    
    with patch('time.time', return_value=100.0):
        overlay.start_transition("User", None, mock_finished)
        
    # Advance time past duration
    with patch('time.time', return_value=100.2):
        overlay._update_progress()
        assert overlay._progress == 1.0
        assert not overlay.timer.isActive()
        mock_finished.assert_called_once()

def test_loading_center_widget_theming(qapp):
    """Test that the center widget loads theme colors correctly."""
    widget = LoadingCenterWidget()
    
    # Patch the function as imported in app.profile_transition
    with patch('app.profile_transition.settings.get_setting', return_value="cyberpunk"), \
         patch('app.profile_transition.get_color_scheme') as mock_get_scheme:
        
        # Mock a scheme
        mock_scheme = MagicMock()
        mock_scheme.text_primary = "#FF00FF"
        mock_scheme.accent_color = "#00FFFF"
        mock_get_scheme.return_value = mock_scheme
        
        widget.set_data("Cyberpunker", None)
        
        assert widget._name == "Cyberpunker"
        assert widget.scheme == mock_scheme
        assert "#FF00FF" in widget.name_label.styleSheet()

def test_overlay_interaction_blocking(qapp):
    """Test that overlay blocks mouse events (Layer 3)."""
    overlay = ProfileTransitionOverlay()
    # WA_TransparentForMouseEvents should be False to BLOCK events
    assert overlay.testAttribute(Qt.WA_TransparentForMouseEvents) is False
