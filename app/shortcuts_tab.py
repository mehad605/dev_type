from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from app import settings

class ShortcutItem(QFrame):
    """A row displaying a shortcut and its description."""
    def __init__(self, key_text: str, description: str, parent=None):
        super().__init__(parent)
        self.setObjectName("ShortcutItem")
        self.setFrameShape(QFrame.StyledPanel)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(20)
        
        # Key Label (Pill style)
        self.key_label = QLabel(key_text)
        self.key_label.setAlignment(Qt.AlignCenter)
        self.key_label.setFixedWidth(120)
        key_font = QFont()
        key_font.setPointSize(10)
        key_font.setBold(True)
        self.key_label.setFont(key_font)
        
        # Description Label
        self.desc_label = QLabel(description)
        desc_font = QFont()
        desc_font.setPointSize(11)
        self.desc_label.setFont(desc_font)
        
        layout.addWidget(self.key_label)
        layout.addWidget(self.desc_label)
        layout.addStretch()
        
        self.apply_theme()

    def apply_theme(self):
        from app.themes import get_color_scheme
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)
        
        self.setStyleSheet(f"""
            QFrame#ShortcutItem {{
                background-color: {scheme.bg_secondary};
                border: 1px solid {scheme.border_color};
                border-radius: 8px;
            }}
            QFrame#ShortcutItem:hover {{
                border-color: {scheme.accent_color};
                background-color: {scheme.bg_tertiary};
            }}
        """)
        
        self.key_label.setStyleSheet(f"""
            QLabel {{
                background-color: {scheme.accent_color};
                color: {scheme.bg_primary};
                border-radius: 6px;
                padding: 4px 8px;
            }}
        """)
        
        self.desc_label.setStyleSheet(f"color: {scheme.text_primary}; background: transparent;")

class ShortcutsTab(QWidget):
    """Tab displaying all available keyboard shortcuts."""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        title_label = QLabel("Keyboard Shortcuts")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel("Increase your productivity with these powerful keyboard combinations.")
        desc_label.setStyleSheet("color: #888888; font-size: 11pt;")
        layout.addWidget(desc_label)
        
        # Scroll area for shortcuts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setContentsMargins(0, 10, 0, 10)
        self.container_layout.setSpacing(12)
        
        # Global Shortcuts
        self.add_section("Global", [
            ("Ctrl + T", "Cycle through available themes"),
            ("Alt + 1-7", "Switch between tabs"),
            ("Ctrl + L", "Toggle Lenient Mode (No mistake fixing)"),
            ("Ctrl + G", "Toggle Ghost Text visibility"),
            ("Ctrl + M", "Toggle sound (Mute/Unmute)"),
            ("Ctrl + S", "Toggle 'Show what you type' mode")
        ])
        
        # Typing Tab Shortcuts
        self.add_section("Typing Tab", [
            ("Ctrl + P", "Pause or Resume the current typing session"),
            ("Ctrl + R", "Select a random file from the current folder"),
            ("Ctrl + D", "Toggle Instant Death mode"),
            ("Alt + R", "Start a race against your ghost"),
            ("ESC", "Reset the current line or file")
        ])
        
        self.container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        self.title_label = title_label
        self.apply_theme()

    def add_section(self, title: str, shortcuts: list):
        section_label = QLabel(title.upper())
        section_label.setStyleSheet("color: #5e81ac; font-weight: bold; font-size: 10pt; margin-top: 10px;")
        self.container_layout.addWidget(section_label)
        
        for key, desc in shortcuts:
            item = ShortcutItem(key, desc)
            self.container_layout.addWidget(item)

    def apply_theme(self):
        from app.themes import get_color_scheme
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)
        
        self.title_label.setStyleSheet(f"color: {scheme.text_primary};")
        
        # Update all items
        for i in range(self.container_layout.count()):
            widget = self.container_layout.itemAt(i).widget()
            if isinstance(widget, ShortcutItem):
                widget.apply_theme()
            elif isinstance(widget, QLabel) and widget.text().isupper():
                widget.setStyleSheet(f"color: {scheme.accent_color}; font-weight: bold; font-size: 10pt; margin-top: 10px;")
