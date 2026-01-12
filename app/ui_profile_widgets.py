import random
from PySide6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout, 
                               QPushButton, QFrame, QLayout)
from PySide6.QtCore import Qt, Signal, QSize, QPoint
from PySide6.QtGui import QPixmap, QPainter, QBrush, QColor, QPainterPath, QFont, QIcon

from app.ui_icons import get_icon

class AvatarGenerator:
    """Helper to generate avatar colors/initials."""
    COLORS = [
        "#FF5555", "#BD93F9", "#FF79C6", "#8BE9FD", 
        "#50FA7B", "#F1FA8C", "#FFB86C", "#6272A4"
    ]
    
    @staticmethod
    def get_color_for_name(name: str) -> str:
        # Consistent color hashing
        idx = sum(ord(c) for c in name) % len(AvatarGenerator.COLORS)
        return AvatarGenerator.COLORS[idx]

class ProfileAvatar(QWidget):
    def __init__(self, name: str, image_path: str = None, size: int = 32, parent=None):
        super().__init__(parent)
        self._name = name
        self._image_path = image_path
        self._size = size
        self.setFixedSize(size, size)
        
    def set_data(self, name: str, image_path: str = None):
        self._name = name
        self._image_path = image_path
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw circular mask
        path = QPainterPath()
        path.addEllipse(0, 0, self._size, self._size)
        painter.setClipPath(path)
        
        if self._image_path and self._image_path != "None": # Handle explicit string "None" just in case
            # Draw Image
            pixmap = QPixmap(self._image_path)
            if not pixmap.isNull():
                painter.drawPixmap(0, 0, self._size, self._size, pixmap.scaled(
                    self._size, self._size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                ))
                return

        # Fallback: Initials
        bg_color = QColor(AvatarGenerator.get_color_for_name(self._name))
        painter.fillRect(0, 0, self._size, self._size, bg_color)
        
        painter.setPen(Qt.white)
        font = QFont("Segoe UI", int(self._size * 0.45), QFont.Bold)
        painter.setFont(font)
        
        initial = self._name[0].upper() if self._name else "?"
        painter.drawText(self.rect(), Qt.AlignCenter, initial)


