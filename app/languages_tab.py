"""Languages tab widget for displaying language-grouped files."""
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QLabel,
    QFrame,
    QGridLayout,
)
from PySide6.QtCore import Qt, Signal, QObject, QRunnable, QThreadPool
from typing import Callable, Dict, List, Optional, Tuple
from app import settings, stats_db
from app.language_cache import build_signature, load_cached_snapshot, save_snapshot

# Debug timing flag
DEBUG_STARTUP_TIMING = True


def _get_icon_manager():
    # Delay icon loader import until a card draws
    from app.icon_manager import get_icon_manager

    return get_icon_manager()


def _get_folder_scanner():
    # Fetch scanner lazily to avoid loading heavy modules on startup
    from app.file_scanner import scan_folders

    return scan_folders


class _LanguageScanSignals(QObject):
    completed = Signal(dict, tuple)


class _LanguageScanTask(QRunnable):
    """Background task that scans folders for language groupings."""

    def __init__(self, folders_snapshot: Tuple[str, ...], scanner: Callable[[List[str]], Dict[str, List[str]]]):
        super().__init__()
        self.folders_snapshot = folders_snapshot
        self.signals = _LanguageScanSignals()
        self._scanner = scanner

    def run(self):
        try:
            result = self._scanner(list(self.folders_snapshot))
        except Exception:
            result = {}
        self.signals.completed.emit(result, self.folders_snapshot)


