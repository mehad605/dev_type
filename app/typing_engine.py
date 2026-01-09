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
    elapsed_time: float = 0  # Total accumulated typing time (excludes pauses)
    is_paused: bool = True
    last_keystroke_time: float = 0
    is_finished: bool = False  # Track if session is completed
    _session_start: float = 0  # When current typing session started (for pause/resume)
    
    # Keep start_time for backward compatibility but it's not used for timing anymore
    start_time: float = 0
    
    # Per-key stats for this session
    # Maps character to count of correct/incorrect attempts
    key_hits: dict = None  # Lazy init in __post_init__ or process_keystroke
    key_misses: dict = None
    key_confusions: dict = None  # Maps expected char -> {actual_char: count}
    
    def __post_init__(self):
        if self.key_hits is None: self.key_hits = {}
        if self.key_misses is None: self.key_misses = {}
        if self.key_confusions is None: self.key_confusions = {}
    
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
    
    def __init__(self, content: str, pause_delay: float = 7.0, allow_continue_mistakes: bool = False):
        self.state = TypingState(content=content)
        self.pause_delay = pause_delay  # Seconds of inactivity before auto-pause
        self.mistake_at: Optional[int] = None
        self.allow_continue_mistakes = allow_continue_mistakes  # Allow continuing despite mistakes
    
    def start(self):
        """Start or resume the typing session."""
        if self.state.is_paused:
            self.state.is_paused = False
            # Record when this active typing session started
            self.state._session_start = time.time()
            if self.state.start_time == 0:
                self.state.start_time = time.time()  # For backward compatibility
            self.state.last_keystroke_time = time.time()
    
    def pause(self):
        """Pause the typing session."""
        if not self.state.is_paused:
            # Accumulate time from this session before pausing
            if self.state._session_start > 0:
                self.state.elapsed_time += time.time() - self.state._session_start
                self.state._session_start = 0
            self.state.is_paused = True
    
    def update_elapsed_time(self):
        """Legacy method - no longer needed as get_elapsed_time() calculates live time."""
        pass  # Time is now calculated on-demand via get_elapsed_time()
    
    def get_elapsed_time(self) -> float:
        """Get the current elapsed time for display."""
        if not self.state.is_paused and self.state._session_start > 0:
            return self.state.elapsed_time + (time.time() - self.state._session_start)
        return self.state.elapsed_time
    
    def get_wpm(self) -> float:
        """Get the current WPM using live elapsed time."""
        elapsed = self.get_elapsed_time()
        if elapsed <= 0:
            return 0.0
        minutes = elapsed / 60.0
        if minutes == 0:
            return 0.0
        return (self.state.cursor_position / 5.0) / minutes
    
    def check_auto_pause(self) -> bool:
        """Check if session should auto-pause due to inactivity."""
        if not self.state.is_paused and self.state.last_keystroke_time > 0:
            if time.time() - self.state.last_keystroke_time > self.pause_delay:
                self.pause()
                return True
        return False
    
    def process_keystroke(self, typed_char: str) -> Tuple[bool, str]:
        """
        Process a single keystroke.
        
        Args:
            typed_char: The character that was typed
            
        Returns:
            (is_correct, expected_char) tuple
        """
        # Don't process if already finished
        if self.state.is_finished:
            return False, ""
            
        # Start session if paused
        if self.state.is_paused:
            self.start()
        
        self.state.last_keystroke_time = time.time()
        
        if self.state.cursor_position >= len(self.state.content):
            return False, ""
        
        # If there's a mistake and we're not allowing continuation, block input
        if self.mistake_at is not None and not self.allow_continue_mistakes:
            # Count as incorrect keystroke but don't advance
            self.state.incorrect_keystrokes += 1
            return False, ""
            
        expected_char = self.state.content[self.state.cursor_position]
        is_correct = typed_char == expected_char
        
        if is_correct:
            self.state.correct_keystrokes += 1
            self.state.key_hits[expected_char] = self.state.key_hits.get(expected_char, 0) + 1
            self.state.cursor_position += 1
            
            # Clear mistake marker if we were allowing continuation and typed correctly
            if self.mistake_at is not None and self.mistake_at < self.state.cursor_position:
                self.mistake_at = None
            
            # Check if we just completed the file
            if self.state.cursor_position >= len(self.state.content):
                self.state.is_finished = True
                self.pause()  # Properly pause to accumulate final time
        else:
            self.state.incorrect_keystrokes += 1
            self.state.key_misses[expected_char] = self.state.key_misses.get(expected_char, 0) + 1
            
            # Record what was typed instead
            if expected_char not in self.state.key_confusions:
                self.state.key_confusions[expected_char] = {}
            actual_char = typed_char if typed_char else "[NONE]"
            self.state.key_confusions[expected_char][actual_char] = self.state.key_confusions[expected_char].get(actual_char, 0) + 1
            
            if self.allow_continue_mistakes:
                # Allow cursor to advance even on mistakes
                self.state.cursor_position += 1
                # Track that there was a mistake (for UI highlighting)
                if self.mistake_at is None:
                    self.mistake_at = self.state.cursor_position - 1
            else:
                # Don't advance cursor on incorrect keystroke
                self.mistake_at = self.state.cursor_position
        
        return is_correct, expected_char
    
    def process_backspace(self):
        """Process a backspace keystroke."""
        # If there's a mistake at current position and we're in strict mode,
        # just clear the mistake marker without moving the cursor
        if self.mistake_at is not None and self.state.cursor_position == self.mistake_at and not self.allow_continue_mistakes:
            self.mistake_at = None
            self.state.last_keystroke_time = time.time()
            return
        
        # In lenient mode or when mistake is behind us, clear mistake marker
        # and move cursor back
        if self.mistake_at is not None:
            self.mistake_at = None
        
        # Move cursor back if possible
        if self.state.cursor_position > 0:
            self.state.cursor_position -= 1
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
        
        # If we backspaced over a mistake, clear the lock
        if self.mistake_at is not None and pos <= self.mistake_at:
            self.mistake_at = None
            
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
        self.state.is_finished = False
        self.mistake_at = None
    
    def reset_cursor_only(self):
        """Reset cursor to beginning but keep stats running (for race mode instant death)."""
        self.state.cursor_position = 0
        self.mistake_at = None
        # Keep time running, keep keystroke counts, keep paused state
    
    def get_final_stats(self) -> dict:
        """Get final stats at the end of a session."""
        return {
            "wpm": self.get_wpm(),
            "accuracy": self.state.accuracy(),
            "time": self.get_elapsed_time(),
            "total": self.state.total_keystrokes(),
            "correct": self.state.correct_keystrokes,
            "incorrect": self.state.incorrect_keystrokes,
            "status_text": "Finished",
            "status_color": "#a3be8c"  # Green for finished
        }
    
    def load_progress(self, cursor_pos: int, correct: int, incorrect: int, elapsed: float):
        """Load saved progress into the engine."""
        self.state.cursor_position = cursor_pos
        self.state.correct_keystrokes = correct
        self.state.incorrect_keystrokes = incorrect
        self.state.elapsed_time = elapsed
        self.state.is_paused = True
        self.state.start_time = time.time() - elapsed  # Adjust start time
        self.mistake_at = None  # Don't load mistake state
