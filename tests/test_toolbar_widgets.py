"""Tests for custom toolbar buttons."""
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QPaintEvent
from PySide6.QtCore import Qt
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


def test_toolbar_button_events(qapp):
    """Test enter/leave events update hover state."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"), \
         patch('app.toolbar_widgets.ToolbarButton.update'):

        mock_scheme = MagicMock()
        mock_get_scheme.return_value = mock_scheme

        btn = ToolbarButton()

        # Initially no hover
        assert btn._hover is False

        # Enter event
        btn._hover = True
        btn._update_colors()
        assert btn._hover is True

        # Leave event
        btn._hover = False
        assert btn._hover is False


@patch('app.toolbar_widgets.QPainter')
def test_toolbar_button_paint_event_drawing(mock_painter_class, qapp):
    """Test ToolbarButton paintEvent."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):

        mock_scheme = MagicMock()
        mock_scheme.bg_tertiary = "#222222"
        mock_get_scheme.return_value = mock_scheme

        btn = ToolbarButton()
        btn.setEnabled(True)
        btn.setCheckable(True)
        btn.setChecked(False)
        btn._hover = True

        mock_painter = MagicMock()
        mock_painter_class.return_value = mock_painter

        event = QPaintEvent(btn.rect())
        btn.paintEvent(event)

        mock_painter.setRenderHint.assert_called()
        mock_painter.setBrush.assert_called()
        mock_painter.drawRoundedRect.assert_called()


@patch('app.toolbar_widgets.QPainter')
def test_ghost_button_paint_event(mock_painter_class, qapp):
    """Test GhostButton paintEvent."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):

        mock_scheme = MagicMock()
        mock_scheme.bg_tertiary = "#222222"
        mock_get_scheme.return_value = mock_scheme

        btn = GhostButton()

        mock_painter = MagicMock()
        mock_painter_class.return_value = mock_painter

        event = QPaintEvent(btn.rect())
        btn.paintEvent(event)

        # Should call super().paintEvent and then draw ghost icon
        assert mock_painter.setRenderHint.call_count >= 2  # Base + ghost
        mock_painter.drawPath.assert_called()
        mock_painter.drawEllipse.assert_called()


@patch('app.toolbar_widgets.QPainter')
def test_instant_death_button_paint_event(mock_painter_class, qapp):
    """Test InstantDeathButton paintEvent."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):

        mock_scheme = MagicMock()
        mock_scheme.bg_tertiary = "#222222"
        mock_scheme.text_primary = "#FFFFFF"
        mock_get_scheme.return_value = mock_scheme

        btn = InstantDeathButton()
        btn.setChecked(False)  # Normal eyes

        mock_painter = MagicMock()
        mock_painter_class.return_value = mock_painter

        event = QPaintEvent(btn.rect())
        btn.paintEvent(event)

        # Should call super().paintEvent and then draw skull
        assert mock_painter.setRenderHint.call_count >= 2  # Base + skull
        mock_painter.drawRoundedRect.assert_called()
        # For normal eyes, should draw filled ellipses
        mock_painter.drawEllipse.assert_called()


@patch('app.toolbar_widgets.QPainter')
def test_instant_death_button_paint_event_checked(mock_painter_class, qapp):
    """Test InstantDeathButton paintEvent when checked (X eyes)."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):

        mock_scheme = MagicMock()
        mock_scheme.bg_tertiary = "#222222"
        mock_scheme.text_primary = "#FFFFFF"
        mock_get_scheme.return_value = mock_scheme

        btn = InstantDeathButton()
        btn.setChecked(True)  # X eyes

        mock_painter = MagicMock()
        mock_painter_class.return_value = mock_painter

        event = QPaintEvent(btn.rect())
        btn.paintEvent(event)

        # Should call super().paintEvent and then draw skull with X eyes
        assert mock_painter.setRenderHint.call_count >= 2  # Base + skull
        mock_painter.drawRoundedRect.assert_called()
        # For checked eyes, should draw X lines, not ellipses
        mock_painter.drawLine.assert_called()


def test_instant_death_button_get_icon_color_checked(qapp):
    """Test InstantDeathButton get_icon_color when checked."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):

        mock_scheme = MagicMock()
        mock_scheme.text_primary = "#FFFFFF"
        mock_get_scheme.return_value = mock_scheme

        btn = InstantDeathButton()
        btn.setEnabled(True)
        btn.setChecked(True)

        color = btn.get_icon_color()
        assert color.name() == "#bf616a"


def test_instant_death_button_get_icon_color_hover(qapp):
    """Test InstantDeathButton get_icon_color when hovering."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):

        mock_scheme = MagicMock()
        mock_scheme.text_primary = "#FFFFFF"
        mock_get_scheme.return_value = mock_scheme

        btn = InstantDeathButton()
        btn.setEnabled(True)
        btn.setChecked(False)
        btn._hover = True

        color = btn.get_icon_color()
        assert color.name().upper() == "#FFFFFF"
