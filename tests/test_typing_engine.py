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
    is_correct, expected, _ = engine.process_keystroke("h")
    
    assert is_correct is True
    assert expected == "h"
    assert engine.state.cursor_position == 1
    assert engine.state.correct_keystrokes == 1
    assert engine.state.incorrect_keystrokes == 0
    assert not engine.state.is_paused  # Auto-starts on first keystroke


def test_incorrect_keystroke():
    """Test processing incorrect keystroke - cursor doesn't advance."""
    engine = TypingEngine("hello")
    is_correct, expected, _ = engine.process_keystroke("x")
    
    assert is_correct is False
    assert expected == "h"
    assert engine.state.cursor_position == 0  # Doesn't advance on error
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
    
    engine.process_keystroke("a")  # Correct - advances to position 1
    engine.process_keystroke("x")  # Incorrect - doesn't advance
    engine.process_backspace()  # Backspace to clear mistake marker
    engine.process_keystroke("b")  # Correct - advances to position 2
    engine.process_keystroke("c")  # Correct - advances to position 3
    
    # 3 correct out of 4 total (including the incorrect 'x') = 75%
    assert engine.state.total_keystrokes() == 4
    assert abs(engine.state.accuracy() - 0.75) < 0.01


def test_wpm_calculation():
    """Test WPM calculation."""
    engine = TypingEngine("hello world")
    engine.start()  # Start the engine properly
    # Simulate some elapsed time by setting the session start in the past
    engine.state._session_start = time.time() - 60  # Started 1 minute ago
    
    # Type 5 characters
    for char in "hello":
        engine.process_keystroke(char)
    
    # WPM = (5 chars / 5) / 1 minute = 1 WPM
    wpm = engine.get_wpm()
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


def test_continue_on_error_enabled():
    """Test typing with mistake - requires backspace to continue."""
    engine = TypingEngine("hello")
    
    # Type incorrect character
    is_correct, expected, _ = engine.process_keystroke("x")
    
    assert is_correct is False
    assert expected == "h"
    assert engine.state.cursor_position == 0  # Does NOT advance on error
    assert engine.state.incorrect_keystrokes == 1
    assert engine.mistake_at == 0  # Mistake marker set
    
    # Trying to type again should be blocked
    is_correct2, expected2, _ = engine.process_keystroke("e")
    assert engine.state.cursor_position == 0  # Still at position 0
    
    # Must backspace first
    engine.process_backspace()
    assert engine.mistake_at is None  # Mistake marker cleared
    
    # Now can type the correct character
    is_correct3, expected3, _ = engine.process_keystroke("h")
    assert is_correct3 is True
    assert engine.state.cursor_position == 1


def test_continue_on_error_disabled():
    """Test that backspace clears mistake and allows continuing."""
    engine = TypingEngine("hello")
    
    # Type incorrect character
    is_correct, expected, _ = engine.process_keystroke("x")
    
    assert is_correct is False
    assert expected == "h"
    assert engine.state.cursor_position == 0  # Does NOT advance
    assert engine.state.incorrect_keystrokes == 1
    assert engine.mistake_at == 0
    
    # Backspace to clear the mistake
    engine.process_backspace()
    assert engine.mistake_at is None
    
    # Now type correct character
    is_correct2, expected2, _ = engine.process_keystroke("h")
    assert is_correct2 is True
    assert engine.state.cursor_position == 1


def test_allow_continue_mistakes_true():
    """Test allow_continue_mistakes=True mode (lenient)."""
    engine = TypingEngine("hello", allow_continue_mistakes=True)
    
    # Type incorrect character - cursor should advance
    is_correct, expected, _ = engine.process_keystroke("x")
    assert is_correct is False
    assert engine.state.cursor_position == 1  # Advances even on error
    assert engine.mistake_at == 0  # Mistake marked at position 0
    
    # Can continue typing
    is_correct2, expected2, _ = engine.process_keystroke("e")
    assert is_correct2 is True
    assert engine.state.cursor_position == 2


def test_allow_continue_mistakes_false():
    """Test allow_continue_mistakes=False mode (strict)."""
    engine = TypingEngine("hello", allow_continue_mistakes=False)
    
    # Type incorrect character - cursor should NOT advance
    is_correct, expected, _ = engine.process_keystroke("x")
    assert is_correct is False
    assert engine.state.cursor_position == 0  # Does not advance
    assert engine.mistake_at == 0
    
    # Cannot continue - blocked
    is_correct2, expected2, _ = engine.process_keystroke("e")
    assert engine.state.cursor_position == 0  # Still blocked


def test_backspace_in_lenient_mode():
    """Test backspace behavior in lenient mode."""
    engine = TypingEngine("hello", allow_continue_mistakes=True)
    
    # Type wrong
    engine.process_keystroke("x")  # Wrong, advances to 1
    
    assert engine.state.cursor_position == 1
    assert engine.mistake_at == 0
    
    # Backspace should move back AND clear mistake
    engine.process_backspace()
    assert engine.state.cursor_position == 0
    assert engine.mistake_at is None  # Cleared


def test_backspace_in_strict_mode():
    """Test backspace behavior in strict mode."""
    engine = TypingEngine("hello", allow_continue_mistakes=False)
    
    # Type wrong
    engine.process_keystroke("x")  # Wrong, stays at 0
    
    assert engine.state.cursor_position == 0
    assert engine.mistake_at == 0
    
    # Backspace clears mistake marker
    engine.process_backspace()
    assert engine.state.cursor_position == 0  # Still at 0
    assert engine.mistake_at is None  # Cleared


