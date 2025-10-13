from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
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
from PySide6.QtCore import Qt, Signal, QObject
import sys
from pathlib import Path
import app.settings as settings
from app.languages_tab import LanguagesTab
from app.editor_tab import EditorTab


class FoldersTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        settings.init_db()
        self.s = None
        self.layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("+")
        self.add_btn.setToolTip("Add folder")
        self.edit_btn = QPushButton("✎")
        self.view_toggle = QPushButton("Detail View")
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.view_toggle)
        toolbar.addStretch()

        container = QWidget()
        container.setLayout(toolbar)
        self.layout.addWidget(container)

        self.list = QListWidget()
        self.layout.addWidget(self.list)

        self.add_btn.clicked.connect(self.on_add)
        self.edit_btn.setCheckable(True)
        self.edit_btn.toggled.connect(self.on_edit_toggled)
        self.view_toggle.setCheckable(True)
        self.view_toggle.toggled.connect(self.on_view_toggled)
        self.list.itemDoubleClicked.connect(self.on_folder_double_clicked)

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
        for p in settings.get_folders():
            it = QListWidgetItem(QIcon.fromTheme("folder"), str(p))
            it.setData(Qt.UserRole, p)
            self.list.addItem(it)

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
        # enter remove mode; show red X on items (simplified as suffix)
        for i in range(self.list.count()):
            it = self.list.item(i)
            p = it.data(Qt.UserRole)
            if checked:
                it.setText(f"{p}  [remove]")
                # attach click handler
                self.list.itemClicked.connect(self._maybe_remove_item)
            else:
                it.setText(p)
                try:
                    self.list.itemClicked.disconnect(self._maybe_remove_item)
                except Exception:
                    pass

    def _maybe_remove_item(self, item: QListWidgetItem):
        # Only active in edit mode
        if not self.edit_btn.isChecked():
            return
        p = item.data(Qt.UserRole)
        delete_confirm = settings.get_setting("delete_confirm", "1")
        do_confirm = delete_confirm == "1"
        if do_confirm:
            mb = QMessageBox(self)
            mb.setWindowTitle("Confirm remove")
            mb.setText(f"Remove folder {p}?")
            cb = QCheckBox("Don't ask again")
            mb.setCheckBox(cb)
            mb.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            r = mb.exec()
            if r == QMessageBox.Yes:
                settings.remove_folder(p)
                if cb.isChecked():
                    settings.set_setting("delete_confirm", "0")
            else:
                return
        else:
            settings.remove_folder(p)
        self.load_folders()
        # Notify parent to refresh languages tab
        parent_window = self.window()
        if hasattr(parent_window, 'refresh_languages_tab'):
            parent_window.refresh_languages_tab()

    def on_view_toggled(self, checked: bool):
        if checked:
            self.view_toggle.setText("Icon View")
            self.list.setViewMode(QListWidget.ViewMode.IconMode)
        else:
            self.view_toggle.setText("Detail View")
            self.list.setViewMode(QListWidget.ViewMode.ListMode)


class MainWindow(QMainWindow):
    # Signals for dynamic settings updates
    font_changed = Signal(str, int, bool)  # family, size, ligatures
    colors_changed = Signal()
    cursor_changed = Signal(str, str)  # type, style
    space_char_changed = Signal(str)
    pause_delay_changed = Signal(float)
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
        
        # Editor/Typing tab
        self.editor_tab = EditorTab()
        self.tabs.addTab(self.editor_tab, "Typing")

        # Settings tab
        settings.init_db()
        self.settings_tab = self._create_settings_tab()
        self.tabs.addTab(self.settings_tab, "Settings")

        self.setCentralWidget(self.tabs)
        
        # Apply initial theme
        self.apply_current_theme()
        
        # Connect settings signals to editor tab for dynamic updates
        self._connect_settings_signals()

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
        
        # General settings group
        general_group = QGroupBox("General")
        general_layout = QVBoxLayout()
        
        self.delete_confirm_cb = QCheckBox("Show delete confirmation dialogs")
        cur_val = settings.get_setting("delete_confirm", "1")
        self.delete_confirm_cb.setChecked(cur_val == "1")
        self.delete_confirm_cb.stateChanged.connect(self.on_delete_confirm_changed)
        general_layout.addWidget(self.delete_confirm_cb)
        
        self.show_typed_cb = QCheckBox("Show what you actually typed (not what was expected)")
        self.show_typed_cb.setToolTip(
            "When CHECKED: If you type 'x' instead of 'c', you'll see 'x' in red\n"
            "When UNCHECKED: If you type 'x' instead of 'c', you'll see 'c' in red"
        )
        show_typed = settings.get_setting("show_typed_char", "1")
        self.show_typed_cb.setChecked(show_typed == "1")
        self.show_typed_cb.stateChanged.connect(self.on_show_typed_changed)
        general_layout.addWidget(self.show_typed_cb)
        
        general_group.setLayout(general_layout)
        s_layout.addWidget(general_group)
        
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
        self.pause_delay_spin.valueChanged.connect(self.on_pause_delay_changed)
        typing_layout.addRow("Auto-pause delay:", self.pause_delay_spin)
        
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
        self.tabs.setCurrentIndex(2)  # Switch to typing tab
    
    def open_typing_tab_for_language(self, language: str, files: list):
        """Switch to typing tab and load files for a specific language."""
        self.editor_tab.load_language_files(language, files)
        self.tabs.setCurrentIndex(2)  # Switch to typing tab
    
    def refresh_languages_tab(self):
        """Refresh the languages tab after folders change."""
        self.languages_tab.refresh_languages()

    def on_delete_confirm_changed(self, state: int):
        settings.set_setting("delete_confirm", "1" if state == Qt.Checked else "0")

    def on_theme_changed(self, theme: str):
        settings.set_setting("theme", theme)
        self.apply_current_theme()
        self.update_color_buttons_from_theme()

    def on_scheme_changed(self, scheme: str):
        settings.set_setting("dark_scheme", scheme)
        self.apply_current_theme()
        self.update_color_buttons_from_theme()
    
    def on_show_typed_changed(self, state: int):
        settings.set_setting("show_typed_char", "1" if state == Qt.Checked else "0")
        self.show_typed_changed.emit(state == Qt.Checked)
    
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
        # General settings
        delete_confirm = settings.get_setting("delete_confirm", "1")
        self.delete_confirm_cb.setChecked(delete_confirm == "1")
        
        show_typed = settings.get_setting("show_typed_char", "1")
        self.show_typed_cb.setChecked(show_typed == "1")
        
        allow_continue = settings.get_setting("allow_continue_on_error", "1")
        self.allow_continue_cb.setChecked(allow_continue == "1")
        
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
        
        # Show typed character
        show_typed = settings.get_setting("show_typed_char", "1") == "1"
        self.show_typed_changed.emit(show_typed)
    
    def _connect_settings_signals(self):
        """Connect settings change signals to editor tab for dynamic updates."""
        if hasattr(self.editor_tab, 'typing_area'):
            self.font_changed.connect(self.editor_tab.typing_area.update_font)
            self.colors_changed.connect(self.editor_tab.typing_area.update_colors)
            self.cursor_changed.connect(self.editor_tab.typing_area.update_cursor)
            self.space_char_changed.connect(self.editor_tab.typing_area.update_space_char)
            self.pause_delay_changed.connect(self.editor_tab.typing_area.update_pause_delay)
            self.show_typed_changed.connect(self.editor_tab.typing_area.update_show_typed)


def run_app():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
