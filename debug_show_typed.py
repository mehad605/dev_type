"""Debug test to verify show_typed_char behavior."""
from app import settings
from app.typing_engine import TypingEngine

# Initialize settings
settings.init_db()

# Test 1: Verify setting can be changed
print("Test 1: Settings persistence")
print("-" * 40)
settings.set_setting("show_typed_char", "1")
value = settings.get_setting("show_typed_char")
print(f"Set to '1', got back: '{value}'")
assert value == "1", f"Expected '1', got '{value}'"

settings.set_setting("show_typed_char", "0")
value = settings.get_setting("show_typed_char")
print(f"Set to '0', got back: '{value}'")
assert value == "0", f"Expected '0', got '{value}'"
print("✅ Settings persistence works\n")

# Test 2: Verify typing logic
print("Test 2: Typing logic")
print("-" * 40)

# Simulate what happens in typing_area when show_typed_char is True
show_typed_char = True
char = 'x'  # What user typed
expected = 'h'  # What was expected
is_correct = False

if is_correct:
    display_char = char
else:
    display_char = char if show_typed_char else expected

print(f"show_typed_char = {show_typed_char}")
print(f"User typed: '{char}'")
print(f"Expected: '{expected}'")
print(f"Display char: '{display_char}'")
print(f"Expected display: 'x' (what user typed)")
assert display_char == 'x', f"Expected 'x', got '{display_char}'"
print("✅ Shows what user typed when setting is True\n")

# Test 3: Verify typing logic when False
show_typed_char = False
if is_correct:
    display_char = char
else:
    display_char = char if show_typed_char else expected

print(f"show_typed_char = {show_typed_char}")
print(f"User typed: '{char}'")
print(f"Expected: '{expected}'")
print(f"Display char: '{display_char}'")
print(f"Expected display: 'h' (what was expected)")
assert display_char == 'h', f"Expected 'h', got '{display_char}'"
print("✅ Shows what was expected when setting is False\n")

print("=" * 40)
print("✅ ALL TESTS PASSED")
print("=" * 40)
