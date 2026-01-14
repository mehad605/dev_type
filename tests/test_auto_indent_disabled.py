
from app.typing_engine import TypingEngine

def test_auto_indent_disabled():
    """
    Test checking behavior when auto-indent is explicitly disabled.
    We expect that typing a newline does NOT skip subsequent whitespace.
    The user must manually type the indentation.
    """
    # 0. Setup: Code with indentation
    content = "def foo():\n    pass"
    engine = TypingEngine(content)
    
    # 1. Explicitly disable auto-indent
    engine.auto_indent = False
    
    # 2. Type "def foo():"
    # Length: 10 chars
    for char in "def foo():":
        is_correct, expected, skipped = engine.process_keystroke(char)
        assert is_correct is True
        assert skipped == 0
        
    # Current cursor position should be 10 (0-indexed, so pointing at index 10 which is '\n')
    assert engine.state.cursor_position == 10
    
    # 3. Type Newline "\n"
    # When auto-indent is OFF, this should just advance cursor by 1.
    # It should NOT skip the 4 spaces.
    is_correct, expected, skipped = engine.process_keystroke("\n")
    
    # ASSERTIONS related to display state and expectations
    assert is_correct is True
    assert expected == "\n"
    
    # Crux of the test: No characters should be skipped
    assert skipped == 0, "Auto-indent is OFF, so no characters should be skipped."
    
    # Cursor should be at 11 now (first space)
    # Expected display state: Cursor is at the beginning of the next line, BEFORE the spaces.
    # If auto-indent were ON, cursor would be at 15 (after spaces).
    assert engine.state.cursor_position == 11
    assert engine.state.content[engine.state.cursor_position] == " "
    
    # 4. Verify we can manually type the spaces
    # User types 4 spaces
    for i in range(4):
        is_correct, expected, skipped = engine.process_keystroke(" ")
        assert is_correct is True
        assert expected == " "
        assert skipped == 0
        # Cursor moves 11 -> 12 -> 13 -> 14 -> 15
        assert engine.state.cursor_position == 11 + (i + 1)

    # After manually typing spaces, we should be at 'p'
    assert engine.state.cursor_position == 15
    assert engine.state.content[engine.state.cursor_position] == "p"
