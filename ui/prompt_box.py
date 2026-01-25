"""Prompt management box widget with file upload and action buttons."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
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


class PromptManagementBox(QWidget):
    """Widget for managing prompts with file upload and action buttons."""

    sendRequested = pyqtSignal()
    grabRequested = pyqtSignal()
    summarizeRequested = pyqtSignal()
    savePromptRequested = pyqtSignal()
    filesChanged = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.uploaded_files: List[UploadedFile] = []
        self.file_chips: List[FileChip] = []

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        file_section = QFrame()
        file_section.setObjectName("fileSection")
        file_section.setStyleSheet("""
            QFrame#fileSection {
                background-color: #F5F5F5;
                border: 2px dashed #BDBDBD;
                border-radius: 8px;
            }
        """)

        file_layout = QVBoxLayout(file_section)
        file_layout.setContentsMargins(12, 8, 12, 8)
        file_layout.setSpacing(6)

        file_header = QHBoxLayout()

        self.file_count_label = QLabel(f"Files (0/{MAX_FILES})")
        self.file_count_label.setStyleSheet("font-weight: bold; color: #333; font-size: 12px;")
        file_header.addWidget(self.file_count_label)

        file_header.addStretch()

        upload_btn = QPushButton("Upload Files")
        upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 11px;
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

        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(16)

        mode_label = QLabel("Upload Mode:")
        mode_label.setStyleSheet("font-size: 11px; color: #666;")
        mode_layout.addWidget(mode_label)

        self.mode_group = QButtonGroup(self)

        self.inject_radio = QRadioButton("Inject Content")
        self.inject_radio.setChecked(True)
        self.inject_radio.setStyleSheet("font-size: 11px;")
        self.mode_group.addButton(self.inject_radio)
        mode_layout.addWidget(self.inject_radio)

        self.upload_radio = QRadioButton("Upload File")
        self.upload_radio.setStyleSheet("font-size: 11px;")
        self.mode_group.addButton(self.upload_radio)
        mode_layout.addWidget(self.upload_radio)

        mode_layout.addStretch()
        file_layout.addLayout(mode_layout)

        layout.addWidget(file_section)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Type your prompt here... (Enter = newline)")
        self.text_edit.setMaximumHeight(120)
        self.text_edit.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #CCC;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
            }
            QPlainTextEdit:focus {
                border-color: #2196F3;
            }
        """)
        layout.addWidget(self.text_edit)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:disabled {
                background-color: #CCC;
            }
        """)
        self.send_btn.clicked.connect(self.sendRequested.emit)
        button_layout.addWidget(self.send_btn)

        self.grab_btn = QPushButton("Grab")
        self.grab_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.grab_btn.clicked.connect(self.grabRequested.emit)
        button_layout.addWidget(self.grab_btn)

        self.summarize_btn = QPushButton("Summarize")
        self.summarize_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.summarize_btn.clicked.connect(self.summarizeRequested.emit)
        button_layout.addWidget(self.summarize_btn)

        button_layout.addStretch()

        self.save_btn = QPushButton("Save as Prompt")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.save_btn.clicked.connect(self.savePromptRequested.emit)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

    def _open_file_dialog(self):
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
            self.filesChanged.emit(self.uploaded_files)

    def _remove_file(self, filename: str):
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
        self.filesChanged.emit(self.uploaded_files)

    def _update_file_count(self):
        count = len(self.uploaded_files)
        self.file_count_label.setText(f"Files ({count}/{MAX_FILES})")

    def get_text(self) -> str:
        return self.text_edit.toPlainText().strip()

    def set_text(self, text: str):
        self.text_edit.setPlainText(text)

    def clear_text(self):
        self.text_edit.clear()

    def get_files(self) -> List[UploadedFile]:
        return self.uploaded_files.copy()

    def get_upload_mode(self) -> str:
        return "inject" if self.inject_radio.isChecked() else "upload"

    def clear_files(self):
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
        self.filesChanged.emit([])

    def set_send_enabled(self, enabled: bool):
        self.send_btn.setEnabled(enabled)
