"""Item editor dialog for viewing and editing prompts/responses."""

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from config import COLOR_PALETTE, DEFAULT_CATEGORIES
from utils.models import CategoryType, ColorLabel, PromptItem, ResponseItem


class ColorButton(QPushButton):
    """Button for selecting a color."""

    def __init__(self, color_name: str, color_hex: str, parent=None):
        super().__init__(parent)
        self.color_name = color_name
        self.color_hex = color_hex
        self.setFixedSize(24, 24)
        self._selected = False
        self._update_style()

    def _update_style(self):
        border = "2px solid #333" if self._selected else "1px solid #CCC"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color_hex};
                border: {border};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #666;
            }}
        """)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()


class ItemEditorDialog(QDialog):
    """Modal dialog for viewing and editing items."""

    def __init__(self, item=None, item_type="prompt", parent=None):
        super().__init__(parent)
        self.item = item
        self.item_type = item_type
        self.result_item = None

        self.setWindowTitle("Edit Prompt" if item_type == "prompt" else "Edit Response")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        self._setup_ui()
        self._populate_fields()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title_layout = QHBoxLayout()
        title_label = QLabel("Title:")
        title_label.setFixedWidth(80)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Enter title...")
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)

        category_layout = QHBoxLayout()
        category_label = QLabel("Category:")
        category_label.setFixedWidth(80)
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(DEFAULT_CATEGORIES)
        category_layout.addWidget(category_label)
        category_layout.addWidget(self.category_combo)
        layout.addLayout(category_layout)

        color_layout = QHBoxLayout()
        color_label = QLabel("Color:")
        color_label.setFixedWidth(80)
        color_layout.addWidget(color_label)

        self.color_buttons = {}
        color_container = QHBoxLayout()
        color_container.setSpacing(4)
        for color_name, color_hex in COLOR_PALETTE.items():
            btn = ColorButton(color_name, color_hex)
            btn.clicked.connect(lambda checked, cn=color_name: self._on_color_selected(cn))
            self.color_buttons[color_name] = btn
            color_container.addWidget(btn)
        color_container.addStretch()
        color_layout.addLayout(color_container)
        layout.addLayout(color_layout)

        content_label = QLabel("Content:")
        layout.addWidget(content_label)

        self.content_edit = QPlainTextEdit()
        self.content_edit.setPlaceholderText("Enter content...")
        self.content_edit.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #CCC;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.content_edit, 1)

        if self.item_type == "response" and self.item:
            info_frame = QFrame()
            info_frame.setStyleSheet("background-color: #F5F5F5; border-radius: 4px; padding: 8px;")
            info_layout = QHBoxLayout(info_frame)
            info_layout.setContentsMargins(8, 4, 8, 4)

            if self.item.platform:
                platform_label = QLabel(f"Platform: {self.item.platform}")
                platform_label.setStyleSheet("color: #666; font-size: 11px;")
                info_layout.addWidget(platform_label)

            info_layout.addStretch()

            created_label = QLabel(f"Created: {self.item.created_at.strftime('%Y-%m-%d %H:%M')}")
            created_label.setStyleSheet("color: #666; font-size: 11px;")
            info_layout.addWidget(created_label)

            layout.addWidget(info_frame)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #BDBDBD;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _populate_fields(self):
        if self.item:
            self.title_edit.setText(self.item.title)
            self.content_edit.setPlainText(self.item.content)

            index = self.category_combo.findText(self.item.category.value)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
            else:
                self.category_combo.setCurrentText(self.item.category.value)

            self._on_color_selected(self.item.color.value)
        else:
            self._on_color_selected("Purple" if self.item_type == "prompt" else "Blue")

    def _on_color_selected(self, color_name: str):
        self.selected_color = color_name
        for name, btn in self.color_buttons.items():
            btn.set_selected(name == color_name)

    def _on_save(self):
        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText().strip()

        if not title:
            title = content[:80] if content else "Untitled"

        category_text = self.category_combo.currentText()
        try:
            category = CategoryType(category_text)
        except ValueError:
            category = CategoryType.UNCATEGORIZED

        try:
            color = ColorLabel(self.selected_color)
        except ValueError:
            color = ColorLabel.PURPLE if self.item_type == "prompt" else ColorLabel.BLUE

        now = datetime.now()

        if self.item_type == "prompt":
            self.result_item = PromptItem(
                id=self.item.id if self.item else None,
                title=title,
                content=content,
                category=category,
                color=color,
                display_order=self.item.display_order if self.item else 0,
                created_at=self.item.created_at if self.item else now,
                updated_at=now
            )
        else:
            import hashlib
            content_hash = self.item.content_hash if self.item else hashlib.sha256(content.encode()).hexdigest()

            self.result_item = ResponseItem(
                id=self.item.id if self.item else None,
                title=title,
                content=content,
                category=category,
                color=color,
                platform=self.item.platform if self.item else None,
                tab_id=self.item.tab_id if self.item else None,
                content_hash=content_hash,
                display_order=self.item.display_order if self.item else 0,
                created_at=self.item.created_at if self.item else now,
                updated_at=now
            )

        self.accept()

    def get_result(self):
        return self.result_item
