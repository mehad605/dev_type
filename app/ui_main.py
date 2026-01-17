"""
Main UI module for Dev Typing App.

DEBUG_STARTUP_TIMING flag controls detailed startup performance profiling.
Set to True to see timing breakdowns during app initialization.
Also update the flag in:
  - app/editor_tab.py
  - app/languages_tab.py
for complete profiling coverage.
"""
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QStackedLayout,
    QSizePolicy,
    QFileDialog,
    QLabel,
    QToolBar,
    QStackedWidget,
    QTabWidget,
    QCheckBox,
    QMessageBox,
    QComboBox,
    QGroupBox,
    QFormLayout,
    QDialog,
    QScrollArea,
    QSlider,
    QSpinBox,
    QLineEdit,
    QColorDialog,
    QTextEdit,
    QRadioButton,
    QLayout,
    QGridLayout,
    QInputDialog,
)
from PySide6.QtGui import QIcon, QColor, QFontDatabase
from PySide6.QtCore import Qt, Signal, QObject, QSize, QTimer
import sys
import json
import shutil
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

import app.settings as settings
from app.languages_tab import LanguagesTab
from app.history_tab import HistoryTab
from app.editor_tab import EditorTab
from app.stats_tab import StatsTab
from app.shortcuts_tab import ShortcutsTab
from app.ui_profile_widgets import ProfileTrigger
from app.ui_profile_selector import ProfileManagerDialog
from app.profile_manager import get_profile_manager
from app.profile_transition import ProfileTransitionOverlay # NEW
from PySide6.QtWidgets import QGraphicsBlurEffect # NEW
from PySide6.QtCore import QPropertyAnimation, QEasingCurve # NEW
from app.ui_icons import get_pixmap, get_icon
# Toggle for startup timing debug output - set to False in production
DEBUG_STARTUP_TIMING = True


class FolderCardWidget(QFrame):
    """Stylized folder row used within the folders list."""

    remove_requested = Signal(str)  # Signal to request removal of this folder path

    def __init__(self, folder_path: str, parent=None):
        super().__init__(parent)
        self.setObjectName("folderCard")
        self.folder_path = folder_path
        self._list_widget = None
        self._list_item = None
        self._selected = False
        self._remove_mode = False
        self._folder_exists = Path(folder_path).exists()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(80) # Two rows is shorter
        
        # Main layout (Horizontal)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(14)

        # 1. Icon on the left
        self.icon_label = QLabel()
        self.icon_label.setObjectName("folderIcon")
        self.icon_label.setFixedSize(48, 48) # Fixed size to ensure alignment
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)

        # 2. Left side stack: Title on top, Metadata Row below
        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(4)
        
        self.name_label = QLabel(Path(folder_path).name or folder_path)
        self.name_label.setObjectName("folderName")
        details_layout.addWidget(self.name_label)

        # NEW: Horizontal layout for Path + Stats
        meta_row_layout = QHBoxLayout()
        meta_row_layout.setSpacing(8) # Space between path pill and count pills
        meta_row_layout.setContentsMargins(0, 0, 0, 0)

        # Absolute Path Pill
        self.path_pill = QFrame()
        self.path_pill.setObjectName("pathPill")
        path_pill_layout = QHBoxLayout(self.path_pill)
        path_pill_layout.setContentsMargins(10, 0, 10, 0)
        
        self.path_label = QLabel(folder_path if self._folder_exists else "Folder not found")
        self.path_label.setObjectName("folderPath")
        path_pill_layout.addWidget(self.path_label)
        
        meta_row_layout.addWidget(self.path_pill)

        # Stats Row (Now part of the same horizontal row)
        self.stats_container = QWidget()
        self.stats_container.setObjectName("statsContainer")
        self.stats_layout = QHBoxLayout(self.stats_container)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        self.stats_layout.setSpacing(6)
        
        meta_row_layout.addWidget(self.stats_container)
        meta_row_layout.addStretch() # Pushes everything to the left

        details_layout.addLayout(meta_row_layout)
        
        layout.addLayout(details_layout)
        layout.addStretch()

        # Remove button
        self.remove_btn = QPushButton()
        self.remove_btn.setIcon(get_icon("TRASH"))
        self.remove_btn.setIconSize(QSize(20, 20))
        self.remove_btn.setFixedSize(32, 32)
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.hide()
        self.remove_btn.setObjectName("removeBtn")
        self.remove_btn.clicked.connect(self._on_remove_clicked)  # Connect the signal!
        layout.addWidget(self.remove_btn)

        self.setCursor(Qt.PointingHandCursor)
        self._apply_style()
        self._update_icon()

    def sizeHint(self):
        return QSize(super().sizeHint().width(), 80)

    def _update_icon(self):
        """Update icon based on existence and size."""
        # Folder icon scales to match combined height of text stack
        size = 48
        icon_name = "FOLDER" if self._folder_exists else "WARNING"
        color = "orange" if not self._folder_exists else None
        self.icon_label.setPixmap(get_pixmap(icon_name, size=size, color_override=color))

    def attach(self, list_widget: QListWidget, list_item: QListWidgetItem):
        self._list_widget = list_widget
        self._list_item = list_item

    def _on_remove_clicked(self):
        self.remove_requested.emit(self.folder_path)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._apply_style()

    def set_remove_mode(self, enabled: bool):
        self._remove_mode = enabled
        if enabled:
            self.remove_btn.show()
        else:
            self.remove_btn.hide()
        self._apply_style()
        
        # Force layout update
        if self._list_item and self._list_widget:
            self.adjustSize()
            self._list_item.setSizeHint(self.sizeHint())
            # Use a timer to force a redraw if immediate update fails
            QTimer.singleShot(0, self._list_widget.doItemsLayout)

    def _apply_style(self):
        # Get current theme colors
        from app.themes import get_color_scheme
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)
        
        # Default state
        base_color = scheme.card_bg
        border_color = scheme.card_border
        text_primary = scheme.text_primary
        text_secondary = scheme.text_secondary
        accent = scheme.accent_color
        
        # Warning state for missing folders
        if not self._folder_exists:
            border_color = scheme.warning_color
            text_secondary = scheme.warning_color
        
        if self._selected:
            base_color = scheme.bg_tertiary
            border_color = accent
        
        style = f"""
            /* The main card background */
            QFrame#folderCard {{
                background-color: {base_color};
                border: 1px solid {border_color};
                border-radius: 10px;
            }}

            QFrame#folderCard:hover {{
                background-color: {scheme.bg_tertiary if not self._selected else scheme.bg_tertiary};
                border-color: {scheme.accent_color if not self._selected else scheme.accent_color};
            }}

            /* KILL ALL NESTED BACKGROUNDS to prevent boxed artifacts */
            QWidget, QFrame {{
                background: transparent;
                border: none;
            }}

            QLabel#folderName {{ 
                color: {text_primary}; 
                font-weight: 700; 
                font-size: 15px; 
            }}
            
            /* ONLY the pills get a background */
            QFrame#pathPill, QFrame.statPill {{
                background-color: rgba(255, 255, 255, 0.06);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                min-height: 24px;
                max-height: 24px;
            }}
            
            QLabel#folderPath, QLabel.statText {{ 
                color: {text_secondary}; 
                font-size: 10px; 
                font-weight: 500;
                padding: 0 4px;
            }}

            /* Ensure the folder icon has no box */
            QLabel#folderIcon {{
                background: transparent;
            }}

            QPushButton#removeBtn {{
                background-color: transparent;
                border: none;
            }}
            QPushButton#removeBtn:hover {{
                background-color: rgba(255, 68, 68, 0.15);
                border-radius: 14px;
            }}
        """
        self.setStyleSheet(style)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton and self._list_widget and self._list_item:
            self._list_widget.setCurrentItem(self._list_item)
            self._list_widget.itemClicked.emit(self._list_item)

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        if event.button() == Qt.LeftButton and self._list_widget and self._list_item:
            self._list_widget.setCurrentItem(self._list_item)
            self._list_widget.itemDoubleClicked.emit(self._list_item)
    
    def update_stats(self, file_count: int, language_count: int, session_count: int):
        """Update the statistics display for this folder."""
        # Clear existing items
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not self._folder_exists:
            return
            
        def add_stat(icon_name, text):
            pill = QFrame()
            pill.setProperty("class", "statPill")
            pill_layout = QHBoxLayout(pill)
            pill_layout.setContentsMargins(10, 0, 10, 0)
            pill_layout.setSpacing(6)
            pill_layout.setAlignment(Qt.AlignCenter)
            
            icon = QLabel()
            icon.setObjectName("pillIcon")
            icon.setPixmap(get_pixmap(icon_name, size=12))
            pill_layout.addWidget(icon)
            
            lbl = QLabel(text)
            lbl.setProperty("class", "statText")
            pill_layout.addWidget(lbl)
            
            self.stats_layout.addWidget(pill)

        if file_count > 0:
            add_stat("FILES", f"{file_count} files")
            
        if language_count > 0:
            add_stat("CODE", f"{language_count} languages")
            
        if session_count > 0:
            add_stat("TYPING", f"{session_count} sessions")
            
        self.stats_layout.addStretch()
        
        # Critical: Update size hints after content changes in lazy-loaded/dynamic widgets
        QTimer.singleShot(0, self._force_update_size)

    def _force_update_size(self):
        """Force list widget to recognize new height requirements."""
        try:
            if self._list_item and self._list_widget:
                self.adjustSize()
                self._list_item.setSizeHint(self.sizeHint())
                self._list_widget.updateGeometries()
        except RuntimeError:
            # Widget might have been deleted (e.g. list cleared) before timer fired
            pass
    
    def folder_exists(self) -> bool:
        """Check if the folder path exists."""
        return self._folder_exists


class FoldersTab(QWidget):
    def __init__(self, parent=None):
        if DEBUG_STARTUP_TIMING:
            import time
            t_start = time.time()
        
        super().__init__(parent)
        self.s = None
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(12)
        self.layout.setContentsMargins(16, 16, 16, 16)

        # Modern header section
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        
        from app.themes import get_color_scheme
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)
        
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(8)
        header_layout.setContentsMargins(0, 0, 0, 12)
        
        # Title Container
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(10)
        
        icon_label = QLabel()
        icon_label.setPixmap(get_pixmap("FOLDER", size=32))
        
        self.title_label = QLabel("Folders")
        self.title_label.setObjectName("folderTabTitle")
        self.title_label.setStyleSheet("font-size: 18pt; font-weight: bold;")
        
        title_layout.addWidget(icon_label)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        
        header_layout.addWidget(title_container)
        
        self.desc_label = QLabel("Add folders containing code files you want to practice typing.")
        self.desc_label.setObjectName("folderTabDesc")
        self.desc_label.setStyleSheet(f"color: {scheme.text_secondary}; font-size: 10pt;")
        header_layout.addWidget(self.desc_label)
        
        self.layout.addWidget(header)
        if DEBUG_STARTUP_TIMING:
            print(f"    [FoldersTab] Header setup: {time.time() - t:.3f}s")

        # Modern toolbar with styled buttons
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        
        # Get theme colors for buttons
        from app.themes import get_color_scheme
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)
        
        self.add_btn = QPushButton("Add Folder")
        self.add_btn.setIcon(get_icon("PLUS"))
        self.add_btn.setIconSize(QSize(16, 16))
        self.add_btn.setToolTip("Add a new folder")
        self.add_btn.setMinimumHeight(36)
        # Soft green
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                text-align: left;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
        """)
        
        self.edit_btn = QPushButton("Remove Folder")
        self.edit_btn.setIcon(get_icon("TRASH"))
        self.edit_btn.setIconSize(QSize(16, 16))
        self.edit_btn.setCheckable(True)
        self.edit_btn.setMinimumHeight(36)
        # Bright red
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                text-align: left;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff0000;
            }
            QPushButton:checked {
                background-color: #ff0000;
                border: 3px solid #ffeb3b;
            }
        """)
        
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addStretch()

        self.layout.addLayout(toolbar)

        # Styled list widget
        self.list = QListWidget()
        self.list.setFrameShape(QFrame.NoFrame)
        self.list.setSpacing(6)
        self.list.setSelectionMode(QListWidget.SingleSelection)
        self.list.setAttribute(Qt.WA_MacShowFocusRect, False) # Hide Mac focus rect if on Mac
        self.list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                padding: 4px 0;
                outline: none;
            }
            QListWidget::item {
                margin: 0;
                padding: 0;
                background: transparent;
                outline: none;
            }
            QListWidget::item:selected {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item:focus {
                outline: none;
            }
        """)
        self.layout.addWidget(self.list)
        
        # Connect selection signal
        self.list.currentItemChanged.connect(self._on_selection_changed)
        
        # Loading indicator (hidden by default)
        self.loading_label = QLabel("Scanning folders...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #888888; font-size: 12pt; padding: 20px;")
        self.loading_label.hide()
        self.layout.addWidget(self.loading_label)

        self.add_btn.clicked.connect(self.on_add)
        self.edit_btn.toggled.connect(self.on_edit_toggled)
        self.list.itemDoubleClicked.connect(self.on_folder_double_clicked)

        if DEBUG_STARTUP_TIMING:
            t = time.time()
        self.load_folders()
        if DEBUG_STARTUP_TIMING:
            print(f"    [FoldersTab] load_folders(): {time.time() - t:.3f}s")
            print(f"    [FoldersTab] TOTAL: {time.time() - t_start:.3f}s")

    def _on_selection_changed(self, current, previous):
        """Update selected state of folder cards."""
        if previous:
            widget = self.list.itemWidget(previous)
            if isinstance(widget, FolderCardWidget):
                widget.set_selected(False)
        if current:
            widget = self.list.itemWidget(current)
            if isinstance(widget, FolderCardWidget):
                widget.set_selected(True)

    def on_folder_double_clicked(self, item: QListWidgetItem):
        """Navigate to typing tab when folder is double-clicked."""
        if self.edit_btn.isChecked():
            return  # Don't navigate in edit mode
        folder_path = item.data(Qt.UserRole)
        
        # Explicitly unselect the widget immediately
        widget = self.list.itemWidget(item)
        if isinstance(widget, FolderCardWidget):
            widget.set_selected(False)
            
        # Clear selection and focus so it doesn't look "stuck" (like hover) when returning
        self.list.clearSelection()
        self.list.setCurrentItem(None) # Ensure current item anchor is also cleared
        self.list.clearFocus()
        
        # Signal parent window to switch to typing tab with this folder
        parent_window = self.window()
        if hasattr(parent_window, 'open_typing_tab'):
            parent_window.open_typing_tab(folder_path)

    def load_folders(self):
        """Load folders using custom FolderCardWidget."""
        if DEBUG_STARTUP_TIMING:
            import time
            t0 = time.time()
        
        self.list.clear()
        
        folders = settings.get_folders()
        is_remove_mode = hasattr(self, 'edit_btn') and self.edit_btn.isChecked()
        
        # Collect folder stats from file scanner and session history
        from app.file_scanner import scan_folders as scan_folder_files
        from app import stats_db
        
        for i, path_str in enumerate(folders):
            # Create widget
            card = FolderCardWidget(path_str)
            card.set_remove_mode(is_remove_mode)
            card.remove_requested.connect(self._maybe_remove_item)
            
            # Create list item
            item = QListWidgetItem(self.list)
            item.setData(Qt.UserRole, path_str)
            
            # Attach widget to item
            card.attach(self.list, item)
            self.list.setItemWidget(item, card)
            
            # Compute stats if folder exists
            if card.folder_exists():
                try:
                    # Scan for files (quick since already cached in most cases)
                    language_files = scan_folder_files([path_str])
                    file_count = sum(len(files) for files in language_files.values())
                    language_count = len(language_files)
                    
                    # Count sessions for files in this folder
                    session_count = 0
                    try:
                        all_sessions = stats_db.fetch_session_history(limit=10000)
                        for session in all_sessions:
                            if session.get('file_path', '').startswith(path_str):
                                session_count += 1
                    except Exception:
                        pass
                    
                    card.update_stats(file_count, language_count, session_count)
                except Exception:
                    card.update_stats(0, 0, 0)
            else:
                # Still call update_stats to finalize layout
                card.update_stats(0, 0, 0)

            # Important: Update size hint after dynamic content is added
            card.adjustSize()
            item.setSizeHint(card.sizeHint())

        self.list.updateGeometries()

        if DEBUG_STARTUP_TIMING:
            t3 = time.time()
            print(f"      [FOLDERS] TOTAL load_folders(): {t3-t0:.3f}s")

    def on_add(self):
        dlg = QFileDialog(self, "Select folder to add")
        dlg.setFileMode(QFileDialog.Directory)
        dlg.setOption(QFileDialog.ShowDirsOnly, True)
        if dlg.exec():
            selected = dlg.selectedFiles()
            
            # Show loading indicator
            self.loading_label.setText(f"Scanning {len(selected)} folder(s)...")
            self.loading_label.show()
            self.list.hide()
            QApplication.processEvents()  # Force UI update
            
            for p in selected:
                settings.add_folder(p)
            
            # Reload folders (this will update stats)
            self.load_folders()
            
            # Hide loading indicator
            self.loading_label.hide()
            self.list.show()
        
        # Notify parent to refresh languages tab
        parent_window = self.window()
        if hasattr(parent_window, 'refresh_languages_tab'):
            parent_window.refresh_languages_tab()

    def on_edit_toggled(self, checked: bool):
        """Toggle remove mode for folders."""
        # Text remains "Remove Folder" even when checked
        
        # Update all widgets
        for i in range(self.list.count()):
            item = self.list.item(i)
            widget = self.list.itemWidget(item)
            if isinstance(widget, FolderCardWidget):
                widget.set_remove_mode(checked)

    def _maybe_remove_item(self, folder_path: str):
        """Handle folder removal with optional confirmation."""
        delete_confirm = settings.get_setting("delete_confirm", settings.get_default("delete_confirm"))
        should_confirm = (delete_confirm == "1")
        
        should_remove = True
        if should_confirm:
            # Custom styled dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Confirm Removal")
            dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            dialog.setAttribute(Qt.WA_TranslucentBackground)
            
            # Get theme colors
            from app.themes import get_color_scheme
            scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
            scheme = get_color_scheme("dark", scheme_name)
            
            # Layout
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # Main container
            container = QFrame()
            container.setObjectName("dialogContainer")
            container.setStyleSheet(f"""
                QFrame#dialogContainer {{
                    background-color: {scheme.bg_secondary};
                    border: 1px solid {scheme.border_color};
                    border-radius: 16px;
                }}
                QLabel {{ color: {scheme.text_primary}; }}
                QCheckBox {{ color: {scheme.text_primary}; }}
            """)
            layout.addWidget(container)
            
            c_layout = QVBoxLayout(container)
            c_layout.setSpacing(0)
            # Add 1px margin so the container border is visible
            c_layout.setContentsMargins(1, 1, 1, 1)
            
            # Header
            header = QFrame()
            header.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5e81ac, stop:1 #81a1c1);
                border-top-left-radius: 15px;
                border-top-right-radius: 15px;
                padding: 20px;
            """)
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(12)
            
            header_icon = QLabel()
            header_icon.setPixmap(get_pixmap("TRASH", size=24, color_override="white"))
            header_icon.setStyleSheet("background: transparent;")
            header_layout.addWidget(header_icon)
            
            header_title = QLabel("Remove Folder?")
            header_title.setStyleSheet("font-size: 20px; font-weight: bold; color: white; background: transparent;")
            header_layout.addWidget(header_title)
            header_layout.addStretch()
            
            c_layout.addWidget(header)
            
            # Content Body
            body = QWidget()
            # Add bottom radius to match container
            body.setStyleSheet("border-bottom-left-radius: 15px; border-bottom-right-radius: 15px; background-color: transparent;")
            body_layout = QVBoxLayout(body)
            body_layout.setContentsMargins(24, 24, 24, 24)
            body_layout.setSpacing(16)
            
            # Question
            msg = QLabel("Are you sure you want to remove this folder from the app?")
            msg.setWordWrap(True)
            msg.setStyleSheet(f"font-size: 15px; color: {scheme.text_primary};")
            body_layout.addWidget(msg)
            
            # Folder Path Box
            path_box = QFrame()
            path_box.setStyleSheet(f"""
                background-color: {scheme.bg_tertiary};
                border-radius: 8px;
                padding: 12px;
            """)
            path_layout = QHBoxLayout(path_box)
            path_layout.setContentsMargins(0, 0, 0, 0)
            path_layout.setSpacing(10)
            
            folder_icon = QLabel()
            folder_icon.setPixmap(get_pixmap("FOLDER", size=18))
            folder_icon.setStyleSheet("background: transparent;")
            path_layout.addWidget(folder_icon)
            
            
            path_text = QLabel(folder_path)
            path_text.setStyleSheet(f"font-family: monospace; font-size: 13px; color: {scheme.text_primary}; background: transparent;")
            path_text.setWordWrap(True)
            path_layout.addWidget(path_text, 1)
            
            body_layout.addWidget(path_box)
            
            # Info Text
            info = QLabel("This action only removes the folder from the application; the actual folder remains on your computer.")
            info.setWordWrap(True)
            info.setStyleSheet(f"color: {scheme.text_secondary}; font-size: 12px;")
            body_layout.addWidget(info)
            
            # Checkbox
            cb = QCheckBox("Don't ask me again")
            cb.setCursor(Qt.PointingHandCursor)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    spacing: 8px;
                    font-size: 14px;
                    color: {scheme.text_primary};
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border-radius: 4px;
                    border: 2px solid {scheme.border_color};
                    background-color: transparent;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #4a90e2;
                    border-color: #4a90e2;
                    image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='20 6 9 17 4 12'/%3E%3C/svg%3E");
                }}
            """)
            body_layout.addWidget(cb)
            
            # Buttons
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(12)
            btn_layout.addStretch()
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setCursor(Qt.PointingHandCursor)
            cancel_btn.setMinimumHeight(36)
            cancel_btn.setMinimumWidth(100)
            cancel_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {scheme.bg_tertiary};
                    color: {scheme.text_primary};
                    border: none;
                    border-radius: 18px;
                    font-weight: bold;
                    font-size: 14px;
                }}
                QPushButton:hover {{ background-color: {scheme.border_color}; }}
            """)
            cancel_btn.clicked.connect(dialog.reject)
            
            remove_btn = QPushButton("Remove")
            remove_btn.setIcon(get_icon("TRASH"))
            remove_btn.setCursor(Qt.PointingHandCursor)
            remove_btn.setMinimumHeight(36)
            remove_btn.setMinimumWidth(100)
            remove_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff4444;
                    color: white;
                    border: none;
                    border-radius: 18px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover { background-color: #ff0000; }
            """)
            remove_btn.clicked.connect(dialog.accept)
            
            btn_layout.addWidget(cancel_btn)
            btn_layout.addWidget(remove_btn)
            body_layout.addLayout(btn_layout)
            
            c_layout.addWidget(body)
            
            if dialog.exec() == QDialog.Accepted:
                if cb.isChecked():
                    settings.set_setting("delete_confirm", "0")
                    # Notify main window to update settings UI
                    parent_window = self.window()
                    if hasattr(parent_window, 'refresh_settings_ui'):
                        parent_window.refresh_settings_ui()
                should_remove = True
            else:
                should_remove = False
        
        if should_remove:
            # Remove the folder
            settings.remove_folder(folder_path)
            
            # Immediately update the UI
            self.load_folders()
            
            # Notify parent to refresh languages tab
            parent_window = self.window()
            if hasattr(parent_window, 'refresh_languages_tab'):
                parent_window.refresh_languages_tab()

    def on_view_toggled(self, checked: bool):
        pass

    def _update_folder_selection_state(self):
        pass

    def _set_remove_mode_for_cards(self, enabled: bool):
        pass

    def _apply_view_mode_to_cards(self, compact: bool):
        pass

    def _apply_view_mode_styles(self):
        pass

    def _first_card_size(self) -> Optional[QSize]:
        if not self.list.count():
            return None
        widget = self.list.itemWidget(self.list.item(0))
        return widget.sizeHint() if widget else None

    def apply_theme(self):
        """Apply current theme to FoldersTab and all its children."""
        from app.themes import get_color_scheme
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)
        
        # Update header labels
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"font-size: 18pt; font-weight: bold; color: {scheme.text_primary};")
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"color: {scheme.text_secondary}; font-size: 10pt;")
        
        # Update list widget styling to maintain clean look
        self.list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                padding: 4px 0;
                outline: none;
            }
            QListWidget::item {
                margin: 0;
                padding: 0;
                background: transparent;
                outline: none;
            }
            QListWidget::item:selected {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item:focus {
                outline: none;
            }
        """)

        # Update toolbar buttons
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {scheme.success_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                text-align: left;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {scheme.success_color};
                opacity: 0.8;
            }}
        """)
        
        self.edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {scheme.error_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                text-align: left;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {scheme.error_color};
                opacity: 0.8;
            }}
            QPushButton:checked {{
                background-color: {scheme.error_color};
                border: 3px solid {scheme.accent_color};
            }}
        """)
        
        # Update FolderCardWidgets
        for i in range(self.list.count()):
            item = self.list.item(i)
            widget = self.list.itemWidget(item)
            if isinstance(widget, FolderCardWidget):
                widget._apply_style()
                widget._update_icon()


