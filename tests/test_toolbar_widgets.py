"""Tests for custom toolbar buttons."""
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor
from app.toolbar_widgets import ToolbarButton, GhostButton, InstantDeathButton
from unittest.mock import MagicMock, patch

@pytest.fixture(scope="module")
def qapp():
    """Ensure a QApplication is running."""
    yield QApplication.instance() or QApplication([])

def test_toolbar_button_color_logic(qapp):
    """Test that ToolbarButton calculates icon colors based on state."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):
        
        mock_scheme = MagicMock()
        mock_scheme.text_primary = "#FFFFFF"
        mock_scheme.accent_color = "#FF00FF"
        mock_get_scheme.return_value = mock_scheme
        
        btn = ToolbarButton()
        
        # State: Normal
        btn.setEnabled(True)
        btn.setCheckable(True)
        btn.setChecked(False)
        btn._hover = False
        color = btn.get_icon_color()
        assert color.name().upper() == "#FFFFFF"
        assert color.alpha() == 180
        
        # State: Hover
        btn._hover = True
        color = btn.get_icon_color()
        assert color.name().upper() == "#FFFFFF"
        assert color.alpha() == 255
        
        # State: Checked
        btn._hover = False
        btn.setChecked(True)
        color = btn.get_icon_color()
        assert color.name().upper() == "#FF00FF"
        
        # State: Disabled
        btn.setEnabled(False)
        color = btn.get_icon_color()
        assert color.alpha() == 50

def test_instant_death_button_special_color(qapp):
    """Test that InstantDeathButton uses dangerous red color when active."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):
        
        mock_scheme = MagicMock()
        mock_scheme.text_primary = "#FFFFFF"
        mock_get_scheme.return_value = mock_scheme
        
        btn = InstantDeathButton()
        btn.setChecked(True)
        
        color = btn.get_icon_color()
        # Red-ish color specified in code: #bf616a
        assert color.name().lower() == "#bf616a"

def test_toolbar_button_paint_event(qapp):
    """Integration test to ensure paintEvent doesn't crash."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):
        
        mock_scheme = MagicMock()
        mock_scheme.bg_tertiary = "#222222"
        mock_scheme.text_primary = "#FFFFFF"
        mock_scheme.accent_color = "#FF0000"
        mock_get_scheme.return_value = mock_scheme
        
        # Test GhostButton (specific paint logic)
        btn = GhostButton()
        btn._hover = True
        btn.repaint() # Triggers paintEvent
        
        # Test InstantDeathButton (specific paint logic)
        btn2 = InstantDeathButton()
        btn2.setChecked(True)
        btn2.repaint()
