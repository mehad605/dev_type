"""Tests for typing engine logic."""
import time
from app.typing_engine import TypingEngine, TypingState


def test_typing_state():
    """Test TypingState dataclass."""
    state = TypingState(content="hello world")
    assert state.cursor_position == 0
    assert state.total_keystrokes() == 0
    assert state.accuracy() == 1.0
    assert state.wpm() == 0.0
    assert not state.is_complete()
    
    state.cursor_position = 11
    assert state.is_complete()


def test_typing_engine_initialization():
    """Test engine initialization."""
    engine = TypingEngine("test content")
    assert engine.state.content == "test content"
    assert engine.state.is_paused
    assert engine.state.cursor_position == 0


def test_correct_keystroke():
    """Test processing correct keystroke."""
    engine = TypingEngine("hello")
    is_correct, expected = engine.process_keystroke("h")
    
    assert is_correct is True
    assert expected == "h"
    assert engine.state.cursor_position == 1
    assert engine.state.correct_keystrokes == 1
    assert engine.state.incorrect_keystrokes == 0
    assert not engine.state.is_paused  # Auto-starts on first keystroke


def test_incorrect_keystroke():
    """Test processing incorrect keystroke."""
    engine = TypingEngine("hello")
    is_correct, expected = engine.process_keystroke("x")
    
    assert is_correct is False
    assert expected == "h"
    assert engine.state.cursor_position == 0  # Doesn't advance
    assert engine.state.correct_keystrokes == 0
    assert engine.state.incorrect_keystrokes == 1


def test_backspace():
    """Test backspace functionality."""
    engine = TypingEngine("hello")
    engine.process_keystroke("h")
    engine.process_keystroke("e")
    assert engine.state.cursor_position == 2
    
    engine.process_backspace()
    assert engine.state.cursor_position == 1
    
    engine.process_backspace()
    assert engine.state.cursor_position == 0
    
    # Can't go below 0
    engine.process_backspace()
    assert engine.state.cursor_position == 0


def test_ctrl_backspace():
    """Test Ctrl+Backspace (delete word) functionality."""
    engine = TypingEngine("hello world")
    
    # Type "hello "
    for char in "hello ":
        engine.process_keystroke(char)
    
    assert engine.state.cursor_position == 6
    
    # Ctrl+Backspace should delete " " and "hello"
    engine.process_ctrl_backspace()
    assert engine.state.cursor_position == 0


def test_accuracy_calculation():
    """Test accuracy calculation."""
    engine = TypingEngine("abc")
    
    engine.process_keystroke("a")  # Correct
    engine.process_keystroke("x")  # Incorrect
    engine.process_keystroke("b")  # Correct
    
    # 2 correct out of 3 total = 66.67%
    assert engine.state.total_keystrokes() == 3
    assert abs(engine.state.accuracy() - 0.6667) < 0.01


def test_wpm_calculation():
    """Test WPM calculation."""
    engine = TypingEngine("hello world")
    engine.state.start_time = time.time() - 60  # Started 1 minute ago
    engine.state.is_paused = False
    
    # Type 5 characters
    for char in "hello":
        engine.process_keystroke(char)
    
    engine.update_elapsed_time()
    
    # WPM = (5 chars / 5) / 1 minute = 1 WPM
    wpm = engine.state.wpm()
    assert 0.8 < wpm < 1.2  # Allow some timing variance


def test_pause_and_resume():
    """Test pausing and resuming session."""
    engine = TypingEngine("test")
    assert engine.state.is_paused
    
    engine.start()
    assert not engine.state.is_paused
    
    engine.pause()
    assert engine.state.is_paused


def test_reset():
    """Test resetting session."""
    engine = TypingEngine("hello")
    engine.process_keystroke("h")
    engine.process_keystroke("e")
    
    assert engine.state.cursor_position == 2
    assert engine.state.correct_keystrokes == 2
    
    engine.reset()
    
    assert engine.state.cursor_position == 0
    assert engine.state.correct_keystrokes == 0
    assert engine.state.is_paused


def test_load_progress():
    """Test loading saved progress."""
    engine = TypingEngine("hello world")
    engine.load_progress(cursor_pos=5, correct=5, incorrect=1, elapsed=10.5)
    
    assert engine.state.cursor_position == 5
    assert engine.state.correct_keystrokes == 5
    assert engine.state.incorrect_keystrokes == 1
    assert engine.state.elapsed_time == 10.5
    assert engine.state.is_paused
