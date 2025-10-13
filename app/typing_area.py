"""Typing area widget with character-by-character validation and color coding."""
from PySide6.QtWidgets import QTextEdit, QWidget, QVBoxLayout
from PySide6.QtGui import (
    QTextCharFormat, QColor, QFont, QTextCursor, 
    QKeyEvent, QPalette, QSyntaxHighlighter, QTextDocument
)
from PySide6.QtCore import Qt, Signal, QTimer
from typing import Optional
from app.typing_engine import TypingEngine
from app import settings


class TypingHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for coloring typed/untyped characters."""
    
    def __init__(self, parent: QTextDocument, engine: TypingEngine):
        super().__init__(parent)
        self.engine = engine
        self.show_typed_char = True  # Show what was typed vs expected
        
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
        
        self.typed_chars = {}  # position -> (typed_char, is_correct)
    
    def set_typed_char(self, position: int, typed_char: str, is_correct: bool):
        """Record a typed character at a position."""
        self.typed_chars[position] = (typed_char, is_correct)
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
                typed_char, is_correct = self.typed_chars[pos]
                if is_correct:
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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine: Optional[TypingEngine] = None
        self.highlighter: Optional[TypingHighlighter] = None
        
        # Load space character from settings
        self.space_char = settings.get_setting("space_char", "␣")
        self.enter_char = "⏎"  # Default enter character display
        self.original_content = ""  # Original file content (without special chars)
        self.display_content = ""  # Content with special chars for display
        
        # Configure widget
        self.setReadOnly(True)  # Prevent normal editing
        
        # Load font from settings
        font_family = settings.get_setting("font_family", "Consolas")
        font_size = int(settings.get_setting("font_size", "12"))
        self.setFont(QFont(font_family, font_size))
        
        # Auto-pause timer
        self.pause_timer = QTimer()
        self.pause_timer.timeout.connect(self._check_auto_pause)
        self.pause_timer.start(1000)  # Check every second
        
        # Cursor position tracking
        self.current_typing_position = 0
    
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
        self.engine = TypingEngine(self.original_content, pause_delay=pause_delay)
        
        # Set display content
        self.setPlainText(self.display_content)
        
        # Setup highlighter
        self.highlighter = TypingHighlighter(self.document(), self.engine)
        
        # Reset cursor
        self.current_typing_position = 0
        self._update_cursor_position()
        
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
            self.current_typing_position = progress["cursor_position"]
            self._update_cursor_position()
    
    def _prepare_display_content(self, content: str) -> str:
        """Convert content for display with special characters."""
        result = content.replace(' ', self.space_char)
        result = result.replace('\n', self.enter_char + '\n')
        result = result.replace('\t', self.space_char * 4)  # Tab = 4 spaces
        return result
    
    def _update_cursor_position(self):
        """Update visual cursor to current typing position."""
        cursor = self.textCursor()
        cursor.setPosition(self.current_typing_position)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard input for typing."""
        if not self.engine:
            return
        
        key = event.key()
        text = event.text()
        modifiers = event.modifiers()
        
        # Handle Backspace
        if key == Qt.Key_Backspace:
            if modifiers & Qt.ControlModifier:
                # Ctrl+Backspace
                old_pos = self.engine.state.cursor_position
                self.engine.process_ctrl_backspace()
                new_pos = self.engine.state.cursor_position
                # Clear typed chars in range
                for pos in range(new_pos, old_pos):
                    self.highlighter.clear_typed_char(pos)
                self.current_typing_position = new_pos
                self._update_cursor_position()
            else:
                # Regular backspace
                if self.current_typing_position > 0:
                    self.engine.process_backspace()
                    self.current_typing_position = self.engine.state.cursor_position
                    self.highlighter.clear_typed_char(self.current_typing_position)
                    self._update_cursor_position()
            self.stats_updated.emit()
            return
        
        # Handle Tab
        if key == Qt.Key_Tab:
            # Process 4 spaces for tab
            for _ in range(4):
                if self.engine.state.cursor_position >= len(self.engine.state.content):
                    break
                is_correct, expected = self.engine.process_keystroke(' ')
                self.highlighter.set_typed_char(
                    self.current_typing_position, 
                    self.space_char if not is_correct else self.space_char,
                    is_correct
                )
                if is_correct:
                    self.current_typing_position += 1
            self._update_cursor_position()
            self.stats_updated.emit()
            return
        
        # Handle printable characters
        if text and len(text) == 1:
            char = text
            
            # Map space to actual space
            if key == Qt.Key_Space:
                char = ' '
            # Map Enter to newline
            elif key == Qt.Key_Return or key == Qt.Key_Enter:
                char = '\n'
            
            # Process keystroke
            is_correct, expected = self.engine.process_keystroke(char)
            
            # Display typed character or expected based on settings
            show_typed = settings.get_setting("show_typed_char", "1") == "1"
            display_char = char if not is_correct and show_typed else expected
            
            # Convert for display
            if display_char == ' ':
                display_char = self.space_char
            elif display_char == '\n':
                display_char = self.enter_char
            
            self.highlighter.set_typed_char(
                self.current_typing_position, 
                display_char,
                is_correct
            )
            
            if is_correct:
                self.current_typing_position += 1
            
            self._update_cursor_position()
            self.stats_updated.emit()
            
            # Check if completed
            if self.engine.state.is_complete():
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
            self.current_typing_position = 0
            self._update_cursor_position()
            self.stats_updated.emit()
    
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
            }
        
        return {
            "wpm": self.engine.state.wpm(),
            "accuracy": self.engine.state.accuracy(),
            "time": self.engine.state.elapsed_time,
            "correct": self.engine.state.correct_keystrokes,
            "incorrect": self.engine.state.incorrect_keystrokes,
            "total": self.engine.state.total_keystrokes(),
            "is_paused": self.engine.state.is_paused,
        }
    
    def update_font(self, family: str, size: int, ligatures: bool):
        """Update font settings dynamically."""
        font = QFont(family, size)
        if ligatures:
            font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
    
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
    
    def update_cursor(self, cursor_type: str, cursor_style: str):
        """Update cursor settings dynamically."""
        # Cursor visual updates are handled by Qt's cursor blinking
        # The cursor_type (blinking/static) and cursor_style (block/underscore/ibeam)
        # would need custom rendering implementation for full support
        # For now, we'll use Qt's default cursor behavior
        if cursor_style == "block":
            self.setCursorWidth(10)
        elif cursor_style == "underscore":
            self.setCursorWidth(2)
        elif cursor_style == "ibeam":
            self.setCursorWidth(1)
    
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
    
    def update_pause_delay(self, delay: float):
        """Update auto-pause delay dynamically."""
        if self.engine:
            self.engine.pause_delay = delay
    
    def update_show_typed(self, show_typed: bool):
        """Update show typed character setting dynamically."""
        if self.highlighter:
            self.highlighter.show_typed_char = show_typed
            self.highlighter.rehighlight()
