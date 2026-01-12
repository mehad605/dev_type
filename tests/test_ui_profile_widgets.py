"""Tests for profile-related UI widgets."""
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.ui_profile_widgets import AvatarGenerator, ProfileAvatar, ProfileTrigger, ProfileCard
from unittest.mock import MagicMock, patch

@pytest.fixture(scope="module")
def qapp():
    """Ensure a QApplication is running."""
    yield QApplication.instance() or QApplication([])

def test_avatar_generator_consistency():
    """Test that the avatar generator returns consistent colors for the same name."""
    name = "TestUser"
    color1 = AvatarGenerator.get_color_for_name(name)
    color2 = AvatarGenerator.get_color_for_name(name)
    assert color1 == color2
    assert color1 in AvatarGenerator.COLORS

def test_profile_avatar_data_update(qapp):
    """Test that ProfileAvatar stores and updates data correctly."""
    avatar = ProfileAvatar("Initial", size=48)
    assert avatar._name == "Initial"
    assert avatar._size == 48
    
    avatar.set_data("Updated", "path/to/img.png")
    assert avatar._name == "Updated"
    assert avatar._image_path == "path/to/img.png"

def test_profile_trigger_hover_effect(qapp):
    """Test that ProfileTrigger updates its stylesheet on hover."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):
        
        # Mock scheme
        mock_scheme = MagicMock()
        mock_scheme.button_hover = "#888888"
        mock_scheme.accent_color = "#FF0000"
        mock_scheme.border_color = "#111111"
        mock_get_scheme.return_value = mock_scheme
        
        trigger = ProfileTrigger("User")
        
        # Test Normal State
        trigger._update_style(False)
        assert "#111111" in trigger.styleSheet() # Normal border
        
        # Test Hover State
        trigger._update_style(True)
        assert "#888888" in trigger.styleSheet() # Hover bg
        assert "#FF0000" in trigger.styleSheet() # Accent border

def test_profile_card_delete_button_locking(qapp):
    """Test that the delete button is hidden when it's inappropriate to delete."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):
        
        mock_scheme = MagicMock()
        mock_scheme.accent_color = "#00FF00"
        mock_scheme.card_border = "#111111"
        mock_scheme.button_hover = "#222222"
        mock_scheme.text_primary = "#FFFFFF"
        mock_get_scheme.return_value = mock_scheme
        
        # Case 1: Active profile (cannot delete)
        card_active = ProfileCard("Active", is_active=True, total_profiles=3)
        assert card_active.delete_btn.isHidden() is True
        
        # Case 2: Only one profile (cannot delete)
        card_only = ProfileCard("OnlyOne", is_active=False, total_profiles=1)
        assert card_only.delete_btn.isHidden() is True
        
        # Case 3: Inactive profile, multiple existing (can delete)
        card_normal = ProfileCard("Inactive", is_active=False, total_profiles=2)
        assert card_normal.delete_btn.isHidden() is False

def test_profile_card_metadata_display(qapp):
    """Test that the profile card displays name and handles truncation."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):
        
        mock_scheme = MagicMock()
        mock_get_scheme.return_value = mock_scheme
        
        # Long name truncation
        long_name = "ThisIsAReallyLongProfileName"
        card = ProfileCard(long_name)
        assert "..." in card.name_lbl.text()
        assert len(card.name_lbl.text()) <= 20
