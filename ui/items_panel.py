"""Items panel widget with filtering and drag-and-drop support."""

from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from config import COLOR_PALETTE, DEFAULT_CATEGORIES
from ui.item_button import ItemButton
from utils.models import CategoryType, ColorLabel, PromptItem, ResponseItem


class ItemsPanel(QWidget):
    """Scrollable panel with filters for prompt/response items."""

    itemClicked = pyqtSignal(object)
    selectionChanged = pyqtSignal(list)
    deleteRequested = pyqtSignal(object)
    orderChanged = pyqtSignal(object, int)

    def __init__(self, item_type: str = "prompt", parent=None):
        super().__init__(parent)
        self.item_type = item_type
        self.items: List = []
        self.item_buttons: List[ItemButton] = []
        self.selected_items: List = []

        self._drag_start_pos = None
        self._dragged_item = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(8, 4, 8, 4)
        filter_layout.setSpacing(8)

        cat_label = QLabel("Category:")
        cat_label.setStyleSheet("font-size: 11px; color: #666;")
        filter_layout.addWidget(cat_label)

        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.addItems(DEFAULT_CATEGORIES)
        self.category_filter.setStyleSheet("""
            QComboBox {
                border: 1px solid #CCC;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 150px;
                font-size: 11px;
            }
        """)
        self.category_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.category_filter)

        color_label = QLabel("Color:")
        color_label.setStyleSheet("font-size: 11px; color: #666;")
        filter_layout.addWidget(color_label)

        self.color_filter = QComboBox()
        self.color_filter.addItem("All Colors")
        for color_name in COLOR_PALETTE.keys():
            self.color_filter.addItem(color_name)
        self.color_filter.setStyleSheet("""
            QComboBox {
                border: 1px solid #CCC;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 100px;
                font-size: 11px;
            }
        """)
        self.color_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.color_filter)

        filter_layout.addStretch()

        self.count_label = QLabel("0 items")
        self.count_label.setStyleSheet("font-size: 11px; color: #666;")
        filter_layout.addWidget(self.count_label)

        layout.addWidget(filter_frame)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(4)
        self.scroll_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

    def set_items(self, items: List):
        self.items = items
        self._rebuild_buttons()

    def add_item(self, item):
        self.items.append(item)
        self._add_button(item)
        self._update_count()

    def remove_item(self, item):
        for i, existing in enumerate(self.items):
            if existing.id == item.id:
                self.items.pop(i)
                break

        for btn in self.item_buttons:
            if btn.item.id == item.id:
                self.scroll_layout.removeWidget(btn)
                btn.deleteLater()
                self.item_buttons.remove(btn)
                break

        if item in self.selected_items:
            self.selected_items.remove(item)
            self.selectionChanged.emit(self.selected_items)

        self._update_count()

    def update_item(self, item):
        for i, existing in enumerate(self.items):
            if existing.id == item.id:
                self.items[i] = item
                break

        for btn in self.item_buttons:
            if btn.item.id == item.id:
                btn.update_item(item)
                break

        self._apply_filters()

    def _rebuild_buttons(self):
        for btn in self.item_buttons:
            self.scroll_layout.removeWidget(btn)
            btn.deleteLater()
        self.item_buttons.clear()
        self.selected_items.clear()

        for item in self.items:
            self._add_button(item)

        self._apply_filters()
        self._update_count()

    def _add_button(self, item):
        btn = ItemButton(item)
        btn.clicked.connect(self._on_item_clicked)
        btn.selectionChanged.connect(self._on_selection_changed)
        btn.deleteRequested.connect(self._on_delete_requested)

        self.item_buttons.append(btn)
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, btn)

    def _on_item_clicked(self, item):
        self.itemClicked.emit(item)

    def _on_selection_changed(self, item, selected: bool):
        if selected:
            if item not in self.selected_items:
                self.selected_items.append(item)
        else:
            if item in self.selected_items:
                self.selected_items.remove(item)

        self.selectionChanged.emit(self.selected_items)

    def _on_delete_requested(self, item):
        self.deleteRequested.emit(item)

    def _apply_filters(self):
        category_filter = self.category_filter.currentText()
        color_filter = self.color_filter.currentText()

        visible_count = 0
        for btn in self.item_buttons:
            item = btn.item
            visible = True

            if category_filter != "All Categories":
                if item.category.value != category_filter:
                    visible = False

            if color_filter != "All Colors":
                if item.color.value != color_filter:
                    visible = False

            btn.setVisible(visible)
            if visible:
                visible_count += 1

        self.count_label.setText(f"{visible_count} items")

    def _update_count(self):
        visible_count = sum(1 for btn in self.item_buttons if btn.isVisible())
        self.count_label.setText(f"{visible_count} items")

    def get_selected_items(self) -> List:
        return self.selected_items.copy()

    def clear_selection(self):
        for btn in self.item_buttons:
            btn.set_selected(False)
        self.selected_items.clear()
        self.selectionChanged.emit([])

    def refresh(self):
        self._apply_filters()

    def reorder_item(self, item, new_index: int):
        for i, existing in enumerate(self.items):
            if existing.id == item.id:
                self.items.pop(i)
                break

        self.items.insert(new_index, item)
        self._rebuild_buttons()
        self.orderChanged.emit(item, new_index)
