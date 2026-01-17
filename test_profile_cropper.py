"""
Quick visual test for the modernized profile picture cropper.
Run this to see the new UI in action.
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

try:
    from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QFileDialog
    from PySide6.QtCore import Qt
    from app.ui_profile_selector import ImageCropperDialog, ProfileEditDialog
    
    class TestWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Profile Picture Cropper Test")
            self.setFixedSize(400, 200)
            
            layout = QVBoxLayout(self)
            layout.setContentsMargins(40, 40, 40, 40)
            layout.setSpacing(20)
            
            # Test cropper directly
            btn1 = QPushButton("Test Image Cropper Dialog")
            btn1.setFixedHeight(50)
            btn1.clicked.connect(self.test_cropper)
            layout.addWidget(btn1)
            
            # Test full profile edit dialog
            btn2 = QPushButton("Test Profile Edit Dialog")
            btn2.setFixedHeight(50)
            btn2.clicked.connect(self.test_profile_edit)
            layout.addWidget(btn2)
            
            self.setStyleSheet("""
                QWidget {
                    background-color: #2E3440;
                    color: #ECEFF4;
                }
                QPushButton {
                    background: #3B4252;
                    color: #ECEFF4;
                    border: 1px solid #4C566A;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: #434C5E;
                    border-color: #88C0D0;
                }
            """)
        
        def test_cropper(self):
            """Test the image cropper dialog directly."""
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "Select Test Image", 
                "", 
                "Images (*.png *.jpg *.jpeg)"
            )
            if file_path:
                dialog = ImageCropperDialog(file_path, self)
                if dialog.exec():
                    print(f"Cropped image saved to: {dialog.get_cropped_image_path()}")
                else:
                    print("Cropping cancelled")
        
        def test_profile_edit(self):
            """Test the full profile edit dialog."""
            dialog = ProfileEditDialog(parent=self)
            if dialog.exec():
                name, img_path = dialog.get_data()
                print(f"Profile created: {name}")
                print(f"Image path: {img_path}")
            else:
                print("Profile edit cancelled")
    
    def main():
        app = QApplication(sys.argv)
        window = TestWindow()
        window.show()
        sys.exit(app.exec())
    
    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"Error: {e}")
    print("\nThis test requires PySide6 to be installed.")
    print("Install it with: pip install PySide6")
    sys.exit(1)