class ProfileTrigger(QWidget):
    """Pill-shaped trigger for the main window header."""
    clicked = Signal()
    
    def __init__(self, name: str, image_path: str = None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        
        self.layout = QHBoxLayout(self)
        # Margins: (Left, Top, Right, Bottom)
        # Tight margins for pill shape
        self.layout.setContentsMargins(6, 0, 14, 0)
        self.layout.setSpacing(8)
        self.layout.setSizeConstraint(QLayout.SetFixedSize)
        
        self.avatar = ProfileAvatar(name, image_path, size=28)
        self.layout.addWidget(self.avatar)
        
        self.name_label = QLabel(name)
        self.layout.addWidget(self.name_label)
        
        self.setObjectName("ProfileTrigger")
        self.apply_theme()
        
    def apply_theme(self):
        """Apply the current theme to the trigger widget."""
        from app.themes import get_color_scheme
        from app import settings
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)
        
        # Scale colors for hover effect manually or use scheme
        # We'll use border_color and apply opacity
        
        self.name_label.setStyleSheet(f"color: {scheme.text_primary}; font-weight: 600; font-size: 12px; border: none; background: transparent;")
        
        self._update_style(False)

    def _update_style(self, hovered: bool):
        """Update style based on hover state."""
        from app.themes import get_color_scheme
        from app import settings
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)
        
        if hovered:
            bg_color = scheme.button_hover
            border_color = scheme.accent_color
        else:
            # Semi-transparent background based on card_bg or similar? 
            # Or just use border
            bg_color = "rgba(127, 127, 127, 0.1)" # Generic transparent tint
            # Better: use scheme.card_bg with opacity if reachable, but simple tint is safer for "pill" look
            border_color = scheme.border_color
            
        self.setStyleSheet(f"""
            QWidget#ProfileTrigger {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 18px;
            }}
        """)
    
    def enterEvent(self, event):
        """Handle mouse enter for hover effect."""
        self._update_style(True)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave for hover effect."""
        self._update_style(False)
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse click."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
        
    def update_profile(self, name: str, image_path: str):
        self.avatar.set_data(name, image_path)
        self.name_label.setText(name)
        self.updateGeometry()


class ProfileCard(QFrame):
    """Card widget for the Profile Manager Grid."""
    edit_clicked = Signal(str)
    delete_clicked = Signal(str)
    
    
    def __init__(self, name: str, image_path: str = None, is_active: bool = False, total_profiles: int = 1, parent=None):
        super().__init__(parent)
        self._name = name
        self.setFixedSize(160, 200)
        self.setCursor(Qt.PointingHandCursor)
        
        self.setObjectName("ProfileCard")
        
        from app.themes import get_color_scheme
        from app import settings
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)
        
        # Flat design with subtle borders for visibility
        # Active profile gets a bright border, others get a subtle border
        if is_active:
            border_color = scheme.accent_color
            border_width = "2px"
        else:
            border_color = scheme.card_border
            border_width = "1px"
        
        self.setStyleSheet(f"""
            QFrame#ProfileCard {{
                background-color: transparent;
                border: {border_width} solid {border_color};
                border-radius: 12px;
            }}
            QFrame#ProfileCard:hover {{
                background-color: {scheme.button_hover};
                border: 2px solid {scheme.accent_color};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        
        # Large Avatar
        self.avatar = ProfileAvatar(name, image_path, size=80)
        layout.addWidget(self.avatar, 0, Qt.AlignHCenter)
        
        # Name (truncate if too long)
        display_name = name if len(name) <= 15 else name[:15] + "..."
        self.name_lbl = QLabel(display_name)
        self.name_lbl.setAlignment(Qt.AlignCenter)
        self.name_lbl.setWordWrap(True)
        self.name_lbl.setStyleSheet(f"color: {scheme.text_primary}; font-size: 14px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(self.name_lbl)
        
        layout.addStretch()
        
        # Action Buttons (Edit / Delete)
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(10)
        self.actions_layout.setAlignment(Qt.AlignCenter)
        
        self.edit_btn = QPushButton()
        self.edit_btn.setIcon(get_icon("EDIT"))
        self.edit_btn.setFixedSize(28, 28)
        self.edit_btn.setToolTip("Edit Profile")
        self.edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self._name))
        
        self.delete_btn = QPushButton()
        self.delete_btn.setIcon(get_icon("TRASH"))
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.setToolTip("Delete Profile")
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self._name))
        
        style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
            }
        """
        self.edit_btn.setStyleSheet(style)
        self.delete_btn.setStyleSheet(style)
        
        # Hide delete button if this is the only profile OR if it's the active profile
        if total_profiles <= 1 or is_active:
            self.delete_btn.setVisible(False)
            
        self.actions_layout.addWidget(self.edit_btn)
        self.actions_layout.addWidget(self.delete_btn)
        
        layout.addLayout(self.actions_layout)
        
    def mousePressEvent(self, event):
        # If clicked on buttons, let them handle it.
        # If clicked elsewhere, propagate to parent (Selector) for Selection
        child = self.childAt(event.pos())
        if child in (self.edit_btn, self.delete_btn):
            super().mousePressEvent(event)
        else:
            # Emit custom signal or let parent list widget handle item click
            # But we are in a Grid Layout, not ListWidget with items.
            # So we manually ignore or call parent?
            # Easiest: Parent listens to mousePress on this widget via event filter or subclassing.
            # Or better: "profile_selected.emit(name)"
            event.ignore() 
            # Ignoring allows the flow to go to parent? No, mouse events are tricky.
            # Let's add a signal for valid selection click
            pass

