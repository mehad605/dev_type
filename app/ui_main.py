from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QStackedLayout,
    QSizePolicy,
    QFileDialog,
    QLabel,
    QToolBar,
    QStackedWidget,
    QTabWidget,
    QCheckBox,
    QMessageBox,
    QComboBox,
    QGroupBox,
    QFormLayout,
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Signal, QObject, QSize
import sys
from pathlib import Path
from typing import Optional
import app.settings as settings
from app.languages_tab import LanguagesTab
from app.history_tab import HistoryTab
from app.editor_tab import EditorTab


class FolderCardWidget(QFrame):
    """Stylized folder row used within the folders list."""

    BADGE_STYLE = (
        "background-color: #bf616a; color: white; padding: 2px 10px;"
        "border-radius: 10px; font-size: 10px; text-transform: uppercase;"
    )

    def __init__(self, folder_path: str, parent=None):
        super().__init__(parent)
        self.setObjectName("folderCard")
        self.folder_path = folder_path
        self._list_widget: Optional[QListWidget] = None
        self._list_item: Optional[QListWidgetItem] = None
        self._selected = False
        self._remove_mode = False
        self._compact = False

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.stack = QStackedLayout()
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.stack)

        # Detail layout
        self.detail_widget = QWidget()
        detail_layout = QHBoxLayout(self.detail_widget)
        detail_layout.setContentsMargins(16, 12, 16, 12)
        detail_layout.setSpacing(12)

        self.detail_icon = QLabel("📁")
        self.detail_icon.setObjectName("folderIcon")
        self.detail_icon.setStyleSheet("font-size: 22px;")
        detail_layout.addWidget(self.detail_icon)

        detail_text = QVBoxLayout()
        detail_text.setContentsMargins(0, 0, 0, 0)
        detail_text.setSpacing(2)
        self.detail_name = QLabel(Path(folder_path).name or folder_path)
        self.detail_name.setObjectName("folderName")
        self.detail_info = QLabel(folder_path)
        self.detail_info.setObjectName("folderPath")
        self.detail_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        detail_text.addWidget(self.detail_name)
        detail_text.addWidget(self.detail_info)
        detail_layout.addLayout(detail_text, stretch=1)

        self.detail_remove = QLabel("Remove")
        self.detail_remove.setObjectName("removeBadgeDetail")
        self.detail_remove.setStyleSheet(self.BADGE_STYLE)
        self.detail_remove.setVisible(False)
        detail_layout.addWidget(self.detail_remove, alignment=Qt.AlignRight | Qt.AlignTop)

        self.stack.addWidget(self.detail_widget)

        # Compact layout
        self.compact_widget = QWidget()
        compact_layout = QVBoxLayout(self.compact_widget)
        compact_layout.setContentsMargins(16, 16, 16, 16)
        compact_layout.setSpacing(6)
        compact_layout.setAlignment(Qt.AlignCenter)

        self.compact_icon = QLabel("📁")
        self.compact_icon.setObjectName("compactFolderIcon")
        self.compact_icon.setStyleSheet("font-size: 28px;")
        compact_layout.addWidget(self.compact_icon, alignment=Qt.AlignHCenter)

        self.compact_name = QLabel(Path(folder_path).name or folder_path)
        self.compact_name.setObjectName("compactFolderName")
        self.compact_name.setAlignment(Qt.AlignCenter)
        compact_layout.addWidget(self.compact_name)

        self.compact_remove = QLabel("Remove")
        self.compact_remove.setObjectName("removeBadgeCompact")
        self.compact_remove.setStyleSheet(self.BADGE_STYLE)
        self.compact_remove.setVisible(False)
        compact_layout.addWidget(self.compact_remove, alignment=Qt.AlignHCenter)

        self.stack.addWidget(self.compact_widget)

        self._apply_style()

    def sizeHint(self):  # noqa: D401 - simple override for predictable sizing
        """Return preferred size depending on active layout."""
        if self._compact:
            return QSize(200, 150)
        return QSize(360, 76)

    def attach(self, list_widget: QListWidget, list_item: QListWidgetItem):
        self._list_widget = list_widget
        self._list_item = list_item

    def set_selected(self, selected: bool):
        self._selected = selected
        self._apply_style()

    def set_remove_mode(self, enabled: bool):
        self._remove_mode = enabled
        self.detail_remove.setVisible(enabled)
        self.compact_remove.setVisible(enabled)
        self._apply_style()

    def set_compact(self, compact: bool):
        if self._compact == compact:
            return
        self._compact = compact
        if compact:
            self.stack.setCurrentWidget(self.compact_widget)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            hint = self.sizeHint()
            self.setMinimumSize(hint)
            self.setMaximumSize(hint)
        else:
            self.stack.setCurrentWidget(self.detail_widget)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            detail_height = self.sizeHint().height()
            self.setMinimumHeight(detail_height)
            self.setMaximumHeight(detail_height)
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
            self.setMaximumSize(QSize(16777215, detail_height))
        self.updateGeometry()
        self._apply_style()

    def _apply_style(self):
        base_color = "rgba(236, 239, 244, 0.05)"
        border_color = "rgba(236, 239, 244, 0.10)"
        if self._selected:
            base_color = "rgba(129, 161, 193, 0.20)"
            border_color = "#81a1c1"
        if self._remove_mode:
            border_color = "#bf616a"

        self.setStyleSheet(
            f"QFrame#folderCard {{"
            f"background-color: {base_color};"
            f"border: 1px solid {border_color};"
            "border-radius: 12px;"
            "}"
            "QFrame#folderCard:hover { border-color: #88c0d0; }"
            "QLabel#folderName, QLabel#compactFolderName { color: #eceff4; font-weight: 600; }"
            "QLabel#folderPath { color: #a5abb6; font-size: 11px; }"
        )

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton and self._list_widget and self._list_item:
            self._list_widget.setCurrentItem(self._list_item)
            self._list_widget.itemClicked.emit(self._list_item)

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        if event.button() == Qt.LeftButton and self._list_widget and self._list_item:
            self._list_widget.setCurrentItem(self._list_item)
            self._list_widget.itemDoubleClicked.emit(self._list_item)


class FoldersTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        settings.init_db()
        self.s = None
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(12)
        self.layout.setContentsMargins(16, 16, 16, 16)

        # Modern header section
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(8)
        header_layout.setContentsMargins(0, 0, 0, 12)
        
        title_label = QLabel("📁 Code Folders")
        title_label.setStyleSheet("font-size: 18pt; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        desc_label = QLabel("Add folders containing code files you want to practice typing.")
        desc_label.setStyleSheet("color: #888888; font-size: 10pt;")
        header_layout.addWidget(desc_label)
        
        self.layout.addWidget(header)

        # Modern toolbar with styled buttons
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        
        self.add_btn = QPushButton("➕ Add Folder")
        self.add_btn.setToolTip("Add a new folder")
        self.add_btn.setMinimumHeight(36)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #5e81ac;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #81a1c1;
            }
            QPushButton:pressed {
                background-color: #4c566a;
            }
        """)
        
        self.edit_btn = QPushButton("✏️ Remove Mode")
        self.edit_btn.setCheckable(True)
        self.edit_btn.setMinimumHeight(36)
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #bf616a;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #d08770;
            }
            QPushButton:pressed {
                background-color: #a54c56;
            }
            QPushButton:checked {
                background-color: #d08770;
            }
        """)
        
        self.view_toggle = QPushButton("📋 Detail View")
        self.view_toggle.setCheckable(True)
        self.view_toggle.setMinimumHeight(36)
        self.view_toggle.setStyleSheet("""
            QPushButton {
                background-color: #4c566a;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #5e81ac;
            }
        """)
        
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.view_toggle)
        toolbar.addStretch()

        self.layout.addLayout(toolbar)

        # Styled list widget
        self.list = QListWidget()
        self.list.setFrameShape(QFrame.NoFrame)
        self.list.setSpacing(12)
        self.list.setSelectionMode(QListWidget.SingleSelection)
        self.list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                padding: 4px 0;
            }
            QListWidget::item {
                margin: 0;
                padding: 0;
            }
            QListWidget::item:selected {
                background: transparent;
            }
        """)
        self.layout.addWidget(self.list)

        self.add_btn.clicked.connect(self.on_add)
        self.edit_btn.toggled.connect(self.on_edit_toggled)
        self.view_toggle.toggled.connect(self.on_view_toggled)
        self.list.itemDoubleClicked.connect(self.on_folder_double_clicked)
        self.list.itemSelectionChanged.connect(self._update_folder_selection_state)

        self.load_folders()

    def on_folder_double_clicked(self, item: QListWidgetItem):
        """Navigate to typing tab when folder is double-clicked."""
        if self.edit_btn.isChecked():
            return  # Don't navigate in edit mode
        folder_path = item.data(Qt.UserRole)
        # Signal parent window to switch to typing tab with this folder
        parent_window = self.window()
        if hasattr(parent_window, 'open_typing_tab'):
            parent_window.open_typing_tab(folder_path)

    def load_folders(self):
        self.list.clear()
        folders = settings.get_folders()
        for path_str in folders:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, path_str)
            item.setText(path_str)
            card = FolderCardWidget(path_str)
            card.attach(self.list, item)
            card.set_compact(self.view_toggle.isChecked())
            item.setSizeHint(card.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, card)

        self._update_folder_selection_state()
        self._set_remove_mode_for_cards(self.edit_btn.isChecked())
        self._apply_view_mode_styles()

    def on_add(self):
        dlg = QFileDialog(self, "Select folder to add")
        dlg.setFileMode(QFileDialog.Directory)
        dlg.setOption(QFileDialog.ShowDirsOnly, True)
        if dlg.exec():
            selected = dlg.selectedFiles()
            for p in selected:
                settings.add_folder(p)
        # reload
        self.load_folders()
        # Notify parent to refresh languages tab
        parent_window = self.window()
        if hasattr(parent_window, 'refresh_languages_tab'):
            parent_window.refresh_languages_tab()

    def on_edit_toggled(self, checked: bool):
        """Toggle remove mode for folders."""
        if checked:
            self.edit_btn.setText("✅ Done")
            # Connect click handler for removal (only if not already connected)
            self.list.itemClicked.connect(self._maybe_remove_item)
            self._set_remove_mode_for_cards(True)
        else:
            self.edit_btn.setText("✏️ Remove Mode")
            # Disconnect click handler
            try:
                self.list.itemClicked.disconnect(self._maybe_remove_item)
            except (RuntimeError, TypeError):
                # Already disconnected or never connected
                pass
            self._set_remove_mode_for_cards(False)
            self._update_folder_selection_state()

    def _maybe_remove_item(self, item: QListWidgetItem):
        """Handle folder removal with optional confirmation."""
        if not self.edit_btn.isChecked():
            return
        
        p = item.data(Qt.UserRole)
        delete_confirm = settings.get_setting("delete_confirm", "1")
        should_confirm = (delete_confirm == "1")
        
        should_remove = True
        if should_confirm:
            mb = QMessageBox(self)
            mb.setWindowTitle("Confirm Removal")
            mb.setText(f"Remove folder from list?\n\n{p}")
            mb.setIcon(QMessageBox.Question)
            mb.setInformativeText("This will not delete the folder from your computer, only remove it from the app.")
            
            # Add "Don't ask again" checkbox
            cb = QCheckBox("Don't ask me again")
            mb.setCheckBox(cb)
            mb.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            mb.setDefaultButton(QMessageBox.No)
            
            result = mb.exec()
            
            if result == QMessageBox.Yes:
                # If "don't ask again" was checked, save the setting
                if cb.isChecked():
                    settings.set_setting("delete_confirm", "0")
                should_remove = True
            else:
                should_remove = False
        
        if should_remove:
            # Remove the folder
            settings.remove_folder(p)
            
            # Immediately update the UI
            self.load_folders()
            if self.edit_btn.isChecked():
                self._set_remove_mode_for_cards(True)
            
            # Notify parent to refresh languages tab
            parent_window = self.window()
            if hasattr(parent_window, 'refresh_languages_tab'):
                parent_window.refresh_languages_tab()

    def on_view_toggled(self, checked: bool):
        """Toggle between list and icon view modes."""
        if checked:
            self.view_toggle.setText("🔲 Icon View")
            self.list.setViewMode(QListWidget.ViewMode.IconMode)
        else:
            self.view_toggle.setText("📋 Detail View")
            self.list.setViewMode(QListWidget.ViewMode.ListMode)
        self._apply_view_mode_to_cards(checked)
        self._apply_view_mode_styles()

    def _update_folder_selection_state(self):
        for i in range(self.list.count()):
            item = self.list.item(i)
            widget = self.list.itemWidget(item)
            if isinstance(widget, FolderCardWidget):
                widget.set_selected(item.isSelected())

    def _set_remove_mode_for_cards(self, enabled: bool):
        for i in range(self.list.count()):
            widget = self.list.itemWidget(self.list.item(i))
            if isinstance(widget, FolderCardWidget):
                widget.set_remove_mode(enabled)

    def _apply_view_mode_to_cards(self, compact: bool):
        for i in range(self.list.count()):
            item = self.list.item(i)
            widget = self.list.itemWidget(item)
            if isinstance(widget, FolderCardWidget):
                widget.set_compact(compact)
                item.setSizeHint(widget.sizeHint())

    def _apply_view_mode_styles(self):
        compact = self.view_toggle.isChecked()
        if compact:
            self.list.setSpacing(16)
            self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.list.setResizeMode(QListWidget.Adjust)
            self.list.setWrapping(True)
            self.list.setFlow(QListWidget.LeftToRight)
            self.list.setUniformItemSizes(True)
            card_size = self._first_card_size()
            if card_size:
                self.list.setGridSize(QSize(card_size.width() + 20, card_size.height() + 20))
        else:
            self.list.setSpacing(8)
            self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.list.setWrapping(False)
            self.list.setFlow(QListWidget.TopToBottom)
            self.list.setUniformItemSizes(False)
            self.list.setGridSize(QSize())
        # minimize the native list highlight to let cards show their own focus
        self.list.setStyleSheet(
            "QListWidget::item { margin: 0; padding: 0; }"
            "QListWidget::item:selected { background-color: transparent; }"
        )

    def _first_card_size(self) -> Optional[QSize]:
        if not self.list.count():
            return None
        widget = self.list.itemWidget(self.list.item(0))
        if isinstance(widget, FolderCardWidget):
            return widget.sizeHint()
        else:
            return None


class MainWindow(QMainWindow):
    # Signals for dynamic settings updates
    font_changed = Signal(str, int, bool)  # family, size, ligatures
    colors_changed = Signal()
    cursor_changed = Signal(str, str)  # type, style
    space_char_changed = Signal(str)
    pause_delay_changed = Signal(float)
    allow_continue_changed = Signal(bool)
    show_typed_changed = Signal(bool)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dev Typing App")
        self.resize(900, 600)
        self.tabs = QTabWidget()
        self.folders_tab = FoldersTab()
        self.tabs.addTab(self.folders_tab, "Folders")
        
        # Languages tab
        self.languages_tab = LanguagesTab()
        self.tabs.addTab(self.languages_tab, "Languages")

        # History tab
        self.history_tab = HistoryTab()
        self.tabs.addTab(self.history_tab, "History")
        
        # Editor/Typing tab
        self.editor_tab = EditorTab()
        self.tabs.addTab(self.editor_tab, "Typing")

        # Settings tab
        settings.init_db()
        self.settings_tab = self._create_settings_tab()
        self.tabs.addTab(self.settings_tab, "Settings")

        self.setCentralWidget(self.tabs)
        self._last_tab_index = self.tabs.currentIndex()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        # Apply initial theme
        self.apply_current_theme()
        
        # Connect settings signals to editor tab for dynamic updates
        self._connect_settings_signals()
        
        # Emit initial settings to apply them to the typing area
        self._emit_initial_settings()

    def _on_tab_changed(self, index: int):
        """Persist typing progress whenever we leave the typing tab."""
        typing_index = self.tabs.indexOf(self.editor_tab)
        if typing_index != -1 and self._last_tab_index == typing_index and index != typing_index:
            self.editor_tab.save_active_progress()
        self._last_tab_index = index

    def closeEvent(self, event):
        """Ensure active typing progress is saved before exit."""
        if hasattr(self, "editor_tab"):
            self.editor_tab.save_active_progress()
        super().closeEvent(event)

    def _create_settings_tab(self) -> QWidget:
        """Create and return the settings tab widget."""
        from PySide6.QtWidgets import QScrollArea, QSlider, QSpinBox, QLineEdit, QColorDialog
        from PySide6.QtCore import QSize
        
        # Main scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        settings_widget = QWidget()
        s_layout = QVBoxLayout(settings_widget)
        
        # Typing Behavior settings group
        typing_behavior_group = QGroupBox("Typing Behavior")
        typing_behavior_layout = QVBoxLayout()
        
        lenient_label = QLabel("Lenient Mode")
        lenient_label.setStyleSheet("font-weight: bold;")
        typing_behavior_layout.addWidget(lenient_label)

        description = QLabel(
            "In lenient mode you can continue typing without fixing your mistypes."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #888888; font-size: 10pt;")
        typing_behavior_layout.addWidget(description)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self.allow_continue_enabled_btn = QPushButton("Enabled")
        self.allow_continue_disabled_btn = QPushButton("Disabled")
        for btn in (self.allow_continue_enabled_btn, self.allow_continue_disabled_btn):
            btn.setCheckable(True)
            btn.setMinimumHeight(34)
            btn.setCursor(Qt.PointingHandCursor)

        self.allow_continue_enabled_btn.clicked.connect(lambda: self._handle_allow_continue_button(True))
        self.allow_continue_disabled_btn.clicked.connect(lambda: self._handle_allow_continue_button(False))

        button_row.addWidget(self.allow_continue_enabled_btn)
        button_row.addWidget(self.allow_continue_disabled_btn)
        button_row.addStretch()
        typing_behavior_layout.addLayout(button_row)

        allow_continue = settings.get_setting("allow_continue_mistakes", "0") == "1"
        self._update_allow_continue_buttons(allow_continue)

        # Show typed characters option
        show_typed_label = QLabel("Show what you type")
        show_typed_label.setStyleSheet("font-weight: bold;")
        typing_behavior_layout.addWidget(show_typed_label)

        show_typed_description = QLabel(
            "Display the characters you actually type instead of the reference text when mistakes happen."
        )
        show_typed_description.setWordWrap(True)
        show_typed_description.setStyleSheet("color: #888888; font-size: 9pt;")
        typing_behavior_layout.addWidget(show_typed_description)

        show_button_row = QHBoxLayout()
        show_button_row.setSpacing(8)

        self.show_typed_enabled_btn = QPushButton("Enabled")
        self.show_typed_disabled_btn = QPushButton("Disabled")
        for btn in (self.show_typed_enabled_btn, self.show_typed_disabled_btn):
            btn.setCheckable(True)
            btn.setMinimumHeight(34)
            btn.setCursor(Qt.PointingHandCursor)

        self.show_typed_enabled_btn.clicked.connect(lambda: self._handle_show_typed_button(True))
        self.show_typed_disabled_btn.clicked.connect(lambda: self._handle_show_typed_button(False))

        show_button_row.addWidget(self.show_typed_enabled_btn)
        show_button_row.addWidget(self.show_typed_disabled_btn)
        show_button_row.addStretch()
        typing_behavior_layout.addLayout(show_button_row)

        show_typed = settings.get_setting("show_typed_characters", "0") == "1"
        self._update_show_typed_buttons(show_typed)
        
        typing_behavior_group.setLayout(typing_behavior_layout)
        s_layout.addWidget(typing_behavior_group)
        
        # Theme settings group
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        cur_theme = settings.get_setting("theme", "dark")
        self.theme_combo.setCurrentText(cur_theme)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        theme_layout.addRow("Theme:", self.theme_combo)
        
        self.scheme_combo = QComboBox()
        self.scheme_combo.addItems(["nord", "catppuccin", "dracula"])
        cur_scheme = settings.get_setting("dark_scheme", "nord")
        self.scheme_combo.setCurrentText(cur_scheme)
        self.scheme_combo.currentTextChanged.connect(self.on_scheme_changed)
        theme_layout.addRow("Dark scheme:", self.scheme_combo)
        
        theme_group.setLayout(theme_layout)
        s_layout.addWidget(theme_group)
        
        # Color settings group
        colors_group = QGroupBox("Colors")
        colors_layout = QFormLayout()
        
        # Helper function to create color button
        def create_color_button(setting_key: str, default: str, label: str):
            color_val = settings.get_setting(setting_key, default)
            btn = QPushButton()
            btn.setFixedSize(80, 30)
            btn.setStyleSheet(f"background-color: {color_val}; border: 1px solid #666;")
            btn.clicked.connect(lambda: self.on_color_pick(setting_key, btn, label))
            
            row_layout = QHBoxLayout()
            row_layout.addWidget(btn)
            reset_btn = QPushButton("Reset")
            reset_btn.clicked.connect(lambda: self.on_color_reset(setting_key, default, btn))
            row_layout.addWidget(reset_btn)
            row_layout.addStretch()
            
            colors_layout.addRow(f"{label}:", row_layout)
            return btn
        
        self.color_untyped_btn = create_color_button("color_untyped", "#555555", "Untyped text")
        self.color_correct_btn = create_color_button("color_correct", "#00ff00", "Correct text")
        self.color_incorrect_btn = create_color_button("color_incorrect", "#ff0000", "Incorrect text")
        self.color_paused_btn = create_color_button("color_paused_highlight", "#ffaa00", "Paused files")
        self.color_cursor_btn = create_color_button("color_cursor", "#ffffff", "Cursor")
        
        colors_group.setLayout(colors_layout)
        s_layout.addWidget(colors_group)
        
        # Cursor settings group
        cursor_group = QGroupBox("Cursor")
        cursor_layout = QFormLayout()
        
        self.cursor_type_combo = QComboBox()
        self.cursor_type_combo.addItems(["blinking", "static"])
        cursor_type = settings.get_setting("cursor_type", "blinking")
        self.cursor_type_combo.setCurrentText(cursor_type)
        self.cursor_type_combo.currentTextChanged.connect(self.on_cursor_type_changed)
        cursor_layout.addRow("Type:", self.cursor_type_combo)
        
        self.cursor_style_combo = QComboBox()
        self.cursor_style_combo.addItems(["block", "underscore", "ibeam"])
        cursor_style = settings.get_setting("cursor_style", "block")
        self.cursor_style_combo.setCurrentText(cursor_style)
        self.cursor_style_combo.currentTextChanged.connect(self.on_cursor_style_changed)
        cursor_layout.addRow("Style:", self.cursor_style_combo)
        
        cursor_group.setLayout(cursor_layout)
        s_layout.addWidget(cursor_group)
        
        # Font settings group
        font_group = QGroupBox("Font")
        font_layout = QFormLayout()
        
        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems([
            "Consolas", "Courier New", "Monaco", "Menlo", 
            "DejaVu Sans Mono", "Liberation Mono", "Fira Code",
            "JetBrains Mono", "Source Code Pro"
        ])
        font_family = settings.get_setting("font_family", "Consolas")
        self.font_family_combo.setCurrentText(font_family)
        self.font_family_combo.currentTextChanged.connect(self.on_font_family_changed)
        font_layout.addRow("Family:", self.font_family_combo)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 32)
        font_size = int(settings.get_setting("font_size", "12"))
        self.font_size_spin.setValue(font_size)
        self.font_size_spin.valueChanged.connect(self.on_font_size_changed)
        font_layout.addRow("Size:", self.font_size_spin)
        
        self.font_ligatures_cb = QCheckBox("Enable font ligatures")
        ligatures = settings.get_setting("font_ligatures", "0")
        self.font_ligatures_cb.setChecked(ligatures == "1")
        self.font_ligatures_cb.stateChanged.connect(self.on_font_ligatures_changed)
        font_layout.addRow("", self.font_ligatures_cb)
        
        font_group.setLayout(font_layout)
        s_layout.addWidget(font_group)
        
        # Typing settings group
        typing_group = QGroupBox("Typing")
        typing_layout = QFormLayout()
        
        # Space character
        self.space_char_combo = QComboBox()
        self.space_char_combo.addItems(["␣", "·", " ", "custom"])
        space_char = settings.get_setting("space_char", "␣")
        if space_char in ["␣", "·", " "]:
            self.space_char_combo.setCurrentText(space_char)
        else:
            self.space_char_combo.setCurrentText("custom")
        
        self.space_char_custom = QLineEdit()
        self.space_char_custom.setMaxLength(1)
        self.space_char_custom.setText(space_char if space_char not in ["␣", "·", " "] else "")
        self.space_char_custom.setEnabled(self.space_char_combo.currentText() == "custom")
        
        self.space_char_combo.currentTextChanged.connect(self.on_space_char_changed)
        self.space_char_custom.textChanged.connect(self.on_space_char_custom_changed)
        
        space_layout = QHBoxLayout()
        space_layout.addWidget(self.space_char_combo)
        space_layout.addWidget(QLabel("Custom:"))
        space_layout.addWidget(self.space_char_custom)
        typing_layout.addRow("Space char:", space_layout)
        
        # Pause delay
        self.pause_delay_spin = QSpinBox()
        self.pause_delay_spin.setRange(1, 60)
        self.pause_delay_spin.setSuffix(" seconds")
        pause_delay = int(float(settings.get_setting("pause_delay", "7")))
        self.pause_delay_spin.setValue(pause_delay)

        best_wpm_min = settings.get_setting("best_wpm_min_accuracy", "0.9")
        try:
            best_wpm_percent = int(round(float(best_wpm_min) * 100)) if best_wpm_min is not None else 90
        except (TypeError, ValueError):
            best_wpm_percent = 90
        if hasattr(self, "best_wpm_accuracy_spin"):
            self.best_wpm_accuracy_spin.setValue(best_wpm_percent)
        self.pause_delay_spin.valueChanged.connect(self.on_pause_delay_changed)
        typing_layout.addRow("Auto-pause delay:", self.pause_delay_spin)

        # Best WPM accuracy threshold
        self.best_wpm_accuracy_spin = QSpinBox()
        self.best_wpm_accuracy_spin.setRange(0, 100)
        self.best_wpm_accuracy_spin.setSuffix(" %")
        try:
            best_wpm_acc_raw = settings.get_setting("best_wpm_min_accuracy", "0.9")
            best_wpm_percent = int(round(float(best_wpm_acc_raw) * 100)) if best_wpm_acc_raw is not None else 90
        except (TypeError, ValueError):
            best_wpm_percent = 90
        self.best_wpm_accuracy_spin.setValue(best_wpm_percent)
        self.best_wpm_accuracy_spin.valueChanged.connect(self.on_best_wpm_accuracy_changed)
        typing_layout.addRow("Best WPM min accuracy:", self.best_wpm_accuracy_spin)
        
        typing_group.setLayout(typing_layout)
        s_layout.addWidget(typing_group)
        
        # Import/Export group
        import_export_group = QGroupBox("Backup & Restore")
        import_export_layout = QVBoxLayout()
        
        export_settings_btn = QPushButton("Export Settings as JSON")
        export_settings_btn.clicked.connect(self.on_export_settings)
        import_export_layout.addWidget(export_settings_btn)
        
        import_settings_btn = QPushButton("Import Settings from JSON")
        import_settings_btn.clicked.connect(self.on_import_settings)
        import_export_layout.addWidget(import_settings_btn)
        
        export_data_btn = QPushButton("Export Data (Stats & Progress)")
        export_data_btn.clicked.connect(self.on_export_data)
        import_export_layout.addWidget(export_data_btn)
        
        import_data_btn = QPushButton("Import Data")
        import_data_btn.clicked.connect(self.on_import_data)
        import_export_layout.addWidget(import_data_btn)
        
        import_export_group.setLayout(import_export_layout)
        s_layout.addWidget(import_export_group)
        
        s_layout.addStretch()
        
        scroll.setWidget(settings_widget)
        return scroll

    def open_typing_tab(self, folder_path: str):
        """Switch to typing tab and load the specified folder."""
        self.editor_tab.load_folder(folder_path)
        self.tabs.setCurrentWidget(self.editor_tab)

    def _update_folder_selection_state(self):
        for i in range(self.list.count()):
            item = self.list.item(i)
            widget = self.list.itemWidget(item)
            if isinstance(widget, FolderCardWidget):
                widget.set_selected(item.isSelected())

    def _set_remove_mode_for_cards(self, enabled: bool):
        for i in range(self.list.count()):
            widget = self.list.itemWidget(self.list.item(i))
            if isinstance(widget, FolderCardWidget):
                widget.set_remove_mode(enabled)
    
    def open_typing_tab_for_language(self, language: str, files: list):
        """Switch to typing tab and load files for a specific language."""
        self.editor_tab.load_language_files(language, files)
        self.tabs.setCurrentWidget(self.editor_tab)
    
    def refresh_languages_tab(self):
        """Refresh the languages tab after folders change."""
        self.languages_tab.refresh_languages()

    def refresh_history_tab(self):
        """Refresh the session history tab."""
        if hasattr(self, "history_tab"):
            self.history_tab.refresh_history()

    def on_allow_continue_changed(self, state: int):
        """Handle allow continue with mistakes setting change."""
        settings.set_setting("allow_continue_mistakes", "1" if state == Qt.Checked else "0")
        self.allow_continue_changed.emit(state == Qt.Checked)

    def on_theme_changed(self, theme: str):
        settings.set_setting("theme", theme)
        self.apply_current_theme()
        self.update_color_buttons_from_theme()

    def on_scheme_changed(self, scheme: str):
        settings.set_setting("dark_scheme", scheme)
        self.apply_current_theme()
        self.update_color_buttons_from_theme()
    
    def on_color_pick(self, setting_key: str, button: QPushButton, label: str):
        """Open color picker dialog."""
        from PySide6.QtWidgets import QColorDialog
        from PySide6.QtGui import QColor
        
        current_color = settings.get_setting(setting_key, "#ffffff")
        color = QColorDialog.getColor(QColor(current_color), self, f"Pick {label}")
        
        if color.isValid():
            color_hex = color.name()
            settings.set_setting(setting_key, color_hex)
            button.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #666;")
            self.colors_changed.emit()
    
    def on_color_reset(self, setting_key: str, default: str, button: QPushButton):
        """Reset color to default."""
        settings.set_setting(setting_key, default)
        button.setStyleSheet(f"background-color: {default}; border: 1px solid #666;")
        self.colors_changed.emit()
    
    def on_cursor_type_changed(self, cursor_type: str):
        settings.set_setting("cursor_type", cursor_type)
        cursor_style = settings.get_setting("cursor_style", "block")
        self.cursor_changed.emit(cursor_type, cursor_style)
    
    def on_cursor_style_changed(self, cursor_style: str):
        settings.set_setting("cursor_style", cursor_style)
        cursor_type = settings.get_setting("cursor_type", "blinking")
        self.cursor_changed.emit(cursor_type, cursor_style)
    
    def on_font_family_changed(self, font_family: str):
        settings.set_setting("font_family", font_family)
        self._emit_font_changed()
    
    def on_font_size_changed(self, font_size: int):
        settings.set_setting("font_size", str(font_size))
        self._emit_font_changed()
    
    def on_font_ligatures_changed(self, state: int):
        settings.set_setting("font_ligatures", "1" if state == Qt.Checked else "0")
        self._emit_font_changed()
    
    def _emit_font_changed(self):
        """Helper to emit font_changed signal with current font settings."""
        family = settings.get_setting("font_family", "Consolas")
        size = int(settings.get_setting("font_size", "12"))
        ligatures = settings.get_setting("font_ligatures", "0") == "1"
        self.font_changed.emit(family, size, ligatures)
    
    def on_space_char_changed(self, char_option: str):
        """Handle space character dropdown change."""
        if char_option != "custom":
            settings.set_setting("space_char", char_option)
            self.space_char_custom.setEnabled(False)
            self.space_char_changed.emit(char_option)
        else:
            self.space_char_custom.setEnabled(True)
            if self.space_char_custom.text():
                settings.set_setting("space_char", self.space_char_custom.text())
                self.space_char_changed.emit(self.space_char_custom.text())
    
    def on_space_char_custom_changed(self, text: str):
        """Handle custom space character input."""
        if text and self.space_char_combo.currentText() == "custom":
            settings.set_setting("space_char", text)
            self.space_char_changed.emit(text)
    
    def on_pause_delay_changed(self, delay: int):
        settings.set_setting("pause_delay", str(delay))
        self.pause_delay_changed.emit(float(delay))

    def on_best_wpm_accuracy_changed(self, percent: int):
        clamped = max(0, min(100, int(percent)))
        ratio = clamped / 100.0
        settings.set_setting("best_wpm_min_accuracy", f"{ratio:.4f}")
    
    def on_export_settings(self):
        """Export settings to JSON file."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import json
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Settings", "settings.json", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                # Get all settings
                conn = settings._connect()
                cur = conn.cursor()
                cur.execute("SELECT key, value FROM settings")
                settings_dict = {row[0]: row[1] for row in cur.fetchall()}
                conn.close()
                
                with open(file_path, 'w') as f:
                    json.dump(settings_dict, f, indent=2)
                
                QMessageBox.information(self, "Success", "Settings exported successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to export settings: {e}")
    
    def on_import_settings(self):
        """Import settings from JSON file."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import json
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Settings", "", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    settings_dict = json.load(f)
                
                # Import each setting
                for key, value in settings_dict.items():
                    settings.set_setting(key, value)
                
                # Apply settings dynamically
                self._refresh_all_settings_ui()
                self.apply_current_theme()
                self._emit_all_settings_signals()
                
                QMessageBox.information(
                    self, "Success", 
                    "Settings imported and applied successfully!"
                )
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to import settings: {e}")
    
    def on_export_data(self):
        """Export statistics and progress data to JSON."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import json
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Data", "typing_data.json", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                conn = settings._connect()
                cur = conn.cursor()
                
                # Export file stats
                cur.execute("SELECT * FROM file_stats")
                file_stats = []
                for row in cur.fetchall():
                    file_stats.append({
                        "file_path": row[0],
                        "best_wpm": row[1],
                        "last_wpm": row[2],
                        "best_accuracy": row[3],
                        "last_accuracy": row[4],
                        "times_practiced": row[5],
                        "last_practiced": row[6],
                        "completed": row[7]
                    })
                
                # Export session progress
                cur.execute("SELECT * FROM session_progress")
                sessions = []
                for row in cur.fetchall():
                    sessions.append({
                        "file_path": row[0],
                        "cursor_position": row[1],
                        "total_characters": row[2],
                        "correct_keystrokes": row[3],
                        "incorrect_keystrokes": row[4],
                        "session_time": row[5],
                        "is_paused": row[6],
                        "last_updated": row[7]
                    })
                
                conn.close()
                
                data = {
                    "file_stats": file_stats,
                    "session_progress": sessions
                }
                
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                QMessageBox.information(self, "Success", "Data exported successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to export data: {e}")
    
    def on_import_data(self):
        """Import statistics and progress data from JSON."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import json
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Data", "", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                conn = settings._connect()
                cur = conn.cursor()
                
                # Import file stats
                for stat in data.get("file_stats", []):
                    cur.execute("""
                        INSERT OR REPLACE INTO file_stats
                        (file_path, best_wpm, last_wpm, best_accuracy, last_accuracy,
                         times_practiced, last_practiced, completed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        stat["file_path"], stat["best_wpm"], stat["last_wpm"],
                        stat["best_accuracy"], stat["last_accuracy"],
                        stat["times_practiced"], stat.get("last_practiced"),
                        stat["completed"]
                    ))
                
                # Import session progress
                for session in data.get("session_progress", []):
                    cur.execute("""
                        INSERT OR REPLACE INTO session_progress
                        (file_path, cursor_position, total_characters,
                         correct_keystrokes, incorrect_keystrokes, session_time,
                         is_paused, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session["file_path"], session["cursor_position"],
                        session["total_characters"], session["correct_keystrokes"],
                        session["incorrect_keystrokes"], session["session_time"],
                        session["is_paused"], session.get("last_updated")
                    ))
                
                conn.commit()
                conn.close()
                
                # Refresh UI to show imported data
                if hasattr(self.editor_tab, 'file_tree'):
                    self.editor_tab.file_tree.refresh_tree()
                    self.editor_tab.file_tree.refresh_incomplete_sessions()
                
                self.refresh_languages_tab()
                
                QMessageBox.information(self, "Success", "Data imported and UI refreshed successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to import data: {e}")
    
    def apply_current_theme(self):
        """Apply the current theme settings to the entire application."""
        from app.themes import get_color_scheme, apply_theme_to_app
        
        # Get current theme settings
        theme = settings.get_setting("theme", "dark")
        scheme_name = settings.get_setting("dark_scheme", "nord")
        
        # Get the color scheme
        scheme = get_color_scheme(theme, scheme_name)
        
        # Apply to application
        app = QApplication.instance()
        if app:
            apply_theme_to_app(app, scheme)
        
        # Update typing area colors if editor tab is initialized
        if hasattr(self, 'editor_tab') and hasattr(self.editor_tab, 'typing_area'):
            self.update_typing_colors(scheme)
            # Update stats display theme
            if hasattr(self.editor_tab, 'stats_display'):
                self.editor_tab.stats_display.apply_theme()
    
    def update_typing_colors(self, scheme):
        """Update typing area highlighter colors from scheme."""
        typing_area = self.editor_tab.typing_area
        if typing_area.highlighter:
            from PySide6.QtGui import QColor
            
            # Update highlighter colors
            typing_area.highlighter.untyped_format.setForeground(QColor(scheme.text_untyped))
            typing_area.highlighter.correct_format.setForeground(QColor(scheme.text_correct))
            typing_area.highlighter.incorrect_format.setForeground(QColor(scheme.text_incorrect))
            
            # Trigger rehighlight to apply changes
            typing_area.highlighter.rehighlight()
    
    def update_color_buttons_from_theme(self):
        """Update color picker button displays to reflect theme colors."""
        from app.themes import get_color_scheme
        
        # Get current theme
        theme = settings.get_setting("theme", "dark")
        scheme_name = settings.get_setting("dark_scheme", "nord")
        scheme = get_color_scheme(theme, scheme_name)
        
        # Update color buttons if they exist
        if hasattr(self, 'color_untyped_btn'):
            settings.set_setting("color_untyped", scheme.text_untyped)
            self.color_untyped_btn.setStyleSheet(
                f"background-color: {scheme.text_untyped}; border: 1px solid #666;"
            )
        
        if hasattr(self, 'color_correct_btn'):
            settings.set_setting("color_correct", scheme.text_correct)
            self.color_correct_btn.setStyleSheet(
                f"background-color: {scheme.text_correct}; border: 1px solid #666;"
            )
        
        if hasattr(self, 'color_incorrect_btn'):
            settings.set_setting("color_incorrect", scheme.text_incorrect)
            self.color_incorrect_btn.setStyleSheet(
                f"background-color: {scheme.text_incorrect}; border: 1px solid #666;"
            )
        
        if hasattr(self, 'color_paused_btn'):
            settings.set_setting("color_paused_highlight", scheme.text_paused)
            self.color_paused_btn.setStyleSheet(
                f"background-color: {scheme.text_paused}; border: 1px solid #666;"
            )
        
        if hasattr(self, 'color_cursor_btn'):
            settings.set_setting("color_cursor", scheme.cursor_color)
            self.color_cursor_btn.setStyleSheet(
                f"background-color: {scheme.cursor_color}; border: 1px solid #666;"
            )
    
    def _refresh_all_settings_ui(self):
        """Refresh all settings UI controls to match imported settings."""
        # Theme settings
        theme = settings.get_setting("theme", "dark")
        self.theme_combo.setCurrentText(theme)
        
        scheme = settings.get_setting("dark_scheme", "nord")
        self.scheme_combo.setCurrentText(scheme)
        
        # Cursor settings
        cursor_type = settings.get_setting("cursor_type", "blinking")
        self.cursor_type_combo.setCurrentText(cursor_type)
        
        cursor_style = settings.get_setting("cursor_style", "block")
        self.cursor_style_combo.setCurrentText(cursor_style)
        
        # Font settings
        font_family = settings.get_setting("font_family", "Consolas")
        self.font_family_combo.setCurrentText(font_family)
        
        font_size = int(settings.get_setting("font_size", "12"))
        self.font_size_spin.setValue(font_size)
        
        ligatures = settings.get_setting("font_ligatures", "0")
        self.font_ligatures_cb.setChecked(ligatures == "1")
        
        # Typing settings
        space_char = settings.get_setting("space_char", "␣")
        if space_char in ["␣", "·", " "]:
            self.space_char_combo.setCurrentText(space_char)
        else:
            self.space_char_combo.setCurrentText("custom")
            self.space_char_custom.setText(space_char)
        
        pause_delay = int(float(settings.get_setting("pause_delay", "7")))
        self.pause_delay_spin.setValue(pause_delay)
        
        # Typing behavior
        allow_continue = settings.get_setting("allow_continue_mistakes", "0")
        self._update_allow_continue_buttons(allow_continue == "1")
        show_typed_state = settings.get_setting("show_typed_characters", "0") == "1"
        self._update_show_typed_buttons(show_typed_state)
    
    def _emit_all_settings_signals(self):
        """Emit all settings signals to update connected components."""
        # Font settings
        self._emit_font_changed()
        
        # Color settings
        self.colors_changed.emit()
        
        # Cursor settings
        cursor_type = settings.get_setting("cursor_type", "blinking")
        cursor_style = settings.get_setting("cursor_style", "block")
        self.cursor_changed.emit(cursor_type, cursor_style)
        
        # Space character
        space_char = settings.get_setting("space_char", "␣")
        self.space_char_changed.emit(space_char)
        
        # Pause delay
        pause_delay = float(settings.get_setting("pause_delay", "7"))
        self.pause_delay_changed.emit(pause_delay)
        
        # Allow continue with mistakes
        allow_continue = settings.get_setting("allow_continue_mistakes", "0") == "1"
        self.allow_continue_changed.emit(allow_continue)

        # Show typed characters
        show_typed = settings.get_setting("show_typed_characters", "0") == "1"
        self.show_typed_changed.emit(show_typed)

    def _connect_settings_signals(self):
        """Connect settings change signals to editor tab for dynamic updates."""
        if hasattr(self.editor_tab, 'typing_area'):
            self.font_changed.connect(self.editor_tab.typing_area.update_font)
            self.colors_changed.connect(self.editor_tab.typing_area.update_colors)
            self.cursor_changed.connect(self.editor_tab.typing_area.update_cursor)
            self.space_char_changed.connect(self.editor_tab.typing_area.update_space_char)
            self.pause_delay_changed.connect(self.editor_tab.typing_area.update_pause_delay)
            self.allow_continue_changed.connect(self.editor_tab.typing_area.update_allow_continue)
            self.show_typed_changed.connect(self.editor_tab.typing_area.update_show_typed_characters)
    
    def _emit_initial_settings(self):
        """Emit initial settings to apply them immediately after connection."""
        # Font settings
        family = settings.get_setting("font_family", "Consolas")
        size = int(settings.get_setting("font_size", "12"))
        ligatures = settings.get_setting("font_ligatures", "0") == "1"
        self.font_changed.emit(family, size, ligatures)
        
        # Color settings
        self.colors_changed.emit()
        
        # Cursor settings
        cursor_type = settings.get_setting("cursor_type", "blinking")
        cursor_style = settings.get_setting("cursor_style", "block")
        self.cursor_changed.emit(cursor_type, cursor_style)
        
        # Space character
        space_char = settings.get_setting("space_char", "␣")
        self.space_char_changed.emit(space_char)
        
        # Pause delay
        pause_delay = float(settings.get_setting("pause_delay", "7"))
        self.pause_delay_changed.emit(pause_delay)
        
        # Allow continue with mistakes
        allow_continue = settings.get_setting("allow_continue_mistakes", "0") == "1"
        self._update_allow_continue_buttons(allow_continue)
        self.allow_continue_changed.emit(allow_continue)

        # Show typed characters
        show_typed = settings.get_setting("show_typed_characters", "0") == "1"
        self._update_show_typed_buttons(show_typed)
        self.show_typed_changed.emit(show_typed)

    def _update_allow_continue_buttons(self, enabled: bool):
        """Refresh the button styles for the allow-continue setting."""
        if not hasattr(self, 'allow_continue_enabled_btn'):
            return
        active_style = (
            "background-color: #5e81ac; color: white; border: none; border-radius: 6px;"
            " font-weight: bold;"
        )
        inactive_style = (
            "background-color: #3b4252; color: #d8dee9; border: 1px solid #434c5e; border-radius: 6px;"
        )
        self.allow_continue_enabled_btn.setChecked(enabled)
        self.allow_continue_disabled_btn.setChecked(not enabled)
        self.allow_continue_enabled_btn.setStyleSheet(active_style if enabled else inactive_style)
        self.allow_continue_disabled_btn.setStyleSheet(active_style if not enabled else inactive_style)

    def _handle_allow_continue_button(self, enabled: bool):
        """Handle clicks on the allow-continue buttons."""
        current = settings.get_setting("allow_continue_mistakes", "0") == "1"
        if current == enabled:
            # Still ensure buttons reflect state
            self._update_allow_continue_buttons(enabled)
            return
        settings.set_setting("allow_continue_mistakes", "1" if enabled else "0")
        self._update_allow_continue_buttons(enabled)
        self.allow_continue_changed.emit(enabled)

    def _update_show_typed_buttons(self, enabled: bool):
        """Refresh the button styles for the show-typed setting."""
        if not hasattr(self, 'show_typed_enabled_btn'):
            return
        active_style = (
            "background-color: #5e81ac; color: white; border: none; border-radius: 6px;"
            " font-weight: bold;"
        )
        inactive_style = (
            "background-color: #3b4252; color: #d8dee9; border: 1px solid #434c5e; border-radius: 6px;"
        )
        self.show_typed_enabled_btn.setChecked(enabled)
        self.show_typed_disabled_btn.setChecked(not enabled)
        self.show_typed_enabled_btn.setStyleSheet(active_style if enabled else inactive_style)
        self.show_typed_disabled_btn.setStyleSheet(active_style if not enabled else inactive_style)

    def _handle_show_typed_button(self, enabled: bool):
        """Handle clicks on the show-typed buttons."""
        current = settings.get_setting("show_typed_characters", "0") == "1"
        if current == enabled:
            self._update_show_typed_buttons(enabled)
            return
        settings.set_setting("show_typed_characters", "1" if enabled else "0")
        self._update_show_typed_buttons(enabled)
        self.show_typed_changed.emit(enabled)


def run_app():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
