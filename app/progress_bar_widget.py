"""Progress bar widget for typing progress visualization."""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen
from app import settings


class ProgressBarWidget(QWidget):
    """Visual progress bar showing typing completion percentage."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(8)  # Thin progress bar
        self.setMinimumWidth(200)
        
        self.progress = 0.0  # 0.0 to 1.0
        self.total_chars = 0
        self.current_pos = 0
    
    def set_progress(self, current_pos: int, total_chars: int):
        """Update progress based on current position and total characters."""
        self.current_pos = current_pos
        self.total_chars = total_chars
        
        if total_chars > 0:
            self.progress = min(1.0, current_pos / total_chars)
        else:
            self.progress = 0.0
        
        self.update()
    
    def reset(self):
        """Reset progress to zero."""
        self.progress = 0.0
        self.current_pos = 0
        self.total_chars = 0
        self.update()
    
    def paintEvent(self, event):
        """Draw the progress bar."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        
        # Background (unfilled portion)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#2a2a2a"))
        painter.drawRoundedRect(rect, 4, 4)
        
        # Filled portion (progress) - solid color from settings
        if self.progress > 0:
            filled_width = int(rect.width() * self.progress)
            filled_rect = rect.adjusted(0, 0, -(rect.width() - filled_width), 0)
            
            # Get progress bar color from settings
            progress_color = settings.get_setting("progress_bar_color", "#4CAF50")
            painter.setBrush(QColor(progress_color))
            painter.drawRoundedRect(filled_rect, 4, 4)
        
        # Optional: Border
        painter.setPen(QPen(QColor("#444444"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 4, 4)
        
        painter.end()
    
    def get_progress_text(self) -> str:
        """Get progress as percentage text."""
        percentage = int(self.progress * 100)
        return f"{percentage}%"
