"""File tree widget for displaying files in folders/languages with WPM stats."""
from PySide6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
    QStyle,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QTreeWidgetItemIterator,
    QPushButton,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QBrush, QColor, QPixmap, QPainter, QFont
from pathlib import Path
from typing import List, Optional, Dict
import re
import fnmatch
import json
import random
from app import settings, stats_db
from app.file_scanner import LANGUAGE_MAP, should_ignore_file, should_ignore_folder


def _get_icon_manager():
    from app.icon_manager import get_icon_manager

    return get_icon_manager()


class InternalFileTree(QTreeWidget):
    """Tree widget displaying files with best/last WPM columns."""
    
    file_selected = Signal(str)  # Emits file path when file is clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Setup columns: File | Best WPM | Last WPM
        self.setHeaderLabels(["File", "Best", "Last"])
        self.setColumnWidth(0, 300)
        self.setColumnWidth(1, 80)
        self.setColumnWidth(2, 80)
        
        # Enable sorting
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)
        
        # Connect selection signal
        self.itemClicked.connect(self.on_item_clicked)
        
        # Get incomplete sessions for highlighting
        self.incomplete_files = set(stats_db.get_incomplete_sessions())

        # Cache icons so we do not recreate them per row
        self._icon_cache: Dict[str, QIcon] = {}
        self.folder_icon = self.style().standardIcon(QStyle.SP_DirIcon)
        self.generic_file_icon = self.style().standardIcon(QStyle.SP_FileIcon)
        
        # Expansion persistence
        self.expanded_paths = set()
        self._persistence_enabled = True
        self._load_expansion_state()
        
        self.itemExpanded.connect(self._on_item_expanded)
        self.itemCollapsed.connect(self._on_item_collapsed)
        
        # Ignore settings
        self.ignored_files = []
        self.ignored_folders = []
        self._load_ignore_settings()
        
        # State for reloading
        self._last_load_args = None  # (method_name, args, kwargs)

    def set_persistence_enabled(self, enabled: bool):
        """Enable or disable expansion state persistence."""
        self._persistence_enabled = enabled

    def _load_expansion_state(self):
        """Load expanded folder paths from settings."""
        try:
            data = settings.get_setting("expanded_folders", "[]")
            self.expanded_paths = set(json.loads(data))
        except:
            self.expanded_paths = set()

    def _save_expansion_state_to_db(self):
        """Save expanded folder paths to settings."""
        if not self._persistence_enabled:
            return
        settings.set_setting("expanded_folders", json.dumps(list(self.expanded_paths)))

    def _on_item_expanded(self, item):
        """Handle item expansion."""
        path = item.data(0, Qt.UserRole)
        if path:
            self.expanded_paths.add(path)
            self._save_expansion_state_to_db()

    def _on_item_collapsed(self, item):
        """Handle item collapse."""
        path = item.data(0, Qt.UserRole)
        if path:
            if path in self.expanded_paths:
                self.expanded_paths.remove(path)
                self._save_expansion_state_to_db()
    
    def _load_ignore_settings(self):
        """Load global ignore settings."""
        raw_files = settings.get_setting("ignored_files", settings.get_default("ignored_files"))
        raw_folders = settings.get_setting("ignored_folders", settings.get_default("ignored_folders"))
        
        self.ignored_files = [p.strip() for p in raw_files.split('\n') if p.strip()]
        self.ignored_folders = [p.strip() for p in raw_folders.split('\n') if p.strip()]

    def update_ignore_settings(self):
        """Reload ignore settings and refresh the tree."""
        self._load_ignore_settings()
        self.reload_tree()

    def reload_tree(self):
        """Reload the tree using the last used load method."""
        if not self._last_load_args:
            return
            
        method_name, args, kwargs = self._last_load_args
        if hasattr(self, method_name):
            getattr(self, method_name)(*args, **kwargs)

    def _is_ignored(self, path: Path) -> bool:
        """Check if a file or folder should be ignored using global logic."""
        if path.is_dir():
            return should_ignore_folder(path, self.ignored_folders)
        elif path.is_file():
            return should_ignore_file(path, self.ignored_files)
        return False

    def load_folder(self, folder_path: str):
        """Load a single folder and display its file tree."""
        self._last_load_args = ("load_folder", (folder_path,), {})
        self.refresh_incomplete_sessions()
        self.clear()
        root_path = Path(folder_path)
        if not root_path.exists():
            return
        
        root_item = QTreeWidgetItem(self, [root_path.name, "", ""])
        root_item.setData(0, Qt.UserRole, str(root_path))
        root_item.setIcon(0, self.folder_icon)
        self._populate_tree(root_item, root_path)
        root_item.setExpanded(True)
    
    def load_folders(self, folder_paths: List[str]):
        """Load multiple folders and display them as separate tree roots."""
        self._last_load_args = ("load_folders", (folder_paths,), {})
        self.refresh_incomplete_sessions()
        self.clear()
        for folder_path in folder_paths:
            root_path = Path(folder_path)
            if not root_path.exists():
                continue
            
            root_item = QTreeWidgetItem(self, [root_path.name, "", ""])
            root_item.setData(0, Qt.UserRole, str(root_path))
            root_item.setIcon(0, self.folder_icon)
            self._populate_tree(root_item, root_path)
            # Check persistence for root items in multi-folder view
            if str(root_path) in self.expanded_paths:
                root_item.setExpanded(True)
            else:
                root_item.setExpanded(False)
    
    def load_language_files(self, language: str, files: List[str]):
        """Load files grouped by their parent folders for a specific language."""
        self._last_load_args = ("load_language_files", (language, files), {})
        self.refresh_incomplete_sessions()
        self.clear()
        
        # Group files by their parent folder
        folder_files: Dict[str, List[str]] = {}
        for file_path in files:
            parent = str(Path(file_path).parent)
            if parent not in folder_files:
                folder_files[parent] = []
            folder_files[parent].append(file_path)

        stats_cache = stats_db.get_file_stats_for_files(files)
        
        # Create tree items for each folder
        for folder, file_list in sorted(folder_files.items()):
            folder_path = Path(folder)
            folder_item = QTreeWidgetItem(self, [folder_path.name, "", ""])
            folder_item.setData(0, Qt.UserRole, folder)
            folder_item.setIcon(0, self.folder_icon)
            
            for file_path in sorted(file_list):
                file_path_obj = Path(file_path)
                # Get actual WPM stats from database
                stats = stats_cache.get(file_path)
                best_wpm = f"{stats['best_wpm']:.1f}" if stats and stats['best_wpm'] > 0 else "--"
                last_wpm = f"{stats['last_wpm']:.1f}" if stats and stats['last_wpm'] > 0 else "--"
                language = LANGUAGE_MAP.get(file_path_obj.suffix.lower())
                
                file_item = QTreeWidgetItem(folder_item, [
                    file_path_obj.name,
                    best_wpm,
                    last_wpm
                ])
                file_item.setData(0, Qt.UserRole, str(file_path))
                icon, icon_error = self._icon_for_language(language)
                file_item.setIcon(0, icon)
                if icon_error:
                    file_item.setToolTip(0, f"{file_path}\n(Icon unavailable: {icon_error})")
                else:
                    file_item.setToolTip(0, str(file_path))
                
                # Highlight if incomplete session
                self._apply_incomplete_highlight(file_item, file_path)
            
            # Check persistence
            if str(folder) in self.expanded_paths:
                folder_item.setExpanded(True)
            else:
                folder_item.setExpanded(False)
    
    def _populate_tree(self, parent_item: QTreeWidgetItem, path: Path):
        """Recursively populate tree with files and folders."""
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return
        
        file_candidates = [
            item for item in items
            if item.is_file() and item.suffix.lower() in LANGUAGE_MAP
        ]
        stats_cache = stats_db.get_file_stats_for_files(str(item) for item in file_candidates)

        for item in items:
            if item.name.startswith('.'):
                continue
            
            if self._is_ignored(item):
                continue
            
            if item.is_dir():
                folder_item = QTreeWidgetItem(parent_item, [item.name, "", ""])
                folder_item.setData(0, Qt.UserRole, str(item))
                folder_item.setIcon(0, self.folder_icon)
                self._populate_tree(folder_item, item)
                
                # Check persistence
                if str(item) in self.expanded_paths:
                    folder_item.setExpanded(True)
            elif item.is_file():
                # Only show supported file types
                if item.suffix.lower() not in LANGUAGE_MAP:
                    continue

                # Get actual WPM stats from cache
                file_path_str = str(item)
                stats = stats_cache.get(file_path_str)
                best_wpm = f"{stats['best_wpm']:.1f}" if stats and stats['best_wpm'] > 0 else "--"
                last_wpm = f"{stats['last_wpm']:.1f}" if stats and stats['last_wpm'] > 0 else "--"
                language = LANGUAGE_MAP.get(item.suffix.lower())
                
                file_item = QTreeWidgetItem(parent_item, [
                    item.name,
                    best_wpm,
                    last_wpm
                ])
                file_item.setData(0, Qt.UserRole, file_path_str)
                icon, icon_error = self._icon_for_language(language)
                file_item.setIcon(0, icon)
                if icon_error:
                    file_item.setToolTip(0, f"{file_path_str}\n(Icon unavailable: {icon_error})")
                else:
                    file_item.setToolTip(0, file_path_str)
                
                # Highlight if incomplete session
                self._apply_incomplete_highlight(file_item, file_path_str)
    
    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click - emit signal if it's a file."""
        file_path = item.data(0, Qt.UserRole)
        if file_path and Path(file_path).is_file():
            self.file_selected.emit(file_path)
    
    def _get_incomplete_highlight_color(self) -> QColor:
        """Get the highlight color for incomplete files from theme settings."""
        from app import settings
        paused_color = settings.get_setting("color_paused_highlight", settings.get_default("color_paused_highlight"))
        # Make it slightly transparent for better visibility
        color = QColor(paused_color)
        color.setAlpha(80)  # 30% opacity
        return color
    
    def _apply_incomplete_highlight(self, item: QTreeWidgetItem, file_path: str):
        """Apply highlight to file item if it has an incomplete session."""
        if file_path in self.incomplete_files:
            highlight_color = self._get_incomplete_highlight_color()
            brush = QBrush(highlight_color)
            # Apply to all columns
            for col in range(self.columnCount()):
                item.setBackground(col, brush)
            # Add indicator in the filename (⏸ pause symbol)
            current_text = item.text(0)
            if not current_text.endswith(" ⏸"):
                item.setText(0, f"{current_text} ⏸")
    
    def refresh_incomplete_sessions(self):
        """Refresh the list of incomplete sessions (call after completing a file)."""
        self.incomplete_files = set(stats_db.get_incomplete_sessions())
    
    def refresh_file_stats(self, file_path: str):
        """Update the stats display for a specific file in the tree."""
        if not file_path:
            return
        
        # Get fresh stats from database
        stats = stats_db.get_file_stats(file_path)
        item = self._find_file_item(file_path)
        if not item:
            return

        if stats:
            best_wpm = f"{stats['best_wpm']:.1f}" if stats['best_wpm'] > 0 else "--"
            last_wpm = f"{stats['last_wpm']:.1f}" if stats['last_wpm'] > 0 else "--"
            item.setText(1, best_wpm)
            item.setText(2, last_wpm)

        # Refresh incomplete session highlighting
        self.refresh_incomplete_sessions()
        if file_path in self.incomplete_files:
            self._apply_incomplete_highlight(item, file_path)
        else:
            for col in range(self.columnCount()):
                item.setBackground(col, QBrush())
            current_text = item.text(0)
            if current_text.endswith(" ⏸"):
                item.setText(0, current_text[:-2])
    
    def _find_file_item(self, file_path: str) -> Optional[QTreeWidgetItem]:
        """Recursively search for a file item by its path."""
        def search_item(parent: QTreeWidgetItem) -> Optional[QTreeWidgetItem]:
            for i in range(parent.childCount()):
                child = parent.child(i)
                stored_path = child.data(0, Qt.UserRole)
                if stored_path == file_path:
                    return child
                # Recursively search children
                result = search_item(child)
                if result:
                    return result
            return None
        
        # Search from root items
        for i in range(self.topLevelItemCount()):
            root_item = self.topLevelItem(i)
            stored_path = root_item.data(0, Qt.UserRole)
            if stored_path == file_path:
                return root_item
            # Search children
            result = search_item(root_item)
            if result:
                return result
        
        return None

    def _icon_for_language(self, language: Optional[str]) -> tuple[QIcon, Optional[str]]:
        """Return an icon appropriate for the detected language.
        
        Returns:
            Tuple of (QIcon, error_message) where error_message is None if icon loaded successfully
        """
        if not language:
            return self.generic_file_icon, None

        cache_key = f"lang::{language}"
        error_key = f"err::{language}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key], self._icon_cache.get(error_key)

        manager = _get_icon_manager()
        pixmap = manager.get_icon(language, size=24)
        if pixmap:
            icon = QIcon(pixmap)
            self._icon_cache[cache_key] = icon
            return icon, None

        emoji = manager.get_emoji_fallback(language)
        icon = self._emoji_icon(emoji)
        self._icon_cache[cache_key] = icon
        
        # Store any download error for tooltip
        error = manager.get_download_error(language)
        if error:
            self._icon_cache[error_key] = error
        return icon, error

    def _emoji_icon(self, emoji: str) -> QIcon:
        cache_key = f"emoji::{emoji}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        font = QFont()
        font.setPointSize(14)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, emoji)
        painter.end()

        icon = QIcon(pixmap)
        self._icon_cache[cache_key] = icon
        return icon
    
    def get_all_file_items(self) -> List[QTreeWidgetItem]:
        """Get all file items (not folders) from the tree."""
        file_items = []
        
        def collect_files(item: QTreeWidgetItem):
            file_path = item.data(0, Qt.UserRole)
            # Check if it's a file (not a folder)
            if file_path and Path(file_path).is_file():
                file_items.append(item)
            
            # Recursively collect from children
            for i in range(item.childCount()):
                collect_files(item.child(i))
        
        # Collect from all top-level items
        for i in range(self.topLevelItemCount()):
            collect_files(self.topLevelItem(i))
        
        return file_items
    
    def get_visible_file_items(self) -> List[QTreeWidgetItem]:
        """Get all visible (not hidden by filter) file items from the tree."""
        file_items = []
        
        def collect_visible_files(item: QTreeWidgetItem):
            # Skip hidden items
            if item.isHidden():
                return
            
            file_path = item.data(0, Qt.UserRole)
            # Check if it's a file (not a folder)
            if file_path and Path(file_path).is_file():
                file_items.append(item)
            
            # Recursively collect from children
            for i in range(item.childCount()):
                collect_visible_files(item.child(i))
        
        # Collect from all top-level items
        for i in range(self.topLevelItemCount()):
            collect_visible_files(self.topLevelItem(i))
        
        return file_items
    
    def open_random_file(self):
        """Select and open a random file from the tree (respects search filter)."""
        # Use visible items to respect the current search filter
        file_items = self.get_visible_file_items()
        
        if not file_items:
            return  # No files available
        
        # Choose a random file
        random_item = random.choice(file_items)
        
        # Ensure the item is visible (expand parents if needed)
        self._ensure_item_visible(random_item)
        
        # Select the item and scroll to ensure it's visible
        self.setCurrentItem(random_item)
        self.scrollToItem(random_item)
        
        # Emit the file_selected signal (simulating double-click)
        file_path = random_item.data(0, Qt.UserRole)
        if file_path:
            self.file_selected.emit(file_path)
    
    def _ensure_item_visible(self, item: QTreeWidgetItem):
        """Expand all parent items to make the given item visible."""
        parent = item.parent()
        while parent:
            parent.setExpanded(True)
            parent = parent.parent()


