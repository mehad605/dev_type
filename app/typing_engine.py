"""Typing logic engine - handles character validation, stats calculation, and state management."""
import time
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class TypingState:
    """Current state of a typing session."""
    content: str  # Original file content
    cursor_position: int = 0  # Current typing position
    correct_keystrokes: int = 0
    incorrect_keystrokes: int = 0
    start_time: float = 0
    elapsed_time: float = 0
    is_paused: bool = True
    last_keystroke_time: float = 0
    
    def total_keystrokes(self) -> int:
        return self.correct_keystrokes + self.incorrect_keystrokes
    
    def accuracy(self) -> float:
        total = self.total_keystrokes()
        if total == 0:
            return 1.0
        return self.correct_keystrokes / total
    
    def wpm(self) -> float:
        if self.elapsed_time <= 0:
            return 0.0
        # WPM = (characters / 5) / (time in minutes)
        minutes = self.elapsed_time / 60.0
        if minutes == 0:
            return 0.0
        return (self.cursor_position / 5.0) / minutes
    
    def is_complete(self) -> bool:
        return self.cursor_position >= len(self.content)


class TypingEngine:
    """Engine for managing typing session logic."""
    
    def __init__(self, content: str, pause_delay: float = 7.0):
        self.state = TypingState(content=content)
        self.pause_delay = pause_delay  # Seconds of inactivity before auto-pause
    
    def start(self):
        """Start or resume the typing session."""
        if self.state.is_paused:
            self.state.is_paused = False
            if self.state.start_time == 0:
                self.state.start_time = time.time()
            self.state.last_keystroke_time = time.time()
    
    def pause(self):
        """Pause the typing session."""
        if not self.state.is_paused:
            self.state.is_paused = True
            self.update_elapsed_time()
    
    def update_elapsed_time(self):
        """Update elapsed time (call periodically or before pause)."""
        if not self.state.is_paused and self.state.start_time > 0:
            self.state.elapsed_time = time.time() - self.state.start_time
    
    def check_auto_pause(self) -> bool:
        """Check if session should auto-pause due to inactivity."""
        if not self.state.is_paused and self.state.last_keystroke_time > 0:
            if time.time() - self.state.last_keystroke_time > self.pause_delay:
                self.pause()
                return True
        return False
    
    def process_keystroke(self, typed_char: str, advance_on_error: bool = True) -> Tuple[bool, str]:
        """
        Process a single keystroke.
        
        Args:
            typed_char: The character that was typed
            advance_on_error: Whether to advance cursor on incorrect keystroke
            
        Returns:
            (is_correct, expected_char) tuple
        """
        # Start session if paused
        if self.state.is_paused:
            self.start()
        
        self.state.last_keystroke_time = time.time()
        
        if self.state.cursor_position >= len(self.state.content):
            return False, ""
        
        expected_char = self.state.content[self.state.cursor_position]
        is_correct = typed_char == expected_char
        
        if is_correct:
            self.state.correct_keystrokes += 1
            self.state.cursor_position += 1
        else:
            self.state.incorrect_keystrokes += 1
            if advance_on_error:
                self.state.cursor_position += 1
        
        self.update_elapsed_time()
        return is_correct, expected_char
    
    def process_backspace(self):
        """Process a backspace keystroke."""
        if self.state.cursor_position > 0:
            self.state.cursor_position -= 1
            # Don't count backspace in keystroke stats
            self.state.last_keystroke_time = time.time()
    
    def process_ctrl_backspace(self):
        """Process Ctrl+Backspace (delete word to the left)."""
        if self.state.cursor_position == 0:
            return
        
        # Move back to start of current word
        pos = self.state.cursor_position - 1
        
        # Skip whitespace
        while pos > 0 and self.state.content[pos].isspace():
            pos -= 1
        
        # Skip word characters
        while pos > 0 and not self.state.content[pos].isspace():
            pos -= 1
        
        # Don't go past beginning
        if pos > 0 or self.state.content[0].isspace():
            pos += 1
        
        self.state.cursor_position = pos
        self.state.last_keystroke_time = time.time()
    
    def reset(self):
        """Reset cursor to beginning (revert to start of file)."""
        self.state.cursor_position = 0
        self.state.correct_keystrokes = 0
        self.state.incorrect_keystrokes = 0
        self.state.elapsed_time = 0
        self.state.start_time = 0
        self.state.is_paused = True
        self.state.last_keystroke_time = 0
    
    def load_progress(self, cursor_pos: int, correct: int, incorrect: int, elapsed: float):
        """Load saved progress into the engine."""
        self.state.cursor_position = cursor_pos
        self.state.correct_keystrokes = correct
        self.state.incorrect_keystrokes = incorrect
        self.state.elapsed_time = elapsed
        self.state.is_paused = True
        self.state.start_time = time.time() - elapsed  # Adjust start time