class MainWindow(QMainWindow):
    # Signals for dynamic settings updates
    font_changed = Signal(str, int, bool)  # family, size, ligatures
    colors_changed = Signal()
    cursor_changed = Signal(str, str)  # type, style
    space_char_changed = Signal(str)
    tab_width_changed = Signal(int)
    pause_delay_changed = Signal(float)
    allow_continue_changed = Signal(bool)
    show_typed_changed = Signal(bool)
    show_ghost_text_changed = Signal(bool)
    sound_enabled_changed = Signal(bool)
    instant_death_changed = Signal(bool)
    ignored_patterns_changed = Signal()
    progress_bar_pos_changed = Signal(str)
    stats_display_pos_changed = Signal(str)
    auto_indent_changed = Signal(bool)
    
    def __init__(self):
        if DEBUG_STARTUP_TIMING:
            import time
            t_init_start = time.time()
        
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        super().__init__()
        if DEBUG_STARTUP_TIMING:
            print(f"  [INIT] QMainWindow.__init__: {time.time() - t:.3f}s")
        
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        settings.init_db()
        if DEBUG_STARTUP_TIMING:
            print(f"  [INIT] DB initialization: {time.time() - t:.3f}s")
        
        # Initialize sound manager
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        from app.sound_manager import get_sound_manager
        sound_mgr = get_sound_manager()
        sound_enabled = settings.get_setting("sound_enabled", settings.get_default("sound_enabled")) == "1"
        sound_profile = settings.get_setting("sound_profile", settings.get_default("sound_profile"))
        sound_volume = int(settings.get_setting("sound_volume", settings.get_default("sound_volume"))) / 100.0
        sound_mgr.set_enabled(sound_enabled)
        sound_mgr.set_profile(sound_profile)
        sound_mgr.set_volume(sound_volume)
        if DEBUG_STARTUP_TIMING:
            print(f"  [INIT] Sound manager: {time.time() - t:.3f}s")
        
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        self.setWindowTitle("Dev Typing App")
        
        # Set application icon
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.resize(1000, 700)
        
        # --- Root Layout Strategy for Layers ---
        self.central_widget_container = QWidget()
        self.setCentralWidget(self.central_widget_container)
        
        self.stack_layout = QStackedLayout(self.central_widget_container)
        self.stack_layout.setStackingMode(QStackedLayout.StackAll)
        
        # Layer 1: Content Container (will be blurred)
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # Setup Blur Effect (Attached to PROXY, not content)
        self.blur_effect = QGraphicsBlurEffect()
        self.blur_effect.setBlurRadius(0) 
        
        self.stack_layout.addWidget(self.content_container)
        
        # Layer 2: Proxy Label for High-Fidelity Blur Transition
        self.proxy_label = QLabel()
        self.proxy_label.setScaledContents(True) # In case of slight resize
        self.proxy_label.setGraphicsEffect(self.blur_effect) # Apply blur here
        self.proxy_label.hide()
        self.stack_layout.addWidget(self.proxy_label)
        
        # Setup Tabs (add to content layer)
        self.tabs = QTabWidget()
        self.tabs.tabBar().setIconSize(QSize(18, 18))
        self.content_layout.addWidget(self.tabs)
        
        # Layer 3: Transition Overlay (sits on top)
        self.transition_overlay = ProfileTransitionOverlay(self)
        self.stack_layout.addWidget(self.transition_overlay)
        
        # Profile Trigger (Top Right)
        self.pm = get_profile_manager()
        curr_profile = self.pm.get_active_profile()
        # Find image path for current profile
        all_profiles = self.pm.get_all_profiles()
        p_data = next((p for p in all_profiles if p["name"] == curr_profile), None)
        img_path = p_data["image"] if p_data else None
        
        self.profile_trigger = ProfileTrigger(curr_profile, img_path)
        self.profile_trigger.clicked.connect(self.open_profile_manager)
        
        # Wrap in container to add right margin
        trigger_container = QWidget()
        # Transparent background ensures no rectangular box appears around the pill
        trigger_container.setStyleSheet("background: transparent; border: none;")

        trigger_layout = QHBoxLayout(trigger_container)

        # VERTICAL CENTERING:
        # Margin format: (Left, Top, Right, Bottom)
        # Tab bar is ~40px high, button is now 36px
        # (40-36)/2 = 2px for perfect centering
        # We keep 12px on Right to avoid the window edge.
        trigger_layout.setContentsMargins(0, 2, 12, 2) 
        trigger_layout.setSpacing(0)
        trigger_layout.setAlignment(Qt.AlignVCenter) # Vertical centering

        trigger_layout.addWidget(self.profile_trigger)
        trigger_layout.setSizeConstraint(QLayout.SetFixedSize)

        self.tabs.setCornerWidget(trigger_container, Qt.TopRightCorner)
        trigger_container.setAttribute(Qt.WA_TransparentForMouseEvents, False) # Ensure container doesn't block

        # Connect Profile Signals
        self.pm.profile_updated.connect(self._on_profile_updated)
        self.pm.profile_switched.connect(self.switch_profile)
    
    # Tabs
        if DEBUG_STARTUP_TIMING:
            print(f"  [INIT] Window setup + QTabWidget: {time.time() - t:.3f}s")
        
        # --- Folders Tab (Immediate) ---
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        self.folders_tab = FoldersTab()
        if DEBUG_STARTUP_TIMING:
            t_add = time.time()
            print(f"  [INIT] FoldersTab: {t_add - t:.3f}s")
        self.tabs.addTab(self.folders_tab, get_icon("FOLDER"), "Folders")
        
        # --- Languages Tab (Immediate) ---
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        self.languages_tab = LanguagesTab()
        if DEBUG_STARTUP_TIMING:
            t_add = time.time()
            print(f"  [INIT] LanguagesTab: {t_add - t:.3f}s")
        self.tabs.addTab(self.languages_tab, get_icon("CODE"), "Languages")

        # --- History Tab (Lazy) ---
        self.history_tab = QLabel("Loading History...")
        self.history_tab.setAlignment(Qt.AlignCenter)
        self.history_tab.setStyleSheet("color: #888888; font-size: 14pt;")
        self.tabs.addTab(self.history_tab, get_icon("CLOCK"), "History")
        
        # --- Stats Tab (Lazy) ---
        self.stats_tab = QLabel("Loading Stats...")
        self.stats_tab.setAlignment(Qt.AlignCenter)
        self.stats_tab.setStyleSheet("color: #888888; font-size: 14pt;")
        self.tabs.addTab(self.stats_tab, get_icon("CHART"), "Stats")
        
        # --- Editor/Typing Tab (Lazy) ---
        # EditorTab is lightweight in init, but we want to defer its 'ensure_loaded'
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        self.editor_tab = EditorTab()
        if DEBUG_STARTUP_TIMING:
            t_add = time.time()
            print(f"  [INIT] EditorTab (init only): {t_add - t:.3f}s")
        self.tabs.addTab(self.editor_tab, get_icon("TYPING"), "Typing")

        # --- Shortcuts Tab (Immediate) ---
        self.shortcuts_tab = ShortcutsTab()
        self.tabs.addTab(self.shortcuts_tab, get_icon("KEYBOARD"), "Shortcuts")

        # --- Settings Tab (Lazy) ---
        self.settings_tab = QLabel("Loading Settings...")
        self.settings_tab.setAlignment(Qt.AlignCenter)
        self.settings_tab.setStyleSheet("color: #888888; font-size: 14pt;")
        self.tabs.addTab(self.settings_tab, get_icon("SETTINGS"), "Settings")

        if DEBUG_STARTUP_TIMING:
            t = time.time()
        # self.setCentralWidget(self.tabs) # Already added to content_layout earlier
        self._last_tab_index = self.tabs.currentIndex()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        if DEBUG_STARTUP_TIMING:
            print(f"  [INIT] setCentralWidget + signals: {time.time() - t:.3f}s")
        
        # Connect settings signals to editor tab for dynamic updates
        # (We can connect these now because editor_tab instance exists, even if not fully loaded)
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        self._connect_settings_signals()
        if DEBUG_STARTUP_TIMING:
            print(f"  [INIT] Connect signals: {time.time() - t:.3f}s")
        
        # Connect profile manager signals
        self.pm.profile_updated.connect(self._on_profile_updated)
        
        # Load custom fonts
        self._load_custom_fonts()
        
        # Emit initial settings to apply them to the typing area
        # (This might need to be re-emitted when editor loads, but safe to do now)
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        self._emit_initial_settings()
        if DEBUG_STARTUP_TIMING:
            print(f"  [INIT] Emit settings: {time.time() - t:.3f}s")

        # Trigger background loading sequence
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        # Start loading other tabs after a brief delay to let the UI show up
        QTimer.singleShot(100, self._start_background_loading)
        
        if DEBUG_STARTUP_TIMING:
            print(f"  [INIT] QTimer.singleShot (background load): {time.time() - t:.3f}s")
            print(f"  [INIT] === TOTAL MainWindow.__init__: {time.time() - t_init_start:.3f}s ===")

    def _start_background_loading(self):
        """Start the chain of background tab loading."""
        # 1. Load Languages data (scan) - was previously done separately
        self.languages_tab.ensure_loaded()
        
        # 2. Schedule next step: History Tab
        QTimer.singleShot(50, self._load_history_tab_lazy)

    def _load_history_tab_lazy(self):
        """Lazy load history tab."""
        if isinstance(self.history_tab, QLabel):
            real_history = HistoryTab()
            self._replace_tab(self.history_tab, real_history, "History")
            self.history_tab = real_history
        
        # 3. Schedule next step: Stats Tab
        QTimer.singleShot(50, self._load_stats_tab_lazy)
    
    def _load_stats_tab_lazy(self):
        """Lazy load stats tab."""
        if isinstance(self.stats_tab, QLabel):
            real_stats = StatsTab()
            self._replace_tab(self.stats_tab, real_stats, "Stats")
            self.stats_tab = real_stats
        
        # 4. Schedule next step: Editor Tab content
        QTimer.singleShot(50, self._load_editor_tab_lazy)

    def _load_editor_tab_lazy(self):
        """Lazy load editor tab content."""
        self.editor_tab.ensure_loaded()
        
        # Connect signals now that typing_area exists
        self._connect_settings_signals()
        
        # 5. Schedule next step: Settings Tab
        QTimer.singleShot(50, self._load_settings_tab_lazy)

    def _load_settings_tab_lazy(self):
        """Lazy load settings tab."""
        if isinstance(self.settings_tab, QLabel):
            real_settings = self._create_settings_tab()
            self._replace_tab(self.settings_tab, real_settings, "Settings")
            self.settings_tab = real_settings
            
            # Force Qt to process pending events
            QApplication.processEvents()
            
            if hasattr(self, 'scheme_combo'):
                self.scheme_combo.setFocusPolicy(Qt.StrongFocus)
                self.scheme_combo.style().polish(self.scheme_combo)
                self.scheme_combo.setFocusPolicy(Qt.StrongFocus)
                self.scheme_combo.style().polish(self.scheme_combo)
            
            # Re-emit settings to ensure all UI elements are synced
            self._emit_initial_settings()

    def _replace_tab(self, old_widget, new_widget, label):
        """Helper to replace a tab widget in-place."""
        index = self.tabs.indexOf(old_widget)
        if index != -1:
            is_current = (self.tabs.currentIndex() == index)
            icon = self.tabs.tabIcon(index)
            self.tabs.removeTab(index)
            self.tabs.insertTab(index, new_widget, icon, label)
            if is_current:
                self.tabs.setCurrentIndex(index)
            old_widget.deleteLater()

    def _on_tab_changed(self, index: int):
        """Handle tab change logic, including unsaved changes warnings."""
        # Check if we are LEAVING settings tab with unsaved color changes
        if (hasattr(self, 'settings_tab') and not isinstance(self.settings_tab, QLabel)):
            settings_index = self.tabs.indexOf(self.settings_tab)
            if (hasattr(self, '_colors_dirty') and self._colors_dirty and 
                self._last_tab_index == settings_index and index != settings_index):
                
                scheme_name = settings.get_setting("dark_scheme", "dracula")
                reply = QMessageBox.question(
                    self, "Unsaved Changes",
                    f"You have unsaved color changes for theme '{scheme_name}'.\n\nDo you want to save them?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
                )
                
                if reply == QMessageBox.Save:
                    self.on_save_theme()
                elif reply == QMessageBox.Cancel:
                    # Block signals to prevent recursion and go back
                    self.tabs.blockSignals(True)
                    self.tabs.setCurrentIndex(settings_index)
                    self.tabs.blockSignals(False)
                    return # Important: skip updating _last_tab_index
                else: # Discard
                    self._colors_dirty = False
                    # Revert live preview
                    self.apply_current_theme()
                    self.update_color_buttons_from_theme()

        # Existing persistence logic for editor
        typing_index = self.tabs.indexOf(self.editor_tab)
        if typing_index != -1 and self._last_tab_index == typing_index and index != typing_index:
            self.editor_tab.save_active_progress()

        languages_index = self.tabs.indexOf(self.languages_tab)
        if index == languages_index and languages_index != -1:
            self.languages_tab.ensure_loaded()
            
        self._last_tab_index = index

    def keyPressEvent(self, event):
        """Handle global keyboard shortcuts."""
        modifiers = event.modifiers()
        key = event.key()
        
        # 1. Behavioral Global Shortcuts (Work everywhere)
        if (modifiers & Qt.ControlModifier):
            if key == Qt.Key_L:
                # Toggle Lenient Mode
                current = settings.get_setting("allow_continue_mistakes", "0") == "1"
                self._handle_allow_continue_button(not current)
                event.accept()
                return
            elif key == Qt.Key_G:
                # Toggle Show Ghost Text
                current = settings.get_setting("show_ghost_text", "1") == "1"
                self._handle_show_ghost_text_button(not current)
                event.accept()
                return
            elif key == Qt.Key_M:
                # Toggle Sound/Mute
                current = settings.get_setting("sound_enabled", "1") == "1"
                self._handle_sound_enabled_button(not current)
                self.sound_enabled_changed.emit(not current)
                event.accept()
                return
            elif key == Qt.Key_S:
                # Toggle Show What You Type
                current = settings.get_setting("show_typed_characters", "0") == "1"
                self._handle_show_typed_button(not current)
                event.accept()
                return
            elif key == Qt.Key_D:
                # Toggle Instant Death
                current = settings.get_setting("instant_death_mode", "0") == "1"
                self._handle_instant_death_button(not current)
                event.accept()
                return
            elif key == Qt.Key_I:
                # Toggle Auto Indent (Ctrl + I)
                current = settings.get_setting("auto_indent", "0") == "1"
                self._handle_auto_indent_button(not current)
                event.accept()
                return
            elif key == Qt.Key_T:
                # Cycle Themes
                self._cycle_themes()
                event.accept()
                return
            elif (modifiers & Qt.ShiftModifier) and key == Qt.Key_P:
                # Switch Profile
                self.open_profile_manager()
                event.accept()
                return

        # 2. Layout & Tab Navigation (Global)
        if (modifiers & Qt.AltModifier) and not (modifiers & Qt.ControlModifier):
            # Alt + 1-7: Direct tab switching
            tab_index = -1
            if key == Qt.Key_1: tab_index = 0
            elif key == Qt.Key_2: tab_index = 1
            elif key == Qt.Key_3: tab_index = 2
            elif key == Qt.Key_4: tab_index = 3
            elif key == Qt.Key_5: tab_index = 4
            elif key == Qt.Key_6: tab_index = 5
            elif key == Qt.Key_7: tab_index = 6
            
            if tab_index != -1 and tab_index < self.tabs.count():
                self.tabs.setCurrentIndex(tab_index)
                event.accept()
                return

        # 3. Session-Specific Shortcuts (Typing Tab ONLY)
        if hasattr(self, 'editor_tab') and self.tabs.currentWidget() == self.editor_tab:
            # ESC: Reset
            if key == Qt.Key_Escape:
                if hasattr(self.editor_tab, 'on_reset_clicked'):
                    self.editor_tab.on_reset_clicked()
                event.accept()
                return

            # Ctrl actions
            if (modifiers & Qt.ControlModifier):
                if key == Qt.Key_P:
                    # Toggle Pause/Resume
                    if hasattr(self.editor_tab, 'toggle_pause'):
                        self.editor_tab.toggle_pause()
                    event.accept()
                    return
                elif key == Qt.Key_R:
                    # Random File
                    if hasattr(self.editor_tab, 'file_tree') and hasattr(self.editor_tab.file_tree, '_on_random_clicked'):
                        self.editor_tab.file_tree._on_random_clicked()
                    event.accept()
                    return
            
            # Alt actions
            if (modifiers & Qt.AltModifier):
                if key == Qt.Key_R:
                    # Start Race
                    if hasattr(self.editor_tab, 'on_ghost_clicked'):
                        self.editor_tab.on_ghost_clicked()
                    event.accept()
                    return

        super().keyPressEvent(event)

    def _cycle_themes(self):
        """Cycle through all available themes."""
        from app.themes import THEMES, _get_custom_themes
        
        # Get all available schemes
        scheme_names = list(THEMES.get("dark", {}).keys())
        customs = _get_custom_themes()
        if "dark" in customs:
            scheme_names.extend(list(customs["dark"].keys()))
        
        # Deduplicate and sort
        scheme_names = sorted(list(set(scheme_names)))
        if not scheme_names:
            return
            
        # Get current scheme
        current = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        
        # Find next index
        try:
            idx = scheme_names.index(current)
            next_idx = (idx + 1) % len(scheme_names)
        except ValueError:
            next_idx = 0
            
        next_scheme = scheme_names[next_idx]
        
        # Apply next theme
        settings.set_setting("dark_scheme", next_scheme)
        
        # Update combo box if it exists (is loaded)
        if hasattr(self, 'scheme_combo'):
            self.scheme_combo.blockSignals(True)
            idx = self.scheme_combo.findText(next_scheme)
            if idx >= 0:
                self.scheme_combo.setCurrentIndex(idx)
            self.scheme_combo.blockSignals(False)
            
        # Apply theme globally
        self.apply_current_theme()
        
        # Show a momentary notification (optional, but good for feedback)
        # self.statusBar().showMessage(f"Theme: {next_scheme}", 2000)

    def closeEvent(self, event):
        """Ensure active typing progress is saved before exit."""
        if hasattr(self, "editor_tab"):
            self.editor_tab.save_active_progress()
        super().closeEvent(event)

    def _create_settings_tab(self) -> QWidget:
        """Create and return the settings tab widget."""
        if DEBUG_STARTUP_TIMING:
            import time
            t_start = time.time()
        
        # Imports moved to top of file
        
        if DEBUG_STARTUP_TIMING:

            t = time.time()
            
        # Top-level container for search bar + scroll area
        container_widget = QWidget()
        container_layout = QVBoxLayout(container_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0) # Search bar sits flush or close

        # === Search Bar Setup ===
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(40, 10, 40, 5) # Match settings margins
        
        self.settings_search_input = QLineEdit()
        self.settings_search_input.setPlaceholderText("Search settings...")
        self.settings_search_input.setClearButtonEnabled(True)
        self.settings_search_input.setMinimumHeight(30)
        # Style similar to VS Code - a bit darker/prominent
        self.settings_search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: #252526;
                color: #cccccc;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #007fd4;
            }
        """)
        self.settings_search_input.textChanged.connect(self._filter_settings)
        
        search_layout.addWidget(self.settings_search_input)
        container_layout.addWidget(search_container)

        # Main scroll area for settings
        scroll = QScrollArea()
        self.settings_scroll_area = scroll # Save ref for scrolling logic
        self._settings_scroll_pos = 0 # Store previous scroll position
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame) # Remove border for cleaner integration
        
        container_layout.addWidget(scroll)

        
        settings_widget = QWidget()
        self.settings_scroll_widget = settings_widget # Save ref for search
        s_layout = QVBoxLayout(settings_widget)
        # Add padding to sides as requested
        s_layout.setContentsMargins(40, 10, 40, 10)
        
        if DEBUG_STARTUP_TIMING:
            print(f"    [SettingsTab] Basic setup: {time.time() - t:.3f}s")
        
        # General settings group
        general_group = QGroupBox("General")
        general_layout = QVBoxLayout()
        
        confirm_del_label = QLabel("Confirm Folder Deletion")
        confirm_del_label.setStyleSheet("font-weight: bold;")
        general_layout.addWidget(confirm_del_label)
        
        confirm_del_desc = QLabel("Ask for confirmation before removing a folder from the list.")
        confirm_del_desc.setWordWrap(True)
        confirm_del_desc.setStyleSheet("color: #888888; font-size: 10pt;")
        general_layout.addWidget(confirm_del_desc)
        
        confirm_del_row = QHBoxLayout()
        confirm_del_row.setSpacing(8)
        
        self.confirm_del_enabled_btn = QPushButton("Enabled")
        self.confirm_del_disabled_btn = QPushButton("Disabled")
        for btn in (self.confirm_del_enabled_btn, self.confirm_del_disabled_btn):
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            
        self.confirm_del_enabled_btn.clicked.connect(lambda: self._handle_confirm_del_button(True))
        self.confirm_del_disabled_btn.clicked.connect(lambda: self._handle_confirm_del_button(False))
        
        confirm_del_row.addWidget(self.confirm_del_enabled_btn)
        confirm_del_row.addWidget(self.confirm_del_disabled_btn)
        confirm_del_row.addStretch()
        general_layout.addLayout(confirm_del_row)
        
        confirm_del = settings.get_setting("delete_confirm", settings.get_default("delete_confirm")) == "1"
        self._update_confirm_del_buttons(confirm_del)
        
        general_group.setLayout(general_layout)
        s_layout.addWidget(general_group)

        # UI Layout settings group
        layout_group = QGroupBox("Interface Layout")
        layout_layout = QVBoxLayout()
        
        # Progress Bar Position
        pb_pos_label = QLabel("Progress Bar Position")
        pb_pos_label.setStyleSheet("font-weight: bold;")
        layout_layout.addWidget(pb_pos_label)
        
        pb_pos_row = QHBoxLayout()
        pb_pos_row.addWidget(QLabel("Location:"))
        self.pb_pos_combo = QComboBox()
        self.pb_pos_combo.addItem("Top", "top")
        self.pb_pos_combo.addItem("Bottom", "bottom")
        self.pb_pos_combo.setMinimumWidth(120)
        
        current_pb_pos = settings.get_setting("progress_bar_pos", settings.get_default("progress_bar_pos"))
        index = self.pb_pos_combo.findData(current_pb_pos)
        if index >= 0:
            self.pb_pos_combo.setCurrentIndex(index)
        
        self.pb_pos_combo.currentIndexChanged.connect(self._handle_pb_pos_changed)
        pb_pos_row.addWidget(self.pb_pos_combo)
        pb_pos_row.addStretch()
        layout_layout.addLayout(pb_pos_row)
        
        layout_layout.addSpacing(10)
        
        # Stats Display Position
        stats_pos_label = QLabel("Stats Display Position")
        stats_pos_label.setStyleSheet("font-weight: bold;")
        layout_layout.addWidget(stats_pos_label)
        
        stats_pos_row = QHBoxLayout()
        stats_pos_row.addWidget(QLabel("Location:"))
        self.stats_pos_combo = QComboBox()
        self.stats_pos_combo.addItem("Right Sidebar", "right")
        self.stats_pos_combo.addItem("Bottom Bar", "bottom")
        self.stats_pos_combo.setMinimumWidth(120)
        
        current_stats_pos = settings.get_setting("stats_display_pos", settings.get_default("stats_display_pos"))
        index = self.stats_pos_combo.findData(current_stats_pos)
        if index >= 0:
            self.stats_pos_combo.setCurrentIndex(index)
        
        self.stats_pos_combo.currentIndexChanged.connect(self._handle_stats_pos_changed)
        stats_pos_row.addWidget(self.stats_pos_combo)
        stats_pos_row.addStretch()
        layout_layout.addLayout(stats_pos_row)
        
        layout_group.setLayout(layout_layout)
        s_layout.addWidget(layout_group)

        # History Retention settings group
        history_group = QGroupBox("History Retention")
        history_layout = QVBoxLayout()
        
        retention_label = QLabel("Session History Retention")
        retention_label.setStyleSheet("font-weight: bold;")
        history_layout.addWidget(retention_label)
        
        retention_desc = QLabel(
            "Automatically clean up old session history to keep the database size manageable. "
            "Sessions older than the selected period will be deleted on app startup."
        )
        retention_desc.setWordWrap(True)
        retention_desc.setStyleSheet("color: #888888; font-size: 10pt;")
        history_layout.addWidget(retention_desc)
        
        retention_row = QHBoxLayout()
        retention_row.setSpacing(8)
        
        retention_row.addWidget(QLabel("Keep history for:"))
        
        self.retention_combo = QComboBox()
        self.retention_combo.addItem("30 days", "30")
        self.retention_combo.addItem("60 days", "60")
        self.retention_combo.addItem("90 days", "90")
        self.retention_combo.addItem("180 days", "180")
        self.retention_combo.addItem("1 year", "365")
        self.retention_combo.addItem("Forever", "0")
        self.retention_combo.setMinimumWidth(120)
        
        current_retention = settings.get_setting("history_retention_days", settings.get_default("history_retention_days"))
        index = self.retention_combo.findData(current_retention)
        if index >= 0:
            self.retention_combo.setCurrentIndex(index)
        
        self.retention_combo.currentIndexChanged.connect(self._handle_retention_changed)
        retention_row.addWidget(self.retention_combo)
        retention_row.addStretch()
        
        history_layout.addLayout(retention_row)
        
        history_group.setLayout(history_layout)
        s_layout.addWidget(history_group)

        # Typing Behavior settings group
        typing_behavior_group = QGroupBox("Typing Behavior")
        typing_behavior_layout = QVBoxLayout()
        
        lenient_label = QLabel("Lenient Mode")
        lenient_label.setStyleSheet("font-weight: bold;")
        typing_behavior_layout.addWidget(lenient_label)

        description = QLabel(
            "In lenient mode you can continue typing without fixing your mistypes."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #888888; font-size: 10pt;")
        typing_behavior_layout.addWidget(description)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self.allow_continue_enabled_btn = QPushButton("Enabled")
        self.allow_continue_disabled_btn = QPushButton("Disabled")
        for btn in (self.allow_continue_enabled_btn, self.allow_continue_disabled_btn):
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.setCursor(Qt.PointingHandCursor)

        self.allow_continue_enabled_btn.clicked.connect(lambda: self._handle_allow_continue_button(True))
        self.allow_continue_disabled_btn.clicked.connect(lambda: self._handle_allow_continue_button(False))

        button_row.addWidget(self.allow_continue_enabled_btn)
        button_row.addWidget(self.allow_continue_disabled_btn)
        button_row.addStretch()
        typing_behavior_layout.addLayout(button_row)

        allow_continue = settings.get_setting("allow_continue_mistakes", settings.get_default("allow_continue_mistakes")) == "1"
        self._update_allow_continue_buttons(allow_continue)

        # Show typed characters option
        show_typed_label = QLabel("Show what you type")
        show_typed_label.setStyleSheet("font-weight: bold;")
        typing_behavior_layout.addWidget(show_typed_label)

        show_typed_description = QLabel(
            "Display the characters you actually type instead of the reference text when mistakes happen."
        )
        show_typed_description.setWordWrap(True)
        show_typed_description.setStyleSheet("color: #888888; font-size: 9pt;")
        typing_behavior_layout.addWidget(show_typed_description)

        show_button_row = QHBoxLayout()
        show_button_row.setSpacing(8)

        self.show_typed_enabled_btn = QPushButton("Enabled")
        self.show_typed_disabled_btn = QPushButton("Disabled")
        for btn in (self.show_typed_enabled_btn, self.show_typed_disabled_btn):
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.setCursor(Qt.PointingHandCursor)

        self.show_typed_enabled_btn.clicked.connect(lambda: self._handle_show_typed_button(True))
        self.show_typed_disabled_btn.clicked.connect(lambda: self._handle_show_typed_button(False))

        show_button_row.addWidget(self.show_typed_enabled_btn)
        show_button_row.addWidget(self.show_typed_disabled_btn)
        show_button_row.addStretch()
        typing_behavior_layout.addLayout(show_button_row)

        show_typed = settings.get_setting("show_typed_characters", settings.get_default("show_typed_characters")) == "1"
        self._update_show_typed_buttons(show_typed)
        
        # Show ghost text option
        show_ghost_label = QLabel("Show what ghost types")
        show_ghost_label.setStyleSheet("font-weight: bold;")
        typing_behavior_layout.addWidget(show_ghost_label)

        show_ghost_description = QLabel(
            "Display the ghost text overlay during the race. If disabled, only the ghost progress bar will be shown."
        )
        show_ghost_description.setWordWrap(True)
        show_ghost_description.setStyleSheet("color: #888888; font-size: 9pt;")
        typing_behavior_layout.addWidget(show_ghost_description)

        show_ghost_button_row = QHBoxLayout()
        show_ghost_button_row.setSpacing(8)

        self.show_ghost_enabled_btn = QPushButton("Enabled")
        self.show_ghost_disabled_btn = QPushButton("Disabled")
        for btn in (self.show_ghost_enabled_btn, self.show_ghost_disabled_btn):
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.setCursor(Qt.PointingHandCursor)

        self.show_ghost_enabled_btn.clicked.connect(lambda: self._handle_show_ghost_text_button(True))
        self.show_ghost_disabled_btn.clicked.connect(lambda: self._handle_show_ghost_text_button(False))

        show_ghost_button_row.addWidget(self.show_ghost_enabled_btn)
        show_ghost_button_row.addWidget(self.show_ghost_disabled_btn)
        show_ghost_button_row.addStretch()
        typing_behavior_layout.addLayout(show_ghost_button_row)

        show_ghost = settings.get_setting("show_ghost_text", settings.get_default("show_ghost_text")) == "1"
        self._update_show_ghost_text_buttons(show_ghost)
        
        # Smart Indentation option
        auto_indent_label = QLabel("Smart Indentation")
        auto_indent_label.setStyleSheet("font-weight: bold;")
        typing_behavior_layout.addWidget(auto_indent_label)

        auto_indent_description = QLabel(
            "Matches previous line indentation and auto-indents after block openers (':', '{', etc.). "
            "Backspace un-indents a full level if at a tab stop."
        )
        auto_indent_description.setWordWrap(True)
        auto_indent_description.setStyleSheet("color: #888888; font-size: 9pt;")
        typing_behavior_layout.addWidget(auto_indent_description)

        auto_indent_button_row = QHBoxLayout()
        auto_indent_button_row.setSpacing(8)

        self.auto_indent_enabled_btn = QPushButton("Enabled")
        self.auto_indent_disabled_btn = QPushButton("Disabled")
        for btn in (self.auto_indent_enabled_btn, self.auto_indent_disabled_btn):
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.setCursor(Qt.PointingHandCursor)

        self.auto_indent_enabled_btn.clicked.connect(lambda: self._handle_auto_indent_button(True))
        self.auto_indent_disabled_btn.clicked.connect(lambda: self._handle_auto_indent_button(False))

        auto_indent_button_row.addWidget(self.auto_indent_enabled_btn)
        auto_indent_button_row.addWidget(self.auto_indent_disabled_btn)
        auto_indent_button_row.addStretch()
        typing_behavior_layout.addLayout(auto_indent_button_row)

        auto_indent = settings.get_setting("auto_indent", settings.get_default("auto_indent")) == "1"
        self._update_auto_indent_buttons(auto_indent)

        # Instant Death option (also in Settings)
        death_label = QLabel("Instant Death Mode")
        death_label.setStyleSheet("font-weight: bold;")
        typing_behavior_layout.addWidget(death_label)

        death_description = QLabel(
            "Immediately reset to the beginning of the file if any mistake is made. Hardcore mode."
        )
        death_description.setWordWrap(True)
        death_description.setStyleSheet("color: #888888; font-size: 9pt;")
        typing_behavior_layout.addWidget(death_description)

        death_button_row = QHBoxLayout()
        death_button_row.setSpacing(8)

        self.instant_death_enabled_btn = QPushButton("Enabled")
        self.instant_death_disabled_btn = QPushButton("Disabled")
        for btn in (self.instant_death_enabled_btn, self.instant_death_disabled_btn):
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.setCursor(Qt.PointingHandCursor)

        self.instant_death_enabled_btn.clicked.connect(lambda: self._handle_instant_death_button(True))
        self.instant_death_disabled_btn.clicked.connect(lambda: self._handle_instant_death_button(False))

        death_button_row.addWidget(self.instant_death_enabled_btn)
        death_button_row.addWidget(self.instant_death_disabled_btn)
        death_button_row.addStretch()
        typing_behavior_layout.addLayout(death_button_row)

        instant_death = settings.get_setting("instant_death_mode", settings.get_default("instant_death_mode")) == "1"
        self._update_instant_death_buttons(instant_death)

        
        typing_behavior_group.setLayout(typing_behavior_layout)
        s_layout.addWidget(typing_behavior_group)
        
        # Global Exclusions settings group
        explorer_group = QGroupBox("Global Exclusions")
        explorer_layout = QVBoxLayout()
        
        explorer_desc = QLabel(
            "Exclude files and folders globally using standard glob patterns. "
            "To ignore a file type, use <b>*.extension</b> (e.g. *.exe). "
            "Exact filenames or paths also work. Hidden items are removed from all counts and statistics."
        )
        explorer_desc.setWordWrap(True)
        explorer_desc.setStyleSheet("color: #888888; font-size: 9pt;")
        explorer_layout.addWidget(explorer_desc)
        
        # Ignored Files
        explorer_layout.addWidget(QLabel("Ignored Files/Patterns (one per line):"))
        self.ignored_files_edit = QTextEdit()
        self.ignored_files_edit.setPlaceholderText("*.exe\n*.zip\n*.pyc\nconfig.json\n\"CaseSensitiveName.py\"")
        self.ignored_files_edit.setMaximumHeight(100)
        self.ignored_files_edit.setText(settings.get_setting("ignored_files", settings.get_default("ignored_files")))
        explorer_layout.addWidget(self.ignored_files_edit)
        
        # Ignored Folders
        explorer_layout.addWidget(QLabel("Ignored Folders (one per line):"))
        self.ignored_folders_edit = QTextEdit()
        self.ignored_folders_edit.setPlaceholderText(".git\nnode_modules\nvenv\nbuild\n\"ExactFolderName\"")
        self.ignored_folders_edit.setMaximumHeight(100)
        self.ignored_folders_edit.setText(settings.get_setting("ignored_folders", settings.get_default("ignored_folders")))
        explorer_layout.addWidget(self.ignored_folders_edit)

        # Apply initial theme styling
        from app.themes import get_color_scheme
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        initial_scheme = get_color_scheme("dark", scheme_name)
        self._update_ignore_inputs_style(initial_scheme)
        
        # Use a timer to debounce save
        self._ignore_save_timer = QTimer()
        self._ignore_save_timer.setSingleShot(True)
        self._ignore_save_timer.setInterval(1000)
        self._ignore_save_timer.timeout.connect(self._save_ignore_settings)
        
        self.ignored_files_edit.textChanged.connect(self._ignore_save_timer.start)
        self.ignored_folders_edit.textChanged.connect(self._ignore_save_timer.start)
        
        explorer_group.setLayout(explorer_layout)
        s_layout.addWidget(explorer_group)
        
        # Color Scheme settings group
        color_scheme_group = QGroupBox("Color Scheme")
        color_scheme_layout = QVBoxLayout()
        color_scheme_layout.setSpacing(0)
        
        # Base Palette Selector (Moved from separate group)
        palette_row_widget = QWidget()
        palette_row = QHBoxLayout(palette_row_widget)
        palette_row.setContentsMargins(5, 5, 5, 10)
        palette_row.addWidget(QLabel("Base Palette:"))
        
        self.scheme_combo = QComboBox()
        self._populate_scheme_combo("dark")
        
        cur_scheme = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        index = self.scheme_combo.findText(cur_scheme)
        if index >= 0:
            self.scheme_combo.setCurrentIndex(index)
            
        self.scheme_combo.currentTextChanged.connect(self.on_scheme_changed)
        palette_row.addWidget(self.scheme_combo)
        palette_row.addStretch()
        
        color_scheme_layout.addWidget(palette_row_widget)
        
        # Theme Customization Section (Integrated)
        color_scheme_layout.addSpacing(10)
        
        # 1. Section Title
        self.theme_settings_title = QLabel("THEME SETTINGS: DRACULA")
        self.theme_settings_title.setStyleSheet("font-weight: bold; font-size: 11pt; padding: 5px;")
        color_scheme_layout.addWidget(self.theme_settings_title)
        
        # 3. Dynamic Grid for Colors
        # We use a grid to keep columns aligned but wrap it in a container
        grid_container = QWidget()
        self.color_grid = QGridLayout(grid_container)
        self.color_grid.setContentsMargins(15, 0, 15, 15)
        self.color_grid.setSpacing(10)
        self.color_grid.setColumnStretch(1, 1) # Space between name and color
        
        # Add Header row directly into the grid for perfect alignment
        header_bg = QFrame()
        header_bg.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border-top: 1px solid #444; border-bottom: 1px solid #444;")
        header_bg.setFixedHeight(35)
        self.color_grid.addWidget(header_bg, 0, 0, 1, 3) # Span across columns 0, 1, and 2
        
        prop_header = QLabel("  PROPERTY")
        prop_header.setStyleSheet("font-weight: bold; color: #888; font-size: 8pt; background: transparent;")
        self.color_grid.addWidget(prop_header, 0, 0, Qt.AlignVCenter)
        
        val_header = QLabel("COLOR & VALUE  ")
        val_header.setStyleSheet("font-weight: bold; color: #888; font-size: 8pt; background: transparent;")
        self.color_grid.addWidget(val_header, 0, 2, Qt.AlignRight | Qt.AlignVCenter)

        self.color_buttons = {}
        self.color_hex_labels = {}
        
        categories = [
            ("CORE PALETTE", [
                ("bg_primary", "Main Background", "Used for the main window and typing area background."),
                ("bg_secondary", "Secondary Background", "Used for sidebars, headers, and secondary UI panels."),
                ("bg_tertiary", "Selection/Hover", "Used for hovered items and selected list entries."),
                ("accent_color", "Accent Color", "Used for focus indicators, selection highlights, and active elements."),
            ]),
            ("TYPOGRAPHY", [
                ("text_primary", "Main Text", "Used for the most important text like filenames and titles."),
                ("text_secondary", "Secondary Text", "Used for paths, stats, and less prominent information."),
                ("text_disabled", "Disabled Text", "Used for labels or buttons that are currently inactive."),
            ]),
            ("FOLDER & CARDS", [
                ("card_bg", "Card Background", "Specific background for Folder rows and Language cards."),
                ("card_border", "Card Border", "Specific border color for Folder rows and Language cards."),
            ]),
            ("TYPING STATES", [
                ("text_untyped", "Untyped Text", "The color of characters in the editor that haven't been typed yet."),
                ("text_correct", "Correct Text", "The color of characters that you have typed correctly."),
                ("text_incorrect", "Incorrect Text", "The color of characters that you have typed incorrectly."),
                ("text_paused", "Paused Text", "The highlight color for the code block you was previously typing (if session paused)."),
                ("cursor_color", "Cursor Color", "The color of the typing cursor in the editor."),
            ]),
            ("UI COMPONENTS", [
                ("border_color", "Borders", "Generic border color used for main divides and standard widgets."),
                ("button_bg", "Button Background", "The default background color for all standard buttons."),
                ("button_hover", "Button Hover", "The background color when hovering over a button."),
            ]),
            ("STATUS COLORS", [
                ("success_color", "Success", "Used for positive messages, 100% accuracy, and completions."),
                ("warning_color", "Warning", "Used for alerts and warnings (e.g. missing folder)."),
                ("error_color", "Error", "Used for critical errors and failure states."),
                ("info_color", "Info", "Used for informational notifications and tips."),
            ]),
        ]
        
        row = 1
        for cat_name, items in categories:
            # Category Row
            cat_label = QLabel(cat_name)
            cat_label.setStyleSheet("""
                background-color: rgba(255, 255, 255, 0.03);
                color: #aaa;
                font-weight: bold;
                font-size: 8pt;
                padding: 4px 10px;
                margin-top: 10px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            """)
            self.color_grid.addWidget(cat_label, row, 0, 1, 3)
            row += 1
            
            for item in items:
                key, label = item[0], item[1]
                tooltip = item[2] if len(item) > 2 else ""
                
                # Name Label
                name_lbl = QLabel(label)
                name_lbl.setStyleSheet("color: #ccc; padding-left: 5px;")
                if tooltip:
                    name_lbl.setToolTip(tooltip)
                self.color_grid.addWidget(name_lbl, row, 0)
                
                # Color swatch + Hex Label
                swatch_container = QWidget()
                swatch_layout = QHBoxLayout(swatch_container)
                swatch_layout.setContentsMargins(0, 0, 0, 0)
                swatch_layout.setSpacing(8)
                
                # Circular swatch (button)
                btn = QPushButton()
                btn.setFixedSize(22, 22)
                btn.setCursor(Qt.PointingHandCursor)
                if tooltip:
                    btn.setToolTip(tooltip)
                # Perfect circle styling: radius should be exactly half of width/height
                # Using a slightly darker border for better definition on light colors
                btn.setStyleSheet("""
                    QPushButton {
                        border-radius: 11px;
                        border: 1px solid rgba(255, 255, 255, 0.15);
                        background-color: #000;
                    }
                    QPushButton:hover {
                        border: 1px solid rgba(255, 255, 255, 0.4);
                    }
                """)
                btn.clicked.connect(lambda checked=False, k=key: self.on_unified_color_pick(k))
                self.color_buttons[key] = btn
                
                # Hex string label - using a clearer weight and letter spacing to avoid blurriness
                hex_lbl = QLabel("#000000")
                hex_lbl.setStyleSheet("""
                    color: #999; 
                    font-family: 'JetBrains Mono', 'Cascadia Code', monospace; 
                    font-size: 10pt;
                    font-weight: 500;
                """)
                self.color_hex_labels[key] = hex_lbl
                
                swatch_layout.addStretch()
                swatch_layout.addWidget(btn)
                swatch_layout.addWidget(hex_lbl)
                swatch_container.setMinimumWidth(130)
                
                self.color_grid.addWidget(swatch_container, row, 2)
                row += 1
        
        color_scheme_layout.addWidget(grid_container)
        
        # 4. Action Buttons Footer
        footer_widget = QWidget()
        footer_widget.setStyleSheet("background-color: rgba(0, 0, 0, 0.1); border-top: 1px solid #444;")
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(15, 12, 15, 12)
        
        self.btn_reset_theme = QPushButton("Reset Defaults")
        self.btn_reset_theme.clicked.connect(self.on_reset_theme)
        self.btn_reset_theme.setCursor(Qt.PointingHandCursor)
        self.btn_reset_theme.setMinimumWidth(100)
        footer_layout.addWidget(self.btn_reset_theme)
        
        footer_layout.addStretch()
        
        self.btn_save_theme = QPushButton("Save Theme")
        self.btn_save_theme.clicked.connect(self.on_save_theme)
        self.btn_save_theme.setCursor(Qt.PointingHandCursor)
        self.btn_save_theme.setStyleSheet("background-color: #6272a4; color: white; border: none; padding: 8px 20px;")
        footer_layout.addWidget(self.btn_save_theme)
        
        self.btn_new_theme = QPushButton("+ New Theme")
        self.btn_new_theme.clicked.connect(self.on_new_theme)
        self.btn_new_theme.setCursor(Qt.PointingHandCursor)
        self.btn_new_theme.setStyleSheet("background-color: #5e81ac; color: white; border: none; padding: 8px 20px;")
        footer_layout.addWidget(self.btn_new_theme)
        
        color_scheme_layout.addWidget(footer_widget)
        
        color_scheme_group.setLayout(color_scheme_layout)
        s_layout.addWidget(color_scheme_group)
        
        # Initialize working scheme state
        self._colors_dirty = False
        self.update_color_buttons_from_theme()
        
        # Cursor settings group
        cursor_group = QGroupBox("Cursor")
        cursor_layout = QVBoxLayout()
        
        # Cursor Type (Blinking/Static)
        cursor_layout.addWidget(QLabel("Type:"))
        type_row = QHBoxLayout()
        type_row.setSpacing(8)
        
        self.cursor_blink_btn = QPushButton("Blinking")
        self.cursor_static_btn = QPushButton("Static")
        
        for btn in (self.cursor_blink_btn, self.cursor_static_btn):
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            
        self.cursor_blink_btn.clicked.connect(lambda: self._handle_cursor_type_button("blinking"))
        self.cursor_static_btn.clicked.connect(lambda: self._handle_cursor_type_button("static"))
        
        type_row.addWidget(self.cursor_blink_btn)
        type_row.addWidget(self.cursor_static_btn)
        type_row.addStretch()
        cursor_layout.addLayout(type_row)
        
        # Cursor Style (Block/Underscore/IBeam)
        cursor_layout.addWidget(QLabel("Style:"))
        style_row = QHBoxLayout()
        style_row.setSpacing(12)
        
        self.cursor_preview_widgets = []  # List of (style_name, widget) to toggle blinking
        
        def create_cursor_style_button(style_name: str, label: str):
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setFixedSize(100, 80)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda: self._handle_cursor_style_button(style_name))
            
            btn_layout = QVBoxLayout(btn)
            btn_layout.setContentsMargins(4, 8, 4, 8)
            
            # Preview container (mimic editor look)
            preview_container = QWidget()
            preview_container.setFixedSize(40, 40)
            preview_container.setStyleSheet("background-color: #2e3440; border-radius: 4px;")
            
            # Character label (the 'text' being typed)
            char_label = QLabel("a", preview_container)
            char_label.setAlignment(Qt.AlignCenter)
            char_label.setGeometry(0, 0, 40, 40)
            char_label.setStyleSheet("color: #d8dee9; font-family: 'JetBrains Mono', monospace; font-size: 24px; background: transparent;")
            
            # The actual cursor shape
            cursor_shape = QLabel(preview_container)
            
            if style_name == "block":
                # Block covers the character, semi-transparent or behind?
                # In editor it's usually an overlay or inverted color. 
                # Let's make it a white block with opacity to show character through, or just white block.
                # Standard block cursor usually covers.
                cursor_shape.setStyleSheet("background-color: rgba(255, 255, 255, 0.8);") 
                cursor_shape.setGeometry(10, 5, 20, 30) # Centered over 'a'
                # Ensure cursor is on top of char for block? Or behind? 
                # If on top with opacity, it looks like a selection.
                # Let's put it behind for "block" style if we want to see the letter, 
                # OR make the letter color inverted. 
                # For simplicity, let's just put it on top with high alpha.
                char_label.raise_() # Keep character on top of block cursor so it's visible (inverted look simulation)
                char_label.setStyleSheet("color: #2e3440; font-family: 'JetBrains Mono', monospace; font-size: 24px; background: transparent; font-weight: bold;")
                
            elif style_name == "underscore":
                cursor_shape.setStyleSheet("background-color: #ffffff;")
                cursor_shape.setGeometry(10, 32, 20, 4)  # Bottom line
                
            elif style_name == "ibeam":
                cursor_shape.setStyleSheet("background-color: #ffffff;")
                cursor_shape.setGeometry(9, 5, 2, 30)  # Vertical line to the left of character
            
            # Center the preview container in the button layout
            preview_layout = QHBoxLayout()
            preview_layout.addStretch()
            preview_layout.addWidget(preview_container)
            preview_layout.addStretch()
            btn_layout.addLayout(preview_layout)
            
            # Label
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("background: transparent; font-weight: bold;")
            btn_layout.addWidget(lbl)
            
            self.cursor_preview_widgets.append((style_name, cursor_shape))
            return btn

        self.cursor_block_btn = create_cursor_style_button("block", "Block")
        self.cursor_underscore_btn = create_cursor_style_button("underscore", "Underscore")
        self.cursor_ibeam_btn = create_cursor_style_button("ibeam", "I-Beam")
        
        style_row.addWidget(self.cursor_block_btn)
        style_row.addWidget(self.cursor_underscore_btn)
        style_row.addWidget(self.cursor_ibeam_btn)
        style_row.addStretch()
        cursor_layout.addLayout(style_row)
        
        cursor_group.setLayout(cursor_layout)
        s_layout.addWidget(cursor_group)
        
        # Initialize cursor buttons state
        current_type = settings.get_setting("cursor_type", settings.get_default("cursor_type"))
        self._update_cursor_type_buttons(current_type)
        
        current_style = settings.get_setting("cursor_style", settings.get_default("cursor_style"))
        self._update_cursor_style_buttons(current_style)
        
        # Setup blink timer for previews
        self._settings_cursor_timer = QTimer(self)
        self._settings_cursor_timer.setInterval(500)
        self._settings_cursor_timer.timeout.connect(self._on_cursor_preview_blink)
        if current_type == "blinking":
            self._settings_cursor_timer.start()
        
        # Font settings group
        font_group = QGroupBox("Fonts")
        font_layout = QVBoxLayout()
        font_layout.setContentsMargins(15, 20, 15, 15)
        font_layout.setSpacing(10)
        
        # Helper for flat styling
        font_control_style = """
            QComboBox, QSpinBox {
                background-color: #2e3440;
                color: #eceff4;
                border: 1px solid #434c5e;
                border-radius: 6px;
                padding-left: 10px;
            }
            QComboBox:hover, QSpinBox:hover {
                border: 1px solid #88c0d0;
            }
            QComboBox::drop-down {
                border: none;
            }
        """
        
        # --- Typing Font Section ---
        typing_sec = QVBoxLayout()
        typing_label = QLabel("TYPING AREA FONT")
        typing_label.setStyleSheet("color: #88c0d0; font-size: 10px; font-weight: bold; letter-spacing: 1.5px; margin-bottom: 5px;")
        typing_sec.addWidget(typing_label)
        
        typing_grid = QGridLayout()
        typing_grid.setContentsMargins(10, 0, 0, 10)
        typing_grid.setHorizontalSpacing(20)
        
        # Family
        self.font_family_combo = QComboBox()
        self.font_family_combo.setMinimumWidth(260)
        self.font_family_combo.setFixedHeight(36)
        self.font_family_combo.setStyleSheet(font_control_style)
        self._populate_font_families(self.font_family_combo)
        self.font_family_combo.setCurrentText(settings.get_setting("font_family", settings.get_default("font_family")))
        self.font_family_combo.currentTextChanged.connect(self.on_font_family_changed)
        
        family_label = QLabel("Family:")
        family_label.setStyleSheet("font-weight: 500;")
        typing_grid.addWidget(family_label, 0, 0)
        typing_grid.addWidget(self.font_family_combo, 0, 1)
        
        # Size Stepper
        size_row = QHBoxLayout()
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 48)
        self.font_size_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.font_size_spin.setAlignment(Qt.AlignCenter)
        self.font_size_spin.setFixedWidth(60)
        self.font_size_spin.setFixedHeight(36)
        self.font_size_spin.setStyleSheet(font_control_style + "QSpinBox { padding-left: 0; }")
        self.font_size_spin.setValue(settings.get_setting_int("font_size", 12))
        self.font_size_spin.valueChanged.connect(self.on_font_size_changed)

        btn_style = """
            QPushButton {
                font-size: 20px;
                font-weight: 900;
                background: #3b4252;
                color: #eceff4;
                border: 1px solid #434c5e;
                border-radius: 6px;
                padding: 0;
            }
            QPushButton:hover {
                background: #4c566a;
                border-color: #88c0d0;
            }
            QPushButton:pressed {
                background: #88c0d0;
                color: #2e3440;
            }
        """

        btn_minus = QPushButton("−")  # Using a proper minus sign character
        btn_plus = QPushButton("+")
        for btn in [btn_minus, btn_plus]:
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(btn_style)
        
        btn_minus.clicked.connect(lambda: self.font_size_spin.setValue(self.font_size_spin.value() - 1))
        btn_plus.clicked.connect(lambda: self.font_size_spin.setValue(self.font_size_spin.value() + 1))
        
        size_row.addWidget(btn_minus)
        size_row.addWidget(self.font_size_spin)
        size_row.addWidget(btn_plus)
        size_row.addStretch()
        
        size_label = QLabel("Size:")
        size_label.setStyleSheet("font-weight: 500;")
        typing_grid.addWidget(size_label, 1, 0)
        typing_grid.addLayout(size_row, 1, 1)
        
        typing_sec.addLayout(typing_grid)
        font_layout.addLayout(typing_sec)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background: rgba(255,255,255,0.08); margin: 10px 0;")
        font_layout.addWidget(line)

        # --- UI Font Section ---
        ui_sec = QVBoxLayout()
        ui_label = QLabel("USER INTERFACE FONT")
        ui_label.setStyleSheet("color: #88c0d0; font-size: 10px; font-weight: bold; letter-spacing: 1.5px; margin-bottom: 5px;")
        ui_sec.addWidget(ui_label)
        
        ui_grid = QGridLayout()
        ui_grid.setContentsMargins(10, 0, 0, 10)
        ui_grid.setHorizontalSpacing(20)
        
        # UI Family
        self.ui_font_family_combo = QComboBox()
        self.ui_font_family_combo.setMinimumWidth(260)
        self.ui_font_family_combo.setFixedHeight(36)
        self.ui_font_family_combo.setStyleSheet(font_control_style)
        self._populate_font_families(self.ui_font_family_combo)
        self.ui_font_family_combo.setCurrentText(settings.get_setting("ui_font_family", settings.get_default("ui_font_family")))
        self.ui_font_family_combo.currentTextChanged.connect(self.on_ui_font_family_changed)
        
        ui_family_label = QLabel("Family:")
        ui_family_label.setStyleSheet("font-weight: 500;")
        ui_grid.addWidget(ui_family_label, 0, 0)
        ui_grid.addWidget(self.ui_font_family_combo, 0, 1)
        
        # UI Size Stepper
        ui_size_row = QHBoxLayout()
        self.ui_font_size_spin = QSpinBox()
        self.ui_font_size_spin.setRange(8, 24)
        self.ui_font_size_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.ui_font_size_spin.setAlignment(Qt.AlignCenter)
        self.ui_font_size_spin.setFixedWidth(60)
        self.ui_font_size_spin.setFixedHeight(36)
        self.ui_font_size_spin.setStyleSheet(font_control_style + "QSpinBox { padding-left: 0; }")
        self.ui_font_size_spin.setValue(settings.get_setting_int("ui_font_size", 10))
        self.ui_font_size_spin.valueChanged.connect(self.on_ui_font_size_changed)

        ui_btn_minus = QPushButton("-")
        ui_btn_plus = QPushButton("+")
        for btn in [ui_btn_minus, ui_btn_plus]:
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(btn_style)
        
        ui_btn_minus.clicked.connect(lambda: self.ui_font_size_spin.setValue(self.ui_font_size_spin.value() - 1))
        ui_btn_plus.clicked.connect(lambda: self.ui_font_size_spin.setValue(self.ui_font_size_spin.value() + 1))
        
        ui_size_row.addWidget(ui_btn_minus)
        ui_size_row.addWidget(self.ui_font_size_spin)
        ui_size_row.addWidget(ui_btn_plus)
        ui_size_row.addStretch()
        
        ui_size_label = QLabel("Size:")
        ui_size_label.setStyleSheet("font-weight: 500;")
        ui_grid.addWidget(ui_size_label, 1, 0)
        ui_grid.addLayout(ui_size_row, 1, 1)
        
        ui_sec.addLayout(ui_grid)
        font_layout.addLayout(ui_sec)
        
        # --- Add Font Button at the bottom ---
        self.add_font_btn = QPushButton("  + Import Custom Font File")
        self.add_font_btn.clicked.connect(self.on_add_font_file)
        self.add_font_btn.setMinimumHeight(44)
        self.add_font_btn.setCursor(Qt.PointingHandCursor)
        self.add_font_btn.setStyleSheet("""
            QPushButton { 
                background: #4c566a; 
                color: #eceff4; 
                border: 1px solid #5e81ac; 
                border-radius: 8px; 
                font-weight: bold; 
                margin-top: 15px; 
            } 
            QPushButton:hover { 
                background: #5e81ac; 
            }
        """)
        font_layout.addWidget(self.add_font_btn)
        
        font_group.setLayout(font_layout)
        s_layout.addWidget(font_group)
        
        # Typing settings group
        typing_group = QGroupBox("Typing")
        typing_layout = QFormLayout()
        
        # Space character
        self.space_char_combo = QComboBox()
        self.space_char_combo.addItems(["␣", "·", " ", "custom"])
        space_char = settings.get_setting("space_char", settings.get_default("space_char"))
        if space_char in ["␣", "·", " "]:
            self.space_char_combo.setCurrentText(space_char)
        else:
            self.space_char_combo.setCurrentText("custom")
        
        self.space_char_custom = QLineEdit()
        self.space_char_custom.setMaxLength(1)
        self.space_char_custom.setText(space_char if space_char not in ["␣", "·", " "] else "")
        self.space_char_custom.setEnabled(self.space_char_combo.currentText() == "custom")
        # Match the dropdown styling - no bottom highlight
        self.space_char_custom.setStyleSheet("""
            QLineEdit {
                background-color: #2e3440;
                color: #eceff4;
                border: 1px solid #434c5e;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QLineEdit:hover {
                border: 1px solid #88c0d0;
            }
            QLineEdit:focus {
                border: 1px solid #88c0d0;
            }
            QLineEdit:disabled {
                background-color: #3b4252;
                color: #4c566a;
            }
        """)
        
        self.space_char_combo.currentTextChanged.connect(self.on_space_char_changed)
        self.space_char_custom.textChanged.connect(self.on_space_char_custom_changed)
        
        space_layout = QHBoxLayout()
        space_layout.addWidget(self.space_char_combo)
        space_layout.addWidget(QLabel("Custom:"))
        space_layout.addWidget(self.space_char_custom)
        space_layout.addStretch() # Ensure this row also doesn't stretch weirdly
        typing_layout.addRow("Space char:", space_layout)
        
        # Tab width - modern stepper with +/- buttons
        tab_width_row = QHBoxLayout()
        tab_width_row.setSpacing(8)
        
        self.tab_width_spin = QSpinBox()
        self.tab_width_spin.setRange(1, 8)
        self.tab_width_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.tab_width_spin.setAlignment(Qt.AlignCenter)
        self.tab_width_spin.setFixedWidth(60)
        self.tab_width_spin.setFixedHeight(36)
        self.tab_width_spin.setSuffix(" spaces")
        # Use space_per_tab for the shortcut behavior
        space_per_tab = int(settings.get_setting("space_per_tab", settings.get_default("space_per_tab")))
        self.tab_width_spin.setValue(space_per_tab)
        self.tab_width_spin.valueChanged.connect(self.on_tab_width_changed)
        
        # Reuse the button style from fonts section
        spinner_btn_style = """
            QPushButton {
                font-size: 20px;
                font-weight: 900;
                background: #3b4252;
                color: #eceff4;
                border: 1px solid #434c5e;
                border-radius: 6px;
                padding: 0;
            }
            QPushButton:hover {
                background: #4c566a;
                border-color: #88c0d0;
            }
            QPushButton:pressed {
                background: #88c0d0;
                color: #2e3440;
            }
        """
        
        spinner_input_style = """
            QSpinBox {
                background-color: #2e3440;
                color: #eceff4;
                border: 1px solid #434c5e;
                border-radius: 6px;
                padding-left: 0;
            }
            QSpinBox:hover {
                border: 1px solid #88c0d0;
            }
        """
        
        self.tab_width_spin.setStyleSheet(spinner_input_style)
        
        tab_minus_btn = QPushButton("−")
        tab_plus_btn = QPushButton("+")
        for btn in [tab_minus_btn, tab_plus_btn]:
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(spinner_btn_style)
        
        tab_minus_btn.clicked.connect(lambda: self.tab_width_spin.setValue(self.tab_width_spin.value() - 1))
        tab_plus_btn.clicked.connect(lambda: self.tab_width_spin.setValue(self.tab_width_spin.value() + 1))
        
        tab_width_row.addWidget(tab_minus_btn)
        tab_width_row.addWidget(self.tab_width_spin)
        tab_width_row.addWidget(tab_plus_btn)
        tab_width_row.addStretch()
        typing_layout.addRow("Space insert per tab:", tab_width_row)
        
        # Pause delay - modern stepper with +/- buttons
        pause_delay_row = QHBoxLayout()
        pause_delay_row.setSpacing(8)
        
        self.pause_delay_spin = QSpinBox()
        self.pause_delay_spin.setRange(1, 60)
        self.pause_delay_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.pause_delay_spin.setAlignment(Qt.AlignCenter)
        self.pause_delay_spin.setFixedWidth(80)
        self.pause_delay_spin.setFixedHeight(36)
        self.pause_delay_spin.setSuffix(" seconds")
        pause_delay = int(settings.get_setting_float("pause_delay", 7.0, min_val=1.0, max_val=60.0))
        self.pause_delay_spin.setValue(pause_delay)
        self.pause_delay_spin.setStyleSheet(spinner_input_style)
        self.pause_delay_spin.valueChanged.connect(self.on_pause_delay_changed)
        
        pause_minus_btn = QPushButton("−")
        pause_plus_btn = QPushButton("+")
        for btn in [pause_minus_btn, pause_plus_btn]:
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(spinner_btn_style)
        
        pause_minus_btn.clicked.connect(lambda: self.pause_delay_spin.setValue(self.pause_delay_spin.value() - 1))
        pause_plus_btn.clicked.connect(lambda: self.pause_delay_spin.setValue(self.pause_delay_spin.value() + 1))
        
        pause_delay_row.addWidget(pause_minus_btn)
        pause_delay_row.addWidget(self.pause_delay_spin)
        pause_delay_row.addWidget(pause_plus_btn)
        pause_delay_row.addStretch()
        
        typing_layout.addRow("Auto-pause delay:", pause_delay_row)

        # Best WPM accuracy threshold - modern stepper with +/- buttons
        best_wpm_row = QHBoxLayout()
        best_wpm_row.setSpacing(8)
        
        self.best_wpm_accuracy_spin = QSpinBox()
        self.best_wpm_accuracy_spin.setRange(0, 100)
        self.best_wpm_accuracy_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.best_wpm_accuracy_spin.setAlignment(Qt.AlignCenter)
        self.best_wpm_accuracy_spin.setFixedWidth(60)
        self.best_wpm_accuracy_spin.setFixedHeight(36)
        self.best_wpm_accuracy_spin.setSuffix(" %")
        try:
            best_wpm_acc_raw = settings.get_setting("best_wpm_min_accuracy", settings.get_default("best_wpm_min_accuracy"))
            best_wpm_percent = int(round(float(best_wpm_acc_raw) * 100)) if best_wpm_acc_raw is not None else 90
        except (TypeError, ValueError):
            best_wpm_percent = 90
        self.best_wpm_accuracy_spin.setValue(best_wpm_percent)
        self.best_wpm_accuracy_spin.setStyleSheet(spinner_input_style)
        self.best_wpm_accuracy_spin.valueChanged.connect(self.on_best_wpm_accuracy_changed)
        
        best_wpm_minus_btn = QPushButton("−")
        best_wpm_plus_btn = QPushButton("+")
        for btn in [best_wpm_minus_btn, best_wpm_plus_btn]:
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(spinner_btn_style)
        
        best_wpm_minus_btn.clicked.connect(lambda: self.best_wpm_accuracy_spin.setValue(self.best_wpm_accuracy_spin.value() - 1))
        best_wpm_plus_btn.clicked.connect(lambda: self.best_wpm_accuracy_spin.setValue(self.best_wpm_accuracy_spin.value() + 1))
        
        best_wpm_row.addWidget(best_wpm_minus_btn)
        best_wpm_row.addWidget(self.best_wpm_accuracy_spin)
        best_wpm_row.addWidget(best_wpm_plus_btn)
        best_wpm_row.addStretch()
        typing_layout.addRow("Best WPM min accuracy:", best_wpm_row)
        
        typing_group.setLayout(typing_layout)
        s_layout.addWidget(typing_group)
        
        # Sound settings group (simplified)
        sound_group = QGroupBox("Sounds")
        sound_layout = QVBoxLayout()
        
        # Sound enabled/disabled buttons
        sound_enabled_label = QLabel("Typing Sounds")
        sound_enabled_label.setStyleSheet("font-weight: bold;")
        sound_layout.addWidget(sound_enabled_label)
        
        sound_description = QLabel(
            "Play a sound effect when you press keys while typing. Use the volume icon in the typing tab to adjust volume."
        )
        sound_description.setWordWrap(True)
        sound_description.setStyleSheet("color: #888888; font-size: 10pt;")
        sound_layout.addWidget(sound_description)
        
        sound_button_row = QHBoxLayout()
        sound_button_row.setSpacing(8)
        
        self.sound_enabled_btn = QPushButton("Enabled")
        self.sound_disabled_btn = QPushButton("Disabled")
        for btn in (self.sound_enabled_btn, self.sound_disabled_btn):
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
        
        self.sound_enabled_btn.clicked.connect(lambda: self._handle_sound_enabled_button(True))
        self.sound_disabled_btn.clicked.connect(lambda: self._handle_sound_enabled_button(False))
        
        sound_button_row.addWidget(self.sound_enabled_btn)
        sound_button_row.addWidget(self.sound_disabled_btn)
        sound_button_row.addStretch()
        sound_layout.addLayout(sound_button_row)
        
        sound_enabled = settings.get_setting("sound_enabled", settings.get_default("sound_enabled")) == "1"
        self._update_sound_enabled_buttons(sound_enabled)
        
        # Profile selector (No Sound, Default_1, and custom profiles)
        profile_label = QLabel("Sound")
        profile_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        sound_layout.addWidget(profile_label)
        
        profile_layout = QHBoxLayout()
        self.sound_profile_combo = QComboBox()
        self.sound_profile_combo.setMinimumHeight(34)
        
        # Load all available profiles
        self._load_sound_profiles()
        
        current_profile = settings.get_setting("sound_profile", settings.get_default("sound_profile"))
        index = self.sound_profile_combo.findData(current_profile)
        if index >= 0:
            self.sound_profile_combo.setCurrentIndex(index)
        
        # Check for sound loading errors and show tooltip
        from app.sound_manager import get_sound_manager
        sound_mgr = get_sound_manager()
        error = sound_mgr.get_last_error()
        if error:
            self.sound_profile_combo.setToolTip(f"Warning: {error}")
        
        self.sound_profile_combo.currentIndexChanged.connect(self.on_sound_profile_changed)
        profile_layout.addWidget(self.sound_profile_combo)
        
        # Test button for main settings
        self.test_sound_btn = QPushButton(" Test")
        self.test_sound_btn.setIcon(get_icon("SOUND"))
        self.test_sound_btn.setMinimumHeight(34)
        self.test_sound_btn.setStyleSheet("padding: 0 10px;")
        self.test_sound_btn.setToolTip("Play the selected sound")
        self.test_sound_btn.clicked.connect(self._test_current_sound)
        profile_layout.addWidget(self.test_sound_btn)

        # Add Manage Sounds button
        manage_profiles_btn = QPushButton("Manage Sounds...")
        manage_profiles_btn.setMinimumHeight(34)
        manage_profiles_btn.clicked.connect(self.on_manage_sound_profiles)
        profile_layout.addWidget(manage_profiles_btn)
        
        profile_layout.addStretch()
        sound_layout.addLayout(profile_layout)
        
        sound_group.setLayout(sound_layout)
        s_layout.addWidget(sound_group)
        
        # Data Directory settings group
        data_dir_group = QGroupBox("Data Directory")
        data_dir_layout = QVBoxLayout()
        
        data_dir_desc = QLabel(
            "Choose where to store your typing statistics, ghosts, and custom sounds. "
            "The directory must have the required internal structure (created automatically)."
        )
        data_dir_desc.setWordWrap(True)
        data_dir_desc.setStyleSheet("color: #888888; font-size: 9pt;")
        data_dir_layout.addWidget(data_dir_desc)
        
        # Current data directory display
        data_dir_path_layout = QHBoxLayout()
        data_dir_path_label = QLabel("Current Location:")
        data_dir_path_label.setStyleSheet("font-weight: bold;")
        data_dir_path_layout.addWidget(data_dir_path_label)
        
        try:
            from app.portable_data import get_data_dir
            current_data_dir = str(get_data_dir())
        except:
            current_data_dir = str(settings.get_data_dir())
        
        self.data_dir_display = QLabel(current_data_dir)
        self.data_dir_display.setWordWrap(True)
        self.data_dir_display.setStyleSheet("color: #666; font-family: monospace; font-size: 9pt;")
        data_dir_path_layout.addWidget(self.data_dir_display, stretch=1)
        data_dir_layout.addLayout(data_dir_path_layout)
        
        # Buttons to change or reset data directory
        data_dir_buttons = QHBoxLayout()
        
        change_data_dir_btn = QPushButton("Change Location...")
        change_data_dir_btn.clicked.connect(self.on_change_data_directory)
        data_dir_buttons.addWidget(change_data_dir_btn)
        
        reset_data_dir_btn = QPushButton("Reset to Default")
        reset_data_dir_btn.clicked.connect(self.on_reset_data_directory)
        data_dir_buttons.addWidget(reset_data_dir_btn)
        
        data_dir_buttons.addStretch()
        data_dir_layout.addLayout(data_dir_buttons)
        
        data_dir_group.setLayout(data_dir_layout)
        s_layout.addWidget(data_dir_group)

        s_layout.addStretch()
        
        scroll.setWidget(settings_widget)
        
        # Store layout items for filtering
        # We need to map: GroupBox -> [Child Widgets/Labels] or just filter deeply.
        # A simple approach: Iterate over all GroupBoxes. For each, iterate over children.
        # If any child text matches, show child + group. Else hide.
        self_settings_groups = []       
        
        if DEBUG_STARTUP_TIMING:
            print(f"    [SettingsTab] TOTAL: {time.time() - t_start:.3f}s")
        
        return container_widget

    def _filter_settings(self, text: str):
        """Filter settings groups and items based on search text."""
        query = text.lower().strip()
        
        # Helper to find recursive text in a layout item
        def has_matching_text(widget):
            if not widget: return False
            
            # Check labels, buttons, checkboxes directly
            if isinstance(widget, (QLabel, QPushButton, QCheckBox, QRadioButton)):
                if query in widget.text().lower():
                    return True
            if isinstance(widget, (QGroupBox)):
                if query in widget.title().lower():
                    return True

            # If it's a container, check children
            # This is a bit manual in Qt. simpler:
            # We will traverse the whole settings_widget tree.
            return False

        # Better approach:
        # Traverse the main VBox (s_layout).
        # Items are mainly GroupBoxes.
        # Inside GroupBoxes are Layouts (Form or VBox).
        # We check if GroupBox title matches OR any internal widget matches.
        
        # Let's assume we stored it (we didn't yet, so let's rely on finding it or logic update).
        # BETTER: Save settings_widget as self.settings_scroll_widget
        pass # Replaced below logic since we need to save the reference
        
        if not hasattr(self, 'settings_scroll_widget'):
            # Find the scroll area in the current tab (Settings)
            # This is fragile. 
            # Let's update _create_settings_tab to save self.settings_scroll_widget
            return 

        if not query:
            # Restore saved scroll position if we were searching
            if hasattr(self, '_settings_scroll_pos') and self._settings_scroll_pos > 0:
                # Use a singleShot to ensure layout settles before scrolling
                QTimer.singleShot(10, lambda: self.settings_scroll_area.verticalScrollBar().setValue(self._settings_scroll_pos))
        else:
            # If starting a new search (was empty before), save position
            if len(query) == 1 and not hasattr(self, '_search_active'):
                 self._settings_scroll_pos = self.settings_scroll_area.verticalScrollBar().value()

        widget = self.settings_scroll_widget
        layout = widget.layout()
        
        has_visible_groups = False
        
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if not item: continue
            w = item.widget()
            if not w or not isinstance(w, QGroupBox): 
                continue
                
            group_box = w
            
            # If query is empty, show everything
            if not query:
                self._set_group_visible(group_box, True, list_items=True)
                continue

            group_visible = False
            
            # Check group title
            if query in group_box.title().lower():
                group_visible = True
                # If group matches, show all contents
                self._set_group_visible(group_box, True, list_items=True)
                has_visible_groups = True
                continue
            
            # Check children
            # This helper effectively keeps rows visible if they match
            if self._filter_group_contents(group_box, query):
                group_visible = True
                has_visible_groups = True
            
            group_box.setVisible(group_visible)


    def _set_group_visible(self, group: QGroupBox, visible: bool, list_items=False):
        """Helper to show/hide a group."""
        group.setVisible(visible)
        # We generally shouldn't manually toggle children visibility as it can break 
        # complex widgets like QComboBox internals. The GroupBox visibility is sufficient.

    def _filter_group_contents(self, group: QGroupBox, query: str) -> bool:
        """
        Filter items inside a GroupBox. 
        Returns True if at least one item matches (and thus Group stays visible).
        Items that don't match are hidden (if possible).
        """
        layout = group.layout()
        if not layout: return False
        
        has_match = False
        
        # We need to iterate layout items.
        # QFormLayout: itemAt(i, QFormLayout.LabelRole) / FieldRole
        # QVBoxLayout / QHBoxLayout: itemAt(i)
        
        # Universal approach: Validate widgets
        # BUT: In Layouts, hiding a widget usually hides the row if layout handles it.
        # For FormLayout, we might need to hide both label and field.
        
        children = group.findChildren(QWidget)
        # This gives a flat list. It's hard to associate labels with inputs using findChildren.
        
        # Iterating layout is safer for rows.
        count = layout.count()
        
        # Strategy:
        # 1. Iterate over "rows" or "items".
        # 2. Check if text in that item matches.
        # 3. If match, setVisible(True). catch: setVisible on a Label might hide it, but the input remains?
        
        # Simpler heuristic for VS Code like settings:
        # Just check if ANY text in the group matches. If so, show the WHOLE group.
        # Modifying rows inside is complex because of layout variations (Form vs VBox + HBox rows).
        
        # Let's try aggressive strict filtering:
        # - Iterate all child widgets.
        # - Identify "Rows" (e.g. text + input).
        
        # For this revision let's stick to: 
        # Show Group IF (Title matches OR Any Child Text matches).
        # We won't hide individual rows inside the group yet (complicated and might break layouts).
        
        should_show_group = False
        if query in group.title().lower():
            should_show_group = True
        
        if not should_show_group:
            # Check text of labels and buttons
            widget_types = (QLabel, QPushButton, QRadioButton, QCheckBox)
            for widget_type in widget_types:
                for child in group.findChildren(widget_type):
                    text = child.text().lower()
                    if query in text:
                        should_show_group = True
                        break
                if should_show_group:
                    break
        
        # Also check tooltips?
        if not should_show_group:
             for child in group.findChildren(QWidget):
                if child.toolTip() and query in child.toolTip().lower():
                    should_show_group = True
                    break
                    
        return should_show_group


    def open_typing_tab(self, folder_path: str):
        """Switch to typing tab and load the specified folder."""
        self.editor_tab.load_folder(folder_path)
        self.tabs.setCurrentWidget(self.editor_tab)

    def _update_folder_selection_state(self):
        for i in range(self.list.count()):
            item = self.list.item(i)
            widget = self.list.itemWidget(item)
            if isinstance(widget, FolderCardWidget):
                widget.set_selected(item.isSelected())

    def _set_remove_mode_for_cards(self, enabled: bool):
        for i in range(self.list.count()):
            widget = self.list.itemWidget(self.list.item(i))
            if isinstance(widget, FolderCardWidget):
                widget.set_remove_mode(enabled)
    
    def open_typing_tab_for_language(self, language: str, files: list):
        """Switch to typing tab and load files for a specific language."""
        self.editor_tab.load_language_files(language, files)
        self.tabs.setCurrentWidget(self.editor_tab)
    
    def refresh_languages_tab(self):
        """Refresh the languages tab after folders change."""
        self.languages_tab.mark_dirty()
        if self.tabs.currentWidget() is self.languages_tab:
            self.languages_tab.ensure_loaded(force=True)
    
    def refresh_language_stats(self, file_path: str = None):
        """Refresh language card stats after session completion (without full rescan)."""
        if hasattr(self.languages_tab, 'refresh_language_stats'):
            self.languages_tab.refresh_language_stats(file_path)

    def refresh_history_tab(self):
        """Refresh the session history tab."""
        if hasattr(self, "history_tab"):
            self.history_tab.refresh_history()

    def refresh_stats_tab(self):
        """Refresh the stats tab after session completion."""
        if hasattr(self, "stats_tab") and hasattr(self.stats_tab, "refresh"):
            self.stats_tab.refresh()

    def _populate_scheme_combo(self, theme_type: str):
        """Populate the scheme combo box based on the selected theme type."""
        self.scheme_combo.blockSignals(True)
        self.scheme_combo.clear()
        
        from app.themes import THEMES, _get_custom_themes
        
        # Built-in themes
        items = list(THEMES.get(theme_type, {}).keys())
        
        # Custom themes
        customs = _get_custom_themes()
        if theme_type in customs:
            items.extend(list(customs[theme_type].keys()))
            
        # Deduplicate and sort
        items = sorted(list(set(items)))
        
        self.scheme_combo.addItems(items)
        self.scheme_combo.blockSignals(False)

    def on_scheme_changed(self, scheme: str):
        """Handle scheme change."""
        if not scheme: return
        settings.set_setting("dark_scheme", scheme)
        self.apply_current_theme()
        self.update_color_buttons_from_theme()
    
    def on_color_pick(self, setting_key: str, button: QPushButton, label: str):
        """Open color picker dialog."""
        from PySide6.QtWidgets import QColorDialog
        from PySide6.QtGui import QColor
        
        current_color = settings.get_setting(setting_key, "#ffffff")
        color = QColorDialog.getColor(QColor(current_color), self, f"Pick {label}")
        
        if color.isValid():
            color_hex = color.name()
            settings.set_setting(setting_key, color_hex)
            button.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #666;")
            self.colors_changed.emit()
    
    def on_color_reset(self, setting_key: str, default: str, button: QPushButton):
        """Reset color to default."""
        settings.set_setting(setting_key, default)
        button.setStyleSheet(f"background-color: {default}; border: 1px solid #666;")
        self.colors_changed.emit()
    
    def _handle_cursor_type_button(self, type_str: str):
        """Handle cursor type button click."""
        current = settings.get_setting("cursor_type", settings.get_default("cursor_type"))
        if current == type_str:
            self._update_cursor_type_buttons(type_str)
            return
            
        settings.set_setting("cursor_type", type_str)
        self._update_cursor_type_buttons(type_str)
        
        # Handle timer
        if type_str == "blinking":
            self._settings_cursor_timer.start()
        else:
            self._settings_cursor_timer.stop()
            # Ensure visible when stopped
            for _, widget in self.cursor_preview_widgets:
                widget.setVisible(True)
                
        cursor_style = settings.get_setting("cursor_style", settings.get_default("cursor_style"))
        self.cursor_changed.emit(type_str, cursor_style)

    def _update_cursor_type_buttons(self, type_str: str):
        """Update visual state of cursor type buttons."""
        active_style = (
            "background-color: #5e81ac; color: white; border: none; border-radius: 6px;"
            " font-weight: bold;"
        )
        inactive_style = (
            "background-color: #3b4252; color: #d8dee9; border: 1px solid #434c5e; border-radius: 6px;"
        )
        
        is_blinking = (type_str == "blinking")
        self.cursor_blink_btn.setChecked(is_blinking)
        self.cursor_static_btn.setChecked(not is_blinking)
        
        self.cursor_blink_btn.setStyleSheet(active_style if is_blinking else inactive_style)
        self.cursor_static_btn.setStyleSheet(active_style if not is_blinking else inactive_style)

    def _update_cursor_style_buttons(self, style_str: str):
        """Update visual state of cursor style buttons."""
        active_style = (
            "QPushButton { background-color: #5e81ac; color: white; border: 2px solid #88c0d0; border-radius: 8px; }"
        )
        inactive_style = (
            "QPushButton { background-color: #3b4252; color: #d8dee9; border: 1px solid #434c5e; border-radius: 8px; }"
            "QPushButton:hover { border: 1px solid #88c0d0; }"
        )
        
        btns = {
            "block": self.cursor_block_btn,
            "underline": self.cursor_underline_btn,
            "beam": self.cursor_beam_btn
        }
        
        for k, btn in btns.items():
            btn.setChecked(k == style_str)
            btn.setStyleSheet(active_style if k == style_str else inactive_style)

    def _handle_cursor_style_button(self, style_str: str):
        """Handle cursor style button click."""
        current = settings.get_setting("cursor_style", settings.get_default("cursor_style"))
        if current == style_str:
            self._update_cursor_style_buttons(style_str)
            return
            
        settings.set_setting("cursor_style", style_str)
        self._update_cursor_style_buttons(style_str)
        
        cursor_type = settings.get_setting("cursor_type", settings.get_default("cursor_type"))
        self.cursor_changed.emit(cursor_type, style_str)

    def _update_cursor_style_buttons(self, style_str: str):
        """Update visual state of cursor style buttons."""
        active_style = (
            "QPushButton { background-color: #5e81ac; color: white; border: 2px solid #88c0d0; border-radius: 8px; }"
        )
        inactive_style = (
            "QPushButton { background-color: #3b4252; color: #d8dee9; border: 1px solid #434c5e; border-radius: 8px; }"
            "QPushButton:hover { border: 1px solid #88c0d0; }"
        )
        
        for btn, name in [
            (self.cursor_block_btn, "block"),
            (self.cursor_underscore_btn, "underscore"),
            (self.cursor_ibeam_btn, "ibeam")
        ]:
            is_active = (name == style_str)
            btn.setChecked(is_active)
            btn.setStyleSheet(active_style if is_active else inactive_style)

    def _on_cursor_preview_blink(self):
        """Toggle visibility of cursor previews for blinking effect."""
        for _, widget in self.cursor_preview_widgets:
            widget.setVisible(not widget.isVisible())

    def on_font_family_changed(self, font_family: str):
        settings.set_setting("font_family", font_family)
        self._emit_font_changed()
    
    def on_font_size_changed(self, font_size: int):
        settings.set_setting("font_size", str(font_size))
        self._emit_font_changed()

    def on_ui_font_family_changed(self, font_family: str):
        """Handle UI font family change."""
        settings.set_setting("ui_font_family", font_family)
        self.apply_current_theme()
        
    def on_ui_font_size_changed(self, font_size: int):
        """Handle UI font size change."""
        settings.set_setting("ui_font_size", str(font_size))
        self.apply_current_theme()
    
    def _emit_font_changed(self):
        """Helper to emit font_changed signal for the TYPING AREA."""
        family = settings.get_setting("font_family", settings.get_default("font_family"))
        size = settings.get_setting_int("font_size", 12, min_val=8, max_val=48)
        self.font_changed.emit(family, size, False)  # Ligatures removed
    
    def on_space_char_changed(self, char_option: str):
        """Handle space character dropdown change."""
        if char_option != "custom":
            settings.set_setting("space_char", char_option)
            self.space_char_custom.setEnabled(False)
            self.space_char_changed.emit(char_option)
        else:
            self.space_char_custom.setEnabled(True)
            if self.space_char_custom.text():
                settings.set_setting("space_char", self.space_char_custom.text())
                self.space_char_changed.emit(self.space_char_custom.text())
    
    def on_space_char_custom_changed(self, text: str):
        """Handle custom space character input."""
        if text and self.space_char_combo.currentText() == "custom":
            settings.set_setting("space_char", text)
            self.space_char_changed.emit(text)
    
    def on_pause_delay_changed(self, delay: int):
        settings.set_setting("pause_delay", str(delay))
        self.pause_delay_changed.emit(float(delay))
    
    def on_tab_width_changed(self, width: int):
        """Handle tab width (shortcut value) change."""
        settings.set_setting("space_per_tab", str(width))
        self.tab_width_changed.emit(width)
    
    def _load_custom_fonts(self):
        """Load custom fonts from settings and register them with QFontDatabase."""
        import json
        custom_fonts_raw = settings.get_setting("custom_fonts", "[]")
        try:
            custom_fonts = json.loads(custom_fonts_raw)
        except (ValueError, TypeError):
            custom_fonts = []
            
        from app.portable_data import get_fonts_dir
        fonts_dir = get_fonts_dir()
        
        for font_file in custom_fonts:
            font_path = fonts_dir / font_file
            if font_path.exists():
                font_id = QFontDatabase.addApplicationFont(str(font_path))
                if font_id == -1:
                    print(f"Failed to load custom font: {font_file}")
            else:
                print(f"Custom font file not found: {font_file}")

    def _populate_font_families(self, combo=None):
        """Populate a font family combo box with system and custom fonts."""
        target_combo = combo if combo else (self.font_family_combo if hasattr(self, 'font_family_combo') else None)
        if not target_combo:
            return
            
        current_text = target_combo.currentText()
        target_combo.blockSignals(True)
        target_combo.clear()
        
        # Priority fonts first
        priority_fonts = [
            "JetBrains Mono", "Fira Code", "Source Code Pro", 
            "Consolas", "Courier New", "Monaco", "Menlo", 
            "DejaVu Sans Mono", "Liberation Mono", "Segoe UI", "Roboto", "Inter", "Ubuntu"
        ]
        
        all_families = QFontDatabase.families()
        
        # Add priority fonts that are available
        available_priority = [f for f in priority_fonts if f in all_families]
        target_combo.addItems(available_priority)
        
        # Add all other fonts
        other_fonts = [f for f in all_families if f not in available_priority]
        target_combo.addItems(sorted(other_fonts))
        
        if current_text in all_families:
            target_combo.setCurrentText(current_text)
        else:
            # Fallback based on setting if generic
            setting_key = "ui_font_family" if target_combo == getattr(self, 'ui_font_family_combo', None) else "font_family"
            default_font = settings.get_setting(setting_key, settings.get_default(setting_key))
            if default_font in all_families:
                target_combo.setCurrentText(default_font)
            elif target_combo.count() > 0:
                target_combo.setCurrentIndex(0)
            
        target_combo.blockSignals(False)

    def on_add_font_file(self):
        """Open a file dialog to add a new font file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Font File",
            "",
            "Font Files (*.ttf *.otf *.woff2 *.woff);;All Files (*)"
        )
        
        if not file_path:
            return
            
        path = Path(file_path)
        from app.portable_data import get_fonts_dir
        fonts_dir = get_fonts_dir()
        dest_path = fonts_dir / path.name
        
        try:
            # Copy file to data directory
            if not dest_path.exists() or dest_path.resolve() != path.resolve():
                shutil.copy2(file_path, dest_path)
            
            # Register font
            font_id = QFontDatabase.addApplicationFont(str(dest_path))
            if font_id == -1:
                QMessageBox.warning(self, "Font Error", f"Failed to load font: {path.name}\nIt might be an unsupported format.")
                return
                
            # Get font families from this file
            families = QFontDatabase.applicationFontFamilies(font_id)
            if not families:
                QMessageBox.warning(self, "Font Error", "Loaded font has no families?")
                return
                
            family_name = families[0]
            
            # Update settings
            import json
            custom_fonts_raw = settings.get_setting("custom_fonts", "[]")
            try:
                custom_fonts = json.loads(custom_fonts_raw)
            except:
                custom_fonts = []
                
            if path.name not in custom_fonts:
                custom_fonts.append(path.name)
                settings.set_setting("custom_fonts", json.dumps(custom_fonts))
            
            # Refresh UI
            if hasattr(self, 'font_family_combo'):
                self._populate_font_families(self.font_family_combo)
            if hasattr(self, 'ui_font_family_combo'):
                self._populate_font_families(self.ui_font_family_combo)
                
            # For now, apply to editor if that's what user likely expects
            if hasattr(self, 'font_family_combo'):
                self.font_family_combo.setCurrentText(family_name)
                self.on_font_family_changed(family_name)
            
            QMessageBox.information(self, "Font Added", f"Successfully added font: {family_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add font: {e}")
    
    def _load_sound_profiles(self):
        """Load sound profiles into combo box."""
        from app.sound_manager import get_sound_manager
        manager = get_sound_manager()
        
        self.sound_profile_combo.clear()
        self.sound_profile_combo.addItem("No Sound", "none")
        
        all_profiles = manager.get_all_profiles()
        for profile_id, profile_data in all_profiles.items():
            if profile_id != "none":
                name = profile_data["name"]
                self.sound_profile_combo.addItem(name, profile_id)
    
    def _update_sound_enabled_buttons(self, enabled: bool):
        """Update sound enabled/disabled button states."""
        active_style = (
            "background-color: #5e81ac; color: white; border: none; border-radius: 6px;"
            " font-weight: bold;"
        )
        inactive_style = (
            "background-color: #3b4252; color: #d8dee9; border: 1px solid #434c5e; border-radius: 6px;"
        )
        
        self.sound_enabled_btn.setChecked(enabled)
        self.sound_disabled_btn.setChecked(not enabled)
        
        self.sound_enabled_btn.setStyleSheet(active_style if enabled else inactive_style)
        self.sound_disabled_btn.setStyleSheet(active_style if not enabled else inactive_style)
    
    def _handle_show_ghost_text_button(self, enabled: bool):
        """Handle clicks on the show-ghost-text buttons."""
        self._update_show_ghost_text_buttons(enabled)
        settings.set_setting("show_ghost_text", "1" if enabled else "0")
        self.show_ghost_text_changed.emit(enabled)

    def _update_instant_death_buttons(self, enabled: bool):
        """Refresh the button styles for the instant-death setting."""
        if not hasattr(self, 'instant_death_enabled_btn'): return
        
        active_style = (
            "background-color: #5e81ac; color: white; border: none; border-radius: 6px;"
            " font-weight: bold;"
        )
        inactive_style = (
            "background-color: #3b4252; color: #d8dee9; border: 1px solid #434c5e; border-radius: 6px;"
        )
        
        self.instant_death_enabled_btn.setChecked(enabled)
        self.instant_death_disabled_btn.setChecked(not enabled)
        
        self.instant_death_enabled_btn.setStyleSheet(active_style if enabled else inactive_style)
        self.instant_death_disabled_btn.setStyleSheet(active_style if not enabled else inactive_style)

    def _handle_instant_death_button(self, enabled: bool):
        """Handle clicks on the instant-death buttons."""
        settings.set_setting("instant_death_mode", "1" if enabled else "0")
        self._update_instant_death_buttons(enabled)
        self.instant_death_changed.emit(enabled)

    def _handle_pb_pos_changed(self, index):
        """Handle progress bar position change."""
        pos = self.pb_pos_combo.itemData(index)
        if pos:
            settings.set_setting("progress_bar_pos", pos)
            self.progress_bar_pos_changed.emit(pos)

    def _handle_stats_pos_changed(self, index):
        """Handle stats display position change."""
        pos = self.stats_pos_combo.itemData(index)
        if pos:
            settings.set_setting("stats_display_pos", pos)
            self.stats_display_pos_changed.emit(pos)

    def _handle_sound_enabled_button(self, enabled: bool):
        """Handle sound enabled/disabled button clicks."""
        self._update_sound_enabled_buttons(enabled)
        settings.set_setting("sound_enabled", "1" if enabled else "0")
        
        from app.sound_manager import get_sound_manager
        get_sound_manager().set_enabled(enabled)
        self.sound_enabled_changed.emit(enabled)
    
    def on_sound_profile_changed(self, index):
        """Handle sound profile selection change."""
        profile_id = self.sound_profile_combo.itemData(index)
        if profile_id:
            settings.set_setting("sound_profile", profile_id)
            
            from app.sound_manager import get_sound_manager
            sound_mgr = get_sound_manager()
            sound_mgr.set_profile(profile_id)
            
            # Check for loading errors and show tooltip
            error = sound_mgr.get_last_error()
            if error:
                self.sound_profile_combo.setToolTip(f"⚠️ {error}")
            else:
                self.sound_profile_combo.setToolTip("")
    
    def _test_current_sound(self):
        """Play the currently selected sound for testing."""
        from app.sound_manager import get_sound_manager
        sound_mgr = get_sound_manager()
        sound_mgr.play_keypress()

    def on_manage_sound_profiles(self):
        """Open sound manager dialog."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QMessageBox
        from app.sound_profile_editor import SoundProfileEditor
        from app.sound_manager import get_sound_manager
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Sounds")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Profile list
        profile_list = QListWidget()
        manager = get_sound_manager()
        all_profiles = manager.get_all_profiles()
        for profile_id, profile_data in all_profiles.items():
            if profile_id != "none":  # Don't show "No Sound" in manager
                name = profile_data["name"]
                builtin = profile_data.get("builtin", False)
                label = f"{name} {'(Built-in)' if builtin else '(Custom)'}"
                profile_list.addItem(label)
                profile_list.item(profile_list.count() - 1).setData(Qt.UserRole, profile_id)
        layout.addWidget(profile_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        new_btn = QPushButton("New Sound...")
        def create_new():
            editor = SoundProfileEditor(parent=dialog)
            if editor.exec() == QDialog.Accepted:
                # Refresh list and combo
                profile_list.clear()
                all_profiles = manager.get_all_profiles()
                for pid, pdata in all_profiles.items():
                    if pid != "none":
                        label = f"{pdata['name']} {'(Built-in)' if pdata.get('builtin', False) else '(Custom)'}"
                        profile_list.addItem(label)
                        profile_list.item(profile_list.count() - 1).setData(Qt.UserRole, pid)
                self._load_sound_profiles()
        new_btn.clicked.connect(create_new)
        btn_layout.addWidget(new_btn)
        
        edit_btn = QPushButton("Edit...")
        def edit_selected():
            current = profile_list.currentItem()
            if not current:
                QMessageBox.warning(dialog, "No Selection", "Please select a sound to edit.")
                return
            profile_id = current.data(Qt.UserRole)
            # We now allow editing built-ins (creates a custom override)
            editor = SoundProfileEditor(profile_id, parent=dialog)
            if editor.exec() == QDialog.Accepted:
                # Refresh list
                profile_list.clear()
                all_profiles = manager.get_all_profiles()
                for pid, pdata in all_profiles.items():
                    if pid != "none":
                        label = f"{pdata['name']} {'(Built-in)' if pdata.get('builtin', False) else '(Custom)'}"
                        profile_list.addItem(label)
                        profile_list.item(profile_list.count() - 1).setData(Qt.UserRole, pid)
                self._load_sound_profiles()
        edit_btn.clicked.connect(edit_selected)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete")
        def delete_selected():
            current = profile_list.currentItem()
            if not current:
                QMessageBox.warning(dialog, "No Selection", "Please select a sound to delete.")
                return
            profile_id = current.data(Qt.UserRole)
            is_builtin = manager.get_all_profiles()[profile_id].get("builtin", False)
            has_custom = profile_id in manager.custom_profiles
            
            if is_builtin and not has_custom:
                QMessageBox.warning(dialog, "Cannot Delete", "The original built-in sound cannot be deleted.")
                return
            
            confirm_msg = f"Delete custom override for '{current.text().split(' (')[0]}' and revert to built-in?" if has_custom and is_builtin else f"Delete sound '{current.text().split(' (')[0]}'?"
            reply = QMessageBox.question(dialog, "Confirm Delete", confirm_msg)
            if reply == QMessageBox.Yes:
                if manager.delete_custom_profile(profile_id):
                    profile_list.takeItem(profile_list.currentRow())
                    self._load_sound_profiles()
                    QMessageBox.information(dialog, "Success", "Sound deleted.")
                else:
                    QMessageBox.critical(dialog, "Error", "Failed to delete sound.")
        delete_btn.clicked.connect(delete_selected)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        dialog.exec()

    def on_best_wpm_accuracy_changed(self, percent: int):
        clamped = max(0, min(100, int(percent)))
        ratio = clamped / 100.0
        settings.set_setting("best_wpm_min_accuracy", f"{ratio:.4f}")
    
    def on_change_data_directory(self):
        """Allow user to select a new data directory location."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        
        # Get current directory
        try:
            from app.portable_data import get_data_dir, get_data_manager
            current_dir = str(get_data_dir())
        except:
            current_dir = str(settings.get_data_dir())
        
        # Open directory picker
        new_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Data Directory",
            current_dir,
            QFileDialog.ShowDirsOnly
        )
        
        if new_dir:
            # Confirm with user
            reply = QMessageBox.question(
                self,
                "Change Data Directory",
                f"Change data directory to:\n\n{new_dir}\n\n"
                "The new directory will be created with the required structure. "
                "You may need to restart the application for all changes to take effect.\n\n"
                "Continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    from app.portable_data import get_data_manager
                    manager = get_data_manager()
                    
                    if manager.set_data_directory(Path(new_dir)):
                        self.data_dir_display.setText(new_dir)
                        QMessageBox.information(
                            self,
                            "Success",
                            "Data directory changed successfully!\n\n"
                            "Please restart the application for all changes to take effect."
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "Error",
                            "Failed to set data directory. Please ensure the path is valid."
                        )
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to change data directory: {e}")
    
    def on_reset_data_directory(self):
        """Reset data directory to default location."""
        from PySide6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            "Reset Data Directory",
            "Reset data directory to default location (next to executable)?\n\n"
            "You may need to restart the application for all changes to take effect.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                from app.portable_data import get_data_manager
                manager = get_data_manager()
                
                if manager.reset_to_default_directory():
                    new_dir = str(manager.data_dir)
                    self.data_dir_display.setText(new_dir)
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Data directory reset to:\n{new_dir}\n\n"
                        "Please restart the application for all changes to take effect."
                    )
                else:
                    QMessageBox.warning(self, "Error", "Failed to reset data directory.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to reset data directory: {e}")
    
    def apply_current_theme(self):
        """Apply the current theme settings to the entire application."""
        if DEBUG_STARTUP_TIMING:
            import time
            t_total = time.time()
        
        from app.themes import get_color_scheme, apply_theme_to_app
        
        # Get current theme settings
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        
        # Get the color scheme (always dark mode)
        scheme = get_color_scheme("dark", scheme_name)
        
        # Apply to application
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        app = QApplication.instance()
        if app:
            apply_theme_to_app(app, scheme)
        if DEBUG_STARTUP_TIMING:
            print(f"  [THEME] apply_theme_to_app: {time.time() - t:.3f}s")
        
        # Update typing area colors if editor tab is initialized
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        if hasattr(self, 'editor_tab'):
            self.editor_tab.apply_theme()
            if hasattr(self.editor_tab, 'typing_area'):
                self.update_typing_colors(scheme)
                # Re-apply font settings as global stylesheet might have overridden them
                self._emit_font_changed()
        if DEBUG_STARTUP_TIMING:
            print(f"  [THEME] update_typing_colors: {time.time() - t:.3f}s")
        
        # Update specific tabs
        if hasattr(self, 'folders_tab') and hasattr(self.folders_tab, 'apply_theme'):
            self.folders_tab.apply_theme()
            
        if hasattr(self, 'languages_tab') and hasattr(self.languages_tab, 'apply_theme'):
            self.languages_tab.apply_theme()
            
        if hasattr(self, 'history_tab') and not isinstance(self.history_tab, QLabel) and hasattr(self.history_tab, 'apply_theme'):
            self.history_tab.apply_theme()
            
        if hasattr(self, 'stats_tab') and not isinstance(self.stats_tab, QLabel) and hasattr(self.stats_tab, 'apply_theme'):
            self.stats_tab.apply_theme()
            
        if hasattr(self, 'profile_trigger') and hasattr(self.profile_trigger, 'apply_theme'):
            self.profile_trigger.apply_theme()
        
        if hasattr(self, 'shortcuts_tab') and hasattr(self.shortcuts_tab, 'apply_theme'):
            self.shortcuts_tab.apply_theme()
            
        if not isinstance(self.settings_tab, QLabel):
            self.update_color_buttons_from_theme()

        self._update_ignore_inputs_style(scheme)

        # Update tab icons (ensures icons match theme colors)
        self.tabs.setTabIcon(self.tabs.indexOf(self.folders_tab), get_icon("FOLDER"))
        self.tabs.setTabIcon(self.tabs.indexOf(self.languages_tab), get_icon("CODE"))
        self.tabs.setTabIcon(self.tabs.indexOf(self.history_tab), get_icon("CLOCK"))
        self.tabs.setTabIcon(self.tabs.indexOf(self.stats_tab), get_icon("CHART"))
        self.tabs.setTabIcon(self.tabs.indexOf(self.editor_tab), get_icon("TYPING"))
        self.tabs.setTabIcon(self.tabs.indexOf(self.settings_tab), get_icon("SETTINGS"))
        self.tabs.setTabIcon(self.tabs.indexOf(self.shortcuts_tab), get_icon("KEYBOARD"))

        if DEBUG_STARTUP_TIMING:
            print(f"  [THEME] TOTAL apply_current_theme: {time.time() - t_total:.3f}s")
        
        self.colors_changed.emit()
    
    def update_typing_colors(self, scheme):
        """Update typing area highlighter colors from scheme."""
        typing_area = self.editor_tab.typing_area
        if typing_area.highlighter:
            from PySide6.QtGui import QColor
            
            # Update highlighter colors
            typing_area.highlighter.untyped_format.setForeground(QColor(scheme.text_untyped))
            typing_area.highlighter.correct_format.setForeground(QColor(scheme.text_correct))
            typing_area.highlighter.incorrect_format.setForeground(QColor(scheme.text_incorrect))
            
            # Trigger rehighlight to apply changes
            typing_area.highlighter.rehighlight()

    def _update_ignore_inputs_style(self, scheme):
        """Update styles for the ignored files/folders input areas."""
        if not hasattr(self, 'ignored_files_edit') or not hasattr(self, 'ignored_folders_edit'):
            return
            
        style = f"""
            QTextEdit {{
                background-color: {scheme.bg_secondary};
                color: {scheme.text_primary};
                border: 1px solid {scheme.border_color};
                border-radius: 4px;
                padding: 4px;
            }}
            QTextEdit:focus {{
                border: 1px solid {scheme.accent_color};
                background-color: {scheme.bg_tertiary};
            }}
        """
        
        if self.ignored_files_edit:
            self.ignored_files_edit.setStyleSheet(style)
        if self.ignored_folders_edit:
            self.ignored_folders_edit.setStyleSheet(style)
    
    def update_color_buttons_from_theme(self):
        """Update color picker button displays and labels to reflect theme colors."""
        if not hasattr(self, 'color_buttons'):
            return
            
        from app.themes import get_color_scheme, is_builtin_theme
        
        # Get current theme settings
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        
        # Update Section Title
        if hasattr(self, 'theme_settings_title'):
            self.theme_settings_title.setText(f"THEME SETTINGS: {scheme_name.upper()}")
        
        # Get scheme object
        self.working_scheme = get_color_scheme("dark", scheme_name)
        
        # Update swatches and text labels
        for key, btn in self.color_buttons.items():
            if hasattr(self.working_scheme, key):
                col = getattr(self.working_scheme, key)
                # Update circular swatch style
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {col};
                        border-radius: 11px;
                        border: 1px solid rgba(255, 255, 255, 0.15);
                    }}
                    QPushButton:hover {{
                        border: 1px solid rgba(255, 255, 255, 0.4);
                    }}
                """)
                # Update hex label text
                if key in self.color_hex_labels:
                    self.color_hex_labels[key].setText(col.upper())
        
        # Update Reset Button State
        is_builtin = is_builtin_theme("dark", scheme_name)
        if is_builtin:
             self.btn_reset_theme.setEnabled(False)
             self.btn_reset_theme.setToolTip("Current theme is at default values.")
        else:
             self.btn_reset_theme.setEnabled(True)
             self.btn_reset_theme.setToolTip("Delete custom modifications for this theme.")
             
        # Update Save Button
        self.btn_save_theme.setStyleSheet("background-color: #44475a; color: white; border: none; padding: 8px 20px;")
        self._colors_dirty = False
    
    def refresh_settings_ui(self):
        """Refresh all settings UI controls to match imported settings."""
        scheme = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        self.scheme_combo.setCurrentText(scheme)
        
        # Cursor settings
        cursor_type = settings.get_setting("cursor_type", settings.get_default("cursor_type"))
        self._update_cursor_type_buttons(cursor_type)
        
        cursor_style = settings.get_setting("cursor_style", settings.get_default("cursor_style"))
        self._update_cursor_style_buttons(cursor_style)
        
        # Font settings
        self._populate_font_families(self.font_family_combo)
        font_family = settings.get_setting("font_family", settings.get_default("font_family"))
        self.font_family_combo.setCurrentText(font_family)
        
        font_size = settings.get_setting_int("font_size", 12, min_val=8, max_val=48)
        self.font_size_spin.setValue(font_size)
        
        # UI Font settings
        self._populate_font_families(self.ui_font_family_combo)
        ui_font_family = settings.get_setting("ui_font_family", settings.get_default("ui_font_family"))
        self.ui_font_family_combo.setCurrentText(ui_font_family)
        
        ui_font_size = settings.get_setting_int("ui_font_size", 10, min_val=8, max_val=24)
        self.ui_font_size_spin.setValue(ui_font_size)
        
        # Typing settings
        space_char = settings.get_setting("space_char", settings.get_default("space_char"))
        if space_char in ["␣", "·", " "]:
            self.space_char_combo.setCurrentText(space_char)
        else:
            self.space_char_combo.setCurrentText("custom")
            self.space_char_custom.setText(space_char)
        
        pause_delay = int(float(settings.get_setting("pause_delay", settings.get_default("pause_delay"))))
        self.pause_delay_spin.setValue(pause_delay)
        
        # Typing behavior
        confirm_del = settings.get_setting("delete_confirm", settings.get_default("delete_confirm"))
        self._update_confirm_del_buttons(confirm_del == "1")
        
        allow_continue = settings.get_setting("allow_continue_mistakes", settings.get_default("allow_continue_mistakes"))
        self._update_allow_continue_buttons(allow_continue == "1")
        show_typed_state = settings.get_setting("show_typed_characters", settings.get_default("show_typed_characters")) == "1"
        self._update_show_typed_buttons(show_typed_state)
        show_ghost_state = settings.get_setting("show_ghost_text", settings.get_default("show_ghost_text")) == "1"
        self._update_show_ghost_text_buttons(show_ghost_state)
        auto_indent_state = settings.get_setting("auto_indent", settings.get_default("auto_indent")) == "1"
        self._update_auto_indent_buttons(auto_indent_state)
        
        # Global Exclusion settings
        if hasattr(self, 'ignored_files_edit'):
            self.ignored_files_edit.setText(settings.get_setting("ignored_files", settings.get_default("ignored_files")))
        if hasattr(self, 'ignored_folders_edit'):
            self.ignored_folders_edit.setText(settings.get_setting("ignored_folders", settings.get_default("ignored_folders")))

        # Interface Layout settings
        if hasattr(self, 'pb_pos_combo'):
            pb_pos = settings.get_setting("progress_bar_pos", settings.get_default("progress_bar_pos"))
            index = self.pb_pos_combo.findData(pb_pos)
            if index >= 0:
                self.pb_pos_combo.blockSignals(True)
                self.pb_pos_combo.setCurrentIndex(index)
                self.pb_pos_combo.blockSignals(False)

        if hasattr(self, 'stats_pos_combo'):
            stats_pos = settings.get_setting("stats_display_pos", settings.get_default("stats_display_pos"))
            index = self.stats_pos_combo.findData(stats_pos)
            if index >= 0:
                self.stats_pos_combo.blockSignals(True)
                self.stats_pos_combo.setCurrentIndex(index)
                self.stats_pos_combo.blockSignals(False)
    
    def _emit_all_settings_signals(self):
        """Emit all settings signals to update connected components."""
        # Font settings
        self._emit_font_changed()
        
        # Color settings
        self.colors_changed.emit()
        
        # Cursor settings
        cursor_type = settings.get_setting("cursor_type", settings.get_default("cursor_type"))
        cursor_style = settings.get_setting("cursor_style", settings.get_default("cursor_style"))
        self.cursor_changed.emit(cursor_type, cursor_style)
        
        # Space character
        space_char = settings.get_setting("space_char", settings.get_default("space_char"))
        self.space_char_changed.emit(space_char)
        
        # Pause delay
        pause_delay = float(settings.get_setting("pause_delay", settings.get_default("pause_delay")))
        self.pause_delay_changed.emit(pause_delay)
        
        # Allow continue with mistakes
        allow_continue = settings.get_setting("allow_continue_mistakes", settings.get_default("allow_continue_mistakes")) == "1"
        self.allow_continue_changed.emit(allow_continue)

        # Show typed characters
        show_typed = settings.get_setting("show_typed_characters", settings.get_default("show_typed_characters")) == "1"
        self.show_typed_changed.emit(show_typed)

        # Show ghost text
        show_ghost = settings.get_setting("show_ghost_text", settings.get_default("show_ghost_text")) == "1"
        self.show_ghost_text_changed.emit(show_ghost)
        
        # Ignored patterns
        self.ignored_patterns_changed.emit()

    def _connect_settings_signals(self):
        """Connect settings change signals to editor tab for dynamic updates."""
        if hasattr(self.editor_tab, 'typing_area'):
            self.font_changed.connect(self.editor_tab.typing_area.update_font)
            self.colors_changed.connect(self.editor_tab.typing_area.update_colors)
            self.cursor_changed.connect(self.editor_tab.typing_area.update_cursor)
            self.space_char_changed.connect(self.editor_tab.typing_area.update_space_char)
            self.tab_width_changed.connect(self.editor_tab.typing_area.update_tab_width)
            self.pause_delay_changed.connect(self.editor_tab.typing_area.update_pause_delay)
            self.allow_continue_changed.connect(self.editor_tab.typing_area.update_allow_continue)
            self.show_typed_changed.connect(self.editor_tab.typing_area.update_show_typed_characters)
            self.show_ghost_text_changed.connect(self.editor_tab.typing_area.update_show_ghost_text)
            self.ignored_patterns_changed.connect(self.editor_tab.update_ignore_settings)
        
            # Connect progress bar color updates
            self.colors_changed.connect(self.editor_tab.update_progress_bar_color)
            
            # Connect layout position updates
            self.progress_bar_pos_changed.connect(self.editor_tab.update_layout)
            self.stats_display_pos_changed.connect(self.editor_tab.update_layout)
            
            # Connect Instant Death and Auto Indent (Bidirectional sync)
            self.instant_death_changed.connect(lambda enabled: self.editor_tab._set_instant_death_mode(enabled, persist=False))
            self.auto_indent_changed.connect(lambda enabled: self.editor_tab._set_auto_indent(enabled, persist=False))
            
            self.editor_tab.toggle_instant_death_requested.connect(self._handle_instant_death_button)
            self.editor_tab.toggle_smart_indent_requested.connect(self._handle_auto_indent_button)
            
            # Additional UI sync
            self.sound_enabled_changed.connect(self.editor_tab.sound_widget.set_enabled)
            self.colors_changed.connect(self.editor_tab.apply_theme)
    
    def _emit_initial_settings(self):
        """Emit initial settings to apply them immediately after connection."""
        # Font settings
        family = settings.get_setting("font_family", settings.get_default("font_family"))
        size = int(settings.get_setting("font_size", settings.get_default("font_size")))
        self.font_changed.emit(family, size, False)  # Ligatures removed, always False
        
        # Color settings
        self.colors_changed.emit()
        
        # Cursor settings
        cursor_type = settings.get_setting("cursor_type", settings.get_default("cursor_type"))
        cursor_style = settings.get_setting("cursor_style", settings.get_default("cursor_style"))
        self.cursor_changed.emit(cursor_type, cursor_style)
        
        # Update preview timer state
        if cursor_type == "blinking":
            if hasattr(self, '_settings_cursor_timer') and not self._settings_cursor_timer.isActive():
                self._settings_cursor_timer.start()
        else:
            if hasattr(self, '_settings_cursor_timer'):
                self._settings_cursor_timer.stop()
                if hasattr(self, 'cursor_preview_widgets'):
                    for _, widget in self.cursor_preview_widgets:
                        widget.setVisible(True)
        
        # Space character
        space_char = settings.get_setting("space_char", settings.get_default("space_char"))
        self.space_char_changed.emit(space_char)
        
        # Pause delay
        pause_delay = float(settings.get_setting("pause_delay", settings.get_default("pause_delay")))
        self.pause_delay_changed.emit(pause_delay)
        
        # Allow continue with mistakes
        allow_continue = settings.get_setting("allow_continue_mistakes", settings.get_default("allow_continue_mistakes")) == "1"
        self._update_allow_continue_buttons(allow_continue)
        self.allow_continue_changed.emit(allow_continue)

        # Show typed characters
        show_typed = settings.get_setting("show_typed_characters", settings.get_default("show_typed_characters")) == "1"
        self._update_show_typed_buttons(show_typed)
        self.show_typed_changed.emit(show_typed)

        # Show ghost text
        show_ghost = settings.get_setting("show_ghost_text", settings.get_default("show_ghost_text")) == "1"
        self._update_show_ghost_text_buttons(show_ghost)
        self.show_ghost_text_changed.emit(show_ghost)
        
        # UI Layout settings
        pb_pos = settings.get_setting("progress_bar_pos", settings.get_default("progress_bar_pos"))
        self.progress_bar_pos_changed.emit(pb_pos)
        
        stats_pos = settings.get_setting("stats_display_pos", settings.get_default("stats_display_pos"))
        self.stats_display_pos_changed.emit(stats_pos)

    def on_ignored_extensions_changed(self, text: str):
        """Deprecated: Logic moved to _save_ignore_settings."""
        pass

    def _apply_ignore_extensions(self):
        """Apply ignored extensions and refresh UI."""
        # Note: LanguagesTab and FoldersTab will re-scan if their refresh() or load_folders() is called
        if hasattr(self, 'folders_tab'):
            self.folders_tab.load_folders()
            
        if hasattr(self, 'languages_tab'):
            self.languages_tab.ensure_loaded(force=True)
            
        if hasattr(self, 'stats_tab') and not isinstance(self.stats_tab, QLabel):
            self.stats_tab.refresh()




    def start_profile_transition(self, target_profile: str):
        """Start the high-fidelity focus-switch transition."""
        if target_profile == self.pm.get_active_profile():
            return
            
        # Get image for overlay
        all_p = self.pm.get_all_profiles()
        p_data = next((p for p in all_p if p["name"] == target_profile), None)
        img_path = p_data["image"] if p_data else None
        
        # 1. Prepare Proxy with Screenshot of CURRENT state
        QApplication.processEvents() # Ensure rendering is current
        screenshot = self.content_container.grab()
        self.proxy_label.setPixmap(screenshot)
        self.proxy_label.resize(self.content_container.size())
        self.proxy_label.show()
        self.proxy_label.raise_() # Ensure it sits above content
        
        # 2. Blur Animation (0 -> 20px) on PROXY
        self.blur_anim = QPropertyAnimation(self.blur_effect, b"blurRadius")
        self.blur_anim.setDuration(400)
        self.blur_anim.setStartValue(0)
        self.blur_anim.setEndValue(20)
        self.blur_anim.setEasingCurve(QEasingCurve.OutQuad)
        self.blur_anim.start()
        
        # 3. Start Overlay
        self.transition_overlay.start_transition(
            target_profile, 
            img_path, 
            lambda: self._finish_profile_switch(target_profile)
        )

    def _finish_profile_switch(self, target_profile: str):
        """Called when overlay animation completes."""
        # 4. Data Swap (In-Place)
        self.switch_profile(target_profile)
        
        # Force layout update to ensure new theme/data is rendered
        QApplication.processEvents()
        
        # 5. Capture NEW state for unblurring
        # We need to make sure content_container has updated its look
        screenshot = self.content_container.grab()
        self.proxy_label.setPixmap(screenshot)
        
        # 6. Reverse Blur (20 -> 0px)
        self.unblur_anim = QPropertyAnimation(self.blur_effect, b"blurRadius")
        self.unblur_anim.setDuration(400)
        self.unblur_anim.setStartValue(20)
        self.unblur_anim.setEndValue(0)
        self.unblur_anim.setEasingCurve(QEasingCurve.InQuad)
        
        # Hide BOTH proxy and overlay when done
        self.unblur_anim.finished.connect(self.proxy_label.hide)
        self.unblur_anim.finished.connect(self.transition_overlay.hide)
        
        self.unblur_anim.start()
        
        # 7. Switch to Folders Tab (index 0)
        self.tabs.setCurrentIndex(0)

    def open_profile_manager(self):
        """Open the profile manager dialog."""
        dialog = ProfileManagerDialog(parent=self)
        
        # Variable to capture selection
        selection = {"name": None}
        
        def on_selected(name):
            selection["name"] = name
            
        dialog.profile_selected.connect(on_selected)
        dialog.exec()
        
        if selection["name"]:
            self.start_profile_transition(selection["name"])
        
    def _on_profile_updated(self, name):
        """Handle profile information (name/image) updates."""
        # Only update if it's the active profile
        if name == self.pm.get_active_profile():
            # Re-initialize DB path because the folder name might have changed
            db_path = self.pm.get_current_db_path()
            settings.init_db(str(db_path))

            all_profiles = self.pm.get_all_profiles()
            p_data = next((p for p in all_profiles if p["name"] == name), None)
            img_path = p_data["image"] if p_data else None
            self.profile_trigger.update_profile(name, img_path)
            logger.info(f"Active profile updated: {name}. DB path refreshed.")

    def switch_profile(self, name):
        """Switch profile and reload data in-place."""
        if name == self.pm.get_active_profile():
            return
            
        # 1. Switch Backend & DB
        self.pm.switch_profile(name)
        db_path = self.pm.get_current_db_path()
        settings.init_db(str(db_path))
        
        # 2. Update Profile Trigger
        all_profiles = self.pm.get_all_profiles()
        p_data = next((p for p in all_profiles if p["name"] == name), None)
        img_path = p_data["image"] if p_data else None
        self.profile_trigger.update_profile(name, img_path)
        
        # 3. Reload Managers
        from app.ghost_manager import get_ghost_manager
        from app.sound_manager import get_sound_manager
        get_ghost_manager().refresh()
        get_sound_manager().refresh()

        # 4. Reload Tabs
        
        # Folders
        if hasattr(self, 'folders_tab'):
            self.folders_tab.load_folders()
            
        # Languages
        if hasattr(self, 'languages_tab'):
            self.languages_tab.ensure_loaded(force=True)
            
        # History
        if hasattr(self, 'history_tab') and not isinstance(self.history_tab, QLabel):
            if hasattr(self.history_tab, 'refresh'):
                self.history_tab.refresh()
            else:
                # Reset to lazy state if refresh not supported
                # For now just assume it handles itself or user won't notice until click
                pass

        # Stats
        if hasattr(self, 'stats_tab') and not isinstance(self.stats_tab, QLabel):
            if hasattr(self.stats_tab, 'refresh'):
                self.stats_tab.refresh()
                
        # Settings - Reload values from new DB
        if hasattr(self, 'settings_tab'):
            # Reset Settings Tab UI State
            if hasattr(self, 'settings_search_input'):
                self.settings_search_input.clear()
            if hasattr(self, 'settings_scroll_area'):
                self.settings_scroll_area.verticalScrollBar().setValue(0)
                
            # Refresh all toggle button states from new profile's settings
            auto_indent_state = settings.get_setting("auto_indent", settings.get_default("auto_indent")) == "1"
            self._update_auto_indent_buttons(auto_indent_state)
            
            allow_continue_state = settings.get_setting("allow_continue_mistakes", settings.get_default("allow_continue_mistakes")) == "1"
            self._update_allow_continue_buttons(allow_continue_state)
            
            show_typed_state = settings.get_setting("show_typed_characters", settings.get_default("show_typed_characters")) == "1"
            self._update_show_typed_buttons(show_typed_state)
            
            show_ghost_state = settings.get_setting("show_ghost_text", settings.get_default("show_ghost_text")) == "1"
            self._update_show_ghost_text_buttons(show_ghost_state)
            
            instant_death_state = settings.get_setting("instant_death_mode", settings.get_default("instant_death_mode")) == "1"
            self._update_instant_death_buttons(instant_death_state)
            
            sound_enabled_state = settings.get_setting("sound_enabled", settings.get_default("sound_enabled")) == "1"
            self._update_sound_enabled_buttons(sound_enabled_state)
            
            confirm_del_state = settings.get_setting("delete_confirm", settings.get_default("delete_confirm")) == "1"
            self._update_confirm_del_buttons(confirm_del_state)

        # 4. Refresh Editor Settings & THEME
        self.apply_current_theme() # Apply theme for the new profile
        self._emit_initial_settings()

        # Update scheme combo box to reflect new profile's theme
        if hasattr(self, 'scheme_combo'):
            current_scheme = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
            index = self.scheme_combo.findText(current_scheme)
            if index >= 0:
                self.scheme_combo.blockSignals(True)
                self.scheme_combo.setCurrentIndex(index)
                self.scheme_combo.blockSignals(False)
        
        # 5. Reset Editor Session if needed
        # The editor logic listens to settings changes, so it should be fine.

    def _update_allow_continue_buttons(self, enabled: bool):
        """Refresh the button styles for the allow-continue setting."""
        if not hasattr(self, 'allow_continue_enabled_btn'):
            return
        active_style = (
            "background-color: #5e81ac; color: white; border: none; border-radius: 6px;"
            " font-weight: bold;"
        )
        inactive_style = (
            "background-color: #3b4252; color: #d8dee9; border: 1px solid #434c5e; border-radius: 6px;"
        )
        self.allow_continue_enabled_btn.setChecked(enabled)
        self.allow_continue_disabled_btn.setChecked(not enabled)
        self.allow_continue_enabled_btn.setStyleSheet(active_style if enabled else inactive_style)
        self.allow_continue_disabled_btn.setStyleSheet(active_style if not enabled else inactive_style)

    def _update_confirm_del_buttons(self, enabled: bool):
        """Refresh the button styles for the confirm-deletion setting."""
        if not hasattr(self, 'confirm_del_enabled_btn'):
            return
        active_style = (
            "background-color: #5e81ac; color: white; border: none; border-radius: 6px;"
            " font-weight: bold;"
        )
        inactive_style = (
            "background-color: #3b4252; color: #d8dee9; border: 1px solid #434c5e; border-radius: 6px;"
        )
        self.confirm_del_enabled_btn.setChecked(enabled)
        self.confirm_del_disabled_btn.setChecked(not enabled)
        self.confirm_del_enabled_btn.setStyleSheet(active_style if enabled else inactive_style)
        self.confirm_del_disabled_btn.setStyleSheet(active_style if not enabled else inactive_style)

    def _handle_confirm_del_button(self, enabled: bool):
        """Handle clicks on the confirm-deletion buttons."""
        current = settings.get_setting("delete_confirm", settings.get_default("delete_confirm")) == "1"
        if current == enabled:
            self._update_confirm_del_buttons(enabled)
            return
        settings.set_setting("delete_confirm", "1" if enabled else "0")
        self._update_confirm_del_buttons(enabled)
    
    def _handle_retention_changed(self):
        """Handle changes to the history retention period."""
        if not hasattr(self, 'retention_combo'):
            return
        days = self.retention_combo.currentData()
        if days is not None:
            settings.set_setting("history_retention_days", str(days))

    def _handle_allow_continue_button(self, enabled: bool):
        """Handle clicks on the allow-continue buttons."""
        current = settings.get_setting("allow_continue_mistakes", settings.get_default("allow_continue_mistakes")) == "1"
        if current == enabled:
            # Still ensure buttons reflect state
            self._update_allow_continue_buttons(enabled)
            return
        settings.set_setting("allow_continue_mistakes", "1" if enabled else "0")
        self._update_allow_continue_buttons(enabled)
        self.allow_continue_changed.emit(enabled)

    def _update_show_typed_buttons(self, enabled: bool):
        """Refresh the button styles for the show-typed setting."""
        if not hasattr(self, 'show_typed_enabled_btn'):
            return
        active_style = (
            "background-color: #5e81ac; color: white; border: none; border-radius: 6px;"
            " font-weight: bold;"
        )
        inactive_style = (
            "background-color: #3b4252; color: #d8dee9; border: 1px solid #434c5e; border-radius: 6px;"
        )
        self.show_typed_enabled_btn.setChecked(enabled)
        self.show_typed_disabled_btn.setChecked(not enabled)
        self.show_typed_enabled_btn.setStyleSheet(active_style if enabled else inactive_style)
        self.show_typed_disabled_btn.setStyleSheet(active_style if not enabled else inactive_style)

    def _handle_show_typed_button(self, enabled: bool):
        """Handle clicks on the show-typed buttons."""
        current = settings.get_setting("show_typed_characters", settings.get_default("show_typed_characters")) == "1"
        if current == enabled:
            self._update_show_typed_buttons(enabled)
            return
        settings.set_setting("show_typed_characters", "1" if enabled else "0")
        self._update_show_typed_buttons(enabled)
        self.show_typed_changed.emit(enabled)

    def _update_show_ghost_text_buttons(self, enabled: bool):
        """Refresh the button styles for the show-ghost-text setting."""
        if not hasattr(self, 'show_ghost_enabled_btn'):
            return
        active_style = (
            "background-color: #5e81ac; color: white; border: none; border-radius: 6px;"
            " font-weight: bold;"
        )
        inactive_style = (
            "background-color: #3b4252; color: #d8dee9; border: 1px solid #434c5e; border-radius: 6px;"
        )
        self.show_ghost_enabled_btn.setChecked(enabled)
        self.show_ghost_disabled_btn.setChecked(not enabled)
        self.show_ghost_enabled_btn.setStyleSheet(active_style if enabled else inactive_style)
        self.show_ghost_disabled_btn.setStyleSheet(active_style if not enabled else inactive_style)

    def _handle_show_ghost_text_button(self, enabled: bool):
        """Handle clicks on the show-ghost-text buttons."""
        current = settings.get_setting("show_ghost_text", settings.get_default("show_ghost_text")) == "1"
        if current == enabled:
            self._update_show_ghost_text_buttons(enabled)
            return
        settings.set_setting("show_ghost_text", "1" if enabled else "0")
        self._update_show_ghost_text_buttons(enabled)
        self.show_ghost_text_changed.emit(enabled)

    def _save_ignore_settings(self):
        """Save ignored files/folders settings and refresh all tabs."""
        if hasattr(self, 'ignored_files_edit'):
            settings.set_setting("ignored_files", self.ignored_files_edit.toPlainText())
        if hasattr(self, 'ignored_folders_edit'):
            settings.set_setting("ignored_folders", self.ignored_folders_edit.toPlainText())
            
        self.ignored_patterns_changed.emit()
        self._apply_ignore_extensions()




    # =========================================================================
    # Theme Management Methods
    # =========================================================================

    def on_unified_color_pick(self, key):
        """Handle color picking for the unified theme editor."""
        from PySide6.QtWidgets import QColorDialog
        
        if not hasattr(self, 'working_scheme'):
            return

        current_color = getattr(self.working_scheme, key, "#FFFFFF")
        
        color = QColorDialog.getColor(QColor(current_color), self, f"Select Color for {key}")
        if color.isValid():
            hex_color = color.name()
            # Update working scheme
            setattr(self.working_scheme, key, hex_color)
            
            # Update button
            if key in self.color_buttons:
                self.color_buttons[key].setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_color};
                        border-radius: 11px;
                        border: 1px solid rgba(255, 255, 255, 0.3);
                    }}
                    QPushButton:hover {{
                        border: 1px solid rgba(255, 255, 255, 0.5);
                    }}
                """)
            
            # Update hex label
            if key in self.color_hex_labels:
                self.color_hex_labels[key].setText(hex_color.upper())
                
            # Apply live preview
            from app.themes import apply_theme_to_app
            app = QApplication.instance()
            apply_theme_to_app(app, self.working_scheme)
            
            # Update editor colors specifically
            self.update_typing_colors(self.working_scheme)
            
            # Mark dirty
            self._colors_dirty = True
            
            # Enable Save Highlights
            self.btn_save_theme.setStyleSheet("background-color: #bd93f9; color: white; border: none; padding: 8px 20px; font-weight: bold;")

    def on_save_theme(self):
        """Save current colors to the current theme name (overwrite)."""
        from app.themes import save_custom_theme
        scheme_name = settings.get_setting("dark_scheme", "dracula")
        save_custom_theme(scheme_name, self.working_scheme, "dark")
        
        self._colors_dirty = False
        self.btn_save_theme.setStyleSheet("") # Reset style
        QMessageBox.information(self, "Theme Saved", f"Theme '{scheme_name}' has been updated.")
        
        # Refresh UI to show Reset button enabled
        self.update_color_buttons_from_theme()

    def on_new_theme(self):
        """Save current colors as a NEW theme."""
        from PySide6.QtWidgets import QInputDialog
        from app.themes import save_custom_theme, THEMES
        
        name, ok = QInputDialog.getText(self, "New Theme", "Enter name for new theme:")
        if ok and name:
            # Clean name
            clean_name = name.lower().replace(" ", "_")
            if not clean_name:
                return
            
            # Save
            save_custom_theme(clean_name, self.working_scheme, "dark")
            
            # Switch to new theme in settings
            settings.set_setting("dark_scheme", clean_name)
            
            # Refresh combination box
            self._populate_scheme_combo("dark")
            # Select the new item
            index = self.scheme_combo.findText(clean_name)
            if index >= 0:
                self.scheme_combo.setCurrentIndex(index)
            
            self._colors_dirty = False
            QMessageBox.information(self, "Theme Created", f"Theme '{name}' created and selected.")

    def on_reset_theme(self):
        """Reset the current theme to its built-in default (deletes custom override)."""
        from app.themes import delete_custom_theme, is_builtin_theme, get_color_scheme
        from app.themes import apply_theme_to_app
        
        scheme_name = settings.get_setting("dark_scheme", "dracula")
        
        if is_builtin_theme("dark", scheme_name):
            return
            
        reply = QMessageBox.question(
            self, "Reset Theme", 
            f"Are you sure you want to reset '{scheme_name}' to defaults? This will delete your custom changes.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            delete_custom_theme(scheme_name, "dark")
            
            # Refresh everything
            self.apply_current_theme()
            self.update_color_buttons_from_theme()
            
            self._colors_dirty = False
            QMessageBox.information(self, "Reset", f"Theme '{scheme_name}' reset to defaults.")

    def _update_auto_indent_buttons(self, enabled: bool):
        """Refresh the button styles for the auto-indent setting."""
        if not hasattr(self, "auto_indent_enabled_btn"): return
        
        active_style = (
            "background-color: #5e81ac; color: white; border: none; border-radius: 6px;"
            " font-weight: bold;"
        )
        inactive_style = (
            "background-color: #3b4252; color: #d8dee9; border: 1px solid #434c5e; border-radius: 6px;"
        )
        
        self.auto_indent_enabled_btn.setChecked(enabled)
        self.auto_indent_disabled_btn.setChecked(not enabled)
        
        self.auto_indent_enabled_btn.setStyleSheet(active_style if enabled else inactive_style)
        self.auto_indent_disabled_btn.setStyleSheet(active_style if not enabled else inactive_style)

    def _handle_auto_indent_button(self, enabled: bool):
        """Handle clicks on the auto-indent buttons."""
        settings.set_setting("auto_indent", "1" if enabled else "0")
        self._update_auto_indent_buttons(enabled)
        self.auto_indent_changed.emit(enabled)
        # Update engine immediately if it exists
        if hasattr(self, 'editor_tab'):
            if self.editor_tab.typing_area and self.editor_tab.typing_area.engine:
                self.editor_tab.typing_area.engine.auto_indent = enabled
            if self.editor_tab.file_tree:
                self.editor_tab.file_tree.reload_tree()


def create_splash_screen(app):
    """Create and show a splash screen during startup."""
    from PySide6.QtGui import QFont, QColor
    from PySide6.QtWidgets import QProgressBar
    from app.themes import get_color_scheme
    
    # Get current theme for splash
    scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
    scheme = get_color_scheme("dark", scheme_name)
    
    # Create a simple splash widget
    splash_widget = QWidget()
    splash_widget.setFixedSize(450, 300)
    splash_widget.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    splash_widget.setStyleSheet(f"""
        QWidget {{
            background-color: {scheme.bg_primary};
            border: 3px solid {scheme.border_color};
            border-radius: 12px;
        }}
        QLabel {{
            color: {scheme.text_primary};
            background: transparent;
        }}
        QProgressBar {{
            border: 2px solid {scheme.border_color};
            border-radius: 5px;
            background-color: {scheme.bg_secondary};
            text-align: center;
            color: {scheme.text_primary};
            font-size: 11px;
            font-weight: bold;
        }}
        QProgressBar::chunk {{
            background-color: {scheme.accent_color};
            border-radius: 3px;
        }}
    """)
    
    layout = QVBoxLayout(splash_widget)
    layout.setContentsMargins(40, 40, 40, 40)
    layout.setSpacing(20)
    
    # Title
    title_container = QWidget()
    title_layout = QHBoxLayout(title_container)
    title_layout.setContentsMargins(0, 0, 0, 0)
    title_layout.setSpacing(15)
    title_layout.setAlignment(Qt.AlignCenter)
    
    title_icon = QLabel()
    title_icon.setPixmap(get_pixmap("KEYBOARD", size=48))
    title_layout.addWidget(title_icon)
    
    title_label = QLabel("Dev Typing App")
    title_label.setAlignment(Qt.AlignCenter)
    title_font = QFont("Segoe UI", 28)
    title_font.setBold(True)
    title_label.setFont(title_font)
    title_label.setStyleSheet(f"color: {scheme.text_primary};")
    title_layout.addWidget(title_label)
    
    layout.addWidget(title_container)
    
    # Subtitle
    subtitle = QLabel("Practice coding by typing")
    subtitle.setAlignment(Qt.AlignCenter)
    subtitle.setFont(QFont("Segoe UI", 11))
    subtitle.setStyleSheet(f"color: {scheme.accent_color};")
    layout.addWidget(subtitle)
    
    layout.addStretch()
    
    # Progress bar
    progress_bar = QProgressBar()
    progress_bar.setMinimum(0)
    progress_bar.setMaximum(100)
    progress_bar.setValue(0)
    progress_bar.setTextVisible(True)
    progress_bar.setFormat("%p%")
    progress_bar.setFixedHeight(25)
    layout.addWidget(progress_bar)
    
    # Status label
    status = QLabel("Initializing...")
    status.setAlignment(Qt.AlignCenter)
    status.setFont(QFont("Segoe UI", 10))
    status.setStyleSheet(f"color: {scheme.text_secondary};")
    layout.addWidget(status)
    
    # Center on screen
    from PySide6.QtGui import QGuiApplication
    screen = QGuiApplication.primaryScreen().geometry()
    splash_widget.move(
        (screen.width() - splash_widget.width()) // 2,
        (screen.height() - splash_widget.height()) // 2
    )
    
    splash_widget.show()
    app.processEvents()
    
    return splash_widget, status, progress_bar


def run_app_with_splash(splash=None):
    """
    Run the application with an optional pre-created splash screen.
    
    Args:
        splash: An InstantSplash instance, or None for no splash.
    """
    import time
    start = time.time()
    
    if DEBUG_STARTUP_TIMING:
        print("[STARTUP] Starting app initialization...")
    
    def update(text: str, progress: int):
        if splash:
            try:
                splash.update(text, progress)
            except:
                pass
    
    # Create QApplication
    if DEBUG_STARTUP_TIMING:
        t1 = time.time()
    update("Initializing...", 25)
    app = QApplication(sys.argv)
    if DEBUG_STARTUP_TIMING:
        print(f"[STARTUP] QApplication created: {time.time() - t1:.3f}s")
    
    # Initialize Profile System
    update("Loading profile...", 30)
    from app.profile_manager import get_profile_manager
    pm = get_profile_manager()
    active_db = pm.get_current_db_path()

    # Initialize database
    if DEBUG_STARTUP_TIMING:
        t_db = time.time()
    update("Loading settings...", 40)
    settings.init_db(str(active_db))
    if DEBUG_STARTUP_TIMING:
        print(f"[STARTUP] Database initialized: {time.time() - t_db:.3f}s")
    
    # Cleanup old session history (non-blocking, in background)
    try:
        retention_days = settings.get_setting("history_retention_days", settings.get_default("history_retention_days"))
        retention_days = int(retention_days) if retention_days and retention_days != "0" else 0
        if retention_days > 0:
            import threading
            def cleanup_history():
                from app import stats_db
                stats_db.cleanup_old_sessions(retention_days)
            
            cleanup_thread = threading.Thread(target=cleanup_history, daemon=True)
            cleanup_thread.start()
    except Exception as e:
        if DEBUG_STARTUP_TIMING:
            print(f"[STARTUP] History cleanup error: {e}")
    
    # Create main window
    if DEBUG_STARTUP_TIMING:
        t2 = time.time()
    update("Building interface...", 60)
    win = MainWindow()
    if DEBUG_STARTUP_TIMING:
        print(f"[STARTUP] MainWindow created: {time.time() - t2:.3f}s")
    
    # Apply theme
    if DEBUG_STARTUP_TIMING:
        t_theme = time.time()
    update("Applying theme...", 85)
    win.apply_current_theme()
    if DEBUG_STARTUP_TIMING:
        print(f"[STARTUP] Theme applied: {time.time() - t_theme:.3f}s")
    
    # Final update before showing
    update("Ready!", 100)
    
    # Brief pause so user sees "Ready!"
    time.sleep(0.15)
    
    # Close splash and show main window
    if splash:
        try:
            splash.close()
        except:
            pass
    
    win.show()
    win.raise_()
    win.activateWindow()
    
    if DEBUG_STARTUP_TIMING:
        print(f"[STARTUP] TOTAL TIME: {time.time() - start:.3f}s")
    
    sys.exit(app.exec())


def run_app():
    """Run the application without a splash screen."""
    run_app_with_splash(None)


if __name__ == "__main__":
    run_app()
