"""History tab widget for reviewing and managing past typing sessions."""
import csv
from datetime import datetime
from typing import Dict, List, Optional, Union
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFileDialog,
)

from app import stats_db


class HistoryTab(QWidget):
    """Tab providing filterable view of session history with bulk deletion."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_filters: Dict[str, Optional[Union[float, str]]] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("Session History")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        language_label = QLabel("Language")
        filter_row.addWidget(language_label)

        self.language_combo = QComboBox()
        self.language_combo.setMinimumWidth(150)
        filter_row.addWidget(self.language_combo)

        name_label = QLabel("File")
        filter_row.addWidget(name_label)

        self.name_filter_input = QLineEdit()
        self.name_filter_input.setPlaceholderText("Contains")
        filter_row.addWidget(self.name_filter_input)

        wpm_label = QLabel("WPM")
        filter_row.addWidget(wpm_label)

        self.min_wpm_input = self._create_numeric_input("Min")
        filter_row.addWidget(self.min_wpm_input)

        self.max_wpm_input = self._create_numeric_input("Max")
        filter_row.addWidget(self.max_wpm_input)

        duration_label = QLabel("Duration (s)")
        filter_row.addWidget(duration_label)

        self.min_duration_input = self._create_numeric_input("Min")
        filter_row.addWidget(self.min_duration_input)

        self.max_duration_input = self._create_numeric_input("Max")
        filter_row.addWidget(self.max_duration_input)

        self.apply_filters_btn = QPushButton("Apply Filters")
        self.apply_filters_btn.clicked.connect(self.apply_filters)
        filter_row.addWidget(self.apply_filters_btn)

        self.clear_filters_btn = QPushButton("Clear")
        self.clear_filters_btn.clicked.connect(self.clear_filters)
        filter_row.addWidget(self.clear_filters_btn)

        filter_row.addStretch()

        self.edit_mode_btn = QPushButton("✏️ Edit Mode")
        self.edit_mode_btn.setCheckable(True)
        self.edit_mode_btn.clicked.connect(self.toggle_edit_mode)
        filter_row.addWidget(self.edit_mode_btn)
        
        self.export_btn = QPushButton("📥 Export CSV")
        self.export_btn.clicked.connect(self.export_to_csv)
        filter_row.addWidget(self.export_btn)

        layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.delete_btn = QPushButton("🗑 Delete Selected")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected)
        action_row.addWidget(self.delete_btn)

        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #888888;")
        action_row.addWidget(self.count_label)

        action_row.addStretch()
        layout.addLayout(action_row)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Date",
            "Language",
            "File",
            "WPM",
            "Accuracy",
            "Duration (s)",
            "Correct",
            "Incorrect",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setShowGrid(True)
        self.table.setStyleSheet(
            "QTableWidget {"
            "gridline-color: rgba(236, 239, 244, 0.25);"
            "background-color: transparent;"
            "border: 1px solid rgba(236, 239, 244, 0.20);"
            "border-radius: 8px;"
            "}"
            "QHeaderView::section {"
            "background-color: rgba(129, 161, 193, 0.18);"
            "color: #eceff4;"
            "padding: 6px;"
            "border: none;"
            "}"
            "QTableWidget::item {"
            "color: #e5e9f0;"
            "border-right: 1px solid rgba(236, 239, 244, 0.1);"
            "border-bottom: 1px solid rgba(236, 239, 244, 0.1);"
            "}"
            "QTableWidget::item:selected {"
            "background-color: rgba(136, 192, 208, 0.28);"
            "color: #eceff4;"
            "}"
        )
        layout.addWidget(self.table)

        self.refresh_filters()
        self.apply_filters()

    def _create_numeric_input(self, placeholder: str) -> QLineEdit:
        """Create a numeric line edit accepting floats with optional blank value."""
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        validator = QDoubleValidator(0.0, 100000.0, 2, line_edit)
        validator.setNotation(QDoubleValidator.StandardNotation)
        line_edit.setValidator(validator)
        return line_edit

    def refresh_filters(self):
        """Refresh language dropdown options."""
        languages = stats_db.list_history_languages()
        current_language = self.language_combo.currentData()
        self.language_combo.blockSignals(True)
        self.language_combo.clear()
        self.language_combo.addItem("All Languages", None)
        for language in languages:
            self.language_combo.addItem(language, language)
        self.language_combo.blockSignals(False)

        if current_language:
            index = self.language_combo.findData(current_language)
            if index >= 0:
                self.language_combo.setCurrentIndex(index)

    def apply_filters(self):
        """Apply current filter values and reload table."""
        filters = {
            "language": self.language_combo.currentData(),
            "file_contains": (self.name_filter_input.text().strip() or None),
            "min_wpm": self._parse_float(self.min_wpm_input.text()),
            "max_wpm": self._parse_float(self.max_wpm_input.text()),
            "min_duration": self._parse_float(self.min_duration_input.text()),
            "max_duration": self._parse_float(self.max_duration_input.text()),
        }

        if self._range_invalid(filters["min_wpm"], filters["max_wpm"]):
            QMessageBox.warning(self, "Invalid Range", "Minimum WPM must be less than or equal to maximum WPM.")
            return
        if self._range_invalid(filters["min_duration"], filters["max_duration"]):
            QMessageBox.warning(self, "Invalid Range", "Minimum duration must be less than or equal to maximum duration.")
            return

        self.current_filters = filters
        self._load_history()

    def clear_filters(self):
        """Clear all filter inputs."""
        self.language_combo.setCurrentIndex(0)
        self.name_filter_input.clear()
        for widget in (self.min_wpm_input, self.max_wpm_input, self.min_duration_input, self.max_duration_input):
            widget.clear()
        self.apply_filters()

    def toggle_edit_mode(self, enabled: bool):
        """Toggle multi-select deletion mode."""
        self.table.setSelectionMode(QTableWidget.ExtendedSelection if enabled else QTableWidget.NoSelection)
        self.delete_btn.setEnabled(enabled)
        self.edit_mode_btn.setText("✅ Done" if enabled else "✏️ Edit Mode")
        if not enabled:
            self.table.clearSelection()

    def delete_selected(self):
        """Delete the currently selected rows from history."""
        selected_items = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Select sessions to delete while in edit mode.")
            return

        record_ids: List[int] = []
        for model_index in selected_items:
            row = model_index.row()
            item = self.table.item(row, 0)
            if not item:
                continue
            record_id = item.data(Qt.UserRole)
            if record_id is not None:
                record_ids.append(int(record_id))

        if not record_ids:
            return

        confirm = QMessageBox.question(
            self,
            "Delete Sessions",
            f"Delete {len(record_ids)} selected session(s)? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        stats_db.delete_session_history(record_ids)
        self.refresh_filters()
        self._load_history()

        parent_window = self.window()
        if hasattr(parent_window, "refresh_languages_tab"):
            parent_window.refresh_languages_tab()

    def refresh_history(self):
        """Refresh filters and table content, keeping current selections."""
        self.refresh_filters()
        self._load_history()

    def _range_invalid(self, minimum: Optional[float], maximum: Optional[float]) -> bool:
        return minimum is not None and maximum is not None and minimum > maximum

    def _parse_float(self, text: str) -> Optional[float]:
        return float(text) if text else None

    def _load_history(self):
        """Load rows from the database according to stored filters."""
        filters = getattr(self, "current_filters", {})
        history = stats_db.fetch_session_history(
            language=filters.get("language"),
            file_contains=filters.get("file_contains"),
            min_wpm=filters.get("min_wpm"),
            max_wpm=filters.get("max_wpm"),
            min_duration=filters.get("min_duration"),
            max_duration=filters.get("max_duration"),
        )

        header = self.table.horizontalHeader()
        sort_col = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for record in history:
            row = self.table.rowCount()
            self.table.insertRow(row)

            timestamp_value = record.get("recorded_at")
            timestamp_item = QTableWidgetItem(self._format_timestamp(timestamp_value))
            timestamp_item.setData(Qt.UserRole, record.get("id"))
            if timestamp_value:
                timestamp_item.setData(Qt.EditRole, timestamp_value)
            timestamp_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, timestamp_item)

            language_item = QTableWidgetItem(record.get("language") or "Unknown")
            language_item.setData(Qt.EditRole, (record.get("language") or "Unknown"))
            language_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, language_item)

            file_path = record.get("file_path") or ""
            file_name = Path(file_path).name if file_path else ""
            file_item = QTableWidgetItem(file_name)
            file_item.setData(Qt.EditRole, file_name.lower())
            file_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, file_item)

            wpm_item = QTableWidgetItem(f"{record.get('wpm', 0.0):.1f}")
            wpm_item.setData(Qt.EditRole, record.get("wpm", 0.0))
            wpm_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, wpm_item)

            accuracy = record.get("accuracy", 0.0)
            accuracy_item = QTableWidgetItem(f"{accuracy * 100:.1f}%")
            accuracy_item.setData(Qt.EditRole, accuracy)
            accuracy_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, accuracy_item)

            duration_item = QTableWidgetItem(f"{record.get('duration', 0.0):.1f}")
            duration_item.setData(Qt.EditRole, record.get("duration", 0.0))
            duration_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, duration_item)

            correct_item = QTableWidgetItem(str(record.get("correct", 0)))
            correct_item.setData(Qt.EditRole, record.get("correct", 0))
            correct_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 6, correct_item)

            incorrect_item = QTableWidgetItem(str(record.get("incorrect", 0)))
            incorrect_item.setData(Qt.EditRole, record.get("incorrect", 0))
            incorrect_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 7, incorrect_item)

        self.count_label.setText(f"Showing {len(history)} session(s)")
        self.table.setSortingEnabled(True)
        if self.table.rowCount() and 0 <= sort_col < self.table.columnCount():
            self.table.sortItems(sort_col, sort_order)

    def _format_timestamp(self, value: Optional[str]) -> str:
        """Format timestamp string for display."""
        if not value:
            return ""
        try:
            return datetime.fromisoformat(value).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return value
    
    def export_to_csv(self):
        """Export current filtered session history to CSV file."""
        filters = getattr(self, "current_filters", {})
        history = stats_db.fetch_session_history(
            language=filters.get("language"),
            file_contains=filters.get("file_contains"),
            min_wpm=filters.get("min_wpm"),
            max_wpm=filters.get("max_wpm"),
            min_duration=filters.get("min_duration"),
            max_duration=filters.get("max_duration"),
        )
        
        if not history:
            QMessageBox.information(self, "No Data", "No session history to export.")
            return
        
        # Ask user where to save the CSV
        default_filename = f"session_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Session History",
            default_filename,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'Date', 'Language', 'File', 'WPM', 'Accuracy', 
                    'Duration (s)', 'Correct', 'Incorrect'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for record in history:
                    timestamp_value = record.get("recorded_at", "")
                    formatted_date = self._format_timestamp(timestamp_value)
                    file_path_val = record.get("file_path") or ""
                    file_name = Path(file_path_val).name if file_path_val else ""
                    accuracy = record.get("accuracy", 0.0)
                    
                    writer.writerow({
                        'Date': formatted_date,
                        'Language': record.get("language") or "Unknown",
                        'File': file_name,
                        'WPM': f"{record.get('wpm', 0.0):.1f}",
                        'Accuracy': f"{accuracy * 100:.1f}%",
                        'Duration (s)': f"{record.get('duration', 0.0):.1f}",
                        'Correct': record.get("correct", 0),
                        'Incorrect': record.get("incorrect", 0)
                    })
            
            QMessageBox.information(
                self, 
                "Export Successful", 
                f"Exported {len(history)} session(s) to:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export session history:\n{str(e)}"
            )
