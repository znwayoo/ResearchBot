"""Clickable item button widget for prompts and responses."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QVBoxLayout,
)

from config import COLOR_PALETTE


class ItemButton(QFrame):
    """Clickable button representing a prompt or response item."""

    clicked = pyqtSignal(object)
    selectionChanged = pyqtSignal(object, bool)
    deleteRequested = pyqtSignal(object)

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self._selected = False

        self._setup_ui()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _setup_ui(self):
        self.setFixedHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        color_hex = COLOR_PALETTE.get(self.item.color.value, "#9E9E9E")

        self.setStyleSheet(f"""
            ItemButton {{
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-left: 4px solid {color_hex};
                border-radius: 4px;
            }}
            ItemButton:hover {{
                background-color: #F5F5F5;
                border-color: #BDBDBD;
                border-left: 4px solid {color_hex};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self._on_checkbox_changed)
        layout.addWidget(self.checkbox)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title = self.item.title[:60] + "..." if len(self.item.title) > 60 else self.item.title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #333;")
        text_layout.addWidget(self.title_label)

        category_text = self.item.category.value
        self.category_label = QLabel(category_text)
        self.category_label.setStyleSheet("font-size: 10px; color: #666;")
        text_layout.addWidget(self.category_label)

        layout.addLayout(text_layout, 1)

    def _on_checkbox_changed(self, state):
        self._selected = state == Qt.CheckState.Checked.value
        self.selectionChanged.emit(self.item, self._selected)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.pos())
            if not isinstance(child, QCheckBox):
                self.clicked.emit(self.item)
        super().mousePressEvent(event)

    def _show_context_menu(self, position):
        menu = QMenu(self)

        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(lambda: self.clicked.emit(self.item))
        menu.addAction(edit_action)

        menu.addSeparator()

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.deleteRequested.emit(self.item))
        menu.addAction(delete_action)

        menu.exec(self.mapToGlobal(position))

    def is_selected(self) -> bool:
        return self._selected

    def set_selected(self, selected: bool):
        self._selected = selected
        self.checkbox.setChecked(selected)

    def update_item(self, item):
        self.item = item
        color_hex = COLOR_PALETTE.get(item.color.value, "#9E9E9E")
        self.setStyleSheet(f"""
            ItemButton {{
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-left: 4px solid {color_hex};
                border-radius: 4px;
            }}
            ItemButton:hover {{
                background-color: #F5F5F5;
                border-color: #BDBDBD;
                border-left: 4px solid {color_hex};
            }}
        """)

        title = item.title[:60] + "..." if len(item.title) > 60 else item.title
        self.title_label.setText(title)
        self.category_label.setText(item.category.value)
