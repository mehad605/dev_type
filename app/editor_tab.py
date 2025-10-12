"""Editor/Typing tab with file tree, typing area, and stats display."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from typing import Optional, List
from app.file_tree import FileTreeWidget
from app.typing_area import TypingAreaWidget
from app.stats_display import StatsDisplayWidget
from app import stats_db


class EditorTab(QWidget):
    """Complete editor/typing tab with tree, typing area, and stats."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file: Optional[str] = None
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Horizontal splitter: file tree | typing area
        h_splitter = QSplitter(Qt.Horizontal)
        
        # Left side: File tree
        self.file_tree = FileTreeWidget()
        self.file_tree.file_selected.connect(self.on_file_selected)
        h_splitter.addWidget(self.file_tree)
        
        # Right side: Typing area + stats
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        # Top toolbar
        toolbar = QHBoxLayout()
        self.reset_btn = QPushButton("⟲ Reset to Top")
        self.reset_btn.setToolTip("Reset cursor to beginning of file")
        self.reset_btn.clicked.connect(self.on_reset_clicked)
        toolbar.addWidget(self.reset_btn)
        toolbar.addStretch()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("font-weight: bold; color: #888888;")
        toolbar.addWidget(self.file_label)
        
        right_layout.addLayout(toolbar)
        
        # Vertical splitter: typing area | stats
        v_splitter = QSplitter(Qt.Vertical)
        
        # Typing area (larger)
        self.typing_area = TypingAreaWidget()
        self.typing_area.stats_updated.connect(self.on_stats_updated)
        self.typing_area.session_completed.connect(self.on_session_completed)
        v_splitter.addWidget(self.typing_area)
        
        # Stats display (smaller)
        self.stats_display = StatsDisplayWidget()
        v_splitter.addWidget(self.stats_display)
        
        # Set initial sizes (70% typing, 30% stats)
        v_splitter.setSizes([700, 300])
        
        right_layout.addWidget(v_splitter)
        h_splitter.addWidget(right_widget)
        
        # Set initial sizes (30% tree, 70% typing)
        h_splitter.setSizes([300, 700])
        
        main_layout.addWidget(h_splitter)
        
        # Timer for updating stats display
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(100)  # Update every 100ms
    
    def load_folder(self, folder_path: str):
        """Load a single folder for practice."""
        self.file_tree.load_folder(folder_path)
    
    def load_folders(self, folder_paths: List[str]):
        """Load multiple folders for practice."""
        self.file_tree.load_folders(folder_paths)
    
    def load_language_files(self, language: str, files: List[str]):
        """Load files filtered by language."""
        self.file_tree.load_language_files(language, files)
    
    def on_file_selected(self, file_path: str):
        """Handle file selection from tree."""
        # Save progress of current file if any
        if self.current_file and self.typing_area.engine:
            self._save_current_progress()
        
        # Load new file
        self.current_file = file_path
        self.file_label.setText(file_path.split('\\')[-1] if '\\' in file_path else file_path.split('/')[-1])
        self.typing_area.load_file(file_path)
        self.typing_area.setFocus()
        
        # Update stats display
        self.on_stats_updated()
    
    def on_stats_updated(self):
        """Handle stats update from typing area."""
        stats = self.typing_area.get_stats()
        self.stats_display.update_stats(stats)
    
    def update_display(self):
        """Periodic update of stats display."""
        if self.typing_area.engine and not self.typing_area.engine.state.is_paused:
            self.typing_area.engine.update_elapsed_time()
            self.on_stats_updated()
    
    def on_reset_clicked(self):
        """Handle reset button click."""
        if not self.current_file:
            return
        
        # Confirm reset
        reply = QMessageBox.question(
            self,
            "Reset Session",
            "Reset typing session to the beginning of the file?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.typing_area.reset_session()
            # Clear saved progress
            stats_db.clear_session_progress(self.current_file)
    
    def on_session_completed(self):
        """Handle completed typing session."""
        if not self.current_file or not self.typing_area.engine:
            return
        
        # Get final stats
        stats = self.typing_area.get_stats()
        
        # Save to database
        stats_db.update_file_stats(
            self.current_file,
            wpm=stats["wpm"],
            accuracy=stats["accuracy"],
            completed=True
        )
        
        # Refresh file tree to update incomplete session highlights
        self.file_tree.refresh_incomplete_sessions()
        
        # Clear session progress
        stats_db.clear_session_progress(self.current_file)
        
        # Show completion message
        QMessageBox.information(
            self,
            "Session Complete!",
            f"Congratulations! You completed the file.\n\n"
            f"WPM: {stats['wpm']:.1f}\n"
            f"Accuracy: {stats['accuracy']*100:.1f}%\n"
            f"Time: {stats['time']:.1f}s"
        )
        
        # Refresh file tree to update stats
        self.file_tree.on_item_clicked(
            self.file_tree.currentItem(),
            0
        )
    
    def _save_current_progress(self):
        """Save progress of current file."""
        if not self.current_file or not self.typing_area.engine:
            return
        
        engine = self.typing_area.engine
        
        # Only save if session has started and not completed
        if engine.state.cursor_position > 0 and not engine.state.is_complete():
            stats_db.save_session_progress(
                self.current_file,
                cursor_pos=engine.state.cursor_position,
                total_chars=len(engine.state.content),
                correct=engine.state.correct_keystrokes,
                incorrect=engine.state.incorrect_keystrokes,
                time=engine.state.elapsed_time,
                is_paused=True
            )
    
    def closeEvent(self, event):
        """Handle widget close - save progress."""
        self._save_current_progress()
        super().closeEvent(event)
