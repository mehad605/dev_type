import logging
import os
from PySide6.QtWidgets import (QDialog, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                               QGridLayout, QScrollArea, QPushButton, QLineEdit, 
                               QFileDialog, QMessageBox, QFrame)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap

from app.profile_manager import get_profile_manager
from app.ui_profile_widgets import ProfileCard, AvatarGenerator, ProfileAvatar
from app.ui_icons import get_icon
from app import settings
from app.themes import get_color_scheme

logger = logging.getLogger(__name__)

class ProfileEditDialog(QDialog):
    """Dialog to create or edit a profile."""
    
    def __init__(self, current_name=None, current_image=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Profile" if not current_name else "Edit Profile")
        self.setFixedSize(450, 380)
        
        self.name = current_name
        self.image_path = current_image
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        # Avatar Preview - use ProfileAvatar for circular display
        avatar_container = QWidget()
        avatar_container.setStyleSheet("background: transparent;")
        avatar_layout = QHBoxLayout(avatar_container)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.setAlignment(Qt.AlignCenter)
        
        self.avatar_preview = ProfileAvatar(self.name or "?", self.image_path, size=100)
        avatar_layout.addWidget(self.avatar_preview)
        
        layout.addWidget(avatar_container)
        
        # Upload Button
        self.upload_btn = QPushButton("Upload Photo")
        self.upload_btn.setIcon(get_icon("FOLDER"))
        self.upload_btn.setFixedHeight(40)
        self.upload_btn.setCursor(Qt.PointingHandCursor)
        self.upload_btn.clicked.connect(self.upload_photo)
        layout.addWidget(self.upload_btn)
        
        # Name Input
        name_container = QVBoxLayout()
        name_container.setSpacing(8)
        
        name_lbl = QLabel("Profile Name")
        name_lbl.setStyleSheet("color: #ECEFF4; font-weight: 600; background: transparent;")
        name_container.addWidget(name_lbl)
        
        self.name_input = QLineEdit(self.name or "")
        self.name_input.setPlaceholderText("Enter name...")
        self.name_input.setMaxLength(15)  # Hard limit of 15 characters
        self.name_input.setFixedHeight(44)
        self.name_input.textChanged.connect(self.on_name_changed)
        name_container.addWidget(self.name_input)
        
        layout.addLayout(name_container)
        
        layout.addStretch()
        
        # Buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(44)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setFixedHeight(44)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setDefault(True)
        self.save_btn.setEnabled(bool(self.name))
        
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self.accept)
        
        action_layout.addWidget(self.cancel_btn)
        action_layout.addWidget(self.save_btn)
        layout.addLayout(action_layout)
        
        # Styles - clean, no extra backgrounds
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)

        self.setStyleSheet(f"""
            QDialog {{ 
                background-color: {scheme.bg_primary}; 
                color: {scheme.text_primary}; 
            }}
            QLabel {{ 
                color: {scheme.text_primary}; 
            }}
            QLineEdit {{
                background: {scheme.bg_tertiary};
                color: {scheme.text_primary};
                border: 1px solid {scheme.card_border};
                border-radius: 8px;
                padding: 0 12px;
                selection-background-color: {scheme.accent_color};
            }}
            QLineEdit:focus {{
                border: 1px solid {scheme.accent_color};
            }}
            QPushButton {{
                background: {scheme.button_bg};
                color: {scheme.text_primary};
                border: 1px solid {scheme.card_border};
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{ 
                background: {scheme.button_hover}; 
                border-color: {scheme.accent_color};
            }}
            QPushButton:default {{
                background: {scheme.accent_color};
                border-color: {scheme.accent_color};
                color: {scheme.bg_primary}; /* Contrast text on accent */
            }}
            QPushButton:default:hover {{
                background: {scheme.button_hover}; /* Or slightly lighter accent */
            }}
        """)
    def update_preview(self):
        """Update the avatar preview with current name and image."""
        self.avatar_preview.set_data(self.name or "?", self.image_path)

    def on_name_changed(self, text):
        self.name = text.strip()
        self.save_btn.setEnabled(bool(self.name))
        if not self.image_path:
            self.update_preview()

    def upload_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Profile Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.image_path = file_path
            self.update_preview()
            
    def get_data(self):
        return self.name, self.image_path


