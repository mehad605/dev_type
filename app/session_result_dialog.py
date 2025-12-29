"""
Modern session result dialog matching the specific 'Neon' design.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QWidget, QGraphicsDropShadowEffect, QToolTip
)
from PySide6.QtCore import Qt, QRectF, QPointF, QPoint
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush, QFont, QPixmap, QFontMetrics
from pathlib import Path
from typing import List, Dict, Tuple


class InteractiveWPMGraph(QWidget):
    """Interactive WPM vs Time graph widget with hover tooltips."""
    
    def __init__(self, times: List[float], wpms: List[float], total_time: float, 
                 line_color: str, theme_colors: dict, parent=None):
        super().__init__(parent)
        self.line_color = QColor(line_color)
        self.theme = theme_colors or {}
        
        # Round total time to whole seconds
        self.total_time = max(1, int(total_time) if total_time == int(total_time) else int(total_time) + 1)
        
        # Data is already in (second, wpm) format - use directly as markers
        # times and wpms are parallel lists
        self.second_markers = [(int(t), w) for t, w in zip(times, wpms) if t >= 1]
        
        # Graph margins
        self.margin_left = 45
        self.margin_right = 15
        self.margin_top = 25
        self.margin_bottom = 30
        
        # Mouse tracking
        self.setMouseTracking(True)
        self.hover_second = None  # Which second marker is hovered
        
        # Calculate axis ranges - start from 1 second, end at total_time
        self.x_min = 1
        self.x_max = max(self.total_time, max((s for s, _ in self.second_markers), default=1))
        
        # Calculate y-axis max - ALWAYS next multiple of 10 above max WPM
        if self.second_markers:
            max_wpm = max(wpm for _, wpm in self.second_markers)
        else:
            max_wpm = 100
        
        # Round up to next 10
        self.y_max = ((int(max_wpm) // 10) + 1) * 10
        
        # Dynamic y-step based on range
        if self.y_max <= 50:
            self.y_step = 10
        elif self.y_max <= 100:
            self.y_step = 20
        elif self.y_max <= 200:
            self.y_step = 50
        else:
            self.y_step = 100
        
        # Calculate x-axis step dynamically
        duration = self.x_max - self.x_min
        if duration <= 5:
            self.x_step = 1
        elif duration <= 15:
            self.x_step = 2
        elif duration <= 30:
            self.x_step = 5
        else:
            self.x_step = 10
        
        self.setFixedSize(500, 180)
        self.setStyleSheet("background: transparent;")
    
    def _graph_rect(self) -> QRectF:
        """Get the rectangle area for the graph (excluding margins)."""
        return QRectF(
            self.margin_left,
            self.margin_top,
            self.width() - self.margin_left - self.margin_right,
            self.height() - self.margin_top - self.margin_bottom
        )
    
    def _time_to_x(self, time_sec: float) -> float:
        """Convert time to x coordinate."""
        rect = self._graph_rect()
        # Map from [x_min, x_max] to graph width
        normalized = (time_sec - self.x_min) / (self.x_max - self.x_min) if self.x_max > self.x_min else 0
        return rect.x() + normalized * rect.width()
    
    def _wpm_to_y(self, wpm: float) -> float:
        """Convert WPM to y coordinate."""
        rect = self._graph_rect()
        return rect.y() + rect.height() - (wpm / self.y_max) * rect.height()
    
    def _find_hovered_marker(self, x: float, y: float) -> int:
        """Find which second marker is being hovered, if any."""
        for second, wpm in self.second_markers:
            marker_x = self._time_to_x(second)
            marker_y = self._wpm_to_y(wpm)
            
            # Check if mouse is within 10 pixels of marker
            if abs(x - marker_x) < 12 and abs(y - marker_y) < 12:
                return second
        return None
    
    def mouseMoveEvent(self, event):
        """Track mouse position and update hover info."""
        x = event.position().x()
        y = event.position().y()
        self.hover_second = self._find_hovered_marker(x, y)
        self.update()
    
    def leaveEvent(self, event):
        """Clear hover when mouse leaves."""
        self.hover_second = None
        self.update()
    
    def paintEvent(self, event):
        """Draw the interactive graph."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Colors
        bg_color = QColor(self.theme.get('bg', '#18181b'))
        text_color = QColor(self.theme.get('text', '#ffffff'))
        grid_color = QColor(self.theme.get('text_secondary', '#444444'))
        
        rect = self._graph_rect()
        
        # Draw background
        painter.fillRect(self.rect(), bg_color)
        
        # Draw grid lines
        grid_color.setAlpha(50)
        painter.setPen(QPen(grid_color, 1))
        
        # Horizontal grid lines (WPM) - dynamic spacing
        for wpm in range(0, self.y_max + 1, self.y_step):
            y = self._wpm_to_y(wpm)
            painter.drawLine(QPointF(rect.x(), y), QPointF(rect.x() + rect.width(), y))
        
        # Vertical grid lines - dynamic spacing
        t = self.x_min
        while t <= self.x_max:
            x = self._time_to_x(t)
            painter.drawLine(QPointF(x, rect.y()), QPointF(x, rect.y() + rect.height()))
            t += self.x_step
        
        # Draw axes border
        grid_color.setAlpha(150)
        painter.setPen(QPen(grid_color, 1))
        painter.drawRect(rect)
        
        # Draw axis labels
        painter.setPen(text_color)
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        
        # Y-axis labels - dynamic spacing
        for wpm in range(0, self.y_max + 1, self.y_step):
            y = self._wpm_to_y(wpm)
            painter.drawText(QRectF(0, y - 8, self.margin_left - 5, 16), 
                           Qt.AlignRight | Qt.AlignVCenter, str(wpm))
        
        # X-axis labels - dynamic spacing (whole seconds only)
        t = self.x_min
        while t <= self.x_max:
            x = self._time_to_x(t)
            painter.drawText(QRectF(x - 15, rect.y() + rect.height() + 2, 30, 20), 
                           Qt.AlignCenter, f"{int(t)}")
            t += self.x_step
        
        # Axis titles
        font.setPointSize(9)
        painter.setFont(font)
        
        # Y-axis title (rotated)
        painter.save()
        painter.translate(12, rect.y() + rect.height() / 2)
        painter.rotate(-90)
        painter.drawText(QRectF(-30, -10, 60, 20), Qt.AlignCenter, "WPM")
        painter.restore()
        
        # X-axis title
        painter.drawText(QRectF(rect.x(), self.height() - 15, rect.width(), 15), 
                        Qt.AlignCenter, "Time (seconds)")
        
        # Draw the WPM curve connecting the second markers (smooth line through whole seconds only)
        if len(self.second_markers) >= 2:
            path = QPainterPath()
            first_sec, first_wpm = self.second_markers[0]
            path.moveTo(self._time_to_x(first_sec), self._wpm_to_y(first_wpm))
            
            for sec, wpm in self.second_markers[1:]:
                path.lineTo(self._time_to_x(sec), self._wpm_to_y(wpm))
            
            painter.setPen(QPen(self.line_color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
        
        # Draw second markers (interactive dots)
        for second, wpm in self.second_markers:
            marker_x = self._time_to_x(second)
            marker_y = self._wpm_to_y(wpm)
            
            is_hovered = (self.hover_second == second)
            
            # Draw dot
            if is_hovered:
                painter.setPen(QPen(self.line_color, 2))
                painter.setBrush(QBrush(self.line_color))
                painter.drawEllipse(QPointF(marker_x, marker_y), 5, 5)
            else:
                painter.setPen(QPen(self.line_color, 1))
                painter.setBrush(QBrush(bg_color))
                painter.drawEllipse(QPointF(marker_x, marker_y), 3, 3)
        
        # Draw tooltip for hovered marker
        if self.hover_second is not None:
            # Find the WPM for this second
            hover_wpm = None
            for sec, wpm in self.second_markers:
                if sec == self.hover_second:
                    hover_wpm = wpm
                    break
            
            if hover_wpm is not None:
                dot_x = self._time_to_x(self.hover_second)
                dot_y = self._wpm_to_y(hover_wpm)
                
                # Tooltip text
                tooltip_text = f"{self.hover_second}s | {hover_wpm:.1f} WPM"
                font.setPointSize(9)
                font.setBold(True)
                painter.setFont(font)
                fm = QFontMetrics(font)
                text_width = fm.horizontalAdvance(tooltip_text)
                text_height = fm.height()
                
                tooltip_x = dot_x + 10
                tooltip_y = dot_y - 25
                
                # Keep tooltip on screen
                if tooltip_x + text_width + 10 > self.width():
                    tooltip_x = dot_x - text_width - 20
                if tooltip_y < 5:
                    tooltip_y = dot_y + 10
                
                # Draw tooltip background
                tooltip_rect = QRectF(tooltip_x, tooltip_y, text_width + 10, text_height + 6)
                painter.setPen(Qt.NoPen)
                tooltip_bg = QColor(bg_color)
                tooltip_bg.setAlpha(230)
                painter.setBrush(tooltip_bg)
                painter.drawRoundedRect(tooltip_rect, 4, 4)
                
                # Draw tooltip border
                painter.setPen(QPen(self.line_color, 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(tooltip_rect, 4, 4)
                
                # Draw tooltip text
                painter.setPen(text_color)
                painter.drawText(tooltip_rect, Qt.AlignCenter, tooltip_text)
        
        # Draw legend
        legend_x = rect.x() + 10
        legend_y = rect.y() + 5
        
        painter.setPen(QPen(self.line_color, 2))
        painter.drawLine(QPointF(legend_x, legend_y + 6), QPointF(legend_x + 20, legend_y + 6))
        
        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(text_color)
        painter.drawText(QPointF(legend_x + 25, legend_y + 10), "Your WPM")


class IconWidget(QWidget):
    """Custom widget to draw simple vector icons."""
    def __init__(self, icon_type, color, size=24, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.color = QColor(color)
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        painter.translate(w/2, h/2)
        scale = min(w, h) / 24.0
        painter.scale(scale, scale)
        
        pen = QPen(self.color, 2)
        painter.setPen(pen)
        
        if self.icon_type == 'user':
            # Head
            painter.drawEllipse(QPointF(0, -4), 4, 4)
            # Body
            path = QPainterPath()
            path.arcMoveTo(-8, 12, 16, 16, 0)
            path.arcTo(-8, 2, 16, 16, 0, 180)
            painter.drawPath(path)
            
        elif self.icon_type == 'ghost':
            path = QPainterPath()
            # Head
            path.moveTo(-6, 8)
            path.lineTo(-6, 0)
            path.arcTo(-6, -8, 12, 12, 180, -180)
            path.lineTo(6, 8)
            # Wavy bottom
            path.lineTo(2, 6)
            path.lineTo(-2, 8)
            path.lineTo(-6, 6)
            path.closeSubpath()
            painter.drawPath(path)
            # Eyes
            painter.setBrush(self.color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(-2, -2), 1, 1)
            painter.drawEllipse(QPointF(2, -2), 1, 1)
            
        elif self.icon_type == 'check':
            # Simple check mark in green
            painter.setPen(QPen(self.color, 2.5))
            painter.setBrush(Qt.NoBrush)
            
            path = QPainterPath()
            path.moveTo(-4, 0)
            path.lineTo(-1, 4)
            path.lineTo(5, -4)
            painter.drawPath(path)
            
        elif self.icon_type == 'x':
            # Simple X mark in red
            painter.setPen(QPen(self.color, 2.5))
            painter.drawLine(-4, -4, 4, 4)
            painter.drawLine(-4, 4, 4, -4)
            
        elif self.icon_type == 'clock':
            painter.setPen(QPen(self.color, 1.5))
            painter.drawEllipse(QPointF(0, 0), 9, 9)
            painter.drawLine(0, -5, 0, 0)
            painter.drawLine(0, 0, 3, 3)
            
        elif self.icon_type == 'sum':
            # Summation symbol (Σ)
            painter.setPen(QPen(self.color, 2))
            path = QPainterPath()
            # Top horizontal line
            path.moveTo(-4, -8)
            path.lineTo(4, -8)
            # Diagonal to middle
            path.lineTo(-2, 0)
            # Diagonal to bottom
            path.lineTo(4, 8)
            # Bottom horizontal line
            path.lineTo(-4, 8)
            painter.drawPath(path)


class StatCard(QFrame):
    """Card displaying stats for a player."""
    def __init__(self, title, wpm, acc, correct, incorrect, time_val, color, icon_type, theme_colors=None, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.color = color
        self.theme = theme_colors or {}
        
        # Get theme colors
        bg_secondary = self.theme.get('bg', '#252525')
        border_color = self.theme.get('border', '#333')
        
        # Style
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background-color: {bg_secondary};
                border: 2px solid {color};
                border-radius: 15px;
            }}
        """)
        
        # Glow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(color))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)
        
        # 1. Icon Section
        icon_layout = QVBoxLayout()
        icon_layout.setSpacing(5)
        icon_layout.setAlignment(Qt.AlignCenter)
        
        # Circle background for icon
        icon_bg = QFrame()
        icon_bg.setFixedSize(50, 50)
        # Semi-transparent background for icon
        c = QColor(color)
        rgba = f"rgba({c.red()},{c.green()},{c.blue()}, 0.2)"
        icon_bg.setStyleSheet(f"background-color: {rgba}; border-radius: 25px; border: none;")
        icon_bg_layout = QVBoxLayout(icon_bg)
        icon_bg_layout.setContentsMargins(0,0,0,0)
        icon_bg_layout.setAlignment(Qt.AlignCenter)
        
        icon = IconWidget(icon_type, color, 28)
        icon_bg_layout.addWidget(icon)
        
        text_primary = self.theme.get('text', '#e0e0e0')
        name_lbl = QLabel(title)
        name_lbl.setStyleSheet(f"color: {text_primary}; font-size: 12px; font-weight: bold; border: none;")
        name_lbl.setAlignment(Qt.AlignCenter)
        
        icon_layout.addWidget(icon_bg)
        icon_layout.addWidget(name_lbl)
        layout.addLayout(icon_layout)
        
        layout.addSpacing(15)
        
        # 2. WPM
        self._add_stat(layout, f"{wpm:.1f}", "WPM", size=24)
        
        layout.addSpacing(10)
        
        # 3. Acc
        self._add_stat(layout, f"{acc:.0f}%", "Acc", size=24)
        
        layout.addSpacing(15)
        
        # 4. Details (Check, X, Total, Time)
        success_color = self.theme.get('success', '#4CAF50')
        error_color = self.theme.get('error', '#FF5252')
        accent_color = self.theme.get('accent', '#2196F3')
        text_secondary = self.theme.get('text_secondary', '#aaaaaa')
        self._add_detail(layout, "check", success_color, str(correct))
        self._add_detail(layout, "x", error_color, str(incorrect))
        total_chars = correct + incorrect
        self._add_detail(layout, "sum", accent_color, str(total_chars))
        self._add_detail(layout, "clock", text_secondary, f"{time_val:.0f}s")

    def _add_stat(self, layout, value, label, size=24):
        container = QWidget()
        container.setStyleSheet("border: none;")
        v = QVBoxLayout(container)
        v.setContentsMargins(0,0,0,0)
        v.setSpacing(0)
        v.setAlignment(Qt.AlignCenter)
        
        text_primary = self.theme.get('text', 'white')
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"color: {text_primary}; font-size: {size}px; font-weight: bold; border: none;")
        val_lbl.setAlignment(Qt.AlignCenter)
        
        text_secondary = self.theme.get('text_secondary', '#888888')
        lbl_lbl = QLabel(label)
        lbl_lbl.setStyleSheet(f"color: {text_secondary}; font-size: 12px; border: none;")
        lbl_lbl.setAlignment(Qt.AlignCenter)
        
        v.addWidget(val_lbl)
        v.addWidget(lbl_lbl)
        layout.addWidget(container)

    def _add_detail(self, layout, icon_type, color, value):
        container = QWidget()
        container.setStyleSheet("border: none;")
        v = QVBoxLayout(container)
        v.setContentsMargins(0,0,0,0)
        v.setSpacing(4)
        v.setAlignment(Qt.AlignCenter)
        
        icon = IconWidget(icon_type, color, 20)
        
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"color: {color}; font-size: 14px; border: none; font-weight: bold;")
        val_lbl.setAlignment(Qt.AlignCenter)
        
        v.addWidget(icon)
        v.addWidget(val_lbl)
        layout.addWidget(container)


class SessionResultDialog(QDialog):
    def __init__(self, parent=None, stats=None, is_new_best=False, is_race=False,
                 race_info=None, theme_colors=None, filename: str = None,
                 user_keystrokes: List[Dict] = None, ghost_keystrokes: List[Dict] = None,
                 wpm_history: List[Tuple[int, float]] = None):
        super().__init__(parent)
        self.stats = stats or {}
        self.is_race = is_race
        self.race_info = race_info or {}
        self.filename = filename or ""
        self.theme_colors = theme_colors or {}
        self.user_keystrokes = user_keystrokes or []
        self.ghost_keystrokes = ghost_keystrokes or []
        self.wpm_history = wpm_history or []  # List of (second, wpm) tuples
        
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        
        # Calculate dynamic height based on content
        base_height = 280  # Title + file + player card + button + margins
        card_height = 100  # Height per stat card
        # Show graph if we have WPM history
        has_graph_data = len(self.wpm_history) >= 2
        graph_height = 200 if has_graph_data else 0
        
        if self.is_race:
            total_height = base_height + (2 * card_height) + graph_height  # User + Ghost cards + graph
        else:
            total_height = base_height + card_height + graph_height  # User card + graph
        
        self.setFixedSize(550, total_height)
        
        self._drag_pos = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Get theme colors
        theme = self.theme_colors or {}
        bg_primary = theme.get('bg', '#18181b')
        text_primary = theme.get('text', '#ffffff')
        text_secondary = theme.get('text_secondary', '#888888')
        success_color = theme.get('success', '#4CAF50')
        error_color = theme.get('error', '#FF5252')
        accent_color = theme.get('accent', '#2196F3')
        border_color = theme.get('border', '#333')
        user_color = theme.get('user_color', '#4CAF50')
        ghost_color = theme.get('ghost_color', '#9C27B0')
        
        # Main background frame - use dynamic height
        bg_frame = QFrame(self)
        bg_frame.setGeometry(0, 0, self.width(), self.height())
        bg_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_primary};
                border-radius: 20px;
                border: 1px solid {border_color};
            }}
        """)
        
        layout = QVBoxLayout(bg_frame)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 1. Title
        title_lbl = QLabel()
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(f"font-size: 36px; font-weight: 900; letter-spacing: 1px; border: none;")
        
        user_wpm = self.stats.get('wpm', 0)
        ghost_wpm = self.race_info.get('ghost_wpm', 0)
        
        if self.is_race:
            if user_wpm >= ghost_wpm:
                title_lbl.setText("YOU WON!")
                title_lbl.setStyleSheet(title_lbl.styleSheet() + f"color: {success_color};")
            else:
                title_lbl.setText("YOU LOST")
                title_lbl.setStyleSheet(title_lbl.styleSheet() + f"color: {error_color};")
        else:
            title_lbl.setText("FINISHED")
            title_lbl.setStyleSheet(title_lbl.styleSheet() + f"color: {text_primary};")
            
        layout.addWidget(title_lbl)
        
        # 2. File Name
        file_lbl = QLabel(f"File: {Path(self.filename).name}")
        file_lbl.setAlignment(Qt.AlignCenter)
        file_lbl.setStyleSheet(f"color: {text_secondary}; font-size: 14px; border: none;")
        layout.addWidget(file_lbl)
        
        layout.addSpacing(10)
        
        # 3. Player Card
        correct = self.stats.get('correct', 0)
        incorrect = self.stats.get('incorrect', 0)
        total = correct + incorrect
        acc = (correct / total * 100) if total > 0 else 0
        time_val = self.stats.get('time', 0)
        
        player_card = StatCard(
            "Player", user_wpm, acc, correct, incorrect, time_val,
            user_color, "user", theme
        )
        layout.addWidget(player_card)
        
        # 4. Ghost Card (Always show if race, or maybe show 'Personal Best' if not?)
        # Screenshot shows Ghost.
        if self.is_race:
            g_acc = self.race_info.get('ghost_acc', 100)
            g_time = self.race_info.get('ghost_time', 0)
            
            # Estimate counts if missing
            g_total_chars = int(ghost_wpm * 5 * (g_time / 60)) if g_time > 0 else 0
            g_correct = int(g_total_chars * (g_acc / 100))
            g_incorrect = g_total_chars - g_correct
            
            ghost_card = StatCard(
                "Ghost", ghost_wpm, g_acc, g_correct, g_incorrect, g_time,
                ghost_color, "ghost", theme
            )
            layout.addWidget(ghost_card)
        
        # Add interactive WPM graph if we have WPM history data
        if len(self.wpm_history) >= 2:
            # Convert wpm_history to the format expected by InteractiveWPMGraph
            times = [float(sec) for sec, wpm in self.wpm_history]
            wpms = [wpm for sec, wpm in self.wpm_history]
            total_time = self.stats.get('time', 0)
            
            graph_widget = InteractiveWPMGraph(
                times=times,
                wpms=wpms,
                total_time=total_time,
                line_color=user_color,
                theme_colors=theme,
                parent=self
            )
            layout.addWidget(graph_widget, alignment=Qt.AlignCenter)
            
        layout.addSpacing(20)
        
        # 5. Continue Button
        btn = QPushButton("Continue")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(50)
        button_bg = theme.get('button_bg', '#2196F3')
        button_hover = theme.get('button_hover', '#1976D2')
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {button_bg};
                color: {text_primary};
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {button_hover};
            }}
        """)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = None
            event.accept()

