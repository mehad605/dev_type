"""Test for show_typed_char functionality."""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import settings
from app.typing_area import TypingAreaWidget
from PySide6.QtWidgets import QApplication


def test_show_typed_char_setting():
    """Test that show_typed_char setting persists and loads correctly."""
    import tempfile
    
    # Create temp database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        settings.init_db(str(db_path))
        
        # Set show_typed_char to False
        settings.set_setting("show_typed_char", "0")
        
        # Verify it's saved
        value = settings.get_setting("show_typed_char", "1")
        assert value == "0", f"Expected '0', got '{value}'"
        
        # Set it to True
        settings.set_setting("show_typed_char", "1")
        
        # Verify it's saved
        value = settings.get_setting("show_typed_char", "0")
        assert value == "1", f"Expected '1', got '{value}'"
        
        print("✅ show_typed_char setting persists correctly")


def test_typing_area_loads_setting():
    """Test that TypingAreaWidget loads show_typed_char setting."""
    import tempfile
    
    # Need QApplication for Qt widgets
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        settings.init_db(str(db_path))
        
        # Test with setting = True
        settings.set_setting("show_typed_char", "1")
        widget1 = TypingAreaWidget()
        assert widget1.show_typed_char is True, "Should load as True"
        
        # Test with setting = False
        settings.set_setting("show_typed_char", "0")
        widget2 = TypingAreaWidget()
        assert widget2.show_typed_char is False, "Should load as False"
        
        print("✅ TypingAreaWidget loads show_typed_char correctly")


if __name__ == "__main__":
    test_show_typed_char_setting()
    test_typing_area_loads_setting()
    print("\n✅ All manual tests passed!")
