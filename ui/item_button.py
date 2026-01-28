"""Clickable item button (pill) widget for prompts, responses, and summaries."""

from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt6.QtGui import QAction, QDrag, QPixmap, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
)

from config import COLOR_PALETTE, DARK_THEME


def get_contrasting_text_color(hex_color: str) -> str:
    """Return white or black text color based on background luminance."""
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#FFFFFF" if luminance < 0.5 else "#1E1E1E"


def lighten_color(hex_color: str, factor: float = 0.2) -> str:
    """Lighten a hex color by a factor."""
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f"#{r:02x}{g:02x}{b:02x}"


class ItemButton(QFrame):
    """Clickable pill representing a prompt, response, or summary item."""

    clicked = pyqtSignal(object)  # Single click - select
    doubleClicked = pyqtSignal(object)  # Double click - edit
    selectionChanged = pyqtSignal(object, bool)
    deleteRequested = pyqtSignal(object)
    dragStarted = pyqtSignal(object)  # Drag initiated

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self._selected = False
        self._drag_start_pos = None

        self._setup_ui()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _get_color_hex(self) -> str:
        """Get the hex color for this item."""
        color_name = self.item.color if isinstance(self.item.color, str) else self.item.color.value
        return COLOR_PALETTE.get(color_name, "#757575")

    def _setup_ui(self):
        self.setFixedHeight(36)
        # Width will be set by parent panel based on container size
        self.setMinimumWidth(100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        color_hex = self._get_color_hex()
        text_color = get_contrasting_text_color(color_hex)
        hover_color = lighten_color(color_hex, 0.15)

        self._color_hex = color_hex
        self._text_color = text_color
        self._hover_color = hover_color

        self._update_styles()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 6, 4)
        layout.setSpacing(4)

        # Truncate title - will be shown with ellipsis via CSS
        max_chars = 28
        title = self.item.title[:max_chars] + "..." if len(self.item.title) > max_chars else self.item.title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {text_color}; background: transparent;")
        layout.addWidget(self.title_label, 1)

        self.edit_btn = QPushButton("...")
        self.edit_btn.setFixedSize(20, 20)
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {text_color};
                border: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.3);
            }}
        """)
        self.edit_btn.clicked.connect(lambda: self.doubleClicked.emit(self.item))
        layout.addWidget(self.edit_btn)

    def _update_styles(self):
        if self._selected:
            self.setStyleSheet(f"""
                ItemButton {{
                    background-color: {self._color_hex};
                    border: 2px solid #FFFFFF;
                    border-radius: 6px;
                }}
                ItemButton:hover {{
                    background-color: {self._hover_color};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                ItemButton {{
                    background-color: {self._color_hex};
                    border: none;
                    border-radius: 6px;
                }}
                ItemButton:hover {{
                    background-color: {self._hover_color};
                }}
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
            self._did_drag = False  # Track if we dragged
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        try:
            if not (event.buttons() & Qt.MouseButton.LeftButton):
                return
            if self._drag_start_pos is None:
                return

            distance = (event.pos() - self._drag_start_pos).manhattanLength()
            if distance < QApplication.startDragDistance():
                return

            self._start_drag()
        except RuntimeError:
            pass  # Widget was deleted

    def _start_drag(self):
        """Start a drag operation."""
        self._did_drag = True  # Mark that we're dragging

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData("application/x-researchbot-item", str(self.item.id).encode())
        drag.setMimeData(mime_data)

        # Create a semi-transparent pixmap of the button for the drag cursor
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setOpacity(0.7)
        self.render(painter)
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        # Emit signal before starting drag (parent will hide this button and show ghost)
        self.dragStarted.emit(self.item)

        # Execute the drag
        drag.exec(Qt.DropAction.MoveAction)

        # Note: Don't call _update_styles() here - the button may have been
        # deleted during the drag operation when the panel rebuilds

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Only toggle selection if we didn't drag
            if not getattr(self, '_did_drag', False):
                child = self.childAt(event.pos())
                if not isinstance(child, QPushButton):
                    self._toggle_selection()
        self._drag_start_pos = None
        self._did_drag = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = None
            self.doubleClicked.emit(self.item)
        super().mouseDoubleClickEvent(event)

    def _toggle_selection(self):
        self._selected = not self._selected
        self._update_styles()
        self.selectionChanged.emit(self.item, self._selected)

    def _show_context_menu(self, position):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
            }}
            QMenu::item:selected {{
                background-color: {DARK_THEME['surface_light']};
            }}
        """)

        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(lambda: self.doubleClicked.emit(self.item))
        menu.addAction(edit_action)

        select_action = QAction("Deselect" if self._selected else "Select", self)
        select_action.triggered.connect(self._toggle_selection)
        menu.addAction(select_action)

        menu.addSeparator()

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.deleteRequested.emit(self.item))
        menu.addAction(delete_action)

        menu.exec(self.mapToGlobal(position))

    def is_selected(self) -> bool:
        return self._selected

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_styles()

    def update_item(self, item):
        self.item = item

        color_hex = self._get_color_hex()
        text_color = get_contrasting_text_color(color_hex)
        hover_color = lighten_color(color_hex, 0.15)

        self._color_hex = color_hex
        self._text_color = text_color
        self._hover_color = hover_color

        self._update_styles()

        max_chars = 28
        title = item.title[:max_chars] + "..." if len(item.title) > max_chars else item.title
        self.title_label.setText(title)
        self.title_label.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {text_color}; background: transparent;")
        self.edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {text_color};
                border: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.3);
            }}
        """)
