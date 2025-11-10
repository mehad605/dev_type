"""Custom sound volume widget with visual volume indicator."""
from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QCursor
from app import settings


class SoundVolumeWidget(QWidget):
    """Visual sound volume control with icon, hover tooltip, and scroll adjustment."""
    
    volume_changed = Signal(int)  # Emits volume (0-100)
    enabled_changed = Signal(bool)  # Emits when toggled on/off
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)  # Back to 40x40, no text below
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        
        # Load initial state from settings
        self.volume = int(settings.get_setting("sound_volume", "50"))
        self.enabled = settings.get_setting("sound_enabled", "1") == "1"
        
        # Visual properties
        self.hover = False
    
    def set_volume(self, volume: int):
        """Set volume (0-100)."""
        self.volume = max(0, min(100, volume))
        self.update()
    
    def set_enabled(self, enabled: bool):
        """Set enabled state."""
        self.enabled = enabled
        self.update()
    
    def paintEvent(self, event):
        """Draw the volume icon with fill indicator (Windows-style)."""
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
        except:
            pass
        
        # Icon area
        rect = self.rect().adjusted(5, 5, -5, -5)
        
        if self.enabled:
            # Draw speaker icon (Windows style)
            base_color = QColor("#ffffff" if self.hover else "#cccccc")
            painter.setPen(Qt.NoPen)
            painter.setBrush(base_color)
            
            # Speaker cone (small rectangle)
            cone_rect = QRect(rect.left() + 2, rect.center().y() - 3, 6, 6)
            painter.drawRect(cone_rect)
            
            # Speaker horn (triangle pointing right)
            horn_points = [
                QPoint(cone_rect.right(), cone_rect.top()),
                QPoint(cone_rect.right() + 6, rect.center().y() - 8),
                QPoint(cone_rect.right() + 6, rect.center().y() + 8),
                QPoint(cone_rect.right(), cone_rect.bottom())
            ]
            painter.drawPolygon(horn_points)
            
            # Sound waves (3 single curved lines) - Windows style
            volume_ratio = self.volume / 100.0
            wave_base_x = rect.left() + 16
            
            painter.setBrush(Qt.NoBrush)
            
            # Calculate which waves to show based on volume
            num_waves = 3
            for i in range(num_waves):
                # Determine if this wave should be lit
                wave_threshold = (i + 1) / num_waves
                if volume_ratio >= wave_threshold - 0.05:
                    wave_color = QColor("#4CAF50")  # Green
                else:
                    wave_color = QColor("#444444")  # Dark
                
                painter.setPen(QPen(wave_color, 2, Qt.SolidLine, Qt.RoundCap))
                
                # Draw single curved arc (parenthesis style)
                arc_x = wave_base_x + (i * 4)
                arc_size = 6 + (i * 3)
                
                # Single arc covering top to bottom
                painter.drawArc(
                    arc_x - 2,
                    rect.center().y() - arc_size,
                    arc_size,
                    arc_size * 2,
                    -90 * 16,  # start angle (left side)
                    180 * 16   # span angle (180 degrees = half circle)
                )
        else:
            # Draw muted icon (Windows style)
            muted_color = QColor("#ff4444")
            painter.setPen(Qt.NoPen)
            painter.setBrush(muted_color)
            
            # Speaker cone (small rectangle)
            cone_rect = QRect(rect.left() + 2, rect.center().y() - 3, 6, 6)
            painter.drawRect(cone_rect)
            
            # Speaker horn (triangle pointing right)
            horn_points = [
                QPoint(cone_rect.right(), cone_rect.top()),
                QPoint(cone_rect.right() + 6, rect.center().y() - 8),
                QPoint(cone_rect.right() + 6, rect.center().y() + 8),
                QPoint(cone_rect.right(), cone_rect.bottom())
            ]
            painter.drawPolygon(horn_points)
            
            # Draw X to indicate muted (like Windows)
            painter.setPen(QPen(muted_color, 2.5, Qt.SolidLine, Qt.RoundCap))
            painter.setBrush(Qt.NoBrush)
            
            x_center = rect.left() + 22
            y_center = rect.center().y()
            x_size = 6
            
            painter.drawLine(x_center - x_size, y_center - x_size, 
                           x_center + x_size, y_center + x_size)
            painter.drawLine(x_center - x_size, y_center + x_size, 
                           x_center + x_size, y_center - x_size)
        
        try:
            painter.end()
        except:
            pass
    
    def enterEvent(self, event):
        """Show tooltip on hover."""
        self.hover = True
        try:
            if self.enabled:
                QToolTip.showText(
                    QCursor.pos(),
                    f"Volume: {self.volume}%",
                    self
                )
            else:
                QToolTip.showText(
                    QCursor.pos(),
                    "Sound Muted",
                    self
                )
        except Exception as e:
            print(f"[SoundVolumeWidget] Error in enterEvent: {e}")
        self.update()
    
    def leaveEvent(self, event):
        """Hide tooltip."""
        self.hover = False
        try:
            QToolTip.hideText()
        except Exception as e:
            print(f"[SoundVolumeWidget] Error in leaveEvent: {e}")
        self.update()
    
    def wheelEvent(self, event):
        """Adjust volume with mouse wheel."""
        if not self.enabled:
            return
        
        delta = event.angleDelta().y()
        change = 5 if delta > 0 else -5
        new_volume = max(0, min(100, self.volume + change))
        
        if new_volume != self.volume:
            self.volume = new_volume
            self.volume_changed.emit(self.volume)
            
            # Update tooltip with just the volume
            QToolTip.showText(
                QCursor.pos(),
                f"Volume: {self.volume}%",
                self
            )
            
            self.update()
    
    def mouseDoubleClickEvent(self, event):
        """Toggle enabled/disabled on double-click."""
        if event.button() == Qt.LeftButton:
            self.enabled = not self.enabled
            self.enabled_changed.emit(self.enabled)
            
            # Update tooltip
            if self.enabled:
                QToolTip.showText(
                    QCursor.pos(),
                    f"Volume: {self.volume}%",
                    self
                )
            else:
                QToolTip.showText(
                    QCursor.pos(),
                    "Sound Muted",
                    self
                )
            
            self.update()
