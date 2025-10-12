"""Stats display widget showing live typing statistics."""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class StatsBox(QFrame):
    """Individual stat display box."""
    
    def __init__(self, title: str, color: str = "#ffffff", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        
        layout = QVBoxLayout(self)
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 11px; color: #aaaaaa;")
        layout.addWidget(self.title_label)
        
        # Value
        self.value_label = QLabel("--")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color};")
        layout.addWidget(self.value_label)
    
    def set_value(self, value: str):
        """Update the displayed value."""
        self.value_label.setText(value)


class KeystrokeBox(QFrame):
    """Detailed keystroke statistics box."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Keystrokes")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 11px; color: #aaaaaa;")
        layout.addWidget(title)
        
        # Counts section
        counts_layout = QHBoxLayout()
        
        self.correct_count = QLabel("0")
        self.correct_count.setStyleSheet("color: #00ff00; font-weight: bold;")
        self.correct_count.setAlignment(Qt.AlignCenter)
        
        self.incorrect_count = QLabel("0")
        self.incorrect_count.setStyleSheet("color: #ff0000; font-weight: bold;")
        self.incorrect_count.setAlignment(Qt.AlignCenter)
        
        self.total_count = QLabel("0")
        self.total_count.setStyleSheet("color: #00bfff; font-weight: bold;")
        self.total_count.setAlignment(Qt.AlignCenter)
        
        counts_layout.addWidget(QLabel("✓"))
        counts_layout.addWidget(self.correct_count)
        counts_layout.addStretch()
        counts_layout.addWidget(QLabel("✗"))
        counts_layout.addWidget(self.incorrect_count)
        counts_layout.addStretch()
        counts_layout.addWidget(QLabel("Σ"))
        counts_layout.addWidget(self.total_count)
        
        layout.addLayout(counts_layout)
        
        # Percentages section
        percent_layout = QHBoxLayout()
        
        self.correct_percent = QLabel("100%")
        self.correct_percent.setStyleSheet("color: #00ff00; font-size: 11px;")
        self.correct_percent.setAlignment(Qt.AlignCenter)
        
        self.incorrect_percent = QLabel("0%")
        self.incorrect_percent.setStyleSheet("color: #ff0000; font-size: 11px;")
        self.incorrect_percent.setAlignment(Qt.AlignCenter)
        
        self.total_percent = QLabel("100%")
        self.total_percent.setStyleSheet("color: #00bfff; font-size: 11px;")
        self.total_percent.setAlignment(Qt.AlignCenter)
        
        percent_layout.addWidget(self.correct_percent)
        percent_layout.addStretch()
        percent_layout.addWidget(self.incorrect_percent)
        percent_layout.addStretch()
        percent_layout.addWidget(self.total_percent)
        
        layout.addLayout(percent_layout)
    
    def update_stats(self, correct: int, incorrect: int, total: int):
        """Update keystroke statistics."""
        self.correct_count.setText(str(correct))
        self.incorrect_count.setText(str(incorrect))
        self.total_count.setText(str(total))
        
        if total > 0:
            correct_pct = (correct / total) * 100
            incorrect_pct = (incorrect / total) * 100
            self.correct_percent.setText(f"{correct_pct:.1f}%")
            self.incorrect_percent.setText(f"{incorrect_pct:.1f}%")
            self.total_percent.setText("100%")
        else:
            self.correct_percent.setText("--")
            self.incorrect_percent.setText("--")
            self.total_percent.setText("--")


class StatsDisplayWidget(QWidget):
    """Widget displaying live typing statistics."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        
        # WPM box
        self.wpm_box = StatsBox("WPM", color="#00ff00")
        layout.addWidget(self.wpm_box)
        
        # Time box
        self.time_box = StatsBox("Time", color="#c0c0c0")
        layout.addWidget(self.time_box)
        
        # Accuracy box
        self.accuracy_box = StatsBox("Accuracy", color="#00ff00")
        layout.addWidget(self.accuracy_box)
        
        # Keystrokes box
        self.keystroke_box = KeystrokeBox()
        layout.addWidget(self.keystroke_box)
        
        # Paused indicator
        self.paused_label = QLabel("⏸ PAUSED")
        self.paused_label.setAlignment(Qt.AlignCenter)
        self.paused_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #ffaa00; "
            "background-color: #333333; padding: 10px; border-radius: 5px;"
        )
        self.paused_label.hide()
        layout.addWidget(self.paused_label)
        
        layout.addStretch()
    
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
        
        # Paused indicator
        is_paused = stats.get("is_paused", True)
        self.paused_label.setVisible(is_paused)
