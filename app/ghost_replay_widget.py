"""
A dedicated widget to handle the ghost replay animation and controls.
This widget overlays the typing area during replay.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PySide6.QtCore import Qt, QTimer, Signal, QEvent
from PySide6.QtGui import QKeyEvent

class GhostReplayWidget(QWidget):
    """
    A widget that overlays the typing area to show and control a ghost replay.
    """
    replay_finished = Signal()

    def __init__(self, typing_area, parent=None):
        super().__init__(parent)
        self.typing_area = typing_area
        self.ghost_data = None
        self.replay_timers = []
        self.is_replaying = False

        # --- UI Setup ---
        self.setParent(typing_area) # Make it an overlay on the typing area
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            GhostReplayWidget {
                background-color: rgba(46, 52, 64, 0.85);
                border-radius: 5px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        title_label = QLabel("👻 Ghost Replay")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #d8dee9;")
        layout.addWidget(title_label)

        self.status_label = QLabel("Replay in progress...")
        self.status_label.setStyleSheet("font-size: 16px; color: #88c0d0;")
        layout.addWidget(self.status_label)

        stop_button = QPushButton("⏹ Stop Replay")
        stop_button.setStyleSheet("""
            QPushButton {
                background-color: #bf616a;
                color: #eceff4;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #d08770;
            }
        """)
        stop_button.clicked.connect(self.stop_replay)
        layout.addWidget(stop_button)

        self.hide() # Hidden by default

    def start_replay(self, ghost_data: dict):
        """Starts the replay animation."""
        if self.is_replaying:
            return

        self.ghost_data = ghost_data
        self.is_replaying = True

        # Prepare typing area
        self.typing_area.stop_ghost_recording()
        self.typing_area.reset_session()
        self.typing_area.setReadOnly(True)

        # Show overlay
        self.resize(self.parent().size())
        self.show()
        self.raise_()

        # Schedule keystrokes
        keystrokes = self.ghost_data.get("keys", [])
        if not keystrokes:
            self.stop_replay()
            return

        print(f"[GhostReplay] Starting new replay with {len(keystrokes)} keystrokes")

        # Normalize timestamps to start immediately
        first_timestamp = keystrokes[0]["t"]
        for keystroke in keystrokes:
            normalized_time = keystroke["t"] - first_timestamp
            key_char = keystroke["k"]
            
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(lambda k=key_char: self._replay_keystroke(k))
            timer.start(normalized_time)
            self.replay_timers.append(timer)

        # Schedule the end of the replay
        last_normalized_time = keystrokes[-1]["t"] - first_timestamp
        end_timer = QTimer()
        end_timer.setSingleShot(True)
        end_timer.timeout.connect(self.stop_replay)
        end_timer.start(last_normalized_time + 500) # 500ms after last key
        self.replay_timers.append(end_timer)

    def stop_replay(self):
        """Stops the replay and cleans up."""
        if not self.is_replaying:
            return

        print("[GhostReplay] Replay stopped.")
        self.is_replaying = False

        # Clean up timers
        for timer in self.replay_timers:
            timer.stop()
        self.replay_timers.clear()

        # Hide overlay and restore typing area state
        self.hide()
        self.typing_area.setReadOnly(False)
        self.typing_area.start_ghost_recording()

        # Emit signal
        self.replay_finished.emit()

    def _replay_keystroke(self, key_char: str):
        """Simulates a single keystroke event."""
        if not self.is_replaying:
            return

        # Map special characters to Qt key codes
        if key_char == '\b':
            event = QKeyEvent(QEvent.KeyPress, Qt.Key_Backspace, Qt.NoModifier, "")
        elif key_char == '\n':
            event = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier, "\n")
        elif key_char == '\t':
            event = QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier, "\t")
        else:
            # Regular character
            text = key_char
            key_code = ord(text.upper()) if len(text) == 1 else 0
            event = QKeyEvent(QEvent.KeyPress, key_code, Qt.NoModifier, text)
        
        # Post the event to the typing area's event queue
        QApplication.postEvent(self.typing_area, event)

    def resizeEvent(self, event):
        """Ensure the overlay covers the parent."""
        if self.parent():
            self.resize(self.parent().size())
        super().resizeEvent(event)
