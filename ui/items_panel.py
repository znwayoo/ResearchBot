"""Items panel widget with filtering and flow layout for pills."""

from typing import List

from PyQt6.QtCore import Qt, pyqtSignal, QRect, QTimer, QPropertyAnimation, QPoint, QEasingCurve
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QColor, QPen, QPolygon
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QStyle,
    QStyleOptionComboBox,
)

from config import COLOR_PALETTE, DARK_THEME, DEFAULT_CATEGORIES
from ui.item_button import ItemButton


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
        arrow_x = self.width() - 18
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

        from PyQt6.QtCore import QPoint
        polygon = QPolygon([QPoint(x, y) for x, y in points])
        painter.drawPolygon(polygon)
        painter.end()


class DropPlaceholder(QFrame):
    """Ghost placeholder showing where a dragged item will be placed."""

    def __init__(self, width: int = 150, height: int = 36, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.1);
                border: 2px dashed #FFFFFF;
                border-radius: 6px;
            }
        """)


class ItemsPanel(QWidget):
    """Scrollable panel with filters for prompt/response/summary pills."""

    itemClicked = pyqtSignal(object)  # For editing (double click)
    selectionChanged = pyqtSignal(list)  # List of selected items
    deleteRequested = pyqtSignal(object)  # Single item delete
    deleteSelectedRequested = pyqtSignal(list)  # Bulk delete
    orderChanged = pyqtSignal(object, int)  # Item moved to new position
    exportRequested = pyqtSignal(list)  # Export selected items

    def __init__(self, item_type: str = "prompt", storage=None, parent=None):
        super().__init__(parent)
        self.item_type = item_type
        self.storage = storage
        self.items: List = []
        self.item_buttons: List[ItemButton] = []
        self.selected_items: List = []

        # Drag state - SortableJS-inspired
        self._dragged_item = None
        self._dragged_button = None
        self._drop_placeholder = None
        self._drop_target_index = -1
        self._original_index = -1
        self._animations = []
        self._captured_positions = {}  # Store positions before animation
        self._last_swap_index = -1  # Prevent jittery swaps
        self._swap_threshold = 0.55  # 55% threshold like SortableJS
        self._last_direction = 0  # Track drag direction

        # Dynamic sizing for 2 columns
        self._num_columns = 2
        self._pill_spacing = 8
        self._pill_margin = 8
        self._pill_height = 36
        self._pill_width = 200  # Default, will be recalculated

        self._setup_ui()
        self.setAcceptDrops(True)

    def _get_filter_combo_style(self, min_width: int) -> str:
        """Get consistent combo box styling for filters."""
        return f"""
            QComboBox {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                padding: 5px 24px 5px 10px;
                min-width: {min_width}px;
                font-size: 11px;
            }}
            QComboBox:hover {{
                border-color: {DARK_THEME['text_secondary']};
            }}
            QComboBox:on {{
                border-color: {DARK_THEME['accent']};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border: none;
                background: transparent;
                margin-right: 4px;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 10px;
                height: 10px;
                border: none;
                background: transparent;
            }}
            QComboBox QAbstractItemView {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                outline: none;
                padding: 2px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 6px 10px;
                border-radius: 3px;
                margin: 1px 2px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {DARK_THEME['surface_light']};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {DARK_THEME['accent']};
                color: white;
            }}
        """

    def _setup_ui(self):
        self.setStyleSheet(f"background-color: {DARK_THEME['background']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        filter_frame = QFrame()
        filter_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DARK_THEME['surface']};
                border-radius: 4px;
            }}
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(8, 6, 8, 6)
        filter_layout.setSpacing(8)

        cat_label = QLabel("Category:")
        cat_label.setStyleSheet(f"font-size: 11px; color: {DARK_THEME['text_secondary']};")
        filter_layout.addWidget(cat_label)

        self.category_filter = ArrowComboBox()
        self.category_filter.addItem("All")
        self.category_filter.addItems(DEFAULT_CATEGORIES)
        if self.storage:
            custom_cats = self.storage.get_custom_categories()
            for cat in custom_cats:
                if cat not in DEFAULT_CATEGORIES:
                    self.category_filter.addItem(cat)
        self.category_filter.setStyleSheet(self._get_filter_combo_style(140))
        self.category_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.category_filter)

        color_label = QLabel("Color:")
        color_label.setStyleSheet(f"font-size: 11px; color: {DARK_THEME['text_secondary']};")
        filter_layout.addWidget(color_label)

        self.color_filter = ArrowComboBox()
        self.color_filter.addItem("All")
        for color_name in COLOR_PALETTE.keys():
            self.color_filter.addItem(color_name)
        self.color_filter.setStyleSheet(self._get_filter_combo_style(80))
        self.color_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.color_filter)

        filter_layout.addStretch()

        self.selection_label = QLabel("")
        self.selection_label.setStyleSheet(f"font-size: 11px; color: {DARK_THEME['accent']}; font-weight: bold;")
        filter_layout.addWidget(self.selection_label)

        # Delete button - only shown when items are selected
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setFixedHeight(24)
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['error']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 2px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #D32F2F;
            }}
        """)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.delete_btn.hide()  # Hidden by default
        filter_layout.addWidget(self.delete_btn)

        # Export button
        self.export_btn = QPushButton("Export")
        self.export_btn.setFixedHeight(24)
        self.export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                padding: 2px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent']};
                border-color: {DARK_THEME['accent']};
            }}
        """)
        self.export_btn.clicked.connect(self._on_export)
        filter_layout.addWidget(self.export_btn)

        self.count_label = QLabel("0 items")
        self.count_label.setStyleSheet(f"font-size: 11px; color: {DARK_THEME['text_secondary']};")
        filter_layout.addWidget(self.count_label)

        layout.addWidget(filter_frame)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {DARK_THEME['background']};
            }}
            QScrollBar:vertical {{
                background-color: {DARK_THEME['surface']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {DARK_THEME['border']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {DARK_THEME['text_secondary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet(f"background-color: {DARK_THEME['background']};")

        self.flow_container = QVBoxLayout(self.scroll_content)
        self.flow_container.setContentsMargins(8, 8, 8, 8)
        self.flow_container.setSpacing(6)
        self.flow_container.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

    def set_items(self, items: List):
        self.items = items
        self._rebuild_buttons()

    def add_item(self, item):
        self.items.append(item)
        self._rebuild_buttons()

    def remove_item(self, item):
        for i, existing in enumerate(self.items):
            if existing.id == item.id:
                self.items.pop(i)
                break

        if item in self.selected_items:
            self.selected_items.remove(item)
            self._update_selection_label()
            self.selectionChanged.emit(self.selected_items)

        self._rebuild_buttons()

    def update_item(self, item):
        for i, existing in enumerate(self.items):
            if existing.id == item.id:
                self.items[i] = item
                break
        self._rebuild_buttons()

    def _rebuild_buttons(self):
        while self.flow_container.count():
            item = self.flow_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        self.item_buttons.clear()

        # Calculate pill width based on container width
        self._calculate_pill_width()

        current_row = QHBoxLayout()
        current_row.setSpacing(self._pill_spacing)
        current_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        column_count = 0

        for item in self.items:
            btn = ItemButton(item)
            btn.setFixedSize(self._pill_width, self._pill_height)
            btn.doubleClicked.connect(self._on_item_double_clicked)
            btn.selectionChanged.connect(self._on_selection_changed)
            btn.deleteRequested.connect(self._on_delete_requested)
            btn.dragStarted.connect(self._on_drag_started)

            if item in self.selected_items:
                btn.set_selected(True)

            self.item_buttons.append(btn)

            if column_count >= self._num_columns:
                self.flow_container.addLayout(current_row)
                current_row = QHBoxLayout()
                current_row.setSpacing(self._pill_spacing)
                current_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
                column_count = 0

            current_row.addWidget(btn)
            column_count += 1

        if current_row.count() > 0:
            current_row.addStretch()
            self.flow_container.addLayout(current_row)

        self.flow_container.addStretch()
        self._apply_filters()

    def _calculate_pill_width(self):
        """Calculate pill width based on available container width for 2 columns."""
        # Get width from scroll area viewport
        available_width = 0
        try:
            available_width = self.scroll_area.viewport().width()
        except:
            pass

        if available_width < 100:
            available_width = self.width()

        if available_width < 100:
            available_width = 600  # Default fallback

        # Subtract margins and scrollbar space
        available_width = available_width - (self._pill_margin * 2) - 12

        # Calculate width for 2 columns with spacing
        total_spacing = self._pill_spacing * (self._num_columns - 1)
        self._pill_width = int((available_width - total_spacing) / self._num_columns)

        # Ensure reasonable bounds for 2 columns
        self._pill_width = max(150, min(400, self._pill_width))

    def resizeEvent(self, event):
        """Recalculate pill sizes when container is resized."""
        super().resizeEvent(event)
        # Delay rebuild slightly to avoid issues during resize
        if self.items and not self._dragged_item:
            old_pill_width = self._pill_width
            self._calculate_pill_width()
            # Only rebuild if pill width actually changed significantly
            if abs(self._pill_width - old_pill_width) > 5:
                QTimer.singleShot(100, self._rebuild_buttons)

    def showEvent(self, event):
        """Recalculate when widget becomes visible."""
        super().showEvent(event)
        if self.items:
            QTimer.singleShot(50, self._rebuild_buttons)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _on_item_double_clicked(self, item):
        self.itemClicked.emit(item)

    def _on_selection_changed(self, item, selected: bool):
        if selected:
            if item not in self.selected_items:
                self.selected_items.append(item)
        else:
            if item in self.selected_items:
                self.selected_items.remove(item)

        self._update_selection_label()
        self.selectionChanged.emit(self.selected_items)

    def _update_selection_label(self):
        count = len(self.selected_items)
        if count > 0:
            self.selection_label.setText(f"{count} selected")
            self.delete_btn.show()
        else:
            self.selection_label.setText("")
            self.delete_btn.hide()

    def _on_delete_requested(self, item):
        self.deleteRequested.emit(item)

    def _on_export(self):
        """Handle export button click."""
        if self.selected_items:
            self.exportRequested.emit(self.selected_items.copy())
        else:
            # Export all items if none selected
            self.exportRequested.emit(self.items.copy())

    def _apply_filters(self):
        category_filter = self.category_filter.currentText()
        color_filter = self.color_filter.currentText()

        visible_count = 0
        for btn in self.item_buttons:
            item = btn.item
            visible = True

            if category_filter != "All":
                item_category = item.category if isinstance(item.category, str) else item.category.value
                if item_category != category_filter:
                    visible = False

            if color_filter != "All":
                item_color = item.color if isinstance(item.color, str) else item.color.value
                if item_color != color_filter:
                    visible = False

            btn.setVisible(visible)
            if visible:
                visible_count += 1

        self.count_label.setText(f"{visible_count} items")

    def get_selected_items(self) -> List:
        return self.selected_items.copy()

    def clear_selection(self):
        for btn in self.item_buttons:
            btn.set_selected(False)
        self.selected_items.clear()
        self._update_selection_label()
        self.selectionChanged.emit([])

    def refresh(self):
        self._rebuild_buttons()

    def refresh_categories(self):
        """Refresh the category filter dropdown with latest categories."""
        current = self.category_filter.currentText()
        self.category_filter.clear()
        self.category_filter.addItem("All")
        self.category_filter.addItems(DEFAULT_CATEGORIES)

        if self.storage:
            custom_cats = self.storage.get_custom_categories()
            for cat in custom_cats:
                if cat not in DEFAULT_CATEGORIES:
                    self.category_filter.addItem(cat)

        # Restore previous selection if still valid
        index = self.category_filter.findText(current)
        if index >= 0:
            self.category_filter.setCurrentIndex(index)
        else:
            self.category_filter.setCurrentIndex(0)  # Default to "All"

    def delete_selected(self):
        """Request deletion of all selected items."""
        if self.selected_items:
            self.deleteSelectedRequested.emit(self.selected_items.copy())

    def _on_drag_started(self, item):
        """Handle drag start - capture animation state like SortableJS."""
        self._dragged_item = item
        self._animations = []
        self._last_swap_index = -1
        self._last_direction = 0

        # Capture current positions of all buttons (SortableJS captureAnimationState)
        self._captured_positions = {}
        for btn in self.item_buttons:
            self._captured_positions[btn] = btn.pos()

        for i, btn in enumerate(self.item_buttons):
            if btn.item.id == item.id:
                self._dragged_button = btn
                self._original_index = i
                self._drop_target_index = i

                # Create ghost placeholder with same size as pills
                self._create_drop_placeholder()
                self._drop_placeholder.move(btn.pos())
                self._drop_placeholder.show()
                self._drop_placeholder.raise_()

                # Hide the dragged button
                btn.hide()
                break

    def _create_drop_placeholder(self):
        """Create the drop placeholder widget with same size as pills."""
        if self._drop_placeholder is None:
            self._drop_placeholder = DropPlaceholder(self._pill_width, self._pill_height, self.scroll_content)
        else:
            self._drop_placeholder.setFixedSize(self._pill_width, self._pill_height)

    def _remove_drop_placeholder(self):
        """Hide and clean up the drop placeholder."""
        # Stop all animations gracefully
        for anim in self._animations:
            anim.stop()
        self._animations = []

        if self._drop_placeholder:
            self._drop_placeholder.hide()

        self._drop_target_index = -1
        self._last_swap_index = -1
        self._captured_positions = {}

        if self._dragged_button:
            self._dragged_button.show()
            self._dragged_button._update_styles()
            self._dragged_button = None

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accept drag if it contains our item data."""
        if event.mimeData().hasFormat("application/x-researchbot-item"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag movement with SortableJS-like swap threshold."""
        if not event.mimeData().hasFormat("application/x-researchbot-item"):
            event.ignore()
            return

        drop_pos = event.position().toPoint()
        target_index = self._find_drop_index_with_threshold(drop_pos)

        # Only animate if target changed and passes threshold check
        if target_index != self._drop_target_index and target_index >= 0:
            self._animate_items_for_drop(target_index)

        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """When drag leaves, restore original positions."""
        if self._original_index is not None and self._original_index >= 0:
            self._animate_items_for_drop(self._original_index)
        event.accept()

    def dropEvent(self, event: QDropEvent):
        """Handle drop - reorder items."""
        if not event.mimeData().hasFormat("application/x-researchbot-item"):
            self._remove_drop_placeholder()
            event.ignore()
            return

        if not self._dragged_item:
            self._remove_drop_placeholder()
            event.ignore()
            return

        target_index = self._drop_target_index
        original_index = self._original_index

        self._remove_drop_placeholder()

        # Reorder if dropped at a different position
        if target_index >= 0 and target_index != original_index:
            self._reorder_item(self._dragged_item, target_index)
        else:
            # Rebuild to restore positions
            self._rebuild_buttons()

        self._dragged_item = None
        self._dragged_button = None
        self._original_index = -1
        event.acceptProposedAction()

    def _find_drop_index_with_threshold(self, pos) -> int:
        """Find drop index using SortableJS-like swap threshold logic."""
        scroll_widget_pos = self.scroll_area.mapFromParent(pos)
        scroll_pos = self.scroll_area.widget().mapFromParent(scroll_widget_pos)

        # Get visible buttons (excluding dragged)
        visible_buttons = [(i, btn) for i, btn in enumerate(self.item_buttons)
                          if btn != self._dragged_button and btn.isVisible()]

        if not visible_buttons:
            return 0

        # Check each button with threshold
        for i, btn in visible_buttons:
            btn_rect = btn.geometry()

            if not btn_rect.contains(scroll_pos):
                continue

            # Calculate position within button (0.0 to 1.0)
            relative_x = (scroll_pos.x() - btn_rect.x()) / btn_rect.width()
            relative_y = (scroll_pos.y() - btn_rect.y()) / btn_rect.height()

            # Determine direction based on original position
            if self._original_index < i:
                # Dragging forward - need to cross threshold from left
                if relative_x > self._swap_threshold:
                    return i
            elif self._original_index > i:
                # Dragging backward - need to cross threshold from right
                if relative_x < (1 - self._swap_threshold):
                    return i
            else:
                return i

            # If within threshold but not crossed, keep current target
            return self._drop_target_index if self._drop_target_index >= 0 else self._original_index

        # Grid-based fallback for empty areas
        cell_width = self._pill_width + self._pill_spacing
        cell_height = self._pill_height + self._pill_spacing

        col = max(0, int((scroll_pos.x() - self._pill_margin) / cell_width))
        row = max(0, int((scroll_pos.y() - self._pill_margin) / cell_height))
        col = min(col, self._num_columns - 1)

        target_index = row * self._num_columns + col
        total_items = len(self.item_buttons)

        return max(0, min(target_index, total_items - 1))

    def _animate_items_for_drop(self, target_index: int):
        """Animate items shifting with SortableJS-like smooth transitions."""
        if not self._drop_placeholder or self._original_index is None:
            return

        # Prevent rapid back-and-forth by checking if we just swapped
        if target_index == self._last_swap_index:
            return

        self._drop_target_index = target_index
        self._last_swap_index = target_index

        # Stop existing animations
        for anim in self._animations:
            anim.stop()
        self._animations = []

        # Calculate grid positions
        pill_width = self._pill_width
        pill_height = self._pill_height
        spacing = self._pill_spacing
        margin = self._pill_margin
        num_cols = self._num_columns

        def get_grid_pos(slot):
            """Get x, y position for a grid slot."""
            row = slot // num_cols
            col = slot % num_cols
            x = margin + col * (pill_width + spacing)
            y = margin + row * (pill_height + spacing)
            return x, y

        # Build list of non-dragged buttons
        other_buttons = [btn for btn in self.item_buttons if btn != self._dragged_button]

        # Assign slots - ghost placeholder takes target_index slot
        ghost_x, ghost_y = get_grid_pos(target_index)

        # Animate ghost placeholder
        ghost_anim = QPropertyAnimation(self._drop_placeholder, b"pos")
        ghost_anim.setDuration(125)  # Slightly faster for responsiveness
        ghost_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        ghost_anim.setEndValue(QPoint(ghost_x, ghost_y))
        ghost_anim.start()
        self._animations.append(ghost_anim)
        self._drop_placeholder.show()
        self._drop_placeholder.raise_()

        # Assign positions to other buttons, skipping the ghost slot
        slot = 0
        for btn in other_buttons:
            # Skip the slot reserved for ghost
            if slot == target_index:
                slot += 1

            target_x, target_y = get_grid_pos(slot)
            current_pos = btn.pos()

            # Only animate if position changed
            if current_pos.x() != target_x or current_pos.y() != target_y:
                anim = QPropertyAnimation(btn, b"pos")
                anim.setDuration(125)
                anim.setEasingCurve(QEasingCurve.Type.OutQuad)
                anim.setEndValue(QPoint(target_x, target_y))
                anim.start()
                self._animations.append(anim)

            slot += 1

    def _reorder_item(self, item, new_index: int):
        """Reorder an item to a new position."""
        old_index = -1
        for i, existing in enumerate(self.items):
            if existing.id == item.id:
                old_index = i
                break

        if old_index == -1 or old_index == new_index:
            return

        self.items.pop(old_index)
        if new_index > old_index:
            new_index -= 1
        self.items.insert(new_index, item)

        for i, it in enumerate(self.items):
            it.display_order = i

        self.orderChanged.emit(item, new_index)
        self._rebuild_buttons()
