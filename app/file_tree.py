"""File tree widget for displaying files in folders/languages with WPM stats."""
from PySide6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
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
                stats = stats_db.get_file_stats(str(item))
                best_wpm = f"{stats['best_wpm']:.1f}" if stats and stats['best_wpm'] > 0 else "--"
                last_wpm = f"{stats['last_wpm']:.1f}" if stats and stats['last_wpm'] > 0 else "--"
                
                file_item = QTreeWidgetItem(parent_item, [
                    item.name,
                    best_wpm,
                    last_wpm
                ])
                file_item.setData(0, Qt.UserRole, str(item))
    
    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click - emit signal if it's a file."""
        file_path = item.data(0, Qt.UserRole)
        if file_path and Path(file_path).is_file():
            self.file_selected.emit(file_path)
