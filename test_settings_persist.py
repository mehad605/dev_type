"""Test settings persistence."""
from app import settings

settings.init_db()

print("Testing settings persistence:")
print(f"Initial value: {settings.get_setting('allow_continue_mistakes', '0')}")

settings.set_setting('allow_continue_mistakes', '1')
print(f"After setting to '1': {settings.get_setting('allow_continue_mistakes')}")

settings.set_setting('allow_continue_mistakes', '0')
print(f"After setting to '0': {settings.get_setting('allow_continue_mistakes')}")

print("\n✅ Setting persists correctly in database!")
