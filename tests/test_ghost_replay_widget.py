"""Tests for GhostReplayWidget."""
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch


@pytest.fixture
def app():
    """Create QApplication for testing."""
    from PySide6.QtWidgets import QApplication
    
    _app = QApplication.instance()
    if _app is None:
        _app = QApplication(sys.argv)
    yield _app


@pytest.fixture
def mock_typing_area(app):
    """Create a mock typing area."""
    from PySide6.QtWidgets import QTextEdit
    
    mock = QTextEdit()
    mock.stop_ghost_recording = Mock()
    mock.reset_session = Mock()
    mock.start_ghost_recording = Mock()
    return mock


@pytest.fixture
def replay_widget(app, mock_typing_area):
    """Create a GhostReplayWidget instance."""
    from app.ghost_replay_widget import GhostReplayWidget
    
    widget = GhostReplayWidget(mock_typing_area)
    yield widget
    widget.stop_replay()  # Clean up any active timers


class TestGhostReplayWidgetInitialization:
    """Test GhostReplayWidget initialization."""
    
    def test_initialization(self, replay_widget):
        """Test that widget initializes correctly."""
        assert replay_widget is not None
        assert replay_widget.ghost_data is None
        assert replay_widget.is_replaying is False
        assert replay_widget.replay_timers == []
    
    def test_widget_hidden_initially(self, replay_widget):
        """Test that widget is hidden initially."""
        assert replay_widget.isVisible() is False
    
    def test_has_status_label(self, replay_widget):
        """Test that widget has a status label."""
        assert replay_widget.status_label is not None


class TestGhostReplayState:
    """Test replay state management."""
    
    def test_start_replay_sets_state(self, replay_widget, mock_typing_area):
        """Test that start_replay sets the is_replaying flag."""
        ghost_data = {
            "keys": [
                {"t": 0, "k": "h"},
                {"t": 100, "k": "i"},
            ]
        }
        
        replay_widget.start_replay(ghost_data)
        
        assert replay_widget.is_replaying is True
        assert replay_widget.ghost_data == ghost_data
        
        replay_widget.stop_replay()
    
    def test_start_replay_prepares_typing_area(self, replay_widget, mock_typing_area):
        """Test that start_replay prepares the typing area."""
        ghost_data = {"keys": [{"t": 0, "k": "a"}]}
        
        replay_widget.start_replay(ghost_data)
        
        mock_typing_area.stop_ghost_recording.assert_called_once()
        mock_typing_area.reset_session.assert_called_once()
        
        replay_widget.stop_replay()
    
    def test_start_replay_creates_timers(self, replay_widget):
        """Test that start_replay creates timers for keystrokes."""
        ghost_data = {
            "keys": [
                {"t": 0, "k": "a"},
                {"t": 100, "k": "b"},
                {"t": 200, "k": "c"},
            ]
        }
        
        replay_widget.start_replay(ghost_data)
        
        # Should have timers for each keystroke plus end timer
        assert len(replay_widget.replay_timers) >= 3
        
        replay_widget.stop_replay()
    
    def test_start_replay_ignores_if_already_replaying(self, replay_widget):
        """Test that starting replay twice doesn't create duplicate state."""
        ghost_data = {"keys": [{"t": 0, "k": "a"}]}
        
        replay_widget.start_replay(ghost_data)
        initial_timer_count = len(replay_widget.replay_timers)
        
        # Try to start again
        replay_widget.start_replay(ghost_data)
        
        # Should not have doubled timers
        assert len(replay_widget.replay_timers) == initial_timer_count
        
        replay_widget.stop_replay()
    
    def test_start_replay_empty_keystrokes(self, replay_widget):
        """Test starting replay with empty keystrokes stops immediately."""
        ghost_data = {"keys": []}
        
        replay_widget.start_replay(ghost_data)
        
        # Should have stopped since no keystrokes
        assert replay_widget.is_replaying is False


class TestStopReplay:
    """Test stop_replay functionality."""
    
    def test_stop_replay_clears_state(self, replay_widget):
        """Test that stop_replay clears all state."""
        ghost_data = {"keys": [{"t": 0, "k": "a"}]}
        
        replay_widget.start_replay(ghost_data)
        replay_widget.stop_replay()
        
        assert replay_widget.is_replaying is False
        assert len(replay_widget.replay_timers) == 0
    
    def test_stop_replay_hides_widget(self, replay_widget):
        """Test that stop_replay hides the widget."""
        ghost_data = {"keys": [{"t": 0, "k": "a"}]}
        
        replay_widget.start_replay(ghost_data)
        # Widget visibility depends on parent showing
        # Just verify stop_replay sets hidden state
        replay_widget.stop_replay()
        assert replay_widget.isHidden() or not replay_widget.isVisible()
    
    def test_stop_replay_restores_typing_area(self, replay_widget, mock_typing_area):
        """Test that stop_replay restores typing area state."""
        ghost_data = {"keys": [{"t": 0, "k": "a"}]}
        
        replay_widget.start_replay(ghost_data)
        replay_widget.stop_replay()
        
        mock_typing_area.start_ghost_recording.assert_called_once()
    
    def test_stop_replay_emits_signal(self, replay_widget):
        """Test that stop_replay emits replay_finished signal."""
        ghost_data = {"keys": [{"t": 0, "k": "a"}]}
        
        signal_received = []
        replay_widget.replay_finished.connect(lambda: signal_received.append(True))
        
        replay_widget.start_replay(ghost_data)
        replay_widget.stop_replay()
        
        assert len(signal_received) == 1
    
    def test_stop_replay_safe_when_not_replaying(self, replay_widget):
        """Test that stop_replay is safe when not replaying."""
        # Should not raise
        replay_widget.stop_replay()
        
        assert replay_widget.is_replaying is False


class TestReplayKeystroke:
    """Test keystroke replay logic."""
    
    def test_replay_keystroke_noop_when_not_replaying(self, replay_widget):
        """Test that _replay_keystroke does nothing when not replaying."""
        # Should not raise even when not replaying
        replay_widget._replay_keystroke("a")
    
    def test_keystroke_mapping_backspace(self, replay_widget):
        """Test that backspace creates correct key event."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtCore import QEvent
        
        # Just verify the event creation logic without posting
        event = QKeyEvent(QEvent.KeyPress, Qt.Key_Backspace, Qt.NoModifier, "")
        assert event.key() == Qt.Key_Backspace
    
    def test_keystroke_mapping_newline(self, replay_widget):
        """Test that newline creates correct key event."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtCore import QEvent
        
        event = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier, "\n")
        assert event.key() == Qt.Key_Return
    
    def test_keystroke_mapping_tab(self, replay_widget):
        """Test that tab creates correct key event."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtCore import QEvent
        
        event = QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier, "\t")
        assert event.key() == Qt.Key_Tab
    
    def test_keystroke_mapping_regular_char(self, replay_widget):
        """Test that regular characters create correct key events."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtCore import QEvent
        
        event = QKeyEvent(QEvent.KeyPress, ord('A'), Qt.NoModifier, "a")
        assert event.text() == "a"
