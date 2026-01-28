"""Item editor dialog for viewing and editing prompts/responses/summaries."""

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QPolygon
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from config import COLOR_PALETTE, DARK_THEME, DEFAULT_CATEGORIES
from utils.models import PromptItem, ResponseItem, SummaryItem


class ArrowComboBox(QComboBox):
    """ComboBox with a properly rendered down arrow."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def paintEvent(self, event):
        """Custom paint to ensure arrow is visible."""
        super().paintEvent(event)

        # Draw the arrow manually
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Arrow position (right side of combo box)
        arrow_size = 6
        arrow_x = self.width() - 20
        arrow_y = (self.height() - arrow_size) // 2

        # Set color based on state
        if self.view().isVisible():
            color = QColor(DARK_THEME['accent'])
        else:
            color = QColor(DARK_THEME['text_secondary'])

        painter.setPen(QPen(color, 2))
        painter.setBrush(color)

        # Draw triangle pointing down (or up if dropdown is open)
        if self.view().isVisible():
            # Up arrow when open
            points = [
                (arrow_x, arrow_y + arrow_size),
                (arrow_x + arrow_size, arrow_y + arrow_size),
                (arrow_x + arrow_size // 2, arrow_y)
            ]
        else:
            # Down arrow when closed
            points = [
                (arrow_x, arrow_y),
                (arrow_x + arrow_size, arrow_y),
                (arrow_x + arrow_size // 2, arrow_y + arrow_size)
            ]

        polygon = QPolygon([QPoint(x, y) for x, y in points])
        painter.drawPolygon(polygon)
        painter.end()


class ColorButton(QPushButton):
    """Button for selecting a color."""

    def __init__(self, color_name: str, color_hex: str, parent=None):
        super().__init__(parent)
        self.color_name = color_name
        self.color_hex = color_hex
        self.setFixedSize(28, 28)
        self._selected = False
        self._update_style()

    def _update_style(self):
        border = "2px solid #FFFFFF" if self._selected else f"1px solid {DARK_THEME['border']}"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color_hex};
                border: {border};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #AAAAAA;
            }}
        """)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()


