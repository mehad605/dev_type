import logging
import os
import tempfile
from PySide6.QtWidgets import (QDialog, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                               QGridLayout, QScrollArea, QPushButton, QLineEdit,
                               QFileDialog, QMessageBox, QFrame, QSlider)
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QRect, QRectF, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QPen, QColor, QBrush, QFont, QLinearGradient, QDragEnterEvent, QDropEvent

from app.profile_manager import get_profile_manager
from app.ui_profile_widgets import ProfileCard, AvatarGenerator, ProfileAvatar
from app.ui_icons import get_icon
from app import settings
from app.themes import get_color_scheme

logger = logging.getLogger(__name__)


class ImageCropWidget(QWidget):
    """Modern widget for panning and zooming image with circular crop overlay."""
    
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.original_pixmap = pixmap
        self.zoom_factor = 1.0
        self.pan_offset = QPoint(0, 0)
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.is_hovered = False
        self._size_initialized = False

        self.setMouseTracking(True)
    
    def showEvent(self, event):
        """Initialize zoom when widget is first shown and has proper size."""
        super().showEvent(event)
        if not self._size_initialized:
            self._size_initialized = True
            self.reset_view()  # Set proper initial zoom

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Modern gradient background
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(30, 30, 35))
        gradient.setColorAt(1, QColor(20, 20, 25))
        painter.fillRect(self.rect(), gradient)

        if self.original_pixmap.isNull():
            # Draw placeholder text if no image
            painter.setPen(QColor(150, 150, 150))
            font = QFont("Segoe UI", 12)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "No image loaded")
            return

        # Calculate scaled image size
        scaled_width = int(self.original_pixmap.width() * self.zoom_factor)
        scaled_height = int(self.original_pixmap.height() * self.zoom_factor)

        # Calculate image position with pan offset
        center = QPoint(self.width() // 2, self.height() // 2)
        image_x = center.x() - scaled_width // 2 + self.pan_offset.x()
        image_y = center.y() - scaled_height // 2 + self.pan_offset.y()

        # Draw the scaled image
        scaled_pixmap = self.original_pixmap.scaled(
            scaled_width, scaled_height, 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        painter.drawPixmap(image_x, image_y, scaled_pixmap)

        # Draw darkened overlay outside circle
        center = QPoint(self.width() // 2, self.height() // 2)
        circle_radius = min(self.width(), self.height()) // 2 - 10

        # Create path for the overlay (everything except the circle)
        full_path = QPainterPath()
        full_path.addRect(self.rect())
        
        circle_path = QPainterPath()
        circle_path.addEllipse(center, circle_radius, circle_radius)
        
        overlay_path = full_path.subtracted(circle_path)
        painter.fillPath(overlay_path, QColor(0, 0, 0, 160))

        # Draw circle border with modern styling
        pen = QPen(QColor(255, 255, 255, 200), 3)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, circle_radius, circle_radius)

        # Draw subtle inner glow
        pen = QPen(QColor(255, 255, 255, 80), 1)
        painter.setPen(pen)
        painter.drawEllipse(center, circle_radius - 2, circle_radius - 2)

        # Draw zoom level indicator
        zoom_percentage = int(self.zoom_factor / self.max_zoom * 100)
        zoom_text = f"{zoom_percentage}%"
        
        painter.setPen(QColor(255, 255, 255, 180))
        font = QFont("Segoe UI", 11, QFont.Medium)
        painter.setFont(font)
        
        # Draw zoom text in bottom right
        text_rect = painter.fontMetrics().boundingRect(zoom_text)
        text_x = self.width() - text_rect.width() - 15
        text_y = self.height() - 15
        
        # Background for zoom text
        bg_rect = text_rect.adjusted(-8, -4, 8, 4)
        bg_rect.moveTopLeft(QPoint(text_x - 8, text_y - text_rect.height() - 4))
        painter.setBrush(QColor(0, 0, 0, 120))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bg_rect, 4, 4)
        
        painter.setPen(QColor(255, 255, 255, 200))
        painter.drawText(text_x, text_y, zoom_text)

        # Draw hint text when hovered
        if self.is_hovered:
            hint_text = "Drag to reposition • Scroll to zoom"
            painter.setPen(QColor(255, 255, 255, 150))
            font = QFont("Segoe UI", 10)
            painter.setFont(font)
            
            hint_rect = painter.fontMetrics().boundingRect(hint_text)
            hint_x = (self.width() - hint_rect.width()) // 2
            hint_y = 25
            
            # Background for hint
            bg_rect = hint_rect.adjusted(-10, -5, 10, 5)
            bg_rect.moveTopLeft(QPoint(hint_x - 10, hint_y - hint_rect.height() - 5))
            painter.setBrush(QColor(0, 0, 0, 140))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bg_rect, 6, 6)
            
            painter.setPen(QColor(255, 255, 255, 200))
            painter.drawText(hint_x, hint_y, hint_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

    @property
    def min_zoom(self):
        """Minimum zoom factor to ensure image fully covers the circle."""
        display_size = min(self.width(), self.height())
        circle_radius = display_size // 2 - 10
        circle_diameter = circle_radius * 2

        img_width = self.original_pixmap.width()
        img_height = self.original_pixmap.height()

        if img_width > 0 and img_height > 0:
            scale_x = circle_diameter / img_width
            scale_y = circle_diameter / img_height
            # Image must fully cover the circle (diameter x diameter square)
            return max(scale_x, scale_y)
        return 0.1

    def _constrain_offset(self, offset: QPoint) -> QPoint:
        """Constrain pan offset so image always covers the circle."""
        display_size = min(self.width(), self.height())
        radius = display_size // 2 - 10
        
        img_w = self.original_pixmap.width() * self.zoom_factor
        img_h = self.original_pixmap.height() * self.zoom_factor
        
        # We need the distance from center to image edge to be at least 'radius'
        # center_to_right_edge = img_w / 2 - offset_x
        # We need center_to_right_edge >= radius
        # => offset_x <= img_w / 2 - radius
        
        max_x = max(0, img_w / 2 - radius)
        max_y = max(0, img_h / 2 - radius)
        
        new_x = max(-max_x, min(max_x, offset.x()))
        new_y = max(-max_y, min(max_y, offset.y()))
        
        return QPoint(int(new_x), int(new_y))

    def mouseMoveEvent(self, event):
        if self.dragging:
            delta = event.pos() - self.drag_start_pos
            intended_offset = self.pan_offset + delta
            
            # Constrain the offset
            self.pan_offset = self._constrain_offset(intended_offset)
            
            self.drag_start_pos = event.pos()
            self.update()

    def wheelEvent(self, event):
        # Zoom in/out with mouse wheel
        zoom_delta = event.angleDelta().y() / 120.0
        zoom_factor = 1.0 + (zoom_delta * 0.15)

        new_zoom = self.zoom_factor * zoom_factor
        new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))

        if new_zoom != self.zoom_factor:
            mouse_pos = event.position().toPoint()
            center = QPoint(self.width() // 2, self.height() // 2)
            
            # Zoom towards mouse, but re-constrain
            zoom_center = mouse_pos - center
            zoom_ratio = new_zoom / self.zoom_factor
            
            new_pan = (self.pan_offset + zoom_center) * zoom_ratio - zoom_center
            
            # Apply new zoom first to calculate constraints correctly
            self.zoom_factor = new_zoom
            self.pan_offset = self._constrain_offset(new_pan)
            
            self.update()

    @property
    def max_zoom(self):
        return 5.0  # Increased max zoom to allow fine tuning

    @property
    def current_zoom_factor(self):
        return self.zoom_factor

    @property
    def current_pan_offset(self):
        return self.pan_offset


class ImageCropperDialog(QDialog):
    """Modern dialog for cropping profile images with circular overlay."""

    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crop Profile Picture")
        self.setFixedSize(460, 620)  # Adjusted for 400x400 image widget

        self.original_image_path = image_path
        self.cropped_image_path = None

        # Load original image
        self.original_pixmap = QPixmap(image_path)
        if self.original_pixmap.isNull():
            QMessageBox.warning(self, "Error", "Failed to load image.")
            self.reject()
            return

        # Validate image size
        max_size = 10 * 1024 * 1024  # 10MB
        file_size = os.path.getsize(image_path)
        if file_size > max_size:
            QMessageBox.warning(self, "Error", "Image file is too large. Please select an image under 10MB.")
            self.reject()
            return

        self.setup_ui()

    def setup_ui(self):
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title
        title = QLabel("Adjust Your Photo")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {scheme.text_primary};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Image display area - custom widget for pan/zoom
        self.image_widget = ImageCropWidget(self.original_pixmap, self)
        self.image_widget.setFixedSize(400, 400) # Reduced size to prevent layout collisions
        layout.addWidget(self.image_widget, alignment=Qt.AlignCenter)

        # Quick action buttons (below the image, not overlapping)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setIcon(get_icon("REFRESH"))
        self.reset_btn.setFixedHeight(40)
        self.reset_btn.setFixedWidth(100)
        self.reset_btn.clicked.connect(self.on_reset_clicked)
        self.reset_btn.setCursor(Qt.PointingHandCursor)

        self.fit_btn = QPushButton("Fit")
        self.fit_btn.setIcon(get_icon("MINIMIZE"))
        self.fit_btn.setFixedHeight(40)
        self.fit_btn.setFixedWidth(100)
        self.fit_btn.clicked.connect(self.on_fit_clicked)
        self.fit_btn.setCursor(Qt.PointingHandCursor)

        actions_layout.addStretch()
        actions_layout.addWidget(self.reset_btn)
        actions_layout.addWidget(self.fit_btn)
        actions_layout.addStretch()

        layout.addLayout(actions_layout)

        # Main action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(48)
        self.cancel_btn.setFixedWidth(120)
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)

        self.crop_btn = QPushButton("Apply")
        self.crop_btn.setFixedHeight(48)
        self.crop_btn.setFixedWidth(120)
        self.crop_btn.clicked.connect(self.accept)
        self.crop_btn.setDefault(True)
        self.crop_btn.setCursor(Qt.PointingHandCursor)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.crop_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Apply modern styling
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {scheme.bg_primary};
                color: {scheme.text_primary};
            }}
            QPushButton {{
                background: {scheme.button_bg};
                color: {scheme.text_primary};
                border: 1px solid {scheme.card_border};
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background: {scheme.button_hover};
                border-color: {scheme.accent_color};
            }}
            QPushButton:default {{
                background: {scheme.accent_color};
                border-color: {scheme.accent_color};
                color: {scheme.bg_primary};
            }}
            QPushButton:default:hover {{
                background: {scheme.button_hover};
            }}
        """)



    def on_reset_clicked(self):
        """Reset to default view (fill circle)."""
        self.image_widget.reset_view()

    def on_fit_clicked(self):
        """Fit entire image in circle."""
        self.image_widget.fit_to_circle()

    def accept(self):
        """Crop the image and save it."""
        try:
            # Create circular crop using current zoom/pan state
            cropped_pixmap = self.create_circular_crop()

            # Save to temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix='_profile_crop.png')
            os.close(temp_fd)  # Close the file descriptor

            if cropped_pixmap.save(temp_path, "PNG"):
                self.cropped_image_path = temp_path
                super().accept()
            else:
                QMessageBox.warning(self, "Error", "Failed to save cropped image.")
                self.reject()

        except Exception as e:
            logger.error(f"Failed to crop image: {e}")
            QMessageBox.warning(self, "Error", f"Failed to crop image: {str(e)}")
            self.reject()

    def create_circular_crop(self) -> QPixmap:
        """Create a circular crop of the image based on current zoom/pan state."""
        if not self.image_widget:
            return QPixmap()

        # Get the visible area within the circle
        widget_size = self.image_widget.size()
        center = QPoint(widget_size.width() // 2, widget_size.height() // 2)
        circle_radius = min(widget_size.width(), widget_size.height()) // 2 - 10

        # Calculate zoom and pan
        zoom = self.image_widget.current_zoom_factor
        pan = self.image_widget.current_pan_offset

        # Calculate where the scaled image is positioned in the widget
        scaled_width = int(self.original_pixmap.width() * zoom)
        scaled_height = int(self.original_pixmap.height() * zoom)
        image_x = center.x() - scaled_width // 2 + pan.x()
        image_y = center.y() - scaled_height // 2 + pan.y()

        # Circle center in scaled image coordinates
        circle_center_scaled_x = center.x() - image_x
        circle_center_scaled_y = center.y() - image_y

        # Circle center in original image coordinates
        center_world_x = circle_center_scaled_x / zoom
        center_world_y = circle_center_scaled_y / zoom

        # Circle radius in original image coordinates
        circle_world_radius = circle_radius / zoom

        # Define the crop rectangle (square that fits in circle)
        crop_size = int(circle_world_radius * 2)
        crop_x = int(center_world_x - circle_world_radius)
        crop_y = int(center_world_y - circle_world_radius)

        # Ensure crop rectangle is within image bounds
        crop_x = max(0, min(crop_x, self.original_pixmap.width() - crop_size))
        crop_y = max(0, min(crop_y, self.original_pixmap.height() - crop_size))
        crop_size = min(crop_size, self.original_pixmap.width() - crop_x, self.original_pixmap.height() - crop_y)

        if crop_size <= 0:
            # Fallback to center crop
            crop_size = min(self.original_pixmap.width(), self.original_pixmap.height())
            crop_x = (self.original_pixmap.width() - crop_size) // 2
            crop_y = (self.original_pixmap.height() - crop_size) // 2

        # Extract square crop
        cropped_pixmap = self.original_pixmap.copy(crop_x, crop_y, crop_size, crop_size)

        # Create circular mask
        circle_pixmap = QPixmap(crop_size, crop_size)
        circle_pixmap.fill(Qt.transparent)

        painter = QPainter(circle_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw circular mask
        path = QPainterPath()
        path.addEllipse(0, 0, crop_size, crop_size)
        painter.setClipPath(path)

        # Draw the cropped image
        painter.drawPixmap(0, 0, cropped_pixmap)

        painter.end()

        return circle_pixmap

    def get_cropped_image_path(self) -> str:
        """Get the path to the cropped image."""
        return self.cropped_image_path
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
            # Open cropper dialog
            cropper = ImageCropperDialog(file_path, self)
            if cropper.exec():
                self.image_path = cropper.get_cropped_image_path()
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
