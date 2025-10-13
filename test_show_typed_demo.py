"""Interactive test to demonstrate show_typed_char behavior."""
from app import settings
from app.typing_engine import TypingEngine

settings.init_db()

print("=" * 60)
print("TESTING: Show Typed Character Setting")
print("=" * 60)
print()

# Create engine with test content
content = "hello"
engine = TypingEngine(content)

print(f"Expected text: '{content}'")
print()

# Test 1: With show_typed_char = True (CHECKED)
print("-" * 60)
print("TEST 1: Setting CHECKED (show what you typed)")
print("-" * 60)
settings.set_setting("show_typed_char", "1")
show_typed_char = settings.get_setting("show_typed_char", "1") == "1"
print(f"show_typed_char = {show_typed_char}")
print()

# Simulate typing wrong character
char = 'x'  # User types 'x'
is_correct, expected = engine.process_keystroke(char, advance_on_error=True)

print(f"Position 0 - Expected: '{expected}', User typed: '{char}'")
print(f"Is correct: {is_correct}")

# Determine what to display
if is_correct:
    display_char = char
else:
    display_char = char if show_typed_char else expected

print(f"Display character: '{display_char}'")
print(f"✅ RESULT: Shows '{display_char}' in red (what you actually typed)")
print()

# Reset engine
engine.reset()

# Test 2: With show_typed_char = False (UNCHECKED)
print("-" * 60)
print("TEST 2: Setting UNCHECKED (show what was expected)")
print("-" * 60)
settings.set_setting("show_typed_char", "0")
show_typed_char = settings.get_setting("show_typed_char", "1") == "1"
print(f"show_typed_char = {show_typed_char}")
print()

# Simulate typing wrong character again
char = 'x'  # User types 'x'
is_correct, expected = engine.process_keystroke(char, advance_on_error=True)

print(f"Position 0 - Expected: '{expected}', User typed: '{char}'")
print(f"Is correct: {is_correct}")

# Determine what to display
if is_correct:
    display_char = char
else:
    display_char = char if show_typed_char else expected

print(f"Display character: '{display_char}'")
print(f"✅ RESULT: Shows '{display_char}' in red (what was expected)")
print()

print("=" * 60)
print("SUMMARY:")
print("=" * 60)
print("CHECKED   (show_typed_char=True):  Type 'x', see 'x' in red")
print("UNCHECKED (show_typed_char=False): Type 'x', see 'h' in red")
print("=" * 60)
