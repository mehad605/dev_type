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

        # User progress
        if self.total_chars > 0:
            self.progress = min(1.0, self.current_pos / self.total_chars)
        else:
            self.progress = 0.0

        # Ghost progress - clean 3-branch logic
        if ghost_pos is not None:
            # Explicit ghost position provided - enable and update
            self.display_ghost = True
            self.ghost_pos = max(0, min(ghost_pos, self.total_chars)) if self.total_chars > 0 else 0
            self.ghost_progress = self.ghost_pos / self.total_chars if self.total_chars > 0 else 0.0
        elif self.display_ghost and self.total_chars > 0:
            # Ghost enabled but no new position - maintain current (clamp to valid range)
            self.ghost_pos = min(self.ghost_pos, self.total_chars)
            self.ghost_progress = self.ghost_pos / self.total_chars
        else:
            # Ghost disabled or no content - reset
            self.ghost_pos = 0
            self.ghost_progress = 0.0

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
        """Draw the progress bar with glow effect."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        
        # Background (unfilled portion)
        painter.setPen(Qt.NoPen)
        # Use a semi-transparent dark background
        painter.setBrush(QColor(0, 0, 0, 60))
        painter.drawRoundedRect(rect, 6, 6)
        
        # Determine colors
        if self.bar_type == "ghost":
            # Ghost bar uses ghost color
            base_color_hex = settings.get_setting("ghost_progress_bar_color", settings.get_default("ghost_progress_bar_color"))
        else:
            # User bar uses user/progress color
            base_color_hex = settings.get_setting("user_progress_bar_color", None)
            if not base_color_hex:
                base_color_hex = settings.get_setting("progress_bar_color", settings.get_default("progress_bar_color"))

        base_color = QColor(base_color_hex)
        
        # Draw Outline
        outline_color = QColor(base_color)
        outline_color.setAlpha(100)
        painter.setPen(QPen(outline_color, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 6, 6)
        
        # Draw Ghost Bar (if visible)
        if self.display_ghost and self.ghost_progress > 0:
            ghost_color_hex = settings.get_setting("ghost_progress_bar_color", "#8AB4F8")
            ghost_color = QColor(ghost_color_hex)
            ghost_color.setAlpha(100)  # More transparent
            
            ghost_width = int(rect.width() * min(1.0, self.ghost_progress))
            if ghost_width > 0:
                ghost_rect = rect.adjusted(0, 0, -(rect.width() - ghost_width), 0)
                painter.setBrush(ghost_color)
                painter.drawRoundedRect(ghost_rect, 6, 6)

        # Draw User Bar
        if self.progress > 0:
            filled_width = int(rect.width() * min(1.0, self.progress))
            if filled_width > 0:
                filled_rect = rect.adjusted(0, 0, -(rect.width() - filled_width), 0)
                
                # Create gradient for glow effect
                from PySide6.QtGui import QLinearGradient
                gradient = QLinearGradient(filled_rect.topLeft(), filled_rect.bottomLeft())
                gradient.setColorAt(0, base_color.lighter(130))
                gradient.setColorAt(1, base_color)
                
                painter.setBrush(gradient)
                painter.drawRoundedRect(filled_rect, 6, 6)
                
                # Add a subtle glow at the end
                if filled_width > 10:
                    glow_rect = filled_rect.adjusted(filled_width - 10, 0, 0, 0)
                    glow_gradient = QLinearGradient(glow_rect.topLeft(), glow_rect.topRight())
                    glow_gradient.setColorAt(0, QColor(255, 255, 255, 0))
                    glow_gradient.setColorAt(1, QColor(255, 255, 255, 100))
                    painter.setBrush(glow_gradient)
                    painter.drawRoundedRect(filled_rect, 6, 6) # Re-draw to clip glow to rounded rect
        
        painter.end()
    
    def get_progress_text(self) -> str:
        """Get progress as percentage text."""
        user_pct = int(self.progress * 100)
        if self.display_ghost:
            ghost_pct = int(self.ghost_progress * 100)
            return f"You {user_pct}% | Ghost {ghost_pct}%"
        return f"{user_pct}%"
