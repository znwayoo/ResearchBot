"""Sidebar tabs widget with embedded browser views and logs."""

from datetime import datetime
from typing import Dict, Optional

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile
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


class PlatformBrowser(QWebEngineView):
    """Embedded browser for a platform."""

    responseReady = pyqtSignal(str)
    pageLoaded = pyqtSignal(str)

    def __init__(self, platform: str, parent=None):
        super().__init__(parent)
        self.platform = platform
        self._setup_browser()

    def _setup_browser(self):
        """Configure the browser."""
        profile = QWebEngineProfile.defaultProfile()
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )

        self.loadFinished.connect(self._on_load_finished)

    def _on_load_finished(self, ok: bool):
        """Handle page load completion."""
        if ok:
            self.pageLoaded.emit(self.platform)

    def navigate(self, url: str):
        """Navigate to a URL."""
        self.setUrl(QUrl(url))

    def execute_js(self, script: str, callback=None):
        """Execute JavaScript on the page."""
        if callback:
            self.page().runJavaScript(script, callback)
        else:
            self.page().runJavaScript(script)

    def fill_input_and_send(self, text: str, callback=None):
        """Fill input field and send query based on platform."""
        escaped_text = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")

        if self.platform == "gemini":
            script = f"""
            (function() {{
                const textarea = document.querySelector('div[contenteditable="true"], rich-textarea textarea, textarea');
                if (textarea) {{
                    if (textarea.tagName === 'TEXTAREA') {{
                        textarea.value = `{escaped_text}`;
                        textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }} else {{
                        textarea.innerText = `{escaped_text}`;
                        textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                    setTimeout(() => {{
                        const sendBtn = document.querySelector('button[aria-label="Send message"], button.send-button, button[mattooltip="Send message"]');
                        if (sendBtn) sendBtn.click();
                    }}, 500);
                    return 'sent';
                }}
                return 'input not found';
            }})();
            """
        elif self.platform == "perplexity":
            script = f"""
            (function() {{
                const textarea = document.querySelector('textarea[placeholder="Ask anything..."], textarea[placeholder="Ask follow-up..."], textarea');
                if (textarea) {{
                    textarea.value = `{escaped_text}`;
                    textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    setTimeout(() => {{
                        const sendBtn = document.querySelector('button[aria-label="Submit"], button[type="submit"]');
                        if (sendBtn) sendBtn.click();
                    }}, 500);
                    return 'sent';
                }}
                return 'input not found';
            }})();
            """
        elif self.platform == "chatgpt":
            script = f"""
            (function() {{
                const textarea = document.querySelector('textarea[id="prompt-textarea"], div[contenteditable="true"][id="prompt-textarea"], textarea');
                if (textarea) {{
                    if (textarea.tagName === 'TEXTAREA') {{
                        textarea.value = `{escaped_text}`;
                    }} else {{
                        textarea.innerText = `{escaped_text}`;
                    }}
                    textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    setTimeout(() => {{
                        const sendBtn = document.querySelector('button[data-testid="send-button"], button[aria-label="Send prompt"]');
                        if (sendBtn && !sendBtn.disabled) sendBtn.click();
                    }}, 500);
                    return 'sent';
                }}
                return 'input not found';
            }})();
            """
        else:
            script = "return 'unknown platform';"

        if callback:
            self.execute_js(script, callback)
        else:
            self.execute_js(script)

    def get_response_text(self, callback):
        """Extract response text from the page."""
        if self.platform == "gemini":
            script = """
            (function() {
                const responses = document.querySelectorAll('message-content, div[class*="response"], div.model-response');
                if (responses.length > 0) {
                    const last = responses[responses.length - 1];
                    return last.innerText || last.textContent || '';
                }
                return '';
            })();
            """
        elif self.platform == "perplexity":
            script = """
            (function() {
                const responses = document.querySelectorAll('div.prose, div[class*="answer"], div[data-testid="response-container"]');
                if (responses.length > 0) {
                    const last = responses[responses.length - 1];
                    return last.innerText || last.textContent || '';
                }
                return '';
            })();
            """
        elif self.platform == "chatgpt":
            script = """
            (function() {
                const responses = document.querySelectorAll('div[data-message-author-role="assistant"], div.agent-turn div[class*="markdown"]');
                if (responses.length > 0) {
                    const last = responses[responses.length - 1];
                    return last.innerText || last.textContent || '';
                }
                return '';
            })();
            """
        else:
            script = "return '';"

        self.execute_js(script, callback)


class PlatformTab(QWidget):
    """Tab containing an embedded browser for a platform."""

    def __init__(self, platform: str, url: str, parent=None):
        super().__init__(parent)
        self.platform = platform
        self.url = url
        self.browser: Optional[PlatformBrowser] = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)

        self.status_label = QLabel("Loading...")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                color: #333;
            }
            QPushButton:hover {
                background-color: #BDBDBD;
            }
        """)
        refresh_btn.clicked.connect(self._refresh_browser)
        header_layout.addWidget(refresh_btn)

        layout.addWidget(header)

        self.browser = PlatformBrowser(self.platform)
        self.browser.pageLoaded.connect(self._on_page_loaded)
        layout.addWidget(self.browser, 1)

        self.browser.navigate(self.url)

    def _refresh_browser(self):
        """Refresh the browser."""
        if self.browser:
            self.browser.reload()

    def _on_page_loaded(self, platform: str):
        """Handle page load."""
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 12px;")

    def set_status(self, status: str, is_ready: bool = False):
        """Update the status label."""
        self.status_label.setText(status)
        if is_ready:
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 12px;")
        else:
            self.status_label.setStyleSheet("color: #FF9800; font-size: 12px;")


class TerminalTab(QWidget):
    """Widget for the terminal/logs tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QFrame()
        header.setStyleSheet("background-color: #263238;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

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
                border: none;
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
        formatted = f"[{timestamp}] [{level}] {message}"
        self.log_output.appendPlainText(formatted)

        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear(self):
        """Clear the log output."""
        self.log_output.clear()


class BrowserTabs(QWidget):
    """Tabbed widget containing embedded browser views and terminal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.platform_tabs: Dict[str, PlatformTab] = {}
        self.terminal_tab: Optional[TerminalTab] = None

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

        platform_names = {
            "gemini": "Gemini",
            "perplexity": "Perplexity",
            "chatgpt": "ChatGPT"
        }

        for platform, url in PLATFORMS.items():
            tab = PlatformTab(platform, url)
            self.platform_tabs[platform] = tab
            self.tabs.addTab(tab, platform_names.get(platform, platform.title()))

        self.terminal_tab = TerminalTab()
        self.tabs.addTab(self.terminal_tab, "Terminal")

        layout.addWidget(self.tabs)

    def get_browser(self, platform: str) -> Optional[PlatformBrowser]:
        """Get the browser for a platform."""
        if platform in self.platform_tabs:
            return self.platform_tabs[platform].browser
        return None

    def append_log(self, message: str, level: str = "INFO"):
        """Append a log message to the terminal."""
        if self.terminal_tab:
            self.terminal_tab.append_log(message, level)

    def set_platform_status(self, platform: str, status: str, is_ready: bool = False):
        """Set the status for a platform tab."""
        if platform in self.platform_tabs:
            self.platform_tabs[platform].set_status(status, is_ready)

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