class ItemEditorDialog(QDialog):
    """Modal dialog for viewing and editing items."""

    deleteRequested = pyqtSignal(object)

    def __init__(self, item=None, item_type="prompt", storage=None, parent=None):
        super().__init__(parent)
        self.item = item
        self.item_type = item_type
        self.storage = storage
        self.result_item = None
        self.custom_color_hex = None
        self.selected_color = "Purple"

        title_map = {"prompt": "Edit Prompt", "response": "Edit Response", "summary": "Edit Summary"}
        self.setWindowTitle(title_map.get(item_type, "Edit Item"))
        self.setMinimumSize(550, 500)
        self.setModal(True)

        self._setup_ui()
        self._populate_fields()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DARK_THEME['background']};
            }}
            QLabel {{
                color: {DARK_THEME['text_primary']};
            }}
            QLineEdit, QPlainTextEdit {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                padding: 6px;
            }}
            QLineEdit:focus, QPlainTextEdit:focus {{
                border-color: {DARK_THEME['accent']};
            }}
            QComboBox {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 6px;
                padding: 8px 32px 8px 12px;
                min-width: 200px;
                font-size: 13px;
            }}
            QComboBox:hover {{
                border-color: {DARK_THEME['text_secondary']};
            }}
            QComboBox:on {{
                border-color: {DARK_THEME['accent']};
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 24px;
                border: none;
                background: transparent;
                margin-right: 6px;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 12px;
                height: 12px;
                border: none;
                background: transparent;
            }}
            QComboBox QAbstractItemView {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-top: none;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
                outline: none;
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                border-radius: 4px;
                margin: 2px 4px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {DARK_THEME['surface_light']};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {DARK_THEME['accent']};
                color: white;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

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
        self.category_combo = ArrowComboBox()
        self.category_combo.setEditable(False)
        self.category_combo.setMaxVisibleItems(15)

        categories = list(DEFAULT_CATEGORIES)
        if self.storage:
            try:
                custom_cats = self.storage.get_custom_categories()
                for cat in custom_cats:
                    if cat not in categories:
                        categories.append(cat)
            except Exception:
                pass

        for cat in categories:
            self.category_combo.addItem(cat)

        category_layout.addWidget(category_label)
        category_layout.addWidget(self.category_combo, 1)

        manage_cat_btn = QPushButton("...")
        manage_cat_btn.setFixedSize(28, 28)
        manage_cat_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent']};
            }}
        """)
        manage_cat_btn.setToolTip("Manage categories")
        manage_cat_btn.clicked.connect(self._manage_categories)
        category_layout.addWidget(manage_cat_btn)

        layout.addLayout(category_layout)

        color_layout = QHBoxLayout()
        color_label = QLabel("Color:")
        color_label.setFixedWidth(80)
        color_layout.addWidget(color_label)

        self.color_buttons = {}
        color_container = QHBoxLayout()
        color_container.setSpacing(6)
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
        layout.addWidget(self.content_edit, 1)

        if self.item and hasattr(self.item, 'platform') and self.item.platform:
            info_frame = QFrame()
            info_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {DARK_THEME['surface']};
                    border-radius: 4px;
                }}
            """)
            info_layout = QHBoxLayout(info_frame)
            info_layout.setContentsMargins(8, 4, 8, 4)

            platform_label = QLabel(f"Platform: {self.item.platform}")
            platform_label.setStyleSheet(f"color: {DARK_THEME['text_secondary']}; font-size: 11px;")
            info_layout.addWidget(platform_label)

            info_layout.addStretch()

            created_label = QLabel(f"Created: {self.item.created_at.strftime('%Y-%m-%d %H:%M')}")
            created_label.setStyleSheet(f"color: {DARK_THEME['text_secondary']}; font-size: 11px;")
            info_layout.addWidget(created_label)

            layout.addWidget(info_frame)

        button_layout = QHBoxLayout()

        if self.item:
            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DARK_THEME['error']};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 20px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #D32F2F;
                }}
            """)
            delete_btn.clicked.connect(self._on_delete)
            button_layout.addWidget(delete_btn)

        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['border']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['success']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #388E3C;
            }}
        """)
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _populate_fields(self):
        if self.item:
            self.title_edit.setText(self.item.title)
            self.content_edit.setPlainText(self.item.content)

            index = self.category_combo.findText(self.item.category)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
            else:
                self.category_combo.addItem(self.item.category)
                self.category_combo.setCurrentText(self.item.category)

            color = self.item.color if self.item.color in COLOR_PALETTE else "Purple"
            self._on_color_selected(color)
        else:
            default_color = {"prompt": "Purple", "response": "Blue", "summary": "Green"}
            color_name = default_color.get(self.item_type, "Gray")
            self._on_color_selected(color_name)

    def _manage_categories(self):
        """Open dialog to manage custom categories."""
        dialog = CategoryManagerDialog(self.storage, self)
        if dialog.exec():
            self._refresh_categories()

    def _refresh_categories(self):
        """Refresh the category combo box."""
        current = self.category_combo.currentText()
        self.category_combo.clear()

        categories = list(DEFAULT_CATEGORIES)
        if self.storage:
            try:
                custom_cats = self.storage.get_custom_categories()
                for cat in custom_cats:
                    if cat not in categories:
                        categories.append(cat)
            except Exception:
                pass

        for cat in categories:
            self.category_combo.addItem(cat)

        index = self.category_combo.findText(current)
        if index >= 0:
            self.category_combo.setCurrentIndex(index)
        else:
            self.category_combo.setCurrentText(current)

    def _on_color_selected(self, color_name: str):
        self.selected_color = color_name
        for name, btn in self.color_buttons.items():
            btn.set_selected(name == color_name)

    def _on_delete(self):
        if self.item:
            self.deleteRequested.emit(self.item)
            self.reject()

    def _on_save(self):
        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText().strip()

        if not title:
            title = content[:80] if content else "Untitled"

        category_text = self.category_combo.currentText().strip()
        if not category_text:
            category_text = "Uncategorized"

        color = self.selected_color if self.selected_color else "Purple"
        if color not in COLOR_PALETTE:
            color = "Purple" if self.item_type == "prompt" else ("Blue" if self.item_type == "response" else "Green")

        now = datetime.now()

        if self.item_type == "prompt":
            self.result_item = PromptItem(
                id=self.item.id if self.item else None,
                title=title,
                content=content,
                category=category_text,
                color=color,
                display_order=self.item.display_order if self.item else 0,
                created_at=self.item.created_at if self.item else now,
                updated_at=now
            )
        elif self.item_type == "response":
            import hashlib
            content_hash = self.item.content_hash if self.item else hashlib.sha256(content.encode()).hexdigest()

            self.result_item = ResponseItem(
                id=self.item.id if self.item else None,
                title=title,
                content=content,
                category=category_text,
                color=color,
                platform=self.item.platform if self.item else None,
                tab_id=self.item.tab_id if self.item else None,
                content_hash=content_hash,
                display_order=self.item.display_order if self.item else 0,
                created_at=self.item.created_at if self.item else now,
                updated_at=now
            )
        else:
            self.result_item = SummaryItem(
                id=self.item.id if self.item else None,
                title=title,
                content=content,
                category=category_text,
                color=color,
                source_responses=self.item.source_responses if self.item else [],
                platform=self.item.platform if self.item else None,
                display_order=self.item.display_order if self.item else 0,
                created_at=self.item.created_at if self.item else now,
                updated_at=now
            )

        self.accept()

    def get_result(self):
        return self.result_item


