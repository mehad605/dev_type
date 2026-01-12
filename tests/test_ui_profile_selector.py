"""Tests for profile selection and editing dialogs."""
import pytest
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtCore import Qt
from app.ui_profile_selector import ProfileEditDialog, ProfileManagerDialog
from unittest.mock import MagicMock, patch

@pytest.fixture(scope="module")
def qapp():
    """Ensure a QApplication is running."""
    yield QApplication.instance() or QApplication([])

def test_profile_edit_dialog_validation_logic(qapp):
    """Test that save button is only enabled with a valid name."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):
        
        mock_get_scheme.return_value = MagicMock()
        
        # Scenario: Empty name initially
        dialog = ProfileEditDialog()
        assert dialog.save_btn.isEnabled() is False
        
        # Scenario: Valid name typed
        dialog.name_input.setText("Zoof")
        assert dialog.save_btn.isEnabled() is True
        assert dialog.name == "Zoof"
        
        # Scenario: Spaces only
        dialog.name_input.setText("   ")
        assert dialog.save_btn.isEnabled() is False

def test_profile_edit_dialog_image_update(qapp):
    """Test that uploading a photo updates the internal state."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):
        
        mock_get_scheme.return_value = MagicMock()
        dialog = ProfileEditDialog()
        
        # Simulate QFileDialog success
        with patch('PySide6.QtWidgets.QFileDialog.getOpenFileName', return_value=("test_image.png", "Images")):
            dialog.upload_photo()
            assert dialog.image_path == "test_image.png"
            assert dialog.avatar_preview._image_path == "test_image.png"

def test_profile_manager_grid_population(qapp):
    """Test that the manager dialog populates the grid based on profiles."""
    with patch('app.ui_profile_selector.get_profile_manager') as mock_get_pm, \
         patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):
        
        # Mock Profile Manager
        mock_pm = MagicMock()
        mock_pm.get_all_profiles.return_value = [
            {"name": "Profile 1", "image": None, "is_active": True},
            {"name": "Profile 2", "image": None, "is_active": False},
            {"name": "Profile 3", "image": None, "is_active": False}
        ]
        mock_get_pm.return_value = mock_pm
        mock_get_scheme.return_value = MagicMock()
        
        dialog = ProfileManagerDialog()
        
        # Verify 3 cards in the grid layout
        assert dialog.grid_layout.count() == 3
        
        # Check if first card corresponds to P1
        first_card = dialog.grid_layout.itemAt(0).widget()
        assert first_card._name == "Profile 1"

def test_profile_manager_create_flow(qapp):
    """Test that creating a profile from the manager triggers refresh."""
    with patch('app.ui_profile_selector.get_profile_manager') as mock_get_pm, \
         patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):
        
        mock_pm = MagicMock()
        mock_pm.get_all_profiles.return_value = []
        mock_get_pm.return_value = mock_pm
        mock_get_scheme.return_value = MagicMock()
        
        dialog = ProfileManagerDialog()
        
        with patch('app.ui_profile_selector.ProfileEditDialog.exec', return_value=True), \
             patch('app.ui_profile_selector.ProfileEditDialog.get_data', return_value=("NewGuy", None)), \
             patch.object(dialog, 'refresh_grid') as mock_refresh:
            
            mock_pm.create_profile.return_value = True
            dialog.create_profile()
            
            mock_pm.create_profile.assert_called_with("NewGuy", None)
            mock_refresh.assert_called_once()
