"""Tests for sound_volume_widget.py - Sound volume control widget."""
import pytest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt


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
