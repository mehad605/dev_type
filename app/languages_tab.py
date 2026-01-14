"""Languages tab widget for displaying language-grouped files."""
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QFrame,
    QGridLayout,
)
from PySide6.QtCore import Qt, Signal, QObject, QRunnable, QThreadPool
from PySide6.QtGui import QFont
from typing import Callable, Dict, List, Optional, Tuple
from app import settings, stats_db
from app.language_cache import build_signature, load_cached_snapshot, save_snapshot
from app.ui_icons import get_pixmap, get_icon

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
    progress = Signal(int)  # file count found so far


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
            # Emit final count
            total_files = sum(len(files) for files in result.values())
            self.signals.progress.emit(total_files)
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
        self.setObjectName("LanguageCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setFixedSize(220, 200)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(10)

        # Language icon - try to get from icon manager
        self.icon_manager = _get_icon_manager()
        # self.icon_manager.icon_downloaded.connect(self._on_icon_ready) # Removed: Icons are local now
        
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self._update_icon()
        
        layout.addWidget(self.icon_label)
        
        # Language name
        name_label = QLabel(language)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("font-weight: 600; font-size: 16px; margin-top: 6px;")
        layout.addWidget(name_label)

        # File count - simple text
        completed = max(0, completed_count)
        total = len(files)
        if total > 0:
            progress_pct = int((completed / total) * 100)
            count_text = f"{completed}/{total} files • {progress_pct}% complete"
        else:
            count_text = f"{total} files"
        
        count_label = QLabel(count_text)
        count_label.setAlignment(Qt.AlignCenter)
        count_label.setStyleSheet("color: gray; font-size: 12px; margin-top: 2px;")
        layout.addWidget(count_label)

        # Avg WPM
        self.wpm_label = QLabel()
        self.wpm_label.setAlignment(Qt.AlignCenter)
        self._set_wpm_display(average_wpm, sample_size)
        layout.addWidget(self.wpm_label)
        
        layout.addStretch()
        
        # Store original style for click feedback
        self._pressed = False
        
    def _update_icon(self):
        icon_pixmap = self.icon_manager.get_icon(self.language, size=56)
        if icon_pixmap:
            # Use downloaded icon
            self.icon_label.setPixmap(icon_pixmap)
            self.icon_label.setToolTip("")
        else:
            # Fallback to local SVG icon
            # Use 'CODE' icon for languages without a devicon
            self.icon_label.setPixmap(get_pixmap("CODE", size=56))
            self.icon_label.setToolTip("")
            self.icon_label.setText("") # Clear any text
            
            # Show tooltip if download failed
            error = self.icon_manager.get_download_error(self.language)
            if error:
                self.icon_label.setToolTip(f"Icon unavailable: {error}")

    def _on_icon_ready(self, language: str):
        """Slot called when an icon is downloaded."""
        if language == self.language:
            self._update_icon()
    
    def mousePressEvent(self, event):
        """Handle card click with visual feedback."""
        if event.button() == Qt.LeftButton:
            self._pressed = True
            # Visual feedback: slightly darken the card
            self.setStyleSheet(self.styleSheet() + """
                QFrame#LanguageCard { 
                    background-color: rgba(0, 0, 0, 0.15); 
                }
            """)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Reset visual feedback and emit click signal."""
        if event.button() == Qt.LeftButton and self._pressed:
            self._pressed = False
            # Reset style (theme will reapply on next update)
            self.setStyleSheet("")
            self.clicked.emit(self.language, self.files)
        super().mouseReleaseEvent(event)

    def _set_wpm_display(self, average_wpm: Optional[float], sample_size: int):
        """Update the WPM label contents and styling."""
        from app.themes import get_color_scheme
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)
        
        if average_wpm is None or sample_size == 0:
            self.wpm_label.setText("No sessions yet")
            self.wpm_label.setStyleSheet(f"color: {scheme.text_secondary}; font-size: 11px; font-style: italic;")
        else:
            self.wpm_label.setText(f"{average_wpm:.0f} WPM avg")
            self.wpm_label.setStyleSheet(f"color: {scheme.cursor_color}; font-size: 12px; font-weight: 600;")

    def apply_theme(self):
        """Apply current theme colors to the card."""
        from app.themes import get_color_scheme
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)
        
        # Base card style is mostly handled by global stylesheet via QFrame#LanguageCard
        # but we need to update internal labels if they have custom colors
        
        # Name label
        layout = self.layout()
        if layout and layout.count() >= 3:
            name_label = layout.itemAt(2).widget()
            if isinstance(name_label, QLabel):
                name_label.setStyleSheet(f"font-weight: 600; font-size: 16px; margin-top: 6px; color: {scheme.text_primary};")
            
            count_label = layout.itemAt(3).widget()
            if isinstance(count_label, QLabel):
                count_label.setStyleSheet(f"color: {scheme.text_secondary}; font-size: 12px; margin-top: 2px;")
                
            # WPM label is already updated via _set_wpm_display if we call it
            # But we need to refresh icons too
            self._update_icon()
            
            # Extract current stats and re-apply styling
            # (In a real app, storing these as attributes is cleaner, but let's try to infer or re-call)
            # Actually, _set_wpm_display uses local vars. Let's just update styles.
            self.wpm_label.setStyleSheet(f"color: {scheme.cursor_color}; font-size: 12px; font-weight: 600;")
            if "No sessions" in self.wpm_label.text():
                 self.wpm_label.setStyleSheet(f"color: {scheme.text_secondary}; font-size: 11px; font-style: italic;")


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
        
        # Header section
        header_container = QHBoxLayout()
        header_container.setContentsMargins(20, 16, 20, 12)
        
        from app.themes import get_color_scheme
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)
        
        self.header_label = QLabel("Languages")
        header_font = QFont()
        header_font.setPointSize(20)
        header_font.setWeight(QFont.Bold)
        self.header_label.setFont(header_font)
        self.header_label.setStyleSheet(f"color: {scheme.text_primary};")
        header_container.addWidget(self.header_label)
        
        header_container.addStretch()
        
        # Subtitle
        self.subtitle_label = QLabel("Click a language to start typing")
        self.subtitle_label.setStyleSheet(f"color: {scheme.text_secondary}; font-size: 13px; padding-top: 6px;")
        header_container.addWidget(self.subtitle_label)
        
        self.layout.addLayout(header_container)
        
        # Scroll area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        # Container for cards
        self.card_container = QWidget()
        self.card_container.setStyleSheet("background: transparent;")
        self.card_layout = QGridLayout(self.card_container)
        self.card_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.card_layout.setSpacing(16)
        self.card_layout.setContentsMargins(20, 20, 20, 20)
        scroll.setWidget(self.card_container)
        
        self.layout.addWidget(scroll)

        # Initial loading state from cache
        if self._cached_language_files:
            self._populate_cards(self._cached_language_files)
            # We don't mark as _loaded=True here yet because we still want to verify 
            # with ensure_loaded(), but at least the UI is not empty.
        else:
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
        self._language_cards = {} # Clear references to doomed widgets

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
        
        # Batch fetch WPM averages for all languages at once
        all_langs = list(language_files.keys())
        bulk_averages = stats_db.get_bulk_recent_wpm_averages(all_langs, limit_per_lang=10)
        
        # Store card references for later updates
        self._language_cards: Dict[str, LanguageCard] = {}

        for lang, files in sorted(language_files.items()):
            recent = bulk_averages.get(lang)
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
            self._language_cards[lang] = card

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
        self._show_message("Scanning folders… (0 files found)")

        scanner = _get_folder_scanner()
        task = _LanguageScanTask(snapshot, scanner)
        task.signals.completed.connect(self._on_scan_finished)
        task.signals.progress.connect(self._on_scan_progress)
        self._active_task = task
        self._thread_pool.start(task)
    
    def _on_scan_progress(self, file_count: int):
        """Update scanning message with current file count."""
        if self._status_label and self._loading:
            self._status_label.setText(f"Scanning folders… ({file_count} files found)")

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
    
    def refresh_language_stats(self, file_path: Optional[str] = None):
        """Refresh stats for language cards after a session completes.
        
        Args:
            file_path: Optional path to determine which language to refresh.
                       If None, refreshes all cards.
        """
        if not hasattr(self, '_language_cards'):
            return
        
        # Determine which language the file belongs to
        target_language = None
        if file_path:
            for lang, files in self._cached_language_files.items():
                if file_path in files:
                    target_language = lang
                    break
        
        # Refresh relevant cards
        for lang, card in self._language_cards.items():
            if target_language and lang != target_language:
                continue
            
            files = self._cached_language_files.get(lang, [])
            if not files:
                continue
            
            # Recalculate stats
            stats_map = stats_db.get_file_stats_for_files(files)
            recent = stats_db.get_recent_wpm_average(files, limit=10)
            avg_wpm = recent.get("average") if recent else None
            sample_size = recent.get("count", 0) if recent else 0
            completed_count = sum(
                1 for path in files if stats_map.get(path, {}).get("completed")
            )
            
            # Update card display
            card._set_wpm_display(avg_wpm, sample_size)
            
            # Update file count label (find and update the count label)
            total = len(files)
            if total > 0:
                progress_pct = int((completed_count / total) * 100)
                count_text = f"{completed_count}/{total} files • {progress_pct}% complete"
            else:
                count_text = f"{total} files"
            
            # Find the count label (third label in the layout)
            layout = card.layout()
            if layout and layout.count() >= 4:
                count_label = layout.itemAt(3).widget()
                if isinstance(count_label, QLabel):
                    count_label.setText(count_text)

    def apply_theme(self):
        """Apply current theme to LanguagesTab and all its children."""
        from app.themes import get_color_scheme
        scheme_name = settings.get_setting("dark_scheme", settings.get_default("dark_scheme"))
        scheme = get_color_scheme("dark", scheme_name)
        
        # Update header labels
        if hasattr(self, 'header_label'):
            self.header_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {scheme.text_primary};")
        if hasattr(self, 'subtitle_label'):
            self.subtitle_label.setStyleSheet(f"color: {scheme.text_secondary}; font-size: 13px; padding-top: 6px;")
        
        # Update cards
        if hasattr(self, '_language_cards'):
            for card in self._language_cards.values():
                card.apply_theme()
