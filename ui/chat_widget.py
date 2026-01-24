"""Chat widget for displaying conversation history."""

from datetime import datetime
from typing import List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QVBoxLayout,
    QWidget,
)

import pyperclip


class MessageWidget(QFrame):
    """Individual message bubble widget."""

    def __init__(self, text: str, is_user: bool, timestamp: datetime = None):
        super().__init__()
        self.text = text
        self.is_user = is_user
        self.timestamp = timestamp or datetime.now()

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        content_layout = QHBoxLayout()

        if self.is_user:
            content_layout.addStretch()

        bubble = QFrame()
        bubble.setObjectName("messageBubble")

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        bubble_layout.setSpacing(4)

        sender_label = QLabel("You" if self.is_user else "ResearchBot")
        message_label = QLabel(self.text)
        message_label.setWordWrap(True)
        message_label.setTextFormat(Qt.TextFormat.PlainText)
        message_label.setMaximumWidth(500)
        time_label = QLabel(self.timestamp.strftime("%H:%M"))

        if self.is_user:
            bubble.setStyleSheet("""
                QFrame#messageBubble {
                    background-color: #007AFF;
                    border-radius: 12px;
                }
            """)
            sender_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #FFFFFF;")
            message_label.setStyleSheet("color: #FFFFFF; font-size: 13px;")
            time_label.setStyleSheet("font-size: 10px; color: #E0E0E0;")
        else:
            bubble.setStyleSheet("""
                QFrame#messageBubble {
                    background-color: #E5E5EA;
                    border-radius: 12px;
                }
            """)
            sender_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #333333;")
            message_label.setStyleSheet("color: #333333; font-size: 13px;")
            time_label.setStyleSheet("font-size: 10px; color: #666666;")

        bubble_layout.addWidget(sender_label)
        bubble_layout.addWidget(message_label)
        bubble_layout.addWidget(time_label)

        content_layout.addWidget(bubble)

        if not self.is_user:
            content_layout.addStretch()

        layout.addLayout(content_layout)


class ChatWidget(QWidget):
    """Main chat display widget with message history."""

    messageAdded = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages: List[dict] = []

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.message_list = QListWidget()
        self.message_list.setSpacing(4)
        self.message_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.message_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.message_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.message_list.customContextMenuRequested.connect(self._show_context_menu)

        self.message_list.setStyleSheet("""
            QListWidget {
                background-color: #F5F5F5;
                border: none;
            }
            QListWidget::item {
                padding: 0;
                border: none;
            }
            QListWidget::item:selected {
                background-color: transparent;
            }
        """)

        layout.addWidget(self.message_list)

    def add_user_message(self, text: str):
        """Add a user message to the chat."""
        self._add_message(text, is_user=True)

    def add_bot_message(self, text: str):
        """Add a bot message to the chat."""
        self._add_message(text, is_user=False)

    def _add_message(self, text: str, is_user: bool):
        """Add a message to the chat display."""
        timestamp = datetime.now()

        self.messages.append({
            "text": text,
            "is_user": is_user,
            "timestamp": timestamp
        })

        widget = MessageWidget(text, is_user, timestamp)

        item = QListWidgetItem()
        item.setSizeHint(widget.sizeHint())
        self.message_list.addItem(item)
        self.message_list.setItemWidget(item, widget)

        self.message_list.scrollToBottom()

        self.messageAdded.emit(text, is_user)

    def _show_context_menu(self, position):
        """Show context menu for copying messages."""
        item = self.message_list.itemAt(position)
        if not item:
            return

        index = self.message_list.row(item)
        if index >= len(self.messages):
            return

        menu = QMenu(self)

        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(lambda: self._copy_message(index))
        menu.addAction(copy_action)

        menu.exec(self.message_list.mapToGlobal(position))

    def _copy_message(self, index: int):
        """Copy message text to clipboard."""
        if 0 <= index < len(self.messages):
            text = self.messages[index]["text"]
            pyperclip.copy(text)

    def clear_chat(self):
        """Clear all messages from the chat."""
        self.messages.clear()
        self.message_list.clear()

    def get_messages(self) -> List[dict]:
        """Get all messages in the chat."""
        return self.messages.copy()

    def get_last_bot_message(self) -> str:
        """Get the last bot message text."""
        for msg in reversed(self.messages):
            if not msg["is_user"]:
                return msg["text"]
        return ""
