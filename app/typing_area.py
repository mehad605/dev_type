"""Typing area widget with character-by-character validation and color coding."""
import logging
import time
import json
from pathlib import Path
from PySide6.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QApplication
from PySide6.QtGui import (
    QTextCharFormat, QColor, QFont, QTextCursor,
    QKeyEvent, QPalette, QSyntaxHighlighter, QTextDocument, QPainter
)
from PySide6.QtCore import Qt, Signal, QTimer, QRect, QPoint
from typing import Optional
from app.typing_engine import TypingEngine
from app import settings

logger = logging.getLogger(__name__)

# File size limits
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB hard limit
WARN_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB warning threshold


class TypingHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for coloring typed/untyped characters."""
    
    def __init__(self, parent: QTextDocument, engine: TypingEngine, parent_widget=None):
        super().__init__(parent)
        self.engine = engine
        self.parent_widget = parent_widget
        self.display_offset = 0  # Offset from start of file for sliding window
        
        # Color formats - load from settings
        self.untyped_format = QTextCharFormat()
        untyped_color = settings.get_setting("color_untyped", settings.get_default("color_untyped"))
        self.untyped_format.setForeground(QColor(untyped_color))
        
        self.correct_format = QTextCharFormat()
        correct_color = settings.get_setting("color_correct", settings.get_default("color_correct"))
        self.correct_format.setForeground(QColor(correct_color))

        self.skipped_format = QTextCharFormat()
        # Use same color for skipped characters so they look "correctly typed"
        self.skipped_format.setForeground(QColor(correct_color))

        self.incorrect_format = QTextCharFormat()
        incorrect_color = settings.get_setting("color_incorrect", settings.get_default("color_incorrect"))
        self.incorrect_format.setForeground(QColor(incorrect_color))

        self.ghost_format = QTextCharFormat()
        ghost_color = settings.get_setting("ghost_text_color", settings.get_default("ghost_text_color"))
        self.ghost_format.setForeground(QColor(ghost_color))
        
        self.show_ghost_text = settings.get_setting("show_ghost_text", settings.get_default("show_ghost_text")) == "1"
        
        self.typed_chars = {}  # position -> {typed, expected, is_correct, is_skipped}
        self.ghost_display_limit = 0

    def set_typed_char(self, position: int, typed_char: str, expected_char: str, is_correct: bool, is_skipped: bool = False):
        """Record a typed character at a position."""
        self.typed_chars[position] = {
            "typed": typed_char,
            "expected": expected_char,
            "is_correct": is_correct,
            "is_skipped": is_skipped,
            "length": max(len(expected_char), len(typed_char), 1),
        }
        self.rehighlight()
    
    def clear_typed_char(self, position: int):
        """Clear typed character at position (for backspace)."""
        if position in self.typed_chars:
            del self.typed_chars[position]
        self.rehighlight()
    
    def clear_all(self):
        """Clear all typed characters."""
        self.typed_chars.clear()
        self.rehighlight()
    
    def highlightBlock(self, text: str):
        """Apply formatting to text block."""
        block_start = self.currentBlock().position()
        
        # Calculate visual cursor position
        visual_cursor_pos = -1
        if self.parent_widget:
            # Safely get the display position corresponding to current engine cursor
            visual_cursor_pos = self.parent_widget._engine_to_display_position(self.engine.state.cursor_position)
        else:
            # Fallback (legacy/test support)
            visual_cursor_pos = self.engine.state.cursor_position

        for i, char in enumerate(text):
            # Map relative document position to absolute file position
            pos = block_start + i + self.display_offset
            
            if pos in self.typed_chars:
                info = self.typed_chars[pos]
                if info["is_correct"]:
                    if info.get("is_skipped", False):
                        # Skipped characters (auto-indent) - use semi-transparent correct color
                        self.setFormat(i, 1, self.skipped_format)
                    else:
                        self.setFormat(i, 1, self.correct_format)
                else:
                    self.setFormat(i, 1, self.incorrect_format)
            elif pos < visual_cursor_pos:
                # Already typed correctly (moved past it)
                self.setFormat(i, 1, self.correct_format)
            elif pos < self.ghost_display_limit and self.show_ghost_text:
                self.setFormat(i, 1, self.ghost_format)
            else:
                # Not yet typed
                self.setFormat(i, 1, self.untyped_format)

    def update_show_ghost_text(self, enabled: bool):
        """Update whether ghost text should be shown."""
        self.show_ghost_text = enabled
        self.rehighlight()

    def set_ghost_display_limit(self, limit: int):
        """Update the highest display index the ghost has reached."""
        new_limit = max(0, limit)
        if new_limit != self.ghost_display_limit:
            self.ghost_display_limit = new_limit
            self.rehighlight()

    def clear_ghost_progress(self):
        """Clear any ghost overlay progress."""
        if self.ghost_display_limit != 0:
            self.ghost_display_limit = 0
            self.rehighlight()

    def set_ghost_color(self, color_hex: str):
        """Update the ghost text color."""
        self.ghost_format.setForeground(QColor(color_hex))
        self.rehighlight()


class TypingAreaWidget(QTextEdit):
    """Text area widget for typing practice with validation and color coding."""
    
    stats_updated = Signal()  # Emitted when stats change
    session_completed = Signal()  # Emitted when file is fully typed
    mistake_occurred = Signal()  # Emitted when user makes a typing mistake
    first_key_pressed = Signal()  # Emitted when user presses the first race key
    typing_resumed = Signal()  # Emitted when user resumes typing from paused state
    typing_paused = Signal()   # Emitted when session auto-pauses due to inactivity
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine: Optional[TypingEngine] = None
        self.highlighter: Optional[TypingHighlighter] = None
        
        # Load settings
        self.space_char = settings.get_setting("space_char", settings.get_default("space_char"))
        # tab_width is now used ONLY for visual expansion of \t characters (fixed to 4 for consistency)
        self.tab_width = 4 
        # space_per_tab controls how many characters the Tab key shortcut processes
        self.space_per_tab = int(settings.get_setting("space_per_tab", "4"))
        
        self.enter_char = "⏎"  # Default enter character display
        self.original_content = ""  # Original file content (without special chars)
        self.display_content = ""  # Content with special chars for display
        self.show_typed_characters = settings.get_setting("show_typed_characters", settings.get_default("show_typed_characters")) == "1"

        # Custom cursor state
        self.cursor_color = QColor(settings.get_setting("color_cursor", settings.get_default("color_cursor")))
        self.cursor_style = settings.get_setting("cursor_style", settings.get_default("cursor_style")).lower()
        self.cursor_blink_mode = settings.get_setting("cursor_type", settings.get_default("cursor_type")).lower()
        self._cursor_visible = True
        self._cursor_rect = QRect()
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._toggle_cursor_visible)
        
        # Configure widget
        self.setReadOnly(True)  # Prevent normal editing
        self.setTabChangesFocus(False)
        
        # Load font from settings
        font_family = settings.get_setting("font_family", settings.get_default("font_family"))
        font_size = settings.get_setting_int("font_size", 12, min_val=8, max_val=32)
        self.setFont(QFont(font_family, font_size))

        # Track cursor position changes for custom drawing
        self.cursorPositionChanged.connect(self._on_qt_cursor_changed)
        
        # Load cursor settings
        cursor_type = settings.get_setting("cursor_type", settings.get_default("cursor_type"))
        cursor_style = settings.get_setting("cursor_style", settings.get_default("cursor_style"))
        self.update_cursor(cursor_type, cursor_style)
        
        # Auto-pause timer
        self.pause_timer = QTimer()
        self.pause_timer.timeout.connect(self._check_auto_pause)
        self.pause_timer.start(1000)  # Check every second
        
        # Cursor position tracking
        self.current_typing_position = 0
        
        # Ghost recording
        self.is_recording_ghost = False
        self.ghost_keystrokes = []
        self.ghost_accumulated_ms = 0
        self.ghost_segment_start_perf = None
        self._has_emitted_first_key = False
        
        # Logging for Intent Test
        self.logging_enabled = False

        # Sliding Window / Large File Optimization (Infinite Runner)
        self.WINDOW_SIZE = 100        # Lines per window
        self.SLIDE_THRESHOLD = 20     # Lines from bottom before sliding
        self.SLIDE_STEP = 40          # How many lines to advance when sliding
        
        self.window_start_line = 0
        self.window_end_line = self.WINDOW_SIZE
        self.window_offset_display = 0
        self.engine_to_display_map = []
        self.line_starts_engine = []
        self.line_starts_display = []

        # Ghost overlay state (race mode)
        self._ghost_display_limit = 0
    
    def load_file(self, file_path: str):
        """Load a file for typing practice."""
        # Check file size before loading
        try:
            file_size = Path(file_path).stat().st_size
            
            if file_size > MAX_FILE_SIZE_BYTES:
                size_mb = file_size / (1024 * 1024)
                self.original_content = (
                    f"Error: File too large ({size_mb:.1f} MB).\n\n"
                    f"Maximum supported file size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.\n"
                    "Please select a smaller file for typing practice."
                )
                self._setup_error_display()
                return
            
            if file_size > WARN_FILE_SIZE_BYTES:
                size_mb = file_size / (1024 * 1024)
                logger.warning(f"Loading large file ({size_mb:.1f} MB): {file_path}")
                
        except (OSError, PermissionError) as e:
            self.original_content = f"Error: Cannot access file: {e}"
            self._setup_error_display()
            return
        
        # Try multiple encodings in order of likelihood
        encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    self.original_content = f.read()
                break  # Success, stop trying
            except UnicodeDecodeError:
                continue  # Try next encoding
            except Exception as e:
                # Other errors (file not found, permission denied, etc.)
                self.original_content = f"Error loading file: {e}"
                break
        else:
            # All encodings failed
            self.original_content = "Error: Could not decode file with any supported encoding (tried UTF-8, CP1252, Latin-1)"
        
        # 1. Initialize engine with expanded tabs FIRST
        # Use a fixed width of 4 for consistent visual mapping
        typing_content = self.original_content.replace('\t', ' ' * 4)
        
        pause_delay = settings.get_setting_float("pause_delay", 7.0, min_val=0.0, max_val=60.0)
        allow_continue = settings.get_setting("allow_continue_mistakes", settings.get_default("allow_continue_mistakes")) == "1"
        self.engine = TypingEngine(typing_content, pause_delay=pause_delay, allow_continue_mistakes=allow_continue)
        self.engine.auto_indent = settings.get_setting("auto_indent", "0") == "1"

        # 2. Prepare display content from the expanded engine content
        # This guarantees 1-to-1 visual correspondence
        self.display_content = self._prepare_display_content(typing_content)
        
        # 3. Fast index mapping (will now use engine.state.content)
        self._recalculate_index_maps()
        
        # Setup highlighter but don't set document yet
        self.highlighter = TypingHighlighter(self.document(), self.engine, parent_widget=self)
        self._ghost_display_limit = 0
        self.highlighter.clear_ghost_progress()
        
        # Initialize window
        self.window_start_line = 0
        self.window_end_line = self.WINDOW_SIZE
        self.refresh_window()
        
        # Reset cursor
        self.current_typing_position = 0
        self._update_cursor_position()
        
        # Try to load saved progress
        from app import stats_db
        progress = stats_db.get_session_progress(file_path, auto_indent=self.engine.auto_indent)
        
        # Start ghost recording (handles resumed state)
        resumed_keystrokes = progress.get("keystrokes") if progress else None
        self.start_ghost_recording(resumed_keystrokes)

        if progress:
            # Parse stored fields
            mistake_at = progress.get("mistake_at", -1)
            max_correct_pos = progress.get("max_correct_position", -1)
            
            skipped_pos = None
            if progress.get("skipped_positions"):
                try:
                    skipped_pos = set(json.loads(progress["skipped_positions"]))
                except: pass
                
            self.engine.load_progress(
                cursor_pos=progress["cursor_position"],
                correct=progress["correct"],
                incorrect=progress["incorrect"],
                elapsed=progress["time"],
                mistake_at=mistake_at,
                max_correct_pos=max_correct_pos,
                skipped_positions=skipped_pos
            )
            
            # Restore highlighter's detailed typing record
            typed_chars_raw = progress.get("typed_chars")
            if typed_chars_raw:
                try:
                    # JSON keys are strings, convert back to integer keys for positions
                    raw_map = json.loads(typed_chars_raw)
                    self.highlighter.typed_chars = {int(k): v for k, v in raw_map.items()}
                except: pass
            self.current_typing_position = self._engine_to_display_position(self.engine.state.cursor_position)
            self._update_cursor_position()
            if self.highlighter:
                self.highlighter.rehighlight()
        else:
            if self.highlighter:
                self.highlighter.clear_all()

        self.stats_updated.emit()
        return progress
        
    def start_ghost_recording(self, resume_data=None):
        """Start or resume recording keystrokes for potential ghost session."""
        self.is_recording_ghost = True
        self._has_emitted_first_key = False
        self._ghost_display_limit = 0
        
        if resume_data:
            try:
                self.ghost_keystrokes = json.loads(resume_data)
                # If we have existing keystrokes, start after the last timestamp
                if self.ghost_keystrokes:
                    self.ghost_accumulated_ms = self.ghost_keystrokes[-1]['t']
                    self._has_emitted_first_key = True # Already started
                else:
                    self.ghost_accumulated_ms = 0
            except Exception as e:
                print(f"[GhostRecorder] Failed to resume keystrokes: {e}")
                self.ghost_keystrokes = []
                self.ghost_accumulated_ms = 0
        else:
            self.ghost_keystrokes = []
            self.ghost_accumulated_ms = 0
            
        self.ghost_segment_start_perf = None
        
        if self.highlighter:
            self.highlighter.clear_ghost_progress()
        print(f"[GhostRecorder] Recording initialized (resumed: {bool(resume_data)})")

    def _recalculate_index_maps(self):
        """Build precise character position mapping and line indices for fast lookup."""
        content = self.engine.state.content if self.engine else self.original_content
        self.engine_to_display_map = [0] * (len(content) + 1)
        self.line_starts_engine = [0]
        self.line_starts_display = [0]
        
        space_len = len(self.space_char) if self.space_char else 1
        enter_len = len(self.enter_char) if self.enter_char else 1
        
        curr_display = 0
        for i, ch in enumerate(content):
            self.engine_to_display_map[i] = curr_display
            if ch == '\n':
                curr_display += enter_len + 1
                self.line_starts_engine.append(i + 1)
                self.line_starts_display.append(curr_display)
            elif ch == '\t':
                curr_display += space_len * self.tab_width
            elif ch == ' ':
                curr_display += space_len
            else:
                curr_display += 1
        self.engine_to_display_map[len(content)] = curr_display

    def refresh_window(self):
        """Update document content to show current sliding window of the file."""
        if not self.line_starts_engine: return
        
        line_count = len(self.line_starts_engine)
        start_line = max(0, min(self.window_start_line, line_count - 1))
        end_line = max(start_line + 1, min(self.window_end_line, line_count))
        
        start_display_pos = self.line_starts_display[start_line]
        if end_line < len(self.line_starts_display):
            end_display_pos = self.line_starts_display[end_line]
        else:
            end_display_pos = len(self.display_content)
            
        window_text = self.display_content[start_display_pos:end_display_pos]
        
        # Update offset state BEFORE setting text
        self.window_offset_display = start_display_pos
        if self.highlighter:
            self.highlighter.display_offset = start_display_pos
        
        # Block signals to prevent recursion/excessive updates
        self.blockSignals(True)
        self.setPlainText(window_text)
        self.blockSignals(False)
        
        # Re-apply typed changes for visible window
        self._refresh_typed_display()
        
        if self.highlighter:
            self.highlighter.rehighlight()
            
    def _maybe_slide_window(self):
        """Slide the window if cursor is nearing edges."""
        if not self.engine or not self.line_starts_engine: return
        
        engine_pos = self.engine.state.cursor_position
        import bisect
        current_line_idx = bisect.bisect_right(self.line_starts_engine, engine_pos) - 1
        
        # Thresholds
        if current_line_idx >= self.window_end_line - self.SLIDE_THRESHOLD:
            # Shift forward
            new_start = min(current_line_idx - 20, len(self.line_starts_engine) - self.WINDOW_SIZE)
            new_start = max(0, int(new_start))
            if new_start > self.window_start_line:
                self.window_start_line = new_start
                self.window_end_line = new_start + self.WINDOW_SIZE
                self.refresh_window()
        elif current_line_idx < self.window_start_line + self.SLIDE_THRESHOLD and self.window_start_line > 0:
            # Shift backward
            new_start = max(0, current_line_idx - (self.WINDOW_SIZE - self.SLIDE_THRESHOLD))
            new_start = int(new_start)
            if new_start < self.window_start_line:
                self.window_start_line = new_start
                self.window_end_line = new_start + self.WINDOW_SIZE
                self.refresh_window()
    
    def _setup_error_display(self):
        """Setup display for error messages (no typing engine)."""
        self.display_content = self.original_content
        self.engine = None
        self.setPlainText(self.display_content)
        self.highlighter = None
        self.current_typing_position = 0
        self.is_recording_ghost = False
        self.ghost_keystrokes = []
    
    def _resume_ghost_recording(self):
        """Called when typing resumes to start a new timing segment."""
        if self.is_recording_ghost and self.ghost_segment_start_perf is None:
            self.ghost_segment_start_perf = time.perf_counter()

    def _pause_ghost_recording(self):
        """Called when typing pauses to finalize the current timing segment."""
        if self.is_recording_ghost and self.ghost_segment_start_perf is not None:
            duration_ms = (time.perf_counter() - self.ghost_segment_start_perf) * 1000
            self.ghost_accumulated_ms += duration_ms
            self.ghost_segment_start_perf = None

    def _record_keystroke(self, key_char: str, is_correct: bool):
        """Record a keystroke for ghost replay."""
        if not self.is_recording_ghost:
            return
        
        # Ensure we are in an active segment if recording
        if self.ghost_segment_start_perf is None:
             self.ghost_segment_start_perf = time.perf_counter()
        
        timestamp_ms = int(self.ghost_accumulated_ms + (time.perf_counter() - self.ghost_segment_start_perf) * 1000)
        
        # Compact format: t=timestamp, k=key, c=correct (1/0)
        self.ghost_keystrokes.append({
            "t": timestamp_ms,
            "k": key_char,
            "c": 1 if is_correct else 0
        })
    
    def get_ghost_data(self) -> list:
        """Get recorded ghost keystrokes."""
        return self.ghost_keystrokes

    def set_ghost_progress_limit(self, engine_cursor: int):
        """Update the ghost overlay based on ghost engine progress."""
        display_pos = self._engine_to_display_position(engine_cursor)
        self._ghost_display_limit = display_pos
        if self.highlighter:
            self.highlighter.set_ghost_display_limit(display_pos)

    def clear_ghost_progress(self):
        """Remove any ghost overlay from the editor."""
        self._ghost_display_limit = 0
        if self.highlighter:
            self.highlighter.clear_ghost_progress()
    
    def _prepare_display_content(self, content: str) -> str:
        """Convert content for display with special characters."""
        result = content.replace(' ', self.space_char)
        result = result.replace('\n', self.enter_char + '\n')
        result = result.replace('\t', self.space_char * self.tab_width)
        return result
    
    def _display_char_for(self, char: str) -> str:
        """Return the visual representation of a character."""
        if char == ' ':
            return self.space_char
        if char == '\n':
            return self.enter_char
        if char == '\t':
            return self.space_char * self.tab_width
        return char

    def _replace_display_char(self, position: int, new_char: str, length: int = 1):
        """Replace the character shown at a position without changing engine state."""
        # Convert absolute display position to window-relative
        rel_pos = position - self.window_offset_display
        if rel_pos < 0 or rel_pos >= self.document().characterCount():
            return

        original_cursor = self.textCursor()
        cursor = QTextCursor(self.document())
        cursor.setPosition(rel_pos)
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, length)
        cursor.insertText(new_char)
        self.setTextCursor(original_cursor)

    def _apply_display_for_position(self, position: int):
        """Ensure the displayed character matches settings for a typed position."""
        if not self.highlighter:
            return
        info = self.highlighter.typed_chars.get(position)
        if not info:
            return

        expected_len = info.get("length", max(len(info.get("expected", "")), 1))
        target_char = info["typed"] if self.show_typed_characters else info["expected"]
        self._replace_display_char(position, target_char, expected_len)

    def _refresh_typed_display(self):
        """Re-apply display text for positions in the current window."""
        if not self.highlighter or not self.highlighter.typed_chars:
            return

        window_start = self.window_offset_display
        window_end = window_start + len(self.toPlainText())
        
        # Only process characters visible in the window for performance
        for position, info in self.highlighter.typed_chars.items():
            if window_start <= position < window_end:
                length = info.get("length", max(len(info.get("expected", "")), 1))
                target_char = info["typed"] if self.show_typed_characters else info["expected"]
                self._replace_display_char(position, target_char, length)

    def _restore_display_for_position(self, position: int):
        """Restore the original expected character at a position."""
        info = self.highlighter.typed_chars.get(position) if self.highlighter else None
        if info:
            expected_char = info["expected"]
            expected_len = info.get("length", max(len(expected_char), 1))
        else:
            if self.engine:
                engine_pos = self._display_position_to_engine(position)
                if engine_pos is not None and engine_pos < len(self.engine.state.content):
                    expected_char = self._display_char_for(self.engine.state.content[engine_pos])
                elif position < len(self.display_content):
                    expected_char = self.display_content[position]
                else:
                    expected_char = ""
            elif position < len(self.display_content):
                expected_char = self.display_content[position]
            else:
                expected_char = ""
            expected_len = max(len(expected_char), 1) if expected_char else 1

        if expected_char:
            self._replace_display_char(position, expected_char, expected_len)

    def _display_position_to_engine(self, display_pos: int) -> Optional[int]:
        """Map a document index (relative to window) back to absolute engine index."""
        abs_display_pos = display_pos + self.window_offset_display
        
        # Binary search for the closest engine index
        import bisect
        engine_idx = bisect.bisect_left(self.engine_to_display_map, abs_display_pos)
        return engine_idx

    def _clear_and_restore_engine_position(self, engine_index: int):
        """Clear typed state and redraw the expected character for an engine index."""
        if engine_index < 0 or not self.engine:
            return

        display_pos = self._engine_to_display_position(engine_index)

        if self.highlighter:
            self.highlighter.clear_typed_char(display_pos)

        if engine_index < len(self.engine.state.content):
            expected_char = self._display_char_for(self.engine.state.content[engine_index])
        elif display_pos < len(self.display_content):
            expected_char = self.display_content[display_pos]
        else:
            expected_char = ""

        if expected_char:
            self._replace_display_char(display_pos, expected_char, max(len(expected_char), 1))

    def _update_cursor_position(self, override_pos: Optional[int] = None):
        """Update visual cursor to current typing position (handled relative to window)."""
        target_pos = override_pos if override_pos is not None else self.current_typing_position
        rel_pos = target_pos - self.window_offset_display
        
        # Guard against position outside window
        doc_len = self.document().characterCount() - 1 # QTextDocument ends with \u2029
        rel_pos = max(0, min(rel_pos, doc_len))
        
        cursor = self.textCursor()
        cursor.setPosition(rel_pos, QTextCursor.MoveAnchor)
        cursor.clearSelection()
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self._update_cursor_geometry()

    def _engine_to_display_position(self, engine_pos: int) -> int:
        """Convert absolute engine index to absolute displayed document index."""
        if engine_pos <= 0:
            return 0
        if not hasattr(self, 'engine_to_display_map') or not self.engine_to_display_map:
            return engine_pos
        
        idx = min(engine_pos, len(self.engine_to_display_map) - 1)
        return self.engine_to_display_map[idx]

    def mousePressEvent(self, event):
        """Ignore left-click attempts to reposition the cursor."""
        if event.button() == Qt.LeftButton:
            self.setFocus(Qt.MouseFocusReason)
            self._update_cursor_position()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Prevent double-click selection from changing cursor location."""
        if event.button() == Qt.LeftButton:
            self.setFocus(Qt.MouseFocusReason)
            self._update_cursor_position()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        """Block drag selections that would alter cursor position."""
        if event.buttons() & Qt.LeftButton:
            self._update_cursor_position()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def _on_qt_cursor_changed(self):
        """Keep custom cursor visuals in sync with Qt cursor changes."""
        self._update_cursor_geometry()

    def _update_cursor_geometry(self):
        """Recalculate cursor rectangle based on style - instant positioning."""
        rect = QRect(self.cursorRect())

        if self.cursor_style == "block":
            min_width = self.fontMetrics().averageCharWidth() or 1
            rect.setWidth(max(rect.width(), min_width))
        elif self.cursor_style == "underscore":
            height = rect.height() or self.fontMetrics().height()
            thickness = max(2, height // 6)
            thickness = min(thickness, height)
            width = max(rect.width(), self.fontMetrics().averageCharWidth(), 2)
            y_pos = rect.y() + height - thickness
            rect = QRect(rect.left(), y_pos, width, thickness)
        else:  # ibeam
            width = max(2, self.logicalDpiX() // 180)
            rect = QRect(rect.left(), rect.top(), width, rect.height())

        # Update cursor position immediately
        old_rect = QRect(self._cursor_rect)
        self._cursor_rect = rect
        self._request_cursor_paint(old_rect)

    def _request_cursor_paint(self, old_rect: Optional[QRect] = None):
        """Schedule viewport update for cursor area."""
        margin = 2
        if old_rect and not old_rect.isNull():
            self.viewport().update(old_rect.adjusted(-margin, -margin, margin, margin))
        if not self._cursor_rect.isNull():
            self.viewport().update(self._cursor_rect.adjusted(-margin, -margin, margin, margin))

    def _toggle_cursor_visible(self):
        """Blink cursor visibility."""
        self._cursor_visible = not self._cursor_visible
        self._request_cursor_paint()

    def _update_blink_timer(self):
        """Start or stop blink timer based on settings and focus."""
        self._cursor_visible = True
        if self.cursor_blink_mode == "blinking" and self.hasFocus():
            flash_time = QApplication.instance().cursorFlashTime() if QApplication.instance() else 1000
            if flash_time <= 0:
                flash_time = 1000
            self._cursor_timer.start(max(100, flash_time // 2))
        else:
            self._cursor_timer.stop()
            self._request_cursor_paint()

    def paintEvent(self, event):
        super().paintEvent(event)
        self._paint_custom_cursor()

    def _paint_custom_cursor(self):
        """Draw the custom cursor with configured color/style."""
        if not self.hasFocus() or not self._cursor_visible or self._cursor_rect.isNull():
            return

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.cursor_color)
        painter.drawRect(self._cursor_rect)
        painter.end()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._cursor_visible = True
        self._update_cursor_geometry()
        self._update_blink_timer()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._cursor_visible = False
        self._cursor_timer.stop()
        self._request_cursor_paint()

    def focusNextPrevChild(self, next: bool) -> bool:
        """Keep Tab/Shift+Tab inside the typing area instead of moving focus."""
        return False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_cursor_geometry()
    
    def _should_emit_first_key(self, event: QKeyEvent) -> bool:
        """Check whether the key event should trigger the first-key signal."""
        key = event.key()
        text = event.text()
        modifiers = event.modifiers()

        if modifiers == Qt.ControlModifier and key == Qt.Key_P:
            return False

        if modifiers & Qt.ControlModifier and key == Qt.Key_Backspace:
            return True

        if key in (Qt.Key_Backspace, Qt.Key_Tab, Qt.Key_Return, Qt.Key_Enter):
            return True

        if key == Qt.Key_Space:
            return True

        if text and text.strip():
            return True

        return False

    def _maybe_emit_first_key(self, event: QKeyEvent):
        if not self._has_emitted_first_key and self._should_emit_first_key(event):
            self._has_emitted_first_key = True
            self.first_key_pressed.emit()

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard input for typing."""
        if not self.engine:
            return
        
        key = event.key()
        text = event.text()
        modifiers = event.modifiers()
        
        if key == Qt.Key_Escape:
            self.reset_session()
            event.accept()
            return

        # Ignore global shortcuts to let them bubble up to MainWindow
        # We only handle Ctrl+P and Ctrl+Backspace here.
        if (modifiers & (Qt.ControlModifier | Qt.AltModifier)):
            if not (key == Qt.Key_P and modifiers & Qt.ControlModifier) and \
               not (key == Qt.Key_Backspace and modifiers & Qt.ControlModifier):
                event.ignore()
                return

        # Intercept Ctrl+P for pause/unpause (don't process as typing)
        if key == Qt.Key_P and modifiers == Qt.ControlModifier:
            # Toggle pause state
            if self.engine.state.is_paused:
                self.engine.start()
                self._resume_ghost_recording()
                self.typing_resumed.emit()
            else:
                self.engine.pause()
                self._pause_ghost_recording()
                self.typing_paused.emit()
            self.stats_updated.emit()
            event.accept()
            return

        self._maybe_emit_first_key(event)
        
        # Check if engine is currently paused before processing keystroke
        # If it is, the keystroke will auto-resume it, and we need to emit a signal
        was_paused = self.engine.state.is_paused
        
        # Play keypress sound for valid typing keys
        from app.sound_manager import get_sound_manager
        sound_mgr = get_sound_manager()

        # Keep display cursor aligned with engine state
        self.current_typing_position = self._engine_to_display_position(self.engine.state.cursor_position)
        
        # Handle Backspace
        if key == Qt.Key_Backspace:
            sound_mgr.play_keypress()  # Sound for backspace
            if modifiers & Qt.ControlModifier:
                # Ctrl+Backspace
                self._record_keystroke("<CTRL-BACKSPACE>", True)
                old_engine_pos = self.engine.state.cursor_position
                self.engine.process_ctrl_backspace()
                new_engine_pos = self.engine.state.cursor_position
                # Clear typed characters for removed range
                for engine_index in range(new_engine_pos, old_engine_pos):
                    self._clear_and_restore_engine_position(engine_index)
                self.current_typing_position = self._engine_to_display_position(new_engine_pos)
                self._maybe_slide_window()
                self._update_cursor_position()
            else:
                # Regular backspace
                self._record_keystroke("\b", True)
                if self.engine.state.cursor_position > 0 or self.engine.mistake_at is not None:
                    old_pos = self.engine.state.cursor_position
                    self.engine.process_backspace(self.space_per_tab)
                    new_pos = self.engine.state.cursor_position
                    
                    # Clear visuals for all removed characters (handles single char, smart backspace, and undo auto-indent)
                    # Use a range to ensure we catch everything if the cursor jumped back multiple spots
                    start_clear = new_pos
                    end_clear = max(old_pos, new_pos + 1) # Ensure at least one char is cleared
                    
                    for idx in range(start_clear, end_clear):
                        self._clear_and_restore_engine_position(idx)
                        
                    self.current_typing_position = self._engine_to_display_position(new_pos)
                    self._maybe_slide_window()
                    self._update_cursor_position()
            self.stats_updated.emit()
            return
        
        # Handle Tab
        if key == Qt.Key_Tab:
            sound_mgr.play_keypress()  # Sound for tab
            
            initial_max_correct = self.engine.state.max_correct_position
            
            all_correct = True
            spaces_processed = 0
            
            # Process up to 'space_per_tab' characters, but stop if we hit non-whitespace
            tab_was_attempted = False
            for _ in range(self.space_per_tab):
                if self.engine.state.cursor_position >= len(self.engine.state.content):
                    break
                
                position = self._engine_to_display_position(self.engine.state.cursor_position)
                expected_actual = self.engine.state.content[self.engine.state.cursor_position]
                
                # Stop tabbing if we reach something that isn't a space or a tab
                if expected_actual not in (' ', '\t'):
                    break
                
                # Physical key press already processed sound; use virtual processing for engine
                tab_was_attempted = True
                char_to_type = expected_actual
                is_correct, expected_from_engine, _ = self.engine.process_keystroke(char_to_type, increment_stats=False, space_per_tab=self.space_per_tab)
                
                if not is_correct:
                    all_correct = False
                    # Log failure
                    if self.logging_enabled:
                        print(f"Tab Processing - Expected: '{expected_from_engine}', Typed: ' ' (FAILED)")
                    # Stop to prevent drawing multiple red indicators at one spot
                    break
                
                # Log success
                if self.logging_enabled:
                     print(f"Tab Processing - Expected: '{expected_from_engine}', Typed: ' '")
                
                if expected_from_engine == "" and not is_correct:
                    # strict mode block
                    break
                
                # Track visual state
                typed_display = self._display_char_for(char_to_type)
                expected_display = self._display_char_for(expected_actual)

                if self.highlighter:
                    self.highlighter.set_typed_char(
                        position,
                        typed_display,
                        expected_display,
                        is_correct
                    )
                self._apply_display_for_position(position)
                spaces_processed += 1
                
            # Manual stats increment: one physical key press = one keystroke
            if tab_was_attempted:
                if all_correct:
                    # Prevent keystroke farming: only credit if we advanced new territory
                    if self.engine.state.max_correct_position > initial_max_correct:
                        self.engine.state.correct_keystrokes += 1
                        # Also increment hit count for space (as a representative of the action)
                        self.engine.state.key_hits[' '] = self.engine.state.key_hits.get(' ', 0) + 1
                else:
                    self.engine.state.incorrect_keystrokes += 1
                    self.engine.state.key_misses[' '] = self.engine.state.key_misses.get(' ', 0) + 1
                
            if spaces_processed > 0:
                self._record_keystroke('\t', all_correct)
                self.current_typing_position = self._engine_to_display_position(self.engine.state.cursor_position)
                self._maybe_slide_window()
                self._update_cursor_position()
                self.stats_updated.emit()
            return
        
        # Handle printable characters
        if text and len(text) == 1:
            sound_mgr.play_keypress()  # Sound for character input
            position = self._engine_to_display_position(self.engine.state.cursor_position)
            char = text
            
            # Map space to actual space
            if key == Qt.Key_Space:
                char = ' '
            # Map Enter to newline
            elif key == Qt.Key_Return or key == Qt.Key_Enter:
                char = '\n'
            
            # Process keystroke
            is_correct, expected, skipped_count = self.engine.process_keystroke(char, space_per_tab=self.space_per_tab)
            
            # Log expected vs actual if enabled
            if self.logging_enabled:
                print(f"Expected: '{expected}', Typed: '{char}'")
            
            # If engine was paused and is now running, emit typing_resumed signal
            if was_paused and not self.engine.state.is_paused:
                self._resume_ghost_recording()
                self.typing_resumed.emit()
            
            # Record keystroke for ghost
            self._record_keystroke(char, is_correct)
            
            # Check for instant death mode BEFORE displaying the mistake
            if not is_correct:
                from app import settings
                instant_death_enabled = settings.get_setting("instant_death_mode", settings.get_default("instant_death_mode")) == "1"
                if instant_death_enabled:
                    # Emit signal and immediately reset without displaying the mistake
                    self.mistake_occurred.emit()
                    return  # Don't process the rest - the reset will be called
                else:
                    # Normal mode - just emit the signal for tracking
                    self.mistake_occurred.emit()
            
            # If there's a mistake lock and this character was blocked, don't display anything
            if expected == "" and not is_correct:
                # Character was blocked by mistake lock, just update stats
                self.stats_updated.emit()
                return
            
            # Track typed vs expected characters
            typed_display = self._display_char_for(char)
            expected_display = self._display_char_for(expected)

            self.highlighter.set_typed_char(
                position,
                typed_display,
                expected_display,
                is_correct
            )

            self._apply_display_for_position(position)
            
            # 4. Handle auto-indent skipped characters
            if skipped_count > 0:
                # Start tracking from the first character after the newline
                temp_engine_pos = self.engine.state.cursor_position - skipped_count
                for _ in range(skipped_count):
                    display_pos = self._engine_to_display_position(temp_engine_pos)
                    actual_char = self.engine.state.content[temp_engine_pos]
                    display_char = self._display_char_for(actual_char)
                    
                    self.highlighter.set_typed_char(
                        display_pos,
                        display_char,
                        display_char,
                        True,
                        is_skipped=True
                    )
                    self._apply_display_for_position(display_pos)
                    temp_engine_pos += 1

            # Update cursor position (engine already advanced if allowed)
            self.current_typing_position = self._engine_to_display_position(self.engine.state.cursor_position)
            
            # Check for window slide
            self._maybe_slide_window()
            
            # If there's a mistake, show cursor after the mistake visually
            visual_cursor_pos = self.current_typing_position
            if self.engine.mistake_at is not None:
                mistake_display_pos = self._engine_to_display_position(self.engine.mistake_at)
                if mistake_display_pos == visual_cursor_pos:
                    # Show cursor after the mistake character so it's clear where the error is
                    visual_cursor_pos = mistake_display_pos + 1
            
            # Use helper for relative cursor update
            self._update_cursor_position(override_pos=visual_cursor_pos)
            self.stats_updated.emit()
            
            # Check if completed
            if self.engine.state.is_finished:
                self._pause_ghost_recording()
                # Emit one final stats update with the completion stats
                self.stats_updated.emit()
                self.session_completed.emit()
    
    def _check_auto_pause(self):
        """Check if session should auto-pause."""
        if self.engine and self.engine.check_auto_pause():
            self._pause_ghost_recording()
            self.typing_paused.emit()
            self.stats_updated.emit()
    
    def reset_session(self):
        """Reset typing session to beginning."""
        if self.engine:
            self.engine.reset()
            self.highlighter.clear_all()
            self.setPlainText(self.display_content)
            self.current_typing_position = 0
            self._update_cursor_position()
            self.stats_updated.emit()
        self._has_emitted_first_key = False
        self.clear_ghost_progress()
        self.start_ghost_recording() # Restart recording from scratch
        self.stats_updated.emit()
    
    def reset_cursor_only(self):
        """Reset cursor to beginning but keep stats running (for race mode instant death)."""
        if self.engine:
            self.engine.reset_cursor_only()
            self.highlighter.clear_all()
            self.setPlainText(self.display_content)
            self.current_typing_position = 0
            self._update_cursor_position()
            self.stats_updated.emit()
        self._has_emitted_first_key = False
        # Don't clear ghost progress - that's handled by the caller
    
    def get_stats(self) -> dict:
        """Get current typing statistics."""
        if not self.engine:
            return {
                "wpm": 0.0,
                "accuracy": 1.0,
                "time": 0.0,
                "correct": 0,
                "incorrect": 0,
                "total": 0,
                "is_paused": True,
                "is_finished": False,
            }
        
        return {
            "wpm": self.engine.get_wpm(),
            "accuracy": self.engine.state.accuracy(),  # Use keystroke-based accuracy consistently
            "time": self.engine.get_elapsed_time(),
            "correct": self.engine.state.correct_keystrokes,
            "incorrect": self.engine.state.incorrect_keystrokes,
            "total": self.engine.state.total_keystrokes(),
            "is_paused": self.engine.state.is_paused,
            "is_finished": self.engine.state.is_finished,
            "key_hits": self.engine.state.key_hits,
            "key_misses": self.engine.state.key_misses,
            "key_confusions": self.engine.state.key_confusions,
            "error_types": self.engine.state.error_types,
        }
    
    def update_font(self, family: str, size: int, ligatures: bool):
        """Update font settings dynamically."""
        font = QFont(family, size)
        # Ligatures support removed
        self.setFont(font)
        self._update_cursor_geometry()
    
    def update_colors(self):
        """Update color settings dynamically."""
        if self.highlighter:
            # Reload colors from settings
            untyped_color = settings.get_setting("color_untyped", settings.get_default("color_untyped"))
            self.highlighter.untyped_format.setForeground(QColor(untyped_color))
            
            correct_color = settings.get_setting("color_correct", settings.get_default("color_correct"))
            self.highlighter.correct_format.setForeground(QColor(correct_color))
            self.highlighter.skipped_format.setForeground(QColor(correct_color))
            
            incorrect_color = settings.get_setting("color_incorrect", settings.get_default("color_incorrect"))
            self.highlighter.incorrect_format.setForeground(QColor(incorrect_color))

            ghost_color = settings.get_setting("ghost_text_color", settings.get_default("ghost_text_color"))
            self.highlighter.set_ghost_color(ghost_color)
            
            # Trigger rehighlight to apply changes
            self.highlighter.rehighlight()

        cursor_color_value = settings.get_setting("color_cursor", settings.get_default("color_cursor"))
        self.cursor_color = QColor(cursor_color_value)
        self._request_cursor_paint()
    
    def update_cursor(self, cursor_type: str, cursor_style: str):
        """Update cursor settings dynamically."""
        self.cursor_blink_mode = (cursor_type or "blinking").lower()
        self.cursor_style = (cursor_style or "block").lower()

        # Hide Qt's default cursor so we can draw our own
        self.setCursorWidth(0)
        
        # Update cursor geometry and timer
        self._update_cursor_geometry()
        self._update_blink_timer()
        
        # Force cursor to be visible and trigger immediate redraw
        self.cursor_visible = True
        self.viewport().update()
        self.update()  # Force full widget update
        
        # If cursor is blinking, restart the blink cycle
        if self.cursor_blink_mode == "blinking" and hasattr(self, '_cursor_timer'):
            self._cursor_timer.stop()
            self._cursor_timer.start(530)  # Standard blink rate
    
    def update_space_char(self, space_char: str):
        """Update space character display dynamically."""
        old_space_char = self.space_char
        self.space_char = space_char
        
        # If content is loaded, regenerate display content
        if self.original_content:
            self.display_content = self._prepare_display_content(self.original_content)
            
            # Save cursor position
            cursor_pos = self.current_typing_position
            
            # Update text
            self.setPlainText(self.display_content)
            
            # Restore cursor and highlighting
            self.current_typing_position = cursor_pos
            self._update_cursor_position()
            if self.highlighter:
                self.highlighter.rehighlight()
                self._refresh_typed_display()
    
    def update_tab_width(self, width: int):
        """Update space per tab setting dynamically."""
        self.space_per_tab = width
        # This setting no longer mutates the existing file content or display width
        # ensuring visual stability while allowing the shortcut to behave as configured.
    
    def update_pause_delay(self, delay: float):
        """Update pause delay setting dynamically."""
        if self.engine:
            self.engine.pause_delay = delay
    
    def update_allow_continue(self, allow_continue: bool):
        """Update allow continue with mistakes setting dynamically."""
        if self.engine:
            self.engine.allow_continue_mistakes = allow_continue

            if allow_continue:
                # If we were previously blocking at a mistake, advance past it now
                if self.engine.mistake_at is not None:
                    mistake_pos = self.engine.mistake_at
                    if self.engine.state.cursor_position == mistake_pos:
                        # Advance cursor to the position after the mistake so typing can continue
                        next_pos = min(mistake_pos + 1, len(self.engine.state.content))
                        self.engine.state.cursor_position = next_pos
                        self.current_typing_position = self._engine_to_display_position(next_pos)
                        self._update_cursor_position()
                    self.engine.mistake_at = None
                    if self.highlighter:
                        self.highlighter.rehighlight()
            else:
                # Going back to strict mode: ensure cursor syncs with engine state
                self.current_typing_position = self._engine_to_display_position(self.engine.state.cursor_position)
                self._update_cursor_position()

    def update_show_typed_characters(self, enabled: bool):
        """Toggle visibility of the actual typed characters."""
        if self.show_typed_characters == enabled:
            return
        self.show_typed_characters = enabled
        self._refresh_typed_display()

    def update_show_ghost_text(self, enabled: bool):
        """Toggle visibility of the ghost text."""
        if self.highlighter:
            self.highlighter.update_show_ghost_text(enabled)

    def set_logging_enabled(self, enabled: bool):
        """Enable or disable logging of typed characters to terminal."""
        self.logging_enabled = enabled
        if enabled:
            print("[TypingArea] Logging enabled")

