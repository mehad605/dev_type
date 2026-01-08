"""Stats display widget showing live typing statistics."""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QGridLayout, QToolTip, QPushButton, QSizePolicy
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QFont, QCursor, QPainter, QPainterPath, QColor, QPen, QLinearGradient
from app import settings


class SparklineWidget(QWidget):
    """Mini chart widget for visualizing data trends."""
    
    def __init__(self, color_hex="#88c0d0", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.values = []
        self.color_hex = color_hex
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def add_value(self, value: float):
        self.values.append(value)
        if len(self.values) > 50:  # Keep last 50 points
            self.values.pop(0)
        self.update()
        
    def set_color(self, color_hex):
        self.color_hex = color_hex
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Draw flat line if not enough data
        if len(self.values) < 2:
            color = QColor(self.color_hex)
            pen = QPen(color, 2)
            painter.setPen(pen)
            # Draw a flat line at the bottom
            y = height - 2
            painter.drawLine(0, y, width, y)
            
            # Fill with very low opacity
            gradient = QLinearGradient(0, 0, 0, height)
            gradient.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 20))
            gradient.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
            painter.fillRect(0, int(y), width, int(height - y), gradient)
            return
            
        min_val = min(self.values)
        max_val = max(self.values)
        val_range = max_val - min_val if max_val != min_val else 1.0
        
        # Create path
        path = QPainterPath()
        
        # Calculate points
        points = []
        step_x = width / (len(self.values) - 1)
        
        for i, val in enumerate(self.values):
            x = i * step_x
            # Normalize value to 0-1 range, then flip Y (0 is top)
            normalized = (val - min_val) / val_range
            y = height - (normalized * height)
            # Add some padding so it doesn't touch edges exactly
            y = height - 2 - (normalized * (height - 4))
            points.append(QPointF(x, y))
            
        path.moveTo(points[0])
        for p in points[1:]:
            path.lineTo(p)
            
        # Draw line
        color = QColor(self.color_hex)
        pen = QPen(color, 2)
        painter.setPen(pen)
        painter.drawPath(path)
        
        # Optional: Fill under line
        fill_path = QPainterPath(path)
        fill_path.lineTo(width, height)
        fill_path.lineTo(0, height)
        fill_path.closeSubpath()
        
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 100))
        gradient.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
        
        painter.fillPath(fill_path, gradient)


