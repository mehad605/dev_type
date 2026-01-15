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
    max_correct_position: int = -1 # Furthest position correctly typed
    auto_skipped_characters: int = 0  # Characters skipped by auto-indent
    skipped_positions: set = None # Positions skipped by auto-indent
    _session_start: float = 0  # When current typing session started (for pause/resume)
    
    # Keep start_time for backward compatibility but it's not used for timing anymore
    start_time: float = 0
    
    # Per-key stats for this session
    # Maps character to count of correct/incorrect attempts
    key_hits: dict = None  # Lazy init in __post_init__ or process_keystroke
    key_misses: dict = None
    key_confusions: dict = None  # Maps expected char -> {actual_char: count}
    error_types: dict = None  # Maps 'omission', 'insertion', 'transposition', 'substitution' -> count
    
    def __post_init__(self):
        if self.key_hits is None: self.key_hits = {}
        if self.key_misses is None: self.key_misses = {}
        if self.key_confusions is None: self.key_confusions = {}
        if self.error_types is None: self.error_types = {'omission': 0, 'insertion': 0, 'transposition': 0, 'substitution': 0}
        if self.skipped_positions is None: self.skipped_positions = set()
    
    def total_keystrokes(self) -> int:
        return self.correct_keystrokes + self.incorrect_keystrokes
    
    def accuracy(self) -> float:
        total = self.total_keystrokes()
        if total == 0:
            return 1.0
        return self.correct_keystrokes / total
    
    def wpm(self) -> float:
        rounded_seconds = round(self.elapsed_time)
        if rounded_seconds <= 0:
            return 0.0
        # WPM = (characters / 5) / (time in minutes)
        minutes = rounded_seconds / 60.0
        if minutes == 0:
            return 0.0
        return (self._get_calculable_chars() / 5.0) / minutes

    def _get_calculable_chars(self) -> int:
        """Get characters that count towards WPM (only correctly typed characters).
        
        Using correct_keystrokes ensures WPM is based on manually typed correct characters,
        preventing inflated WPM from auto-indent or lenient mode advancement on mistakes.
        """
        return self.correct_keystrokes
    
    def is_complete(self) -> bool:
        return self.cursor_position >= len(self.content)


