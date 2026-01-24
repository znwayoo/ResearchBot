"""Sidebar tabs widget for browser views and logs."""

from datetime import datetime
from typing import Dict

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import PLATFORMS


class PlatformTab(QWidget):
    """Widget for a single platform browser tab."""

    launchRequested = pyqtSignal(str)

    def __init__(self, platform: str, url: str, parent=None):
        super().__init__(parent)
        self.platform = platform
        self.url = url

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        self.status_label = QLabel("Not connected")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()

        self.url_label = QLabel(self.url)
        self.url_label.setStyleSheet("color: #999; font-size: 11px;")
        header_layout.addWidget(self.url_label)

        layout.addWidget(header)

        content = QFrame()
        content.setStyleSheet("background-color: #FAFAFA;")
        content_layout = QVBoxLayout(content)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel(self._get_platform_icon())
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(icon_label)

        title_label = QLabel(self.platform.title())
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title_label)

        desc_label = QLabel(
            f"Click the button below to open {self.platform.title()} in a browser window.\n"
            "Log in to your account, then return here to run queries."
        )
        desc_label.setStyleSheet("color: #666; font-size: 13px; margin: 16px;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        content_layout.addWidget(desc_label)

        self.launch_btn = QPushButton(f"Open {self.platform.title()} Browser")
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.launch_btn.clicked.connect(lambda: self.launchRequested.emit(self.platform))
        content_layout.addWidget(self.launch_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #4CAF50; font-size: 12px; margin-top: 12px;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.info_label)

        layout.addWidget(content, 1)

    def _get_platform_icon(self) -> str:
        icons = {
            "gemini": "G",
            "perplexity": "P",
            "chatgpt": "C"
        }
        return icons.get(self.platform, "?")

    def set_status(self, status: str, is_logged_in: bool = False):
        """Update the status label."""
        if is_logged_in:
            self.status_label.setText(f"{status} - Logged in")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 12px;")
            self.info_label.setText("Browser is open and ready")
            self.launch_btn.setText(f"Reopen {self.platform.title()} Browser")
        else:
            self.status_label.setText(status)
            self.status_label.setStyleSheet("color: #FF9800; font-size: 12px;")
            self.info_label.setText("")


class TerminalTab(QWidget):
    """Widget for the terminal/logs tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QFrame()
        header.setStyleSheet("background-color: #263238; padding: 8px;")
        header_layout = QHBoxLayout(header)

        title = QLabel("Terminal / Logs")
        title.setStyleSheet("color: white; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #455A64;
                color: white;
                border-radius: 4px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
        """)
        clear_btn.clicked.connect(self.clear)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
                border: none;
                padding: 8px;
            }
        """)
        layout.addWidget(self.log_output, 1)

    def append_log(self, message: str, level: str = "INFO"):
        """Append a log message."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        colors = {
            "INFO": "#9CDCFE",
            "WARNING": "#DCDCAA",
            "ERROR": "#F48771",
            "SUCCESS": "#4EC9B0"
        }
        color = colors.get(level.upper(), "#D4D4D4")

        formatted = f"[{timestamp}] [{level}] {message}"
        self.log_output.appendPlainText(formatted)

        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear(self):
        """Clear the log output."""
        self.log_output.clear()


class BrowserTabs(QWidget):
    """Tabbed widget containing browser views and terminal."""

    launchBrowserRequested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.platform_tabs: Dict[str, PlatformTab] = {}
        self.terminal_tab = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #CCCCCC;
                background-color: #FAFAFA;
            }
            QTabBar::tab {
                padding: 10px 20px;
                background-color: #F5F5F5;
                border: 1px solid #CCCCCC;
                border-bottom: none;
                margin-right: 2px;
                color: #333;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #FAFAFA;
                border-bottom: 2px solid #2196F3;
                color: #2196F3;
            }
            QTabBar::tab:hover {
                background-color: #E3F2FD;
            }
        """)

        platform_icons = {
            "gemini": "Gemini",
            "perplexity": "Perplexity",
            "chatgpt": "ChatGPT"
        }

        for platform, url in PLATFORMS.items():
            tab = PlatformTab(platform, url)
            tab.launchRequested.connect(self._on_launch_requested)
            self.platform_tabs[platform] = tab
            self.tabs.addTab(tab, platform_icons.get(platform, platform.title()))

        self.terminal_tab = TerminalTab()
        self.tabs.addTab(self.terminal_tab, "Terminal")

        layout.addWidget(self.tabs)

    def _on_launch_requested(self, platform: str):
        """Handle browser launch request from platform tab."""
        self.launchBrowserRequested.emit(platform)

    def append_log(self, message: str, level: str = "INFO"):
        """Append a log message to the terminal."""
        if self.terminal_tab:
            self.terminal_tab.append_log(message, level)

    def set_platform_status(self, platform: str, status: str, is_logged_in: bool = False):
        """Set the status for a platform tab."""
        if platform in self.platform_tabs:
            self.platform_tabs[platform].set_status(status, is_logged_in)

    def show_platform_tab(self, platform: str):
        """Switch to a specific platform tab."""
        if platform in self.platform_tabs:
            index = list(self.platform_tabs.keys()).index(platform)
            self.tabs.setCurrentIndex(index)

    def show_terminal(self):
        """Switch to the terminal tab."""
        self.tabs.setCurrentIndex(len(self.platform_tabs))

    def clear_logs(self):
        """Clear the terminal logs."""
        if self.terminal_tab:
            self.terminal_tab.clear()