class FileTreeWidget(QWidget):
    """Wrapper widget containing search bar and file tree."""
    
    file_selected = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Top bar with search and random button
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setSpacing(4)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search files... (glob or regex)")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.textChanged.connect(self.filter_tree)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                padding: 4px;
                border: 1px solid #3b4252;
                border-radius: 4px;
                background-color: #2e3440;
                color: #d8dee9;
            }
            QLineEdit:focus {
                border: 1px solid #88c0d0;
            }
        """)
        top_bar_layout.addWidget(self.search_bar)
        
        # Random button
        self.random_button = QPushButton("🎲 Random")
        self.random_button.setToolTip("Open a random file from the tree")
        self.random_button.clicked.connect(self._on_random_clicked)
        self.random_button.setStyleSheet("""
            QPushButton {
                padding: 4px 8px;
                border: 1px solid #3b4252;
                border-radius: 4px;
                background-color: #2e3440;
                color: #d8dee9;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3b4252;
                border-color: #88c0d0;
            }
            QPushButton:pressed {
                background-color: #434c5e;
            }
        """)
        top_bar_layout.addWidget(self.random_button)
        
        layout.addLayout(top_bar_layout)
        
        # Internal tree
        self.tree = InternalFileTree()
        self.tree.file_selected.connect(self.file_selected.emit)
        layout.addWidget(self.tree)
        
        self._expanded_paths = set()
        self._is_searching = False
        
    def filter_tree(self, text: str):
        """Filter tree items based on search text."""
        if not text:
            self._show_all_items()
            if self._is_searching:
                self._restore_expansion_state()
                self._is_searching = False
                self.tree.set_persistence_enabled(True)
            return
            
        if not self._is_searching:
            self._save_expansion_state()
            self._is_searching = True
            self.tree.set_persistence_enabled(False)
            
        # Determine matching strategy
        use_glob = '*' in text or '?' in text
        regex_pattern = None
        
        if not use_glob:
            try:
                regex_pattern = re.compile(text, re.IGNORECASE)
            except re.error:
                # Fallback to substring if regex is invalid
                pass
        
        # Helper to check match
        def matches(item_text):
            if use_glob:
                return fnmatch.fnmatch(item_text.lower(), text.lower())
            elif regex_pattern:
                return bool(regex_pattern.search(item_text))
            else:
                return text.lower() in item_text.lower()
        
        # Recursive filter function
        def filter_item(item):
            has_visible_children = False
            child_count = item.childCount()
            
            for i in range(child_count):
                child = item.child(i)
                if filter_item(child):
                    has_visible_children = True
            
            is_file = bool(item.data(0, Qt.UserRole) and Path(item.data(0, Qt.UserRole)).is_file())
            item_matches = matches(item.text(0))
            
            should_show = has_visible_children or (is_file and item_matches)
            
            item.setHidden(not should_show)
            if should_show:
                item.setExpanded(True)
            
            return should_show

        # Apply filter to top level items
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            filter_item(item)

    def _save_expansion_state(self):
        """Save current expansion state of the tree."""
        self._expanded_paths.clear()
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            if item.isExpanded():
                path = item.data(0, Qt.UserRole)
                if path:
                    self._expanded_paths.add(path)
            iterator += 1

    def _restore_expansion_state(self):
        """Restore expansion state of the tree."""
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            path = item.data(0, Qt.UserRole)
            if path:
                item.setExpanded(path in self._expanded_paths)
            iterator += 1

    def _show_all_items(self):
        """Show all items."""
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            item.setHidden(False)
            iterator += 1
    
    def _on_random_clicked(self):
        """Handle random button click."""
        # Open random file (respects current filter)
        self.tree.open_random_file()

    # Proxy methods
    def load_folder(self, folder_path: str):
        self.tree.load_folder(folder_path)
        
    def load_folders(self, folder_paths: List[str]):
        self.tree.load_folders(folder_paths)
        
    def load_language_files(self, language: str, files: List[str]):
        self.tree.load_language_files(language, files)
        
    def refresh_file_stats(self, file_path: str):
        self.tree.refresh_file_stats(file_path)
        
    def refresh_incomplete_sessions(self):
        self.tree.refresh_incomplete_sessions()

    def update_ignore_settings(self):
        """Update ignore settings and refresh tree."""
        self.tree.update_ignore_settings()
