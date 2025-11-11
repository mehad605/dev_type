"""Editor/Typing tab with file tree, typing area, and stats display."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton, QLabel, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QKeyEvent
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
        
        # Ghost replay state
        self.is_replaying = False
        self._replay_timer = QTimer(self)
        self._replay_timer.setSingleShot(True)
        self._replay_timer.timeout.connect(self._advance_ghost_replay)
        self._replay_keystrokes: List[dict] = []
        self._replay_index = 0
        self._replay_prev_timestamp = 0
        self._current_ghost_data: Optional[dict] = None
        self._instant_death_pre_replay: Optional[bool] = None
        self._instant_death_tooltip_pre_replay: Optional[str] = None
        
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
        
        # Ghost replay button
        self.ghost_btn = QPushButton("👻")
        self.ghost_btn.setToolTip("Watch Ghost Replay (Best Run)")
        self.ghost_btn.setFixedHeight(34)
        self.ghost_btn.setMinimumWidth(70)
        self.ghost_btn.clicked.connect(self.on_ghost_clicked)
        self.ghost_btn.setStyleSheet("""
            QPushButton {
                background-color: #4c566a;
                border: none;
                border-radius: 4px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #5e81ac;
            }
            QPushButton:disabled {
                background-color: #3b4252;
                color: #666666;
            }
        """)
        toolbar.addWidget(self.ghost_btn)
        
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
        # Ensure engine matches current instant death state
        self._set_instant_death_mode(self.instant_death_btn.isChecked(), persist=False)
        
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
        self.stats_display.pause_requested.connect(self.toggle_pause)
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
        
        # Update ghost button state
        self._update_ghost_button()
        
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
    
    def _set_instant_death_mode(self, enabled: bool, persist: bool):
        """Apply instant death mode to settings, button, and engine."""
        if persist:
            from app import settings
            settings.set_setting("instant_death_mode", "1" if enabled else "0")
        self.instant_death_btn.blockSignals(True)
        self.instant_death_btn.setChecked(enabled)
        self.instant_death_btn.blockSignals(False)
        self.instant_death_btn.setText("💀 Instant Death: Enabled" if enabled else "💀 Instant Death: Disabled")
        self._update_instant_death_style()
        if hasattr(self, 'typing_area') and self.typing_area.engine:
            self.typing_area.engine.instant_death_mode = enabled

    def on_instant_death_toggled(self, enabled: bool):
        """Handle instant death mode toggle."""
        self._set_instant_death_mode(enabled, persist=True)
    
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

        # Check and save ghost if this is a new best
        self._check_and_save_ghost(stats)

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
    
    def toggle_pause(self):
        """Toggle pause/unpause state."""
        if not self._loaded or not hasattr(self, 'typing_area'):
            return
        
        if self.typing_area.engine:
            if self.typing_area.engine.state.is_paused:
                # Unpause (resume)
                self.typing_area.engine.start()
            else:
                # Pause
                self.typing_area.engine.pause()
            
            # Update stats immediately
            self.on_stats_updated()
    
    def update_progress_bar_color(self):
        """Update progress bar when color settings change."""
        if self._loaded and hasattr(self, 'progress_bar'):
            self.progress_bar.update()
    
    def apply_theme(self):
        """Apply current theme to stats display."""
        if self._loaded and hasattr(self, 'stats_display'):
            self.stats_display.apply_theme()
    
    def _check_and_save_ghost(self, stats: dict):
        """Check if this session is a new best and save ghost if so."""
        from app.ghost_manager import get_ghost_manager
        from datetime import datetime
        
        ghost_mgr = get_ghost_manager()
        wpm = stats["wpm"]
        accuracy = stats["accuracy"]
        instant_death_enabled = self.instant_death_btn.isChecked()
        
        # Check if this is better than existing ghost
        if ghost_mgr.should_save_ghost(self.current_file, wpm):
            # Get keystroke data from typing area
            keystrokes = self.typing_area.get_ghost_data()
            
            # Get final stats from the engine
            final_stats = self.typing_area.engine.get_final_stats()

            # Save the ghost
            success = ghost_mgr.save_ghost(
                self.current_file,
                wpm,
                accuracy,
                keystrokes,
                datetime.now().isoformat(),
                final_stats=final_stats,
                instant_death=instant_death_enabled
            )
            
            if success:
                # Notify user about new best
                QMessageBox.information(
                    self,
                    "New Best! 👻",
                    f"Congratulations! This is your best run for this file.\n\n"
                    f"WPM: {wpm:.1f}\n"
                    f"Accuracy: {accuracy * 100:.1f}%\n\n"
                    f"Ghost replay saved! Click the 👻 button to watch it."
                )
                
                # Update ghost button state
                self._update_ghost_button()
    
    def _update_ghost_button(self):
        """Update ghost button enabled state based on availability."""
        if not self._loaded or not hasattr(self, 'ghost_btn'):
            return
        
        if self.current_file:
            from app.ghost_manager import get_ghost_manager
            ghost_mgr = get_ghost_manager()
            has_ghost = ghost_mgr.has_ghost(self.current_file)
            self.ghost_btn.setEnabled(has_ghost)
            
            if has_ghost:
                # Show ghost stats in tooltip
                stats = ghost_mgr.get_ghost_stats(self.current_file)
                if stats:
                    instant_line = ""
                    if stats.get("instant_death") is not None:
                        instant_line = "\nInstant Death: " + ("On" if stats["instant_death"] else "Off")
                    self.ghost_btn.setToolTip(
                        f"Watch Ghost Replay\n\n"
                        f"Best: {stats['wpm']:.1f} WPM at {stats['accuracy']:.1f}% accuracy\n"
                        f"Recorded: {stats['date'][:10]}" + instant_line
                    )
            else:
                self.ghost_btn.setToolTip("Ghost Not Available\n\nComplete this file to create a ghost replay!")
        else:
            self.ghost_btn.setEnabled(False)
    
    def on_ghost_clicked(self):
        """Handle ghost button click - show replay."""
        # If replay is running, treat button as stop control
        if self.is_replaying:
            self._finalize_ghost_replay(cancelled=True)
            return
        
        if not self.current_file:
            QMessageBox.information(
                self,
                "No File",
                "Please select a file to watch its ghost replay."
            )
            return
        
        from app.ghost_manager import get_ghost_manager
        ghost_mgr = get_ghost_manager()
        ghost_data = ghost_mgr.load_ghost(self.current_file)
        
        if not ghost_data:
            QMessageBox.information(
                self,
                "Ghost Not Available",
                "No ghost replay available for this file.\n\n"
                "Complete the file with a good WPM to create one!"
            )
            return
        
        # Show ghost stats and confirmation
        result = QMessageBox.question(
            self,
            "Ghost Replay",
            f"Watch best run for this file?\n\n"
            f"WPM: {ghost_data['wpm']:.1f}\n"
            f"Accuracy: {ghost_data['acc']:.1f}%\n"
            f"Recorded: {ghost_data['date'][:19]}\n"
            f"Keystrokes: {len(ghost_data['keys'])}\n\n"
            f"The replay will automatically type through the file.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            self.start_ghost_replay(ghost_data)
    
    def start_ghost_replay(self, ghost_data: dict):
        """Begin a ghost replay using the provided keystroke data."""
        keystrokes = ghost_data.get("keys", [])
        if not keystrokes:
            QMessageBox.warning(
                self,
                "Ghost Replay",
                "This ghost does not contain any keystrokes to replay."
            )
            return

        # If a replay is already active, cancel it first
        if self.is_replaying:
            self._finalize_ghost_replay(cancelled=True)

        self.is_replaying = True
        self._current_ghost_data = ghost_data
        self._replay_keystrokes = keystrokes
        self._replay_index = 0
        self._replay_prev_timestamp = keystrokes[0].get("t", 0)

        # Sync instant death mode for replay and lock the control
        recorded_instant_death = ghost_data.get("instant_death_mode")
        self._instant_death_pre_replay = self.instant_death_btn.isChecked()
        self._instant_death_tooltip_pre_replay = self.instant_death_btn.toolTip()
        if recorded_instant_death is not None:
            self._set_instant_death_mode(bool(recorded_instant_death), persist=False)
        self.instant_death_btn.setEnabled(False)
        self.instant_death_btn.setToolTip("Instant Death is locked during replay")

        # Prepare typing area and UI
        self.typing_area.stop_ghost_recording()
        self.typing_area.reset_session()
        self.typing_area.setEnabled(False)
        self.typing_area.setFocus()

        self.file_tree.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.reset_btn.setText("⏸ Replay Running")

        self.ghost_btn.setText("🛑 Stop")
        self.ghost_btn.setToolTip("Stop the ghost replay")

        # Ensure timer is ready
        if self._replay_timer.isActive():
            self._replay_timer.stop()

        # Kick off the replay immediately
        self._replay_timer.start(0)

    def _advance_ghost_replay(self):
        """Advance the replay by one keystroke."""
        if not self.is_replaying or self._replay_index >= len(self._replay_keystrokes):
            # Nothing to play; finish gracefully
            self._finalize_ghost_replay(cancelled=False)
            return

        keystroke = self._replay_keystrokes[self._replay_index]
        key_char = keystroke.get("k", "")
        timestamp = keystroke.get("t", self._replay_prev_timestamp)

        self._dispatch_ghost_key(key_char)

        self._replay_index += 1

        if self._replay_index >= len(self._replay_keystrokes):
            self._finalize_ghost_replay(cancelled=False)
            return

        next_timestamp = self._replay_keystrokes[self._replay_index].get("t", timestamp)
        delay = max(0, int(next_timestamp - timestamp))
        self._replay_prev_timestamp = next_timestamp
        self._replay_timer.start(delay)

    def _dispatch_ghost_key(self, key_char: str):
        """Send a single keystroke to the typing area."""
        if not key_char:
            return

        # Determine key code and text
        modifiers = Qt.NoModifier
        if key_char == '\b':
            key_code = Qt.Key_Backspace
            text = ""
        elif key_char == '\n':
            key_code = Qt.Key_Return
            text = "\n"
        elif key_char == '\t':
            key_code = Qt.Key_Tab
            text = "\t"
        elif key_char == '<CTRL-BACKSPACE>':
            key_code = Qt.Key_Backspace
            text = ""
            modifiers = Qt.ControlModifier
        elif key_char == ' ':
            key_code = Qt.Key_Space
            text = " "
        else:
            text = key_char
            key_code = ord(key_char.upper()) if len(key_char) == 1 else Qt.Key_unknown
        event = QKeyEvent(QEvent.KeyPress, key_code, modifiers, text)

        # Temporarily enable the typing area to receive the event
        was_enabled = self.typing_area.isEnabled()
        if not was_enabled:
            self.typing_area.setEnabled(True)

        QApplication.sendEvent(self.typing_area, event)

        if not was_enabled:
            self.typing_area.setEnabled(False)

    def _finalize_ghost_replay(self, cancelled: bool):
        """Clean up replay state and restore the UI."""
        if self._replay_timer.isActive():
            self._replay_timer.stop()

        was_replaying = self.is_replaying
        self.is_replaying = False

        self._replay_keystrokes = []
        self._replay_index = 0
        self._replay_prev_timestamp = 0

        ghost_data = self._current_ghost_data
        self._current_ghost_data = None

        # Restore UI state
        self.typing_area.setEnabled(True)
        self.file_tree.setEnabled(True)
        self.reset_btn.setEnabled(True)
        self.reset_btn.setText("⟲ Reset to Top")

        self.ghost_btn.setText("👻")
        self._update_ghost_button()

        self.instant_death_btn.setEnabled(True)
        if self._instant_death_pre_replay is not None:
            self._set_instant_death_mode(self._instant_death_pre_replay, persist=False)
        if self._instant_death_tooltip_pre_replay is not None:
            self.instant_death_btn.setToolTip(self._instant_death_tooltip_pre_replay)
        else:
            self.instant_death_btn.setToolTip("Reset to top on any mistake")
        self._instant_death_pre_replay = None
        self._instant_death_tooltip_pre_replay = None

        if cancelled:
            self.typing_area.reset_session()
            self.on_stats_updated()
        elif was_replaying:
            # Replay completed successfully - show original final stats if we have them
            if ghost_data and ghost_data.get("final_stats"):
                self.stats_display.update_stats(ghost_data["final_stats"])
                self.progress_bar.set_progress(1, 1)
                self.progress_label.setText("100%")
            else:
                self.on_stats_updated()

            QMessageBox.information(
                self,
                "Replay Complete",
                "Ghost replay finished!\n\nClick Reset to start typing yourself."
            )

        # Restart recording for the user's next attempt
        self.typing_area.start_ghost_recording()

        self.typing_area.setFocus()

    def closeEvent(self, event):
        """Handle widget close - save progress."""
        if self.is_replaying:
            self._finalize_ghost_replay(cancelled=True)
        self.save_active_progress()
        super().closeEvent(event)
