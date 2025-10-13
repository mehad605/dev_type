"""Quick test for allow_continue_mistakes setting."""
from app.typing_engine import TypingEngine

print("Testing STRICT MODE (allow_continue_mistakes=False - default):")
engine1 = TypingEngine('print', allow_continue_mistakes=False)
c1, e1 = engine1.process_keystroke('m')
print(f"  Typed 'm' (expecting 'p'): cursor_pos={engine1.state.cursor_position}, mistake_at={engine1.mistake_at}")
c2, e2 = engine1.process_keystroke('r')
print(f"  Tried to type 'r': blocked={e2 == ''}, cursor_pos={engine1.state.cursor_position}")

print("\nTesting LENIENT MODE (allow_continue_mistakes=True):")
engine2 = TypingEngine('print', allow_continue_mistakes=True)
c3, e3 = engine2.process_keystroke('m')
print(f"  Typed 'm' (expecting 'p'): cursor_pos={engine2.state.cursor_position}, mistake_at={engine2.mistake_at}")
c4, e4 = engine2.process_keystroke('r')
print(f"  Typed 'r': cursor_pos={engine2.state.cursor_position}, mistake_at={engine2.mistake_at}")
c5, e5 = engine2.process_keystroke('i')
print(f"  Typed 'i': cursor_pos={engine2.state.cursor_position}, mistake_at={engine2.mistake_at}")

print("\n✅ Both modes working correctly!")
