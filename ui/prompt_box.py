"""Prompt management box widget with file upload and action buttons."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import DARK_THEME, MAX_FILE_SIZE, MAX_FILES, SUPPORTED_FORMATS, UPLOAD_DIR
from utils.models import UploadedFile


class FileChip(QFrame):
    """Widget representing an uploaded file chip."""

    removeClicked = pyqtSignal(str)

    def __init__(self, filename: str, parent=None):
        super().__init__(parent)
        self.filename = filename
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {DARK_THEME['surface_light']};
                border-radius: 12px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 6, 4)
        layout.setSpacing(6)

        name_label = QLabel(self.filename[:20] + "..." if len(self.filename) > 20 else self.filename)
        name_label.setStyleSheet(f"color: {DARK_THEME['accent']}; font-size: 11px;")
        layout.addWidget(name_label)

        remove_btn = QPushButton("x")
        remove_btn.setFixedSize(16, 16)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['border']};
                border-radius: 8px;
                font-size: 10px;
                font-weight: bold;
                color: {DARK_THEME['text_primary']};
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['error']};
            }}
        """)
        remove_btn.clicked.connect(lambda: self.removeClicked.emit(self.filename))
        layout.addWidget(remove_btn)


class PromptManagementBox(QWidget):
    """Widget for managing prompts with file upload and action buttons."""

    sendRequested = pyqtSignal()
    grabRequested = pyqtSignal()
    summarizeRequested = pyqtSignal()
    savePromptRequested = pyqtSignal()
    deleteSelectedRequested = pyqtSignal()
    filesChanged = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.uploaded_files: List[UploadedFile] = []
        self.file_chips: List[FileChip] = []
        self._has_selection = False
        self._active_placeholders: List[str] = []
        self._slash_prefix = ""

        self._setup_ui()
        self._setup_completion_popup()

    def _setup_ui(self):
        self.setStyleSheet(f"background-color: {DARK_THEME['background']};")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        file_section = QFrame()
        file_section.setStyleSheet(f"""
            QFrame {{
                background-color: {DARK_THEME['surface']};
                border: 1px dashed {DARK_THEME['border']};
                border-radius: 8px;
            }}
        """)

        file_layout = QVBoxLayout(file_section)
        file_layout.setContentsMargins(12, 8, 12, 8)
        file_layout.setSpacing(6)

        file_header = QHBoxLayout()

        self.file_count_label = QLabel(f"Files (0/{MAX_FILES})")
        self.file_count_label.setStyleSheet(f"font-weight: bold; color: {DARK_THEME['text_primary']}; font-size: 12px;")
        file_header.addWidget(self.file_count_label)

        file_header.addStretch()

        upload_btn = QPushButton("Upload Files")
        upload_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['accent']};
                color: white;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent_hover']};
            }}
        """)
        upload_btn.clicked.connect(self._open_file_dialog)
        file_header.addWidget(upload_btn)

        file_layout.addLayout(file_header)

        self.chips_container = QWidget()
        self.chips_layout = QHBoxLayout(self.chips_container)
        self.chips_layout.setContentsMargins(0, 0, 0, 0)
        self.chips_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.chips_layout.setSpacing(6)
        file_layout.addWidget(self.chips_container)

        # Mode info label (inject content only)
        mode_info = QLabel("File content will be injected into the prompt")
        mode_info.setStyleSheet(f"font-size: 10px; color: {DARK_THEME['text_secondary']}; font-style: italic;")
        file_layout.addWidget(mode_info)

        layout.addWidget(file_section)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Type your prompt here... (Click pills to select, double-click or ... to edit)")
        self.text_edit.setMaximumHeight(100)
        self.text_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
            }}
            QPlainTextEdit:focus {{
                border-color: {DARK_THEME['accent']};
            }}
        """)
        layout.addWidget(self.text_edit)

        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 4, 0, 0)
        button_layout.setSpacing(8)

        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['success']};
                color: white;
                border-radius: 16px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #388E3C;
            }}
            QPushButton:disabled {{
                background-color: {DARK_THEME['border']};
            }}
        """)
        self.send_btn.clicked.connect(self.sendRequested.emit)
        button_layout.addWidget(self.send_btn)

        self.grab_btn = QPushButton("Grab")
        self.grab_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['accent']};
                color: white;
                border-radius: 16px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent_hover']};
            }}
        """)
        self.grab_btn.clicked.connect(self.grabRequested.emit)
        button_layout.addWidget(self.grab_btn)

        self.summarize_btn = QPushButton("Summarize")
        self.summarize_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['warning']};
                color: white;
                border-radius: 16px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #F57C00;
            }}
        """)
        self.summarize_btn.clicked.connect(self.summarizeRequested.emit)
        button_layout.addWidget(self.summarize_btn)

        button_layout.addStretch()

        self.save_btn = QPushButton("Save as Prompt")
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #9C27B0;
                color: white;
                border-radius: 16px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #7B1FA2;
            }}
        """)
        self.save_btn.clicked.connect(self.savePromptRequested.emit)
        button_layout.addWidget(self.save_btn)

        layout.addWidget(button_container)

    def _setup_completion_popup(self):
        """Create the floating completion popup for placeholder selection."""
        self._popup = QListWidget(self)
        self._popup.setWindowFlags(Qt.WindowType.ToolTip)
        self._popup.setStyleSheet(f"""
            QListWidget {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['accent']};
                border-radius: 4px;
                font-size: 13px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 6px 10px;
            }}
            QListWidget::item:selected {{
                background-color: {DARK_THEME['accent']};
                color: white;
            }}
            QListWidget::item:hover {{
                background-color: {DARK_THEME['surface_light']};
            }}
        """)
        self._popup.setMaximumHeight(160)
        self._popup.setMaximumWidth(260)
        self._popup.hide()
        self._popup.itemActivated.connect(self._on_popup_item_selected)

        self.text_edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Intercept key events on the text edit for slash completion."""
        if obj is not self.text_edit:
            return super().eventFilter(obj, event)

        if event.type() == QEvent.Type.KeyPress:
            if self._popup.isVisible():
                key = event.key()
                if key == Qt.Key.Key_Escape:
                    self._popup.hide()
                    return True
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    current = self._popup.currentItem()
                    if current:
                        self._on_popup_item_selected(current)
                        return True
                if key == Qt.Key.Key_Down:
                    row = self._popup.currentRow()
                    if row < self._popup.count() - 1:
                        self._popup.setCurrentRow(row + 1)
                    return True
                if key == Qt.Key.Key_Up:
                    row = self._popup.currentRow()
                    if row > 0:
                        self._popup.setCurrentRow(row - 1)
                    return True
                # Typing filters the list
                if key == Qt.Key.Key_Backspace:
                    if self._slash_prefix:
                        self._slash_prefix = self._slash_prefix[:-1]
                    else:
                        self._popup.hide()
                        return False
                    self._filter_popup()
                    return False
                text = event.text()
                if text and text.isprintable() and text != '/':
                    self._slash_prefix += text.upper()
                    self._filter_popup()
                    return False

            # Detect '/' typed when popup is not visible
            if event.text() == '/' and self._active_placeholders:
                self._slash_prefix = ""
                self._show_popup()

        return super().eventFilter(obj, event)

    def _show_popup(self):
        """Show the placeholder completion popup."""
        self._popup.clear()
        for name in self._active_placeholders:
            item = QListWidgetItem(f"[/{name}]")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self._popup.addItem(item)

        if self._popup.count() == 0:
            return

        self._popup.setCurrentRow(0)

        # Position below the text cursor
        cursor_rect = self.text_edit.cursorRect()
        global_pos = self.text_edit.mapToGlobal(cursor_rect.bottomLeft())
        self._popup.move(global_pos)
        self._popup.setFixedWidth(max(200, self._popup.sizeHintForColumn(0) + 30))
        self._popup.show()
        self._popup.raise_()

    def _filter_popup(self):
        """Filter popup items based on typed prefix after '/'."""
        for i in range(self._popup.count()):
            item = self._popup.item(i)
            name = item.data(Qt.ItemDataRole.UserRole)
            item.setHidden(not name.startswith(self._slash_prefix))

        # Select first visible
        for i in range(self._popup.count()):
            item = self._popup.item(i)
            if not item.isHidden():
                self._popup.setCurrentItem(item)
                break

        # Hide if nothing matches
        visible = any(not self._popup.item(i).isHidden() for i in range(self._popup.count()))
        if not visible:
            self._popup.hide()

    def _on_popup_item_selected(self, item):
        """Insert the selected placeholder into the text edit."""
        name = item.data(Qt.ItemDataRole.UserRole)
        self._popup.hide()

        cursor = self.text_edit.textCursor()

        # Remove the '/' and any typed filter text from the editor
        chars_to_remove = 1 + len(self._slash_prefix)  # '/' + filter chars
        for _ in range(chars_to_remove):
            cursor.deletePreviousChar()

        # Insert [/NAME]=""
        insert_text = f'[/{name}]="'
        cursor.insertText(insert_text)
        # Save position between quotes, then insert closing quote
        cursor.insertText('"')
        cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, 1)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.setFocus()

    def update_placeholders(self, placeholders: List[str]):
        """Update the list of available placeholders from selected pills."""
        self._active_placeholders = placeholders

    def set_selection_active(self, has_selection: bool):
        """Track selection state (delete button moved to items panel)."""
        self._has_selection = has_selection

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
        """Always return inject mode since upload to platform was removed."""
        return "inject"

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
