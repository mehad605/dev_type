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
from PySide6.QtCore import Qt, Signal, QCoreApplication, QTimer
from PySide6.QtGui import QIcon, QBrush, QColor, QPixmap, QPainter, QFont
from pathlib import Path
from typing import List, Optional, Dict, Set
import re
import fnmatch
import json
import random
import os
from app import settings, stats_db
from app.file_scanner import LANGUAGE_MAP, is_text_file
from app.ui_icons import get_icon


def _get_icon_manager():
    from app.icon_manager import get_icon_manager

    return get_icon_manager()


class FileTreeItem(QTreeWidgetItem):
    """Custom QTreeWidgetItem that sorts folders before files."""
    def __lt__(self, other):
        if not isinstance(other, QTreeWidgetItem):
            return super().__lt__(other)

        tree = self.treeWidget()
        # Only apply custom sorting for the first column (Name)
        if tree is not None and tree.sortColumn() == 0:
            role = Qt.UserRole + 1
            # Sort folders (0) before files (1)
            v1 = 0 if self.data(0, role) == "folder" else 1
            v2 = 0 if other.data(0, role) == "folder" else 1
            
            if v1 != v2:
                # Return True if self should come BEFORE other in Ascending (v1 < v2)
                return v1 < v2
                
            # Both are same type, sort by text (case-insensitive)
            return self.text(0).lower() < other.text(0).lower()
            
        return super().__lt__(other)


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
        self._load_ignore_settings()
        
        # State for reloading
        self._last_load_args = None  # (method_name, args, kwargs)
        
        # Large folder optimization state
        self._is_large_dataset = False
        self._all_filepaths: List[str] = []
        self._filtered_filepaths: List[str] = []
        self._file_index: Dict[str, List[str]] = {}  # filename -> [full_paths]
        
        # Lazy loading state
        self._populated_paths: Set[str] = set()
        self._folder_files_cache: Dict[str, List[str]] = {} # For languages tab lazy load
        self.CHUNK_SIZE = 200
        
        # Load expansions
        self._load_expansion_state()

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
            
            # Update folder icon to open state
            if item.data(0, Qt.UserRole + 1) == "folder":
                self._update_folder_icon(item, True)

    def _on_item_collapsed(self, item):
        """Handle item collapse."""
        path = item.data(0, Qt.UserRole)
        if path:
            if path in self.expanded_paths:
                self.expanded_paths.remove(path)
                self._save_expansion_state_to_db()
            
            # Update folder icon to closed state
            if item.data(0, Qt.UserRole + 1) == "folder":
                self._update_folder_icon(item, False)
    
    def _load_ignore_settings(self):
        """Load global ignore settings."""
        from app.file_scanner import get_global_ignore_settings, IgnoreManager
        f_patterns, d_patterns = get_global_ignore_settings()
        self.ignore_manager = IgnoreManager(f_patterns, d_patterns)

    def update_ignore_settings(self):
        """Reload ignore settings and refresh the tree."""
        self._load_ignore_settings()
        self.reload_tree()

    def reload_tree(self):
        """Reload the tree using the most recent load arguments."""
        self.reload_last_load()
            
    def reload_last_load(self):
        """Reload the tree using the most recent load arguments."""
        if not self._last_load_args:
            return
            
        method_name, args, kwargs = self._last_load_args
        if hasattr(self, method_name):
            # Special case for folder paths to ensure they exist
            if method_name in ("load_folder", "load_folders"):
                getattr(self, method_name)(*args, **kwargs)
            else:
                getattr(self, method_name)(*args, **kwargs)

    def restore_last_view(self):
        """Specifically restore the previous folder/language view."""
        self.reload_last_load()

    def _is_ignored(self, path: Path) -> bool:
        """Check if a file or folder should be ignored using global logic."""
        if path.is_dir():
            return self.ignore_manager.should_ignore_folder(path)
        elif path.is_file():
            return self.ignore_manager.should_ignore_file(path)
        return False

    def load_folder(self, folder_path: str):
        """Load a single folder and display its file tree."""
        self._last_load_args = ("load_folder", (folder_path,), {})
        self.refresh_incomplete_sessions()
        
        # Reset optimization state
        self._is_large_dataset = False
        self._all_filepaths.clear()
        self._filtered_filepaths.clear()
        self._file_index.clear()
        self._populated_paths.clear()
        self._folder_files_cache.clear()
        
        # Check if this is a large folder
        from app.file_scanner import is_large_folder, count_files_fast
        threshold = settings.get_setting_int("large_folder_threshold", 1000, min_val=1)
        
        # Fast detection: count files up to threshold + 1
        file_count = count_files_fast(folder_path, threshold=threshold + 1)
        self._is_large_dataset = file_count > threshold
        
        if self._is_large_dataset:
            # For large folders, enumerate all files and build index
            self._enumerate_and_index_folder(folder_path)
        
        self.setSortingEnabled(False)
        self.clear()
        root_path = Path(folder_path)
        if not root_path.exists():
            self.setSortingEnabled(True)
            return
        
        root_item = FileTreeItem(self, [root_path.name, "", ""])
        root_item.setData(0, Qt.UserRole, str(root_path))
        root_item.setData(0, Qt.UserRole + 1, "folder")
        
        # Initial icon
        self._update_folder_icon(root_item, True)
        
        self._populate_tree(root_item, root_path)
        root_item.setExpanded(True)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)
    
    def load_folders(self, folder_paths: List[str]):
        """Load multiple folders and display them as separate tree roots."""
        self._last_load_args = ("load_folders", (folder_paths,), {})
        self.refresh_incomplete_sessions()
        
        # Reset optimization state
        self._is_large_dataset = False
        self._all_filepaths.clear()
        self._filtered_filepaths.clear()
        self._file_index.clear()
        self._populated_paths.clear()
        self._folder_files_cache.clear()
        
        # Check if combined folders form a large dataset
        from app.file_scanner import count_files_fast
        threshold = settings.get_setting_int("large_folder_threshold", 1000, min_val=1)
        
        total_file_count = sum(count_files_fast(fp, threshold=threshold + 1) for fp in folder_paths)
        self._is_large_dataset = total_file_count > threshold
        
        if self._is_large_dataset:
            # Enumerate all files from all folders
            for folder_path in folder_paths:
                self._enumerate_and_index_folder(folder_path)
        
        self.setSortingEnabled(False)
        self.clear()
        for folder_path in folder_paths:
            root_path = Path(folder_path)
            if not root_path.exists():
                continue
            
            root_item = FileTreeItem(self, [root_path.name, "", ""])
            root_item.setData(0, Qt.UserRole, str(root_path))
            root_item.setData(0, Qt.UserRole + 1, "folder")
            
            # Check persistence
            is_expanded = str(root_path) in self.expanded_paths
            self._update_folder_icon(root_item, is_expanded)
            
            self._populate_tree(root_item, root_path)
            
            if is_expanded:
                root_item.setExpanded(True)
            else:
                root_item.setExpanded(False)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)
    
    def load_language_files(self, language: str, files: List[str]):
        """Load files grouped by their parent folders for a specific language.
        
        Implemented with lazy folder population for instant performance.
        """
        self._last_load_args = ("load_language_files", (language, files), {})
        self.refresh_incomplete_sessions()
        
        # Check if this is a large dataset
        threshold = settings.get_setting_int("large_folder_threshold", 1000, min_val=1)
        self._is_large_dataset = len(files) > threshold
        
        self._all_filepaths = list(files)
        self._filtered_filepaths = list(files)
        
        if self._is_large_dataset:
            # Build file index for fast search
            self._file_index = {}
            for file_path in files:
                filename = os.path.basename(file_path).lower()
                if filename not in self._file_index:
                    self._file_index[filename] = []
                self._file_index[filename].append(file_path)
        
        self.setSortingEnabled(False)
        self.clear()
        self._populated_paths.clear()
        self._folder_files_cache.clear()
        
        # Group files by their parent folder for deferred loading
        for file_path in files:
            parent = os.path.dirname(file_path)
            if parent not in self._folder_files_cache:
                self._folder_files_cache[parent] = []
            self._folder_files_cache[parent].append(file_path)
        
        # Create folder items only (Lazy population of contents)
        for folder in sorted(self._folder_files_cache.keys()):
            folder_path = Path(folder)
            folder_item = FileTreeItem(self, [folder_path.name, "", ""])
            folder_item.setData(0, Qt.UserRole, folder)
            folder_item.setData(0, Qt.UserRole + 1, "folder")
            
            # Check persistence
            is_expanded = str(folder) in self.expanded_paths
            self._update_folder_icon(folder_item, is_expanded)
            
            # Add dummy child
            QTreeWidgetItem(folder_item, ["..."])
            
            if is_expanded:
                # Trigger lazy load
                self._on_item_expanded(folder_item)
                folder_item.setExpanded(True)

        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)

    def _populate_tree(self, parent_item: QTreeWidgetItem, path: Path, start_index: int = 0):
        """Populate tree with files and subfolders for the current level only.
        
        This method implements pagination and deferred loading for instant performance.
        """
        path_str = str(path)
        
        # Check if we have pre-grouped files (e.g. from languages tab)
        if path_str in self._folder_files_cache:
            file_candidates = self._folder_files_cache[path_str]
            # When from language cache, we don't show subfolders, just files
            entries = [Path(f) for f in sorted(file_candidates)]
        else:
            try:
                # Standard folder view: get all entries
                entries = sorted(list(path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
            except (PermissionError, OSError):
                return

        # Filtering entries
        valid_entries = []
        for entry in entries:
            # If it's a file, check if it's already in our candidates or check extension
            if entry.is_file():
                if path_str in self._folder_files_cache:
                    # In language mode, we only show files belonging to that language
                    # (already filtered in entries list)
                    pass
                else:
                    if entry.name.startswith('.'): continue
                    if entry.suffix.lower() not in LANGUAGE_MAP: continue
                    if self.ignore_manager.should_ignore_file(entry): continue
            else:
                # Directory
                if path_str in self._folder_files_cache:
                    continue # Hide subfolders in languages mode
                if entry.name.startswith('.'): continue
                if self.ignore_manager.should_ignore_folder(entry): continue
                
            valid_entries.append(entry)

        # Pagination
        total_valid = len(valid_entries)
        end_index = min(start_index + self.CHUNK_SIZE, total_valid)
        chunk = valid_entries[start_index:end_index]

        # Batch fetch stats
        file_paths = [str(item) for item in chunk if item.is_file()]
        auto_indent = settings.get_setting("auto_indent", "0") == "1"
        stats_cache = stats_db.get_file_stats_for_files(file_paths, auto_indent=auto_indent) if file_paths else {}

        for item in chunk:
            if item.is_dir():
                folder_item = FileTreeItem(parent_item, [item.name, " ", " "])
                folder_item.setData(0, Qt.UserRole, str(item))
                folder_item.setData(0, Qt.UserRole + 1, "folder")
                QTreeWidgetItem(folder_item, ["..."])
            else:
                file_path_str = str(item)
                stats = stats_cache.get(file_path_str)
                best_wpm = f"{stats['best_wpm']:.1f}" if stats and stats['best_wpm'] > 0 else "--"
                last_wpm = f"{stats['last_wpm']:.1f}" if stats and stats['last_wpm'] > 0 else "--"
                file_item = FileTreeItem(parent_item, [item.name, best_wpm, last_wpm])
                file_item.setData(0, Qt.UserRole, file_path_str)
                file_item.setData(0, Qt.UserRole + 1, "file")
                self._apply_file_icon(file_item, item.name)
                file_item.setToolTip(0, file_path_str)
                self._apply_incomplete_highlight(file_item, file_path_str)

        if end_index < total_valid:
            remaining = total_valid - end_index
            more_item = QTreeWidgetItem(parent_item, [f"Show More... ({remaining} left)", "", ""])
            more_item.setData(0, Qt.UserRole, path_str)
            more_item.setData(0, Qt.UserRole + 1, "load_more")
            more_item.setData(0, Qt.UserRole + 2, end_index)
            more_item.setForeground(0, QBrush(QColor("#88c0d0")))
            more_item.setFont(0, QFont("", -1, QFont.Bold))

    def _on_item_expanded(self, item):
        """Handle item expansion - triggered for lazy loading."""
        path_str = item.data(0, Qt.UserRole)
        role = item.data(0, Qt.UserRole + 1)
        
        if path_str:
            self.expanded_paths.add(path_str)
            self._save_expansion_state_to_db()
            
            if role == "folder":
                self._update_folder_icon(item, True)
                # Check if it has the dummy child
                if item.childCount() == 1 and item.child(0).text(0) == "...":
                    # Clear dummy and populate real items
                    item.removeChild(item.child(0))
                    self._populate_tree(item, Path(path_str))

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click - supports selection and pagination."""
        path = item.data(0, Qt.UserRole)
        role = item.data(0, Qt.UserRole + 1)
        
        if role == "load_more":
            parent = item.parent() or self.invisibleRootItem()
            start_index = item.data(0, Qt.UserRole + 2)
            parent.removeChild(item)
            
            if path == "SEARCH_RESULTS":
                # Paginate search results
                total_matches = len(self._filtered_filepaths)
                end_index = min(start_index + self.CHUNK_SIZE, total_matches)
                chunk = self._filtered_filepaths[start_index:end_index]
                
                auto_indent = settings.get_setting("auto_indent", "0") == "1"
                stats_cache = stats_db.get_file_stats_for_files(chunk, auto_indent=auto_indent) if chunk else {}
                
                for file_path in chunk:
                    stats = stats_cache.get(file_path)
                    best_wpm = f"{stats['best_wpm']:.1f}" if stats and stats['best_wpm'] > 0 else "--"
                    last_wpm = f"{stats['last_wpm']:.1f}" if stats and stats['last_wpm'] > 0 else "--"
                    res_item = FileTreeItem(parent, [os.path.basename(file_path), best_wpm, last_wpm])
                    res_item.setData(0, Qt.UserRole, file_path)
                    res_item.setData(0, Qt.UserRole + 1, "file")
                    self._apply_file_icon(res_item, file_path)
                    res_item.setToolTip(0, file_path)
                    self._apply_incomplete_highlight(res_item, file_path)
                    
                if end_index < total_matches:
                    more_item = QTreeWidgetItem(parent, [f"Show More Matches... ({total_matches - end_index} left)", "", ""])
                    more_item.setData(0, Qt.UserRole, "SEARCH_RESULTS")
                    more_item.setData(0, Qt.UserRole + 1, "load_more")
                    more_item.setData(0, Qt.UserRole + 2, end_index)
                    more_item.setForeground(0, QBrush(QColor("#88c0d0")))
            elif path:
                self._populate_tree(parent, Path(path), start_index=start_index)
            return

        if role == "file" and path:
            self.file_selected.emit(path)
    
    def _get_incomplete_highlight_color(self) -> QColor:
        """Get the highlight color for incomplete files from theme settings."""
        from app import settings
        # Make it slightly transparent for better visibility
        color = QColor(paused_color)
        color.setAlpha(80)  # 30% opacity
        return color
    
    def _apply_incomplete_highlight(self, item: QTreeWidgetItem, file_path: str):
        """Apply highlight to file item if it has an incomplete session."""
        if file_path in self.incomplete_files:
            highlight_color = self._get_incomplete_highlight_color()
            brush = QBrush(highlight_color)
            for col in range(self.columnCount()):
                item.setBackground(col, brush)
            
            current_text = item.text(0)
            if not current_text.endswith(" (paused)"):
                item.setText(0, f"{current_text} (paused)")
    
    def refresh_incomplete_sessions(self):
        """Refresh the list of incomplete sessions (call after completing a file)."""
        self.incomplete_files = set(stats_db.get_incomplete_sessions())
    
    def refresh_file_stats(self, file_path: str):
        """Update the stats display for a specific file in the tree."""
        if not file_path:
            return
        
        # Get fresh stats from database for the current mode
        auto_indent = settings.get_setting("auto_indent", "0") == "1"
        stats = stats_db.get_file_stats(file_path, auto_indent=auto_indent)
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
            current_text = item.text(0)
            if current_text.endswith(" (paused)"):
                item.setText(0, current_text[:-9]) # len(" (paused)") == 9
    
    def update_active_status(self, file_path: str, is_active: bool):
        """Update the active status of a file (remove/add 'paused' suffix)."""
        if not file_path:
            return
            
        item = self._find_file_item(file_path)
        if not item:
            return
            
        current_text = item.text(0)
        
        if is_active:
            # We are actively typing/viewing this file, so it's not "paused" in the background sense
            if current_text.endswith(" (paused)"):
                item.setText(0, current_text.replace(" (paused)", ""))
        else:
            # We paused or left the file, so if it's incomplete, mark it paused
            if file_path in self.incomplete_files and not current_text.endswith(" (paused)"):
                item.setText(0, f"{current_text} (paused)")

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

    
    def _enumerate_and_index_folder(self, folder_path: str):
        """Enumerate all files in folder and build search index for large datasets.
        
        Non-blocking implementation using processEvents.
        """
        folder = Path(folder_path)
        if not folder.exists():
            return
        
        all_files = []
        process_counter = 0
        
        # Walk through folder and collect all valid code files
        for root, dirs, files in os.walk(folder, followlinks=False):
            root_path = Path(root)
            
            # Respect ignore settings
            dirs[:] = [d for d in dirs if not self.ignore_manager.should_ignore_folder(root_path / d)]
            dirs[:] = [d for d in dirs if not (root_path / d).is_symlink()]
            
            for filename in files:
                file_path = os.path.join(root, filename)
                
                if self.ignore_manager.should_ignore_file(Path(file_path)):
                    continue
                
                ext = os.path.splitext(filename)[1].lower()
                if ext in LANGUAGE_MAP or is_text_file(Path(file_path)):
                    all_files.append(file_path)
                    
                    # Periodic UI updates during scan
                    process_counter += 1
                    if process_counter % 1000 == 0:
                        QCoreApplication.processEvents()
        
        # Store for fast access
        self._all_filepaths.extend(all_files)
        self._filtered_filepaths = list(self._all_filepaths)
        
        # Build search index
        for file_path in all_files:
            filename = os.path.basename(file_path).lower()
            if filename not in self._file_index:
                self._file_index[filename] = []
            self._file_index[filename].append(file_path)
    
    def _update_folder_icon(self, item: QTreeWidgetItem, expanded: bool):
        """Update the folder icon based on its expansion state."""
        path_str = item.data(0, Qt.UserRole)
        if not path_str:
            return
            
        path = Path(path_str)
        manager = _get_icon_manager()
        pixmap = manager.get_folder_icon(path.name, is_open=expanded, size=24)
        if pixmap:
            item.setIcon(0, QIcon(pixmap))
        else:
            item.setIcon(0, self.folder_icon)

    def _apply_file_icon(self, item: QTreeWidgetItem, filename: str):
        """Apply the appropriate file icon."""
        cache_key = f"file::{filename}"
        if cache_key in self._icon_cache:
             item.setIcon(0, self._icon_cache[cache_key])
             return

        manager = _get_icon_manager()
        pixmap = manager.get_file_icon(filename, size=24)
        if pixmap:
            icon = QIcon(pixmap)
            self._icon_cache[cache_key] = icon
            item.setIcon(0, icon)
        else:
            item.setIcon(0, self.generic_file_icon)


    
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
        # Large dataset optimization: use in-memory file list
        if self._is_large_dataset and self._filtered_filepaths:
            # Instant random selection from filtered list
            file_path = random.choice(self._filtered_filepaths)
            self.file_selected.emit(file_path)
            return
        
        # Small dataset: use visible items to respect the current search filter
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
    
    def __init__(self, parent=None, show_header=True):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Search bar (always create so it can be used externally)
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
        
        # Random button (always create)
        self.random_button = QPushButton("Random")
        self.random_button.setIcon(get_icon("TARGET"))
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
        
        if show_header:
            top_bar_layout = QHBoxLayout()
            top_bar_layout.setSpacing(4)
            top_bar_layout.setContentsMargins(0, 0, 0, 0)
            top_bar_layout.addWidget(self.search_bar)
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
            if self._is_searching:
                self._show_all_items()
                self._restore_expansion_state()
                self._is_searching = False
                self.tree.set_persistence_enabled(True)
                # Reset filtered list for large datasets
                if self.tree._is_large_dataset:
                    self.tree._filtered_filepaths = list(self.tree._all_filepaths)
            return
            
        if not self._is_searching:
            self._save_expansion_state()
            self._is_searching = True
            self.tree.set_persistence_enabled(False)
        
        # Large dataset optimization: use file index for instant search
        if self.tree._is_large_dataset:
            query = text.lower()
            matched_files = []
            
            # Search in file names using index (High performance)
            for filename, paths in self.tree._file_index.items():
                if query in filename:
                    matched_files.extend(paths)
            
            # Only search parts if name query yield few results or if user uses /path search
            if len(matched_files) < 100 or '/' in query or '\\' in query:
                for file_path in self.tree._all_filepaths:
                    if query in file_path.lower() and file_path not in matched_files:
                        matched_files.append(file_path)

            # Update filtered list for random button
            self.tree._filtered_filepaths = matched_files
            
            # CLEAR TREE and show results as a flat list for instant response
            self.tree.clear()
            self._is_searching = True
            
            # Populate matched results (paged)
            total_matches = len(matched_files)
            chunk = matched_files[:self.tree.CHUNK_SIZE]
            
            # Batch stats for matches
            auto_indent = settings.get_setting("auto_indent", "0") == "1"
            stats_cache = stats_db.get_file_stats_for_files(chunk, auto_indent=auto_indent) if chunk else {}
            
            for file_path in chunk:
                stats = stats_cache.get(file_path)
                best_wpm = f"{stats['best_wpm']:.1f}" if stats and stats['best_wpm'] > 0 else "--"
                last_wpm = f"{stats['last_wpm']:.1f}" if stats and stats['last_wpm'] > 0 else "--"
                item = FileTreeItem(self.tree, [os.path.basename(file_path), best_wpm, last_wpm])
                item.setData(0, Qt.UserRole, file_path)
                item.setData(0, Qt.UserRole + 1, "file")
                self.tree._apply_file_icon(item, file_path)
                item.setToolTip(0, file_path)
                self.tree._apply_incomplete_highlight(item, file_path)
                
            if total_matches > self.tree.CHUNK_SIZE:
                remaining = total_matches - self.tree.CHUNK_SIZE
                more_item = QTreeWidgetItem(self.tree, [f"Show More Matches... ({remaining} left)", "", ""])
                # We reuse the pagination logic for search results
                more_item.setData(0, Qt.UserRole, "SEARCH_RESULTS") # Special flag
                more_item.setData(0, Qt.UserRole + 1, "load_more")
                more_item.setData(0, Qt.UserRole + 2, self.tree.CHUNK_SIZE)
                more_item.setForeground(0, QBrush(QColor("#88c0d0")))
                
            return
            
        # Small dataset: original implementation with tree traversal
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
        # If we are in large dataset mode and were searching, 
        # the tree was cleared. We must reload.
        if self.tree._is_large_dataset and self._is_searching:
            self.tree.restore_last_view()
            return

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

    def reload_tree(self):
        """Reload the tree using the last used load method."""
        self.tree.reload_tree()
        
    def update_active_status(self, file_path: str, is_active: bool):
        """Update active status of a file."""
        self.tree.update_active_status(file_path, is_active)
