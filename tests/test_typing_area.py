"""Tests for typing area widget, specifically file encoding handling."""
import os
import tempfile
import pytest


class TestFileEncodingFallback:
    """Test file encoding fallback chain in load_file()."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def typing_area(self):
        """Create a TypingAreaWidget instance for testing."""
        # Import here to avoid Qt initialization issues if no display
        from PySide6.QtWidgets import QApplication
        import sys
        
        # Create QApplication if not exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        from app.typing_area import TypingAreaWidget
        widget = TypingAreaWidget()
        yield widget
    
    def test_load_utf8_file(self, typing_area, temp_dir):
        """Test loading a standard UTF-8 encoded file."""
        file_path = os.path.join(temp_dir, "test_utf8.txt")
        content = "Hello, World! 你好世界 🎉"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        typing_area.load_file(file_path)
        
        assert typing_area.original_content == content
        assert "Error" not in typing_area.original_content
    
    def test_load_utf8_bom_file(self, typing_area, temp_dir):
        """Test loading a UTF-8 file with BOM (Byte Order Mark)."""
        file_path = os.path.join(temp_dir, "test_utf8_bom.txt")
        content = "Hello with BOM"
        
        with open(file_path, 'w', encoding='utf-8-sig') as f:
            f.write(content)
        
        typing_area.load_file(file_path)
        
        # UTF-8 reads the BOM as a character, but content should still be usable
        # The BOM is \ufeff - either it's stripped (utf-8-sig) or included (utf-8)
        assert "Hello with BOM" in typing_area.original_content
        assert "Error" not in typing_area.original_content
    
    def test_load_cp1252_file(self, typing_area, temp_dir):
        """Test loading a Windows CP1252 encoded file."""
        file_path = os.path.join(temp_dir, "test_cp1252.txt")
        
        # Write raw CP1252 bytes directly
        # 0x93 = left double quote, 0x94 = right double quote, 0x97 = em dash in CP1252
        raw_bytes = b"Smart quotes: \x93hello\x94 and dashes\x97like this"
        
        with open(file_path, 'wb') as f:
            f.write(raw_bytes)
        
        typing_area.load_file(file_path)
        
        # File should load without error
        assert "Error" not in typing_area.original_content
        # Content should be present (might be decoded slightly differently but readable)
        assert "hello" in typing_area.original_content
    
    def test_load_latin1_file(self, typing_area, temp_dir):
        """Test loading a Latin-1 (ISO-8859-1) encoded file."""
        file_path = os.path.join(temp_dir, "test_latin1.txt")
        content = "Café résumé naïve"
        
        with open(file_path, 'w', encoding='latin-1') as f:
            f.write(content)
        
        typing_area.load_file(file_path)
        
        # Latin-1 should be decoded (possibly by CP1252 or Latin-1 fallback)
        assert "Error" not in typing_area.original_content
        # Basic ASCII parts should be present
        assert "Caf" in typing_area.original_content
        assert "sum" in typing_area.original_content
    
    def test_load_nonexistent_file(self, typing_area, temp_dir):
        """Test loading a file that doesn't exist."""
        file_path = os.path.join(temp_dir, "nonexistent.txt")
        
        typing_area.load_file(file_path)
        
        assert "Error loading file" in typing_area.original_content
        assert "No such file or directory" in typing_area.original_content
    
    def test_load_empty_file(self, typing_area, temp_dir):
        """Test loading an empty file."""
        file_path = os.path.join(temp_dir, "empty.txt")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("")
        
        typing_area.load_file(file_path)
        
        assert typing_area.original_content == ""
    
    def test_load_file_with_special_characters(self, typing_area, temp_dir):
        """Test loading a file with various special characters."""
        file_path = os.path.join(temp_dir, "special.txt")
        content = "def hello():\n    print('¡Hola! © 2024')\n    return True"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        typing_area.load_file(file_path)
        
        assert typing_area.original_content == content
        assert "def hello" in typing_area.original_content
        assert "¡Hola!" in typing_area.original_content
    
    def test_load_file_with_mixed_line_endings(self, typing_area, temp_dir):
        """Test loading a file with different line ending styles."""
        file_path = os.path.join(temp_dir, "mixed_endings.txt")
        
        # Write with explicit bytes to control line endings
        with open(file_path, 'wb') as f:
            f.write(b"line1\nline2\r\nline3\rline4")
        
        typing_area.load_file(file_path)
        
        assert "Error" not in typing_area.original_content
        assert "line1" in typing_area.original_content
        assert "line4" in typing_area.original_content
    
    def test_encoding_fallback_order(self, typing_area, temp_dir):
        """Test that UTF-8 is tried first, then fallbacks."""
        file_path = os.path.join(temp_dir, "utf8_valid.txt")
        content = "Simple ASCII text"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        typing_area.load_file(file_path)
        
        # Should load as UTF-8 (first in chain)
        assert typing_area.original_content == content
    
    def test_binary_file_falls_back_to_latin1(self, typing_area, temp_dir):
        """Test that binary-ish files fall back to Latin-1 which accepts all bytes."""
        file_path = os.path.join(temp_dir, "binary_ish.txt")
        
        # Write bytes that are invalid UTF-8 but valid Latin-1
        with open(file_path, 'wb') as f:
            f.write(bytes([0x80, 0x81, 0x82, 0x83, 0x84]))  # Invalid UTF-8 sequence
        
        typing_area.load_file(file_path)
        
        # Should not error - Latin-1 accepts all byte values 0-255
        assert "Error" not in typing_area.original_content
        # Content should have 5 characters (one per byte)
        assert len(typing_area.original_content) == 5


