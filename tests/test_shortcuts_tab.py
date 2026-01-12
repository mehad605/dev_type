"""Tests for the shortcuts documentation tab."""
import pytest
from PySide6.QtWidgets import QApplication, QLabel
from app.shortcuts_tab import ShortcutsTab, ShortcutItem
from unittest.mock import MagicMock, patch

@pytest.fixture(scope="module")
def qapp():
    """Ensure a QApplication is running."""
    yield QApplication.instance() or QApplication([])

def test_shortcuts_tab_initialization(qapp):
    """Test that the shortcuts tab populates sections correctly."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):
        
        mock_scheme = MagicMock()
        mock_get_scheme.return_value = mock_scheme
        
        tab = ShortcutsTab()
        
        # Verify title
        assert "Keyboard Shortcuts" in tab.title_label.text()
        
        # Verify content exists (sum of items and section labels)
        assert tab.container_layout.count() > 10
        
        # Verify specific important shortcut exists
        found_profile_shortcut = False
        for i in range(tab.container_layout.count()):
            widget = tab.container_layout.itemAt(i).widget()
            if isinstance(widget, ShortcutItem):
                if "Switch Profile" in widget.desc_label.text():
                    found_profile_shortcut = True
                    assert "Ctrl + Shift + P" in widget.key_label.text()
        
        assert found_profile_shortcut is True

def test_shortcut_item_apply_theme(qapp):
    """Test that individual shortcut items respond to theme changes."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="nord"):
        
        mock_scheme = MagicMock()
        mock_scheme.accent_color = "#NORD1"
        mock_scheme.bg_secondary = "#NORD2"
        mock_scheme.text_primary = "#NORD3"
        mock_get_scheme.return_value = mock_scheme
        
        item = ShortcutItem("Ctrl+X", "Delete everything")
        
        # Check if styles contain our mock colors
        assert "#NORD1" in item.key_label.styleSheet()
        assert "#NORD2" in item.styleSheet()
        assert "#NORD3" in item.desc_label.styleSheet()

def test_shortcuts_tab_theme_propagation(qapp):
    """Test that calling apply_theme on the tab updates child widgets."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):
        
        mock_scheme = MagicMock()
        mock_get_scheme.return_value = mock_scheme
        
        tab = ShortcutsTab()
        
        # Change theme mock and property
        mock_scheme.accent_color = "#NEW_ACCENT"
        
        with patch('app.shortcuts_tab.ShortcutItem.apply_theme') as mock_item_apply:
            tab.apply_theme()
            # It should have called apply_theme on all its children ShortcutItems
            assert mock_item_apply.call_count >= 10
