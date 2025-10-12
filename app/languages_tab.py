"""Languages tab widget for displaying language-grouped files."""
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QPushButton,
    QFrame,
    QGridLayout,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon
from typing import Dict, List
from app.file_scanner import scan_folders
from app import settings


class LanguageCard(QFrame):
    """Card widget displaying a single language with stats."""
    
    clicked = Signal(str, list)  # language_name, file_paths
    
    def __init__(self, language: str, files: List[str], parent=None):
        super().__init__(parent)
        self.language = language
        self.files = files
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(2)
        self.setMinimumSize(200, 150)
        self.setMaximumSize(250, 180)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        
        # Language icon placeholder (will be replaced with actual icons later)
        icon_label = QLabel("📄")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(icon_label)
        
        # Language name
        name_label = QLabel(language)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(name_label)
        
        # File count (completed/total)
        # TODO: Track completed files in database
        completed = 0  # Placeholder
        total = len(files)
        count_label = QLabel(f"{completed}/{total} files")
        count_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(count_label)
        
        # Avg WPM (placeholder)
        wpm_label = QLabel("Avg WPM: --")
        wpm_label.setAlignment(Qt.AlignCenter)
        wpm_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(wpm_label)
        
        layout.addStretch()
    
    def mousePressEvent(self, event):
        """Handle card click."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.language, self.files)
        super().mousePressEvent(event)


class LanguagesTab(QWidget):
    """Tab displaying all detected languages as cards."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Languages detected in your folders")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        self.layout.addWidget(header)
        
        # Scroll area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container for cards
        self.card_container = QWidget()
        self.card_layout = QGridLayout(self.card_container)
        self.card_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(self.card_container)
        
        self.layout.addWidget(scroll)
        
        self.refresh_languages()
    
    def refresh_languages(self):
        """Scan folders and update language cards."""
        # Clear existing cards
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get folders from settings
        folders = settings.get_folders()
        if not folders:
            empty_label = QLabel("No folders added. Go to Folders tab to add some.")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: gray; padding: 20px;")
            self.card_layout.addWidget(empty_label, 0, 0)
            return
        
        # Scan and group files
        language_files = scan_folders(folders)
        
        if not language_files:
            empty_label = QLabel("No code files found in added folders.")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: gray; padding: 20px;")
            self.card_layout.addWidget(empty_label, 0, 0)
            return
        
        # Create cards in grid layout
        row, col = 0, 0
        max_cols = 4
        
        for lang, files in sorted(language_files.items()):
            card = LanguageCard(lang, files)
            card.clicked.connect(self.on_language_clicked)
            self.card_layout.addWidget(card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def on_language_clicked(self, language: str, files: List[str]):
        """Handle language card click - navigate to typing tab."""
        parent_window = self.window()
        if hasattr(parent_window, 'open_typing_tab_for_language'):
            parent_window.open_typing_tab_for_language(language, files)
