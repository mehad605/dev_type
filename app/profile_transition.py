from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPainterPath

from app.ui_profile_widgets import ProfileAvatar
from app.themes import get_color_scheme
import app.settings as settings

class ProfileTransitionOverlay(QWidget):
    """
    Layer 3: The Loading Overlay.
    Displays target username, avatar, and a circular progress ring animation.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False) # Block interaction
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.hide()
        
        # State
        self.target_name = ""
        self.target_image = None
        self._progress = 0.0 # 0.0 to 1.0
        
        # Animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_progress)
        self._anim_duration = 1600 # ms (approx 1.5-2s)
        self._start_time = 0
        
        # Callback
        self._on_finished = None
        
        # UI Elements (Avatar is complex to draw manually with widget inside paintEvent of overlay? 
        # Easier to just have widgets centered in a layout)
        
        # Layout for centering content
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        
        # We can use a container for the avatar/text to easily center them, 
        # and draw the ring in paintEvent relative to them or just screen center.
        # Let's just draw everything in paintEvent for "High-Fidelity" control over the ring z-pos vs avatar.
        
        # Actually, using widgets for Avatar and Text is easier for styling/rendering.
        # The ring needs to be drawn.
        # Let's put a custom widget in the center that handles drawing the ring + holding the avatar.
        
        self.center_widget = LoadingCenterWidget(self)
        layout.addWidget(self.center_widget)
        
    def start_transition(self, name: str, image_path: str, on_finished):
        """Start the transition animation."""
        self.target_name = name
        self.target_image = image_path
        self._on_finished = on_finished
        
        # Setup center widget
        self.center_widget.set_data(name, image_path)
        
        # Reset
        self._progress = 0.0
        self.show()
        self.raise_()
        
        # Start Animation
        import time
        self._start_time = time.time() * 1000
        self.timer.start(16) # ~60 FPS
        
    def _update_progress(self):
        import time
        current_time = time.time() * 1000
        elapsed = current_time - self._start_time
        
        if elapsed >= self._anim_duration:
            self._progress = 1.0
            self.timer.stop()
            self.center_widget.set_progress(1.0)
            if self._on_finished:
                self._on_finished()
        else:
            # Easing?
            # Linear for progress ring is usually fine, or slight EaseOut
            t = elapsed / self._anim_duration
            # EaseOutQuad
            self._progress = t * (2 - t)
            self.center_widget.set_progress(self._progress)

class LoadingCenterWidget(QWidget):
    """Widget to draw the avatar, text, and progress ring."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 300)
        
        self._name = ""
        self._image_path = None
        self._progress = 0.0
        
        # Internal Avatar Widget
        self.avatar_widget = ProfileAvatar("", None, size=120, parent=self)
        self.avatar_widget.move(90, 60) # Center horizontally (300-120)/2 = 90
        
        # Text Label
        self.name_label = QLabel(self)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setGeometry(0, 200, 300, 40)
        self.name_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold; background: transparent;")
        
    def set_data(self, name, image_path):
        self._name = name
        self._image_path = image_path
        self.avatar_widget.set_data(name, image_path)
        self.name_label.setText(name)
        
        # Update colors based on theme
        scheme_name = settings.get_setting("dark_scheme", "dracula")
        self.scheme = get_color_scheme("dark", scheme_name)
        self.name_label.setStyleSheet(f"color: {self.scheme.text_primary}; font-size: 24px; font-weight: bold; background: transparent;")
        
    def set_progress(self, p):
        self._progress = p
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw Progress Ring around Avatar
        # Avatar is at (90, 60) size 120x120. Center is (150, 120).
        # Ring radius should be slightly larger, e.g. 70px radius (140px diameter)
        
        center_x, center_y = 150, 120
        radius = 75
        
        # Track (Background ring)
        pen_track = QPen(QColor(self.scheme.accent_color))
        pen_track.setWidth(6)
        color_track = QColor(self.scheme.accent_color)
        color_track.setAlpha(50) # Semi-transparent
        pen_track.setColor(color_track)
        pen_track.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_track)
        painter.drawEllipse(QPoint(center_x, center_y), radius, radius)
        
        # Progress Arc
        if self._progress > 0:
            pen = QPen(QColor(self.scheme.accent_color))
            pen.setWidth(6)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            
            # drawArc uses 1/16th of a degree
            # Start at 90 degrees (12 o'clock) = 90 * 16
            # Positive span is counter-clockwise, so we want negative span for clockwise
            start_angle = 90 * 16 
            span_angle = - (self._progress * 360 * 16)
            
            rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
            painter.drawArc(rect, int(start_angle), int(span_angle))
