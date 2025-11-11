"""Progress bar widget for typing progress visualization."""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen
from app import settings


class ProgressBarWidget(QWidget):
    """Visual progress bar showing typing completion percentage."""
    
    def __init__(self, parent=None, bar_type="user"):
        super().__init__(parent)
        self.setFixedHeight(12)  # Slightly taller for dual bars
        self.setMinimumWidth(220)
        self.bar_type = bar_type  # "user" or "ghost"

        self.progress = 0.0  # User progress
        self.ghost_progress = 0.0
        self.total_chars = 0
        self.current_pos = 0
        self.ghost_pos = 0
        self.display_ghost = False
    
    def set_progress(self, current_pos: int, total_chars: int, ghost_pos: int | None = None):
        """Update progress for user (and optionally ghost) positions."""
        self.current_pos = max(0, current_pos)
        self.total_chars = max(0, total_chars)

        if self.total_chars > 0:
            self.progress = min(1.0, self.current_pos / self.total_chars)
        else:
            self.progress = 0.0

        if ghost_pos is not None and self.total_chars > 0:
            self.display_ghost = True
            self.ghost_pos = max(0, min(ghost_pos, self.total_chars))
            self.ghost_progress = self.ghost_pos / self.total_chars
        elif ghost_pos is None and not self.display_ghost:
            self.ghost_pos = 0
            self.ghost_progress = 0.0

        if ghost_pos is None and self.display_ghost and self.total_chars == 0:
            self.ghost_pos = 0
            self.ghost_progress = 0.0

        if ghost_pos is None and not self.display_ghost:
            self.ghost_pos = 0
            self.ghost_progress = 0.0

        if ghost_pos is None and self.display_ghost and self.total_chars > 0:
            # Maintain ghost progress when display_ghost is already True
            self.ghost_pos = min(self.ghost_pos, self.total_chars)
            self.ghost_progress = self.ghost_pos / self.total_chars if self.total_chars else 0.0

        self.update()

    def show_ghost_progress(self, enabled: bool):
        """Explicitly control whether the ghost overlay is displayed."""
        self.display_ghost = enabled
        if not enabled:
            self.ghost_pos = 0
            self.ghost_progress = 0.0
        self.update()

    def reset(self):
        """Reset progress to zero."""
        self.progress = 0.0
        self.ghost_progress = 0.0
        self.current_pos = 0
        self.ghost_pos = 0
        self.total_chars = 0
        self.display_ghost = False
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
        
        # Filled portion(s)
        if self.bar_type == "ghost":
            # Ghost bar uses ghost color
            progress_color = settings.get_setting("ghost_progress_bar_color", "#8AB4F8")
        else:
            # User bar uses user/progress color
            progress_color = settings.get_setting("user_progress_bar_color", None)
            if not progress_color:
                progress_color = settings.get_setting("progress_bar_color", "#4CAF50")

        ghost_color_value = settings.get_setting("ghost_progress_bar_color", "#8AB4F8")
        ghost_color = QColor(ghost_color_value)
        ghost_color.setAlpha(170)

        if self.display_ghost and self.ghost_progress > 0:
            ghost_width = int(rect.width() * min(1.0, self.ghost_progress))
            ghost_rect = rect.adjusted(0, 1, -(rect.width() - ghost_width), -1)
            painter.setBrush(ghost_color)
            painter.drawRoundedRect(ghost_rect, 4, 4)

        if self.progress > 0:
            filled_width = int(rect.width() * min(1.0, self.progress))
            filled_rect = rect.adjusted(0, 0, -(rect.width() - filled_width), 0)
            painter.setBrush(QColor(progress_color))
            painter.drawRoundedRect(filled_rect, 4, 4)
        
        # Optional: Border
        painter.setPen(QPen(QColor("#444444"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 4, 4)
        
        painter.end()
    
    def get_progress_text(self) -> str:
        """Get progress as percentage text."""
        user_pct = int(self.progress * 100)
        if self.display_ghost:
            ghost_pct = int(self.ghost_progress * 100)
            return f"You {user_pct}% | Ghost {ghost_pct}%"
        return f"{user_pct}%"
