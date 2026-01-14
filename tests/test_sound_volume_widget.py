"""Tests for sound_volume_widget.py - Sound volume control widget."""
import pytest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPaintEvent, QWheelEvent, QMouseEvent


@pytest.fixture(scope="module")
def app():
    """Create QApplication instance for tests."""
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    yield instance


class TestSoundVolumeWidgetInit:
    """Test SoundVolumeWidget initialization."""
    
    @patch('app.sound_volume_widget.settings.get_setting')
    def test_widget_initialization(self, mock_setting, app):
        """Test widget initializes with default values."""
        mock_setting.side_effect = lambda key, default: default
        
        from app.sound_volume_widget import SoundVolumeWidget
        
        widget = SoundVolumeWidget()
        
        assert widget is not None
    
    @patch('app.sound_volume_widget.settings.get_setting')
    def test_widget_fixed_size(self, mock_setting, app):
        """Test widget has fixed size."""
        mock_setting.side_effect = lambda key, default: default
        
        from app.sound_volume_widget import SoundVolumeWidget
        
        widget = SoundVolumeWidget()
        
        assert widget.width() == 40
        assert widget.height() == 40
    
    @patch('app.sound_volume_widget.settings.get_setting')
    def test_default_volume(self, mock_setting, app):
        """Test default volume is loaded from settings."""
        mock_setting.return_value = "75"
        
        from app.sound_volume_widget import SoundVolumeWidget
        
        widget = SoundVolumeWidget()
        
        # Volume from settings
        assert widget.volume == 75
    
    @patch('app.sound_volume_widget.settings.get_setting')
    def test_default_enabled(self, mock_setting, app):
        """Test default enabled state is loaded from settings."""
        mock_setting.side_effect = lambda key, default: "1" if key == "sound_enabled" else default
        
        from app.sound_volume_widget import SoundVolumeWidget
        
        widget = SoundVolumeWidget()
        
        assert widget.enabled is True


class TestSetVolume:
    """Test set_volume method."""
    
    @patch('app.sound_volume_widget.settings.get_setting')
    def test_set_volume_normal(self, mock_setting, app):
        """Test setting volume to normal value."""
        mock_setting.side_effect = lambda key, default: default
        
        from app.sound_volume_widget import SoundVolumeWidget
        
        widget = SoundVolumeWidget()
        widget.set_volume(75)
        
        assert widget.volume == 75
    
    @patch('app.sound_volume_widget.settings.get_setting')
    def test_set_volume_clamp_high(self, mock_setting, app):
        """Test volume is clamped to 100 max."""
        mock_setting.side_effect = lambda key, default: default
        
        from app.sound_volume_widget import SoundVolumeWidget
        
        widget = SoundVolumeWidget()
        widget.set_volume(150)
        
        assert widget.volume == 100
    
    @patch('app.sound_volume_widget.settings.get_setting')
    def test_set_volume_clamp_low(self, mock_setting, app):
        """Test volume is clamped to 0 min."""
        mock_setting.side_effect = lambda key, default: default
        
        from app.sound_volume_widget import SoundVolumeWidget
        
        widget = SoundVolumeWidget()
        widget.set_volume(-10)
        
        assert widget.volume == 0


class TestSetEnabled:
    """Test set_enabled method."""
    
    @patch('app.sound_volume_widget.settings.get_setting')
    def test_set_enabled_true(self, mock_setting, app):
        """Test setting enabled to True."""
        mock_setting.side_effect = lambda key, default: default
        
        from app.sound_volume_widget import SoundVolumeWidget
        
        widget = SoundVolumeWidget()
        widget.set_enabled(True)
        
        assert widget.enabled is True
    
    @patch('app.sound_volume_widget.settings.get_setting')
    def test_set_enabled_false(self, mock_setting, app):
        """Test setting enabled to False."""
        mock_setting.side_effect = lambda key, default: default
        
        from app.sound_volume_widget import SoundVolumeWidget
        
        widget = SoundVolumeWidget()
        widget.set_enabled(False)
        
        assert widget.enabled is False


