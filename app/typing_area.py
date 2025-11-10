"""Typing area widget with character-by-character validation and color coding."""
from PySide6.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QApplication
from PySide6.QtGui import (
    QTextCharFormat, QColor, QFont, QTextCursor,
    QKeyEvent, QPalette, QSyntaxHighlighter, QTextDocument, QPainter
)
from PySide6.QtCore import Qt, Signal, QTimer, QRect, QPoint, QPropertyAnimation, QEasingCurve, QObject, Property
from typing import Optional
from app.typing_engine import TypingEngine
from app import settings


class TypingHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for coloring typed/untyped characters."""
    
    def __init__(self, parent: QTextDocument, engine: TypingEngine):
        super().__init__(parent)
        self.engine = engine
        
        # Color formats - load from settings
        self.untyped_format = QTextCharFormat()
        untyped_color = settings.get_setting("color_untyped", "#555555")
        self.untyped_format.setForeground(QColor(untyped_color))
        
        self.correct_format = QTextCharFormat()
        correct_color = settings.get_setting("color_correct", "#00ff00")
        self.correct_format.setForeground(QColor(correct_color))
        
        self.incorrect_format = QTextCharFormat()
        incorrect_color = settings.get_setting("color_incorrect", "#ff0000")
        self.incorrect_format.setForeground(QColor(incorrect_color))
        
        self.typed_chars = {}  # position -> {typed, expected, is_correct}
    
    def set_typed_char(self, position: int, typed_char: str, expected_char: str, is_correct: bool):
        """Record a typed character at a position."""
        self.typed_chars[position] = {
            "typed": typed_char,
            "expected": expected_char,
            "is_correct": is_correct,
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
        
        for i, char in enumerate(text):
            pos = block_start + i
            
            if pos in self.typed_chars:
                info = self.typed_chars[pos]
                if info["is_correct"]:
                    self.setFormat(i, 1, self.correct_format)
                else:
                    self.setFormat(i, 1, self.incorrect_format)
            elif pos < self.engine.state.cursor_position:
                # Already typed correctly (moved past it)
                self.setFormat(i, 1, self.correct_format)
            else:
                # Not yet typed
                self.setFormat(i, 1, self.untyped_format)


class TypingAreaWidget(QTextEdit):
    """Text area widget for typing practice with validation and color coding."""
    
    stats_updated = Signal()  # Emitted when stats change
    session_completed = Signal()  # Emitted when file is fully typed
    mistake_occurred = Signal()  # Emitted when user makes a typing mistake
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine: Optional[TypingEngine] = None
        self.highlighter: Optional[TypingHighlighter] = None
        
        # Load settings
        self.space_char = settings.get_setting("space_char", "␣")
        self.enter_char = "⏎"  # Default enter character display
        self.original_content = ""  # Original file content (without special chars)
        self.display_content = ""  # Content with special chars for display
        self.show_typed_characters = settings.get_setting("show_typed_characters", "0") == "1"

        # Custom cursor state
        self.cursor_color = QColor(settings.get_setting("color_cursor", "#ffffff"))
        self.cursor_style = settings.get_setting("cursor_style", "block").lower()
        self.cursor_blink_mode = settings.get_setting("cursor_type", "blinking").lower()
        self._cursor_visible = True
        self._cursor_rect = QRect()
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._toggle_cursor_visible)
        
        # Smooth cursor animation
        self._target_cursor_rect = QRect()
        self._animated_cursor_x = 0.0
        self._animated_cursor_y = 0.0
        self._cursor_animation_x = QPropertyAnimation(self, b"_cursor_x_pos")
        self._cursor_animation_x.setDuration(80)  # 0.08 seconds like the example
        self._cursor_animation_x.setEasingCurve(QEasingCurve.OutCubic)  # Smooth ease-out
        self._cursor_animation_y = QPropertyAnimation(self, b"_cursor_y_pos")
        self._cursor_animation_y.setDuration(80)
        self._cursor_animation_y.setEasingCurve(QEasingCurve.OutCubic)
        
        # Configure widget
        self.setReadOnly(True)  # Prevent normal editing
        self.setTabChangesFocus(False)
        
        # Load font from settings
        font_family = settings.get_setting("font_family", "Consolas")
        font_size = int(settings.get_setting("font_size", "12"))
        self.setFont(QFont(font_family, font_size))

        # Track cursor position changes for custom drawing
        self.cursorPositionChanged.connect(self._on_qt_cursor_changed)
        
        # Load cursor settings
        cursor_type = settings.get_setting("cursor_type", "blinking")
        cursor_style = settings.get_setting("cursor_style", "block")
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
        self.ghost_start_time = None
    
    # Property for smooth cursor animation
    def _get_cursor_x_pos(self):
        return self._animated_cursor_x
    
    def _set_cursor_x_pos(self, value):
        self._animated_cursor_x = value
        self._update_animated_cursor_rect()
    
    _cursor_x_pos = Property(float, _get_cursor_x_pos, _set_cursor_x_pos)
    
    def _get_cursor_y_pos(self):
        return self._animated_cursor_y
    
    def _set_cursor_y_pos(self, value):
        self._animated_cursor_y = value
        self._update_animated_cursor_rect()
    
    _cursor_y_pos = Property(float, _get_cursor_y_pos, _set_cursor_y_pos)
    
    def _update_animated_cursor_rect(self):
        """Update cursor rect based on animated position."""
        if self._target_cursor_rect.isNull():
            return
        
        # Create new rect at animated position
        animated_rect = QRect(self._target_cursor_rect)
        animated_rect.moveLeft(int(self._animated_cursor_x))
        animated_rect.moveTop(int(self._animated_cursor_y))
        
        old_rect = QRect(self._cursor_rect)
        self._cursor_rect = animated_rect
        self._request_cursor_paint(old_rect)
    
    def load_file(self, file_path: str):
        """Load a file for typing practice."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.original_content = f.read()
        except Exception as e:
            self.original_content = f"Error loading file: {e}"
        
        # Convert content for display (replace spaces, enters, tabs)
        self.display_content = self._prepare_display_content(self.original_content)
        
        # Initialize engine
        pause_delay = float(settings.get_setting("pause_delay", "7"))
        allow_continue = settings.get_setting("allow_continue_mistakes", "0") == "1"
        self.engine = TypingEngine(self.original_content, pause_delay=pause_delay, allow_continue_mistakes=allow_continue)
        
        # Set display content
        self.setPlainText(self.display_content)
        
        # Setup highlighter
        self.highlighter = TypingHighlighter(self.document(), self.engine)
        
        # Reset cursor
        self.current_typing_position = 0
        self._update_cursor_position()
        
        # Start ghost recording for this session
        self.start_ghost_recording()
        
        # Try to load saved progress
        from app import stats_db
        progress = stats_db.get_session_progress(file_path)
        if progress:
            self.engine.load_progress(
                cursor_pos=progress["cursor_position"],
                correct=progress["correct"],
                incorrect=progress["incorrect"],
                elapsed=progress["time"]
            )
            self.current_typing_position = self._engine_to_display_position(self.engine.state.cursor_position)
            self._update_cursor_position()
            if self.highlighter:
                self.highlighter.rehighlight()
        else:
            if self.highlighter:
                self.highlighter.clear_all()

        self.stats_updated.emit()
    
    def start_ghost_recording(self):
        """Start recording keystrokes for potential ghost session."""
        import time
        self.is_recording_ghost = True
        self.ghost_keystrokes = []
        self.ghost_start_time = time.time()
        print("[GhostRecorder] Started recording")
    
    def stop_ghost_recording(self):
        """Stop recording keystrokes."""
        self.is_recording_ghost = False
        print(f"[GhostRecorder] Stopped recording ({len(self.ghost_keystrokes)} keystrokes)")
    
    def _record_keystroke(self, key_char: str, is_correct: bool):
        """Record a keystroke for ghost replay."""
        if not self.is_recording_ghost or self.ghost_start_time is None:
            return
        
        import time
        timestamp_ms = int((time.time() - self.ghost_start_time) * 1000)
        
        # Compact format: t=timestamp, k=key, c=correct (1/0)
        self.ghost_keystrokes.append({
            "t": timestamp_ms,
            "k": key_char,
            "c": 1 if is_correct else 0
        })
    
    def get_ghost_data(self) -> list:
        """Get recorded ghost keystrokes."""
        return self.ghost_keystrokes
    
    def _prepare_display_content(self, content: str) -> str:
        """Convert content for display with special characters."""
        result = content.replace(' ', self.space_char)
        result = result.replace('\n', self.enter_char + '\n')
        result = result.replace('\t', self.space_char * 4)  # Tab = 4 spaces
        return result
    
    def _display_char_for(self, char: str) -> str:
        """Return the visual representation of a character."""
        if char == ' ':
            return self.space_char
        if char == '\n':
            return self.enter_char
        if char == '\t':
            return self.space_char * 4
        return char

    def _replace_display_char(self, position: int, new_char: str, length: int = 1):
        """Replace the character shown at a position without changing engine state."""
        original_cursor = self.textCursor()
        cursor = QTextCursor(self.document())
        cursor.setPosition(position)
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
        """Re-apply display text for all typed positions based on current visibility mode."""
        if not self.highlighter or not self.highlighter.typed_chars:
            return

        for position, info in self.highlighter.typed_chars.items():
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
        """Map a display index back to the underlying engine index."""
        if display_pos <= 0:
            return 0

        content = self.engine.state.content if self.engine else self.original_content
        if not content:
            return 0

        space_len = len(self.space_char) if self.space_char else 1
        enter_len = len(self.enter_char) if self.enter_char else 1
        current_display = 0

        for idx, ch in enumerate(content):
            if ch == '\n':
                step = enter_len + 1
            elif ch == '\t':
                step = space_len * 4
            elif ch == ' ':
                step = space_len
            else:
                step = 1

            if current_display + step > display_pos:
                return idx

            current_display += step

        return len(content)

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

    def _update_cursor_position(self):
        """Update visual cursor to current typing position."""
        cursor = self.textCursor()
        cursor.setPosition(self.current_typing_position, QTextCursor.MoveAnchor)
        cursor.clearSelection()
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self._update_cursor_geometry()

    def _engine_to_display_position(self, engine_pos: int) -> int:
        """Convert an engine cursor index to the displayed document index."""
        if engine_pos <= 0:
            return 0

        if self.engine:
            content = self.engine.state.content
        else:
            content = self.original_content

        engine_pos = min(engine_pos, len(content))

        display_pos = 0
        space_len = len(self.space_char) if self.space_char else 1
        enter_len = len(self.enter_char) if self.enter_char else 1

        for idx in range(engine_pos):
            ch = content[idx]
            if ch == '\n':
                display_pos += enter_len + 1  # symbol plus newline character
            elif ch == '\t':
                display_pos += space_len * 4
            elif ch == ' ':
                display_pos += space_len
            else:
                display_pos += 1

        return display_pos

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
        """Recalculate cursor rectangle based on style and animate to new position."""
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

        # Store target rectangle
        self._target_cursor_rect = rect
        
        # If this is the first position or animation is disabled, jump immediately
        if self._cursor_rect.isNull() or not self.hasFocus():
            self._animated_cursor_x = float(rect.left())
            self._animated_cursor_y = float(rect.top())
            self._cursor_rect = rect
            self._request_cursor_paint()
            return
        
        # Stop any running animations
        self._cursor_animation_x.stop()
        self._cursor_animation_y.stop()
        
        # Animate smoothly to new position (like CSS transition)
        self._cursor_animation_x.setStartValue(self._animated_cursor_x)
        self._cursor_animation_x.setEndValue(float(rect.left()))
        self._cursor_animation_y.setStartValue(self._animated_cursor_y)
        self._cursor_animation_y.setEndValue(float(rect.top()))
        
        self._cursor_animation_x.start()
        self._cursor_animation_y.start()

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
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard input for typing."""
        if not self.engine:
            return
        
        key = event.key()
        text = event.text()
        modifiers = event.modifiers()
        
        # Intercept Ctrl+P for pause/unpause (don't process as typing)
        if key == Qt.Key_P and modifiers == Qt.ControlModifier:
            # Toggle pause state
            if self.engine.state.is_paused:
                self.engine.start()
            else:
                self.engine.pause()
            self.stats_updated.emit()
            event.accept()
            return
        
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
                self._update_cursor_position()
            else:
                # Regular backspace
                self._record_keystroke("\b", True)
                if self.engine.state.cursor_position > 0 or self.engine.mistake_at is not None:
                    self.engine.process_backspace()
                    target_index = self.engine.state.cursor_position
                    self._clear_and_restore_engine_position(target_index)
                    self.current_typing_position = self._engine_to_display_position(target_index)
                    self._update_cursor_position()
            self.stats_updated.emit()
            return
        
        # Handle Tab
        if key == Qt.Key_Tab:
            sound_mgr.play_keypress()  # Sound for tab
            all_correct = True
            spaces_processed = 0
            # Process 4 spaces for tab
            for _ in range(4):
                if self.engine.state.cursor_position >= len(self.engine.state.content):
                    break
                position = self._engine_to_display_position(self.engine.state.cursor_position)
                expected_char = self.engine.state.content[self.engine.state.cursor_position]
                expected_display = self._display_char_for(expected_char)
                is_correct, expected_from_engine = self.engine.process_keystroke(' ')
                if not is_correct:
                    all_correct = False
                if expected_from_engine == "" and not is_correct:
                    # Record failed tab attempt before exiting
                    self._record_keystroke('\t', False)
                    self.stats_updated.emit()
                    return
                self.highlighter.set_typed_char(
                    position,
                    self.space_char,
                    expected_display,
                    is_correct
                )
                self._apply_display_for_position(position)
                spaces_processed += 1
            if spaces_processed:
                self._record_keystroke('\t', all_correct)
            self.current_typing_position = self._engine_to_display_position(self.engine.state.cursor_position)
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
            is_correct, expected = self.engine.process_keystroke(char)
            
            # Record keystroke for ghost
            self._record_keystroke(char, is_correct)
            
            # Check for instant death mode BEFORE displaying the mistake
            if not is_correct:
                from app import settings
                instant_death_enabled = settings.get_setting("instant_death_mode", "0") == "1"
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
            
            # Update cursor position (engine already advanced if allowed)
            self.current_typing_position = self._engine_to_display_position(self.engine.state.cursor_position)
            
            # If there's a mistake, show cursor after the mistake visually
            visual_cursor_pos = self.current_typing_position
            if self.engine.mistake_at is not None:
                mistake_display_pos = self._engine_to_display_position(self.engine.mistake_at)
                if mistake_display_pos == visual_cursor_pos:
                    # Show cursor after the mistake character so it's clear where the error is
                    visual_cursor_pos = mistake_display_pos + 1
            
            # Update visual cursor
            cursor = self.textCursor()
            cursor.setPosition(visual_cursor_pos, QTextCursor.MoveAnchor)
            cursor.clearSelection()
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
            self._update_cursor_geometry()
            
            self.stats_updated.emit()
            
            # Check if completed
            if self.engine.state.is_finished:
                # Emit one final stats update with the completion stats
                self.stats_updated.emit()
                self.session_completed.emit()
    
    def _check_auto_pause(self):
        """Check if session should auto-pause."""
        if self.engine and self.engine.check_auto_pause():
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
    
    def _calculate_current_accuracy(self) -> float:
        """Calculate accuracy based on current text correctness rather than keystroke history."""
        if not self.engine:
            return 1.0

        typed_entries = self.highlighter.typed_chars if self.highlighter else {}
        total_positions = len(typed_entries)
        correct_positions = 0

        if total_positions:
            correct_positions = sum(1 for info in typed_entries.values() if info.get("is_correct"))

        cursor_pos = self.engine.state.cursor_position
        if cursor_pos > total_positions:
            gap = cursor_pos - total_positions
            total_positions += gap
            correct_positions += gap

        if total_positions == 0:
            return 1.0

        return correct_positions / total_positions

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
            "wpm": self.engine.state.wpm(),
            "accuracy": self._calculate_current_accuracy(),
            "time": self.engine.state.elapsed_time,
            "correct": self.engine.state.correct_keystrokes,
            "incorrect": self.engine.state.incorrect_keystrokes,
            "total": self.engine.state.total_keystrokes(),
            "is_paused": self.engine.state.is_paused,
            "is_finished": self.engine.state.is_finished,
        }
    
    def update_font(self, family: str, size: int, ligatures: bool):
        """Update font settings dynamically."""
        font = QFont(family, size)
        if ligatures:
            font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self._update_cursor_geometry()
    
    def update_colors(self):
        """Update color settings dynamically."""
        if self.highlighter:
            # Reload colors from settings
            untyped_color = settings.get_setting("color_untyped", "#555555")
            self.highlighter.untyped_format.setForeground(QColor(untyped_color))
            
            correct_color = settings.get_setting("color_correct", "#00ff00")
            self.highlighter.correct_format.setForeground(QColor(correct_color))
            
            incorrect_color = settings.get_setting("color_incorrect", "#ff0000")
            self.highlighter.incorrect_format.setForeground(QColor(incorrect_color))
            
            # Trigger rehighlight to apply changes
            self.highlighter.rehighlight()

        cursor_color_value = settings.get_setting("color_cursor", "#ffffff")
        self.cursor_color = QColor(cursor_color_value)
        self._request_cursor_paint()
    
    def update_cursor(self, cursor_type: str, cursor_style: str):
        """Update cursor settings dynamically."""
        self.cursor_blink_mode = (cursor_type or "blinking").lower()
        self.cursor_style = (cursor_style or "block").lower()

        # Hide Qt's default cursor so we can draw our own
        self.setCursorWidth(0)
        self._update_cursor_geometry()
        self._update_blink_timer()
        self.viewport().update()
    
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
