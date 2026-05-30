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
from app.ui_icons import get_pixmap


class InteractiveWPMGraph(QWidget):
    """Interactive WPM vs Time graph widget with hover tooltips and error markers."""
    
    def __init__(self, times: List[float], wpms: List[float], total_time: float, 
                 line_color: str, theme_colors: dict, error_history: List[Tuple[int, int]] = None,
                 is_race: bool = False, ghost_wpm_history: List[Tuple[int, float]] = None,
                 ghost_error_history: List[Tuple[int, int]] = None, ghost_color: str = None,
                 parent=None):
        super().__init__(parent)
        self.line_color = QColor(line_color)
        self.error_color = QColor("#FF5252")  # Red for user errors
        # Ghostly colors - light and ethereal
        self.ghost_wpm_color = QColor("#D8B4FE")  # Light ghostly purple
        self.ghost_error_color = QColor("#93C5FD")  # Light ghostly blue
        self.theme = theme_colors or {}
        self.error_history = error_history or []  # list of (second, error_count)
        self.is_race = is_race
        self.ghost_wpm_history = ghost_wpm_history or []
        self.ghost_error_history = ghost_error_history or []
        
        # Visibility toggles for legend items - hierarchical
        self.user_visible = True  # Master toggle for all user data
        self.user_wpm_visible = True
        self.user_errors_visible = True
        self.ghost_visible = True  # Master toggle for all ghost data
        self.ghost_wpm_visible = True
        self.ghost_errors_visible = True
        
        # Legend hit areas (will be set in paintEvent)
        self.user_label_rect = QRectF()
        self.user_wpm_rect = QRectF()
        self.user_error_rect = QRectF()
        self.ghost_label_rect = QRectF()
        self.ghost_wpm_rect = QRectF()
        self.ghost_error_rect = QRectF()
        
        # Round total time to whole seconds
        self.total_time = max(1, int(total_time) if total_time == int(total_time) else int(total_time) + 1)
        
        # Data is already in (second, wpm) format - use directly as markers
        # times and wpms are parallel lists
        self.second_markers = [(int(t), w) for t, w in zip(times, wpms) if t >= 1]
        self.ghost_second_markers = [(int(t), w) for t, w in self.ghost_wpm_history if t >= 1]
        
        # Graph margins - balanced for both axes, extra top margin for legend
        self.margin_left = 40
        self.margin_right = 40  # Space for right Y-axis (errors)
        self.margin_top = 55 if is_race else 45  # More space for race legend
        self.margin_bottom = 45  # Extra space to prevent clipping with continue button
        
        # Mouse tracking
        self.setMouseTracking(True)
        self.hover_info = None  # (second, type) where type is 'user_wpm', 'user_error', 'ghost_wpm', 'ghost_error'
        self.hover_legend = None  # 'user', 'user_wpm', 'user_error', 'ghost', 'ghost_wpm', 'ghost_error'
        self.previous_hover_legend = None
        
        # Calculate axis ranges - start from 1 second, end at max time
        self.x_min = 1
        all_seconds = [s for s, _ in self.second_markers] + [s for s, _ in self.ghost_second_markers]
        self.x_max = max(self.total_time, max(all_seconds) if all_seconds else 1)
        
        # Calculate y-axis max (WPM) - consider both user and ghost
        all_wpms = [w for _, w in self.second_markers] + [w for _, w in self.ghost_second_markers]
        if all_wpms:
            max_wpm = max(all_wpms)
        else:
            max_wpm = 100
        
        # Round up to next appropriate interval based on magnitude
        if max_wpm <= 50:
            self.y_max = ((int(max_wpm) // 10) + 1) * 10
        elif max_wpm <= 200:
            self.y_max = ((int(max_wpm) // 20) + 1) * 20
        elif max_wpm <= 500:
            self.y_max = ((int(max_wpm) // 50) + 1) * 50
        else:
            self.y_max = ((int(max_wpm) // 100) + 1) * 100
        
        # Dynamic y-step based on range - aim for 5-8 labels
        if self.y_max <= 50:
            self.y_step = 10
        elif self.y_max <= 100:
            self.y_step = 20
        elif self.y_max <= 200:
            self.y_step = 40
        elif self.y_max <= 400:
            self.y_step = 50
        elif self.y_max <= 600:
            self.y_step = 100
        elif self.y_max <= 1000:
            self.y_step = 150
        else:
            # For very high WPM, calculate step to have ~6 labels
            self.y_step = max(200, (self.y_max // 6 // 50) * 50)
        
        # Calculate right Y-axis max (errors) - consider both user and ghost
        all_errors = [e for _, e in self.error_history] + [e for _, e in self.ghost_error_history]
        if all_errors:
            max_errors = max(all_errors)
        else:
            max_errors = 0
        
        # Calculate error axis max and step - aim for 5-8 labels
        if max_errors <= 0:
            self.error_max = 5  # Default if no errors
            self.error_step = 1
        elif max_errors <= 5:
            self.error_max = 5
            self.error_step = 1
        elif max_errors <= 10:
            self.error_max = 10
            self.error_step = 2
        elif max_errors <= 20:
            self.error_max = 20
            self.error_step = 4
        elif max_errors <= 50:
            self.error_max = 50
            self.error_step = 10
        elif max_errors <= 100:
            self.error_max = 100
            self.error_step = 20
        elif max_errors <= 200:
            self.error_max = 200
            self.error_step = 40
        else:
            # For very high error counts, calculate step to have ~6 labels
            self.error_max = ((int(max_errors) // 50) + 1) * 50
            self.error_step = max(50, self.error_max // 6)
        
        # Calculate x-axis step dynamically to avoid clutter
        # Aim for approximately 6-10 labels on the x-axis
        duration = self.x_max - self.x_min
        if duration <= 5:
            self.x_step = 1
        elif duration <= 15:
            self.x_step = 2
        elif duration <= 30:
            self.x_step = 5
        elif duration <= 60:
            self.x_step = 10
        elif duration <= 150:
            self.x_step = 20
        elif duration <= 300:
            self.x_step = 30
        elif duration <= 600:
            self.x_step = 60  # 1 minute intervals
        elif duration <= 1800:
            self.x_step = 180  # 3 minute intervals
        elif duration <= 3600:
            self.x_step = 300  # 5 minute intervals
        else:
            # For very long sessions, calculate step to have ~8 labels
            self.x_step = max(600, (duration // 8 // 60) * 60)  # Round to nearest minute
        
        self.setFixedSize(470, 235 if is_race else 215)  # Taller for race legend + bottom margin
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
    
    def _error_to_y(self, errors: int) -> float:
        """Convert error count to y coordinate (uses right axis scale)."""
        rect = self._graph_rect()
        return rect.y() + rect.height() - (errors / self.error_max) * rect.height()
    
    def _find_hovered_marker(self, x: float, y: float) -> Tuple[int, str]:
        """Find which marker is being hovered, if any.
        Returns (second, type) where type is 'user_wpm', 'user_error', 'ghost_wpm', 'ghost_error', or (None, None)"""
        
        # Check user error markers
        if self.user_visible and self.user_errors_visible:
            for second, errors in self.error_history:
                marker_x = self._time_to_x(second)
                marker_y = self._error_to_y(errors)
                if abs(x - marker_x) < 12 and abs(y - marker_y) < 12:
                    return second, 'user_error'
        
        # Check ghost error markers
        if self.ghost_visible and self.ghost_errors_visible:
            for second, errors in self.ghost_error_history:
                marker_x = self._time_to_x(second)
                marker_y = self._error_to_y(errors)
                if abs(x - marker_x) < 12 and abs(y - marker_y) < 12:
                    return second, 'ghost_error'
        
        # Check user WPM markers
        if self.user_visible and self.user_wpm_visible:
            for second, wpm in self.second_markers:
                marker_x = self._time_to_x(second)
                marker_y = self._wpm_to_y(wpm)
                if abs(x - marker_x) < 12 and abs(y - marker_y) < 12:
                    return second, 'user_wpm'
        
        # Check ghost WPM markers
        if self.ghost_visible and self.ghost_wpm_visible:
            for second, wpm in self.ghost_second_markers:
                marker_x = self._time_to_x(second)
                marker_y = self._wpm_to_y(wpm)
                if abs(x - marker_x) < 12 and abs(y - marker_y) < 12:
                    return second, 'ghost_wpm'
        
        return None, None
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click to toggle legend items."""
        x = event.position().x()
        y = event.position().y()
        
        # Check user master toggle
        if self.user_label_rect.contains(x, y):
            self.user_visible = not self.user_visible
            self.update()
            return
        
        # Check user WPM toggle
        if self.user_wpm_rect.contains(x, y):
            self.user_wpm_visible = not self.user_wpm_visible
            self.update()
            return
        
        # Check user Error toggle
        if self.user_error_rect.contains(x, y):
            self.user_errors_visible = not self.user_errors_visible
            self.update()
            return
        
        # Check ghost toggles (only in race mode)
        if self.is_race:
            if self.ghost_label_rect.contains(x, y):
                self.ghost_visible = not self.ghost_visible
                self.update()
                return
            
            if self.ghost_wpm_rect.contains(x, y):
                self.ghost_wpm_visible = not self.ghost_wpm_visible
                self.update()
                return
            
            if self.ghost_error_rect.contains(x, y):
                self.ghost_errors_visible = not self.ghost_errors_visible
                self.update()
                return
    
    def mouseMoveEvent(self, event):
        """Track mouse position and update hover info."""
        x = event.position().x()
        y = event.position().y()
        self.hover_info = self._find_hovered_marker(x, y)

        # Check legend hover
        self.hover_legend = None
        if self.user_label_rect.contains(x, y):
            self.hover_legend = 'user'
        elif self.user_wpm_rect.contains(x, y):
            self.hover_legend = 'user_wpm'
        elif self.user_error_rect.contains(x, y):
            self.hover_legend = 'user_error'
        elif self.is_race:
            if self.ghost_label_rect.contains(x, y):
                self.hover_legend = 'ghost'
            elif self.ghost_wpm_rect.contains(x, y):
                self.hover_legend = 'ghost_wpm'
            elif self.ghost_error_rect.contains(x, y):
                self.hover_legend = 'ghost_error'

        # Update cursor
        if self.hover_legend:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        # Show tooltip if hover_legend changed
        if self.hover_legend != self.previous_hover_legend:
            if self.hover_legend:
                tooltip_text = "Double-click to toggle visibility"
                QToolTip.showText(event.globalPosition().toPoint(), tooltip_text, self)
            else:
                QToolTip.hideText()
            self.previous_hover_legend = self.hover_legend

        self.update()
    
    def leaveEvent(self, event):
        """Clear hover when mouse leaves."""
        self.hover_info = (None, None)
        self.hover_legend = None
        self.setCursor(Qt.ArrowCursor)
        QToolTip.hideText()
        self.previous_hover_legend = None
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
        
        # Y-axis labels (WPM - left side) - dynamic spacing
        for wpm in range(0, self.y_max + 1, self.y_step):
            y = self._wpm_to_y(wpm)
            painter.drawText(QRectF(0, y - 8, self.margin_left - 5, 16), 
                           Qt.AlignRight | Qt.AlignVCenter, str(wpm))
        
        # Check if any errors are visible
        any_errors_visible = ((self.user_visible and self.user_errors_visible and self.error_history) or
                             (self.ghost_visible and self.ghost_errors_visible and self.ghost_error_history))
        
        # Right Y-axis labels (Errors) - only if errors are visible
        if any_errors_visible:
            painter.setPen(self.error_color)
            for errors in range(0, self.error_max + 1, self.error_step):
                y = self._error_to_y(errors)
                painter.drawText(QRectF(rect.x() + rect.width() + 5, y - 8, self.margin_right - 5, 16), 
                               Qt.AlignLeft | Qt.AlignVCenter, str(errors))
            painter.setPen(text_color)
        
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
        
        # Y-axis title (rotated) - WPM on left
        painter.save()
        painter.translate(12, rect.y() + rect.height() / 2)
        painter.rotate(-90)
        painter.drawText(QRectF(-30, -10, 60, 20), Qt.AlignCenter, "WPM")
        painter.restore()
        
        # Right Y-axis title (rotated) - Errors - only if errors visible
        if any_errors_visible:
            painter.save()
            painter.setPen(self.error_color)
            painter.translate(self.width() - 12, rect.y() + rect.height() / 2)
            painter.rotate(90)
            painter.drawText(QRectF(-30, -10, 60, 20), Qt.AlignCenter, "Errors")
            painter.restore()
            painter.setPen(text_color)
        
        # X-axis title
        painter.drawText(QRectF(rect.x(), self.height() - 15, rect.width(), 15), 
                        Qt.AlignCenter, "Time (seconds)")
        
        # Draw the WPM curve connecting the second markers (only if visible)
        # ===== Draw User Data =====
        user_effective_visible = self.user_visible
        
        # Draw user WPM curve
        if user_effective_visible and self.user_wpm_visible and len(self.second_markers) >= 2:
            path = QPainterPath()
            first_sec, first_wpm = self.second_markers[0]
            path.moveTo(self._time_to_x(first_sec), self._wpm_to_y(first_wpm))
            
            for sec, wpm in self.second_markers[1:]:
                path.lineTo(self._time_to_x(sec), self._wpm_to_y(wpm))
            
            painter.setPen(QPen(self.line_color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
        
        # Draw user WPM markers (interactive dots)
        if user_effective_visible and self.user_wpm_visible:
            for second, wpm in self.second_markers:
                marker_x = self._time_to_x(second)
                marker_y = self._wpm_to_y(wpm)
                
                hover_sec, hover_type = self.hover_info if self.hover_info else (None, None)
                is_hovered = (hover_sec == second and hover_type == 'user_wpm')
                
                # Draw dot (smaller size)
                if is_hovered:
                    painter.setPen(QPen(self.line_color, 1.5))
                    painter.setBrush(QBrush(self.line_color))
                    painter.drawEllipse(QPointF(marker_x, marker_y), 3, 3)
                else:
                    painter.setPen(QPen(self.line_color, 1))
                    painter.setBrush(QBrush(bg_color))
                    painter.drawEllipse(QPointF(marker_x, marker_y), 2, 2)
        
        # Draw user error markers (red X marks)
        if user_effective_visible and self.user_errors_visible:
            for second, errors in self.error_history:
                marker_x = self._time_to_x(second)
                marker_y = self._error_to_y(errors)
                
                hover_sec, hover_type = self.hover_info if self.hover_info else (None, None)
                is_hovered = (hover_sec == second and hover_type == 'user_error')
                
                # Draw X mark (smaller size)
                size = 4 if is_hovered else 2.5
                pen_width = 2 if is_hovered else 1.5
                painter.setPen(QPen(self.error_color, pen_width))
                painter.drawLine(QPointF(marker_x - size, marker_y - size), 
                               QPointF(marker_x + size, marker_y + size))
                painter.drawLine(QPointF(marker_x - size, marker_y + size), 
                               QPointF(marker_x + size, marker_y - size))
        
        # ===== Draw Ghost Data =====
        ghost_effective_visible = self.ghost_visible and self.is_race
        
        # Draw ghost WPM curve
        if ghost_effective_visible and self.ghost_wpm_visible and len(self.ghost_second_markers) >= 2:
            path = QPainterPath()
            first_sec, first_wpm = self.ghost_second_markers[0]
            path.moveTo(self._time_to_x(first_sec), self._wpm_to_y(first_wpm))
            
            for sec, wpm in self.ghost_second_markers[1:]:
                path.lineTo(self._time_to_x(sec), self._wpm_to_y(wpm))
            
            painter.setPen(QPen(self.ghost_wpm_color, 2, Qt.DashLine))  # Dashed for ghost
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
        
        # Draw ghost WPM markers (squares for ghost)
        if ghost_effective_visible and self.ghost_wpm_visible:
            for second, wpm in self.ghost_second_markers:
                marker_x = self._time_to_x(second)
                marker_y = self._wpm_to_y(wpm)
                
                hover_sec, hover_type = self.hover_info if self.hover_info else (None, None)
                is_hovered = (hover_sec == second and hover_type == 'ghost_wpm')
                
                # Draw square marker for ghost (smaller with glow effect)
                size = 3 if is_hovered else 2
                
                # Draw glow effect (slightly larger, semi-transparent)
                glow_color = QColor(self.ghost_wpm_color)
                glow_color.setAlpha(60)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(glow_color))
                painter.drawRect(QRectF(marker_x - size - 2, marker_y - size - 2, (size + 2) * 2, (size + 2) * 2))
                
                if is_hovered:
                    painter.setPen(QPen(self.ghost_wpm_color, 1.5))
                    painter.setBrush(QBrush(self.ghost_wpm_color))
                else:
                    painter.setPen(QPen(self.ghost_wpm_color, 1))
                    painter.setBrush(QBrush(bg_color))
                painter.drawRect(QRectF(marker_x - size, marker_y - size, size * 2, size * 2))
        
        # Draw ghost error markers (blue X marks)
        if ghost_effective_visible and self.ghost_errors_visible:
            for second, errors in self.ghost_error_history:
                marker_x = self._time_to_x(second)
                marker_y = self._error_to_y(errors)
                
                hover_sec, hover_type = self.hover_info if self.hover_info else (None, None)
                is_hovered = (hover_sec == second and hover_type == 'ghost_error')
                
                # Draw X mark in ghost error color (smaller with glow effect)
                size = 4 if is_hovered else 2.5
                pen_width = 2 if is_hovered else 1.5
                
                # Draw glow effect
                glow_color = QColor(self.ghost_error_color)
                glow_color.setAlpha(60)
                painter.setPen(QPen(glow_color, pen_width + 3))
                painter.drawLine(QPointF(marker_x - size, marker_y - size), 
                               QPointF(marker_x + size, marker_y + size))
                painter.drawLine(QPointF(marker_x - size, marker_y + size), 
                               QPointF(marker_x + size, marker_y - size))
                
                # Draw main X
                painter.setPen(QPen(self.ghost_error_color, pen_width))
                painter.drawLine(QPointF(marker_x - size, marker_y - size), 
                               QPointF(marker_x + size, marker_y + size))
                painter.drawLine(QPointF(marker_x - size, marker_y + size), 
                               QPointF(marker_x + size, marker_y - size))
        
        # ===== Draw Tooltips =====
        hover_sec, hover_type = self.hover_info if self.hover_info else (None, None)
        
        if hover_sec is not None and hover_type:
            # Find the data for this hover
            hover_value = None
            tooltip_text = ""
            border_color = text_color
            
            if hover_type == 'user_wpm':
                for sec, wpm in self.second_markers:
                    if sec == hover_sec:
                        hover_value = wpm
                        break
                if hover_value is not None:
                    tooltip_text = f"{hover_sec}s | {hover_value:.1f} WPM"
                    border_color = self.line_color
                    dot_x = self._time_to_x(hover_sec)
                    dot_y = self._wpm_to_y(hover_value)
                    
            elif hover_type == 'ghost_wpm':
                for sec, wpm in self.ghost_second_markers:
                    if sec == hover_sec:
                        hover_value = wpm
                        break
                if hover_value is not None:
                    tooltip_text = f"Ghost {hover_sec}s | {hover_value:.1f} WPM"
                    border_color = self.ghost_wpm_color
                    dot_x = self._time_to_x(hover_sec)
                    dot_y = self._wpm_to_y(hover_value)
                    
            elif hover_type == 'user_error':
                for sec, errors in self.error_history:
                    if sec == hover_sec:
                        hover_value = errors
                        break
                if hover_value is not None:
                    error_label = "error" if hover_value == 1 else "errors"
                    tooltip_text = f"{hover_sec}s | {hover_value} {error_label}"
                    border_color = self.error_color
                    dot_x = self._time_to_x(hover_sec)
                    dot_y = self._error_to_y(hover_value)
                    
            elif hover_type == 'ghost_error':
                for sec, errors in self.ghost_error_history:
                    if sec == hover_sec:
                        hover_value = errors
                        break
                if hover_value is not None:
                    error_label = "error" if hover_value == 1 else "errors"
                    tooltip_text = f"Ghost {hover_sec}s | {hover_value} {error_label}"
                    border_color = self.ghost_error_color
                    dot_x = self._time_to_x(hover_sec)
                    dot_y = self._error_to_y(hover_value)
            
            if hover_value is not None:
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
                painter.setPen(QPen(border_color, 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(tooltip_rect, 4, 4)
                
                # Draw tooltip text
                painter.setPen(text_color)
                painter.drawText(tooltip_rect, Qt.AlignCenter, tooltip_text)
        
        # ===== Draw Legend =====
        # Hierarchical legend: "You" with WPM/Errors below, "Ghost" with WPM/Errors below (if race)
        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)
        fm = QFontMetrics(font)

        line_height = 14
        indent = 15  # Indent for sub-items

        # --- User Legend (left side) ---
        user_legend_x = rect.x() + 5
        legend_y = 3

        # "You" label
        you_text = "You"
        you_visible = self.user_visible
        you_color = text_color if you_visible else QColor(text_color.red(), text_color.green(), text_color.blue(), 80)
        painter.setPen(you_color)
        font.setBold(True)
        font.setUnderline(self.hover_legend == 'user')
        painter.setFont(font)
        painter.drawText(QPointF(user_legend_x, legend_y + 10), you_text)
        self.user_label_rect = QRectF(user_legend_x - 3, legend_y, fm.horizontalAdvance(you_text) + 6, line_height)
        font.setBold(False)
        font.setUnderline(False)
        painter.setFont(font)
        
        # User WPM
        wpm_y = legend_y + line_height
        user_wpm_effective = you_visible and self.user_wpm_visible
        wpm_color = self.line_color if user_wpm_effective else QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 80)
        wpm_text_col = text_color if user_wpm_effective else QColor(text_color.red(), text_color.green(), text_color.blue(), 80)

        # Draw line + dot
        painter.setPen(QPen(wpm_color, 2))
        painter.drawLine(QPointF(user_legend_x + indent, wpm_y + 5), QPointF(user_legend_x + indent + 15, wpm_y + 5))
        painter.setBrush(QBrush(wpm_color))
        painter.drawEllipse(QPointF(user_legend_x + indent + 7.5, wpm_y + 5), 2, 2)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(wpm_text_col)
        font.setUnderline(self.hover_legend == 'user_wpm')
        painter.setFont(font)
        painter.drawText(QPointF(user_legend_x + indent + 20, wpm_y + 9), "WPM")
        font.setUnderline(False)
        painter.setFont(font)
        self.user_wpm_rect = QRectF(user_legend_x + indent - 3, wpm_y - 2, 55, line_height)
        
        # User Errors (only if has error data)
        if self.error_history:
            err_y = wpm_y + line_height
            user_err_effective = you_visible and self.user_errors_visible
            err_color = self.error_color if user_err_effective else QColor(self.error_color.red(), self.error_color.green(), self.error_color.blue(), 80)
            err_text_col = text_color if user_err_effective else QColor(text_color.red(), text_color.green(), text_color.blue(), 80)
            
            # Draw X
            painter.setPen(QPen(err_color, 2))
            x_center = user_legend_x + indent + 5
            y_center = err_y + 5
            painter.drawLine(QPointF(x_center - 3, y_center - 3), QPointF(x_center + 3, y_center + 3))
            painter.drawLine(QPointF(x_center - 3, y_center + 3), QPointF(x_center + 3, y_center - 3))
            painter.setPen(err_text_col)
            font.setUnderline(self.hover_legend == 'user_error')
            painter.setFont(font)
            painter.drawText(QPointF(user_legend_x + indent + 20, err_y + 9), "Errors")
            font.setUnderline(False)
            painter.setFont(font)
            self.user_error_rect = QRectF(user_legend_x + indent - 3, err_y - 2, 60, line_height)
        else:
            self.user_error_rect = QRectF()
        
        # --- Ghost Legend (right side) - only in race mode ---
        if self.is_race:
            ghost_legend_x = rect.x() + rect.width() - 70
            
            # "Ghost" label
            ghost_text = "Ghost"
            ghost_vis = self.ghost_visible
            ghost_label_color = text_color if ghost_vis else QColor(text_color.red(), text_color.green(), text_color.blue(), 80)
            painter.setPen(ghost_label_color)
            font.setBold(True)
            font.setUnderline(self.hover_legend == 'ghost')
            painter.setFont(font)
            painter.drawText(QPointF(ghost_legend_x, legend_y + 10), ghost_text)
            self.ghost_label_rect = QRectF(ghost_legend_x - 3, legend_y, fm.horizontalAdvance(ghost_text) + 6, line_height)
            font.setBold(False)
            font.setUnderline(False)
            painter.setFont(font)
            
            # Ghost WPM
            g_wpm_y = legend_y + line_height
            ghost_wpm_effective = ghost_vis and self.ghost_wpm_visible
            g_wpm_color = self.ghost_wpm_color if ghost_wpm_effective else QColor(self.ghost_wpm_color.red(), self.ghost_wpm_color.green(), self.ghost_wpm_color.blue(), 80)
            g_wpm_text_col = text_color if ghost_wpm_effective else QColor(text_color.red(), text_color.green(), text_color.blue(), 80)
            
            # Draw dashed line + square
            painter.setPen(QPen(g_wpm_color, 2, Qt.DashLine))
            painter.drawLine(QPointF(ghost_legend_x + indent, g_wpm_y + 5), QPointF(ghost_legend_x + indent + 15, g_wpm_y + 5))
            painter.setPen(QPen(g_wpm_color, 1))
            painter.setBrush(QBrush(g_wpm_color) if ghost_wpm_effective else Qt.NoBrush)
            painter.drawRect(QRectF(ghost_legend_x + indent + 5, g_wpm_y + 3, 5, 5))
            painter.setBrush(Qt.NoBrush)
            painter.setPen(g_wpm_text_col)
            font.setUnderline(self.hover_legend == 'ghost_wpm')
            painter.setFont(font)
            painter.drawText(QPointF(ghost_legend_x + indent + 20, g_wpm_y + 9), "WPM")
            font.setUnderline(False)
            painter.setFont(font)
            self.ghost_wpm_rect = QRectF(ghost_legend_x + indent - 3, g_wpm_y - 2, 55, line_height)
            
            # Ghost Errors (only if has ghost error data)
            if self.ghost_error_history:
                g_err_y = g_wpm_y + line_height
                ghost_err_effective = ghost_vis and self.ghost_errors_visible
                g_err_color = self.ghost_error_color if ghost_err_effective else QColor(self.ghost_error_color.red(), self.ghost_error_color.green(), self.ghost_error_color.blue(), 80)
                g_err_text_col = text_color if ghost_err_effective else QColor(text_color.red(), text_color.green(), text_color.blue(), 80)
                
                # Draw X in ghost error color
                painter.setPen(QPen(g_err_color, 2))
                x_center = ghost_legend_x + indent + 5
                y_center = g_err_y + 5
                painter.drawLine(QPointF(x_center - 3, y_center - 3), QPointF(x_center + 3, y_center + 3))
                painter.drawLine(QPointF(x_center - 3, y_center + 3), QPointF(x_center + 3, y_center - 3))
                painter.setPen(g_err_text_col)
                font.setUnderline(self.hover_legend == 'ghost_error')
                painter.setFont(font)
                painter.drawText(QPointF(ghost_legend_x + indent + 20, g_err_y + 9), "Errors")
                font.setUnderline(False)
                painter.setFont(font)
                self.ghost_error_rect = QRectF(ghost_legend_x + indent - 3, g_err_y - 2, 60, line_height)
            else:
                self.ghost_error_rect = QRectF()
        else:
            # Clear ghost rects if not a race
            self.ghost_label_rect = QRectF()
            self.ghost_wpm_rect = QRectF()
            self.ghost_error_rect = QRectF()


class IconWidget(QLabel):
    """Widget to display SVG icons from ui_icons."""
    ICON_MAP = {
        'user': 'USER',
        'ghost': 'GHOST',
        'check': 'CHECK',
        'x': 'CLOSE',
        'clock': 'CLOCK',
        'sum': 'SUM'
    }
    
    def __init__(self, icon_type, color, size=24, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.icon_color = QColor(color) if isinstance(color, str) else color
        self.icon_size = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.update_icon()

    def update_icon(self):
        icon_name = self.ICON_MAP.get(self.icon_type, self.icon_type)
        pixmap = get_pixmap(icon_name, size=self.icon_size, color_override=self.icon_color.name())
        self.setPixmap(pixmap)


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
        self._add_stat(layout, f"{acc:.1f}%", "Acc", size=24)
        
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
        
        minutes = int(time_val // 60)
        seconds = int(time_val % 60)
        self._add_detail(layout, "clock", text_secondary, f"{minutes}:{seconds:02d}")

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
                 wpm_history: List[Tuple[int, float]] = None, 
                 error_history: List[Tuple[int, int]] = None,
                 ghost_wpm_history: List[Tuple[int, float]] = None,
                 ghost_error_history: List[Tuple[int, int]] = None):
        super().__init__(parent)
        self.is_new_best = is_new_best
        self.stats = stats or {}
        self.is_race = is_race
        self.race_info = race_info or {}
        self.filename = filename or ""
        self.theme_colors = theme_colors or {}
        self.user_keystrokes = user_keystrokes or []
        self.ghost_keystrokes = ghost_keystrokes or []
        self.wpm_history = wpm_history or []  # List of (second, wpm) tuples
        self.error_history = error_history or []  # List of (second, error_count) tuples
        self.ghost_wpm_history = ghost_wpm_history or []  # Ghost WPM history
        self.ghost_error_history = ghost_error_history or []  # Ghost error history
        
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        
        # Calculate dynamic height based on content
        base_height = 300  # Title + file + player card + button + margins (increased for spacing)
        card_height = 100  # Height per stat card
        # Show graph if we have WPM history
        has_graph_data = len(self.wpm_history) >= 2
        graph_height = 235 if has_graph_data else 0  # Match the graph widget height
        
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
                title = "YOU WON!"
                if self.is_new_best:
                    title += " (New Best!)"
                title_lbl.setText(title)
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

            # Adjust accuracy if stored as decimal
            if g_acc < 1:
                g_acc *= 100

            # Use stored final_stats for counts if available
            ghost_final_stats = self.race_info.get('ghost_final_stats')
            if ghost_final_stats:
                g_correct = ghost_final_stats.get('correct', 0)
                g_incorrect = ghost_final_stats.get('incorrect', 0)
            else:
                # Fallback: estimate counts from WPM (legacy ghosts without final_stats)
                g_total_chars = int(ghost_wpm * 5 * (g_time / 60)) if g_time > 0 else 0
                g_correct = int(g_total_chars * (g_acc / 100))
                g_incorrect = g_total_chars - g_correct
            
            ghost_card = StatCard(
                "Ghost", ghost_wpm, g_acc, g_correct, g_incorrect, g_time,
                ghost_color, "ghost", theme
            )
            layout.addWidget(ghost_card)
        
        # Add interactive WPM graph if we have WPM history data (user or ghost)
        has_user_data = len(self.wpm_history) >= 2
        has_ghost_data = len(self.ghost_wpm_history) >= 2
        
        if has_user_data or has_ghost_data:
            # Convert wpm_history to the format expected by InteractiveWPMGraph
            times = [float(sec) for sec, wpm in self.wpm_history]
            wpms = [wpm for sec, wpm in self.wpm_history]
            
            # Use the longer time as total time
            user_time = self.stats.get('time', 0)
            ghost_time = self.race_info.get('ghost_time', 0) if self.is_race else 0
            total_time = max(user_time, ghost_time)
            
            graph_widget = InteractiveWPMGraph(
                times=times,
                wpms=wpms,
                total_time=total_time,
                line_color=user_color,
                theme_colors=theme,
                error_history=self.error_history,
                is_race=self.is_race,
                ghost_wpm_history=self.ghost_wpm_history,
                ghost_error_history=self.ghost_error_history,
                ghost_color=ghost_color,
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