class CategoryManagerDialog(QDialog):
    """Dialog for managing custom categories."""

    def __init__(self, storage=None, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.setWindowTitle("Manage Categories")
        self.setMinimumSize(400, 350)
        self.setModal(True)

        self._setup_ui()
        self._load_categories()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DARK_THEME['background']};
            }}
            QLabel {{
                color: {DARK_THEME['text_primary']};
            }}
            QListWidget {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {DARK_THEME['accent']};
                color: white;
            }}
            QListWidget::item:hover {{
                background-color: {DARK_THEME['surface_light']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        header_label = QLabel("Manage Categories")
        header_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {DARK_THEME['text_primary']};")
        layout.addWidget(header_label)

        info_label = QLabel("Default categories cannot be edited or removed. Double-click a custom category to rename it.")
        info_label.setStyleSheet(f"font-size: 11px; color: {DARK_THEME['text_secondary']};")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Add new category row
        add_row = QHBoxLayout()
        self.new_cat_input = QLineEdit()
        self.new_cat_input.setPlaceholderText("New category name...")
        self.new_cat_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {DARK_THEME['accent']};
            }}
        """)
        self.new_cat_input.returnPressed.connect(self._add_category)
        add_row.addWidget(self.new_cat_input, 1)

        add_btn = QPushButton("Add")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['accent']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent_hover']};
            }}
        """)
        add_btn.clicked.connect(self._add_category)
        add_row.addWidget(add_btn)

        layout.addLayout(add_row)

        self.category_list = QListWidget()
        self.category_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.category_list.itemDoubleClicked.connect(self._edit_category)
        layout.addWidget(self.category_list, 1)

        button_layout = QHBoxLayout()

        self.edit_btn = QPushButton("Rename")
        self.edit_btn.setEnabled(False)
        self.edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['accent']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent_hover']};
            }}
            QPushButton:disabled {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_secondary']};
            }}
        """)
        self.edit_btn.clicked.connect(self._edit_category)
        button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Remove")
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['error']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: #D32F2F;
            }}
            QPushButton:disabled {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_secondary']};
            }}
        """)
        self.delete_btn.clicked.connect(self._delete_category)
        button_layout.addWidget(self.delete_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['border']};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _load_categories(self):
        self.category_list.clear()

        for cat in DEFAULT_CATEGORIES:
            item = QListWidgetItem(f"  {cat}  (default)")
            item.setData(Qt.ItemDataRole.UserRole, "default")
            item.setData(Qt.ItemDataRole.UserRole + 1, cat)
            item.setForeground(QColor(DARK_THEME['text_secondary']))
            self.category_list.addItem(item)

        if self.storage:
            try:
                custom_cats = self.storage.get_custom_categories()
                for cat in custom_cats:
                    if cat not in DEFAULT_CATEGORIES:
                        item = QListWidgetItem(f"  {cat}")
                        item.setData(Qt.ItemDataRole.UserRole, "custom")
                        item.setData(Qt.ItemDataRole.UserRole + 1, cat)
                        self.category_list.addItem(item)
            except Exception:
                pass

    def _add_category(self):
        """Add a new custom category."""
        name = self.new_cat_input.text().strip()
        if not name:
            return

        # Check if it already exists
        if name in DEFAULT_CATEGORIES:
            QMessageBox.warning(self, "Error", f"'{name}' is a default category.")
            return

        if self.storage:
            existing = self.storage.get_custom_categories()
            if name in existing:
                QMessageBox.warning(self, "Error", f"'{name}' already exists.")
                return

            try:
                self.storage.add_custom_category(name)
                item = QListWidgetItem(f"  {name}")
                item.setData(Qt.ItemDataRole.UserRole, "custom")
                item.setData(Qt.ItemDataRole.UserRole + 1, name)
                self.category_list.addItem(item)
                self.new_cat_input.clear()
            except Exception:
                QMessageBox.warning(self, "Error", "Failed to add category.")

    def _on_selection_changed(self):
        items = self.category_list.selectedItems()
        if items:
            item = items[0]
            is_custom = item.data(Qt.ItemDataRole.UserRole) == "custom"
            self.edit_btn.setEnabled(is_custom)
            self.delete_btn.setEnabled(is_custom)
        else:
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

    def _edit_category(self):
        items = self.category_list.selectedItems()
        if not items:
            return

        item = items[0]
        if item.data(Qt.ItemDataRole.UserRole) != "custom":
            return

        old_name = item.data(Qt.ItemDataRole.UserRole + 1)
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Category",
            "Enter new name:",
            QLineEdit.EchoMode.Normal,
            old_name
        )

        if ok and new_name.strip() and new_name.strip() != old_name:
            new_name = new_name.strip()
            if self.storage:
                try:
                    self.storage.rename_custom_category(old_name, new_name)
                    item.setText(f"  {new_name}")
                    item.setData(Qt.ItemDataRole.UserRole + 1, new_name)
                except Exception:
                    QMessageBox.warning(self, "Error", "Failed to rename category")

    def _delete_category(self):
        items = self.category_list.selectedItems()
        if not items:
            return

        item = items[0]
        if item.data(Qt.ItemDataRole.UserRole) != "custom":
            return

        cat_name = item.data(Qt.ItemDataRole.UserRole + 1)
        reply = QMessageBox.question(
            self,
            "Remove Category",
            f"Remove category '{cat_name}'?\n\nItems using this category will become 'Uncategorized'.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.storage:
                try:
                    self.storage.delete_custom_category(cat_name)
                    self.category_list.takeItem(self.category_list.row(item))
                except Exception:
                    QMessageBox.warning(self, "Error", "Failed to remove category")
