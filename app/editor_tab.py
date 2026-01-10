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
from app.session_result_dialog import SessionResultDialog
from app import stats_db
from app.file_scanner import get_language_for_file
from app.typing_engine import TypingEngine
import time

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
        
        # Ghost race state
        self.is_racing = False
        self._race_pending_start = False
        self._current_ghost_data: Optional[dict] = None
        self._ghost_engine: Optional[TypingEngine] = None
        self._ghost_keystrokes: List[dict] = []
        self._ghost_index = 0
        self._ghost_prev_timestamp = 0
        self._ghost_cursor_position = 0
        self._display_ghost_progress = False
        self._race_start_perf: Optional[float] = None
        self._user_finish_elapsed: Optional[float] = None
        self._ghost_finish_elapsed: Optional[float] = None
        self._race_paused_at: Optional[float] = None
        self._instant_death_pre_race: Optional[bool] = None
        self._instant_death_tooltip_pre_race: Optional[str] = None
        
        self._ghost_timer = QTimer(self)
        self._ghost_timer.setSingleShot(True)
        self._ghost_timer.timeout.connect(self._advance_ghost_race)
        
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
        
        # Crash recovery: If app crashed during a ghost race, restore original instant death mode
        backup_mode = settings.get_setting("_race_instant_death_backup")
        if backup_mode is not None:
            # Crash happened during race - restore user's original preference
            settings.set_setting("instant_death_mode", backup_mode)
            settings.remove_setting("_race_instant_death_backup")
        
        instant_death_enabled = settings.get_setting("instant_death_mode", settings.get_default("instant_death_mode")) == "1"
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
        self.typing_area.first_key_pressed.connect(self._on_first_race_key)
        self.typing_area.typing_resumed.connect(self._on_typing_resumed)
        self.typing_area.typing_paused.connect(self._on_typing_paused)
        v_splitter.addWidget(self.typing_area)
        # Ensure engine matches current instant death state
        self._set_instant_death_mode(self.instant_death_btn.isChecked(), persist=False)
        
        # Connect to parent window signals for dynamic updates
        window = self.window()
        if hasattr(window, 'cursor_changed'):
            # Connect signals
            window.cursor_changed.connect(self.typing_area.update_cursor)
            window.font_changed.connect(self.typing_area.update_font)
            window.colors_changed.connect(self.typing_area.update_colors)
            window.space_char_changed.connect(self.typing_area.update_space_char)
            window.pause_delay_changed.connect(self.typing_area.update_pause_delay)
            window.allow_continue_changed.connect(self.typing_area.update_allow_continue)
            window.show_typed_changed.connect(self.typing_area.update_show_typed_characters)
            
            # Also connect progress bar color
            window.colors_changed.connect(self.apply_theme)
            
            # Apply current settings immediately
            from app import settings
            
            # Cursor
            c_type = settings.get_setting("cursor_type", settings.get_default("cursor_type"))
            c_style = settings.get_setting("cursor_style", settings.get_default("cursor_style"))
            self.typing_area.update_cursor(c_type, c_style)
            
            # Font
            f_family = settings.get_setting("font_family", settings.get_default("font_family"))
            f_size = settings.get_setting_int("font_size", 12, min_val=8, max_val=32)
            self.typing_area.update_font(f_family, f_size, False)
            
            # Colors
            self.typing_area.update_colors()
            self.update_progress_bar_color()

        
        # Container for progress bar and stats
        self.bottom_container = QWidget()
        bottom_layout = QVBoxLayout(self.bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(5)
        
        # User progress bar section
        user_progress_widget = QWidget()
        user_progress_layout = QHBoxLayout(user_progress_widget)
        user_progress_layout.setContentsMargins(5, 3, 5, 3)
        
        self.user_label = QLabel("You:")
        self.user_label.setStyleSheet("color: #888888; font-weight: bold;")
        self.user_label.setMinimumWidth(35)
        user_progress_layout.addWidget(self.user_label, stretch=0)
        
        self.user_progress_bar = ProgressBarWidget(bar_type="user")
        user_progress_layout.addWidget(self.user_progress_bar, stretch=1)
        
        self.user_progress_label = QLabel("0%")
        self.user_progress_label.setMinimumWidth(45)
        self.user_progress_label.setAlignment(Qt.AlignCenter)
        self.user_progress_label.setStyleSheet("color: #888888; font-weight: bold;")
        user_progress_layout.addWidget(self.user_progress_label, stretch=0)
        
        bottom_layout.addWidget(user_progress_widget)
        
        # Ghost progress bar section (initially hidden)
        ghost_progress_widget = QWidget()
        ghost_progress_layout = QHBoxLayout(ghost_progress_widget)
        ghost_progress_layout.setContentsMargins(5, 3, 5, 3)
        
        self.ghost_label = QLabel("Ghost:")
        ghost_color = settings.get_setting("ghost_text_color", settings.get_default("ghost_text_color"))
        self.ghost_label.setStyleSheet(f"color: {ghost_color}; font-weight: bold;")
        self.ghost_label.setMinimumWidth(35)
        ghost_progress_layout.addWidget(self.ghost_label, stretch=0)
        
        self.ghost_progress_bar = ProgressBarWidget(bar_type="ghost")
        ghost_progress_layout.addWidget(self.ghost_progress_bar, stretch=1)
        
        self.ghost_progress_label = QLabel("0%")
        self.ghost_progress_label.setMinimumWidth(45)
        self.ghost_progress_label.setAlignment(Qt.AlignCenter)
        self.ghost_progress_label.setStyleSheet(f"color: {ghost_color}; font-weight: bold;")
        ghost_progress_layout.addWidget(self.ghost_progress_label, stretch=0)
        
        self.ghost_progress_widget = ghost_progress_widget
        self.ghost_progress_widget.setVisible(False)
        bottom_layout.addWidget(ghost_progress_widget)
        
        # Stats display
        if DEBUG_STARTUP_TIMING:
            t = time.time()
        self.stats_display = StatsDisplayWidget()
        self.stats_display.pause_requested.connect(self.toggle_pause)
        self.stats_display.reset_requested.connect(self.on_reset_clicked)
        if DEBUG_STARTUP_TIMING:
            print(f"    [EditorTab-LAZY] StatsDisplayWidget: {time.time() - t:.3f}s")
        bottom_layout.addWidget(self.stats_display)
        
        v_splitter.addWidget(self.bottom_container)
        
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
        self.apply_theme()
        
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
        
        if self.is_racing or self._race_pending_start:
            self._finalize_ghost_race(cancelled=True)
        
        # Save progress of current file if any
        if self.current_file and self.typing_area.engine:
            self._save_current_progress()
        
        # Clear WPM history for new file
        self.stats_display.clear_wpm_history()
        
        # Load new file
        self.current_file = file_path
        self.typing_area.load_file(file_path)
        self.typing_area.setFocus()
        self.file_tree.refresh_file_stats(file_path)
        self.file_tree.refresh_incomplete_sessions()
        
        # Reset progress bars to show 0% on new file load
        self.user_progress_bar.reset()
        self.user_progress_label.setText("0%")
        self.ghost_progress_bar.reset()
        
        self._display_ghost_progress = False
        self._ghost_cursor_position = 0
        self.ghost_progress_widget.setVisible(False)
        self.typing_area.clear_ghost_progress()
        
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
        self._update_progress_indicator()
    
    def _update_progress_indicator(self):
        """Refresh the progress bars."""
        if not self._loaded or not self.typing_area.engine:
            return
        
        total_chars = len(self.typing_area.engine.state.content)
        user_pos = self.typing_area.engine.state.cursor_position
        
        # Update user progress bar
        self.user_progress_bar.set_progress(user_pos, total_chars)
        user_pct = (user_pos / total_chars * 100) if total_chars > 0 else 0
        self.user_progress_label.setText(f"{user_pct:.0f}%")
        
        # Update ghost progress bar if racing
        if self._display_ghost_progress and hasattr(self, 'ghost_progress_bar'):
            ghost_pos = self._ghost_cursor_position
            self.ghost_progress_bar.set_progress(ghost_pos, total_chars)
            ghost_pct = (ghost_pos / total_chars * 100) if total_chars > 0 else 0
            self.ghost_progress_label.setText(f"{ghost_pct:.0f}%")
    
    def update_display(self):
        """Periodic update of stats display."""
        if not self._loaded:
            return
        if self.typing_area.engine and not self.typing_area.engine.state.is_paused and not self.typing_area.engine.state.is_finished:
            self.on_stats_updated()
    
    def on_reset_clicked(self):
        """Handle reset button click."""
        self._perform_reset(cancel_race=True)
    
    def _perform_reset(self, cancel_race: bool = True):
        """Reset typing session and optionally cancel an active race."""
        self.ensure_loaded()
        if not self.current_file:
            return
        
        if cancel_race and (self.is_racing or self._race_pending_start):
            self._finalize_ghost_race(cancelled=True)
        
        self.typing_area.reset_session()
        stats_db.clear_session_progress(self.current_file)
        self.file_tree.refresh_file_stats(self.current_file)
        self.file_tree.refresh_incomplete_sessions()
        
        self._display_ghost_progress = False
        self._ghost_cursor_position = 0
        self.typing_area.clear_ghost_progress()
        self.ghost_progress_widget.setVisible(False)
        self.user_progress_bar.reset()
        self.ghost_progress_bar.reset()
        self.user_progress_label.setText("0%")
        self.ghost_progress_label.setText("0%")
    
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
        instant_death_enabled = settings.get_setting("instant_death_mode", settings.get_default("instant_death_mode")) == "1"
        if instant_death_enabled:
            if self.is_racing or self._race_pending_start:
                # During a race, reset cursor to beginning but keep stats running
                # The ghost should continue unaffected - don't stop the ghost timer!
                # Save ghost state before reset
                ghost_cursor = self._ghost_cursor_position
                
                # Reset user's cursor only - stats keep accumulating!
                self.typing_area.reset_cursor_only()
                
                # Restore ghost progress after reset
                self.typing_area.set_ghost_progress_limit(ghost_cursor)
                
                # Reset the first key flag so user has to press first key again
                self.typing_area._has_emitted_first_key = False
                
                # Keep the race running! Don't set to pending.
                # The ghost timer keeps advancing, user can just start typing again
                if self.is_racing:
                    # Race is still active, ghost keeps going
                    self.reset_btn.setText("⟲ Reset to Top")
                
                self.typing_area.setFocus()
                self._update_progress_indicator()
            else:
                self.on_reset_clicked()
    
    def on_session_completed(self):
        """Handle completed typing session."""
        if not self._loaded:
            return
        if not self.current_file or not self.typing_area.engine:
            return
        
        # Get final stats
        stats = self.typing_area.get_stats()
        
        # Check if this is a race completion - handle separately
        race_handled = self._handle_user_finished_race(stats)
        if race_handled:
            # Race flow handles all stats saving and display
            return
        
        # Normal (non-race) session completion
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
        
        # Update detailed key statistics for heatmap
        stats_db.update_key_stats(
            language=get_language_for_file(self.current_file),
            key_hits=stats.get("key_hits", {}),
            key_misses=stats.get("key_misses", {})
        )
        stats_db.update_key_confusions(
            language=get_language_for_file(self.current_file),
            key_confusions=stats.get("key_confusions", {})
        )
        stats_db.update_error_type_stats(
            language=get_language_for_file(self.current_file),
            errors=stats.get("error_types", {})
        )

        # Check and save ghost if this is a new best
        is_new_best = self._check_and_save_ghost(stats)

        # Clear session progress and refresh tree highlights/stats
        stats_db.clear_session_progress(self.current_file)
        self.file_tree.refresh_file_stats(self.current_file)

        parent_window = self.window()
        # Refresh language card stats (not full rescan, just update the card)
        if hasattr(parent_window, "refresh_language_stats"):
            parent_window.refresh_language_stats(self.current_file)
        if hasattr(parent_window, "refresh_history_tab"):
            parent_window.refresh_history_tab()
        if hasattr(parent_window, "refresh_stats_tab"):
            parent_window.refresh_stats_tab()
        
        # Show modern completion dialog
        theme_colors = self._get_theme_colors()
        user_keystrokes = self.typing_area.get_ghost_data() if hasattr(self.typing_area, 'get_ghost_data') else []
        
        # Get WPM history from stats display and add final data point
        wpm_history = self.stats_display.get_wpm_history()
        error_history = self.stats_display.get_error_history()
        
        # Add the final WPM at the final time to ensure graph ends at actual result
        # Use round() to match the display formatting (f"{time_val:.0f}s" uses rounding)
        final_second = round(stats["time"]) if stats["time"] > 0 else 0
        final_wpm = stats["wpm"]
        if final_second > 0 and final_wpm > 0:
            # If history is empty or last entry is before final second, add final point
            if not wpm_history or wpm_history[-1][0] < final_second:
                wpm_history.append((final_second, final_wpm))
            elif wpm_history and wpm_history[-1][0] == final_second:
                # Replace last point with final WPM (more accurate)
                wpm_history[-1] = (final_second, final_wpm)
        
        self.stats_display.clear_wpm_history()
        
        dialog = SessionResultDialog(
            parent=self,
            stats=stats,
            is_new_best=is_new_best,
            is_race=False,
            theme_colors=theme_colors,
            filename=self.current_file,
            user_keystrokes=user_keystrokes,
            wpm_history=wpm_history,
            error_history=error_history
        )
        dialog.exec()
    
    def _save_current_progress(self):
        """Save progress of current file."""
        if not self._loaded:
            return
        if not self.current_file or not self.typing_area.engine:
            return
        
        engine = self.typing_area.engine
        engine.pause()
        
        if engine.state.is_complete():
            stats_db.clear_session_progress(self.current_file)
        elif engine.state.cursor_position > 0:
            stats_db.save_session_progress(
                self.current_file,
                cursor_pos=engine.state.cursor_position,
                total_chars=len(engine.state.content),
                correct=engine.state.correct_keystrokes,
                incorrect=engine.state.incorrect_keystrokes,
                time=engine.get_elapsed_time(),
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
                
                # Resume ghost if racing
                if self.is_racing and not self._race_pending_start and self._race_paused_at is not None:
                    # Adjust start time to account for pause duration
                    pause_duration = time.perf_counter() - self._race_paused_at
                    if self._race_start_perf is not None:
                        self._race_start_perf += pause_duration
                    self._race_paused_at = None
                    
                    # Resume ghost timer
                    self._advance_ghost_race()
            else:
                # Pause
                self.typing_area.engine.pause()
                
                # Pause ghost if racing
                if self.is_racing:
                    self._race_paused_at = time.perf_counter()
                    if self._ghost_timer.isActive():
                        self._ghost_timer.stop()
            
            # Update stats immediately
            self.on_stats_updated()
    
    def update_progress_bar_color(self):
        """Update progress bars when color settings change."""
        if self._loaded:
            if hasattr(self, 'user_progress_bar'):
                self.user_progress_bar.update()
            if hasattr(self, 'ghost_progress_bar'):
                self.ghost_progress_bar.update()

    def update_ignore_settings(self):
        """Update file tree ignore settings."""
        if self._loaded and hasattr(self, 'file_tree'):
            self.file_tree.update_ignore_settings()
    
    def apply_theme(self):
        """Apply current theme to stats display and bottom container."""
        if not self._loaded:
            return
            
        from app import settings
        from app.themes import get_color_scheme
        
        theme = settings.get_setting("theme", settings.get_default("theme"))
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme(theme, scheme_name)
        
        # Apply background to bottom container
        if hasattr(self, 'bottom_container'):
            self.bottom_container.setStyleSheet(f"""
                QWidget {{
                    background-color: {scheme.bg_primary};
                    border-top: 1px solid {scheme.bg_secondary};
                }}
                QLabel {{
                    background-color: transparent;
                }}
            """)
            
        # Update labels
        label_style = f"color: {scheme.text_secondary}; font-weight: bold;"
        if hasattr(self, 'user_label'):
            self.user_label.setStyleSheet(label_style)
        if hasattr(self, 'user_progress_label'):
            self.user_progress_label.setStyleSheet(label_style)
        
        ghost_style = f"color: {settings.get_setting('ghost_progress_bar_color', '#8AB4F8')}; font-weight: bold;"
        if hasattr(self, 'ghost_label'):
            self.ghost_label.setStyleSheet(ghost_style)
        if hasattr(self, 'ghost_progress_label'):
            self.ghost_progress_label.setStyleSheet(ghost_style)

        # Update stats display
        if hasattr(self, 'stats_display'):
            self.stats_display.apply_theme()
            
        # Update progress bars
        self.update_progress_bar_color()
    
    def _check_and_save_ghost(self, stats: dict) -> bool:
        """Check if this session is a new best and save ghost if so. Returns True if new best."""
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
            
            # Get WPM and error history for graph display
            wpm_history = self.stats_display.get_wpm_history()
            error_history = self.stats_display.get_error_history()
            
            # Add the final WPM point
            final_second = round(stats["time"]) if stats.get("time", 0) > 0 else 0
            if final_second > 0 and wpm > 0:
                if not wpm_history or wpm_history[-1][0] < final_second:
                    wpm_history.append((final_second, wpm))
                elif wpm_history and wpm_history[-1][0] == final_second:
                    wpm_history[-1] = (final_second, wpm)

            # Save the ghost
            success = ghost_mgr.save_ghost(
                self.current_file,
                wpm,
                accuracy,
                keystrokes,
                datetime.now().isoformat(),
                final_stats=final_stats,
                instant_death=instant_death_enabled,
                wpm_history=wpm_history,
                error_history=error_history
            )
            
            if success:
                # Update ghost button state
                self._update_ghost_button()
                return True
        
        return False
    
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
                        "Race Your Ghost\n\n"
                        f"Best: {stats['wpm']:.1f} WPM at {stats['accuracy']:.1f}% accuracy\n"
                        f"Recorded: {stats['date'][:10]}{instant_line}"
                    )
                else:
                    self.ghost_btn.setToolTip("Race Your Ghost\n\nBest run data not available.")
            else:
                self.ghost_btn.setToolTip("Ghost Not Available\n\nComplete this file to unlock a ghost race!")
        else:
            self.ghost_btn.setEnabled(False)
            self.ghost_btn.setToolTip("Select a file to race your ghost.")
    
    def on_ghost_clicked(self):
        """Handle ghost button click - start or cancel a race."""
        if self.is_racing or self._race_pending_start:
            self._finalize_ghost_race(cancelled=True)
            return
        
        if not self.current_file:
            QMessageBox.information(self, "No File", "Please select a file to race against its ghost.")
            return
        
        from app.ghost_manager import get_ghost_manager
        ghost_mgr = get_ghost_manager()
        ghost_data = ghost_mgr.load_ghost(self.current_file)
        
        if not ghost_data:
            QMessageBox.information(
                self,
                "Ghost Not Available",
                "No ghost data available for this file.\n\nComplete the file with a strong run to create one!",
            )
            return
        
        # Start the race immediately - skip confirmation popup
        self.start_ghost_race(ghost_data)
    
    def start_ghost_race(self, ghost_data: dict):
        """Prepare the UI and engines for a ghost race."""
        keystrokes = ghost_data.get("keys", [])
        if not keystrokes:
            QMessageBox.warning(self, "Ghost Race", "This ghost does not contain any keystrokes to replay.")
            return
        
        self._current_ghost_data = ghost_data
        self._ghost_keystrokes = keystrokes
        self._ghost_index = 0
        self._ghost_prev_timestamp = 0
        self._ghost_cursor_position = 0
        self._ghost_finish_elapsed = ghost_data.get("final_stats", {}).get("time")
        self._user_finish_elapsed = None
        self._race_start_perf = None
        self._display_ghost_progress = True
        
        if self._ghost_timer.isActive():
            self._ghost_timer.stop()
        
        user_engine = self.typing_area.engine
        pause_delay = getattr(user_engine, "pause_delay", 7.0) if user_engine else 7.0
        # Ghost should always allow continuing through mistakes - it's just replaying a recording
        self._ghost_engine = TypingEngine(
            self.typing_area.original_content,
            pause_delay=pause_delay,
            allow_continue_mistakes=True,  # Ghost must always continue to replay correctly
        )
        
        self.typing_area.reset_session()
        stats_db.clear_session_progress(self.current_file)
        self.file_tree.refresh_file_stats(self.current_file)
        self.file_tree.refresh_incomplete_sessions()
        
        self.typing_area.clear_ghost_progress()
        self.typing_area.update_colors()  # Ensure ghost text color is applied
        self.typing_area.start_ghost_recording()
        self.ghost_progress_widget.setVisible(True)
        self._update_progress_indicator()
        
        self.file_tree.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.reset_btn.setText("⏳ Waiting for Start")
        self.ghost_btn.setText("🛑 Cancel")
        self.ghost_btn.setToolTip("Cancel the current ghost race")
        
        recorded_instant_death = ghost_data.get("instant_death_mode")
        self._instant_death_pre_race = self.instant_death_btn.isChecked()
        self._instant_death_tooltip_pre_race = self.instant_death_btn.toolTip()
        
        # Save backup to settings in case of crash during race
        from app import settings
        settings.set_setting("_race_instant_death_backup", "1" if self._instant_death_pre_race else "0")
        
        if recorded_instant_death is not None:
            # Temporarily apply ghost's instant death mode WITHOUT persisting to disk
            # This prevents corruption if app crashes during race
            self._set_instant_death_mode(bool(recorded_instant_death), persist=False)
        self.instant_death_btn.setEnabled(False)
        self.instant_death_btn.setToolTip("Instant Death is locked during the race")
        
        self._race_pending_start = True
        self.is_racing = False
        self.typing_area.setFocus()
    
    def _on_first_race_key(self):
        """Start the ghost playback on the user's first key press."""
        if not self._race_pending_start or not self._ghost_keystrokes:
            return
        
        self._race_pending_start = False
        self.is_racing = True
        self.reset_btn.setText("⟲ Reset to Top")
        self.reset_btn.setEnabled(False)
        self._race_start_perf = time.perf_counter()
        
        # Start ghost immediately - don't wait for first timestamp
        self._ghost_prev_timestamp = 0
        self._ghost_timer.start(0)  # Start immediately!
    
    def _on_typing_resumed(self):
        """Resume the ghost playback when user starts typing again after pause."""
        # Only resume ghost if we're in an active race (not pending start) and ghost is paused
        if self.is_racing and not self._race_pending_start and self._race_paused_at is not None:
            # Adjust start time to account for pause duration
            pause_duration = time.perf_counter() - self._race_paused_at
            if self._race_start_perf is not None:
                self._race_start_perf += pause_duration
            self._race_paused_at = None
            
            # Resume ghost timer
            self._advance_ghost_race()

    def _on_typing_paused(self):
        """Pause the ghost playback when user auto-pauses due to inactivity."""
        # Only pause ghost if we're in an active race and not already paused
        if self.is_racing and not self._race_pending_start and self._race_paused_at is None:
            self._race_paused_at = time.perf_counter()
            if self._ghost_timer.isActive():
                self._ghost_timer.stop()
    
    
    def _advance_ghost_race(self):
        """Advance the ghost playback timeline."""
        if not self.is_racing or self._ghost_index >= len(self._ghost_keystrokes):
            self._handle_ghost_finish()
            return
        
        keystroke = self._ghost_keystrokes[self._ghost_index]
        key_char = keystroke.get("k", "")
        timestamp = keystroke.get("t", self._ghost_prev_timestamp)
        
        self._apply_ghost_keystroke(key_char)
        self._ghost_index += 1
        self._ghost_prev_timestamp = timestamp
        
        if self._ghost_index >= len(self._ghost_keystrokes):
            self._handle_ghost_finish()
            return
        
        next_timestamp = self._ghost_keystrokes[self._ghost_index].get("t", timestamp)
        delay = max(0, int(next_timestamp - timestamp))
        self._ghost_timer.start(delay)
    
    def _apply_ghost_keystroke(self, key_char: str):
        """Advance the ghost engine using a recorded keystroke."""
        if not self._ghost_engine:
            return
        
        if key_char == "<CTRL-BACKSPACE>":
            self._ghost_engine.process_ctrl_backspace()
        elif key_char == "\b":
            self._ghost_engine.process_backspace()
        elif key_char == "\t":
            for _ in range(4):
                self._ghost_engine.process_keystroke(" ")
        elif key_char == "\n":
            self._ghost_engine.process_keystroke("\n")
        elif key_char == " ":
            self._ghost_engine.process_keystroke(" ")
        elif key_char:
            self._ghost_engine.process_keystroke(key_char)
        
        self._ghost_cursor_position = self._ghost_engine.state.cursor_position
        self.typing_area.set_ghost_progress_limit(self._ghost_cursor_position)
        self._update_progress_indicator()
    
    def _handle_ghost_finish(self):
        """Handle the ghost finishing its recorded run."""
        if self._ghost_timer.isActive():
            self._ghost_timer.stop()
        
        if self._ghost_engine:
            self._ghost_cursor_position = self._ghost_engine.state.cursor_position
        else:
            self._ghost_cursor_position = len(self.typing_area.original_content)
        
        self.typing_area.set_ghost_progress_limit(self._ghost_cursor_position)
        self._display_ghost_progress = True
        self.ghost_progress_widget.setVisible(True)
        self._update_progress_indicator()
        
        if self._ghost_finish_elapsed is None:
            if self._current_ghost_data and self._current_ghost_data.get("final_stats"):
                self._ghost_finish_elapsed = self._current_ghost_data["final_stats"].get("time")
            if self._ghost_finish_elapsed is None and self._ghost_keystrokes:
                self._ghost_finish_elapsed = self._ghost_keystrokes[-1].get("t", 0) / 1000.0
        
        # Ghost finished, but user continues - don't end race yet
        # Race will end when user finishes in _handle_user_finished_race
    
    def _handle_user_finished_race(self, stats: dict) -> bool:
        """Finalize race flow when the user finishes their run."""
        if not (self.is_racing or self._race_pending_start):
            return False
        
        if self._race_start_perf is not None:
            self._user_finish_elapsed = time.perf_counter() - self._race_start_perf
        else:
            self._user_finish_elapsed = stats.get("time")
        
        if self._ghost_timer.isActive():
            self._ghost_timer.stop()
        
        if self._ghost_finish_elapsed is None:
            if self._current_ghost_data and self._current_ghost_data.get("final_stats"):
                self._ghost_finish_elapsed = self._current_ghost_data["final_stats"].get("time")
            if self._ghost_finish_elapsed is None and self._ghost_keystrokes:
                self._ghost_finish_elapsed = self._ghost_keystrokes[-1].get("t", 0) / 1000.0
        
        if self._ghost_engine:
            self._ghost_cursor_position = self._ghost_engine.state.cursor_position
        self._display_ghost_progress = True
        self.ghost_progress_widget.setVisible(True)
        self._update_progress_indicator()
        
        # Determine winner based on finish times
        user_time = self._user_finish_elapsed
        ghost_time = self._ghost_finish_elapsed or float("inf")
        winner = "user" if user_time <= ghost_time else "ghost"
        
        # Save race results to database with corrected stats
        # Calculate accurate stats based on actual race time
        if user_time and user_time > 0:
            user_total_chars = len(self.typing_area.original_content) if self.typing_area.original_content else 0
            user_completed_chars = self.typing_area.engine.state.cursor_position if self.typing_area.engine else 0
            minutes = user_time / 60.0
            race_wpm = (user_completed_chars / 5.0) / minutes if minutes > 0 else 0.0
        else:
            race_wpm = stats.get("wpm", 0.0)
            user_total_chars = len(self.typing_area.original_content) if self.typing_area.original_content else 0
            user_completed_chars = self.typing_area.engine.state.cursor_position if self.typing_area.engine else 0
        
        # Calculate accuracy from engine state
        if self.typing_area.engine:
            total_keystrokes = self.typing_area.engine.state.total_keystrokes()
            if total_keystrokes > 0:
                race_accuracy = self.typing_area.engine.state.correct_keystrokes / total_keystrokes
            else:
                race_accuracy = 1.0
            race_correct = self.typing_area.engine.state.correct_keystrokes
            race_incorrect = self.typing_area.engine.state.incorrect_keystrokes
        else:
            race_accuracy = stats.get("accuracy", 1.0)
            race_correct = stats.get("correct", 0)
            race_incorrect = stats.get("incorrect", 0)
        
        # Only save if user completed the file
        if user_completed_chars >= user_total_chars:
            # Save to database with race stats
            stats_db.update_file_stats(
                self.current_file,
                wpm=race_wpm,
                accuracy=race_accuracy,
                completed=True
            )

            stats_db.record_session_history(
                file_path=self.current_file,
                language=get_language_for_file(self.current_file),
                wpm=race_wpm,
                accuracy=race_accuracy,
                total_keystrokes=race_correct + race_incorrect,
                correct_keystrokes=race_correct,
                incorrect_keystrokes=race_incorrect,
                duration=user_time,
                completed=True,
            )
            
            # Update detailed key statistics for heatmap
            if self.typing_area.engine:
                lang = get_language_for_file(self.current_file)
                stats_db.update_key_stats(
                    language=lang,
                    key_hits=self.typing_area.engine.state.key_hits,
                    key_misses=self.typing_area.engine.state.key_misses
                )
                stats_db.update_key_confusions(
                    language=lang,
                    key_confusions=self.typing_area.engine.state.key_confusions
                )
                stats_db.update_error_type_stats(
                    language=lang,
                    errors=self.typing_area.engine.state.error_types
                )

            # Check and save new ghost if this beat the old one
            race_stats = {
                "wpm": race_wpm,
                "accuracy": race_accuracy,
                "time": user_time,
                "correct": race_correct,
                "incorrect": race_incorrect,
                "total": race_correct + race_incorrect,
            }
            is_new_best = self._check_and_save_ghost(race_stats)

            # Clear session progress and refresh tree highlights/stats
            stats_db.clear_session_progress(self.current_file)
            self.file_tree.refresh_file_stats(self.current_file)

            parent_window = self.window()
            if hasattr(parent_window, "refresh_languages_tab"):
                parent_window.refresh_languages_tab()
            if hasattr(parent_window, "refresh_history_tab"):
                parent_window.refresh_history_tab()
            if hasattr(parent_window, "refresh_stats_tab"):
                parent_window.refresh_stats_tab()
        else:
            is_new_best = False
        
        self._finalize_ghost_race(cancelled=False, winner=winner, is_new_best=is_new_best)
        return True
    
    def _finalize_ghost_race(self, cancelled: bool, winner: Optional[str] = None, reason: Optional[str] = None, is_new_best: bool = False):
        """Clean up race state, restore UI, and optionally show results."""
        if self._ghost_timer.isActive():
            self._ghost_timer.stop()
        
        race_was_active = self.is_racing or self._race_pending_start
        self.is_racing = False
        self._race_pending_start = False
        
        self.file_tree.setEnabled(True)
        self.reset_btn.setEnabled(True)
        self.reset_btn.setText("⟲ Reset to Top")
        
        self.ghost_btn.setText("👻")
        self._update_ghost_button()
        
        self.instant_death_btn.setEnabled(True)
        if self._instant_death_pre_race is not None:
            # Restore UI/engine state - don't persist since original preference is already saved
            self._set_instant_death_mode(self._instant_death_pre_race, persist=False)
        if self._instant_death_tooltip_pre_race is not None:
            self.instant_death_btn.setToolTip(self._instant_death_tooltip_pre_race)
        else:
            self.instant_death_btn.setToolTip("Reset to top on any mistake")
        self._instant_death_pre_race = None
        self._instant_death_tooltip_pre_race = None
        
        # Clear crash recovery backup - race completed normally
        from app import settings
        settings.remove_setting("_race_instant_death_backup")
        
        ghost_data = self._current_ghost_data
        user_stats = self.typing_area.get_stats()
        self._current_ghost_data = None
        self._ghost_engine = None
        self._ghost_keystrokes = []
        self._ghost_index = 0
        self._ghost_prev_timestamp = 0
        self._race_start_perf = None
        
        if cancelled:
            self._display_ghost_progress = False
            self._ghost_cursor_position = 0
            self.typing_area.clear_ghost_progress()
            self.ghost_progress_widget.setVisible(False)
        else:
            self._display_ghost_progress = True
            self.ghost_progress_widget.setVisible(True)
        
        self._update_progress_indicator()
        self.typing_area.setFocus()
        
        if not race_was_active:
            self._user_finish_elapsed = None
            self._ghost_finish_elapsed = None
            return
        
        if cancelled:
            self._user_finish_elapsed = None
            self._ghost_finish_elapsed = None
            return
        
        # Calculate accurate stats based on actual race time
        user_time = self._user_finish_elapsed if self._user_finish_elapsed is not None else user_stats.get("time")
        
        # Recalculate WPM based on actual race time (not engine's elapsed time)
        if user_time and user_time > 0:
            user_total_chars = len(self.typing_area.original_content) if self.typing_area.original_content else 0
            user_completed_chars = self.typing_area.engine.state.cursor_position if self.typing_area.engine else 0
            minutes = user_time / 60.0
            user_wpm = (user_completed_chars / 5.0) / minutes if minutes > 0 else 0.0
        else:
            user_wpm = user_stats.get("wpm", 0.0)
            user_total_chars = len(self.typing_area.original_content) if self.typing_area.original_content else 0
            user_completed_chars = self.typing_area.engine.state.cursor_position if self.typing_area.engine else 0
        
        # Calculate accuracy from engine state
        if self.typing_area.engine:
            total_keystrokes = self.typing_area.engine.state.total_keystrokes()
            if total_keystrokes > 0:
                user_acc = (self.typing_area.engine.state.correct_keystrokes / total_keystrokes) * 100
                user_accuracy_decimal = self.typing_area.engine.state.correct_keystrokes / total_keystrokes
            else:
                user_acc = 100.0
                user_accuracy_decimal = 1.0
            user_correct = self.typing_area.engine.state.correct_keystrokes
            user_incorrect = self.typing_area.engine.state.incorrect_keystrokes
            user_total = total_keystrokes
        else:
            user_acc = user_stats.get("accuracy", 0.0) * 100
            user_accuracy_decimal = user_stats.get("accuracy", 1.0)
            user_correct = user_stats.get("correct", 0)
            user_incorrect = user_stats.get("incorrect", 0)
            user_total = user_stats.get("total", 0)
        
        user_completion = (user_completed_chars / user_total_chars * 100) if user_total_chars > 0 else 0
        
        ghost_time = self._ghost_finish_elapsed
        if ghost_time is None and ghost_data and ghost_data.get("final_stats"):
            ghost_time = ghost_data["final_stats"].get("time")
        ghost_wpm = ghost_data.get("wpm") if ghost_data else None
        ghost_acc = ghost_data.get("acc") if ghost_data else None
        
        # Prepare stats for dialog
        race_stats = {
            'wpm': user_wpm,
            'accuracy': user_accuracy_decimal,
            'time': user_time,
            'correct': user_correct,
            'incorrect': user_incorrect,
            'total': user_total,
        }
        
        race_info = {
            'winner': winner,
            'reason': reason,
            'ghost_wpm': ghost_wpm or 0,
            'ghost_time': ghost_time or 0,
            'ghost_acc': ghost_acc or 100,
            'time_delta': (user_time - ghost_time) if (user_time and ghost_time) else 0,
            'ghost_final_stats': ghost_data.get('final_stats') if ghost_data else None,
        }
        
        # Show modern race completion dialog
        theme_colors = self._get_theme_colors()
        user_keystrokes = self.typing_area.get_ghost_data() if hasattr(self.typing_area, 'get_ghost_data') else []
        ghost_keystroke_data = ghost_data.get('keys', []) if ghost_data else []
        
        # Get WPM and error history for the graph
        wpm_history = self.stats_display.get_wpm_history()
        error_history = self.stats_display.get_error_history()
        
        # Add the final WPM at the final time
        final_second = round(user_time) if user_time and user_time > 0 else 0
        final_wpm = user_wpm
        if final_second > 0 and final_wpm > 0:
            if not wpm_history or wpm_history[-1][0] < final_second:
                wpm_history.append((final_second, final_wpm))
            elif wpm_history and wpm_history[-1][0] == final_second:
                wpm_history[-1] = (final_second, final_wpm)
        
        # Get ghost WPM and error history - first try stored data, then calculate
        ghost_wpm_history = ghost_data.get('wpm_history', []) if ghost_data else []
        ghost_error_history = ghost_data.get('error_history', []) if ghost_data else []
        
        # Convert stored tuples back to tuple format if needed (JSON stores as arrays)
        if ghost_wpm_history:
            ghost_wpm_history = [(int(s), float(w)) for s, w in ghost_wpm_history]
        if ghost_error_history:
            ghost_error_history = [(int(s), int(e)) for s, e in ghost_error_history]
        
        # If no stored history, calculate from keystrokes (legacy ghosts)
        if not ghost_wpm_history and ghost_keystroke_data and ghost_time:
            # Calculate ghost WPM at each second based on keystrokes
            ghost_chars_by_second = {}
            ghost_errors_by_second = {}
            for ks in ghost_keystroke_data:
                t_ms = ks.get('t', 0)
                second = int(t_ms / 1000) + 1  # Which second this keystroke is in
                is_correct = ks.get('c', 1) == 1  # 'c' field: 1=correct, 0=incorrect
                if second not in ghost_chars_by_second:
                    ghost_chars_by_second[second] = 0
                    ghost_errors_by_second[second] = 0
                ghost_chars_by_second[second] += 1
                if not is_correct:
                    ghost_errors_by_second[second] += 1
            
            # Calculate cumulative WPM at each second
            cumulative_chars = 0
            for sec in range(1, int(ghost_time) + 1):
                cumulative_chars += ghost_chars_by_second.get(sec, 0)
                minutes = sec / 60.0
                wpm_at_sec = (cumulative_chars / 5.0) / minutes if minutes > 0 else 0
                ghost_wpm_history.append((sec, wpm_at_sec))
                
                # Track errors for this second
                errors_this_sec = ghost_errors_by_second.get(sec, 0)
                if errors_this_sec > 0:
                    ghost_error_history.append((sec, errors_this_sec))
            
            # Add final ghost WPM
            final_ghost_second = round(ghost_time)
            if final_ghost_second > 0 and ghost_wpm:
                if not ghost_wpm_history or ghost_wpm_history[-1][0] < final_ghost_second:
                    ghost_wpm_history.append((final_ghost_second, ghost_wpm))
                elif ghost_wpm_history and ghost_wpm_history[-1][0] == final_ghost_second:
                    ghost_wpm_history[-1] = (final_ghost_second, ghost_wpm)
        
        self.stats_display.clear_wpm_history()
        
        dialog = SessionResultDialog(
            parent=self,
            stats=race_stats,
            is_new_best=is_new_best,
            is_race=True,
            race_info=race_info,
            theme_colors=theme_colors,
            filename=self.current_file,
            user_keystrokes=user_keystrokes,
            ghost_keystrokes=ghost_keystroke_data,
            wpm_history=wpm_history,
            error_history=error_history,
            ghost_wpm_history=ghost_wpm_history,
            ghost_error_history=ghost_error_history
        )
        dialog.exec()
        
        self._user_finish_elapsed = None
        self._ghost_finish_elapsed = None
    
    def _get_theme_colors(self):
        """Get current theme colors for dialogs."""
        from app.themes import get_color_scheme
        from app import settings
        
        # Get current theme settings
        theme = settings.get_setting("theme", settings.get_default("theme"))
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme")) if theme == "dark" else settings.get_setting("light_scheme", settings.get_default("light_scheme"))
        
        # Get the color scheme
        scheme = get_color_scheme(theme, scheme_name)
        
        # Get user/ghost progress bar colors from settings (these are custom)
        user_progress_color = settings.get_setting("user_progress_bar_color", scheme.success_color)
        ghost_progress_color = settings.get_setting("ghost_progress_bar_color", scheme.error_color)
        
        return {
            'bg': scheme.bg_primary,
            'card_bg': scheme.bg_secondary,
            'text': scheme.text_primary,
            'text_secondary': scheme.text_secondary,
            'accent': scheme.accent_color,
            'success': scheme.success_color,
            'warning': scheme.warning_color,
            'error': scheme.error_color,
            'user_color': user_progress_color,
            'ghost_color': ghost_progress_color,
            'user_error': scheme.error_color,
            'ghost_error': scheme.warning_color,
            'border': scheme.border_color,
            'button_bg': scheme.button_bg,
            'button_hover': scheme.button_hover,
        }
    
    def _lighten_color(self, hex_color, factor):
        """Lighten a hex color by a factor."""
        # Remove # if present
        hex_color = hex_color.lstrip('#')
        
        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Lighten
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

    def closeEvent(self, event):
        """Handle widget close - save progress."""
        if self.is_racing or self._race_pending_start:
            self._finalize_ghost_race(cancelled=True)
        self.save_active_progress()
        super().closeEvent(event)
