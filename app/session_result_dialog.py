"""
Custom dialog for displaying typing session results with a modern, visually appealing design.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class SessionResultDialog(QDialog):
    """Modern, styled dialog for displaying session completion results."""
    
    def __init__(self, parent=None, stats=None, is_new_best=False, is_race=False, 
                 race_info=None, theme_colors=None):
        super().__init__(parent)
        self.stats = stats or {}
        self.is_new_best = is_new_best
        self.is_race = is_race
        self.race_info = race_info or {}
        self.theme_colors = theme_colors or self._get_default_colors()
        
        self.setWindowTitle("Session Complete")
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setMaximumWidth(450)
        self.setup_ui()
        self.apply_theme()
    
    def _get_default_colors(self):
        """Get default theme colors if none provided."""
        return {
            'bg': '#1e2738',
            'card_bg': '#2a3447',
            'text': '#e0e6ed',
            'accent': '#5cb3ff',
            'success': '#7ed957',
            'warning': '#ffd93d',
            'error': '#ff6b6b',
        }
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = self._create_title()
        layout.addWidget(title_label, alignment=Qt.AlignCenter)
        
        # Main stats card
        stats_card = self._create_stats_card()
        layout.addWidget(stats_card)
        
        # Keystroke details
        keystroke_widget = self._create_keystroke_details()
        layout.addWidget(keystroke_widget)
        
        # Race comparison if applicable
        if self.is_race and self.race_info:
            race_widget = self._create_race_comparison()
            layout.addWidget(race_widget)
        
        # New best badge if applicable
        if self.is_new_best:
            best_badge = self._create_new_best_badge()
            layout.addWidget(best_badge, alignment=Qt.AlignCenter)
        
        # OK button
        ok_button = QPushButton("Continue")
        ok_button.setMinimumHeight(36)
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)
        
        self.ok_button = ok_button
    
    def _create_title(self):
        """Create the title label."""
        if self.is_race:
            if self.race_info.get('winner') == 'user':
                title_text = "🎉 Victory!"
            elif self.race_info.get('winner') == 'ghost':
                title_text = "👻 Ghost Wins"
            else:
                title_text = "Race Complete"
        else:
            title_text = "Session Complete!"
        
        title = QLabel(title_text)
        title.setObjectName("title")
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        return title
    
    def _create_stats_card(self):
        """Create the main stats display card."""
        card = QFrame()
        card.setObjectName("statsCard")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # WPM - Large display
        wpm = self.stats.get('wpm', 0)
        wpm_container = QHBoxLayout()
        wpm_icon = QLabel("📈")
        wpm_icon.setFont(QFont("Segoe UI Emoji", 24))
        wpm_value = QLabel(f"{wpm:.1f}")
        wpm_value.setObjectName("wpmValue")
        wpm_value.setFont(QFont("Segoe UI", 36, QFont.Bold))
        wpm_label = QLabel("WPM")
        wpm_label.setObjectName("statLabel")
        wpm_label.setFont(QFont("Segoe UI", 10))
        
        wpm_container.addStretch()
        wpm_container.addWidget(wpm_icon)
        wpm_container.addWidget(wpm_value)
        wpm_container.addWidget(wpm_label, alignment=Qt.AlignBottom)
        wpm_container.addStretch()
        layout.addLayout(wpm_container)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setObjectName("separator")
        layout.addWidget(separator)
        
        # Secondary stats row
        secondary_row = QHBoxLayout()
        secondary_row.setSpacing(20)
        
        # Accuracy
        accuracy = self.stats.get('accuracy', 1.0) * 100
        acc_widget = self._create_stat_item("✓", f"{accuracy:.1f}%", "Accuracy", 'success')
        secondary_row.addWidget(acc_widget)
        
        # Time
        time_val = self.stats.get('time', 0)
        mins = int(time_val // 60)
        secs = int(time_val % 60)
        time_str = f"{mins}:{secs:02d}" if mins > 0 else f"0:{secs:02d}"
        time_widget = self._create_stat_item("⏱", time_str, "Time", 'warning')
        secondary_row.addWidget(time_widget)
        
        layout.addLayout(secondary_row)
        
        return card
    
    def _create_stat_item(self, icon, value, label, color_key='text'):
        """Create a stat display item."""
        container = QFrame()
        container.setObjectName("statItem")
        layout = QVBoxLayout(container)
        layout.setSpacing(3)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 18))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # Value
        value_label = QLabel(value)
        value_label.setObjectName(f"statValue_{color_key}")
        value_label.setFont(QFont("Segoe UI", 22, QFont.Bold))
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)
        
        # Label
        label_widget = QLabel(label)
        label_widget.setObjectName("statLabel")
        label_widget.setFont(QFont("Segoe UI", 9))
        label_widget.setAlignment(Qt.AlignCenter)
        layout.addWidget(label_widget)
        
        return container
    
    def _create_keystroke_details(self):
        """Create keystroke breakdown display."""
        container = QFrame()
        container.setObjectName("detailsCard")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(15)
        
        correct = self.stats.get('correct', 0)
        incorrect = self.stats.get('incorrect', 0)
        total = self.stats.get('total', 0)
        
        # Correct keystrokes
        correct_widget = self._create_keystroke_stat("✓", str(correct), 
                                                      f"({correct/total*100:.0f}%)" if total > 0 else "(0%)", 
                                                      'success')
        layout.addWidget(correct_widget)
        
        # Separator
        sep = QLabel("•")
        sep.setObjectName("separator")
        sep.setFont(QFont("Segoe UI", 16))
        layout.addWidget(sep, alignment=Qt.AlignCenter)
        
        # Incorrect keystrokes
        incorrect_widget = self._create_keystroke_stat("✗", str(incorrect), 
                                                        f"({incorrect/total*100:.0f}%)" if total > 0 else "(0%)", 
                                                        'error')
        layout.addWidget(incorrect_widget)
        
        # Separator
        sep2 = QLabel("•")
        sep2.setObjectName("separator")
        sep2.setFont(QFont("Segoe UI", 16))
        layout.addWidget(sep2, alignment=Qt.AlignCenter)
        
        # Total keystrokes
        total_widget = self._create_keystroke_stat("Σ", str(total), "(100%)", 'text')
        layout.addWidget(total_widget)
        
        return container
    
    def _create_keystroke_stat(self, icon, value, percentage, color_key):
        """Create a keystroke stat display."""
        container = QFrame()
        layout = QVBoxLayout(container)
        layout.setSpacing(1)
        layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QLabel(icon)
        icon_label.setObjectName(f"keystrokeIcon_{color_key}")
        icon_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        value_label = QLabel(value)
        value_label.setObjectName(f"keystrokeValue_{color_key}")
        value_label.setFont(QFont("Segoe UI", 15, QFont.Bold))
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)
        
        pct_label = QLabel(percentage)
        pct_label.setObjectName("statLabel")
        pct_label.setFont(QFont("Segoe UI", 8))
        pct_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(pct_label)
        
        return container
    
    def _create_race_comparison(self):
        """Create race comparison section."""
        container = QFrame()
        container.setObjectName("raceCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("👻 Race Results")
        title.setObjectName("sectionTitle")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(title)
        
        # Comparison row
        comp_layout = QHBoxLayout()
        comp_layout.setSpacing(12)
        
        # Your stats
        your_layout = QVBoxLayout()
        your_label = QLabel("You")
        your_label.setObjectName("statLabel")
        your_label.setFont(QFont("Segoe UI", 9))
        your_layout.addWidget(your_label, alignment=Qt.AlignCenter)
        
        your_wpm = QLabel(f"{self.stats.get('wpm', 0):.1f} WPM")
        your_wpm.setObjectName("statValue_accent")
        your_wpm.setFont(QFont("Segoe UI", 12, QFont.Bold))
        your_layout.addWidget(your_wpm, alignment=Qt.AlignCenter)
        
        your_time = QLabel(f"{self.stats.get('time', 0):.2f}s")
        your_time.setObjectName("statLabel")
        your_time.setFont(QFont("Segoe UI", 9))
        your_layout.addWidget(your_time, alignment=Qt.AlignCenter)
        
        comp_layout.addLayout(your_layout)
        
        # VS
        vs_label = QLabel("VS")
        vs_label.setObjectName("vsLabel")
        vs_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        comp_layout.addWidget(vs_label, alignment=Qt.AlignCenter)
        
        # Ghost stats
        ghost_layout = QVBoxLayout()
        ghost_label = QLabel("Ghost")
        ghost_label.setObjectName("statLabel")
        ghost_label.setFont(QFont("Segoe UI", 9))
        ghost_layout.addWidget(ghost_label, alignment=Qt.AlignCenter)
        
        ghost_wpm = QLabel(f"{self.race_info.get('ghost_wpm', 0):.1f} WPM")
        ghost_wpm.setObjectName("statValue_text")
        ghost_wpm.setFont(QFont("Segoe UI", 12, QFont.Bold))
        ghost_layout.addWidget(ghost_wpm, alignment=Qt.AlignCenter)
        
        ghost_time = QLabel(f"{self.race_info.get('ghost_time', 0):.2f}s")
        ghost_time.setObjectName("statLabel")
        ghost_time.setFont(QFont("Segoe UI", 9))
        ghost_layout.addWidget(ghost_time, alignment=Qt.AlignCenter)
        
        comp_layout.addLayout(ghost_layout)
        
        layout.addLayout(comp_layout)
        
        # Time difference
        if 'time_delta' in self.race_info:
            delta = self.race_info['time_delta']
            winner = self.race_info.get('winner')
            if winner == 'user':
                delta_text = f"⏱️ You were {abs(delta):.2f}s faster!"
                delta_color = 'success'
            else:
                delta_text = f"⏱️ Ghost was {abs(delta):.2f}s faster"
                delta_color = 'error'
            
            delta_label = QLabel(delta_text)
            delta_label.setObjectName(f"deltaLabel_{delta_color}")
            delta_label.setFont(QFont("Segoe UI", 10))
            delta_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(delta_label)
        
        return container
    
    def _create_new_best_badge(self):
        """Create new personal best badge."""
        badge = QFrame()
        badge.setObjectName("newBestBadge")
        layout = QVBoxLayout(badge)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(3)
        
        title = QLabel("🏆 NEW PERSONAL BEST! 👻")
        title.setObjectName("bestTitle")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Ghost saved! Challenge it with the 👻 button.")
        subtitle.setObjectName("bestSubtitle")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        return badge
    
    def apply_theme(self):
        """Apply theme colors to the dialog."""
        bg = self.theme_colors['bg']
        card_bg = self.theme_colors['card_bg']
        text = self.theme_colors['text']
        accent = self.theme_colors['accent']
        success = self.theme_colors['success']
        warning = self.theme_colors['warning']
        error = self.theme_colors['error']
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {text};
            }}
            
            QLabel#title {{
                color: {text};
            }}
            
            QFrame#statsCard, QFrame#detailsCard, QFrame#raceCard {{
                background-color: {card_bg};
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            
            QLabel#wpmValue {{
                color: {accent};
            }}
            
            QLabel#statValue_success {{
                color: {success};
            }}
            
            QLabel#statValue_warning {{
                color: {warning};
            }}
            
            QLabel#statValue_error {{
                color: {error};
            }}
            
            QLabel#statValue_accent {{
                color: {accent};
            }}
            
            QLabel#statValue_text {{
                color: {text};
            }}
            
            QLabel#statLabel {{
                color: rgba(224, 230, 237, 0.7);
            }}
            
            QLabel#keystrokeIcon_success {{
                color: {success};
            }}
            
            QLabel#keystrokeIcon_error {{
                color: {error};
            }}
            
            QLabel#keystrokeIcon_text {{
                color: {text};
            }}
            
            QLabel#keystrokeValue_success {{
                color: {success};
            }}
            
            QLabel#keystrokeValue_error {{
                color: {error};
            }}
            
            QLabel#keystrokeValue_text {{
                color: {text};
            }}
            
            QFrame#separator {{
                background-color: rgba(255, 255, 255, 0.1);
                max-height: 1px;
            }}
            
            QLabel#separator {{
                color: rgba(224, 230, 237, 0.3);
            }}
            
            QLabel#sectionTitle {{
                color: {text};
            }}
            
            QLabel#vsLabel {{
                color: rgba(224, 230, 237, 0.5);
            }}
            
            QLabel#deltaLabel_success {{
                color: {success};
            }}
            
            QLabel#deltaLabel_error {{
                color: {error};
            }}
            
            QFrame#newBestBadge {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(255, 215, 0, 0.15),
                    stop:1 rgba(255, 140, 0, 0.15));
                border: 2px solid rgba(255, 215, 0, 0.4);
                border-radius: 10px;
            }}
            
            QLabel#bestTitle {{
                color: #FFD700;
            }}
            
            QLabel#bestSubtitle {{
                color: rgba(224, 230, 237, 0.8);
            }}
            
            QPushButton {{
                background-color: {accent};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 30px;
                font-size: 13px;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: rgba(92, 179, 255, 0.8);
            }}
            
            QPushButton:pressed {{
                background-color: rgba(92, 179, 255, 0.6);
            }}
        """)
