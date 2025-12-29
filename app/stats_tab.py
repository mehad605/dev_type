"""Stats tab widget for visualizing typing statistics and performance metrics."""
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QDate
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QComboBox,
    QDateEdit,
)

from app import stats_db
from app import settings


def get_theme_colors() -> Dict[str, QColor]:
    """Get current theme colors for charts."""
    from app.themes import get_color_scheme
    theme = settings.get_setting("theme", "dark")
    scheme_name = settings.get_setting("dark_scheme", "dracula")
    if theme == "light":
        scheme_name = settings.get_setting("light_scheme", "default")
    scheme = get_color_scheme(theme, scheme_name)
    
    return {
        "bg_primary": QColor(scheme.bg_primary),
        "bg_secondary": QColor(scheme.bg_secondary),
        "bg_tertiary": QColor(scheme.bg_tertiary),
        "text_primary": QColor(scheme.text_primary),
        "text_secondary": QColor(scheme.text_secondary),
        "text_disabled": QColor(scheme.text_disabled),
        "border": QColor(scheme.border_color),
        "accent": QColor(scheme.accent_color),
        "success": QColor(scheme.success_color),
        "warning": QColor(scheme.warning_color),
        "error": QColor(scheme.error_color),
        "info": QColor(scheme.info_color),
    }


class LanguageFilterChip(QFrame):
    """A clickable chip for language filtering."""
    
    toggled = Signal(str, bool)  # language, is_selected
    
    def __init__(self, language: str, is_all: bool = False, parent=None):
        super().__init__(parent)
        self.language = language
        self.is_all = is_all
        self._selected = is_all  # "All" starts selected by default
        
        self.setObjectName("languageChip")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(32)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(4)
        
        self.label = QLabel(language)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        
        self._update_style()
    
    def _update_style(self):
        """Update visual style based on selection state."""
        colors = get_theme_colors()
        
        if self._selected:
            accent = colors["accent"].name()
            self.setStyleSheet(f"""
                QFrame#languageChip {{
                    background-color: {accent};
                    border-radius: 14px;
                    border: 1px solid {accent};
                }}
                QLabel {{
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 12px;
                    background: transparent;
                    border: none;
                }}
            """)
        else:
            bg = colors["bg_secondary"].name()
            border = colors["border"].name()
            bg_hover = colors["bg_tertiary"].name()
            text = colors["text_secondary"].name()
            self.setStyleSheet(f"""
                QFrame#languageChip {{
                    background-color: {bg};
                    border-radius: 14px;
                    border: 1px solid {border};
                }}
                QFrame#languageChip:hover {{
                    background-color: {bg_hover};
                    border: 1px solid {colors["accent"].name()};
                }}
                QLabel {{
                    color: {text};
                    font-size: 12px;
                    background: transparent;
                    border: none;
                }}
            """)
    
    def apply_theme(self):
        """Apply current theme colors."""
        self._update_style()
    
    @property
    def selected(self) -> bool:
        return self._selected
    
    @selected.setter
    def selected(self, value: bool):
        if self._selected != value:
            self._selected = value
            self._update_style()
    
    def mousePressEvent(self, event):
        """Handle click to toggle selection."""
        if event.button() == Qt.LeftButton:
            self.toggled.emit(self.language, not self._selected)
        super().mousePressEvent(event)


class LanguageFilterBar(QWidget):
    """Bar of language filter chips with "All" option."""
    
    filter_changed = Signal(set)  # Set of selected languages (empty = all)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._chips: Dict[str, LanguageFilterChip] = {}
        self._selected_languages: Set[str] = set()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # "All" chip
        self._all_chip = LanguageFilterChip("All", is_all=True)
        self._all_chip.toggled.connect(self._on_all_toggled)
        layout.addWidget(self._all_chip)
        
        # Container for language chips
        self._chips_container = QHBoxLayout()
        self._chips_container.setSpacing(8)
        layout.addLayout(self._chips_container)
        
        layout.addStretch()
    
    def set_languages(self, languages: List[str]):
        """Set available languages, creating chips for each."""
        # Clear existing chips
        for chip in self._chips.values():
            chip.deleteLater()
        self._chips.clear()
        
        # Create new chips
        for lang in sorted(languages):
            chip = LanguageFilterChip(lang)
            chip.toggled.connect(self._on_language_toggled)
            self._chips[lang] = chip
            self._chips_container.addWidget(chip)
        
        # Reset to "All" selected
        self._selected_languages.clear()
        self._all_chip.selected = True
        for chip in self._chips.values():
            chip.selected = False
    
    def _on_all_toggled(self, language: str, is_selected: bool):
        """Handle "All" chip toggle."""
        if is_selected or not self._selected_languages:
            # Select "All" and deselect others
            self._all_chip.selected = True
            self._selected_languages.clear()
            for chip in self._chips.values():
                chip.selected = False
            self.filter_changed.emit(set())  # Empty set = all languages
    
    def _on_language_toggled(self, language: str, is_selected: bool):
        """Handle individual language chip toggle."""
        if is_selected:
            # Add to selection
            self._selected_languages.add(language)
            self._chips[language].selected = True
            self._all_chip.selected = False
        else:
            # Remove from selection
            self._selected_languages.discard(language)
            self._chips[language].selected = False
            
            # If nothing selected, revert to "All"
            if not self._selected_languages:
                self._all_chip.selected = True
        
        self.filter_changed.emit(self._selected_languages.copy())
    
    def get_selected_languages(self) -> Set[str]:
        """Get currently selected languages (empty = all)."""
        return self._selected_languages.copy()
    
    def apply_theme(self):
        """Apply current theme to all chips."""
        self._all_chip.apply_theme()
        for chip in self._chips.values():
            chip.apply_theme()