class TestSignals:
    """Test signal emissions."""
    
    @patch('app.sound_volume_widget.settings.get_setting')
    def test_volume_changed_signal(self, mock_setting, app):
        """Test volume_changed signal exists."""
        mock_setting.side_effect = lambda key, default: default
        
        from app.sound_volume_widget import SoundVolumeWidget
        
        widget = SoundVolumeWidget()
        
        assert hasattr(widget, 'volume_changed')
    
    @patch('app.sound_volume_widget.settings.get_setting')
    def test_enabled_changed_signal(self, mock_setting, app):
        """Test enabled_changed signal exists."""
        mock_setting.side_effect = lambda key, default: default
        
        from app.sound_volume_widget import SoundVolumeWidget
        
        widget = SoundVolumeWidget()
        
        assert hasattr(widget, 'enabled_changed')


class TestPaintEvent:
    """Test paintEvent method."""

    @patch('app.sound_volume_widget.settings.get_setting')
    @patch('app.sound_volume_widget.QPainter')
    def test_paint_event_enabled(self, mock_painter_class, mock_setting, app):
        """Test paintEvent when sound is enabled."""
        mock_setting.side_effect = lambda key, default: default

        from app.sound_volume_widget import SoundVolumeWidget

        widget = SoundVolumeWidget()
        widget.enabled = True
        widget.hover = False

        mock_painter = MagicMock()
        mock_painter_class.return_value = mock_painter

        event = QPaintEvent(widget.rect())
        widget.paintEvent(event)

        # Check that painter methods were called
        mock_painter.setRenderHint.assert_called()
        mock_painter.setPen.assert_called()
        mock_painter.setBrush.assert_called()
        mock_painter.drawRect.assert_called()
        mock_painter.drawPolygon.assert_called()
        mock_painter.drawArc.assert_called()

    @patch('app.sound_volume_widget.settings.get_setting')
    @patch('app.sound_volume_widget.QPainter')
    def test_paint_event_disabled(self, mock_painter_class, mock_setting, app):
        """Test paintEvent when sound is disabled."""
        mock_setting.side_effect = lambda key, default: default

        from app.sound_volume_widget import SoundVolumeWidget

        widget = SoundVolumeWidget()
        widget.enabled = False
        widget.hover = True

        mock_painter = MagicMock()
        mock_painter_class.return_value = mock_painter

        event = QPaintEvent(widget.rect())
        widget.paintEvent(event)

        # Check that painter methods were called for disabled state
        mock_painter.setRenderHint.assert_called()
        mock_painter.setPen.assert_called()
        mock_painter.setBrush.assert_called()
        mock_painter.drawLine.assert_called()  # Cross out for disabled


