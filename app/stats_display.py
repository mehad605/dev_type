"""Stats display widget showing live typing statistics."""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QGridLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from app import settings


class StatsBox(QFrame):
    """Individual stat display box with theme support."""
    
    def __init__(self, title: str, value_key: str = None, parent=None):
        super().__init__(parent)
        self.value_key = value_key
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(9)
        font.setBold(False)
        self.title_label.setFont(font)
        layout.addWidget(self.title_label)
        
        # Value
        self.value_label = QLabel("--")
        self.value_label.setAlignment(Qt.AlignCenter)
        value_font = QFont()
        value_font.setPointSize(20)
        value_font.setBold(True)
        self.value_label.setFont(value_font)
        layout.addWidget(self.value_label)
        
        self.apply_theme()
    
    def set_value(self, value: str):
        """Update the displayed value."""
        self.value_label.setText(value)
    
    def apply_theme(self):
        """Apply current theme colors."""
        theme = settings.get_setting("theme", "dark")
        
        if theme == "dark":
            bg_color = "#2e3440"
            border_color = "#4c566a"
            title_color = "#d8dee9"
            
            # Value colors based on stat type
            if self.value_key == "wpm":
                value_color = "#88c0d0"  # Nord frost blue
            elif self.value_key == "accuracy":
                value_color = "#a3be8c"  # Nord green
            elif self.value_key == "time":
                value_color = "#ebcb8b"  # Nord yellow
            else:
                value_color = "#d8dee9"
        else:
            bg_color = "#eceff4"
            border_color = "#d8dee9"
            title_color = "#2e3440"
            
            if self.value_key == "wpm":
                value_color = "#5e81ac"  # Nord blue
            elif self.value_key == "accuracy":
                value_color = "#a3be8c"  # Nord green
            elif self.value_key == "time":
                value_color = "#d08770"  # Nord orange
            else:
                value_color = "#2e3440"
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
        """)
        self.title_label.setStyleSheet(f"color: {title_color};")
        self.value_label.setStyleSheet(f"color: {value_color};")


class KeystrokeBox(QFrame):
    """Detailed keystroke statistics box with theme support."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)
        
        # Title
        self.title = QLabel("Keystrokes")
        self.title.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(9)
        font.setBold(False)
        self.title.setFont(font)
        layout.addWidget(self.title)
        
        # Grid for stats
        grid = QGridLayout()
        grid.setSpacing(8)
        
        # Correct keystrokes
        self.correct_icon = QLabel("✓")
        self.correct_icon.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.correct_count = QLabel("0")
        self.correct_count.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        count_font = QFont()
        count_font.setPointSize(14)
        count_font.setBold(True)
        self.correct_count.setFont(count_font)
        
        # Incorrect keystrokes
        self.incorrect_icon = QLabel("✗")
        self.incorrect_icon.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.incorrect_count = QLabel("0")
        self.incorrect_count.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.incorrect_count.setFont(count_font)
        
        # Total keystrokes
        self.total_icon = QLabel("Σ")
        self.total_icon.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.total_count = QLabel("0")
        self.total_count.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.total_count.setFont(count_font)
        
        grid.addWidget(self.correct_icon, 0, 0)
        grid.addWidget(self.correct_count, 0, 1)
        grid.addWidget(self.incorrect_icon, 1, 0)
        grid.addWidget(self.incorrect_count, 1, 1)
        grid.addWidget(self.total_icon, 2, 0)
        grid.addWidget(self.total_count, 2, 1)
        
        layout.addLayout(grid)
        
        self.apply_theme()
    
    def update_stats(self, correct: int, incorrect: int, total: int):
        """Update keystroke statistics."""
        self.correct_count.setText(str(correct))
        self.incorrect_count.setText(str(incorrect))
        self.total_count.setText(str(total))
    
    def apply_theme(self):
        """Apply current theme colors."""
        theme = settings.get_setting("theme", "dark")
        correct_color = settings.get_setting("color_correct", "#00ff00")
        incorrect_color = settings.get_setting("color_incorrect", "#ff0000")
        
        if theme == "dark":
            bg_color = "#2e3440"
            border_color = "#4c566a"
            title_color = "#d8dee9"
            total_color = "#88c0d0"
            icon_color = "#d8dee9"
        else:
            bg_color = "#eceff4"
            border_color = "#d8dee9"
            title_color = "#2e3440"
            total_color = "#5e81ac"
            icon_color = "#4c566a"
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
        """)
        
        self.title.setStyleSheet(f"color: {title_color};")
        self.correct_icon.setStyleSheet(f"color: {icon_color};")
        self.incorrect_icon.setStyleSheet(f"color: {icon_color};")
        self.total_icon.setStyleSheet(f"color: {icon_color};")
        self.correct_count.setStyleSheet(f"color: {correct_color};")
        self.incorrect_count.setStyleSheet(f"color: {incorrect_color};")
        self.total_count.setStyleSheet(f"color: {total_color};")


class StatsDisplayWidget(QWidget):
    """Widget displaying live typing statistics with theme support."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
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
        
        # Status indicator (paused/active)
        status_container = QFrame()
        status_container.setFrameShape(QFrame.StyledPanel)
        status_container.setFrameShadow(QFrame.Raised)
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(12, 8, 12, 8)
        
        self.status_label = QLabel("Status")
        self.status_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(9)
        self.status_label.setFont(font)
        status_layout.addWidget(self.status_label)
        
        self.paused_label = QLabel("⏸\nPAUSED")
        self.paused_label.setAlignment(Qt.AlignCenter)
        pause_font = QFont()
        pause_font.setPointSize(12)
        pause_font.setBold(True)
        self.paused_label.setFont(pause_font)
        status_layout.addWidget(self.paused_label)
        
        self.active_label = QLabel("▶\nACTIVE")
        self.active_label.setAlignment(Qt.AlignCenter)
        self.active_label.setFont(pause_font)
        self.active_label.hide()
        status_layout.addWidget(self.active_label)
        
        self.finished_label = QLabel("✓\nFINISHED")
        self.finished_label.setAlignment(Qt.AlignCenter)
        self.finished_label.setFont(pause_font)
        self.finished_label.hide()
        status_layout.addWidget(self.finished_label)
        
        layout.addWidget(status_container, 1)
        
        self.status_container = status_container
        self.apply_theme()
    
    def update_stats(self, stats: dict):
        """Update all statistics displays."""
        # WPM
        wpm = stats.get("wpm", 0.0)
        self.wpm_box.set_value(f"{wpm:.1f}")
        
        # Time
        time_sec = stats.get("time", 0.0)
        minutes = int(time_sec // 60)
        seconds = int(time_sec % 60)
        self.time_box.set_value(f"{minutes}:{seconds:02d}")
        
        # Accuracy
        accuracy = stats.get("accuracy", 1.0) * 100
        self.accuracy_box.set_value(f"{accuracy:.1f}%")
        
        # Keystrokes
        correct = stats.get("correct", 0)
        incorrect = stats.get("incorrect", 0)
        total = stats.get("total", 0)
        self.keystroke_box.update_stats(correct, incorrect, total)
        
        # Status indicator
        is_finished = stats.get("is_finished", False)
        is_paused = stats.get("is_paused", True)
        
        if is_finished:
            self.finished_label.setVisible(True)
            self.paused_label.setVisible(False)
            self.active_label.setVisible(False)
        else:
            self.finished_label.setVisible(False)
            self.paused_label.setVisible(is_paused)
            self.active_label.setVisible(not is_paused)
    
    def apply_theme(self):
        """Apply current theme to all components."""
        theme = settings.get_setting("theme", "dark")
        paused_color = settings.get_setting("color_paused_highlight", "#ffaa00")
        
        if theme == "dark":
            bg_color = "#2e3440"
            border_color = "#4c566a"
            text_color = "#d8dee9"
            active_color = "#a3be8c"
        else:
            bg_color = "#eceff4"
            border_color = "#d8dee9"
            text_color = "#2e3440"
            active_color = "#a3be8c"
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
            }}
        """)
        
        self.status_container.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
        """)
        
        self.status_label.setStyleSheet(f"color: {text_color};")
        self.paused_label.setStyleSheet(f"color: {paused_color};")
        self.active_label.setStyleSheet(f"color: {active_color};")
        
        # Finished color - use green/success color
        finished_color = "#a3be8c" if theme == "dark" else "#a3be8c"
        self.finished_label.setStyleSheet(f"color: {finished_color};")
        
        # Update all boxes
        self.wpm_box.apply_theme()
        self.accuracy_box.apply_theme()
        self.time_box.apply_theme()
        self.keystroke_box.apply_theme()
