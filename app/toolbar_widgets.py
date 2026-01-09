"""Custom styled widgets for the editor toolbar."""
from PySide6.QtWidgets import QPushButton, QToolTip
from PySide6.QtCore import Qt, QPoint, QRect, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QCursor, QPainterPath

from app import settings

class ToolbarButton(QPushButton):
    """Base class for custom painted toolbar buttons."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 34)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self._hover = False
        self._scheme = None
        self._update_colors()

    def _update_colors(self):
        """Get current theme colors."""
        from app.themes import get_color_scheme
        theme = settings.get_setting("theme", settings.get_default("theme"))
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        self._scheme = get_color_scheme(theme, scheme_name)
    
    def enterEvent(self, event):
        self._hover = True
        self._update_colors()
        self.update()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)
        
    def paintEvent(self, event):
        """Draw common background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        if self._hover and self.isEnabled():
            bg_color = QColor(self._scheme.bg_tertiary)
            bg_color.setAlpha(150)
            painter.setBrush(bg_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(self.rect(), 6, 6)
            
        elif self.isChecked():
            # Active background for toggle buttons
            bg_color = QColor(self._scheme.bg_tertiary)
            bg_color.setAlpha(80)
            painter.setBrush(bg_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(self.rect(), 6, 6)

    def get_icon_color(self):
        """Get standardized icon color based on state."""
        if not self.isEnabled():
            c = QColor(self._scheme.text_primary)
            c.setAlpha(50)
            return c
        
        if self.isChecked():
            return QColor(self._scheme.accent_color)
            
        if self._hover:
            return QColor(self._scheme.text_primary)
            
        c = QColor(self._scheme.text_primary)
        c.setAlpha(180)
        return c


class GhostButton(ToolbarButton):
    """A professional looking ghost replay button."""
    
    def paintEvent(self, event):
        # Draw background
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw Ghost Icon
        color = self.get_icon_color()
        painter.setPen(QPen(color, 1.5))
        painter.setBrush(Qt.NoBrush)
        
        rect = self.rect()
        c = rect.center()
        
        # Ghost body path
        path = QPainterPath()
        
        # Head (arc)
        w = 14
        h = 16
        x = c.x() - w/2
        y = c.y() - h/2
        
        path.moveTo(x, y + h) # Bottom left
        path.lineTo(x, y + h/2) # Up to start of head
        path.arcTo(x, y, w, w, 180, 180) # Top dome
        path.lineTo(x + w, y + h) # Down to bottom right
        
        # Bottom wavy line
        wave_h = 2
        path.lineTo(x + w - w/3, y + h - wave_h)
        path.lineTo(x + w - 2*w/3, y + h)
        path.lineTo(x, y + h - wave_h)
        
        painter.drawPath(path)
        
        # Eyes
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        eye_size = 2.5
        painter.drawEllipse(QPoint(int(c.x() - 3), int(c.y() - 1)), eye_size/2, eye_size/2)
        painter.drawEllipse(QPoint(int(c.x() + 3), int(c.y() - 1)), eye_size/2, eye_size/2)
        
        painter.end()


class InstantDeathButton(ToolbarButton):
    """A professional looking skull/danger toggle button."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        
    def get_icon_color(self):
        """Override color for instant death (red alert)."""
        if not self.isEnabled():
            return super().get_icon_color()
            
        if self.isChecked():
            # Red/Orange warning color
             return QColor("#bf616a") # Nord Red-ish
            
        if self._hover:
             return QColor(self._scheme.text_primary) # Hover is white
             
        return super().get_icon_color()

    def paintEvent(self, event):
        # Draw background
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        color = self.get_icon_color()
        painter.setPen(QPen(color, 1.5))
        painter.setBrush(Qt.NoBrush)
        
        rect = self.rect()
        c = rect.center()
        
        # Draw Skull-like geometric shape
        
        # Cranium
        w = 14
        h = 10
        x = c.x() - w/2
        y = c.y() - 6
        
        painter.drawRoundedRect(x, y, w, h, 6, 6)
        
        # Jaw
        jaw_w = 8
        jaw_h = 5
        jaw_x = c.x() - jaw_w/2
        jaw_y = y + h - 1
        
        painter.drawRoundedRect(jaw_x, jaw_y, jaw_w, jaw_h, 2, 2)
        
        # Eyes (X shape or holes)
        if self.isChecked():
            # Angry/Dead eyes (X)
            eye_sz = 3
            # Left Eye
            ex, ey = c.x() - 3, c.y() - 2
            painter.drawLine(ex - 1.5, ey - 1.5, ex + 1.5, ey + 1.5)
            painter.drawLine(ex - 1.5, ey + 1.5, ex + 1.5, ey - 1.5)
            # Right Eye
            ex, ey = c.x() + 3, c.y() - 2
            painter.drawLine(ex - 1.5, ey - 1.5, ex + 1.5, ey + 1.5)
            painter.drawLine(ex - 1.5, ey + 1.5, ex + 1.5, ey - 1.5)
        else:
            # Normal sockets
            painter.setBrush(color) # Fill eyes
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(int(c.x() - 3.5), int(c.y() - 2)), 1.5, 1.5)
            painter.drawEllipse(QPoint(int(c.x() + 3.5), int(c.y() - 2)), 1.5, 1.5)
            
        painter.end()
