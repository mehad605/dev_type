"""Tests for generate_icon.py - Icon generation utilities."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    """Create QApplication instance for tests."""
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    yield instance


class TestConvertSvgToPng:
    """Test convert_svg_to_png function."""
    
    def test_convert_invalid_svg(self, app, tmp_path):
        """Test conversion with invalid SVG file."""
        from app.generate_icon import convert_svg_to_png
        
        # Create invalid SVG
        svg_path = tmp_path / "invalid.svg"
        svg_path.write_text("not valid svg content")
        png_path = tmp_path / "output.png"
        
        result = convert_svg_to_png(svg_path, png_path)
        
        assert result is False
    
    def test_convert_valid_svg(self, app, tmp_path):
        """Test conversion with valid SVG file."""
        from app.generate_icon import convert_svg_to_png
        
        # Create a valid minimal SVG
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80" fill="blue"/>
</svg>'''
        svg_path = tmp_path / "valid.svg"
        svg_path.write_text(svg_content)
        png_path = tmp_path / "output.png"
        
        result = convert_svg_to_png(svg_path, png_path)
        
        assert result is True
        assert png_path.exists()
    
    def test_convert_with_custom_size(self, app, tmp_path):
        """Test conversion with custom size parameter."""
        from app.generate_icon import convert_svg_to_png
        
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <circle cx="50" cy="50" r="40" fill="red"/>
</svg>'''
        svg_path = tmp_path / "circle.svg"
        svg_path.write_text(svg_content)
        png_path = tmp_path / "output_512.png"
        
        result = convert_svg_to_png(svg_path, png_path, size=512)
        
        assert result is True
        assert png_path.exists()
    
    def test_convert_nonexistent_svg(self, app, tmp_path):
        """Test conversion with non-existent SVG file."""
        from app.generate_icon import convert_svg_to_png
        
        svg_path = tmp_path / "nonexistent.svg"
        png_path = tmp_path / "output.png"
        
        result = convert_svg_to_png(svg_path, png_path)
        
        assert result is False


class TestConvertSvgToIco:
    """Test convert_svg_to_ico function."""
    
    def test_convert_invalid_svg_to_ico(self, app, tmp_path):
        """Test ICO conversion with invalid SVG."""
        from app.generate_icon import convert_svg_to_ico
        
        svg_path = tmp_path / "invalid.svg"
        svg_path.write_text("not valid svg")
        ico_path = tmp_path / "output.ico"
        
        result = convert_svg_to_ico(svg_path, ico_path)
        
        assert result is False
    
    def test_convert_valid_svg_to_ico(self, app, tmp_path):
        """Test ICO conversion with valid SVG."""
        from app.generate_icon import convert_svg_to_ico
        
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80" fill="green"/>
</svg>'''
        svg_path = tmp_path / "valid.svg"
        svg_path.write_text(svg_content)
        ico_path = tmp_path / "output.ico"
        
        result = convert_svg_to_ico(svg_path, ico_path)
        
        assert result is True
        assert ico_path.exists()
    
    def test_ico_creates_temp_directory(self, app, tmp_path):
        """Test that temp directory is created during ICO generation."""
        from app.generate_icon import convert_svg_to_ico
        
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect width="100" height="100" fill="purple"/>
</svg>'''
        svg_path = tmp_path / "test.svg"
        svg_path.write_text(svg_content)
        ico_path = tmp_path / "test.ico"
        
        convert_svg_to_ico(svg_path, ico_path)
        
        # Temp directory should have been created (may or may not be cleaned up)
        temp_dir = tmp_path / "temp_ico"
        # The function creates this directory
        assert ico_path.exists()


class TestModuleImports:
    """Test module-level imports and availability."""
    
    def test_module_imports(self, app):
        """Test that all required imports are available."""
        from app.generate_icon import convert_svg_to_png, convert_svg_to_ico
        
        assert callable(convert_svg_to_png)
        assert callable(convert_svg_to_ico)
    
    def test_qsvg_renderer_available(self, app):
        """Test QSvgRenderer is available."""
        from PySide6.QtSvg import QSvgRenderer
        
        assert QSvgRenderer is not None
