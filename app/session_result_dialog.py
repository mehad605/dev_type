"""
Modern session result dialog matching the specific 'Neon' design.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QWidget, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush, QFont
from pathlib import Path
from typing import List, Dict

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
        
        layout.addSpacing(10)
        
        # 2. WPM
        self._add_stat(layout, f"{wpm:.1f}", "WPM", size=24)
        
        # 3. Acc
        self._add_stat(layout, f"{acc:.0f}%", "Acc", size=24)
        
        layout.addStretch()
        
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
                 user_keystrokes: List[Dict] = None, ghost_keystrokes: List[Dict] = None):
        super().__init__(parent)
        self.stats = stats or {}
        self.is_race = is_race
        self.race_info = race_info or {}
        self.filename = filename or ""
        self.theme_colors = theme_colors or {}
        
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(500, 550) # Fixed size like the screenshot
        
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
        
        # Main background frame
        bg_frame = QFrame(self)
        bg_frame.setGeometry(0, 0, 500, 550)
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
        else:
            # If not race, maybe show Personal Best? Or just hide?
            # For now, let's just add a spacer to keep layout balanced if no ghost
            layout.addStretch()
            
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