class StatsBox(QFrame):
    """Individual stat display box with sparkline and theme support."""
    
    def __init__(self, title: str, value_key: str = None, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.value_key = value_key
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(9)
        font.setBold(False)
        self.title_label.setFont(font)
        layout.addWidget(self.title_label)
        
        # Sparkline
        self.sparkline = SparklineWidget()
        layout.addWidget(self.sparkline)
        
        # Value
        self.value_label = QLabel("--")
        self.value_label.setAlignment(Qt.AlignCenter)
        value_font = QFont()
        value_font.setPointSize(22)
        value_font.setBold(True)
        self.value_label.setFont(value_font)
        layout.addWidget(self.value_label)
        
        self.apply_theme()
    
    def set_value(self, value_str: str, raw_value: float = None):
        """Update the displayed value and sparkline."""
        self.value_label.setText(value_str)
        if raw_value is not None:
            self.sparkline.add_value(raw_value)
    
    def apply_theme(self):
        """Apply current theme colors."""
        from app.themes import get_color_scheme
        theme = settings.get_setting("theme", settings.get_default("theme"))
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme(theme, scheme_name)
        
        bg_color = scheme.bg_secondary
        border_color = scheme.border_color
        title_color = scheme.text_secondary
        
        # Value colors based on stat type
        if self.value_key == "wpm":
            value_color = scheme.info_color
        elif self.value_key == "accuracy":
            value_color = scheme.success_color
        elif self.value_key == "time":
            value_color = scheme.warning_color
        else:
            value_color = scheme.text_primary
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
        self.title_label.setStyleSheet(f"color: {title_color}; background: transparent; border: none;")
        self.value_label.setStyleSheet(f"color: {value_color}; background: transparent; border: none;")
        self.sparkline.set_color(value_color)


class KeystrokeBox(QFrame):
    """Detailed keystroke statistics box with theme support."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Title
        self.title = QLabel("Keystrokes")
        self.title.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(9)
        font.setBold(False)
        self.title.setFont(font)
        layout.addWidget(self.title)
        
        # Container for the grid to center it
        self.grid_container = QWidget()
        grid_layout = QHBoxLayout(self.grid_container)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setAlignment(Qt.AlignCenter)
        
        # Grid for stats
        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setContentsMargins(0, 0, 0, 0)
        
        count_font = QFont()
        count_font.setPointSize(11)
        count_font.setBold(True)
        
        # Correct
        self.correct_count = QLabel("0")
        self.correct_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.correct_count.setFont(count_font)
        
        self.correct_icon = QLabel("✓")
        self.correct_icon.setAlignment(Qt.AlignCenter)
        
        self.correct_pct = QLabel("0%")
        self.correct_pct.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.correct_pct.setFont(count_font)
        
        # Incorrect
        self.incorrect_count = QLabel("0")
        self.incorrect_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.incorrect_count.setFont(count_font)
        
        self.incorrect_icon = QLabel("✗")
        self.incorrect_icon.setAlignment(Qt.AlignCenter)
        
        self.incorrect_pct = QLabel("0%")
        self.incorrect_pct.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.incorrect_pct.setFont(count_font)
        
        # Total
        self.total_count = QLabel("0")
        self.total_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.total_count.setFont(count_font)
        
        self.total_icon = QLabel("Σ")
        self.total_icon.setAlignment(Qt.AlignCenter)
        
        self.total_pct = QLabel("100%")
        self.total_pct.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.total_pct.setFont(count_font)
        
        # Add to grid: Count | Icon | Percent
        # Row 0: Correct
        grid.addWidget(self.correct_count, 0, 0)
        grid.addWidget(self.correct_icon, 0, 1)
        grid.addWidget(self.correct_pct, 0, 2)
        
        # Row 1: Incorrect
        grid.addWidget(self.incorrect_count, 1, 0)
        grid.addWidget(self.incorrect_icon, 1, 1)
        grid.addWidget(self.incorrect_pct, 1, 2)
        
        # Row 2: Total
        grid.addWidget(self.total_count, 2, 0)
        grid.addWidget(self.total_icon, 2, 1)
        grid.addWidget(self.total_pct, 2, 2)
        
        grid_layout.addLayout(grid)
        layout.addWidget(self.grid_container)
        
        self.apply_theme()
    
    def update_stats(self, correct: int, incorrect: int, total: int):
        """Update keystroke statistics."""
        # Calculate percentages
        if total > 0:
            correct_pct = (correct / total) * 100
            incorrect_pct = (incorrect / total) * 100
        else:
            correct_pct = 0.0
            incorrect_pct = 0.0
        
        # Update counts
        self.correct_count.setText(str(correct))
        self.incorrect_count.setText(str(incorrect))
        self.total_count.setText(str(total))
        
        # Update percentages
        self.correct_pct.setText(f"{correct_pct:.0f}%")
        self.incorrect_pct.setText(f"{incorrect_pct:.0f}%")
        self.total_pct.setText("100%")
    
    def apply_theme(self):
        """Apply current theme colors."""
        from app.themes import get_color_scheme
        theme = settings.get_setting("theme", settings.get_default("theme"))
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme(theme, scheme_name)
        
        bg_color = scheme.bg_secondary
        border_color = scheme.border_color
        title_color = scheme.text_secondary
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
        
        self.title.setStyleSheet(f"color: {title_color}; background: transparent; border: none;")
        self.grid_container.setStyleSheet("background: transparent; border: none;")
        
        # Icons
        self.correct_icon.setStyleSheet(f"color: {scheme.success_color}; background: transparent; border: none; font-size: 14px;")
        self.incorrect_icon.setStyleSheet(f"color: {scheme.error_color}; background: transparent; border: none; font-size: 14px;")
        self.total_icon.setStyleSheet(f"color: {scheme.info_color}; background: transparent; border: none; font-size: 14px;")
        
        # Counts (same color as icons for visual connection)
        self.correct_count.setStyleSheet(f"color: {scheme.success_color}; background: transparent; border: none;")
        self.incorrect_count.setStyleSheet(f"color: {scheme.error_color}; background: transparent; border: none;")
        self.total_count.setStyleSheet(f"color: {scheme.info_color}; background: transparent; border: none;")
        
        # Percentages (slightly dimmer or same)
        self.correct_pct.setStyleSheet(f"color: {scheme.success_color}; background: transparent; border: none;")
        self.incorrect_pct.setStyleSheet(f"color: {scheme.error_color}; background: transparent; border: none;")
        self.total_pct.setStyleSheet(f"color: {scheme.info_color}; background: transparent; border: none;")


class InteractiveStatusBox(QFrame):
    """Interactive status box that can be clicked to pause/unpause."""
    
    pause_clicked = Signal()  # Emitted when clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        
        self.is_paused = True
        self.is_finished = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        
        self.status_label = QLabel("Status")
        self.status_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(9)
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)
        
        # Status Text
        self.status_text = QLabel("ACTIVE")
        self.status_text.setAlignment(Qt.AlignCenter)
        status_font = QFont()
        status_font.setPointSize(14)
        status_font.setBold(True)
        self.status_text.setFont(status_font)
        layout.addWidget(self.status_text)
        
        # Cancel/Pause Button
        self.action_btn = QPushButton("Cancel")
        self.action_btn.setCursor(Qt.PointingHandCursor)
        self.action_btn.setFixedHeight(30)
        self.action_btn.clicked.connect(self.pause_clicked.emit)
        layout.addWidget(self.action_btn)
    
    def update_status(self, is_paused: bool, is_finished: bool):
        """Update the status display."""
        self.is_paused = is_paused
        self.is_finished = is_finished
        
        if is_finished:
            self.status_text.setText("FINISHED")
            self.action_btn.setText("Reset")
            self.action_btn.setVisible(True)
        elif is_paused:
            self.status_text.setText("PAUSED")
            self.action_btn.setText("Resume")
        else:
            self.status_text.setText("ACTIVE")
            self.action_btn.setText("Cancel")
            
        self.apply_theme()
    
    def apply_theme(self):
        """Apply theme colors."""
        from app.themes import get_color_scheme
        theme = settings.get_setting("theme", settings.get_default("theme"))
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme(theme, scheme_name)
        
        bg_color = scheme.bg_secondary
        border_color = scheme.border_color
        text_color = scheme.text_secondary
        
        if self.is_finished:
            status_color = scheme.success_color
            btn_border = scheme.success_color
        elif self.is_paused:
            status_color = scheme.warning_color
            btn_border = scheme.warning_color
        else:
            status_color = scheme.success_color
            btn_border = scheme.error_color
            
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
        
        self.status_label.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
        self.status_text.setStyleSheet(f"color: {status_color}; background: transparent; border: none;")
        
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {scheme.text_primary};
                border: 1px solid {btn_border};
                border-radius: 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {btn_border};
                color: {scheme.bg_primary};
            }}
        """)

    def mousePressEvent(self, event):
        """Handle mouse click to toggle pause/unpause."""
        # Let the button handle clicks, but if they click the frame, also toggle
        if event.button() == Qt.LeftButton and not self.action_btn.underMouse():
            self.pause_clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)