class ProfileManagerDialog(QDialog):
    """Grid of profiles for managing and selecting."""
    profile_selected = Signal(str) # Name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Switch Profile")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.manager = get_profile_manager()
        
        # Dynamic sizing will be set in refresh_grid
        self.setup_ui()
        self.refresh_grid()
        
    def setup_ui(self):
        # Apply dark theme with transparent backgrounds
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: {scheme.bg_primary}; color: {scheme.text_primary}; }}
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                width: 10px;
                background: {scheme.bg_primary};
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {scheme.card_border};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {scheme.accent_color};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        # Header - no background, just text
        header = QLabel("Who is typing?")
        header.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {scheme.text_primary}; background: transparent; border: none;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Grid Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_widget)
        # Add right margin for scrollbar spacing
        self.grid_layout.setContentsMargins(0, 0, 20, 0)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.scroll.setWidget(self.grid_widget)
        
        layout.addWidget(self.scroll)
        
        # Footer Actions
        footer = QHBoxLayout()
        self.create_btn = QPushButton("Create New Profile")
        self.create_btn.setIcon(get_icon("PLUS"))
        self.create_btn.setFixedSize(220, 44)
        self.create_btn.setCursor(Qt.PointingHandCursor)
        self.create_btn.clicked.connect(self.create_profile)
        self.create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {scheme.accent_color};
                color: {scheme.bg_primary}; /* Contrast */
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {scheme.button_hover};
            }}
        """)
        
        footer.addStretch()
        footer.addWidget(self.create_btn)
        footer.addStretch()
        layout.addLayout(footer)

    def refresh_grid(self):
        # Clear existing
        for i in reversed(range(self.grid_layout.count())): 
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
            
        profiles = self.manager.get_all_profiles()
        total_profiles = len(profiles)
        
        # 5 profiles per row
        cols = 5
        rows_needed = (total_profiles + cols - 1) // cols  # Ceiling division
        
        # Calculate dynamic dialog size
        # Base: 40 (top) + 30 (header) + 20 (spacing) + 44 (button) + 30 (bottom) = 164px
        # Each row: 200 (card height) + 20 (spacing) = 220px
        # Max 2 rows before scrolling (440px for cards)
        
        base_height = 164
        card_row_height = 220
        
        if rows_needed <= 2:
            # No scroll, fit exactly
            dialog_height = base_height + (rows_needed * card_row_height)
            self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            # Fixed height with scroll for 2 rows
            dialog_height = base_height + (2 * card_row_height)
            self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Width: 5 cards * 160px + 4 gaps * 20px + margins 80px + scrollbar space 20px = 1040px
        dialog_width = (cols * 160) + ((cols - 1) * 20) + 80 + 20
        
        self.setFixedSize(dialog_width, dialog_height)
        
        # Populate grid with centered incomplete rows
        for idx, p in enumerate(profiles):
            row = idx // cols
            col = idx % cols
            
            # Check if this is the last row and it's incomplete
            is_last_row = (row == rows_needed - 1)
            items_in_last_row = total_profiles % cols
            if items_in_last_row == 0:
                items_in_last_row = cols
            
            # Calculate column offset for centering incomplete rows
            col_offset = 0
            if is_last_row and items_in_last_row < cols:
                # Center the incomplete row
                col_offset = (cols - items_in_last_row) // 2
            
            card = ProfileCard(p["name"], p["image"], p["is_active"], total_profiles)
            # Card Click logic
            card.mousePressEvent = lambda e, name=p["name"]: self.on_card_clicked(name)
            
            # Action logic
            card.edit_clicked.connect(self.edit_profile)
            card.delete_clicked.connect(self.delete_profile)
            
            self.grid_layout.addWidget(card, row, col + col_offset)

    def on_card_clicked(self, name):
        self.profile_selected.emit(name)
        self.accept()

    def create_profile(self):
        dialog = ProfileEditDialog(parent=self)
        if dialog.exec():
            name, img = dialog.get_data()
            if not name: return
            
            # Uniqueness check
            existing = [p["name"].lower() for p in self.manager.get_all_profiles()]
            if name.lower() in existing:
                QMessageBox.warning(self, "Error", "Profile name already exists.")
                return
            
            if self.manager.create_profile(name, img):
                self.refresh_grid()
                
    def edit_profile(self, name):
        # Get current img
        profiles = self.manager.get_all_profiles()
        current_img = next((p["image"] for p in profiles if p["name"] == name), None)
        
        dialog = ProfileEditDialog(name, current_img, parent=self)
        
        if dialog.exec():
            new_name, new_img = dialog.get_data()
            if not new_name: return
            
            # Handle rename if changed
            final_name = name
            if new_name != name:
                # Uniqueness check
                existing = [p["name"].lower() for p in self.manager.get_all_profiles() if p["name"] != name]
                if new_name.lower() in existing:
                    QMessageBox.warning(self, "Error", "Profile name already exists.")
                    return
                
                if self.manager.rename_profile(name, new_name):
                    final_name = new_name
                else:
                    QMessageBox.warning(self, "Error", "Failed to rename profile.")
                    return

            # Update image if changed
            if new_img != current_img:
                self.manager.update_profile_image(final_name, new_img)
            
            self.refresh_grid()
            
    def delete_profile(self, name):
        total_profiles = len(self.manager.get_all_profiles())
        
        if total_profiles <= 1:
            QMessageBox.warning(self, "Warning", "Cannot delete the only remaining profile.")
            return

        reply = QMessageBox.question(self, "Delete Profile", 
                                     f"Are you sure you want to delete '{name}'?\nAll data will be lost.",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.manager.delete_profile(name):
                self.refresh_grid()
