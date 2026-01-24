"""Input panel widget for query entry and controls."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import MAX_FILE_SIZE, MAX_FILES, SUPPORTED_FORMATS, UPLOAD_DIR
from utils.models import UploadedFile


class FileChip(QFrame):
    """Widget representing an uploaded file chip."""

    removeClicked = pyqtSignal(str)

    def __init__(self, filename: str, parent=None):
        super().__init__(parent)
        self.filename = filename

        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #E3F2FD;
                border-radius: 12px;
                padding: 4px 8px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(4)

        name_label = QLabel(self.filename)
        name_label.setStyleSheet("color: #1976D2; font-size: 12px;")
        layout.addWidget(name_label)

        remove_btn = QPushButton("x")
        remove_btn.setFixedSize(16, 16)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #BBDEFB;
                border-radius: 8px;
                font-size: 10px;
                font-weight: bold;
                color: #1976D2;
            }
            QPushButton:hover {
                background-color: #90CAF9;
            }
        """)
        remove_btn.clicked.connect(lambda: self.removeClicked.emit(self.filename))
        layout.addWidget(remove_btn)


class InputPanel(QWidget):
    """Input panel with file upload, query input, and controls."""

    sendClicked = pyqtSignal()
    exportClicked = pyqtSignal()
    filesAdded = pyqtSignal(list)
    fileRemoved = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.uploaded_files: List[UploadedFile] = []
        self.file_chips: List[FileChip] = []

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        file_section = QFrame()
        file_section.setObjectName("fileSection")
        file_section.setStyleSheet("""
            QFrame#fileSection {
                background-color: #F5F5F5;
                border: 2px dashed #BDBDBD;
                border-radius: 8px;
            }
            QFrame#fileSection QLabel {
                color: #333333;
            }
        """)

        file_layout = QVBoxLayout(file_section)
        file_layout.setContentsMargins(12, 8, 12, 8)

        file_header = QHBoxLayout()

        self.file_count_label = QLabel(f"Files (0/{MAX_FILES})")
        self.file_count_label.setStyleSheet("font-weight: bold; color: #333333; font-size: 13px;")
        file_header.addWidget(self.file_count_label)

        file_header.addStretch()

        upload_btn = QPushButton("Upload Files")
        upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        upload_btn.clicked.connect(self._open_file_dialog)
        file_header.addWidget(upload_btn)

        file_layout.addLayout(file_header)

        self.chips_layout = QHBoxLayout()
        self.chips_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        file_layout.addLayout(self.chips_layout)

        layout.addWidget(file_section)

        self.query_input = QTextEdit()
        self.query_input.setPlaceholderText("Type your research query here...")
        self.query_input.setMaximumHeight(100)
        self.query_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #CCCCCC;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #2196F3;
            }
        """)
        layout.addWidget(self.query_input)

        controls_layout = QHBoxLayout()

        model_layout = QVBoxLayout()
        model_label = QLabel("Model")
        model_label.setStyleSheet("font-size: 11px; color: #666;")
        model_layout.addWidget(model_label)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["Auto", "Perplexity", "Gemini", "ChatGPT"])
        self.model_combo.setStyleSheet(self._combo_style())
        model_layout.addWidget(self.model_combo)
        controls_layout.addLayout(model_layout)

        mode_layout = QVBoxLayout()
        mode_label = QLabel("Mode")
        mode_label.setStyleSheet("font-size: 11px; color: #666;")
        mode_layout.addWidget(mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Auto", "Manual"])
        self.mode_combo.setStyleSheet(self._combo_style())
        mode_layout.addWidget(self.mode_combo)
        controls_layout.addLayout(mode_layout)

        task_layout = QVBoxLayout()
        task_label = QLabel("Task")
        task_label.setStyleSheet("font-size: 11px; color: #666;")
        task_layout.addWidget(task_label)

        self.task_combo = QComboBox()
        self.task_combo.addItems(["Initial Research", "Targeted Research", "Draft"])
        self.task_combo.setStyleSheet(self._combo_style())
        task_layout.addWidget(self.task_combo)
        controls_layout.addLayout(task_layout)

        controls_layout.addStretch()

        # Status and timer section
        status_container = QHBoxLayout()
        status_container.setSpacing(8)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        status_container.addWidget(self.status_label)

        self.timer_label = QLabel("")
        self.timer_label.setStyleSheet("color: #666; font-size: 12px;")
        status_container.addWidget(self.timer_label)

        controls_layout.addLayout(status_container)

        # Setup elapsed timer
        self._elapsed_seconds = 0
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._update_elapsed_time)

        layout.addLayout(controls_layout)

        buttons_layout = QHBoxLayout()

        self.export_btn = QPushButton("Export")
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.export_btn.clicked.connect(self.exportClicked.emit)
        buttons_layout.addWidget(self.export_btn)

        buttons_layout.addStretch()

        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
                padding: 10px 30px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.send_btn.clicked.connect(self.sendClicked.emit)
        buttons_layout.addWidget(self.send_btn)

        layout.addLayout(buttons_layout)

    def _combo_style(self) -> str:
        return """
            QComboBox {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 100px;
            }
            QComboBox:focus {
                border-color: #2196F3;
            }
        """

    def _open_file_dialog(self):
        """Open file selection dialog."""
        if len(self.uploaded_files) >= MAX_FILES:
            return

        remaining = MAX_FILES - len(self.uploaded_files)

        formats = " ".join([f"*{fmt}" for fmt in SUPPORTED_FORMATS])
        file_filter = f"Supported Files ({formats})"

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files",
            str(Path.home()),
            file_filter
        )

        if files:
            self._add_files(files[:remaining])

    def _add_files(self, file_paths: List[str]):
        """Add files to the upload list."""
        new_files = []

        for path in file_paths:
            file_path = Path(path)

            if file_path.suffix.lower() not in SUPPORTED_FORMATS:
                continue

            size = file_path.stat().st_size
            if size > MAX_FILE_SIZE:
                continue

            dest_path = UPLOAD_DIR / file_path.name
            shutil.copy2(path, dest_path)

            uploaded = UploadedFile(
                filename=file_path.name,
                path=str(dest_path),
                file_type=file_path.suffix.lower()[1:],
                size_bytes=size,
                upload_time=datetime.now()
            )

            self.uploaded_files.append(uploaded)
            new_files.append(uploaded)

            chip = FileChip(file_path.name)
            chip.removeClicked.connect(self._remove_file)
            self.file_chips.append(chip)
            self.chips_layout.addWidget(chip)

        self._update_file_count()

        if new_files:
            self.filesAdded.emit(new_files)

    def _remove_file(self, filename: str):
        """Remove a file from the upload list."""
        for i, file in enumerate(self.uploaded_files):
            if file.filename == filename:
                try:
                    os.remove(file.path)
                except OSError:
                    pass

                self.uploaded_files.pop(i)
                break

        for chip in self.file_chips:
            if chip.filename == filename:
                self.chips_layout.removeWidget(chip)
                chip.deleteLater()
                self.file_chips.remove(chip)
                break

        self._update_file_count()
        self.fileRemoved.emit(filename)

    def _update_file_count(self):
        """Update the file count label."""
        count = len(self.uploaded_files)
        self.file_count_label.setText(f"Files ({count}/{MAX_FILES})")

    def get_query(self) -> str:
        """Get the current query text."""
        return self.query_input.toPlainText().strip()

    def get_model(self) -> str:
        """Get the selected model."""
        return self.model_combo.currentText().lower()

    def get_mode(self) -> str:
        """Get the selected mode."""
        return self.mode_combo.currentText().lower()

    def get_task(self) -> str:
        """Get the selected task type."""
        task_map = {
            "Initial Research": "initial",
            "Targeted Research": "targeted",
            "Draft": "draft"
        }
        return task_map.get(self.task_combo.currentText(), "initial")

    def get_files(self) -> List[UploadedFile]:
        """Get the list of uploaded files."""
        return self.uploaded_files.copy()

    def set_status(self, status: str, color: str = "#4CAF50"):
        """Set the status label text and color."""
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def set_send_enabled(self, enabled: bool):
        """Enable or disable the send button."""
        self.send_btn.setEnabled(enabled)

    def set_export_enabled(self, enabled: bool):
        """Enable or disable the export button."""
        self.export_btn.setEnabled(enabled)

    def clear_input(self):
        """Clear the query input."""
        self.query_input.clear()

    def clear_files(self):
        """Clear all uploaded files."""
        for file in self.uploaded_files:
            try:
                os.remove(file.path)
            except OSError:
                pass

        self.uploaded_files.clear()

        for chip in self.file_chips:
            self.chips_layout.removeWidget(chip)
            chip.deleteLater()

        self.file_chips.clear()
        self._update_file_count()

    def start_timer(self):
        """Start the elapsed time timer."""
        self._elapsed_seconds = 0
        self.timer_label.setText("(0s)")
        self._elapsed_timer.start(1000)

    def stop_timer(self):
        """Stop the elapsed time timer."""
        self._elapsed_timer.stop()
        # Keep showing the final time

    def reset_timer(self):
        """Reset and hide the timer."""
        self._elapsed_timer.stop()
        self._elapsed_seconds = 0
        self.timer_label.setText("")

    def _update_elapsed_time(self):
        """Update the elapsed time display."""
        self._elapsed_seconds += 1
        if self._elapsed_seconds < 60:
            self.timer_label.setText(f"({self._elapsed_seconds}s)")
        else:
            minutes = self._elapsed_seconds // 60
            seconds = self._elapsed_seconds % 60
            self.timer_label.setText(f"({minutes}m {seconds}s)")
