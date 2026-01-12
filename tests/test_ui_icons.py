"""Tests for SVG-based UI icons."""
import pytest
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSize
from app.ui_icons import get_svg_content, get_pixmap, get_icon, ICON_PATHS

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])

def test_get_svg_content_valid():
    """Test that all defined icons produce SVG content."""
    for icon_name in ICON_PATHS:
        svg = get_svg_content(icon_name)
        assert "<svg" in svg
        assert "xmlns=" in svg
        assert "stroke=" in svg

def test_get_svg_content_unknown():
    """Test that unknown icons return empty string."""
    assert get_svg_content("NON_EXISTENT_ICON") == ""

def test_get_svg_content_color_override():
    """Test that color override is applied to SVG."""
    custom_color = "#123456"
    svg = get_svg_content("EDIT", color_override=custom_color)
    assert f'stroke="{custom_color}"' in svg

def test_get_pixmap_valid(qapp):
    """Test rendering an icon to a pixmap."""
    size = 32
    pixmap = get_pixmap("EDIT", size=size)
    assert isinstance(pixmap, QPixmap)
    assert not pixmap.isNull()
    assert pixmap.width() == size
    assert pixmap.height() == size

def test_get_pixmap_unknown(qapp):
    """Test that unknown icons return an empty pixmap."""
    pixmap = get_pixmap("NON_EXISTENT")
    assert pixmap.isNull()

def test_get_icon_valid(qapp):
    """Test creating a QIcon."""
    icon = get_icon("SETTINGS")
    assert isinstance(icon, QIcon)
    assert not icon.isNull()
    # Should have a reasonably sized pixmap (we use 64 in the code)
    assert icon.availableSizes()[0].width() >= 24

def test_get_pixmap_color_override(qapp):
    """Test pixmap with color override doesn't crash."""
    pixmap = get_pixmap("DELETE", color_override="#FF00FF")
    assert not pixmap.isNull()