class SummaryStatCard(QFrame):
    """A card displaying a single summary statistic."""
    
    def __init__(self, title: str, value: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("summaryCard")
        self.setFixedHeight(80)
        self.setMinimumWidth(150)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        # Title row with optional icon
        title_text = f"{icon} {title}" if icon else title
        self.title_label = QLabel(title_text)
        self.title_label.setObjectName("cardTitle")
        layout.addWidget(self.title_label)
        
        # Value
        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")
        layout.addWidget(self.value_label)
        
        self._apply_style()
    
    def _apply_style(self):
        colors = get_theme_colors()
        bg = colors["bg_secondary"].name()
        border = colors["border"].name()
        text_sec = colors["text_secondary"].name()
        text_pri = colors["text_primary"].name()
        
        self.setStyleSheet(f"""
            QFrame#summaryCard {{
                background-color: {bg};
                border-radius: 8px;
                border: 1px solid {border};
            }}
            QLabel#cardTitle {{
                color: {text_sec};
                font-size: 11px;
                background: transparent;
                border: none;
            }}
            QLabel#cardValue {{
                color: {text_pri};
                font-size: 20px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """)
    
    def apply_theme(self):
        """Apply current theme colors."""
        self._apply_style()
    
    def set_value(self, value: str):
        """Update the displayed value."""
        self.value_label.setText(value)


class WPMDistributionChart(QWidget):
    """Bar chart showing WPM distribution across sessions."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data: List[Dict] = []  # List of {range_label, count}
        self.hover_index: Optional[int] = None
        
        # Colors will be set from theme
        self._update_colors()
        
        # Margins
        self.margin_left = 45
        self.margin_right = 20
        self.margin_top = 20
        self.margin_bottom = 40
        
        self.setMinimumHeight(200)
        self.setMouseTracking(True)
        self.setStyleSheet("background: transparent;")
    
    def _update_colors(self):
        """Update colors from current theme."""
        colors = get_theme_colors()
        self.bar_color = colors["success"]
        self.bar_hover_color = colors["success"].lighter(120)
        self.bg_color = colors["bg_secondary"]
        self.text_color = colors["text_primary"]
        self.grid_color = colors["border"]
    
    def apply_theme(self):
        """Apply current theme colors."""
        self._update_colors()
        self.update()
    
    def set_data(self, data: List[Dict]):
        """Set the distribution data."""
        self.data = data
        self.update()
    
    def _chart_rect(self) -> QRectF:
        """Get the chart drawing area."""
        return QRectF(
            self.margin_left,
            self.margin_top,
            self.width() - self.margin_left - self.margin_right,
            self.height() - self.margin_top - self.margin_bottom
        )
    
    def _get_bar_rect(self, index: int) -> QRectF:
        """Get the rectangle for a specific bar."""
        if not self.data:
            return QRectF()
        
        rect = self._chart_rect()
        bar_width = rect.width() / len(self.data)
        bar_padding = bar_width * 0.15
        
        max_count = max(d["count"] for d in self.data) if self.data else 1
        if max_count == 0:
            max_count = 1
        
        count = self.data[index]["count"]
        bar_height = (count / max_count) * rect.height()
        
        x = rect.x() + index * bar_width + bar_padding
        y = rect.y() + rect.height() - bar_height
        
        return QRectF(x, y, bar_width - 2 * bar_padding, bar_height)
    
    def mouseMoveEvent(self, event):
        """Track mouse for hover effects."""
        if not self.data:
            self.hover_index = None
            self.update()
            return
        
        rect = self._chart_rect()
        x = event.position().x()
        y = event.position().y()
        
        if rect.contains(x, y):
            bar_width = rect.width() / len(self.data)
            index = int((x - rect.x()) / bar_width)
            if 0 <= index < len(self.data):
                self.hover_index = index
            else:
                self.hover_index = None
        else:
            self.hover_index = None
        
        self.update()
    
    def leaveEvent(self, event):
        """Clear hover when mouse leaves."""
        self.hover_index = None
        self.update()
    
    def paintEvent(self, event):
        """Draw the bar chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), self.bg_color)
        
        rect = self._chart_rect()
        
        if not self.data:
            # Draw empty state
            painter.setPen(QColor("#666666"))
            font = QFont()
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, "No data available")
            return
        
        max_count = max(d["count"] for d in self.data) if self.data else 1
        if max_count == 0:
            max_count = 1
        
        # Calculate nice Y-axis steps
        y_step = max(1, max_count // 5)
        if max_count > 10:
            y_step = ((max_count // 5) // 5 + 1) * 5  # Round to nearest 5
        
        # Draw grid lines and Y-axis labels
        painter.setPen(QPen(self.grid_color, 1))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        
        for i in range(0, max_count + 1, y_step):
            y = rect.y() + rect.height() - (i / max_count) * rect.height()
            painter.drawLine(QPointF(rect.x(), y), QPointF(rect.x() + rect.width(), y))
            
            # Y-axis label
            painter.setPen(self.text_color)
            painter.drawText(QRectF(0, y - 10, self.margin_left - 5, 20),
                           Qt.AlignRight | Qt.AlignVCenter, str(i))
            painter.setPen(QPen(self.grid_color, 1))
        
        # Draw bars
        bar_width = rect.width() / len(self.data)
        
        for i, bucket in enumerate(self.data):
            bar_rect = self._get_bar_rect(i)
            
            # Choose color based on hover
            if i == self.hover_index:
                painter.setBrush(QBrush(self.bar_hover_color))
            else:
                painter.setBrush(QBrush(self.bar_color))
            
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bar_rect, 3, 3)
            
            # X-axis label (WPM range)
            painter.setPen(self.text_color)
            label_x = rect.x() + i * bar_width
            label_rect = QRectF(label_x, rect.y() + rect.height() + 5, bar_width, 30)
            
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(label_rect, Qt.AlignCenter, bucket["range_label"])
        
        # Draw axes
        painter.setPen(QPen(self.grid_color, 2))
        painter.drawLine(QPointF(rect.x(), rect.y()), 
                        QPointF(rect.x(), rect.y() + rect.height()))
        painter.drawLine(QPointF(rect.x(), rect.y() + rect.height()),
                        QPointF(rect.x() + rect.width(), rect.y() + rect.height()))
        
        # Y-axis title
        painter.setPen(self.text_color)
        font.setPointSize(10)
        painter.setFont(font)
        painter.save()
        painter.translate(12, rect.y() + rect.height() / 2)
        painter.rotate(-90)
        painter.drawText(QRectF(-40, -10, 80, 20), Qt.AlignCenter, "Sessions")
        painter.restore()
        
        # X-axis title
        painter.drawText(QRectF(rect.x(), self.height() - 15, rect.width(), 15),
                        Qt.AlignCenter, "WPM Range")
        
        # Draw tooltip if hovering
        if self.hover_index is not None and 0 <= self.hover_index < len(self.data):
            bucket = self.data[self.hover_index]
            bar_rect = self._get_bar_rect(self.hover_index)
            
            tooltip_text = f"{bucket['range_label']} WPM: {bucket['count']} sessions"
            
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            fm = QFontMetrics(font)
            text_width = fm.horizontalAdvance(tooltip_text)
            text_height = fm.height()
            
            tooltip_x = bar_rect.center().x() - text_width / 2 - 8
            tooltip_y = bar_rect.y() - text_height - 15
            
            # Keep tooltip on screen
            if tooltip_x < 5:
                tooltip_x = 5
            if tooltip_x + text_width + 16 > self.width():
                tooltip_x = self.width() - text_width - 20
            if tooltip_y < 5:
                tooltip_y = bar_rect.y() + bar_rect.height() + 5
            
            # Tooltip background
            tooltip_rect = QRectF(tooltip_x, tooltip_y, text_width + 16, text_height + 8)
            painter.setPen(Qt.NoPen)
            tooltip_bg = QColor("#2d2d2d")
            painter.setBrush(tooltip_bg)
            painter.drawRoundedRect(tooltip_rect, 4, 4)
            
            # Tooltip border
            painter.setPen(QPen(self.bar_color, 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(tooltip_rect, 4, 4)
            
            # Tooltip text
            painter.setPen(self.text_color)
            painter.drawText(tooltip_rect, Qt.AlignCenter, tooltip_text)


class WPMAccuracyScatterPlot(QWidget):
    """Scatter plot showing WPM and Accuracy over time with dual Y-axes."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data: List[Dict] = []  # List of session data
        self.hover_info: Optional[Tuple[int, str]] = None  # (index, 'wpm' or 'acc' or 'wpm_trend' or 'acc_trend')
        
        # Colors - will be set from theme
        self._update_colors()
        
        # Margins - increased right margin for axis title spacing
        self.margin_left = 50
        self.margin_right = 60
        self.margin_top = 20
        self.margin_bottom = 45
        
        self.setMinimumHeight(250)
        self.setMouseTracking(True)
        self.setStyleSheet("background: transparent;")
    
    def _update_colors(self):
        """Update colors from current theme."""
        colors = get_theme_colors()
        self.wpm_color = colors["success"]
        self.acc_color = colors["info"]
        self.bg_color = colors["bg_secondary"]
        self.text_color = colors["text_primary"]
        self.grid_color = colors["border"]
    
    def apply_theme(self):
        """Apply current theme colors."""
        self._update_colors()
        self.update()
    
    def set_data(self, data: List[Dict]):
        """Set the session data."""
        self.data = data
        self.update()
    
    def _chart_rect(self) -> QRectF:
        """Get the chart drawing area."""
        return QRectF(
            self.margin_left,
            self.margin_top,
            self.width() - self.margin_left - self.margin_right,
            self.height() - self.margin_top - self.margin_bottom
        )
    
    def _date_to_x(self, index: int) -> float:
        """Convert data index to X coordinate."""
        rect = self._chart_rect()
        if len(self.data) <= 1:
            return rect.x() + rect.width() / 2
        return rect.x() + (index / (len(self.data) - 1)) * rect.width()
    
    def _wpm_to_y(self, wpm: float, max_wpm: float) -> float:
        """Convert WPM to Y coordinate (left axis, 0 at bottom, max at top)."""
        rect = self._chart_rect()
        if max_wpm == 0:
            max_wpm = 100
        return rect.y() + rect.height() - (wpm / max_wpm) * rect.height()
    
    def _acc_to_y(self, acc: float) -> float:
        """Convert accuracy to Y coordinate (right axis, 100% at top, 0% at bottom - INVERTED display)."""
        rect = self._chart_rect()
        # Inverted: 100% at top, 0% at bottom (visually shows high accuracy = high position)
        # But labels go 0% at top to 100% at bottom
        return rect.y() + (acc / 100) * rect.height()
    
    def _calculate_trend_line(self, values: List[float]) -> Tuple[float, float]:
        """Calculate linear regression for trend line. Returns (slope, intercept)."""
        if len(values) < 2:
            return 0, values[0] if values else 0
        
        n = len(values)
        x_vals = list(range(n))
        
        # Calculate means
        x_mean = sum(x_vals) / n
        y_mean = sum(values) / n
        
        # Calculate slope and intercept
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, values))
        denominator = sum((x - x_mean) ** 2 for x in x_vals)
        
        if denominator == 0:
            return 0, y_mean
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        return slope, intercept
    
    def _get_trend_y_at_x(self, x_idx: float, slope: float, intercept: float) -> float:
        """Get the Y value on trend line at a given x index."""
        return slope * x_idx + intercept
    
    def mouseMoveEvent(self, event):
        """Track mouse for hover effects."""
        if not self.data:
            self.hover_info = None
            self.update()
            return
        
        rect = self._chart_rect()
        x = event.position().x()
        y = event.position().y()
        
        # Calculate max WPM for scaling
        max_wpm = max(d["wpm"] for d in self.data) if self.data else 100
        max_wpm = ((int(max_wpm) // 20) + 1) * 20  # Round up to nearest 20
        
        # Calculate trend lines
        wpm_values = [d["wpm"] for d in self.data]
        acc_values = [d["accuracy"] for d in self.data]
        wpm_slope, wpm_intercept = self._calculate_trend_line(wpm_values)
        acc_slope, acc_intercept = self._calculate_trend_line(acc_values)
        
        # Check each data point first (higher priority)
        closest_dist = float('inf')
        closest_info = None
        
        for i, d in enumerate(self.data):
            px = self._date_to_x(i)
            
            # Check WPM point
            py_wpm = self._wpm_to_y(d["wpm"], max_wpm)
            dist_wpm = ((x - px) ** 2 + (y - py_wpm) ** 2) ** 0.5
            if dist_wpm < 15 and dist_wpm < closest_dist:
                closest_dist = dist_wpm
                closest_info = (i, 'wpm')
            
            # Check accuracy point
            py_acc = self._acc_to_y(d["accuracy"])
            dist_acc = ((x - px) ** 2 + (y - py_acc) ** 2) ** 0.5
            if dist_acc < 15 and dist_acc < closest_dist:
                closest_dist = dist_acc
                closest_info = (i, 'acc')
        
        # If no data point is close, check trend lines
        if closest_info is None and len(self.data) >= 2 and rect.contains(x, y):
            # Find the x index corresponding to mouse position
            x_ratio = (x - rect.x()) / rect.width()
            x_idx = x_ratio * (len(self.data) - 1)
            
            # Get trend line Y values at this x position
            wpm_trend_val = self._get_trend_y_at_x(x_idx, wpm_slope, wpm_intercept)
            acc_trend_val = self._get_trend_y_at_x(x_idx, acc_slope, acc_intercept)
            
            trend_wpm_y = self._wpm_to_y(wpm_trend_val, max_wpm)
            trend_acc_y = self._acc_to_y(acc_trend_val)
            
            # Check distance to WPM trend line
            if abs(y - trend_wpm_y) < 8:
                closest_info = (int(x_idx), 'wpm_trend')
            # Check distance to accuracy trend line
            elif abs(y - trend_acc_y) < 8:
                closest_info = (int(x_idx), 'acc_trend')
        
        self.hover_info = closest_info
        self.update()
    
    def leaveEvent(self, event):
        """Clear hover when mouse leaves."""
        self.hover_info = None
        self.update()
    
    def paintEvent(self, event):
        """Draw the scatter plot."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), self.bg_color)
        
        rect = self._chart_rect()
        
        if not self.data:
            # Draw empty state
            painter.setPen(QColor("#666666"))
            font = QFont()
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, "No session data available")
            return
        
        # Calculate max WPM for scaling
        max_wpm = max(d["wpm"] for d in self.data)
        max_wpm = ((int(max_wpm) // 20) + 1) * 20  # Round up to nearest 20
        
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        
        # Draw grid lines
        painter.setPen(QPen(self.grid_color, 1))
        
        # Horizontal grid (WPM scale)
        wpm_step = max(20, max_wpm // 5)
        for wpm in range(0, int(max_wpm) + 1, wpm_step):
            y = self._wpm_to_y(wpm, max_wpm)
            painter.drawLine(QPointF(rect.x(), y), QPointF(rect.x() + rect.width(), y))
        
        # Draw axes
        painter.setPen(QPen(self.grid_color, 2))
        painter.drawRect(rect)
        
        # Left Y-axis labels (WPM - green)
        painter.setPen(self.wpm_color)
        for wpm in range(0, int(max_wpm) + 1, wpm_step):
            y = self._wpm_to_y(wpm, max_wpm)
            painter.drawText(QRectF(0, y - 10, self.margin_left - 5, 20),
                           Qt.AlignRight | Qt.AlignVCenter, str(wpm))
        
        # Right Y-axis labels (Accuracy - blue, 0-100%)
        painter.setPen(self.acc_color)
        for acc in range(0, 101, 20):
            y = self._acc_to_y(acc)
            painter.drawText(QRectF(rect.x() + rect.width() + 5, y - 10, self.margin_right - 5, 20),
                           Qt.AlignLeft | Qt.AlignVCenter, f"{acc}%")
        
        # X-axis labels (dates)
        painter.setPen(self.text_color)
        font.setPointSize(8)
        painter.setFont(font)
        
        # Show a subset of date labels to avoid crowding
        num_labels = min(8, len(self.data))
        if len(self.data) > 1:
            step = max(1, len(self.data) // num_labels)
            for i in range(0, len(self.data), step):
                x = self._date_to_x(i)
                date_str = self.data[i]["date"]
                # Shorten date format
                if len(date_str) >= 10:
                    date_str = date_str[5:10]  # MM-DD format
                painter.drawText(QRectF(x - 25, rect.y() + rect.height() + 5, 50, 20),
                               Qt.AlignCenter, date_str)
        
        # Draw data points
        hover_idx, hover_type = self.hover_info if self.hover_info else (None, None)
        
        for i, d in enumerate(self.data):
            px = self._date_to_x(i)
            
            # WPM point (green circle)
            py_wpm = self._wpm_to_y(d["wpm"], max_wpm)
            is_hovered = (hover_idx == i and hover_type == 'wpm')
            size = 5 if is_hovered else 3
            
            painter.setPen(QPen(self.wpm_color, 1.5 if is_hovered else 1))
            painter.setBrush(QBrush(self.wpm_color) if is_hovered else QBrush(self.bg_color))
            painter.drawEllipse(QPointF(px, py_wpm), size, size)
            
            # Accuracy point (blue circle)
            py_acc = self._acc_to_y(d["accuracy"])
            is_hovered = (hover_idx == i and hover_type == 'acc')
            size = 5 if is_hovered else 3
            
            painter.setPen(QPen(self.acc_color, 1.5 if is_hovered else 1))
            painter.setBrush(QBrush(self.acc_color) if is_hovered else QBrush(self.bg_color))
            painter.drawEllipse(QPointF(px, py_acc), size, size)
        
        # Draw trend lines (best-fit lines)
        if len(self.data) >= 2:
            # Calculate trend lines
            wpm_values = [d["wpm"] for d in self.data]
            acc_values = [d["accuracy"] for d in self.data]
            
            wpm_slope, wpm_intercept = self._calculate_trend_line(wpm_values)
            acc_slope, acc_intercept = self._calculate_trend_line(acc_values)
            
            # Start and end X positions (screen coordinates)
            x_start = self._date_to_x(0)
            x_end = self._date_to_x(len(self.data) - 1)
            
            # WPM trend line (green dashed)
            wpm_y_start = self._wpm_to_y(wpm_intercept, max_wpm)
            wpm_y_end = self._wpm_to_y(wpm_slope * (len(self.data) - 1) + wpm_intercept, max_wpm)
            
            wpm_trend_pen = QPen(self.wpm_color, 2, Qt.DashLine)
            is_wpm_trend_hovered = hover_type == 'wpm_trend'
            if is_wpm_trend_hovered:
                wpm_trend_pen.setWidth(3)
            painter.setPen(wpm_trend_pen)
            painter.drawLine(QPointF(x_start, wpm_y_start), QPointF(x_end, wpm_y_end))
            
            # Accuracy trend line (blue dashed)
            acc_y_start = self._acc_to_y(acc_intercept)
            acc_y_end = self._acc_to_y(acc_slope * (len(self.data) - 1) + acc_intercept)
            
            acc_trend_pen = QPen(self.acc_color, 2, Qt.DashLine)
            is_acc_trend_hovered = hover_type == 'acc_trend'
            if is_acc_trend_hovered:
                acc_trend_pen.setWidth(3)
            painter.setPen(acc_trend_pen)
            painter.drawLine(QPointF(x_start, acc_y_start), QPointF(x_end, acc_y_end))
        
        # Axis titles
        font.setPointSize(10)
        painter.setFont(font)
        
        # Left Y-axis title (WPM)
        painter.setPen(self.wpm_color)
        painter.save()
        painter.translate(12, rect.y() + rect.height() / 2)
        painter.rotate(-90)
        painter.drawText(QRectF(-30, -10, 60, 20), Qt.AlignCenter, "WPM")
        painter.restore()
        
        # Right Y-axis title (Accuracy)
        painter.setPen(self.acc_color)
        painter.save()
        painter.translate(self.width() - 12, rect.y() + rect.height() / 2)
        painter.rotate(90)
        painter.drawText(QRectF(-40, -10, 80, 20), Qt.AlignCenter, "Accuracy")
        painter.restore()
        
        # X-axis title
        painter.setPen(self.text_color)
        painter.drawText(QRectF(rect.x(), self.height() - 15, rect.width(), 15),
                        Qt.AlignCenter, "Date")
        
        # Draw tooltip if hovering
        if self.hover_info is not None:
            idx, point_type = self.hover_info
            
            # Handle trend line tooltips
            if point_type in ('wpm_trend', 'acc_trend'):
                # Calculate trend line slope to describe the trend
                if point_type == 'wpm_trend':
                    wpm_values = [d["wpm"] for d in self.data]
                    slope, intercept = self._calculate_trend_line(wpm_values)
                    if abs(slope) < 0.01:
                        trend_desc = "Your WPM is staying steady"
                    elif slope > 0:
                        trend_desc = f"Your WPM is increasing (+{slope:.2f}/session)"
                    else:
                        trend_desc = f"Your WPM is decreasing ({slope:.2f}/session)"
                    tooltip_text = f"WPM Trend Line\n{trend_desc}"
                    border_color = self.wpm_color
                else:
                    acc_values = [d["accuracy"] for d in self.data]
                    slope, intercept = self._calculate_trend_line(acc_values)
                    if abs(slope) < 0.01:
                        trend_desc = "Your accuracy is staying steady"
                    elif slope > 0:
                        trend_desc = f"Your accuracy is improving (+{slope:.2f}%/session)"
                    else:
                        trend_desc = f"Your accuracy is declining ({slope:.2f}%/session)"
                    tooltip_text = f"Accuracy Trend Line\n{trend_desc}"
                    border_color = self.acc_color
                
                # Position tooltip near mouse cursor (use center of chart)
                px = rect.x() + rect.width() / 2
                py = rect.y() + rect.height() / 2
                
            elif 0 <= idx < len(self.data):
                d = self.data[idx]
                px = self._date_to_x(idx)
                
                if point_type == 'wpm':
                    py = self._wpm_to_y(d["wpm"], max_wpm)
                    file_name = Path(d["file_path"]).name if d.get("file_path") else "Unknown"
                    tooltip_text = f"{d['date']} | {d['wpm']:.1f} WPM | {file_name}"
                    border_color = self.wpm_color
                else:
                    py = self._acc_to_y(d["accuracy"])
                    correct = d.get("correct", 0)
                    incorrect = d.get("incorrect", 0)
                    total = d.get("total", correct + incorrect)
                    if total > 0:
                        correct_pct = correct / total * 100
                        incorrect_pct = incorrect / total * 100
                    else:
                        correct_pct = incorrect_pct = 0
                    file_name = Path(d["file_path"]).name if d.get("file_path") else "Unknown"
                    tooltip_text = f"{d['date']} | {file_name}\n{correct} ({correct_pct:.0f}%) ✓ | {incorrect} ({incorrect_pct:.0f}%) ✗ | {total} total"
                    border_color = self.acc_color
            else:
                return  # Invalid index, skip tooltip
            
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)
            fm = QFontMetrics(font)
            
            # Handle multi-line tooltip
            lines = tooltip_text.split('\n')
            max_width = max(fm.horizontalAdvance(line) for line in lines)
            text_height = fm.height() * len(lines)
            
            tooltip_x = px + 10
            tooltip_y = py - text_height - 15
            
            # Keep tooltip on screen
            if tooltip_x + max_width + 16 > self.width():
                tooltip_x = px - max_width - 25
            if tooltip_y < 5:
                tooltip_y = py + 10
            
            # Tooltip background
            tooltip_rect = QRectF(tooltip_x, tooltip_y, max_width + 16, text_height + 12)
            painter.setPen(Qt.NoPen)
            tooltip_bg = QColor("#2d2d2d")
            painter.setBrush(tooltip_bg)
            painter.drawRoundedRect(tooltip_rect, 4, 4)
            
            # Tooltip border
            painter.setPen(QPen(border_color, 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(tooltip_rect, 4, 4)
            
            # Tooltip text
            painter.setPen(self.text_color)
            y_offset = tooltip_rect.y() + 6
            for line in lines:
                painter.drawText(QRectF(tooltip_rect.x() + 8, y_offset, max_width, fm.height()),
                               Qt.AlignLeft | Qt.AlignVCenter, line)
                y_offset += fm.height()


class DateRangeChart(QWidget):
    """Combined bar + line chart showing daily metrics over a date range."""
    
    # Signal emitted when options change (date range or dropdowns)
    options_changed = Signal()
    
    # Left Y-axis options (bar chart)
    LEFT_OPTIONS = [
        ("total_chars", "Characters Typed"),
        ("completed_sessions", "Sessions Completed"),
    ]
    
    # Right Y-axis options (line chart)
    RIGHT_OPTIONS = [
        ("avg_wpm", "Average WPM"),
        ("highest_wpm", "Highest WPM"),
        ("lowest_wpm", "Lowest WPM"),
        ("avg_accuracy", "Average Accuracy"),
        ("highest_accuracy", "Highest Accuracy"),
        ("lowest_accuracy", "Lowest Accuracy"),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        
        # Data
        self.data: List[Dict[str, Any]] = []
        self.hover_info: Optional[Tuple[int, str]] = None  # (index, 'bar' or 'line')
        
        # Colors - will be set from theme
        self._update_colors()
        
        # Margins
        self.margin_left = 70
        self.margin_right = 70
        self.margin_top = 50
        self.margin_bottom = 45
        
        # Current selections
        self._left_metric = "total_chars"
        self._right_metric = "avg_wpm"
        
        # Create controls
        self._setup_controls()
    
    def _update_colors(self):
        """Update colors from current theme."""
        colors = get_theme_colors()
        self.bg_color = colors["bg_secondary"]
        self.grid_color = colors["border"]
        self.text_color = colors["text_primary"]
        self.bar_color = colors["warning"]  # Orange/yellow for bars
        self.line_color = colors["info"]  # Blue for line
    
    def apply_theme(self):
        """Apply current theme colors."""
        self._update_colors()
        self._update_control_styles()
        self.update()
    
    def _get_combo_style(self) -> str:
        """Get theme-based combo box style."""
        colors = get_theme_colors()
        bg = colors["bg_tertiary"].name()
        text = colors["text_primary"].name()
        border = colors["border"].name()
        hover = colors["accent"].name()
        
        return f"""
            QComboBox {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QComboBox:hover {{ border-color: {hover}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {text};
                margin-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg};
                color: {text};
                selection-background-color: {colors["bg_primary"].name()};
                border: 1px solid {border};
            }}
        """
    
    def _get_date_style(self) -> str:
        """Get theme-based date picker style."""
        colors = get_theme_colors()
        bg = colors["bg_tertiary"].name()
        text = colors["text_primary"].name()
        border = colors["border"].name()
        hover = colors["accent"].name()
        
        return f"""
            QDateEdit {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QDateEdit:hover {{ border-color: {hover}; }}
            QDateEdit::drop-down {{ border: none; width: 20px; }}
            QDateEdit::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {text};
                margin-right: 6px;
            }}
        """
    
    def _update_control_styles(self):
        """Update control widget styles."""
        colors = get_theme_colors()
        combo_style = self._get_combo_style()
        date_style = self._get_date_style()
        
        self.start_date.setStyleSheet(date_style)
        self.end_date.setStyleSheet(date_style)
        self.left_combo.setStyleSheet(combo_style)
        self.right_combo.setStyleSheet(combo_style)
        
        # Update labels
        text_sec = colors["text_secondary"].name()
        for label in [self._start_label, self._end_label]:
            label.setStyleSheet(f"color: {text_sec}; font-size: 11px;")
        
        self._left_label.setStyleSheet(f"color: {self.bar_color.name()}; font-size: 11px; font-weight: bold;")
        self._right_label.setStyleSheet(f"color: {self.line_color.name()}; font-size: 11px; font-weight: bold;")
    
    def _setup_controls(self):
        """Set up the control bar at the top."""
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(8, 8, 8, 0)
        controls_layout.setSpacing(12)
        
        # Get theme-based styles
        colors = get_theme_colors()
        combo_style = self._get_combo_style()
        date_style = self._get_date_style()
        text_sec = colors["text_secondary"].name()
        
        # Start date picker
        self._start_label = QLabel("From:")
        self._start_label.setStyleSheet(f"color: {text_sec}; font-size: 11px;")
        controls_layout.addWidget(self._start_label)
        
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate().addDays(-30))  # Default to 30 days ago
        self.start_date.setFixedWidth(110)
        self.start_date.setStyleSheet(date_style)
        self.start_date.dateChanged.connect(self._on_date_changed)
        controls_layout.addWidget(self.start_date)
        
        # End date picker
        self._end_label = QLabel("To:")
        self._end_label.setStyleSheet(f"color: {text_sec}; font-size: 11px;")
        controls_layout.addWidget(self._end_label)
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())  # Default to today
        self.end_date.setFixedWidth(110)
        self.end_date.setStyleSheet(date_style)
        self.end_date.dateChanged.connect(self._on_date_changed)
        controls_layout.addWidget(self.end_date)
        
        controls_layout.addSpacing(16)
        
        # Left Y-axis dropdown (bars)
        self._left_label = QLabel("Bars:")
        self._left_label.setStyleSheet(f"color: {self.bar_color.name()}; font-size: 11px; font-weight: bold;")
        controls_layout.addWidget(self._left_label)
        
        self.left_combo = QComboBox()
        for key, label in self.LEFT_OPTIONS:
            self.left_combo.addItem(label)
        self.left_combo.setCurrentIndex(0)
        self.left_combo.setFixedWidth(140)
        self.left_combo.setStyleSheet(combo_style)
        self.left_combo.currentIndexChanged.connect(self._on_left_changed)
        controls_layout.addWidget(self.left_combo)
        
        controls_layout.addSpacing(8)
        
        # Right Y-axis dropdown (line)
        self._right_label = QLabel("Line:")
        self._right_label.setStyleSheet(f"color: {self.line_color.name()}; font-size: 11px; font-weight: bold;")
        controls_layout.addWidget(self._right_label)
        
        self.right_combo = QComboBox()
        for key, label in self.RIGHT_OPTIONS:
            self.right_combo.addItem(label)
        self.right_combo.setCurrentIndex(0)
        self.right_combo.setFixedWidth(140)
        self.right_combo.setStyleSheet(combo_style)
        self.right_combo.currentIndexChanged.connect(self._on_right_changed)
        controls_layout.addWidget(self.right_combo)
        
        controls_layout.addStretch()
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addLayout(controls_layout)
        main_layout.addStretch()
    
    def set_default_dates(self, first_date: Optional[str]):
        """Set default date range from first session date to today."""
        if first_date:
            parts = first_date.split("-")
            if len(parts) == 3:
                self.start_date.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
        self.end_date.setDate(QDate.currentDate())
    
    def _on_date_changed(self):
        """Handle date picker changes."""
        self.options_changed.emit()
    
    def _on_left_changed(self, index: int):
        """Handle left dropdown change."""
        self._left_metric = self.LEFT_OPTIONS[index][0]
        self.update()
    
    def _on_right_changed(self, index: int):
        """Handle right dropdown change."""
        self._right_metric = self.RIGHT_OPTIONS[index][0]
        self.update()
    
    def get_date_range(self) -> Tuple[str, str]:
        """Get the selected date range as (start, end) strings."""
        return (
            self.start_date.date().toString("yyyy-MM-dd"),
            self.end_date.date().toString("yyyy-MM-dd")
        )
    
    def set_data(self, data: List[Dict[str, Any]]):
        """Set the chart data."""
        self.data = data
        self.hover_info = None
        self.update()
    
    def _chart_rect(self) -> QRectF:
        """Get the rectangle for the chart area."""
        return QRectF(
            self.margin_left,
            self.margin_top,
            self.width() - self.margin_left - self.margin_right,
            self.height() - self.margin_top - self.margin_bottom
        )
    
    def _x_to_pos(self, idx: int) -> float:
        """Convert data index to X position (center of bar)."""
        rect = self._chart_rect()
        if len(self.data) <= 1:
            return rect.x() + rect.width() / 2
        bar_width = rect.width() / len(self.data)
        return rect.x() + bar_width * idx + bar_width / 2
    
    def _bar_width(self) -> float:
        """Get the width of each bar."""
        rect = self._chart_rect()
        if len(self.data) == 0:
            return 0
        return max(4, (rect.width() / len(self.data)) * 0.7)
    
    def _left_to_y(self, val: float, max_val: float) -> float:
        """Convert left axis value to Y position."""
        rect = self._chart_rect()
        if max_val == 0:
            return rect.y() + rect.height()
        return rect.y() + rect.height() - (val / max_val) * rect.height()
    
    def _right_to_y(self, val: float, max_val: float) -> float:
        """Convert right axis value to Y position."""
        rect = self._chart_rect()
        if max_val == 0:
            return rect.y() + rect.height()
        return rect.y() + rect.height() - (val / max_val) * rect.height()
    
    def _is_right_metric_accuracy(self) -> bool:
        """Check if right metric is an accuracy metric."""
        return "accuracy" in self._right_metric
    
    def mouseMoveEvent(self, event):
        """Track mouse for hover tooltips."""
        x, y = event.position().x(), event.position().y()
        rect = self._chart_rect()
        
        if not rect.contains(x, y) or not self.data:
            self.hover_info = None
            self.update()
            return
        
        # Calculate max values
        max_left = max((d[self._left_metric] for d in self.data), default=1)
        max_left = max(1, max_left)
        
        if self._is_right_metric_accuracy():
            max_right = 100
        else:
            max_right = max((d[self._right_metric] for d in self.data), default=1)
            max_right = ((int(max_right) // 20) + 1) * 20
        
        closest_dist = float('inf')
        closest_info = None
        bar_width = self._bar_width()
        
        for i, d in enumerate(self.data):
            px = self._x_to_pos(i)
            
            # Check bar hover (within bar width)
            if abs(x - px) < bar_width / 2:
                bar_y = self._left_to_y(d[self._left_metric], max_left)
                if y >= bar_y and y <= rect.y() + rect.height():
                    closest_info = (i, 'bar')
                    break
            
            # Check line point
            py_line = self._right_to_y(d[self._right_metric], max_right)
            dist = ((x - px) ** 2 + (y - py_line) ** 2) ** 0.5
            if dist < 12 and dist < closest_dist:
                closest_dist = dist
                closest_info = (i, 'line')
        
        self.hover_info = closest_info
        self.update()
    
    def leaveEvent(self, event):
        """Clear hover when mouse leaves."""
        self.hover_info = None
        self.update()
    
    def paintEvent(self, event):
        """Draw the combined bar + line chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), self.bg_color)
        
        rect = self._chart_rect()
        
        if not self.data:
            painter.setPen(QColor("#666666"))
            font = QFont()
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, "No data for selected date range")
            return
        
        # Calculate max values
        max_left = max((d[self._left_metric] for d in self.data), default=1)
        max_left = max(1, max_left)
        # Round up to nice number
        magnitude = 10 ** (len(str(int(max_left))) - 1)
        max_left = ((int(max_left) // magnitude) + 1) * magnitude
        
        if self._is_right_metric_accuracy():
            max_right = 100
        else:
            max_right = max((d[self._right_metric] for d in self.data), default=1)
            max_right = ((int(max_right) // 20) + 1) * 20
        
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        
        # Draw grid lines
        painter.setPen(QPen(self.grid_color, 1))
        for i in range(6):
            y = rect.y() + (i / 5) * rect.height()
            painter.drawLine(QPointF(rect.x(), y), QPointF(rect.x() + rect.width(), y))
        
        # Draw axes border
        painter.setPen(QPen(self.grid_color, 2))
        painter.drawRect(rect)
        
        # Left Y-axis labels (bar metric - orange)
        painter.setPen(self.bar_color)
        left_step = max_left / 5
        for i in range(6):
            val = left_step * (5 - i)
            y = rect.y() + (i / 5) * rect.height()
            label = self._format_number(val)
            painter.drawText(QRectF(0, y - 10, self.margin_left - 8, 20),
                           Qt.AlignRight | Qt.AlignVCenter, label)
        
        # Right Y-axis labels (line metric - blue)
        painter.setPen(self.line_color)
        right_step = max_right / 5
        for i in range(6):
            val = right_step * (5 - i)
            y = rect.y() + (i / 5) * rect.height()
            if self._is_right_metric_accuracy():
                label = f"{val:.0f}%"
            else:
                label = f"{val:.0f}"
            painter.drawText(QRectF(rect.x() + rect.width() + 8, y - 10, self.margin_right - 8, 20),
                           Qt.AlignLeft | Qt.AlignVCenter, label)
        
        # X-axis labels (dates)
        painter.setPen(self.text_color)
        font.setPointSize(8)
        painter.setFont(font)
        
        num_labels = min(10, len(self.data))
        step = max(1, len(self.data) // num_labels)
        for i in range(0, len(self.data), step):
            x = self._x_to_pos(i)
            date_str = self.data[i]["date"]
            if len(date_str) >= 10:
                date_str = date_str[5:10]  # MM-DD
            painter.drawText(QRectF(x - 25, rect.y() + rect.height() + 5, 50, 20),
                           Qt.AlignCenter, date_str)
        
        hover_idx, hover_type = self.hover_info if self.hover_info else (None, None)
        bar_width = self._bar_width()
        
        # Draw bars (left metric)
        for i, d in enumerate(self.data):
            px = self._x_to_pos(i)
            val = d[self._left_metric]
            bar_top = self._left_to_y(val, max_left)
            bar_bottom = rect.y() + rect.height()
            bar_height = bar_bottom - bar_top
            
            is_hovered = (hover_idx == i and hover_type == 'bar')
            
            # Bar fill
            bar_rect = QRectF(px - bar_width / 2, bar_top, bar_width, bar_height)
            if is_hovered:
                painter.setBrush(self.bar_color.lighter(130))
            else:
                painter.setBrush(self.bar_color)
            painter.setPen(Qt.NoPen)
            painter.drawRect(bar_rect)
        
        # Draw line (right metric)
        if len(self.data) >= 1:
            # Draw connecting line
            if len(self.data) >= 2:
                painter.setPen(QPen(self.line_color, 2))
                for i in range(len(self.data) - 1):
                    x1 = self._x_to_pos(i)
                    y1 = self._right_to_y(self.data[i][self._right_metric], max_right)
                    x2 = self._x_to_pos(i + 1)
                    y2 = self._right_to_y(self.data[i + 1][self._right_metric], max_right)
                    painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            
            # Draw points
            for i, d in enumerate(self.data):
                px = self._x_to_pos(i)
                py = self._right_to_y(d[self._right_metric], max_right)
                is_hovered = (hover_idx == i and hover_type == 'line')
                size = 5 if is_hovered else 3
                
                painter.setPen(QPen(self.line_color, 1.5 if is_hovered else 1))
                painter.setBrush(QBrush(self.line_color) if is_hovered else QBrush(self.bg_color))
                painter.drawEllipse(QPointF(px, py), size, size)
        
        # Axis titles
        font.setPointSize(10)
        painter.setFont(font)
        
        # Left Y-axis title
        painter.setPen(self.bar_color)
        painter.save()
        painter.translate(14, rect.y() + rect.height() / 2)
        painter.rotate(-90)
        left_title = dict(self.LEFT_OPTIONS).get(self._left_metric, "")
        painter.drawText(QRectF(-60, -10, 120, 20), Qt.AlignCenter, left_title)
        painter.restore()
        
        # Right Y-axis title
        painter.setPen(self.line_color)
        painter.save()
        painter.translate(self.width() - 14, rect.y() + rect.height() / 2)
        painter.rotate(90)
        right_title = dict(self.RIGHT_OPTIONS).get(self._right_metric, "")
        painter.drawText(QRectF(-60, -10, 120, 20), Qt.AlignCenter, right_title)
        painter.restore()
        
        # Draw tooltip if hovering
        if self.hover_info is not None:
            idx, point_type = self.hover_info
            if 0 <= idx < len(self.data):
                d = self.data[idx]
                px = self._x_to_pos(idx)
                
                if point_type == 'bar':
                    py = self._left_to_y(d[self._left_metric], max_left)
                    left_label = dict(self.LEFT_OPTIONS).get(self._left_metric, "")
                    val = d[self._left_metric]
                    tooltip_text = f"{d['date']}\n{left_label}: {self._format_number(val)}"
                    border_color = self.bar_color
                else:
                    py = self._right_to_y(d[self._right_metric], max_right)
                    right_label = dict(self.RIGHT_OPTIONS).get(self._right_metric, "")
                    val = d[self._right_metric]
                    if self._is_right_metric_accuracy():
                        tooltip_text = f"{d['date']}\n{right_label}: {val:.1f}%"
                    else:
                        tooltip_text = f"{d['date']}\n{right_label}: {val:.1f}"
                    border_color = self.line_color
                
                font.setPointSize(9)
                font.setBold(True)
                painter.setFont(font)
                fm = QFontMetrics(font)
                
                lines = tooltip_text.split('\n')
                max_width = max(fm.horizontalAdvance(line) for line in lines)
                text_height = fm.height() * len(lines)
                
                tooltip_x = px + 10
                tooltip_y = py - text_height - 15
                
                if tooltip_x + max_width + 16 > self.width():
                    tooltip_x = px - max_width - 25
                if tooltip_y < self.margin_top:
                    tooltip_y = py + 10
                
                tooltip_rect = QRectF(tooltip_x, tooltip_y, max_width + 16, text_height + 12)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor("#2d2d2d"))
                painter.drawRoundedRect(tooltip_rect, 4, 4)
                
                painter.setPen(QPen(border_color, 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(tooltip_rect, 4, 4)
                
                painter.setPen(self.text_color)
                y_offset = tooltip_rect.y() + 6
                for line in lines:
                    painter.drawText(QRectF(tooltip_rect.x() + 8, y_offset, max_width, fm.height()),
                                   Qt.AlignLeft | Qt.AlignVCenter, line)
                    y_offset += fm.height()
    
    def _format_number(self, val: float) -> str:
        """Format large numbers with K/M suffixes."""
        if val >= 1_000_000:
            return f"{val / 1_000_000:.1f}M"
        elif val >= 1_000:
            return f"{val / 1_000:.1f}K"
        else:
            return f"{val:.0f}"


class StatsTab(QWidget):
    """Tab providing visualizations and statistics of typing performance."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_languages: Set[str] = set()
        
        # Get theme colors
        colors = get_theme_colors()
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Header
        self.header = QLabel("Statistics")
        self.header.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {colors['text_primary'].name()};")
        main_layout.addWidget(self.header)
        
        # Language filter bar
        self.filter_bar = LanguageFilterBar()
        self.filter_bar.filter_changed.connect(self._on_filter_changed)
        main_layout.addWidget(self.filter_bar)
        
        # Scroll area for content
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        # Content widget
        self.content = QWidget()
        self.content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(24)
        
        # Summary stats section
        self._create_summary_section()
        
        # Placeholder for charts (Phase 2+)
        self._create_chart_placeholders()
        
        self.content_layout.addStretch()
        
        self.scroll.setWidget(self.content)
        main_layout.addWidget(self.scroll)
        
        # Load initial data
        self.refresh()
    
    def _create_summary_section(self):
        """Create the summary statistics section."""
        colors = get_theme_colors()
        self.summary_label = QLabel("Summary")
        self.summary_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {colors['text_secondary'].name()};")
        self.content_layout.addWidget(self.summary_label)
        
        # Grid of summary cards (2 rows of 5)
        self.summary_cards: Dict[str, SummaryStatCard] = {}
        
        # Row 1: Session counts and WPM stats
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        
        cards_row1 = [
            ("total_completed", "Completed Sessions", "✓"),
            ("total_incomplete", "Incomplete Sessions", "⏸"),
            ("highest_wpm", "Highest WPM", "🚀"),
            ("lowest_wpm", "Lowest WPM", "🐢"),
            ("avg_wpm", "Average WPM", "📊"),
        ]
        
        for key, title, icon in cards_row1:
            card = SummaryStatCard(title, "-", icon)
            self.summary_cards[key] = card
            row1.addWidget(card)
        
        row1.addStretch()
        self.content_layout.addLayout(row1)
        
        # Row 2: Accuracy stats and records
        row2 = QHBoxLayout()
        row2.setSpacing(12)
        
        cards_row2 = [
            ("highest_acc", "Highest Accuracy", "🎯"),
            ("lowest_acc", "Lowest Accuracy", "📉"),
            ("avg_acc", "Average Accuracy", "📈"),
            ("most_chars_day", "Most Chars/Day", "⌨"),
            ("most_sessions_day", "Most Sessions/Day", "🔥"),
        ]
        
        for key, title, icon in cards_row2:
            card = SummaryStatCard(title, "-", icon)
            self.summary_cards[key] = card
            row2.addWidget(card)
        
        row2.addStretch()
        self.content_layout.addLayout(row2)
    
    def _create_chart_placeholders(self):
        """Create chart widgets."""
        colors = get_theme_colors()
        label_style = f"font-size: 16px; font-weight: bold; color: {colors['text_secondary'].name()}; margin-top: 16px;"
        
        # WPM & Accuracy Scatter Plot (real implementation)
        self.scatter_label = QLabel("WPM & Accuracy Over Time")
        self.scatter_label.setStyleSheet(label_style)
        self.content_layout.addWidget(self.scatter_label)
        
        self.scatter_chart = WPMAccuracyScatterPlot()
        self.scatter_chart.setFixedHeight(280)
        self.content_layout.addWidget(self.scatter_chart)
        
        # WPM Distribution Bar Chart (real implementation)
        self.bar_label = QLabel("WPM Distribution")
        self.bar_label.setStyleSheet(label_style)
        self.content_layout.addWidget(self.bar_label)
        
        self.wpm_distribution_chart = WPMDistributionChart()
        self.wpm_distribution_chart.setFixedHeight(220)
        self.content_layout.addWidget(self.wpm_distribution_chart)
        
        # Daily Metrics Chart (bar + line combo)
        self.daily_label = QLabel("Daily Metrics")
        self.daily_label.setStyleSheet(label_style)
        self.content_layout.addWidget(self.daily_label)
        
        self.daily_chart = DateRangeChart()
        self.daily_chart.setFixedHeight(300)
        self.daily_chart.options_changed.connect(self._on_daily_options_changed)
        self.content_layout.addWidget(self.daily_chart)
    
    def _on_filter_changed(self, selected_languages: Set[str]):
        """Handle language filter change."""
        self._selected_languages = selected_languages
        self._update_all_stats()
    
    def refresh(self):
        """Refresh all data in the stats tab."""
        # Load available languages
        languages = stats_db.list_history_languages()
        self.filter_bar.set_languages(languages)
        
        # Set default date range for daily chart
        first_date = stats_db.get_first_session_date()
        self.daily_chart.set_default_dates(first_date)
        
        # Update all stats and charts
        self._update_all_stats()
    
    def _update_all_stats(self):
        """Update all statistics and charts based on current filters."""
        languages_list = list(self._selected_languages) if self._selected_languages else None
        
        # Update summary cards
        self._update_summary_stats(languages_list)
        
        # Update scatter chart
        self._update_scatter_chart(languages_list)
        
        # Update WPM distribution chart
        self._update_wpm_distribution(languages_list)
        
        # Update daily metrics chart
        self._update_daily_chart(languages_list)
    
    def _update_summary_stats(self, languages_list=None):
        """Update the summary statistics based on current filters."""
        # Get aggregated stats from database
        stats = stats_db.get_aggregated_stats(languages=languages_list)
        
        # Update cards
        self.summary_cards["total_completed"].set_value(str(stats.get("total_completed", 0)))
        self.summary_cards["total_incomplete"].set_value(str(stats.get("total_incomplete", 0)))
        
        highest_wpm = stats.get("highest_wpm")
        self.summary_cards["highest_wpm"].set_value(f"{highest_wpm:.1f}" if highest_wpm else "-")
        
        lowest_wpm = stats.get("lowest_wpm")
        self.summary_cards["lowest_wpm"].set_value(f"{lowest_wpm:.1f}" if lowest_wpm else "-")
        
        avg_wpm = stats.get("avg_wpm")
        self.summary_cards["avg_wpm"].set_value(f"{avg_wpm:.1f}" if avg_wpm else "-")
        
        highest_acc = stats.get("highest_acc")
        self.summary_cards["highest_acc"].set_value(f"{highest_acc:.1f}%" if highest_acc else "-")
        
        lowest_acc = stats.get("lowest_acc")
        self.summary_cards["lowest_acc"].set_value(f"{lowest_acc:.1f}%" if lowest_acc else "-")
        
        avg_acc = stats.get("avg_acc")
        self.summary_cards["avg_acc"].set_value(f"{avg_acc:.1f}%" if avg_acc else "-")
        
        most_chars = stats.get("most_chars_day")
        self.summary_cards["most_chars_day"].set_value(f"{most_chars:,}" if most_chars else "-")
        
        most_sessions = stats.get("most_sessions_day")
        self.summary_cards["most_sessions_day"].set_value(str(most_sessions) if most_sessions else "-")
    
    def _update_scatter_chart(self, languages_list=None):
        """Update the WPM & Accuracy scatter chart."""
        session_data = stats_db.get_sessions_over_time(languages=languages_list)
        self.scatter_chart.set_data(session_data)
    
    def _update_wpm_distribution(self, languages_list=None):
        """Update the WPM distribution bar chart."""
        distribution_data = stats_db.get_wpm_distribution(languages=languages_list)
        self.wpm_distribution_chart.set_data(distribution_data)
    
    def _update_daily_chart(self, languages_list=None):
        """Update the daily metrics chart."""
        start_date, end_date = self.daily_chart.get_date_range()
        daily_data = stats_db.get_daily_metrics(
            languages=languages_list,
            start_date=start_date,
            end_date=end_date
        )
        self.daily_chart.set_data(daily_data)
    
    def _on_daily_options_changed(self):
        """Handle daily chart date range changes."""
        languages_list = list(self._selected_languages) if self._selected_languages else None
        self._update_daily_chart(languages_list)
    
    def apply_theme(self):
        """Apply current theme to all widgets in the Stats tab."""
        colors = get_theme_colors()
        
        # Update main container background
        bg_primary = colors["bg_primary"].name()
        bg_secondary = colors["bg_secondary"].name()
        text_primary = colors["text_primary"].name()
        text_secondary = colors["text_secondary"].name()
        border_color = colors["border"].name()
        
        # Update scroll area and content
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {bg_primary};
            }}
            QScrollBar:vertical {{
                background: {bg_primary};
                width: 12px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {bg_secondary};
                min-height: 30px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {border_color};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        self.content.setStyleSheet(f"background-color: {bg_primary};")
        
        # Update header
        self.header.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {text_primary}; margin-bottom: 8px;")
        
        # Update summary label
        self.summary_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {text_secondary}; margin-top: 16px;")
        
        # Update chart section labels
        label_style = f"font-size: 16px; font-weight: bold; color: {text_secondary}; margin-top: 16px;"
        if hasattr(self, 'scatter_label'):
            self.scatter_label.setStyleSheet(label_style)
        if hasattr(self, 'bar_label'):
            self.bar_label.setStyleSheet(label_style)
        if hasattr(self, 'daily_label'):
            self.daily_label.setStyleSheet(label_style)
        
        # Update filter bar
        self.filter_bar.apply_theme()
        
        # Update summary cards
        for card in self.summary_cards.values():
            card.apply_theme()
        
        # Update charts
        self.scatter_chart.apply_theme()
        self.wpm_distribution_chart.apply_theme()
        self.daily_chart.apply_theme()
