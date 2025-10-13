"""File tree widget for displaying files in folders/languages with WPM stats."""
from PySide6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QBrush, QColor
from pathlib import Path
from typing import List, Optional, Dict
from app import settings, stats_db


class FileTreeWidget(QTreeWidget):
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
    
    def load_folder(self, folder_path: str):
        """Load a single folder and display its file tree."""
        self.clear()
        root_path = Path(folder_path)
        if not root_path.exists():
            return
        
        root_item = QTreeWidgetItem(self, [root_path.name, "", ""])
        root_item.setData(0, Qt.UserRole, str(root_path))
        self._populate_tree(root_item, root_path)
        root_item.setExpanded(False)
    
    def load_folders(self, folder_paths: List[str]):
        """Load multiple folders and display them as separate tree roots."""
        self.clear()
        for folder_path in folder_paths:
            root_path = Path(folder_path)
            if not root_path.exists():
                continue
            
            root_item = QTreeWidgetItem(self, [root_path.name, "", ""])
            root_item.setData(0, Qt.UserRole, str(root_path))
            self._populate_tree(root_item, root_path)
            root_item.setExpanded(False)
    
    def load_language_files(self, language: str, files: List[str]):
        """Load files grouped by their parent folders for a specific language."""
        self.clear()
        
        # Group files by their parent folder
        folder_files: Dict[str, List[str]] = {}
        for file_path in files:
            parent = str(Path(file_path).parent)
            if parent not in folder_files:
                folder_files[parent] = []
            folder_files[parent].append(file_path)
        
        # Create tree items for each folder
        for folder, file_list in sorted(folder_files.items()):
            folder_path = Path(folder)
            folder_item = QTreeWidgetItem(self, [folder_path.name, "", ""])
            folder_item.setData(0, Qt.UserRole, folder)
            
            for file_path in sorted(file_list):
                file_path_obj = Path(file_path)
                # Get actual WPM stats from database
                stats = stats_db.get_file_stats(file_path)
                best_wpm = f"{stats['best_wpm']:.1f}" if stats and stats['best_wpm'] > 0 else "--"
                last_wpm = f"{stats['last_wpm']:.1f}" if stats and stats['last_wpm'] > 0 else "--"
                
                file_item = QTreeWidgetItem(folder_item, [
                    file_path_obj.name,
                    best_wpm,
                    last_wpm
                ])
                file_item.setData(0, Qt.UserRole, str(file_path))
                
                # Highlight if incomplete session
                self._apply_incomplete_highlight(file_item, file_path)
            
            folder_item.setExpanded(False)
    
    def _populate_tree(self, parent_item: QTreeWidgetItem, path: Path):
        """Recursively populate tree with files and folders."""
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return
        
        for item in items:
            if item.name.startswith('.'):
                continue
            
            if item.is_dir():
                folder_item = QTreeWidgetItem(parent_item, [item.name, "", ""])
                folder_item.setData(0, Qt.UserRole, str(item))
                self._populate_tree(folder_item, item)
            elif item.is_file():
                # Only show supported file types
                from app.file_scanner import LANGUAGE_MAP
                if item.suffix.lower() not in LANGUAGE_MAP:
                    continue
                
                # Get actual WPM stats from database
                file_path_str = str(item)
                stats = stats_db.get_file_stats(file_path_str)
                best_wpm = f"{stats['best_wpm']:.1f}" if stats and stats['best_wpm'] > 0 else "--"
                last_wpm = f"{stats['last_wpm']:.1f}" if stats and stats['last_wpm'] > 0 else "--"
                
                file_item = QTreeWidgetItem(parent_item, [
                    item.name,
                    best_wpm,
                    last_wpm
                ])
                file_item.setData(0, Qt.UserRole, file_path_str)
                
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
        paused_color = settings.get_setting("color_paused_highlight", "#ffaa00")
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
        if not stats:
            return
        
        best_wpm = f"{stats['best_wpm']:.1f}" if stats['best_wpm'] > 0 else "--"
        last_wpm = f"{stats['last_wpm']:.1f}" if stats['last_wpm'] > 0 else "--"
        
        # Find the item for this file in the tree
        item = self._find_file_item(file_path)
        if item:
            # Update the Best and Last columns
            item.setText(1, best_wpm)
            item.setText(2, last_wpm)
            
            # Refresh incomplete session highlighting
            self.refresh_incomplete_sessions()
            # Remove highlight if no longer incomplete
            if file_path not in self.incomplete_files:
                for col in range(self.columnCount()):
                    item.setBackground(col, QBrush())  # Clear background
                # Remove pause symbol
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