class TestEventHandlers:
    """Test event handler methods."""

    @patch('app.sound_volume_widget.settings.get_setting')
    @patch('app.sound_volume_widget.QToolTip')
    @patch('app.sound_volume_widget.QCursor')
    def test_enter_event_enabled(self, mock_cursor, mock_tooltip, mock_setting, app):
        """Test enterEvent when enabled."""
        mock_setting.side_effect = lambda key, default: default
        mock_cursor.pos.return_value = QPoint(0, 0)

        from app.sound_volume_widget import SoundVolumeWidget

        widget = SoundVolumeWidget()
        widget.enabled = True
        widget.volume = 50

        # Mock event
        event = MagicMock()
        widget.enterEvent(event)

        assert widget.hover is True
        mock_tooltip.showText.assert_called_with(
            QPoint(0, 0),
            "Volume: 50%",
            widget
        )

    @patch('app.sound_volume_widget.settings.get_setting')
    @patch('app.sound_volume_widget.QToolTip')
    @patch('app.sound_volume_widget.QCursor')
    def test_enter_event_disabled(self, mock_cursor, mock_tooltip, mock_setting, app):
        """Test enterEvent when disabled."""
        mock_setting.side_effect = lambda key, default: default
        mock_cursor.pos.return_value = QPoint(0, 0)

        from app.sound_volume_widget import SoundVolumeWidget

        widget = SoundVolumeWidget()
        widget.enabled = False

        event = MagicMock()
        widget.enterEvent(event)

        assert widget.hover is True
        mock_tooltip.showText.assert_called_with(
            QPoint(0, 0),
            "Sound Muted",
            widget
        )

    @patch('app.sound_volume_widget.settings.get_setting')
    @patch('app.sound_volume_widget.QToolTip')
    def test_leave_event(self, mock_tooltip, mock_setting, app):
        """Test leaveEvent."""
        mock_setting.side_effect = lambda key, default: default

        from app.sound_volume_widget import SoundVolumeWidget

        widget = SoundVolumeWidget()
        widget.hover = True

        event = MagicMock()
        widget.leaveEvent(event)

        assert widget.hover is False
        mock_tooltip.hideText.assert_called()

    @patch('app.sound_volume_widget.settings.get_setting')
    @patch('app.sound_volume_widget.QToolTip')
    @patch('app.sound_volume_widget.QCursor')
    def test_wheel_event_enabled_increase(self, mock_cursor, mock_tooltip, mock_setting, app):
        """Test wheelEvent increases volume when enabled."""
        mock_setting.side_effect = lambda key, default: default
        mock_cursor.pos.return_value = QPoint(0, 0)

        from app.sound_volume_widget import SoundVolumeWidget

        widget = SoundVolumeWidget()
        widget.enabled = True
        widget.volume = 50

        # Mock wheel event with positive delta
        event = MagicMock()
        event.angleDelta.return_value = QPoint(0, 120)  # Mock QPoint with y=120

        widget.wheelEvent(event)

        assert widget.volume == 55
        mock_tooltip.showText.assert_called_with(
            QPoint(0, 0),
            "Volume: 55%",
            widget
        )

    @patch('app.sound_volume_widget.settings.get_setting')
    def test_wheel_event_disabled(self, mock_setting, app):
        """Test wheelEvent does nothing when disabled."""
        mock_setting.side_effect = lambda key, default: default

        from app.sound_volume_widget import SoundVolumeWidget

        widget = SoundVolumeWidget()
        widget.enabled = False
        widget.volume = 50

        event = MagicMock()
        event.angleDelta.return_value = QPoint(0, 120)

        widget.wheelEvent(event)

        assert widget.volume == 50

    @patch('app.sound_volume_widget.settings.get_setting')
    @patch('app.sound_volume_widget.QToolTip')
    @patch('app.sound_volume_widget.QCursor')
    def test_mouse_double_click_toggle_enabled(self, mock_cursor, mock_tooltip, mock_setting, app):
        """Test mouseDoubleClickEvent toggles enabled state."""
        mock_setting.side_effect = lambda key, default: default
        mock_cursor.pos.return_value = QPoint(0, 0)

        from app.sound_volume_widget import SoundVolumeWidget

        widget = SoundVolumeWidget()
        widget.enabled = True

        event = MagicMock()
        event.button.return_value = Qt.LeftButton

        widget.mouseDoubleClickEvent(event)

        assert widget.enabled is False
        mock_tooltip.showText.assert_called_with(
            QPoint(0, 0),
            "Sound Muted",
            widget
        )


class TestHoverState:
    """Test hover state handling."""
    
    @patch('app.sound_volume_widget.settings.get_setting')
    def test_initial_hover_false(self, mock_setting, app):
        """Test initial hover state is False."""
        mock_setting.side_effect = lambda key, default: default
        
        from app.sound_volume_widget import SoundVolumeWidget
        
        widget = SoundVolumeWidget()
        
        assert widget.hover is False


class TestMouseTracking:
    """Test mouse tracking setup."""
    
    @patch('app.sound_volume_widget.settings.get_setting')
    def test_mouse_tracking_enabled(self, mock_setting, app):
        """Test mouse tracking is enabled."""
        mock_setting.side_effect = lambda key, default: default
        
        from app.sound_volume_widget import SoundVolumeWidget
        
        widget = SoundVolumeWidget()
        
        assert widget.hasMouseTracking() is True
    
    @patch('app.sound_volume_widget.settings.get_setting')
    def test_pointing_cursor(self, mock_setting, app):
        """Test pointing hand cursor is set."""
        mock_setting.side_effect = lambda key, default: default
        
        from app.sound_volume_widget import SoundVolumeWidget
        
        widget = SoundVolumeWidget()
        
        assert widget.cursor().shape() == Qt.PointingHandCursor