class StatsDisplayWidget(QWidget):
    """Widget displaying live typing statistics with theme support."""
    
    pause_requested = Signal()  # Emitted when user clicks status or presses Ctrl+P
    reset_requested = Signal()  # Emitted when user clicks reset
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statsDisplay")
        self.is_finished = False
        
        # WPM history tracking: list of (time_seconds, wpm) tuples
        self.wpm_history = []
        self._last_recorded_second = -1
        
        # Error tracking: errors per second interval
        self._last_recorded_incorrect = 0  # Track cumulative incorrect count
        self.error_history = []  # list of (second, errors_in_that_second)
        
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # WPM box
        self.wpm_box = StatsBox("Words Per Minute", value_key="wpm")
        layout.addWidget(self.wpm_box, 1)
        
        # Accuracy box
        self.accuracy_box = StatsBox("Accuracy", value_key="accuracy")
        layout.addWidget(self.accuracy_box, 1)
        
        # Time box
        self.time_box = StatsBox("Time Elapsed", value_key="time")
        layout.addWidget(self.time_box, 1)
        
        # Keystrokes box
        self.keystroke_box = KeystrokeBox()
        layout.addWidget(self.keystroke_box, 1)
        
        # Interactive status indicator
        self.status_box = InteractiveStatusBox()
        self.status_box.pause_clicked.connect(self.on_status_action)
        layout.addWidget(self.status_box, 1)
        
        self.apply_theme()
    
    def on_status_action(self):
        """Handle status box click."""
        if self.is_finished:
            self.reset_requested.emit()
        else:
            self.pause_requested.emit()
    
    def update_stats(self, stats: dict):
        """Update all statistics displays."""
        self.is_finished = stats.get("is_finished", False)
        
        # WPM
        wpm = stats.get("wpm", 0.0)
        self.wpm_box.set_value(f"{wpm:.1f}", raw_value=wpm)
        
        # Time
        time_sec = stats.get("time", 0.0)
        minutes = int(time_sec // 60)
        seconds = int(time_sec % 60)
        self.time_box.set_value(f"{minutes}:{seconds:02d}", raw_value=time_sec)
        
        # Keystrokes - get these early for error tracking
        correct = stats.get("correct", 0)
        incorrect = stats.get("incorrect", 0)
        total = stats.get("total", 0)
        
        # Record WPM at each whole second for graph
        current_second = int(time_sec)
        if current_second > 0 and current_second > self._last_recorded_second and wpm > 0:
            self.wpm_history.append((current_second, wpm))
            
            # Track errors for this second interval
            errors_this_second = incorrect - self._last_recorded_incorrect
            if errors_this_second > 0:
                self.error_history.append((current_second, errors_this_second))
            self._last_recorded_incorrect = incorrect
            
            self._last_recorded_second = current_second
        
        # Accuracy
        if total > 0:
            accuracy = stats.get("accuracy", 1.0) * 100
        else:
            accuracy = 0.0
        self.accuracy_box.set_value(f"{accuracy:.1f}%", raw_value=accuracy)
        
        # Update keystroke display
        self.keystroke_box.update_stats(correct, incorrect, total)
        
        # Status indicator
        is_finished = stats.get("is_finished", False)
        is_paused = stats.get("is_paused", True)
        self.status_box.update_status(is_paused, is_finished)
    
    def get_wpm_history(self) -> list:
        """Get the recorded WPM history as list of (second, wpm) tuples."""
        return self.wpm_history.copy()
    
    def get_error_history(self) -> list:
        """Get the recorded error history as list of (second, error_count) tuples."""
        return self.error_history.copy()
    
    def clear_wpm_history(self):
        """Clear the WPM history for a new session."""
        self.wpm_history = []
        self._last_recorded_second = -1
        self.error_history = []
        self._last_recorded_incorrect = 0
    
    def apply_theme(self):
        """Apply current theme to all components."""
        from app.themes import get_color_scheme
        theme = settings.get_setting("theme", settings.get_default("theme"))
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme(theme, scheme_name)
        
        self.setStyleSheet(f"""
            #statsDisplay {{
                background-color: {scheme.bg_primary};
            }}
        """)
        
        # Update all boxes
        self.wpm_box.apply_theme()
        self.accuracy_box.apply_theme()
        self.time_box.apply_theme()
        self.keystroke_box.apply_theme()
        self.status_box.apply_theme()