class TestTypingAreaInitialization:
    """Test TypingAreaWidget initialization."""
    
    @pytest.fixture
    def typing_area(self):
        """Create a TypingAreaWidget instance for testing."""
        from PySide6.QtWidgets import QApplication
        import sys
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        from app.typing_area import TypingAreaWidget
        widget = TypingAreaWidget()
        yield widget
    
    def test_initial_state(self, typing_area):
        """Test that widget initializes with correct default state."""
        assert typing_area.original_content == ""
        assert typing_area.display_content == ""
        assert typing_area.engine is None
        assert typing_area.current_typing_position == 0
    
    def test_load_file_initializes_engine(self, typing_area, tmp_path):
        """Test that loading a file initializes the typing engine."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("hello world", encoding='utf-8')
        
        typing_area.load_file(str(file_path))
        
        assert typing_area.engine is not None
        assert typing_area.engine.state.content == "hello world"


class TestTabWidthSetting:
    """Test configurable tab width setting."""
    
    @pytest.fixture
    def typing_area(self):
        """Create a TypingAreaWidget instance for testing."""
        from PySide6.QtWidgets import QApplication
        import sys
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        from app.typing_area import TypingAreaWidget
        widget = TypingAreaWidget()
        yield widget
    
    def test_default_tab_width(self, typing_area):
        """Test that default tab width is 4."""
        # Default from settings or fallback
        assert typing_area.tab_width == 4
    
    def test_update_tab_width(self, typing_area):
        """Test updating tab width dynamically."""
        typing_area.update_tab_width(2)
        assert typing_area.tab_width == 2
        
        typing_area.update_tab_width(8)
        assert typing_area.tab_width == 8
    
    def test_tab_expansion_in_display_content(self, typing_area, tmp_path):
        """Test that tabs are expanded to correct number of spaces."""
        file_path = tmp_path / "test_tabs.txt"
        file_path.write_text("a\tb\tc", encoding='utf-8')
        
        typing_area.tab_width = 4
        typing_area.load_file(str(file_path))
        
        # Tab should be expanded to 4 space characters (·)
        space_char = typing_area.space_char
        expected_tab = space_char * 4
        assert expected_tab in typing_area.display_content
    
    def test_tab_width_2_expansion(self, typing_area, tmp_path):
        """Test tab expansion with width 2."""
        file_path = tmp_path / "test_tabs2.txt"
        file_path.write_text("x\ty", encoding='utf-8')
        
        typing_area.update_tab_width(2)
        typing_area.load_file(str(file_path))
        
        space_char = typing_area.space_char
        # With width 2, tab becomes 2 space chars
        assert space_char * 2 in typing_area.display_content
    
    def test_tab_width_update_regenerates_display(self, typing_area, tmp_path):
        """Test that changing tab width regenerates display content."""
        file_path = tmp_path / "test_regen.txt"
        file_path.write_text("a\tb", encoding='utf-8')
        
        typing_area.load_file(str(file_path))
        space_char = typing_area.space_char
        
        # Initially 4 spaces
        initial_display = typing_area.display_content
        assert space_char * 4 in initial_display
        
        # Change to 2 spaces
        typing_area.update_tab_width(2)
        updated_display = typing_area.display_content
        
        # Should now have 2 spaces, not 4
        assert space_char * 2 in updated_display
        # The display should be different
        assert initial_display != updated_display
    
    def test_display_char_for_tab(self, typing_area):
        """Test _display_char_for returns correct tab representation."""
        typing_area.tab_width = 4
        space_char = typing_area.space_char
        
        result = typing_area._display_char_for('\t')
        
        assert result == space_char * 4
        assert len(result) == 4
    
    def test_prepare_display_content_with_tabs(self, typing_area):
        """Test _prepare_display_content handles tabs correctly."""
        typing_area.tab_width = 4
        space_char = typing_area.space_char
        
        content = "line1\n\tindented\n\t\tdouble"
        result = typing_area._prepare_display_content(content)
        
        # Check tabs are replaced with space chars
        assert space_char * 4 in result  # Single tab
        assert space_char * 8 in result  # Double tab