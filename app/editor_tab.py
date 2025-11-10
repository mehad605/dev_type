"""Editor/Typing tab with file tree, typing area, and stats display."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from typing import Optional, List
from app.file_tree import FileTreeWidget
from app.typing_area import TypingAreaWidget
from app.stats_display import StatsDisplayWidget
from app.sound_volume_widget import SoundVolumeWidget
from app.progress_bar_widget import ProgressBarWidget
from app import stats_db
from app.file_scanner import get_language_for_file

# Debug timing flag - should match ui_main.DEBUG_STARTUP_TIMING
DEBUG_STARTUP_TIMING = True


class EditorTab(QWidget):
    """Complete editor/typing tab with tree, typing area, and stats."""
    
    def __init__(self, parent=None):
        if DEBUG_STARTUP_TIMING:
            import time
            t_start = time.time()
        
        super().__init__(parent)
        self.current_file: Optional[str] = None
        self._loaded = False  # Lazy loading flag
        
        # Main layout with placeholder
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Placeholder for lazy loading
        placeholder = QLabel("Loading editor...")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #888888; padding: 40px; font-size: 14pt;")
        main_layout.addWidget(placeholder)
        
        if DEBUG_STARTUP_TIMING:
            print(f"    [EditorTab] TOTAL (lazy): {time.time() - t_start:.3f}s")
    
    def ensure_loaded(self):
        """Lazy initialization of the editor tab UI."""
        if self._loaded:
            return
        
        if DEBUG_STARTUP_TIMING:
            import time
            t_start = time.time()
        
        # Clear placeholder
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Horizontal splitter: file tree | typing area
        h_splitter = QSplitter(Qt.Horizontal)
        
        # Left side: File tree
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        self.file_tree = FileTreeWidget()
        if DEBUG_STARTUP_TIMING:
            print(f"    [EditorTab-LAZY] FileTreeWidget: {time.time() - t:.3f}s")
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
        
        # Instant Death mode toggle
        from app import settings
        instant_death_enabled = settings.get_setting("instant_death_mode", "0") == "1"
        self.instant_death_btn = QPushButton("💀 Instant Death: Enabled" if instant_death_enabled else "💀 Instant Death: Disabled")
        self.instant_death_btn.setCheckable(True)
        self.instant_death_btn.setChecked(instant_death_enabled)
        self.instant_death_btn.setToolTip("Reset to top on any mistake")
        self.instant_death_btn.clicked.connect(self.on_instant_death_toggled)
        self._update_instant_death_style()
        toolbar.addWidget(self.instant_death_btn)
        
        toolbar.addStretch()
        
        # Sound volume widget
        self.sound_widget = SoundVolumeWidget()
        self.sound_widget.volume_changed.connect(self.on_sound_volume_changed)
        self.sound_widget.enabled_changed.connect(self.on_sound_enabled_changed)
        toolbar.addWidget(self.sound_widget)
        
        right_layout.addLayout(toolbar)
        
        # Vertical splitter: typing area | stats
        v_splitter = QSplitter(Qt.Vertical)
        
        # Typing area (larger)
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        self.typing_area = TypingAreaWidget()
        if DEBUG_STARTUP_TIMING:
            print(f"    [EditorTab-LAZY] TypingAreaWidget: {time.time() - t:.3f}s")
        self.typing_area.stats_updated.connect(self.on_stats_updated)
        self.typing_area.session_completed.connect(self.on_session_completed)
        self.typing_area.mistake_occurred.connect(self.on_mistake_occurred)
        v_splitter.addWidget(self.typing_area)
        
        # Container for progress bar and stats
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(5)
        
        # Progress bar section (full width)
        progress_widget = QWidget()
        progress_layout = QHBoxLayout(progress_widget)
        progress_layout.setContentsMargins(5, 3, 5, 3)
        
        self.progress_bar = ProgressBarWidget()
        progress_layout.addWidget(self.progress_bar, stretch=1)  # Full width
        
        self.progress_label = QLabel("0%")
        self.progress_label.setMinimumWidth(45)
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #888888; font-weight: bold;")
        progress_layout.addWidget(self.progress_label, stretch=0)
        
        bottom_layout.addWidget(progress_widget)
        
        # Stats display
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        self.stats_display = StatsDisplayWidget()
        if DEBUG_STARTUP_TIMING:
            print(f"    [EditorTab-LAZY] StatsDisplayWidget: {time.time() - t:.3f}s")
        bottom_layout.addWidget(self.stats_display)
        
        v_splitter.addWidget(bottom_container)
        
        # Set initial sizes (75% typing, 25% bottom section with progress+stats)
        v_splitter.setSizes([750, 250])
        
        right_layout.addWidget(v_splitter)
        h_splitter.addWidget(right_widget)
        
        # Set initial sizes (30% tree, 70% typing)
        h_splitter.setSizes([300, 700])
        
        self.layout().addWidget(h_splitter)
        
        # Timer for updating stats display
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(100)  # Update every 100ms
        
        self._loaded = True
        
        if DEBUG_STARTUP_TIMING:
            print(f"    [EditorTab-LAZY] Load complete: {time.time() - t_start:.3f}s")
    
    def showEvent(self, event):
        """Trigger lazy loading when tab is shown."""
        super().showEvent(event)
        self.ensure_loaded()
    
    def load_folder(self, folder_path: str):
        """Load a single folder for practice."""
        self.ensure_loaded()
        self.file_tree.load_folder(folder_path)
    
    def load_folders(self, folder_paths: List[str]):
        """Load multiple folders for practice."""
        self.ensure_loaded()
        self.file_tree.load_folders(folder_paths)
    
    def load_language_files(self, language: str, files: List[str]):
        """Load files filtered by language."""
        self.ensure_loaded()
        self.file_tree.load_language_files(language, files)
    
    def on_file_selected(self, file_path: str):
        """Handle file selection from tree."""
        self.ensure_loaded()
        # Save progress of current file if any
        if self.current_file and self.typing_area.engine:
            self._save_current_progress()
        
        # Load new file
        self.current_file = file_path
        self.typing_area.load_file(file_path)
        self.typing_area.setFocus()
        self.file_tree.refresh_file_stats(file_path)
        
        # Update stats display
        self.on_stats_updated()
    
    def on_stats_updated(self):
        """Handle stats update from typing area."""
        if not self._loaded:
            return
        stats = self.typing_area.get_stats()
        self.stats_display.update_stats(stats)
        
        # Update progress bar
        if self.typing_area.engine:
            cursor_pos = self.typing_area.engine.state.cursor_position
            total_chars = len(self.typing_area.engine.state.content)
            self.progress_bar.set_progress(cursor_pos, total_chars)
            self.progress_label.setText(self.progress_bar.get_progress_text())
    
    def update_display(self):
        """Periodic update of stats display."""
        if not self._loaded:
            return
        if self.typing_area.engine and not self.typing_area.engine.state.is_paused and not self.typing_area.engine.state.is_finished:
            self.typing_area.engine.update_elapsed_time()
            self.on_stats_updated()
    
    def on_reset_clicked(self):
        """Handle reset button click."""
        self.ensure_loaded()
        if not self.current_file:
            return
        self.typing_area.reset_session()
        # Clear saved progress
        stats_db.clear_session_progress(self.current_file)
        self.file_tree.refresh_file_stats(self.current_file)
        # Reset progress bar
        self.progress_bar.reset()
        self.progress_label.setText("0%")
    
    def on_instant_death_toggled(self, enabled: bool):
        """Handle instant death mode toggle."""
        from app import settings
        settings.set_setting("instant_death_mode", "1" if enabled else "0")
        self.instant_death_btn.setText("💀 Instant Death: Enabled" if enabled else "💀 Instant Death: Disabled")
        self._update_instant_death_style()
        
        # Update the typing area's instant death mode
        if hasattr(self, 'typing_area') and self.typing_area.engine:
            self.typing_area.engine.instant_death_mode = enabled
    
    def _update_instant_death_style(self):
        """Update instant death button styling based on state."""
        if self.instant_death_btn.isChecked():
            # Enabled - green/success color
            self.instant_death_btn.setStyleSheet("""
                QPushButton {
                    background-color: #a3be8c;
                    color: #2e3440;
                    border: none;
                    padding: 8px 12px;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #b4d0a0;
                }
            """)
        else:
            # Disabled - same as reset button (neutral)
            self.instant_death_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4c566a;
                    color: #eceff4;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #5e81ac;
                }
            """)
    
    def on_mistake_occurred(self):
        """Handle mistake in typing area - reset if instant death mode is enabled."""
        from app import settings
        instant_death_enabled = settings.get_setting("instant_death_mode", "0") == "1"
        if instant_death_enabled:
            self.on_reset_clicked()
    
    def on_session_completed(self):
        """Handle completed typing session."""
        if not self._loaded:
            return
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

        stats_db.record_session_history(
            file_path=self.current_file,
            language=get_language_for_file(self.current_file),
            wpm=stats["wpm"],
            accuracy=stats["accuracy"],
            total_keystrokes=stats["total"],
            correct_keystrokes=stats["correct"],
            incorrect_keystrokes=stats["incorrect"],
            duration=stats["time"],
            completed=True,
        )

        # Clear session progress and refresh tree highlights/stats
        stats_db.clear_session_progress(self.current_file)
        self.file_tree.refresh_file_stats(self.current_file)

        parent_window = self.window()
        if hasattr(parent_window, "refresh_languages_tab"):
            parent_window.refresh_languages_tab()
        if hasattr(parent_window, "refresh_history_tab"):
            parent_window.refresh_history_tab()
        
        # Show completion message
        QMessageBox.information(
            self,
            "Session Complete!",
            f"Congratulations! You completed the file.\n\n"
            f"WPM: {stats['wpm']:.1f}\n"
            f"Accuracy: {stats['accuracy']*100:.1f}%\n"
            f"Time: {stats['time']:.1f}s"
        )
    
    def _save_current_progress(self):
        """Save progress of current file."""
        if not self._loaded:
            return
        if not self.current_file or not self.typing_area.engine:
            return
        
        engine = self.typing_area.engine
        engine.pause()
        engine.update_elapsed_time()
        
        if engine.state.is_complete():
            stats_db.clear_session_progress(self.current_file)
        elif engine.state.cursor_position > 0:
            stats_db.save_session_progress(
                self.current_file,
                cursor_pos=engine.state.cursor_position,
                total_chars=len(engine.state.content),
                correct=engine.state.correct_keystrokes,
                incorrect=engine.state.incorrect_keystrokes,
                time=engine.state.elapsed_time,
                is_paused=True
            )
        else:
            stats_db.clear_session_progress(self.current_file)

        self.file_tree.refresh_incomplete_sessions()
        self.file_tree.refresh_file_stats(self.current_file)

    def save_active_progress(self):
        """Pause the active session and persist progress, if any."""
        self._save_current_progress()
    
    def on_sound_volume_changed(self, volume: int):
        """Handle volume change from sound widget."""
        from app import settings
        from app.sound_manager import get_sound_manager
        
        settings.set_setting("sound_volume", str(volume))
        get_sound_manager().set_volume(volume / 100.0)
    
    def on_sound_enabled_changed(self, enabled: bool):
        """Handle sound enabled/disabled from sound widget."""
        from app import settings
        from app.sound_manager import get_sound_manager
        
        settings.set_setting("sound_enabled", "1" if enabled else "0")
        get_sound_manager().set_enabled(enabled)
    
    def update_progress_bar_color(self):
        """Update progress bar when color settings change."""
        if self._loaded and hasattr(self, 'progress_bar'):
            self.progress_bar.update()
    
    def apply_theme(self):
        """Apply current theme to stats display."""
        if self._loaded and hasattr(self, 'stats_display'):
            self.stats_display.apply_theme()
    
    def closeEvent(self, event):
        """Handle widget close - save progress."""
        self._save_current_progress()
        super().closeEvent(event)