class LanguageCard(QFrame):
    """Card widget displaying a single language with stats."""

    clicked = Signal(str, list)  # language_name, file_paths

    def __init__(
        self,
        language: str,
        files: List[str],
        average_wpm: Optional[float] = None,
        sample_size: int = 0,
        completed_count: int = 0,
        parent=None,
    ):
        super().__init__(parent)
        self.language = language
        self.files = files
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(2)
        self.setMinimumSize(200, 150)
        self.setMaximumSize(250, 180)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)

        # Language icon - try to get from icon manager, fallback to emoji
        icon_manager = _get_icon_manager()
        icon_pixmap = icon_manager.get_icon(language, size=48)
        
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        
        if icon_pixmap:
            # Use downloaded icon
            icon_label.setPixmap(icon_pixmap)
        else:
            # Fallback to emoji
            emoji = icon_manager.get_emoji_fallback(language)
            icon_label.setText(emoji)
            icon_label.setStyleSheet("font-size: 48px;")
        
        layout.addWidget(icon_label)
        
        # Language name
        name_label = QLabel(language)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(name_label)

        # File count (completed/total)
        completed = max(0, completed_count)
        total = len(files)
        count_label = QLabel(f"{completed}/{total} files")
        count_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(count_label)

        # Avg WPM (placeholder)
        self.wpm_label = QLabel()
        self.wpm_label.setAlignment(Qt.AlignCenter)
        self._set_wpm_display(average_wpm, sample_size)
        layout.addWidget(self.wpm_label)
        
        layout.addStretch()
    
    def mousePressEvent(self, event):
        """Handle card click."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.language, self.files)
        super().mousePressEvent(event)

    def _set_wpm_display(self, average_wpm: Optional[float], sample_size: int):
        """Update the WPM label contents and styling."""
        if average_wpm is None or sample_size == 0:
            self.wpm_label.setText("Avg WPM: --")
            self.wpm_label.setStyleSheet("color: gray; font-size: 12px;")
        else:
            label = f"Avg WPM (last {sample_size}): {average_wpm:.1f}"
            self.wpm_label.setText(label)
            self.wpm_label.setStyleSheet("color: #88c0d0; font-size: 12px; font-weight: bold;")


class LanguagesTab(QWidget):
    """Tab displaying all detected languages as cards."""
    
    def __init__(self, parent=None):
        if DEBUG_STARTUP_TIMING:
            import time
            t_start = time.time()
        
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self._thread_pool = QThreadPool.globalInstance()
        self._loaded = False
        self._loading = False
        self._cached_language_files: Dict[str, List[str]] = {}
        self._last_snapshot: Tuple[str, ...] = tuple()
        self._pending_snapshot: Tuple[str, ...] = tuple()
        self._last_signature: Optional[str] = None
        self._pending_signature: Optional[str] = None
        self._active_task: Optional[_LanguageScanTask] = None
        self._status_label: Optional[QLabel] = None

        if DEBUG_STARTUP_TIMING:
            t = time.time()
        cached = load_cached_snapshot()
        if cached:
            signature, language_files = cached
            self._cached_language_files = language_files
            self._last_signature = signature
        if DEBUG_STARTUP_TIMING:
            print(f"    [LanguagesTab] Load cache: {time.time() - t:.3f}s")
        
        # Header
        header = QLabel("Languages detected in your folders")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        self.layout.addWidget(header)
        
        # Scroll area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container for cards
        self.card_container = QWidget()
        self.card_layout = QGridLayout(self.card_container)
        self.card_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(self.card_container)
        
        self.layout.addWidget(scroll)
        self._show_message("Languages load when needed. Switch to this tab to scan your folders.")
        
        if DEBUG_STARTUP_TIMING:
            print(f"    [LanguagesTab] TOTAL: {time.time() - t_start:.3f}s")
    
    def _clear_cards(self):
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._status_label = None

    def _show_message(self, message: str):
        self._clear_cards()
        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: gray; padding: 20px;")
        self.card_layout.addWidget(label, 0, 0)
        self._status_label = label

    def _populate_cards(self, language_files: Dict[str, List[str]]):
        self._clear_cards()
        if not language_files:
            self._show_message("No code files found in added folders.")
            return

        row, col = 0, 0
        max_cols = 4
        all_files = [path for paths in language_files.values() for path in paths]
        stats_map = stats_db.get_file_stats_for_files(all_files)

        for lang, files in sorted(language_files.items()):
            recent = stats_db.get_recent_wpm_average(files, limit=10)
            avg_wpm = None
            sample_size = 0
            if recent:
                avg_wpm = recent.get("average")
                sample_size = recent.get("count", 0)
            completed_count = sum(
                1 for path in files if stats_map.get(path, {}).get("completed")
            )
            card = LanguageCard(lang, files, avg_wpm, sample_size, completed_count)
            card.clicked.connect(self.on_language_clicked)
            self.card_layout.addWidget(card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def ensure_loaded(self, force: bool = False):
        """Ensure the tab has loaded language data, triggering a scan if needed."""
        if self._loading:
            return

        folders = settings.get_folders()
        snapshot = tuple(sorted(folders))

        if not folders:
            self._cached_language_files = {}
            self._loaded = True
            self._last_snapshot = snapshot
            self._last_signature = None
            self._show_message("No folders added. Go to Folders tab to add some.")
            return

        signature = build_signature(folders)

        if not force and snapshot == self._last_snapshot and signature == self._last_signature:
            if self._cached_language_files:
                self._populate_cards(self._cached_language_files)
                self._loaded = True
            return

        if (
            not force
            and self._cached_language_files
            and signature == self._last_signature
        ):
            self._populate_cards(self._cached_language_files)
            self._loaded = True
            self._last_snapshot = snapshot
            return

        self._loading = True
        self._pending_snapshot = snapshot
        self._pending_signature = signature
        self._show_message("Scanning folders…")

        scanner = _get_folder_scanner()
        task = _LanguageScanTask(snapshot, scanner)
        task.signals.completed.connect(self._on_scan_finished)
        self._active_task = task
        self._thread_pool.start(task)

    def _on_scan_finished(self, language_files: Dict[str, List[str]], snapshot: Tuple[str, ...]):
        if snapshot != self._pending_snapshot:
            return

        self._loading = False
        self._active_task = None
        self._last_snapshot = snapshot
        self._last_signature = self._pending_signature
        self._pending_signature = None
        self._cached_language_files = language_files
        self._loaded = True
        if self._last_signature is not None:
            try:
                save_snapshot(self._last_signature, language_files)
            except OSError:
                pass

        if not language_files:
            self._show_message("No code files found in added folders.")
        else:
            self._populate_cards(language_files)

    def refresh_languages(self, force: bool = False):
        """Public method to refresh language data, optionally forcing a rescan."""
        self.ensure_loaded(force=force)

    def mark_dirty(self):
        """Indicate folder data changed so a fresh scan runs next time."""
        self._loaded = False
        self._cached_language_files = {}
        self._pending_snapshot = tuple()
        self._pending_signature = None
        self._last_signature = None
    
    def on_language_clicked(self, language: str, files: List[str]):
        """Handle language card click - navigate to typing tab."""
        parent_window = self.window()
        if hasattr(parent_window, 'open_typing_tab_for_language'):
            parent_window.open_typing_tab_for_language(language, files)
