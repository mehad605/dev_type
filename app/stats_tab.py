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
    QPushButton,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QComboBox,
    QDateEdit,
)

from app import stats_db
from app import settings


def format_date_display(date_str: str, short: bool = False) -> str:
    """Format a date string from YYYY-MM-DD to human-readable format.
    
    Args:
        date_str: Date in YYYY-MM-DD format.
        short: If True, return short format (e.g., '30 Dec'), otherwise full (e.g., '30 Dec 2025').
    
    Returns:
        Formatted date string.
    """
    try:
        date_obj = datetime.strptime(date_str[:10], "%Y-%m-%d")
        if short:
            return date_obj.strftime("%d %b")  # e.g., "30 Dec"
        return date_obj.strftime("%d %b %Y")  # e.g., "30 Dec 2025"
    except (ValueError, IndexError):
        return date_str


def get_theme_colors() -> Dict[str, QColor]:
    """Get current theme colors for charts."""
    from app.themes import get_color_scheme
    scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
    scheme = get_color_scheme("dark", scheme_name)
    
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
    
    toggled = Signal(str, bool, bool)  # language, is_selected, ctrl_held
    
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
                    border-radius: 16px;
                    border: 2px solid {accent};
                    padding: 0 4px;
                }}
                QLabel {{
                    color: #ffffff;
                    font-weight: 600;
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
                    border-radius: 16px;
                    border: 2px solid transparent;
                    padding: 0 4px;
                }}
                QFrame#languageChip:hover {{
                    background-color: {bg_hover};
                    border: 2px solid {colors["accent"].name()};
                }}
                QLabel {{
                    color: {text};
                    font-size: 12px;
                    font-weight: 500;
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
            ctrl_held = event.modifiers() & Qt.ControlModifier
            self.toggled.emit(self.language, not self._selected, bool(ctrl_held))
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
    
    def _on_all_toggled(self, language: str, is_selected: bool, ctrl_held: bool = False):
        """Handle \"All\" chip toggle."""
        if is_selected or not self._selected_languages:
            # Select "All" and deselect others
            self._all_chip.selected = True
            self._selected_languages.clear()
            for chip in self._chips.values():
                chip.selected = False
            self.filter_changed.emit(set())  # Empty set = all languages
    
    def _on_language_toggled(self, language: str, is_selected: bool, ctrl_held: bool = False):
        """Handle individual language chip toggle.
        
        Without Ctrl: exclusive selection (deselect all others)
        With Ctrl: additive selection (toggle this language)
        """
        if ctrl_held:
            # Ctrl+click: additive toggle
            if is_selected:
                self._selected_languages.add(language)
                self._chips[language].selected = True
            else:
                self._selected_languages.discard(language)
                self._chips[language].selected = False
        else:
            # Regular click: exclusive selection
            # Deselect all others, select only this one
            self._selected_languages.clear()
            for lang, chip in self._chips.items():
                chip.selected = (lang == language)
            self._selected_languages.add(language)
        
        # Update "All" chip state
        self._all_chip.selected = len(self._selected_languages) == 0
        
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


class CalendarHeatmap(QWidget):
    """GitHub-style calendar heatmap showing daily activity for a specific year."""
    
    # Available metrics
    METRIC_OPTIONS = [
        ("total_chars", "Characters Typed"),
        ("completed_sessions", "Sessions Completed"),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        
        # Data
        self._data: Dict[str, float] = {}
        self._daily_data: List[Dict[str, Any]] = []
        self._metric = "total_chars"
        self._year = datetime.now().year
        
        # Visual settings
        self._cell_size = 12
        self._cell_gap = 3
        self._month_label_height = 20
        self._weekday_label_width = 32
        
        # Theme colors
        self._update_colors()
        
        # Hover state
        self._hovered_date: Optional[str] = None
        self._hovered_rect: Optional[QRectF] = None
        
        # Calculate size based on 54 weeks (buffer for Jan alignment)
        total_width = self._weekday_label_width + 54 * (self._cell_size + self._cell_gap)
        total_height = self._month_label_height + 7 * (self._cell_size + self._cell_gap) + 30
        self.setFixedHeight(int(total_height))
        self.setMinimumWidth(int(total_width))

    def set_year(self, year: int):
        """Set the year to display."""
        if self._year != year:
            self._year = year
            self.update()

    def set_metric(self, metric: str):
        """Set the metric to display."""
        if metric != self._metric:
            self._metric = metric
            self._process_data()
            self.update()

    def _process_data(self):
        """Process raw daily data into the display format."""
        self._data = {}
        for entry in self._daily_data:
            date = entry.get("date")
            value = entry.get(self._metric, 0)
            if date:
                self._data[date] = float(value)

    def _update_colors(self):
        """Sync with current theme colors."""
        self._colors = get_theme_colors()
        self._empty_color = self._colors["bg_tertiary"]
        self._text_color = self._colors["text_secondary"]
        accent = self._colors["accent"]
        self._heat_levels = [
            self._empty_color,
            QColor(accent.red(), accent.green(), accent.blue(), 60),
            QColor(accent.red(), accent.green(), accent.blue(), 120),
            QColor(accent.red(), accent.green(), accent.blue(), 180),
            accent,
        ]

    def set_data(self, daily_data: List[Dict[str, Any]]):
        """Update heatmap data."""
        self._daily_data = daily_data
        self._process_data()
        self.update()

    def _get_heat_level(self, value: float) -> int:
        if not self._data or value <= 0:
            return 0
        max_val = max(self._data.values()) if self._data else 1
        if max_val <= 0: return 0
        ratio = value / max_val
        if ratio <= 0: return 0
        elif ratio <= 0.25: return 1
        elif ratio <= 0.5: return 2
        elif ratio <= 0.75: return 3
        else: return 4

    def _get_cell_rect(self, week: int, day: int) -> QRectF:
        x = self._weekday_label_width + week * (self._cell_size + self._cell_gap)
        y = self._month_label_height + day * (self._cell_size + self._cell_gap)
        return QRectF(x, y, self._cell_size, self._cell_size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._update_colors()

        # Start from the Sunday of the week containing Jan 1st
        start_date = QDate(self._year, 1, 1)
        offset = start_date.dayOfWeek() % 7 # 0=Sun, 1=Mon...
        start_date = start_date.addDays(-offset)
        end_date = QDate(self._year, 12, 31)

        # Draw weekday labels
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(self._text_color)
        weekday_labels = ["", "Mon", "", "Wed", "", "Fri", ""]
        for i, label in enumerate(weekday_labels):
            if label:
                y = self._month_label_height + i * (self._cell_size + self._cell_gap)
                painter.drawText(QRectF(0, y, self._weekday_label_width - 6, self._cell_size),
                               Qt.AlignRight | Qt.AlignVCenter, label)

        current_month = -1
        month_positions = []
        current_date = start_date
        week = 0
        self._hovered_rect = None
        
        # Draw cells
        while current_date <= end_date or current_date.dayOfWeek() % 7 != 0:
            day_of_week = current_date.dayOfWeek() % 7
            
            # Month track
            if current_date.year() == self._year and current_date.month() != current_month:
                current_month = current_date.month()
                x_pos = self._weekday_label_width + week * (self._cell_size + self._cell_gap)
                month_name = current_date.toString("MMM")
                month_positions.append((x_pos, month_name))

            if current_date.year() == self._year:
                rect = self._get_cell_rect(week, day_of_week)
                date_str = current_date.toString("yyyy-MM-dd")
                value = self._data.get(date_str, 0)
                level = self._get_heat_level(value)
                color = self._heat_levels[level]
                
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(rect, 2, 2)

                if date_str == self._hovered_date:
                    painter.setPen(QPen(self._colors["text_primary"], 1.5))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRoundedRect(rect.adjusted(-0.5, -0.5, 0.5, 0.5), 2, 2)
                    self._hovered_rect = rect

            current_date = current_date.addDays(1)
            if current_date.dayOfWeek() % 7 == 0:
                week += 1
            if current_date.year() > self._year and current_date.dayOfWeek() % 7 == 0:
                break

        # Render month names
        painter.setPen(self._text_color)
        for x_pos, month_name in month_positions:
            painter.drawText(QRectF(x_pos, 0, 40, self._month_label_height), Qt.AlignLeft | Qt.AlignVCenter, month_name)

        # Legend
        legend_y = self.height() - 15
        legend_x = self._weekday_label_width
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(QRectF(legend_x, legend_y, 30, self._cell_size), Qt.AlignLeft | Qt.AlignVCenter, "Less")
        legend_x += 35
        for i, color in enumerate(self._heat_levels):
            rect = QRectF(legend_x + i * (self._cell_size + 2), legend_y, self._cell_size, self._cell_size)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, 2, 2)
        legend_x += len(self._heat_levels) * (self._cell_size + 2) + 5
        painter.drawText(QRectF(legend_x, legend_y, 30, self._cell_size), Qt.AlignLeft | Qt.AlignVCenter, "More")

        # Tooltip
        if self._hovered_date and self._hovered_rect:
            value = self._data.get(self._hovered_date, 0)
            if self._metric == "total_chars": value_str = f"{int(value):,} chars"
            elif self._metric == "completed_sessions": value_str = f"{int(value)} sessions"
            else: value_str = f"{value:.1f}"
            
            try:
                date_obj = datetime.strptime(self._hovered_date, "%Y-%m-%d")
                date_display = date_obj.strftime("%d %b %Y")
            except: date_display = self._hovered_date
            
            tooltip_text = f"{date_display}: {value_str}"
            fm = QFontMetrics(font)
            text_width = fm.horizontalAdvance(tooltip_text) + 16
            tooltip_rect = QRectF(self._hovered_rect.center().x() - text_width/2, self._hovered_rect.y() - 28, text_width, 22)
            if tooltip_rect.left() < 0: tooltip_rect.moveLeft(0)
            if tooltip_rect.right() > self.width(): tooltip_rect.moveRight(self.width())
            if tooltip_rect.top() < 0: # Flip below if cutoff
                tooltip_rect.moveTop(self._hovered_rect.bottom() + 6)
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(self._colors["bg_secondary"])
            painter.drawRoundedRect(tooltip_rect, 4, 4)
            painter.setPen(QPen(self._colors["border"], 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(tooltip_rect, 4, 4)
            painter.setPen(self._colors["text_primary"])
            painter.drawText(tooltip_rect, Qt.AlignCenter, tooltip_text)

    def mouseMoveEvent(self, event):
        start_date = QDate(self._year, 1, 1)
        offset = start_date.dayOfWeek() % 7
        start_date = start_date.addDays(-offset)
        
        x, y = event.position().x(), event.position().y()
        if x < self._weekday_label_width or y < self._month_label_height:
            if self._hovered_date: self._hovered_date = None; self.update()
            return

        week = int((x - self._weekday_label_width) / (self._cell_size + self._cell_gap))
        day = int((y - self._month_label_height) / (self._cell_size + self._cell_gap))
        
        if 0 <= day <= 6 and week >= 0:
            hovered_date = start_date.addDays(week * 7 + day)
            if hovered_date.year() == self._year:
                date_str = hovered_date.toString("yyyy-MM-dd")
                if date_str != self._hovered_date:
                    self._hovered_date = date_str
                    self.update()
                return
        
        if self._hovered_date: self._hovered_date = None; self.update()

    def leaveEvent(self, event):
        self._hovered_date = None
        self.update()

    def apply_theme(self):
        self._update_colors()
        self.update()


class MetricScatterPlot(QWidget):
    """Scatter plot showing a single metric (WPM or Accuracy) over time."""
    
    def __init__(self, metric_type='wpm', parent=None):
        super().__init__(parent)
        self.metric_type = metric_type  # 'wpm' or 'accuracy'
        self.data: List[Dict] = []  # List of session data
        self.hover_info: Optional[Tuple[int, str]] = None  # (index, 'point' or 'trend')
        self._ctrl_held = False  # Track Ctrl key state for trend line mode
        
        # Colors - will be set from theme
        self._update_colors()
        
        # Adjust margins for single-metric view
        self.margin_left = 55
        self.margin_right = 35
        self.margin_top = 15
        self.margin_bottom = 25
        
        self.setMinimumHeight(180)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)  # Enable keyboard events
        self.setStyleSheet("background: transparent;")
    
    def _update_colors(self):
        """Update colors from current theme."""
        colors = get_theme_colors()
        self.wpm_color = colors["success"]
        self.acc_color = colors["info"]
        self.bg_color = colors["bg_secondary"]
        self.text_color = colors["text_primary"]
        self.grid_color = colors["border"]
        self.active_color = self.wpm_color if self.metric_type == 'wpm' else self.acc_color
    
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
    
    def _val_to_y(self, val: float, min_val: float, max_val: float) -> float:
        """Convert metric value to Y coordinate."""
        rect = self._chart_rect()
        span = max_val - min_val
        if span <= 0:
            span = 10 if self.metric_type == 'wpm' else 20
        clamped_val = max(min_val, min(max_val, val))
        ratio = (clamped_val - min_val) / span
        return rect.y() + rect.height() - (ratio * rect.height())

    def _get_processed_values(self) -> List[float]:
        """Get the metric values to plot, with necessary normalization."""
        if not self.data: return []
        if self.metric_type == 'wpm':
            return [d["wpm"] for d in self.data]
        else:
            vals = []
            for d in self.data:
                correct = d.get("correct", 0)
                incorrect = d.get("incorrect", 0)
                total = d.get("total", correct + incorrect)
                if total > 0:
                    acc = (correct / total) * 100
                else:
                    acc = d.get("accuracy", 0)
                    if acc <= 1.0: acc *= 100
                vals.append(acc)
            return vals

    def _get_range(self, values: List[float]) -> Tuple[float, float]:
        """Calculate the scale range for the metric."""
        if not values: return 0.0, 100.0
        min_v, max_v = min(values), max(values)
        if self.metric_type == 'wpm':
            min_r = (int(min_v) // 10) * 10
            max_r = ((int(max_v) // 10) + 1) * 10
            if max_r - min_r < 20: max_r = min_r + 20
        else:
            min_r = max(0, (int(min_v) // 10) * 10 - 10)
            max_r = min(100, ((int(max_v) // 10) + 1) * 10 + 10)
            if max_r - min_r < 20:
                if max_r > 80: min_r = max_r - 20
                else: max_r = min_r + 20
        return float(min_r), float(max_r)
    
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
    
    
    def mouseMoveEvent(self, event):
        if not self.data: return
        self._ctrl_held = bool(event.modifiers() & Qt.ControlModifier)
        rect = self._chart_rect()
        x, y = event.position().x(), event.position().y()
        
        values = self._get_processed_values()
        min_r, max_r = self._get_range(values)
        slope, intercept = self._calculate_trend_line(values)
        
        closest_info = None
        if self._ctrl_held and len(self.data) >= 2 and rect.contains(x, y):
            x_ratio = (x - rect.x()) / rect.width()
            x_idx = x_ratio * (len(self.data) - 1)
            trend_val = slope * x_idx + intercept
            py_trend = self._val_to_y(trend_val, min_r, max_r)
            if abs(y - py_trend) < 20:
                closest_info = (int(x_idx), 'trend')
        else:
            closest_dist = float('inf')
            for i, val in enumerate(values):
                px = self._date_to_x(i)
                py = self._val_to_y(val, min_r, max_r)
                dist = ((x - px)**2 + (y - py)**2)**0.5
                if dist < 15 and dist < closest_dist:
                    closest_dist = dist
                    closest_info = (i, 'point')
            if closest_info is None and len(self.data) >= 2 and rect.contains(x, y):
                x_ratio = (x - rect.x()) / rect.width()
                x_idx = x_ratio * (len(self.data) - 1)
                trend_val = slope * x_idx + intercept
                py_trend = self._val_to_y(trend_val, min_r, max_r)
                if abs(y - py_trend) < 8:
                    closest_info = (int(x_idx), 'trend')
        
        self.hover_info = closest_info
        self.update()
    
    def leaveEvent(self, event):
        """Clear hover when mouse leaves."""
        self.hover_info = None
        self._ctrl_held = False
        self.update()
    
    def keyPressEvent(self, event):
        """Track Ctrl key press for trend line focus mode."""
        if event.key() == Qt.Key_Control:
            self._ctrl_held = True
            self.update()
        super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        """Track Ctrl key release."""
        if event.key() == Qt.Key_Control:
            self._ctrl_held = False
            self.update()
        super().keyReleaseEvent(event)
    
    def enterEvent(self, event):
        """Set focus when mouse enters to receive key events."""
        self.setFocus()
        super().enterEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.bg_color)
        rect = self._chart_rect()
        
        if not self.data:
            painter.setPen(QColor("#666666"))
            font = QFont(); font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, "No session data available")
            return
        
        values = self._get_processed_values()
        min_r, max_r = self._get_range(values)
        font = QFont(); font.setPointSize(9)
        painter.setFont(font)
        
        # Grid lines
        painter.setPen(QPen(self.grid_color, 1))
        for i in range(6):
            grid_val = min_r + (i / 5.0) * (max_r - min_r)
            y = self._val_to_y(grid_val, min_r, max_r)
            painter.drawLine(QPointF(rect.x(), y), QPointF(rect.x() + rect.width(), y))
        
        painter.setPen(QPen(self.grid_color, 2))
        painter.drawRect(rect)
        
        # Y labels
        painter.setPen(self.active_color)
        for i in range(6):
            grid_val = min_r + (i / 5.0) * (max_r - min_r)
            y = self._val_to_y(grid_val, min_r, max_r)
            label = f"{int(grid_val)}" if self.metric_type == 'wpm' else f"{int(grid_val)}%"
            painter.drawText(QRectF(0, y - 10, self.margin_left - 5, 20),
                           Qt.AlignRight | Qt.AlignVCenter, label)
        
        hover_idx, hover_type = self.hover_info if self.hover_info else (None, None)
        point_opacity = 0.25 if self._ctrl_held else 1.0
        
        # Points
        for i, val in enumerate(values):
            px = self._date_to_x(i)
            py = self._val_to_y(val, min_r, max_r)
            is_hovered = (hover_idx == i and hover_type == 'point') and not self._ctrl_held
            size = 5 if is_hovered else 3
            p_color = QColor(self.active_color)
            p_color.setAlphaF(point_opacity)
            painter.setPen(QPen(p_color, 1.5 if is_hovered else 1))
            painter.setBrush(QBrush(p_color) if is_hovered else QBrush(self.bg_color))
            painter.drawEllipse(QPointF(px, py), size, size)
            
        # Trend Line
        if len(self.data) >= 2:
            slope, intercept = self._calculate_trend_line(values)
            x_start = self._date_to_x(0)
            x_end = self._date_to_x(len(self.data) - 1)
            base_width = 4 if self._ctrl_held else 2
            line_style = Qt.SolidLine if self._ctrl_held else Qt.DashLine
            y_start = self._val_to_y(intercept, min_r, max_r)
            y_end = self._val_to_y(slope * (len(self.data) - 1) + intercept, min_r, max_r)
            trend_pen = QPen(self.active_color, base_width, line_style)
            if hover_type == 'trend' or self._ctrl_held:
                trend_pen.setWidth(base_width + 2)
            painter.setPen(trend_pen)
            painter.drawLine(QPointF(x_start, y_start), QPointF(x_end, y_end))
            
        # Title (Vertical on the left)
        painter.setPen(self.active_color)
        painter.save()
        painter.translate(14, rect.y() + rect.height() / 2)
        painter.rotate(-90)
        title = "WPM" if self.metric_type == 'wpm' else "Accuracy"
        painter.drawText(QRectF(-40, -10, 80, 20), Qt.AlignCenter, title)
        painter.restore()
        
        # Tooltip
        if self.hover_info:
            idx, p_type = self.hover_info
            if p_type == 'trend':
                slope, intercept = self._calculate_trend_line(values)
                unit = "WPM" if self.metric_type == 'wpm' else "%"
                if abs(slope) < 0.01: trend_desc = f"Your {self.metric_type} is steady"
                elif slope > 0: trend_desc = f"Your {self.metric_type} is increasing (+{slope:.2f}{unit}/session)"
                else: trend_desc = f"Your {self.metric_type} is decreasing ({slope:.2f}{unit}/session)"
                tooltip_text = f"{self.metric_type.upper()} Trend Line\n{trend_desc}"
                px, py = rect.x() + rect.width() / 2, rect.y() + rect.height() / 2
            else:
                d = self.data[idx]; px = self._date_to_x(idx)
                py = self._val_to_y(values[idx], min_r, max_r)
                file_name = Path(d["file_path"]).name if d.get("file_path") else "Unknown"
                if self.metric_type == 'wpm':
                    tooltip_text = f"{format_date_display(d['date'])} | {values[idx]:.1f} WPM | {file_name}"
                else:
                    c, inc = d.get("correct", 0), d.get("incorrect", 0)
                    t = d.get("total", c + inc)
                    cp = (c/t*100) if t>0 else 0; ip = (inc/t*100) if t>0 else 0
                    tooltip_text = f"{format_date_display(d['date'])} | {file_name}\n{c} ({cp:.1f}%) ✓ | {inc} ({ip:.1f}%) ✗ | {t} total"
            
            painter.setFont(font); fm = QFontMetrics(font)
            lines = tooltip_text.split('\n')
            tw = max(fm.horizontalAdvance(l) for l in lines)
            th = fm.height() * len(lines)
            tx, ty = px + 10, py - th - 15
            if tx + tw + 16 > self.width(): tx = px - tw - 25
            if ty < 5: ty = py + 10
            t_rect = QRectF(tx, ty, tw + 16, th + 12)
            painter.setPen(Qt.NoPen); painter.setBrush(QColor("#2d2d2d"))
            painter.drawRoundedRect(t_rect, 4, 4)
            painter.setPen(QPen(self.active_color, 1))
            painter.drawRoundedRect(t_rect, 4, 4)
            painter.setPen(QColor("white"))
            for i, line in enumerate(lines):
                painter.drawText(t_rect.adjusted(8, 6 + i*fm.height(), -8, 0), Qt.AlignLeft | Qt.AlignTop, line)


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
                padding: 4px 12px;
                font-size: 11px;
            }}
            QComboBox:hover {{ border-color: {hover}; }}
            QComboBox::drop-down {{ 
                border: none; 
                width: 0px; 
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg};
                color: {text};
                selection-background-color: {colors["bg_primary"].name()};
                border: 1px solid {border};
                outline: 0px;
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
                padding: 4px 12px;
                font-size: 11px;
            }}
            QDateEdit:hover {{ border-color: {hover}; }}
            QDateEdit::drop-down {{ 
                border: none; 
                width: 0px; 
            }}
            QDateEdit::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
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
        self.start_date.setDisplayFormat("dd/MM/yyyy")
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
        self.end_date.setDisplayFormat("dd/MM/yyyy")
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
            val_right = d[self._right_metric]
            if self._is_right_metric_accuracy() and val_right <= 1.0 and d.get("total_keystrokes", 0) > 0:
                val_right = (d["correct_keystrokes"] / d["total_keystrokes"]) * 100
            elif self._is_right_metric_accuracy() and val_right <= 1.0:
                val_right *= 100
                
            py_line = self._right_to_y(val_right, max_right)
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
            date_str = format_date_display(self.data[i]["date"], short=True)
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
                    val1 = self.data[i][self._right_metric]
                    if self._is_right_metric_accuracy() and val1 <= 1.0: val1 *= 100
                    y1 = self._right_to_y(val1, max_right)
                    
                    x2 = self._x_to_pos(i + 1)
                    val2 = self.data[i + 1][self._right_metric]
                    if self._is_right_metric_accuracy() and val2 <= 1.0: val2 *= 100
                    y2 = self._right_to_y(val2, max_right)
                    
                    painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            
            # Draw points
            for i, d in enumerate(self.data):
                px = self._x_to_pos(i)
                val_right = d[self._right_metric]
                if self._is_right_metric_accuracy() and val_right <= 1.0 and d.get("total_keystrokes", 0) > 0:
                    val_right = (d["correct_keystrokes"] / d["total_keystrokes"]) * 100
                elif self._is_right_metric_accuracy() and val_right <= 1.0:
                    val_right *= 100
                    
                py = self._right_to_y(val_right, max_right)
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
                    tooltip_text = f"{format_date_display(d['date'])}\n{left_label}: {self._format_number(val)}"
                    border_color = self.bar_color
                else:
                    py = self._right_to_y(d[self._right_metric], max_right)
                    right_label = dict(self.RIGHT_OPTIONS).get(self._right_metric, "")
                    val = d[self._right_metric]
                    if self._is_right_metric_accuracy():
                        tooltip_text = f"{format_date_display(d['date'])}\n{right_label}: {val:.1f}%"
                    else:
                        tooltip_text = f"{format_date_display(d['date'])}\n{right_label}: {val:.1f}"
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


class KeyboardHeatmap(QWidget):
    """Heatmap visualization showing typing accuracy per key."""
    
    # QWERTY Layout rows - Lower layer
    ROWS_LOWER = [
        ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="],
        ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"],
        ["a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'"],
        ["z", "x", "c", "v", "b", "n", "m", ",", ".", "/"],
        ["SPACE"]
    ]
    
    # QWERTY Layout rows - Upper layer (Shift)
    ROWS_UPPER = [
        ["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+"],
        ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "{", "}", "|"],
        ["A", "S", "D", "F", "G", "H", "J", "K", "L", ":", "\""],
        ["Z", "X", "C", "V", "B", "N", "M", "<", ">", "?"],
        ["SPACE"]
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.raw_stats: Dict[str, Dict[str, int]] = {}
        self.raw_confusions: Dict[str, Dict[str, int]] = {}
        self.display_stats: Dict[str, Dict[str, int]] = {}
        self.display_confusions: Dict[str, Dict[str, int]] = {}
        self.shift_mode = False
        self.hovered_key: Optional[str] = None
        
        # Performance caches
        self._render_cache = {}
        self._tooltip_cache = None
        
        self.setMinimumHeight(240)
        self.setMouseTracking(True)
        self._update_colors()
        
    def _update_colors(self):
        colors = get_theme_colors()
        self.bg_color = colors["bg_secondary"]
        self.text_primary = colors["text_primary"]
        self.text_secondary = colors["text_secondary"]
        self.border_color = colors["border"]
        self.success_color = colors["success"]
        self.error_color = colors["error"]
        self.neutral_color = colors["bg_tertiary"]
        self.tooltip_bg = QColor("#2d2d2d")
        
    def set_data(self, stats: Dict[str, Dict[str, int]], confusions: Dict[str, Dict[str, int]]):
        """Set raw key stats and confusion data, then refresh."""
        self.raw_stats = stats
        self.raw_confusions = confusions
        self._refresh_display_stats()
        
    def _refresh_display_stats(self):
        """Map raw stats to the current layer's keys and pre-calculate render data."""
        self.display_stats = {}
        self.display_confusions = {}
        self._render_cache = {}
        self._tooltip_cache = None
        
        current_rows = self.ROWS_UPPER if self.shift_mode else self.ROWS_LOWER
        
        for row in current_rows:
            for key in row:
                char = ' ' if key == "SPACE" else key
                s = self.raw_stats.get(char, {"correct": 0, "error": 0})
                self.display_stats[key] = s.copy()
                
                c = self.raw_confusions.get(char, {})
                self.display_confusions[key] = c.copy()
                
                # Pre-calculate render data (colors, labels)
                total = s["correct"] + s["error"]
                if total == 0:
                    fill = self.neutral_color
                    text = self.text_secondary
                else:
                    acc = s["correct"] / total
                    if acc > 0.95: fill = self.success_color
                    elif acc < 0.7: fill = self.error_color
                    else:
                        t = (acc - 0.7) / 0.25
                        fill = QColor(
                            int(self.error_color.red() + t * (self.success_color.red() - self.error_color.red())),
                            int(self.error_color.green() + t * (self.success_color.green() - self.error_color.green())),
                            int(self.error_color.blue() + t * (self.success_color.blue() - self.error_color.blue()))
                        )
                    # Contrast calculation
                    lum = (0.299 * fill.red() + 0.587 * fill.green() + 0.114 * fill.blue()) / 255
                    text = QColor(255, 255, 255) if lum < 0.5 else QColor(0, 0, 0)
                
                self._render_cache[key] = {
                    "fill": fill,
                    "text": text,
                    "label": key if key != "SPACE" else "____"
                }
        self.update()

    def toggle_shift(self, enabled: bool):
        """Toggle between lower and upper keyboard layers."""
        self.shift_mode = enabled
        self._refresh_display_stats()

    def apply_theme(self):
        self._update_colors()
        self.update()

    def mouseMoveEvent(self, event):
        pos = event.position()
        new_hover = self._get_key_at(pos.x(), pos.y())
        if new_hover != self.hovered_key:
            self.hovered_key = new_hover
            self._tooltip_cache = None # invalidate tooltip cache
            self.setCursor(Qt.PointingHandCursor if new_hover else Qt.ArrowCursor)
            self.update()

    def leaveEvent(self, event):
        self.hovered_key = None
        self.update()

    def _get_key_at(self, mx: float, my: float) -> Optional[str]:
        """Hit test to find which key is under the mouse."""
        rect, key_size, key_margin, start_x, start_y = self._get_layout_params()
        current_rows = self.ROWS_UPPER if self.shift_mode else self.ROWS_LOWER
        
        for r, row in enumerate(current_rows):
            offset = self._get_row_offset(r, key_size)
            for c, key_label in enumerate(row):
                w = key_size - key_margin
                if key_label == "SPACE": w = key_size * 5 - key_margin
                
                x = start_x + offset + c * key_size
                y = start_y + r * key_size
                if QRectF(x, y, w, key_size - key_margin).contains(mx, my):
                    return key_label
        return None

    def _get_row_offset(self, r: int, key_size: float) -> float:
        if r == 1: return key_size * 0.5
        if r == 2: return key_size * 0.75
        if r == 3: return key_size * 1.25
        if r == 4: return key_size * 4
        return 0

    def _get_layout_params(self):
        rect = self.rect()
        key_margin = 3
        current_rows = self.ROWS_UPPER if self.shift_mode else self.ROWS_LOWER
        max_row_len = max(len(row) for row in current_rows)
        # Make it more compact - slightly smaller keys and tight margins
        key_size = min((rect.width() - 20) / max_row_len, (rect.height() - 10) / len(current_rows))
        key_size = max(25, min(42, key_size))
        total_width = max_row_len * key_size
        start_x = (rect.width() - total_width) / 2
        start_y = (rect.height() - len(current_rows) * key_size) / 2
        return rect, key_size, key_margin, start_x, start_y

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect, key_size, key_margin, start_x, start_y = self._get_layout_params()
        current_rows = self.ROWS_UPPER if self.shift_mode else self.ROWS_LOWER
        
        hover_rect = None
        hover_stats = None
        
        for r, row in enumerate(current_rows):
            offset = self._get_row_offset(r, key_size)
            for c, key_label in enumerate(row):
                w = key_size - key_margin
                h = key_size - key_margin
                if key_label == "SPACE": w = key_size * 5 - key_margin
                
                x = start_x + offset + c * key_size
                y = start_y + r * key_size
                key_rect = QRectF(x, y, w, h)
                
                # Use pre-calculated cache
                cache = self._render_cache.get(key_label)
                if not cache: continue
                
                fill_color = cache["fill"]
                is_hovered = (key_label == self.hovered_key)
                
                if is_hovered:
                    fill_color = fill_color.lighter(120)
                    hover_rect = key_rect
                    hover_stats = self.display_stats.get(key_label)
                
                painter.setPen(Qt.NoPen)
                painter.setBrush(fill_color)
                painter.drawRoundedRect(key_rect, 4, 4)
                
                painter.setPen(cache["text"])
                painter.drawText(key_rect, Qt.AlignCenter, cache["label"])
                
                # Border
                painter.setPen(QPen(self.border_color.lighter(110) if is_hovered else self.border_color, 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(key_rect, 4, 4)

        # Draw Tooltip
        if hover_rect and hover_stats:
            total = hover_stats["correct"] + hover_stats["error"]
            if total > 0:
                # Tooltip Cache Calculation
                if not self._tooltip_cache:
                    acc_pct = (hover_stats["correct"] / total) * 100
                    header_lines = [
                        f"Key: {self.hovered_key}",
                        f"Accuracy: {acc_pct:.1f}% ({hover_stats['correct']}/{total})",
                        f"Total Errors: {hover_stats['error']}"
                    ]
                    
                    confusions = self.display_confusions.get(self.hovered_key, {})
                    sorted_confusions = []
                    if confusions and hover_stats["error"] > 0:
                        sorted_confusions = sorted(confusions.items(), key=lambda x: x[1], reverse=True)[:3]

                    fm = painter.fontMetrics()
                    header_h = len(header_lines) * max(fm.height(), 16)
                    
                    block_w, block_h, block_gap = 38, 38, 6
                    visual_section_w = 0
                    visual_section_h = 0
                    
                    if sorted_confusions:
                        section_title = "Top 3 Mistakes (% of errors):"
                        visual_section_h = 88
                        visual_section_w = len(sorted_confusions) * (block_w + block_gap) - block_gap
                        visual_section_w = max(visual_section_w, fm.horizontalAdvance(section_title))
                    
                    max_w = max(visual_section_w, *(fm.horizontalAdvance(line) for line in header_lines))
                    total_h = header_h + (15 if sorted_confusions else 0) + visual_section_h
                    
                    self._tooltip_cache = {
                        "header_lines": header_lines,
                        "sorted_confusions": sorted_confusions,
                        "section_title": section_title if sorted_confusions else "",
                        "max_w": max_w,
                        "total_h": total_h,
                        "header_h": header_h,
                        "block_w": block_w, "block_h": block_h, "block_gap": block_gap
                    }

                # Use Tooltip Cache
                cache = self._tooltip_cache
                max_w, total_h = cache["max_w"], cache["total_h"]
                
                tx = hover_rect.center().x() - max_w / 2 - 12
                ty = hover_rect.top() - total_h - 20
                if ty < 5: ty = hover_rect.bottom() + 10
                
                tx = max(8, min(tx, rect.width() - max_w - 24))
                ty = max(5, min(ty, rect.height() - total_h - 20))
                
                original_font = painter.font()
                tip_rect = QRectF(tx, ty, max_w + 24, total_h + 12)
                painter.setPen(QPen(self.border_color.lighter(120), 1))
                painter.setBrush(self.tooltip_bg)
                painter.drawRoundedRect(tip_rect, 6, 6)
                
                painter.setPen(self.text_primary)
                curr_y = ty + painter.fontMetrics().height() + 6
                for line in cache["header_lines"]:
                    painter.drawText(int(tx + 12), int(curr_y), line)
                    curr_y += max(painter.fontMetrics().height(), 16)
                
                if cache["sorted_confusions"]:
                    curr_y += 2
                    painter.setPen(QPen(self.border_color, 1))
                    painter.drawLine(int(tx + 12), int(curr_y), int(tx + max_w + 12), int(curr_y))
                    
                    curr_y += 18
                    painter.setPen(self.text_secondary)
                    painter.drawText(int(tx + 12), int(curr_y), cache["section_title"])
                    
                    curr_y += 20
                    confusion_colors = [QColor("#ff1744"), QColor("#ff9100"), QColor("#ffea00")]
                    
                    for i, (char, count) in enumerate(cache["sorted_confusions"]):
                        bx = tx + 12 + i * (cache["block_w"] + cache["block_gap"])
                        err_total = hover_stats["error"]
                        pct = (count / err_total) * 100 if err_total > 0 else 0
                        
                        painter.setPen(confusion_colors[i % 3])
                        painter.setFont(QFont(original_font.family(), 8, QFont.Bold))
                        painter.drawText(QRectF(bx, curr_y - 18, cache["block_w"], 15), Qt.AlignCenter, f"{pct:.0f}%")
                        
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(confusion_colors[i % 3])
                        block_rect = QRectF(bx, curr_y, cache["block_w"], cache["block_h"])
                        painter.drawRoundedRect(block_rect, 4, 4)
                        
                        painter.setPen(QColor(0, 0, 0))
                        painter.setFont(QFont(original_font.family(), 10, QFont.Medium))
                        display_char = char if char != " " else "␣"
                        if display_char == "[NONE]": display_char = "?"
                        painter.drawText(block_rect, Qt.AlignCenter, display_char)
                
                painter.setFont(original_font)




class ErrorTypePieChart(QWidget):
    """Pie chart categorizing typing errors into Missed, Extra, and Swapped."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {'omission': 0, 'insertion': 0, 'transposition': 0, 'substitution': 0}
        self.setMinimumHeight(240)
        self._update_colors()

    def _update_colors(self):
        colors = get_theme_colors()
        self.bg_color = colors["bg_secondary"]
        self.text_primary = colors["text_primary"]
        self.text_secondary = colors["text_secondary"]
        self.slice_colors = [
            QColor("#ff1744"), # Missed - Red
            QColor("#ff9100"), # Extra - Orange
            QColor("#ffea00"), # Swapped - Yellow
        ]
        self.labels = ["Missed Keys", "Extra Keys", "Swapped Keys"]

    def apply_theme(self):
        self._update_colors()
        self.update()

    def set_data(self, data: Dict[str, int]):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        size = min(rect.width() * 0.4, rect.height() - 60)
        size = max(120, size)
        
        # Categorize
        missed = self.data.get('omission', 0)
        extra = self.data.get('insertion', 0) + self.data.get('substitution', 0)
        swapped = self.data.get('transposition', 0)
        
        counts = [missed, extra, swapped]
        total = sum(counts)
        
        legend_w = 220
        gap = 50
        total_content_w = size + gap + legend_w
        
        start_x = (rect.width() - total_content_w) / 2
        pie_rect = QRectF(start_x, (rect.height() - size) / 2, size, size)
        
        if total == 0:
            painter.setPen(QPen(self.text_secondary, 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(pie_rect)
            painter.setPen(self.text_secondary)
            painter.drawText(pie_rect, Qt.AlignCenter, "No errors\nrecorded")
        else:
            start_angle = 90 * 16
            for i, count in enumerate(counts):
                if count == 0: continue
                span_angle = int((count / total) * 360 * 16)
                painter.setPen(Qt.NoPen)
                painter.setBrush(self.slice_colors[i])
                painter.drawPie(pie_rect, start_angle, span_angle)
                start_angle += span_angle
            
            # Donut hole
            hole_size = size * 0.65
            hole_rect = QRectF(
                pie_rect.center().x() - hole_size/2,
                pie_rect.center().y() - hole_size/2,
                hole_size, hole_size
            )
            painter.setBrush(self.bg_color)
            painter.drawEllipse(hole_rect)
            
            # Center text
            painter.setPen(self.text_primary)
            painter.setFont(QFont("Inter", 20, QFont.Bold))
            painter.drawText(hole_rect.adjusted(0, -10, 0, 0), Qt.AlignCenter, str(total))
            painter.setFont(QFont("Inter", 9, QFont.Medium))
            painter.setPen(self.text_secondary)
            painter.drawText(hole_rect.adjusted(0, 25, 0, 0), Qt.AlignCenter, "ERRORS")

        # Legend
        lx = pie_rect.right() + gap
        ly = pie_rect.center().y() - (len(self.labels) * 30) / 2
        
        for i, label in enumerate(self.labels):
            # Color indicator
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.slice_colors[i])
            painter.drawRoundedRect(QRectF(lx, ly + 6, 14, 14), 3, 3)
            
            painter.setFont(QFont("Inter", 10, QFont.Medium))
            painter.setPen(self.text_primary)
            count = counts[i]
            pct = (count / total * 100) if total > 0 else 0
            text = f"{label}: {count} ({pct:.1f}%)"
            painter.drawText(int(lx + 25), int(ly + 18), text)
            ly += 30



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
        
        # Grid of summary cards (2 rows)
        self.summary_cards: Dict[str, SummaryStatCard] = {}
        
        # Row 1: Streak, WPM stats, Accuracy stats
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        
        cards_row1 = [
            ("streak", "Current Streak", "🔥"),
            ("total_completed", "Total Sessions", "✓"),
            ("avg_wpm", "Average WPM", "📊"),
            ("highest_wpm", "Best WPM", "🚀"),
            ("wpm_trend", "WPM Trend (30d)", "📈"),
        ]
        
        for key, title, icon in cards_row1:
            card = SummaryStatCard(title, "-", icon)
            self.summary_cards[key] = card
            row1.addWidget(card)
        
        row1.addStretch()
        self.content_layout.addLayout(row1)
        
        # Row 2: Accuracy stats and activity records
        row2 = QHBoxLayout()
        row2.setSpacing(12)
        
        cards_row2 = [
            ("avg_acc", "Average Accuracy", "🎯"),
            ("highest_acc", "Best Accuracy", "💯"),
            ("acc_trend", "Accuracy Trend (30d)", "📉"),
            ("most_chars_day", "Most Chars/Day", "⌨"),
            ("most_sessions_day", "Most Sessions/Day", "📅"),
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
        # Clean label style without pushing it down with margins (let layout handle it)
        label_style = f"font-size: 16px; font-weight: bold; color: {colors['text_secondary'].name()};"
        
        # Calendar Heatmap (GitHub-style activity visualization)
        # Header row with label and dropdowns
        heatmap_header = QHBoxLayout()
        heatmap_header.setSpacing(12)
        heatmap_header.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        # Add some top margin to the whole header layout instead of individual labels
        heatmap_header.setContentsMargins(0, 16, 0, 0)
        
        self.heatmap_label = QLabel("Activity Heatmap")
        self.heatmap_label.setStyleSheet(label_style)
        heatmap_header.addWidget(self.heatmap_label)
        
        # Metric selector dropdown
        self.heatmap_metric_combo = QComboBox()
        for key, label in CalendarHeatmap.METRIC_OPTIONS:
            self.heatmap_metric_combo.addItem(label)
        self.heatmap_metric_combo.setFixedWidth(160)
        self.heatmap_metric_combo.setStyleSheet(self._get_combo_style())
        self.heatmap_metric_combo.currentIndexChanged.connect(self._on_heatmap_metric_changed)
        heatmap_header.addWidget(self.heatmap_metric_combo)
        
        # Year selector dropdown
        self.heatmap_year_combo = QComboBox()
        self.heatmap_year_combo.setFixedWidth(100)
        self.heatmap_year_combo.setStyleSheet(self._get_combo_style())
        self.heatmap_year_combo.currentIndexChanged.connect(self._on_heatmap_year_changed)
        heatmap_header.addWidget(self.heatmap_year_combo)
        
        heatmap_header.addStretch()
        self.content_layout.addLayout(heatmap_header)
        
        self.calendar_heatmap = CalendarHeatmap()
        self.content_layout.addWidget(self.calendar_heatmap)
        
        # Keyboard Heatmap
        kb_header = QHBoxLayout()
        kb_header.setSpacing(12)
        kb_header.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        kb_header.setContentsMargins(0, 16, 0, 0)
        
        self.heatmap_kb_label = QLabel("Keyboard Accuracy Heatmap")
        self.heatmap_kb_label.setStyleSheet(label_style)
        kb_header.addWidget(self.heatmap_kb_label)
        
        # Shift toggle button
        self.kb_shift_btn = QPushButton("Shift: Off")
        self.kb_shift_btn.setCheckable(True)
        self.kb_shift_btn.setFixedWidth(100)
        self.kb_shift_btn.clicked.connect(self._on_kb_shift_toggled)
        kb_header.addWidget(self.kb_shift_btn)
        
        kb_header.addStretch()
        self.content_layout.addLayout(kb_header)
        
        self.keyboard_heatmap = KeyboardHeatmap()
        self.content_layout.addWidget(self.keyboard_heatmap)
        
        # Error Type Breakdown
        error_header = QHBoxLayout()
        error_header.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        error_header.setContentsMargins(0, 16, 0, 0)
        self.error_breakdown_label = QLabel("Error Type Breakdown")
        self.error_breakdown_label.setStyleSheet(label_style)
        error_header.addWidget(self.error_breakdown_label)
        self.content_layout.addLayout(error_header)
        
        self.error_pie_chart = ErrorTypePieChart()
        self.content_layout.addWidget(self.error_pie_chart)
        
        # WPM Over Time
        wpm_scatter_header = QHBoxLayout()
        wpm_scatter_header.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        wpm_scatter_header.setContentsMargins(0, 16, 0, 0)
        self.wpm_scatter_label = QLabel("WPM Over Time")
        self.wpm_scatter_label.setStyleSheet(label_style)
        wpm_scatter_header.addWidget(self.wpm_scatter_label)
        self.content_layout.addLayout(wpm_scatter_header)
        
        self.wpm_scatter_chart = MetricScatterPlot(metric_type='wpm')
        self.wpm_scatter_chart.setFixedHeight(220)
        self.content_layout.addWidget(self.wpm_scatter_chart)
        
        # Accuracy Over Time
        acc_scatter_header = QHBoxLayout()
        acc_scatter_header.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        acc_scatter_header.setContentsMargins(0, 16, 0, 0)
        self.acc_scatter_label = QLabel("Accuracy Over Time")
        self.acc_scatter_label.setStyleSheet(label_style)
        acc_scatter_header.addWidget(self.acc_scatter_label)
        self.content_layout.addLayout(acc_scatter_header)
        
        self.acc_scatter_chart = MetricScatterPlot(metric_type='accuracy')
        self.acc_scatter_chart.setFixedHeight(220)
        self.content_layout.addWidget(self.acc_scatter_chart)
        
        
        # WPM Distribution Bar Chart
        bar_header = QHBoxLayout()
        bar_header.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        bar_header.setContentsMargins(0, 16, 0, 0)

        self.bar_label = QLabel("WPM Distribution")
        self.bar_label.setStyleSheet(label_style)
        bar_header.addWidget(self.bar_label)
        self.content_layout.addLayout(bar_header)
        
        self.wpm_distribution_chart = WPMDistributionChart()
        self.wpm_distribution_chart.setFixedHeight(220)
        self.content_layout.addWidget(self.wpm_distribution_chart)
        
        # Load persisted preferences
        self._load_stats_preferences()
    
    def _get_combo_style(self) -> str:
        """Get theme-based combo box style for stats dropdowns."""
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
                padding: 4px 12px;
                font-size: 11px;
            }}
            QComboBox:hover {{ border-color: {hover}; }}
            QComboBox::drop-down {{ 
                border: none; 
                width: 0px; 
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg};
                color: {text};
                selection-background-color: {colors["bg_primary"].name()};
                border: 1px solid {border};
                outline: 0px;
            }}
        """
    
    def _load_stats_preferences(self):
        """Load persisted stats page preferences."""
        # Heatmap metric
        heatmap_metric = settings.get_setting("stats_heatmap_metric", settings.get_default("stats_heatmap_metric"))
        metric_keys = [m[0] for m in CalendarHeatmap.METRIC_OPTIONS]
        if heatmap_metric in metric_keys:
            self.heatmap_metric_combo.setCurrentIndex(metric_keys.index(heatmap_metric))
            self.calendar_heatmap.set_metric(heatmap_metric)
    
    def _save_stats_preferences(self):
        """Save current stats page preferences."""
        # Heatmap metric
        heatmap_idx = self.heatmap_metric_combo.currentIndex()
        if 0 <= heatmap_idx < len(CalendarHeatmap.METRIC_OPTIONS):
            settings.set_setting("stats_heatmap_metric", CalendarHeatmap.METRIC_OPTIONS[heatmap_idx][0])
    
    def _on_heatmap_metric_changed(self, index: int):
        """Handle heatmap metric dropdown change."""
        if 0 <= index < len(CalendarHeatmap.METRIC_OPTIONS):
            metric = CalendarHeatmap.METRIC_OPTIONS[index][0]
            self.calendar_heatmap.set_metric(metric)
            self._save_stats_preferences()
    
    def _on_filter_changed(self, selected_languages: Set[str]):
        """Handle language filter change."""
        self._selected_languages = selected_languages
        self._update_all_stats()
    
    def _on_heatmap_year_changed(self, index: int):
        """Handle heatmap year dropdown change."""
        self._update_calendar_heatmap(list(self._selected_languages) if self._selected_languages else None)

    def _on_kb_shift_toggled(self):
        """Handle keyboard heatmap shift toggle."""
        is_on = self.kb_shift_btn.isChecked()
        self.kb_shift_btn.setText("Shift: On" if is_on else "Shift: Off")
        self.keyboard_heatmap.toggle_shift(is_on)
        self._save_stats_preferences()
    
    def refresh(self):
        """Refresh all data in the stats tab."""
        # Load available languages
        languages = stats_db.list_history_languages()
        self.filter_bar.set_languages(languages)
        
        # Load available years for the heatmap
        years = stats_db.get_available_years()
        self.heatmap_year_combo.blockSignals(True)
        self.heatmap_year_combo.clear()
        for y in years:
            self.heatmap_year_combo.addItem(str(y))
        
        # Default to current year
        current_year = datetime.now().year
        idx = self.heatmap_year_combo.findText(str(current_year))
        if idx != -1:
            self.heatmap_year_combo.setCurrentIndex(idx)
        else:
            self.heatmap_year_combo.setCurrentIndex(0)
        self.heatmap_year_combo.blockSignals(False)
        
        # Update all stats and charts
        self._update_all_stats()
    
    def _update_all_stats(self):
        """Update all statistics and charts based on current filters."""
        langs = list(self._selected_languages) if self._selected_languages else None
        
        self._update_summary_stats(langs)
        self._update_calendar_heatmap(langs)
        self._update_keyboard_heatmap()
        self._update_error_type_stats(langs)
        self._update_scatter_chart(langs)
        self._update_wpm_distribution(langs)
    
    def _update_summary_stats(self, languages_list=None):
        """Update the summary statistics based on current filters."""
        # Get aggregated stats from database
        stats = stats_db.get_aggregated_stats(languages=languages_list)
        
        # Get streak
        streak = stats_db.get_current_streak()
        streak_text = f"{streak} days" if streak > 0 else "0"
        self.summary_cards["streak"].set_value(streak_text)
        
        # Get trend comparison (filtered by language)
        trend = stats_db.get_trend_comparison(30, languages=languages_list)
        
        # Update cards
        self.summary_cards["total_completed"].set_value(str(stats.get("total_completed", 0)))
        
        avg_wpm = stats.get("avg_wpm")
        self.summary_cards["avg_wpm"].set_value(f"{avg_wpm:.1f}" if avg_wpm else "-")
        
        highest_wpm = stats.get("highest_wpm")
        self.summary_cards["highest_wpm"].set_value(f"{highest_wpm:.1f}" if highest_wpm else "-")
        
        # WPM trend
        wpm_delta = trend.get("wpm_delta", 0)
        if wpm_delta > 0:
            self.summary_cards["wpm_trend"].set_value(f"+{wpm_delta:.1f}")
        elif wpm_delta < 0:
            self.summary_cards["wpm_trend"].set_value(f"{wpm_delta:.1f}")
        else:
            self.summary_cards["wpm_trend"].set_value("0.0")
        
        avg_acc = stats.get("avg_acc")
        self.summary_cards["avg_acc"].set_value(f"{avg_acc:.1f}%" if avg_acc else "-")
        
        highest_acc = stats.get("highest_acc")
        self.summary_cards["highest_acc"].set_value(f"{highest_acc:.1f}%" if highest_acc else "-")
        
        # Accuracy trend
        acc_delta = trend.get("acc_delta", 0)
        if acc_delta > 0:
            self.summary_cards["acc_trend"].set_value(f"+{acc_delta:.1f}%")
        elif acc_delta < 0:
            self.summary_cards["acc_trend"].set_value(f"{acc_delta:.1f}%")
        else:
            self.summary_cards["acc_trend"].set_value("0.0%")
        
        most_chars = stats.get("most_chars_day")
        self.summary_cards["most_chars_day"].set_value(f"{most_chars:,}" if most_chars else "-")
        
        most_sessions = stats.get("most_sessions_day")
        self.summary_cards["most_sessions_day"].set_value(str(most_sessions) if most_sessions else "-")
    
    def _update_calendar_heatmap(self, languages_list=None):
        """Update the calendar heatmap with daily activity data for the selected year."""
        year_str = self.heatmap_year_combo.currentText()
        if not year_str:
            year = datetime.now().year
        else:
            try:
                year = int(year_str)
            except ValueError:
                year = datetime.now().year
        
        self.calendar_heatmap.set_year(year)
        
        # Load data for the specific year
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        daily_data = stats_db.get_daily_metrics(
            languages=languages_list,
            start_date=start_date,
            end_date=end_date
        )
        self.calendar_heatmap.set_data(daily_data)
    
    def _update_scatter_chart(self, languages_list=None):
        """Update the WPM and Accuracy scatter charts."""
        session_data = stats_db.get_sessions_over_time(languages=languages_list)
        self.wpm_scatter_chart.set_data(session_data)
        self.acc_scatter_chart.set_data(session_data)
    
    def _update_wpm_distribution(self, languages_list=None):
        """Update the WPM distribution bar chart."""
        distribution_data = stats_db.get_wpm_distribution(languages=languages_list)
        self.wpm_distribution_chart.set_data(distribution_data)

    def _update_keyboard_heatmap(self):
        """Update the keyboard accuracy heatmap."""
        langs = list(self._selected_languages) if self._selected_languages else None
        key_stats = stats_db.get_key_stats(langs)
        key_confusions = stats_db.get_key_confusions(langs)
        self.keyboard_heatmap.set_data(key_stats, key_confusions)

    def _update_error_type_stats(self, languages_list=None):
        """Update the error type breakdown pie chart."""
        error_data = stats_db.get_error_type_stats(languages_list)
        self.error_pie_chart.set_data(error_data)
    
    
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
        self.summary_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {text_secondary};")
        
        # Update chart section labels
        label_style = f"font-size: 16px; font-weight: bold; color: {text_secondary};"
        if hasattr(self, 'heatmap_label'):
            self.heatmap_label.setStyleSheet(label_style)
        if hasattr(self, 'heatmap_metric_combo'):
            self.heatmap_metric_combo.setStyleSheet(self._get_combo_style())
        if hasattr(self, 'heatmap_year_combo'):
            self.heatmap_year_combo.setStyleSheet(self._get_combo_style())
        if hasattr(self, 'wpm_scatter_label'):
            self.wpm_scatter_label.setStyleSheet(label_style)
        if hasattr(self, 'acc_scatter_label'):
            self.acc_scatter_label.setStyleSheet(label_style)
        if hasattr(self, 'heatmap_kb_label'):
            self.heatmap_kb_label.setStyleSheet(label_style)
        if hasattr(self, 'error_breakdown_label'):
            self.error_breakdown_label.setStyleSheet(label_style)
        if hasattr(self, 'bar_label'):
            self.bar_label.setStyleSheet(label_style)
        
        if hasattr(self, 'kb_shift_btn'):
            self.kb_shift_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors['bg_tertiary'].name()};
                    color: {colors['text_primary'].name()};
                    border: 1px solid {colors['border'].name()};
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 11px;
                }}
                QPushButton:checked {{
                    background-color: {colors['accent'].name()};
                    color: white;
                }}
            """)
        self.filter_bar.apply_theme()
        
        # Update summary cards
        for card in self.summary_cards.values():
            card.apply_theme()
        
        # Update charts
        self.calendar_heatmap.apply_theme()
        self.wpm_scatter_chart.apply_theme()
        self.acc_scatter_chart.apply_theme()
        self.keyboard_heatmap.apply_theme()
        if hasattr(self, 'error_pie_chart'):
            self.error_pie_chart.apply_theme()
        self.wpm_distribution_chart.apply_theme()
