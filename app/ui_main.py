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
from PySide6.QtCore import Qt
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

    def _create_settings_tab(self) -> QWidget:
        """Create and return the settings tab widget."""
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
        
        s_layout.addStretch()
        return settings_widget

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
        # TODO: Apply theme to application

    def on_scheme_changed(self, scheme: str):
        settings.set_setting("dark_scheme", scheme)
        # TODO: Apply color scheme to application


def run_app():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