class TypingEngine:
    """Engine for managing typing session logic."""
    
    def __init__(self, content: str, pause_delay: float = 7.0, allow_continue_mistakes: bool = False):
        self.state = TypingState(content=content)
        self.pause_delay = pause_delay  # Seconds of inactivity before auto-pause
        self.mistake_at: Optional[int] = None
        self.allow_continue_mistakes = allow_continue_mistakes  # Allow continuing despite mistakes
        self.auto_indent = False  # Changed via setter or init
    
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
        """Get the current elapsed time for display, rounded to nearest second."""
        if not self.state.is_paused and self.state._session_start > 0:
            elapsed = self.state.elapsed_time + (time.time() - self.state._session_start)
        else:
            elapsed = self.state.elapsed_time
        return round(elapsed)
    
    def get_wpm(self) -> float:
        """Get the current WPM using live elapsed time."""
        elapsed = self.get_elapsed_time()
        if elapsed <= 0:
            return 0.0
        minutes = elapsed / 60.0
        if minutes == 0 or self.state.correct_keystrokes == 0:
            return 0.0
        return (self.state._get_calculable_chars() / 5.0) / minutes
    
    def check_auto_pause(self) -> bool:
        """Check if session should auto-pause due to inactivity."""
        if not self.state.is_paused and self.state.last_keystroke_time > 0:
            if time.time() - self.state.last_keystroke_time > self.pause_delay:
                self.pause()
                return True
        return False
    
    def _get_line_indentation(self, pos: int) -> int:
        """Find the indentation of the line containing the given position."""
        content = self.state.content
        # Find newline before pos
        start = content.rfind('\n', 0, pos)
        line_start = start + 1 if start != -1 else 0
        
        # Count leading whitespace
        indent = 0
        while line_start + indent < len(content) and content[line_start + indent] in (' ', '\t'):
            indent += 1
        return indent

    def process_keystroke(self, typed_char: str, increment_stats: bool = True, space_per_tab: int = 4) -> Tuple[bool, str, int]:
        """
        Process a single keystroke.
        
        Args:
            typed_char: The character that was typed
            increment_stats: Whether to increment keystroke counters (False for substeps of Tab)
            
        Returns:
            (is_correct, expected_char, skipped_count) tuple
        """
        # Don't process if already finished
        if self.state.is_finished:
            return False, "", 0
            
        # Start session if paused
        if self.state.is_paused:
            self.start()
        
        if increment_stats:
            self.state.last_keystroke_time = time.time()
        
        if self.state.cursor_position >= len(self.state.content):
            return False, "", 0
        
        expected_char = self.state.content[self.state.cursor_position]
        is_correct = typed_char == expected_char
        
        # If there's a mistake and we're not allowing continuation, block input
        if self.mistake_at is not None and not self.allow_continue_mistakes:
            # Count as incorrect keystroke but don't advance
            if increment_stats:
                self.state.incorrect_keystrokes += 1
            return False, expected_char, 0
            
        if is_correct:
            # Only increment correct_keystrokes if this position hasn't been correctly typed before
            if self.state.cursor_position > self.state.max_correct_position:
                if increment_stats:
                    self.state.correct_keystrokes += 1
                self.state.max_correct_position = self.state.cursor_position
                
            if increment_stats:
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
            if self.mistake_at is None:
                self.mistake_at = self.state.cursor_position
            
            if increment_stats:
                self.state.incorrect_keystrokes += 1
                self.state.key_misses[expected_char] = self.state.key_misses.get(expected_char, 0) + 1
                
                # Categorize Error Type (Heuristics)
                # 1. Swapped: User typed the next character
                next_char = self.state.content[self.state.cursor_position + 1] if self.state.cursor_position + 1 < len(self.state.content) else None
                # 2. Missed: User typed the character after next
                next_next_char = self.state.content[self.state.cursor_position + 2] if self.state.cursor_position + 2 < len(self.state.content) else None
                
                if typed_char == next_char:
                    self.state.error_types['transposition'] += 1
                elif typed_char == next_next_char:
                    self.state.error_types['omission'] += 1
                else:
                    self.state.error_types['substitution'] += 1

                # Track key confusions
                if expected_char not in self.state.key_confusions:
                    self.state.key_confusions[expected_char] = {}
                actual_char = typed_char if typed_char else "[NONE]"
                self.state.key_confusions[expected_char][actual_char] = self.state.key_confusions[expected_char].get(actual_char, 0) + 1
            
            if self.allow_continue_mistakes:
                self.state.cursor_position += 1

        if increment_stats:
            self.state.last_keystroke_time = time.time()

        # Check if finished
        if self.state.is_complete():
            self.state.is_finished = True
            self.pause() # Properly pause to accumulate final time
        
        # Smart-indent logic
        skipped_count = 0
        if is_correct and typed_char == '\n' and self.auto_indent:
            # 1. Get previous line indentation
            # The position before the current cursor is where the \n we just typed is
            prev_line_pos = self.state.cursor_position - 1
            prev_indent = self._get_line_indentation(prev_line_pos)
            
            # 2. Check for block openers at the end of the previous line
            # Find the last non-whitespace character on the previous line
            start_search = prev_line_pos
            content = self.state.content
            # Find start of the previous line
            start_newline = content.rfind('\n', 0, prev_line_pos)
            line_start = start_newline + 1 if start_newline != -1 else 0
            
            last_char = None
            for p in range(prev_line_pos - 1, line_start - 1, -1):
                if content[p] not in (' ', '\t', '\r', '\n'):
                    last_char = content[p]
                    break
            
            target_indent = prev_indent
            if last_char in (':', '{', '[', '('):
                target_indent += space_per_tab
            
            # 3. Auto-fill whitespace on the new line up to target_indent
            while self.state.cursor_position < len(self.state.content) and skipped_count < target_indent:
                next_char = self.state.content[self.state.cursor_position]
                if next_char in (' ', '\t'):
                    self.state.skipped_positions.add(self.state.cursor_position)
                    if self.state.cursor_position > self.state.max_correct_position:
                        self.state.max_correct_position = self.state.cursor_position
                    self.state.cursor_position += 1
                    skipped_count += 1
                else:
                    break
                    
        # Return info about skipped characters if any
        return is_correct, expected_char, skipped_count
    
    def process_backspace(self, space_per_tab: int = 4):
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
            content = self.state.content
            pos = self.state.cursor_position
            
            # Find start of line
            start = content.rfind('\n', 0, pos)
            line_start = start + 1 if start != -1 else 0
            
            # Check if all characters from line_start to pos are whitespace
            is_leading_whitespace = True
            all_skipped = True
            for i in range(line_start, pos):
                if content[i] not in (' ', '\t'):
                    is_leading_whitespace = False
                    all_skipped = False
                    break
                if i not in self.state.skipped_positions:
                    all_skipped = False
            
            # Undo Auto-Indent: If this entire line of whitespace was auto-inserted (skipped),
            # pressing backspace should revert the whole thing including the newline
            if self.auto_indent and is_leading_whitespace and all_skipped and (pos - line_start) > 0:
                # Remove skipped marks for this range
                for p in range(line_start, pos):
                    if p in self.state.skipped_positions:
                        self.state.skipped_positions.remove(p)
                
                # Jump back before the newline (if exists)
                self.state.cursor_position = max(0, line_start - 1)
                self.state.last_keystroke_time = time.time()
                return
            
            # Smart backspace: if we are in leading whitespace and at a tab stop AND auto indent is on
            if self.auto_indent and is_leading_whitespace and (pos - line_start) > 0 and (pos - line_start) % space_per_tab == 0:
                # Delete a whole level
                for _ in range(space_per_tab):
                    if self.state.cursor_position > line_start:
                        self.state.cursor_position -= 1
                        if self.state.cursor_position in self.state.skipped_positions:
                            self.state.skipped_positions.remove(self.state.cursor_position)
            else:
                self.state.cursor_position -= 1
                # If we backspace over a skipped character, remove it from skipped set
                if self.state.cursor_position in self.state.skipped_positions:
                    self.state.skipped_positions.remove(self.state.cursor_position)
            
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

        # Remove any skipped positions in the range we're deleting
        for p in list(self.state.skipped_positions):
            if pos <= p < self.state.cursor_position:
                self.state.skipped_positions.remove(p)
            
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
        self.state.max_correct_position = -1
        self.state.skipped_positions.clear()
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
    
    def load_progress(self, cursor_pos: int, correct: int, incorrect: int, elapsed: float,
                      mistake_at: int = -1, max_correct_pos: int = -1, skipped_positions: set = None):
        """Load saved progress into the engine."""
        self.state.cursor_position = cursor_pos
        self.state.correct_keystrokes = correct
        self.state.incorrect_keystrokes = incorrect
        self.state.elapsed_time = elapsed
        
        # Restore max_correct_position if provided, else fallback to cursor-1
        if max_correct_pos != -1:
            self.state.max_correct_position = max_correct_pos
        else:
            self.state.max_correct_position = max(self.state.max_correct_position, cursor_pos - 1)
            
        self.state.is_paused = True
        self.state.start_time = time.time() - elapsed  # Adjust start time
        self.mistake_at = mistake_at if mistake_at != -1 else None
        
        if skipped_positions:
            self.state.skipped_positions = skipped_positions
