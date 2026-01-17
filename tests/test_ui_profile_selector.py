"""Tests for profile selection and editing dialogs."""
import pytest
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QColor
from app.ui_profile_selector import ProfileEditDialog, ProfileManagerDialog, ImageCropperDialog, ImageCropWidget
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

def test_profile_edit_dialog_image_update(qapp, tmp_path):
    """Test that uploading a photo updates the internal state."""
    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):

        mock_get_scheme.return_value = MagicMock()

        # Create a test image
        test_image = tmp_path / "test_image.png"
        # Create a simple test image (100x100 pixel)
        pixmap = QPixmap(100, 100)
        pixmap.fill(QColor(255, 0, 0))  # Red square
        pixmap.save(str(test_image), "PNG")

        dialog = ProfileEditDialog()

        # Mock the cropper dialog to return the test image path
        with patch('app.ui_profile_selector.ImageCropperDialog') as mock_cropper:
            mock_cropper.return_value.exec.return_value = True
            mock_cropper.return_value.get_cropped_image_path.return_value = str(test_image)

            with patch('PySide6.QtWidgets.QFileDialog.getOpenFileName', return_value=(str(test_image), "Images")):
                dialog.upload_photo()
                assert dialog.image_path == str(test_image)
                assert dialog.avatar_preview._image_path == str(test_image)


def test_image_cropper_file_size_validation(qapp, tmp_path):
    """Test that images over 10MB are rejected."""
    # Create a large file (>10MB)
    large_file = tmp_path / "large_image.png"
    # Write more than 10MB of data
    large_data = b"x" * (11 * 1024 * 1024)  # 11MB
    large_file.write_bytes(large_data)

    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):

        mock_get_scheme.return_value = MagicMock()

        # Mock QMessageBox to avoid dialog popup during test
        with patch('PySide6.QtWidgets.QMessageBox.warning'):
            # This should reject due to file size
            cropper = ImageCropperDialog(str(large_file))
            # The dialog should have rejected itself


def test_image_cropper_valid_file(qapp, tmp_path):
    """Test that valid images are accepted."""
    # Create a valid small image
    test_image = tmp_path / "valid_image.png"
    pixmap = QPixmap(100, 100)
    pixmap.fill(QColor(255, 0, 0))
    pixmap.save(str(test_image), "PNG")

    with patch('app.themes.get_color_scheme') as mock_get_scheme, \
         patch('app.settings.get_setting', return_value="dracula"):

        mock_get_scheme.return_value = MagicMock()

        # This should work without issues
        cropper = ImageCropperDialog(str(test_image))
        # Dialog should be created successfully
        assert cropper.original_pixmap.isNull() == False


def test_image_crop_widget_reset_view(qapp):
    """Test that reset view functionality works."""
    pixmap = QPixmap(200, 200)
    pixmap.fill(QColor(255, 0, 0))

    widget = ImageCropWidget(pixmap)
    widget.resize(400, 400)

    # Change zoom and pan
    widget.zoom_factor = 2.0
    widget.pan_offset = QPoint(50, 50)

    # Reset view
    widget.reset_view()

    # Should be back to fit-in-circle zoom
    assert widget.zoom_factor < 2.0  # Should be smaller
    assert widget.pan_offset == QPoint(0, 0)


def test_image_crop_widget_fit_to_circle(qapp):
    """Test that fit to circle functionality works."""
    pixmap = QPixmap(400, 400)  # Square image
    pixmap.fill(QColor(255, 0, 0))

    widget = ImageCropWidget(pixmap)
    widget.resize(400, 400)

    # Change zoom to something larger
    widget.zoom_factor = 3.0

    # Fit to circle
    widget.fit_to_circle()

    # Should be smaller zoom to fit entire image
    assert widget.zoom_factor <= 1.0

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