def test_completion_with_mistakes():
    """Test completing text with mistakes in lenient mode."""
    engine = TypingEngine("hi", allow_continue_mistakes=True)
    
    engine.process_keystroke("x")  # Wrong
    engine.process_keystroke("i")  # Right
    
    assert engine.state.is_complete()
    assert engine.state.correct_keystrokes == 1
    assert engine.state.incorrect_keystrokes == 1


def test_auto_pause_inactivity():
    """Test auto-pause after inactivity."""
    engine = TypingEngine("hello", pause_delay=0.1)
    
    # Start typing
    engine.process_keystroke("h")
    assert engine.state.is_paused is False
    
    # Wait for auto-pause
    import time
    time.sleep(0.15)
    
    # Check auto-pause
    paused = engine.check_auto_pause()
    assert paused is True
    assert engine.state.is_paused is True


def test_finished_state():
    """Test that engine marks as finished when complete."""
    engine = TypingEngine("hi")
    
    engine.process_keystroke("h")
    assert engine.state.is_finished is False
    
    engine.process_keystroke("i")
    assert engine.state.is_finished is True
    assert engine.state.is_paused is True  # Auto-pauses on completion


def test_no_input_after_finished():
    """Test that no input is processed after finishing."""
    engine = TypingEngine("hi")
    
    engine.process_keystroke("h")
    engine.process_keystroke("i")
    assert engine.state.is_finished is True
    
    # Try to type more - should be blocked
    is_correct, expected, _ = engine.process_keystroke("x")
    assert is_correct is False
    assert expected == ""


def test_auto_indent():
    """Test auto-indentation feature."""
    content = "def hello():\n    pass"
    engine = TypingEngine(content)
    engine.auto_indent = True
    
    # 1. Type "def hello():"
    for char in "def hello():":
        engine.process_keystroke(char)
        
    assert engine.state.cursor_position == 12
    
    # 2. Type "\n" - should trigger auto-indent of 4 spaces
    is_correct, expected, skipped = engine.process_keystroke("\n")
    
    assert is_correct is True
    assert expected == "\n"
    assert skipped == 4
    # Cursor should be: 12 (newline position) + 1 (past newline) + 4 (skipped spaces) = 17
    assert engine.state.cursor_position == 17
    assert engine.state.content[engine.state.cursor_position] == "p" # Next char
    
    # 3. Wpm calculation is based on manually typed correct characters
    # Typed 12 + 1 = 13 characters manually.
    assert engine.state._get_calculable_chars() == 13
    
    # 4. Backspacing over skipped chars
    engine.process_backspace()
    assert engine.state.cursor_position == 12  # Now removes all auto-skipped chars at once
    assert len(engine.state.skipped_positions) == 0
    
    # 5. Ctrl+Backspace should clear skipped positions in range
    # Reset to state before backspace
    engine.state.cursor_position = 17
    engine.state.skipped_positions.add(16)
    
    engine.process_ctrl_backspace()
    # Should delete the indented part and the newline, or just to the start of the line.
    # Actually process_ctrl_backspace deletes word boundaries.
    # From 17 back: skips 16,15,14,13 (spaces), then 12 (\n).
    assert engine.state.cursor_position < 13
    assert len(engine.state.skipped_positions) == 0


def test_no_point_farming():
    """Test that correctly retyping already-typed chars doesn't give points."""
    engine = TypingEngine("abc")

    # 1. Type "a" correctly
    engine.process_keystroke("a")
    assert engine.state.correct_keystrokes == 1
    assert engine.state.max_correct_position == 0

    # 2. Backspace
    engine.process_backspace()
    assert engine.state.cursor_position == 0

    # 3. Type "a" correctly again - should NOT increment correct_keystrokes
    engine.process_keystroke("a")
    assert engine.state.correct_keystrokes == 1
    assert engine.state.max_correct_position == 0

    # 4. Successively type "b" - should increment
    engine.process_keystroke("b")
    assert engine.state.correct_keystrokes == 2
    assert engine.state.max_correct_position == 1

    # 5. Type incorrectly at a previously correct position
    engine.process_backspace() # back to "b" position
    engine.process_backspace() # back to "a" position
    assert engine.state.cursor_position == 0

    # Type "x" instead of "a" - should count as incorrect
    engine.process_keystroke("x")
    assert engine.state.correct_keystrokes == 2 # still 2 from before
    assert engine.state.incorrect_keystrokes == 1


def test_correct_count_after_backspace_and_retype():
    """Test that correct count updates properly when backspacing mistakes and retyping correctly."""
    engine = TypingEngine("power", allow_continue_mistakes=True)

    # Type "pokkr" - p,o correct; k,k,r wrong but advances in lenient mode
    engine.process_keystroke("p")  # correct, cursor=1, correct=1
    engine.process_keystroke("o")  # correct, cursor=2, correct=2
    engine.process_keystroke("k")  # wrong, cursor=3, correct=2
    engine.process_keystroke("k")  # wrong, cursor=4, correct=2
    engine.process_keystroke("r")  # correct, cursor=5, correct=3

    assert engine.state.correct_keystrokes == 3

    # Backspace 3 times
    engine.process_backspace()  # cursor=4
    engine.process_backspace()  # cursor=3
    engine.process_backspace()  # cursor=2

    # Now type "wer"
    engine.process_keystroke("w")  # correct, cursor=3, correct=4
    engine.process_keystroke("e")  # correct, cursor=4, correct=5
    engine.process_keystroke("r")  # correct, cursor=5, correct=5 (already counted)

    assert engine.state.correct_keystrokes == 5
