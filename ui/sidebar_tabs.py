"""Sidebar tabs widget with embedded browser views, logs, and markdown notebook."""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer, QEvent
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEngineProfile, QWebEnginePage
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QColor, QFont, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextFormat, QAction, QTextListFormat

from config import CONFIG_DIR, DARK_THEME, PLATFORMS


class BrowserPage(QWebEnginePage):
    """Custom page that handles new window requests and enables PDF viewing."""

    def __init__(self, profile, browser_view, parent=None):
        super().__init__(profile, parent)
        self._browser_view = browser_view
        # Enable PDF viewing and plugins
        settings = self.settings()
        settings.setAttribute(settings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(settings.WebAttribute.PdfViewerEnabled, True)

    def createWindow(self, _window_type):
        """Handle requests to open links in new windows by navigating in the same view."""
        return self._browser_view

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        """Accept all navigation requests. Redirect external links to Google tab for AI platforms."""
        url_str = url.toString()
        platform = self._browser_view.platform

        # For AI platforms, intercept external link clicks and open in Google tab
        if platform != "google" and is_main_frame and nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            platform_domains = {
                "chatgpt": "chat.openai.com",
                "gemini": "gemini.google.com",
                "perplexity": "perplexity.ai",
                "claude": "claude.ai",
            }
            domain = platform_domains.get(platform, "")
            if domain and domain not in url_str:
                self._browser_view.openInGoogleTab.emit(url_str)
                return False

        return True


class PlatformBrowser(QWebEngineView):
    """Embedded browser for a platform."""

    responseReady = pyqtSignal(str)
    pageLoaded = pyqtSignal(str)
    openInGoogleTab = pyqtSignal(str)  # URL to open in Google tab

    # Shared profile for persistent cookies across all browsers
    _shared_profile = None

    def __init__(self, platform: str, parent=None):
        super().__init__(parent)
        self.platform = platform
        self._setup_browser()

    # Class-level list of listeners for download events
    _download_listeners = []
    _download_directory = str(Path.home() / "Downloads")

    @classmethod
    def get_shared_profile(cls):
        """Get or create shared profile with persistent storage."""
        if cls._shared_profile is None:
            storage_path = str(CONFIG_DIR / "browser_data")

            cls._shared_profile = QWebEngineProfile("ResearchBot", None)
            cls._shared_profile.setPersistentStoragePath(storage_path)
            cls._shared_profile.setCachePath(str(CONFIG_DIR / "browser_cache"))
            cls._shared_profile.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
            )

            # Connect download handler so file downloads work
            cls._shared_profile.downloadRequested.connect(cls._on_download_requested)
        return cls._shared_profile

    @classmethod
    def add_download_listener(cls, listener):
        """Register a callback for download events: listener(filename, state)."""
        cls._download_listeners.append(listener)

    @classmethod
    def set_download_directory(cls, path: str):
        """Set the download directory."""
        cls._download_directory = path

    @classmethod
    def get_download_directory(cls) -> str:
        """Get the current download directory."""
        return cls._download_directory

    @classmethod
    def _on_download_requested(cls, download: QWebEngineDownloadRequest):
        """Handle file download requests by saving to the configured folder."""
        downloads_dir = Path(cls._download_directory)
        downloads_dir.mkdir(parents=True, exist_ok=True)

        suggested_name = download.downloadFileName()
        save_path = downloads_dir / suggested_name

        # Avoid overwriting by appending a number
        counter = 1
        stem = save_path.stem
        suffix = save_path.suffix
        while save_path.exists():
            save_path = downloads_dir / f"{stem} ({counter}){suffix}"
            counter += 1

        download.setDownloadDirectory(str(downloads_dir))
        download.setDownloadFileName(save_path.name)

        filename = save_path.name

        # Notify listeners of download start
        for listener in cls._download_listeners:
            listener(filename, "started", 0)

        def on_progress(bytes_received, bytes_total):
            if bytes_total > 0:
                percent = int(bytes_received * 100 / bytes_total)
            else:
                percent = -1  # Unknown total size
            for cb in cls._download_listeners:
                cb(filename, "progress", percent)

        def on_state_changed(state):
            if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                for cb in cls._download_listeners:
                    cb(filename, "completed", 100)
            elif state == QWebEngineDownloadRequest.DownloadState.DownloadCancelled:
                for cb in cls._download_listeners:
                    cb(filename, "cancelled", 0)
            elif state == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
                for cb in cls._download_listeners:
                    cb(filename, "failed", 0)

        download.receivedBytesChanged.connect(
            lambda: on_progress(download.receivedBytes(), download.totalBytes())
        )
        download.stateChanged.connect(on_state_changed)
        download.accept()

    def _setup_browser(self):
        """Configure the browser with persistent storage."""
        profile = self.get_shared_profile()
        page = BrowserPage(profile, self, self)
        self.setPage(page)

        self.loadFinished.connect(self._on_load_finished)

    def _on_load_finished(self, ok: bool):
        """Handle page load completion."""
        if ok:
            self.pageLoaded.emit(self.platform)

    def contextMenuEvent(self, event):
        """Custom right-click context menu."""
        menu = self.createStandardContextMenu()
        actions_to_remove = []
        for action in menu.actions():
            text = action.text().lower()
            # Remove open in new tab/window and view page source
            if any(phrase in text for phrase in [
                "new tab", "new window", "page source", "view source"
            ]):
                actions_to_remove.append(action)

        for action in actions_to_remove:
            menu.removeAction(action)

        # Add "Open in Google Tab" for non-Google platforms if there's a link
        if self.platform != "google":
            last_context = self.page().contextMenuData()
            link_url = last_context.linkUrl()
            if link_url.isValid() and link_url.toString():
                open_google_action = menu.addAction("Open in Google Tab")
                open_google_action.triggered.connect(
                    lambda: self.openInGoogleTab.emit(link_url.toString())
                )

        menu.exec(event.globalPos())

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
        if self.platform == "gemini":
            self._fill_gemini(text, callback)
        elif self.platform == "perplexity":
            self._fill_perplexity(text, callback)
        elif self.platform == "chatgpt":
            self._fill_chatgpt(text, callback)
        elif self.platform == "claude":
            self._fill_claude(text, callback)
        else:
            if callback:
                callback("unknown platform")

    def _fill_gemini(self, text: str, callback=None):
        """Fill and send query for Google Gemini."""
        # Debug: log the text being sent
        print(f"Gemini: Text length: {len(text)}, Full text: {repr(text[:200])}")
        # Escape text for JavaScript string literal - preserve newlines
        escaped_text = (text.replace("\\", "\\\\")
                           .replace("'", "\\'")
                           .replace("\n", "\\n")
                           .replace("\r", "\\r")
                           .replace("</script>", "<\\/script>"))

        # Use a unique ID for this operation
        op_id = f"gemini_{int(time.time() * 1000)}"
        
        # Step 1: Fill the input
        fill_script = f"""
        (function() {{
            try {{
                const selectors = [
                    'div.ql-editor[contenteditable="true"]',
                    'rich-textarea div[contenteditable="true"]',
                    'div[contenteditable="true"][aria-label*="Enter"]',
                    'div[contenteditable="true"][data-placeholder]',
                    'div.ProseMirror[contenteditable="true"]',
                    'div[contenteditable="true"][role="textbox"]',
                    'div[contenteditable="true"]',
                    'textarea[aria-label*="Enter"]',
                    'textarea'
                ];

                let input = null;
                for (const sel of selectors) {{
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {{
                        input = el;
                        console.log('Gemini: Found input with selector:', sel);
                        break;
                    }}
                }}

                if (!input) {{
                    window._geminiResult = 'input not found';
                    return 'input not found';
                }}

                // Focus the element
                input.focus();
                input.click();

                const text = '{escaped_text}';

                if (input.tagName === 'TEXTAREA') {{
                    input.value = text;
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }} else {{
                    // For contenteditable, clear and set content directly
                    input.focus();

                    // Clear and set content directly
                    input.textContent = text;

                    // Move cursor to end
                    const range = document.createRange();
                    const sel = window.getSelection();
                    range.selectNodeContents(input);
                    range.collapse(false);
                    sel.removeAllRanges();
                    sel.addRange(range);

                    // Trigger input events
                    input.dispatchEvent(new InputEvent('input', {{
                        bubbles: true,
                        cancelable: true,
                        inputType: 'insertText',
                        data: text
                    }}));

                    console.log('Gemini: Inserted text length:', input.textContent ? input.textContent.length : 0, 'Expected:', text.length);
                }}

                window._geminiInput = input;
                window._geminiText = text;
                return 'filled';
            }} catch (error) {{
                console.error('Gemini fill error:', error);
                window._geminiResult = 'error: ' + error.message;
                return 'error: ' + error.message;
            }}
        }})();
        """

        def on_fill_result(result):
            # Debug: log the result
            print(f"Gemini fill result: {result}")
            if result and result != 'filled':
                # If there's an error, pass it to callback
                if callback:
                    callback(result)
                return
            
            # Step 2: Wait a bit, then click send
            def click_send():
                send_script = """
                (function() {
                    try {
                        const input = window._geminiInput;
                        if (!input) {
                            return 'no input';
                        }

                        const sendSelectors = [
                            'button[aria-label*="Send message"]',
                            'button[aria-label*="Send"]',
                            'button[data-at="send"]',
                            'button.send-button',
                            'button[mattooltip*="Send"]',
                            'button[jsaction*="send"]',
                            'button[class*="send"]'
                        ];

                        let sendBtn = null;
                        for (const sel of sendSelectors) {
                            const btn = document.querySelector(sel);
                            if (btn && !btn.disabled && btn.offsetParent !== null) {
                                sendBtn = btn;
                                console.log('Gemini: Found send button with selector:', sel);
                                break;
                            }
                        }

                        if (!sendBtn) {
                            const buttons = document.querySelectorAll('button');
                            for (const btn of buttons) {
                                if (btn.querySelector('svg') && !btn.disabled) {
                                    const rect = btn.getBoundingClientRect();
                                    if (rect.bottom > window.innerHeight - 200) {
                                        sendBtn = btn;
                                        console.log('Gemini: Found send button by position');
                                        break;
                                    }
                                }
                            }
                        }

                        if (sendBtn) {
                            console.log('Gemini: Clicking send button');
                            sendBtn.click();
                            return 'sent';
                        } else {
                            console.log('Gemini: No button found, trying Enter key');
                            input.dispatchEvent(new KeyboardEvent('keydown', {
                                key: 'Enter',
                                code: 'Enter',
                                keyCode: 13,
                                which: 13,
                                bubbles: true,
                                cancelable: true
                            }));
                            return 'sent via enter';
                        }
                    } catch (e) {
                        console.error('Gemini send error:', e);
                        return 'error: ' + e.message;
                    }
                })();
                """
                
                def on_send_result(result):
                    print(f"Gemini send result: {result}")
                    if callback:
                        callback(result if result else 'sent')
                
                self.execute_js(send_script, on_send_result)
            
            QTimer.singleShot(500, click_send)

        self.execute_js(fill_script, on_fill_result)

    def _fill_perplexity(self, text: str, callback=None):
        """Fill and send query for Perplexity AI."""
        # Escape text for JavaScript string literal
        escaped_text = (text.replace("\\", "\\\\")
                           .replace("'", "\\'")
                           .replace("\n", "\\n")
                           .replace("\r", "\\r")
                           .replace("</script>", "<\\/script>"))

        # Step 1: Fill the input
        fill_script = f"""
        (function() {{
            try {{
                const selectors = [
                    'textarea[placeholder*="Ask"]',
                    'textarea[placeholder*="ask"]',
                    'textarea[placeholder*="Search"]',
                    'textarea[placeholder*="anything"]',
                    'textarea[placeholder*="follow-up"]',
                    'textarea[class*="overflow"]',
                    'textarea[class*="input"]',
                    'textarea[rows]',
                    'div[contenteditable="true"][role="textbox"]',
                    'div[contenteditable="true"]',
                    'textarea'
                ];

                let textarea = null;
                for (const sel of selectors) {{
                    const elements = document.querySelectorAll(sel);
                    for (const el of elements) {{
                        const style = window.getComputedStyle(el);
                        if (el.offsetParent !== null &&
                            style.display !== 'none' &&
                            style.visibility !== 'hidden') {{
                            textarea = el;
                            console.log('Perplexity: Found input with selector:', sel);
                            break;
                        }}
                    }}
                    if (textarea) break;
                }}

                if (!textarea) {{
                    return 'input not found';
                }}

                const text = '{escaped_text}';

                // Focus the textarea first
                textarea.focus();
                textarea.click();

                // For React apps, use native setter with tracker reset
                if (textarea.tagName === 'TEXTAREA' || textarea.tagName === 'INPUT') {{
                    const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value'
                    ).set;
                    nativeTextAreaValueSetter.call(textarea, text);

                    // Reset React's value tracker to force change detection
                    const tracker = textarea._valueTracker;
                    if (tracker) {{
                        tracker.setValue('');
                    }}

                    // Dispatch input event
                    textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }} else {{
                    // For contenteditable divs
                    textarea.textContent = text;
                    textarea.dispatchEvent(new InputEvent('input', {{
                        bubbles: true,
                        cancelable: true,
                        inputType: 'insertText',
                        data: text
                    }}));
                }}

                console.log('Perplexity: Set text length:', textarea.value ? textarea.value.length : textarea.textContent.length);

                window._perplexityTextarea = textarea;
                window._perplexityForm = textarea.closest('form');
                return 'filled';
            }} catch (error) {{
                console.error('Perplexity fill error:', error);
                return 'error: ' + error.message;
            }}
        }})();
        """

        def on_fill_result(result):
            print(f"Perplexity fill result: {result}")
            if result and result != 'filled':
                if callback:
                    callback(result)
                return

            # Step 2: Wait a bit, then send
            def click_send():
                send_script = """
                (function() {
                    try {
                        const textarea = window._perplexityTextarea;
                        if (!textarea) {
                            return 'no textarea';
                        }

                        textarea.focus();

                        // Try to find and click submit button
                        const form = window._perplexityForm;
                        if (form) {
                            const submitBtn = form.querySelector('button[type="submit"], button[aria-label*="Submit"], button[aria-label*="Send"]');
                            if (submitBtn && !submitBtn.disabled) {
                                submitBtn.click();
                                return 'sent via button';
                            }
                        }

                        // Fallback to Enter key
                        const enterEvent = new KeyboardEvent('keydown', {
                            key: 'Enter',
                            code: 'Enter',
                            keyCode: 13,
                            which: 13,
                            bubbles: true,
                            cancelable: true
                        });
                        textarea.dispatchEvent(enterEvent);

                        return 'sent via enter';
                    } catch (e) {
                        console.error('Perplexity send error:', e);
                        return 'error: ' + e.message;
                    }
                })();
                """

                def on_send_result(result):
                    print(f"Perplexity send result: {result}")
                    if callback:
                        callback(result if result else 'sent')

                self.execute_js(send_script, on_send_result)

            QTimer.singleShot(800, click_send)

        self.execute_js(fill_script, on_fill_result)

    def _fill_chatgpt(self, text: str, callback=None):
        """Fill and send query for ChatGPT."""
        # Escape text for JavaScript string literal
        escaped_text = (text.replace("\\", "\\\\")
                           .replace("'", "\\'")
                           .replace("\n", "\\n")
                           .replace("\r", "\\r")
                           .replace("</script>", "<\\/script>"))

        # Step 1: Fill the input
        fill_script = f"""
        (function() {{
            try {{
                // ChatGPT now uses contenteditable div with id prompt-textarea
                const selectors = [
                    '#prompt-textarea',
                    'div[id="prompt-textarea"]',
                    'div[contenteditable="true"][data-id="root"]',
                    'div[contenteditable="true"][role="textbox"]',
                    'textarea[id="prompt-textarea"]',
                    'textarea[placeholder*="Message"]',
                    'textarea[data-id="root"]'
                ];

                let input = null;
                for (const sel of selectors) {{
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {{
                        input = el;
                        console.log('ChatGPT: Found input with selector:', sel);
                        break;
                    }}
                }}

                if (!input) {{
                    return 'input not found';
                }}

                // Focus the element
                input.focus();
                input.click();

                const text = '{escaped_text}';

                if (input.tagName === 'TEXTAREA') {{
                    // For textarea
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value'
                    ).set;
                    nativeInputValueSetter.call(input, text);
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }} else {{
                    // For contenteditable div (newer ChatGPT UI)
                    input.innerHTML = '';
                    input.focus();

                    // Use execCommand for better compatibility
                    document.execCommand('insertText', false, text);

                    // If that didn't work, set innerHTML directly
                    if (!input.textContent || input.textContent.length < 10) {{
                        // Create paragraph element for proper formatting
                        const p = document.createElement('p');
                        p.textContent = text;
                        input.innerHTML = '';
                        input.appendChild(p);

                        // Dispatch input event
                        input.dispatchEvent(new InputEvent('input', {{
                            bubbles: true,
                            cancelable: true,
                            inputType: 'insertText',
                            data: text
                        }}));
                    }}
                }}

                window._chatgptInput = input;
                console.log('ChatGPT: Filled text length:', input.textContent ? input.textContent.length : (input.value ? input.value.length : 0));
                return 'filled';
            }} catch (error) {{
                console.error('ChatGPT fill error:', error);
                return 'error: ' + error.message;
            }}
        }})();
        """

        def on_fill_result(result):
            print(f"ChatGPT fill result: {result}")
            if result and result != 'filled':
                if callback:
                    callback(result)
                return

            # Step 2: Wait a bit, then click send
            def click_send():
                send_script = """
                (function() {
                    try {
                        const input = window._chatgptInput;
                        if (!input) {
                            return 'no input';
                        }

                        const sendSelectors = [
                            'button[data-testid="send-button"]',
                            'button[aria-label*="Send message"]',
                            'button[aria-label*="Send prompt"]',
                            'button[aria-label*="Send"]',
                            'form button[type="submit"]'
                        ];

                        let sendBtn = null;
                        for (const sel of sendSelectors) {
                            const btn = document.querySelector(sel);
                            if (btn && !btn.disabled && btn.offsetParent !== null) {
                                sendBtn = btn;
                                console.log('ChatGPT: Found send button with selector:', sel);
                                break;
                            }
                        }

                        if (sendBtn) {
                            console.log('ChatGPT: Clicking send button');
                            sendBtn.click();
                            return 'sent';
                        } else {
                            // Try Enter key
                            console.log('ChatGPT: No button found, trying Enter key');
                            input.dispatchEvent(new KeyboardEvent('keydown', {
                                key: 'Enter',
                                code: 'Enter',
                                keyCode: 13,
                                which: 13,
                                bubbles: true,
                                cancelable: true
                            }));
                            return 'sent via enter';
                        }
                    } catch (e) {
                        console.error('ChatGPT send error:', e);
                        return 'error: ' + e.message;
                    }
                })();
                """

                def on_send_result(result):
                    print(f"ChatGPT send result: {result}")
                    if callback:
                        callback(result if result else 'sent')

                self.execute_js(send_script, on_send_result)

            QTimer.singleShot(500, click_send)

        self.execute_js(fill_script, on_fill_result)

    def get_response_text(self, callback):
        """Extract response text from the page."""
        if self.platform == "gemini":
            self._get_gemini_response(callback)
        elif self.platform == "perplexity":
            self._get_perplexity_response(callback)
        elif self.platform == "chatgpt":
            self._get_chatgpt_response(callback)
        elif self.platform == "claude":
            self._get_claude_response(callback)
        else:
            callback('')

    def _get_gemini_response(self, callback):
        """Extract response from Gemini."""
        script = """
        (function() {
            // Gemini response selectors - looking for model/assistant messages
            const selectors = [
                'message-content.model-response-text',
                'model-response message-content',
                'message-content[class*="model"]',
                'div.model-response-text',
                'div[class*="model-response"]',
                'div[class*="response-container"] div[class*="content"]',
                'div[class*="markdown-main-panel"]',
                'div[class*="response-text"]',
                'div.conversation-container div[class*="message-text"]'
            ];

            let responseText = '';

            for (const sel of selectors) {
                const responses = document.querySelectorAll(sel);
                if (responses.length > 0) {
                    // Get the last response (most recent)
                    const last = responses[responses.length - 1];
                    const text = last.innerText || last.textContent || '';
                    if (text.trim().length > responseText.length) {
                        responseText = text.trim();
                    }
                }
            }

            // Also try looking for any response containers
            if (responseText.length < 50) {
                const containers = document.querySelectorAll('[class*="response"], [class*="answer"]');
                for (const container of containers) {
                    const text = container.innerText || container.textContent || '';
                    if (text.trim().length > responseText.length && text.trim().length > 50) {
                        responseText = text.trim();
                    }
                }
            }

            return responseText;
        })();
        """
        self.execute_js(script, callback)

    def _get_perplexity_response(self, callback):
        """Extract response from Perplexity."""
        script = """
        (function() {
            // Perplexity uses prose class for formatted responses
            const selectors = [
                'div.prose',
                'div[class*="prose"]',
                'div[class*="answer-text"]',
                'div[class*="markdown"]',
                'div[class*="response-content"]',
                'article div[class*="prose"]',
                'div[class*="result-content"]'
            ];

            let responseText = '';

            for (const sel of selectors) {
                const responses = document.querySelectorAll(sel);
                if (responses.length > 0) {
                    // Get the last response
                    const last = responses[responses.length - 1];
                    const text = last.innerText || last.textContent || '';
                    if (text.trim().length > responseText.length) {
                        responseText = text.trim();
                    }
                }
            }

            // Try to find the main answer container
            if (responseText.length < 50) {
                // Look for answer sections
                const answerDivs = document.querySelectorAll('[class*="answer"], [class*="response"]');
                for (const div of answerDivs) {
                    const text = div.innerText || div.textContent || '';
                    // Filter out input areas and short text
                    if (text.trim().length > 100 && text.trim().length > responseText.length) {
                        // Make sure this isn't an input field container
                        if (!div.querySelector('textarea') && !div.querySelector('input')) {
                            responseText = text.trim();
                        }
                    }
                }
            }

            return responseText;
        })();
        """
        self.execute_js(script, callback)

    def _get_chatgpt_response(self, callback):
        """Extract response from ChatGPT."""
        script = """
        (function() {
            // ChatGPT uses data-message-author-role attribute
            const selectors = [
                'div[data-message-author-role="assistant"]',
                'div[data-message-author-role="assistant"] div.markdown',
                'div.agent-turn div.markdown',
                'div[class*="markdown"][class*="prose"]',
                'div.message-content',
                'article[data-testid*="conversation-turn"] div[class*="markdown"]'
            ];

            let responseText = '';

            for (const sel of selectors) {
                const responses = document.querySelectorAll(sel);
                if (responses.length > 0) {
                    // Get the last response
                    const last = responses[responses.length - 1];
                    const text = last.innerText || last.textContent || '';
                    if (text.trim().length > responseText.length) {
                        responseText = text.trim();
                    }
                }
            }

            // Also look for assistant message containers
            if (responseText.length < 50) {
                const messages = document.querySelectorAll('[data-message-author-role="assistant"]');
                if (messages.length > 0) {
                    const last = messages[messages.length - 1];
                    const text = last.innerText || last.textContent || '';
                    if (text.trim().length > responseText.length) {
                        responseText = text.trim();
                    }
                }
            }

            return responseText;
        })();
        """
        self.execute_js(script, callback)

    def check_if_generating(self, callback):
        """Check if the AI is still generating a response."""
        if self.platform == "gemini":
            script = """
            (function() {
                // Check for loading/generating indicators in Gemini
                const loading = document.querySelector('mat-spinner, .loading, div[class*="loading"], div[class*="generating"]');
                const stopBtn = document.querySelector('button[aria-label*="Stop"], button[class*="stop"]');
                return loading !== null || stopBtn !== null;
            })();
            """
        elif self.platform == "perplexity":
            script = """
            (function() {
                // Check for loading indicators in Perplexity
                const loading = document.querySelector('div[class*="loading"], div[class*="generating"], svg[class*="animate"]');
                const stopBtn = document.querySelector('button[aria-label*="Stop"]');
                return loading !== null || stopBtn !== null;
            })();
            """
        elif self.platform == "chatgpt":
            script = """
            (function() {
                // Check for loading indicators in ChatGPT
                const loading = document.querySelector('div[class*="result-streaming"], button[aria-label*="Stop"]');
                const stopBtn = document.querySelector('button[data-testid="stop-button"]');
                return loading !== null || stopBtn !== null;
            })();
            """
        elif self.platform == "claude":
            script = """
            (function() {
                // Check for loading indicators in Claude
                const loading = document.querySelector('div[class*="streaming"], button[aria-label*="Stop"]');
                const stopBtn = document.querySelector('button[data-testid="stop-button"], button[class*="stop"]');
                return loading !== null || stopBtn !== null;
            })();
            """
        else:
            script = "return false;"

        self.execute_js(script, callback)

    def navigate_to_new_chat(self, callback=None):
        """Navigate to a new chat page for the platform."""
        new_chat_scripts = {
            "gemini": """
                (function() {
                    // Try to click "New chat" button if available
                    const newChatBtn = document.querySelector('button[aria-label*="New chat"], a[href*="new"]');
                    if (newChatBtn) {
                        newChatBtn.click();
                        return 'clicked new chat button';
                    }
                    return 'no button found';
                })();
            """,
            "perplexity": """
                (function() {
                    // Skip - _fill_perplexity will handle refresh
                    return 'skipped - will refresh during fill';
                })();
            """,
            "chatgpt": """
                (function() {
                    // Try to click "New chat" button
                    const newChatBtn = document.querySelector('nav a[href="/"], button[data-testid*="new"]');
                    if (newChatBtn) {
                        newChatBtn.click();
                        return 'clicked new chat button';
                    }
                    return 'no button found';
                })();
            """
        }

        if self.platform in new_chat_scripts:
            def on_result(result):
                print(f"{self.platform}: New chat result: {result}")
                if callback:
                    callback(result)
            self.execute_js(new_chat_scripts[self.platform], on_result)
        elif callback:
            callback("unknown platform")

    def debug_page_elements(self, callback):
        """Debug helper to see what elements are available on the page."""
        script = """
        (function() {
            const info = {
                url: window.location.href,
                textareas: document.querySelectorAll('textarea').length,
                contentEditables: document.querySelectorAll('[contenteditable="true"]').length,
                buttons: document.querySelectorAll('button').length
            };

            // Try to find input-like elements
            const inputSelectors = ['textarea', '[contenteditable="true"]'];
            info.inputs = [];
            for (const sel of inputSelectors) {
                document.querySelectorAll(sel).forEach((el, i) => {
                    if (i < 3) {
                        info.inputs.push({
                            selector: sel,
                            placeholder: el.placeholder || el.getAttribute('aria-label') || '',
                            id: el.id || ''
                        });
                    }
                });
            }

            return JSON.stringify(info);
        })();
        """
        self.execute_js(script, callback)

    def fill_input_only(self, text: str, callback=None):
        """Fill input field without submitting, based on platform."""
        if self.platform == "gemini":
            self._fill_only_gemini(text, callback)
        elif self.platform == "perplexity":
            self._fill_only_perplexity(text, callback)
        elif self.platform == "chatgpt":
            self._fill_only_chatgpt(text, callback)
        elif self.platform == "claude":
            self._fill_only_claude(text, callback)
        else:
            if callback:
                callback("unknown platform")

    def _fill_only_gemini(self, text: str, callback=None):
        """Fill input for Gemini without sending."""
        escaped_text = (text.replace("\\", "\\\\")
                           .replace("'", "\\'")
                           .replace("\n", "\\n")
                           .replace("\r", "\\r")
                           .replace("</script>", "<\\/script>"))

        fill_script = f"""
        (function() {{
            try {{
                const selectors = [
                    'div.ql-editor[contenteditable="true"]',
                    'rich-textarea div[contenteditable="true"]',
                    'div[contenteditable="true"][aria-label*="Enter"]',
                    'div[contenteditable="true"][data-placeholder]',
                    'div.ProseMirror[contenteditable="true"]',
                    'div[contenteditable="true"][role="textbox"]',
                    'div[contenteditable="true"]',
                    'textarea[aria-label*="Enter"]',
                    'textarea'
                ];

                let input = null;
                for (const sel of selectors) {{
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {{
                        input = el;
                        break;
                    }}
                }}

                if (!input) {{
                    return 'input not found';
                }}

                input.focus();
                input.click();

                const text = '{escaped_text}';

                if (input.tagName === 'TEXTAREA') {{
                    input.value = text;
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }} else {{
                    // Clear and set content directly
                    input.textContent = text;

                    // Move cursor to end
                    const range = document.createRange();
                    const sel = window.getSelection();
                    range.selectNodeContents(input);
                    range.collapse(false);
                    sel.removeAllRanges();
                    sel.addRange(range);

                    input.dispatchEvent(new InputEvent('input', {{
                        bubbles: true,
                        cancelable: true,
                        inputType: 'insertText',
                        data: text
                    }}));
                }}

                return 'filled';
            }} catch (error) {{
                return 'error: ' + error.message;
            }}
        }})();
        """
        self.execute_js(fill_script, callback)

    def _fill_only_perplexity(self, text: str, callback=None):
        """Fill input for Perplexity without sending."""
        escaped_text = (text.replace("\\", "\\\\")
                           .replace("'", "\\'")
                           .replace("\n", "\\n")
                           .replace("\r", "\\r")
                           .replace("</script>", "<\\/script>"))

        fill_script = f"""
        (function() {{
            try {{
                const selectors = [
                    'textarea[placeholder*="Ask"]',
                    'textarea[placeholder*="ask"]',
                    'textarea[placeholder*="Search"]',
                    'textarea[placeholder*="anything"]',
                    'textarea[placeholder*="follow-up"]',
                    'textarea[class*="overflow"]',
                    'textarea[class*="input"]',
                    'textarea[rows]',
                    'div[contenteditable="true"][role="textbox"]',
                    'div[contenteditable="true"]',
                    'textarea'
                ];

                let textarea = null;
                for (const sel of selectors) {{
                    const elements = document.querySelectorAll(sel);
                    for (const el of elements) {{
                        const style = window.getComputedStyle(el);
                        if (el.offsetParent !== null &&
                            style.display !== 'none' &&
                            style.visibility !== 'hidden') {{
                            textarea = el;
                            break;
                        }}
                    }}
                    if (textarea) break;
                }}

                if (!textarea) {{
                    return 'input not found';
                }}

                const text = '{escaped_text}';

                textarea.focus();
                textarea.click();

                if (textarea.tagName === 'TEXTAREA' || textarea.tagName === 'INPUT') {{
                    const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value'
                    ).set;
                    nativeTextAreaValueSetter.call(textarea, text);

                    const tracker = textarea._valueTracker;
                    if (tracker) {{
                        tracker.setValue('');
                    }}

                    textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }} else {{
                    textarea.textContent = text;
                    textarea.dispatchEvent(new InputEvent('input', {{
                        bubbles: true,
                        cancelable: true,
                        inputType: 'insertText',
                        data: text
                    }}));
                }}

                return 'filled';
            }} catch (error) {{
                return 'error: ' + error.message;
            }}
        }})();
        """
        self.execute_js(fill_script, callback)

    def _fill_only_chatgpt(self, text: str, callback=None):
        """Fill input for ChatGPT without sending."""
        escaped_text = (text.replace("\\", "\\\\")
                           .replace("'", "\\'")
                           .replace("\n", "\\n")
                           .replace("\r", "\\r")
                           .replace("</script>", "<\\/script>"))

        fill_script = f"""
        (function() {{
            try {{
                const selectors = [
                    '#prompt-textarea',
                    'div[id="prompt-textarea"]',
                    'div[contenteditable="true"][data-id="root"]',
                    'div[contenteditable="true"][role="textbox"]',
                    'textarea[id="prompt-textarea"]',
                    'textarea[placeholder*="Message"]',
                    'textarea[data-id="root"]'
                ];

                let input = null;
                for (const sel of selectors) {{
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {{
                        input = el;
                        break;
                    }}
                }}

                if (!input) {{
                    return 'input not found';
                }}

                input.focus();
                input.click();

                const text = '{escaped_text}';

                if (input.tagName === 'TEXTAREA') {{
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value'
                    ).set;
                    nativeInputValueSetter.call(input, text);
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }} else {{
                    input.innerHTML = '';
                    input.focus();
                    document.execCommand('insertText', false, text);
                    if (!input.textContent || input.textContent.length < 10) {{
                        const p = document.createElement('p');
                        p.textContent = text;
                        input.innerHTML = '';
                        input.appendChild(p);
                        input.dispatchEvent(new InputEvent('input', {{
                            bubbles: true,
                            cancelable: true,
                            inputType: 'insertText',
                            data: text
                        }}));
                    }}
                }}

                return 'filled';
            }} catch (error) {{
                return 'error: ' + error.message;
            }}
        }})();
        """
        self.execute_js(fill_script, callback)

    def _fill_claude(self, text: str, callback=None):
        """Fill and send query for Claude."""
        escaped_text = (text.replace("\\", "\\\\")
                           .replace("'", "\\'")
                           .replace("\n", "\\n")
                           .replace("\r", "\\r")
                           .replace("</script>", "<\\/script>"))

        fill_script = f"""
        (function() {{
            try {{
                const selectors = [
                    'div[contenteditable="true"].ProseMirror',
                    'div[contenteditable="true"][data-placeholder]',
                    'div.ProseMirror[contenteditable="true"]',
                    'div[contenteditable="true"]',
                    'textarea[placeholder*="message"]',
                    'textarea[placeholder*="Message"]'
                ];

                let input = null;
                for (const sel of selectors) {{
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {{
                        input = el;
                        console.log('Claude: Found input with selector:', sel);
                        break;
                    }}
                }}

                if (!input) {{
                    return 'input not found';
                }}

                input.focus();
                input.click();

                const text = '{escaped_text}';

                if (input.tagName === 'TEXTAREA') {{
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value'
                    ).set;
                    nativeInputValueSetter.call(input, text);
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }} else {{
                    input.innerHTML = '';
                    input.focus();
                    document.execCommand('insertText', false, text);
                    if (!input.textContent || input.textContent.length < 10) {{
                        const p = document.createElement('p');
                        p.textContent = text;
                        input.innerHTML = '';
                        input.appendChild(p);
                        input.dispatchEvent(new InputEvent('input', {{
                            bubbles: true,
                            cancelable: true,
                            inputType: 'insertText',
                            data: text
                        }}));
                    }}
                }}

                window._claudeInput = input;
                return 'filled';
            }} catch (error) {{
                console.error('Claude fill error:', error);
                return 'error: ' + error.message;
            }}
        }})();
        """

        def on_fill_result(result):
            print(f"Claude fill result: {{result}}")
            if result == "filled":
                QTimer.singleShot(300, lambda: self._send_claude_message(callback))
            elif callback:
                callback(result)

        self.execute_js(fill_script, on_fill_result)

    def _send_claude_message(self, callback=None):
        """Send message in Claude after filling."""
        send_script = """
        (function() {
            try {
                const sendSelectors = [
                    'button[aria-label*="Send"]',
                    'button[data-testid="send-button"]',
                    'button[type="submit"]',
                    'button svg[class*="send"]'
                ];

                let sendBtn = null;
                for (const sel of sendSelectors) {
                    let el = document.querySelector(sel);
                    if (el) {
                        if (el.tagName === 'svg') {
                            el = el.closest('button');
                        }
                        if (el && !el.disabled) {
                            sendBtn = el;
                            console.log('Claude: Found send button with selector:', sel);
                            break;
                        }
                    }
                }

                if (sendBtn) {
                    console.log('Claude: Clicking send button');
                    sendBtn.click();
                    return 'sent';
                } else {
                    console.log('Claude: No button found, trying Enter key');
                    const input = window._claudeInput;
                    if (input) {
                        input.dispatchEvent(new KeyboardEvent('keydown', {
                            key: 'Enter',
                            code: 'Enter',
                            keyCode: 13,
                            bubbles: true,
                            cancelable: true
                        }));
                        return 'enter_sent';
                    }
                    return 'no send method found';
                }
            } catch (e) {
                console.error('Claude send error:', e);
                return 'error: ' + e.message;
            }
        })();
        """

        def on_send_result(result):
            print(f"Claude send result: {{result}}")
            if callback:
                callback(result)

        self.execute_js(send_script, on_send_result)

    def _get_claude_response(self, callback):
        """Extract response from Claude."""
        script = """
        (function() {
            // Claude response selectors
            const selectors = [
                'div[data-testid="assistant-message"]',
                'div[class*="assistant-message"]',
                'div[class*="response-content"]',
                'div.prose',
                'div[class*="markdown"]'
            ];

            let lastResponse = null;
            let lastResponseText = '';

            for (const sel of selectors) {
                const messages = document.querySelectorAll(sel);
                if (messages.length > 0) {
                    lastResponse = messages[messages.length - 1];
                    break;
                }
            }

            if (!lastResponse) {
                // Try finding by looking at conversation structure
                const allMessages = document.querySelectorAll('[data-testid*="message"], div[class*="message"]');
                for (let i = allMessages.length - 1; i >= 0; i--) {
                    const msg = allMessages[i];
                    if (msg.getAttribute('data-testid')?.includes('assistant') ||
                        msg.className?.includes('assistant') ||
                        msg.className?.includes('response')) {
                        lastResponse = msg;
                        break;
                    }
                }
            }

            if (lastResponse) {
                lastResponseText = lastResponse.innerText || lastResponse.textContent || '';
            }

            return lastResponseText.trim();
        })();
        """
        self.execute_js(script, callback)

    def _fill_only_claude(self, text: str, callback=None):
        """Fill input for Claude without sending."""
        escaped_text = (text.replace("\\", "\\\\")
                           .replace("'", "\\'")
                           .replace("\n", "\\n")
                           .replace("\r", "\\r")
                           .replace("</script>", "<\\/script>"))

        fill_script = f"""
        (function() {{
            try {{
                const selectors = [
                    'div[contenteditable="true"].ProseMirror',
                    'div[contenteditable="true"][data-placeholder]',
                    'div.ProseMirror[contenteditable="true"]',
                    'div[contenteditable="true"]',
                    'textarea[placeholder*="message"]',
                    'textarea[placeholder*="Message"]'
                ];

                let input = null;
                for (const sel of selectors) {{
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {{
                        input = el;
                        break;
                    }}
                }}

                if (!input) {{
                    return 'input not found';
                }}

                input.focus();
                input.click();

                const text = '{escaped_text}';

                if (input.tagName === 'TEXTAREA') {{
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value'
                    ).set;
                    nativeInputValueSetter.call(input, text);
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }} else {{
                    input.innerHTML = '';
                    input.focus();
                    document.execCommand('insertText', false, text);
                    if (!input.textContent || input.textContent.length < 10) {{
                        const p = document.createElement('p');
                        p.textContent = text;
                        input.innerHTML = '';
                        input.appendChild(p);
                        input.dispatchEvent(new InputEvent('input', {{
                            bubbles: true,
                            cancelable: true,
                            inputType: 'insertText',
                            data: text
                        }}));
                    }}
                }}

                return 'filled';
            }} catch (error) {{
                return 'error: ' + error.message;
            }}
        }})();
        """
        self.execute_js(fill_script, callback)


class PlatformTab(QWidget):
    """Tab containing an embedded browser for a platform."""

    openInGoogleTab = pyqtSignal(str)  # URL to open in Google tab

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

        # Header with status and buttons
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {DARK_THEME['surface']};
                border-bottom: 1px solid {DARK_THEME['border']};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)

        self.status_label = QLabel("Loading...")
        self.status_label.setStyleSheet(f"color: {DARK_THEME['text_secondary']}; font-size: 12px;")
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()

        # Back button
        back_btn = QPushButton("Back")
        back_btn.setStyleSheet(self._button_style())
        back_btn.clicked.connect(self._go_back)
        header_layout.addWidget(back_btn)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(self._button_style())
        refresh_btn.clicked.connect(self._refresh_browser)
        header_layout.addWidget(refresh_btn)

        # Home button
        home_btn = QPushButton("Home")
        home_btn.setStyleSheet(self._button_style())
        home_btn.clicked.connect(self._go_home)
        header_layout.addWidget(home_btn)

        # Clear data button
        clear_btn = QPushButton("Clear Data")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFCDD2;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                color: #C62828;
            }
            QPushButton:hover {
                background-color: #EF9A9A;
            }
        """)
        clear_btn.clicked.connect(self._clear_browser_data)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        # URL bar - only for Google tab
        if self.platform == "google":
            url_bar = QFrame()
            url_bar.setStyleSheet(f"background-color: {DARK_THEME['surface']};")
            url_layout = QHBoxLayout(url_bar)
            url_layout.setContentsMargins(12, 4, 12, 4)
            url_layout.setSpacing(8)

            self.url_input = QLineEdit()
            self.url_input.setPlaceholderText("Enter URL...")
            self.url_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {DARK_THEME['background']};
                    color: {DARK_THEME['text_primary']};
                    border: 1px solid {DARK_THEME['border']};
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                }}
                QLineEdit:focus {{
                    border-color: {DARK_THEME['accent']};
                }}
            """)
            self.url_input.returnPressed.connect(self._navigate_to_url)
            url_layout.addWidget(self.url_input)

            go_btn = QPushButton("Go")
            go_btn.setFixedWidth(56)
            go_btn.setStyleSheet(self._button_style())
            go_btn.clicked.connect(self._navigate_to_url)
            url_layout.addWidget(go_btn)

            layout.addWidget(url_bar)

        # Create and add the browser
        self.browser = PlatformBrowser(self.platform)
        self.browser.pageLoaded.connect(self._on_page_loaded)
        self.browser.openInGoogleTab.connect(self.openInGoogleTab.emit)
        if self.platform == "google":
            self.browser.urlChanged.connect(self._on_url_changed)
        layout.addWidget(self.browser, 1)

        # Download notification bar (hidden by default)
        self.download_bar = QFrame()
        self.download_bar.setFixedHeight(32)
        self.download_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {DARK_THEME['surface']};
                border-top: 1px solid {DARK_THEME['border']};
            }}
        """)
        download_bar_layout = QHBoxLayout(self.download_bar)
        download_bar_layout.setContentsMargins(12, 4, 12, 4)
        download_bar_layout.setSpacing(8)

        self.download_icon = QLabel()
        self.download_icon.setFixedSize(16, 16)
        download_bar_layout.addWidget(self.download_icon)

        self.download_label = QLabel("")
        self.download_label.setStyleSheet(f"font-size: 11px; color: {DARK_THEME['text_primary']};")
        download_bar_layout.addWidget(self.download_label, 1)

        self.download_close_btn = QPushButton("x")
        self.download_close_btn.setFixedSize(20, 20)
        self.download_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {DARK_THEME['text_secondary']};
                border: none;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {DARK_THEME['text_primary']};
            }}
        """)
        self.download_close_btn.clicked.connect(self.download_bar.hide)
        download_bar_layout.addWidget(self.download_close_btn)

        self.download_bar.hide()
        layout.addWidget(self.download_bar)

        # Register for download notifications
        PlatformBrowser.add_download_listener(self._on_download_event)

        # Timer to auto-hide download bar
        self._download_hide_timer = QTimer()
        self._download_hide_timer.setSingleShot(True)
        self._download_hide_timer.timeout.connect(self.download_bar.hide)

        # Navigate to the platform URL
        self.browser.navigate(self.url)

    def _button_style(self):
        return f"""
            QPushButton {{
                background-color: {DARK_THEME['surface_light']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                padding: 4px 12px;
                color: {DARK_THEME['text_primary']};
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent']};
            }}
        """

    def _go_back(self):
        """Go back in browser history."""
        if self.browser:
            self.browser.back()

    def _go_home(self):
        """Navigate to the platform's home page."""
        if self.browser:
            self.browser.navigate(self.url)

    def _refresh_browser(self):
        """Refresh the browser."""
        if self.browser:
            self.browser.reload()

    def _navigate_to_url(self):
        """Navigate to the URL in the URL bar."""
        if not hasattr(self, 'url_input'):
            return
        url = self.url_input.text().strip()
        if url:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            if self.browser:
                self.browser.navigate(url)

    def _on_url_changed(self, url):
        """Update URL bar when browser URL changes."""
        if hasattr(self, 'url_input'):
            self.url_input.setText(url.toString())

    def _on_download_event(self, filename: str, state: str, percent: int):
        """Show download status in the notification bar."""
        if state == "started":
            self.download_icon.setStyleSheet("background-color: #2196F3; border-radius: 8px;")
            self.download_label.setText(f"Downloading: {filename} (0%)")
            self.download_label.setStyleSheet(f"font-size: 11px; color: {DARK_THEME['text_primary']};")
            self._download_hide_timer.stop()
            self.download_bar.show()
        elif state == "progress":
            self.download_icon.setStyleSheet("background-color: #2196F3; border-radius: 8px;")
            if percent >= 0:
                self.download_label.setText(f"Downloading: {filename} ({percent}%)")
            else:
                self.download_label.setText(f"Downloading: {filename}...")
            self.download_label.setStyleSheet(f"font-size: 11px; color: {DARK_THEME['text_primary']};")
        elif state == "completed":
            self.download_icon.setStyleSheet("background-color: #4CAF50; border-radius: 8px;")
            self.download_label.setText(f"Downloaded: {filename}")
            self.download_label.setStyleSheet("font-size: 11px; color: #4CAF50;")
            self.download_bar.show()
            self._download_hide_timer.start(5000)
        elif state == "failed":
            self.download_icon.setStyleSheet("background-color: #F44336; border-radius: 8px;")
            self.download_label.setText(f"Download failed: {filename}")
            self.download_label.setStyleSheet("font-size: 11px; color: #F44336;")
            self.download_bar.show()
            self._download_hide_timer.start(8000)
        elif state == "cancelled":
            self.download_icon.setStyleSheet("background-color: #FF9800; border-radius: 8px;")
            self.download_label.setText(f"Download cancelled: {filename}")
            self.download_label.setStyleSheet("font-size: 11px; color: #FF9800;")
            self.download_bar.show()
            self._download_hide_timer.start(5000)

    def _clear_browser_data(self):
        """Clear cookies and browser data for this profile."""
        reply = QMessageBox.question(
            self,
            "Clear Browser Data",
            "This will clear all cookies and login data for all platforms.\n\nYou will need to log in again.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            profile = PlatformBrowser.get_shared_profile()
            profile.cookieStore().deleteAllCookies()
            profile.clearHttpCache()

            # Reload the page
            if self.browser:
                self.browser.navigate(self.url)

            self.status_label.setText("Data cleared")
            self.status_label.setStyleSheet("color: #FF9800; font-size: 12px;")

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


class LogTab(QWidget):
    """Widget for the logs tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QFrame()
        header.setStyleSheet(f"background-color: {DARK_THEME['surface']};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Logs")
        title.setStyleSheet(f"color: {DARK_THEME['text_primary']}; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border-radius: 4px;
                padding: 4px 12px;
                border: 1px solid {DARK_THEME['border']};
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent']};
            }}
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

        # Color coding based on level
        color_map = {
            "INFO": "#D4D4D4",
            "WARNING": "#FFA500",
            "ERROR": "#FF6B6B",
            "SUCCESS": "#4CAF50",
            "DEBUG": "#9E9E9E"
        }
        color = color_map.get(level, "#D4D4D4")

        formatted = f"[{timestamp}] [{level}] {message}"
        self.log_output.appendPlainText(formatted)

        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear(self):
        """Clear the log output."""
        self.log_output.clear()


class MarkdownNotebookTab(QWidget):
    """Rich text notebook editor with Word/Google Docs-like formatting, saves as Markdown."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_file = None
        self._is_modified = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create toolbar container for two rows
        toolbar_container = QFrame()
        toolbar_container.setStyleSheet(f"""
            QFrame {{
                background-color: {DARK_THEME['surface']};
                border-bottom: 1px solid {DARK_THEME['border']};
            }}
        """)
        toolbar_container_layout = QVBoxLayout(toolbar_container)
        toolbar_container_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_container_layout.setSpacing(0)

        # Row 1: File operations and text formatting
        row1 = QFrame()
        row1_layout = QHBoxLayout(row1)
        row1_layout.setContentsMargins(8, 6, 8, 4)
        row1_layout.setSpacing(6)

        # File operations
        self.new_btn = self._create_toolbar_btn("New", self._new_document)
        self.open_btn = self._create_toolbar_btn("Open", self._open_document)
        self.save_btn = self._create_toolbar_btn("Save", self._save_document)
        row1_layout.addWidget(self.new_btn)
        row1_layout.addWidget(self.open_btn)
        row1_layout.addWidget(self.save_btn)

        row1_layout.addWidget(self._create_separator())

        # Text formatting buttons
        self.bold_btn = self._create_toolbar_btn("B", self._toggle_bold, bold=True)
        self.italic_btn = self._create_toolbar_btn("I", self._toggle_italic, italic=True)
        self.underline_btn = self._create_toolbar_btn("U", self._toggle_underline, underline=True)
        self.strike_btn = self._create_toolbar_btn("S", self._toggle_strikethrough, strike=True)
        row1_layout.addWidget(self.bold_btn)
        row1_layout.addWidget(self.italic_btn)
        row1_layout.addWidget(self.underline_btn)
        row1_layout.addWidget(self.strike_btn)

        row1_layout.addWidget(self._create_separator())

        row1_layout.addStretch()

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(f"color: {DARK_THEME['text_secondary']}; font-size: 11px;")
        row1_layout.addWidget(self.status_label)

        toolbar_container_layout.addWidget(row1)

        # Row 2: Lists, alignment, and other tools
        row2 = QFrame()
        row2_layout = QHBoxLayout(row2)
        row2_layout.setContentsMargins(8, 4, 8, 6)
        row2_layout.setSpacing(6)

        # Normal text
        self.normal_btn = self._create_toolbar_btn("Normal", self._set_normal)
        row2_layout.addWidget(self.normal_btn)

        row2_layout.addWidget(self._create_separator())

        # Lists
        self.bullet_btn = self._create_toolbar_btn("Bullet List", self._toggle_bullet_list)
        self.number_btn = self._create_toolbar_btn("Numbered List", self._toggle_number_list)
        row2_layout.addWidget(self.bullet_btn)
        row2_layout.addWidget(self.number_btn)

        row2_layout.addStretch()

        toolbar_container_layout.addWidget(row2)

        layout.addWidget(toolbar_container)

        # Title input
        title_frame = QFrame()
        title_frame.setStyleSheet(f"background-color: {DARK_THEME['surface']}; border-bottom: 1px solid {DARK_THEME['border']};")
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(12, 8, 12, 8)

        title_label = QLabel("Title:")
        title_label.setStyleSheet(f"color: {DARK_THEME['text_secondary']}; font-size: 12px;")
        title_layout.addWidget(title_label)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Untitled Note")
        self.title_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 14px;
                font-weight: bold;
            }}
            QLineEdit:focus {{
                border-color: {DARK_THEME['accent']};
            }}
        """)
        self.title_input.textChanged.connect(self._on_content_changed)
        title_layout.addWidget(self.title_input)

        layout.addWidget(title_frame)

        # Rich text editor
        self.editor = QTextEdit()
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DARK_THEME['background']};
                color: {DARK_THEME['text_primary']};
                border: none;
                padding: 16px;
                font-size: 14px;
                line-height: 1.6;
            }}
            QScrollBar:vertical {{
                background-color: {DARK_THEME['surface']};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {DARK_THEME['border']};
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {DARK_THEME['text_secondary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        self.editor.setPlaceholderText("Start writing your notes here...")
        self.editor.setFont(QFont("Georgia", 14))

        # Set default line spacing (1.15x for body text)
        doc = self.editor.document()
        doc.setDefaultStyleSheet(f"""
            body {{ line-height: 1.15; }}
            hr {{ border: none; border-top: 1px solid {DARK_THEME['border']}; margin: 8px 0; }}
            blockquote {{
                border-left: 3px solid {DARK_THEME['border']};
                padding-left: 12px;
                color: {DARK_THEME['text_secondary']};
                font-style: italic;
                margin: 8px 0;
            }}
        """)
        default_block_fmt = QTextBlockFormat()
        default_block_fmt.setLineHeight(115, 1)  # 1 = ProportionalHeight
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(default_block_fmt)

        self.editor.textChanged.connect(self._on_content_changed)
        self.editor.cursorPositionChanged.connect(self._update_format_buttons)

        # Install event filter to handle Enter key for consistent formatting
        self.editor.installEventFilter(self)

        layout.addWidget(self.editor, 1)

        # Word count footer
        footer = QFrame()
        footer.setStyleSheet(f"background-color: {DARK_THEME['surface']}; border-top: 1px solid {DARK_THEME['border']};")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 4, 12, 4)

        self.word_count_label = QLabel("Words: 0 | Characters: 0")
        self.word_count_label.setStyleSheet(f"color: {DARK_THEME['text_secondary']}; font-size: 11px;")
        footer_layout.addWidget(self.word_count_label)

        footer_layout.addStretch()

        self.file_label = QLabel("New Document")
        self.file_label.setStyleSheet(f"color: {DARK_THEME['text_secondary']}; font-size: 11px;")
        footer_layout.addWidget(self.file_label)

        layout.addWidget(footer)

    def _create_separator(self):
        """Create a vertical separator line."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"background-color: {DARK_THEME['border']};")
        sep.setFixedWidth(1)
        return sep

    def _create_toolbar_btn(self, text, callback, bold=False, italic=False, underline=False, strike=False):
        """Create a toolbar button with consistent styling."""
        btn = QPushButton(text)
        btn.setFixedHeight(26)
        btn.setMinimumWidth(32)

        font_style = ""
        if bold:
            font_style += "font-weight: bold;"
        if italic:
            font_style += "font-style: italic;"
        if underline:
            font_style += "text-decoration: underline;"
        if strike:
            font_style += "text-decoration: line-through;"

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 11px;
                {font_style}
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent']};
                border-color: {DARK_THEME['accent']};
            }}
            QPushButton:checked {{
                background-color: {DARK_THEME['accent']};
                border-color: {DARK_THEME['accent']};
            }}
        """)
        btn.setCheckable(bold or italic or underline or strike)
        btn.clicked.connect(callback)
        return btn

    def _toggle_bold(self):
        """Toggle bold formatting on selected text."""
        fmt = QTextCharFormat()
        cursor = self.editor.textCursor()
        current_weight = cursor.charFormat().fontWeight()
        if current_weight == QFont.Weight.Bold:
            fmt.setFontWeight(QFont.Weight.Normal)
        else:
            fmt.setFontWeight(QFont.Weight.Bold)
        cursor.mergeCharFormat(fmt)

    def _toggle_italic(self):
        """Toggle italic formatting on selected text."""
        fmt = QTextCharFormat()
        cursor = self.editor.textCursor()
        fmt.setFontItalic(not cursor.charFormat().fontItalic())
        cursor.mergeCharFormat(fmt)

    def _toggle_underline(self):
        """Toggle underline formatting on selected text."""
        fmt = QTextCharFormat()
        cursor = self.editor.textCursor()
        fmt.setFontUnderline(not cursor.charFormat().fontUnderline())
        cursor.mergeCharFormat(fmt)

    def _toggle_strikethrough(self):
        """Toggle strikethrough formatting on selected text."""
        fmt = QTextCharFormat()
        cursor = self.editor.textCursor()
        fmt.setFontStrikeOut(not cursor.charFormat().fontStrikeOut())
        cursor.mergeCharFormat(fmt)

    def _set_heading(self, level: int):
        """Set the current paragraph as a heading using block-level heading format."""
        cursor = self.editor.textCursor()

        # Set block-level heading with extra spacing
        block_fmt = cursor.blockFormat()
        block_fmt.setHeadingLevel(level)
        block_fmt.setTopMargin(16)
        block_fmt.setBottomMargin(8)
        block_fmt.setLineHeight(150, 1)
        cursor.setBlockFormat(block_fmt)

        # Select only block text, not the block separator
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)

        fmt = QTextCharFormat()
        sizes = {1: 24, 2: 20, 3: 16}
        fmt.setFontPointSize(sizes.get(level, 14))
        fmt.setFontWeight(QFont.Weight.Bold)

        cursor.mergeCharFormat(fmt)

    def _set_normal(self):
        """Reset all formatting to normal text."""
        cursor = self.editor.textCursor()

        # If there's a selection, reset the selection; otherwise reset current block
        if not cursor.hasSelection():
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)

        # Reset character format
        fmt = QTextCharFormat()
        fmt.setFontPointSize(14)
        fmt.setFontWeight(QFont.Weight.Normal)
        fmt.setFontItalic(False)
        fmt.setFontUnderline(False)
        fmt.setFontStrikeOut(False)
        fmt.setFontFamily("Georgia")
        fmt.setForeground(QColor(DARK_THEME['text_primary']))
        fmt.setBackground(QColor(0, 0, 0, 0))  # Transparent
        cursor.setCharFormat(fmt)

        # Reset block format
        block_fmt = cursor.blockFormat()
        block_fmt.setIndent(0)
        block_fmt.setLeftMargin(0)
        block_fmt.setTopMargin(0)
        block_fmt.setBottomMargin(0)
        block_fmt.setHeadingLevel(0)
        block_fmt.setProperty(QTextFormat.Property.BlockQuoteLevel, 0)
        block_fmt.setLineHeight(115, 1)
        block_fmt.setAlignment(Qt.AlignmentFlag.AlignLeft)
        cursor.setBlockFormat(block_fmt)

        # Remove from list if in one
        current_list = cursor.currentList()
        if current_list:
            current_list.remove(cursor.block())

        self.editor.setTextCursor(cursor)

    def _toggle_bullet_list(self):
        """Toggle bullet list for current line."""
        cursor = self.editor.textCursor()
        current_list = cursor.currentList()

        if current_list and current_list.format().style() == QTextListFormat.Style.ListDisc:
            # Remove from list
            current_list.remove(cursor.block())
            # Reset indent
            block_fmt = cursor.blockFormat()
            block_fmt.setIndent(0)
            cursor.setBlockFormat(block_fmt)
        else:
            # Remove from any existing list first
            if current_list:
                current_list.remove(cursor.block())
            # Create bullet list
            list_fmt = QTextListFormat()
            list_fmt.setStyle(QTextListFormat.Style.ListDisc)
            cursor.createList(list_fmt)

        self.editor.setTextCursor(cursor)

    def _toggle_number_list(self):
        """Toggle numbered list for current line."""
        cursor = self.editor.textCursor()
        current_list = cursor.currentList()

        if current_list and current_list.format().style() == QTextListFormat.Style.ListDecimal:
            # Remove from list
            current_list.remove(cursor.block())
            # Reset indent
            block_fmt = cursor.blockFormat()
            block_fmt.setIndent(0)
            cursor.setBlockFormat(block_fmt)
        else:
            # Remove from any existing list first
            if current_list:
                current_list.remove(cursor.block())
            # Create numbered list
            list_fmt = QTextListFormat()
            list_fmt.setStyle(QTextListFormat.Style.ListDecimal)
            cursor.createList(list_fmt)

        self.editor.setTextCursor(cursor)

    def _update_format_buttons(self):
        """Update toolbar button checked states to reflect formatting at cursor."""
        # Only read format state here, never modify document content
        cursor = self.editor.textCursor()
        fmt = cursor.charFormat()

        self.bold_btn.blockSignals(True)
        self.bold_btn.setChecked(fmt.fontWeight() == QFont.Weight.Bold)
        self.bold_btn.blockSignals(False)

        self.italic_btn.blockSignals(True)
        self.italic_btn.setChecked(fmt.fontItalic())
        self.italic_btn.blockSignals(False)

        self.underline_btn.blockSignals(True)
        self.underline_btn.setChecked(fmt.fontUnderline())
        self.underline_btn.blockSignals(False)

        self.strike_btn.blockSignals(True)
        self.strike_btn.setChecked(fmt.fontStrikeOut())
        self.strike_btn.blockSignals(False)

    def _on_content_changed(self):
        """Handle content changes and apply live markdown formatting."""
        self._is_modified = True
        self._update_status()
        self._update_word_count()

        # Apply live markdown formatting (Notion-like)
        self._apply_live_markdown()

    def _update_status(self):
        """Update status label."""
        if self._is_modified:
            self.status_label.setText("Modified")
            self.status_label.setStyleSheet(f"color: {DARK_THEME['warning']}; font-size: 11px;")
        else:
            self.status_label.setText("Saved")
            self.status_label.setStyleSheet(f"color: {DARK_THEME['success']}; font-size: 11px;")

    def _update_word_count(self):
        """Update word and character count."""
        text = self.editor.toPlainText()
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        self.word_count_label.setText(f"Words: {words} | Characters: {chars}")

    def eventFilter(self, obj, event):
        """Handle Enter key to reset formatting for new lines."""
        if obj == self.editor and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                # Reset formatting for the new line after Enter
                cursor = self.editor.textCursor()

                # Check if current block has special formatting
                char_fmt = cursor.charFormat()
                block_fmt = cursor.blockFormat()

                # Check for header (large font), blockquote, or special styling
                is_header = block_fmt.headingLevel() > 0 or char_fmt.fontPointSize() >= 16
                has_margin = block_fmt.leftMargin() > 0
                quote_level = block_fmt.property(QTextFormat.Property.BlockQuoteLevel)
                is_quote = quote_level and quote_level > 0

                if is_header or has_margin or is_quote:
                    # Let the default Enter happen first
                    self.editor.keyPressEvent(event)

                    # Then reset formatting for the new line
                    new_cursor = self.editor.textCursor()

                    # Reset character format to normal
                    fmt = QTextCharFormat()
                    fmt.setFontPointSize(14)
                    fmt.setFontWeight(QFont.Weight.Normal)
                    fmt.setFontItalic(False)
                    fmt.setFontUnderline(False)
                    fmt.setFontStrikeOut(False)
                    fmt.setFontFamily("Georgia")
                    fmt.setForeground(QColor(DARK_THEME['text_primary']))
                    fmt.clearBackground()
                    new_cursor.setCharFormat(fmt)

                    # Reset block format
                    new_block_fmt = new_cursor.blockFormat()
                    new_block_fmt.setLeftMargin(0)
                    new_block_fmt.setTopMargin(0)
                    new_block_fmt.setBottomMargin(0)
                    new_block_fmt.setIndent(0)
                    new_block_fmt.setHeadingLevel(0)
                    new_block_fmt.setProperty(QTextFormat.Property.BlockQuoteLevel, 0)
                    new_block_fmt.setLineHeight(115, 1)
                    new_cursor.setBlockFormat(new_block_fmt)

                    self.editor.setTextCursor(new_cursor)
                    return True  # Event handled

        return super().eventFilter(obj, event)

    def _apply_live_markdown(self):
        """Apply Notion-like live markdown formatting when patterns are completed."""
        import re

        # Prevent recursion
        if getattr(self, '_applying_markdown', False):
            return

        try:
            cursor = self.editor.textCursor()
            position = cursor.position()

            # Only trigger on certain conditions - check if we just typed space/enter
            # by looking at the character before cursor
            if position == 0:
                return

            block = cursor.block()
            text = block.text()

            # Skip if text is too short
            if len(text) < 2:
                return

            # Get character at cursor position within block
            pos_in_block = position - block.position()
            if pos_in_block == 0:
                return

            # Check for completed patterns that should trigger conversion
            block_start = block.position()
            self._applying_markdown = True

            # Patterns that trigger on space after completion
            space_patterns = [
                # Headers at start of line with content
                (r'^(#{1,3})\s+(.+)\s$', self._format_header),
                # Horizontal rule (exactly --- followed by space or at end)
                (r'^---\s*$', self._format_horizontal_rule),
                # Quote > text
                (r'^>\s+(.+)\s$', self._format_quote),
                # Bullet list
                (r'^[-*]\s+(.+)\s$', self._format_bullet),
            ]

            # Patterns that trigger when closed (e.g., **text** )
            closed_patterns = [
                # Bold **text** followed by space
                (r'\*\*([^*]+)\*\*\s', self._format_bold),
                # Italic *text* followed by space (not part of bold)
                (r'(?<!\*)\*([^*]+)\*(?!\*)\s', self._format_italic),
                # Strikethrough ~~text~~ followed by space
                (r'~~([^~]+)~~\s', self._format_strikethrough),
                # Inline code `text` followed by space
                (r'`([^`]+)`\s', self._format_inline_code),
            ]

            # Try space-triggered patterns
            for pattern, format_func in space_patterns:
                match = re.match(pattern, text)
                if match:
                    start = block_start + match.start()
                    end = block_start + match.end()
                    format_func(start, end, match)
                    return  # Only process one pattern per change

            # Try closed patterns
            for pattern, format_func in closed_patterns:
                # Search for pattern ending near cursor position
                for match in re.finditer(pattern, text):
                    match_end = match.end()
                    # Check if this match ends near cursor
                    if abs(pos_in_block - match_end) <= 1:
                        start = block_start + match.start()
                        end = block_start + match.end() - 1  # Exclude trailing space
                        format_func(start, end, match)
                        return  # Only process one pattern per change

        except Exception:
            pass
        finally:
            self._applying_markdown = False

    def _format_header(self, start, end, match):
        """Format header (# ## ###)."""
        level = len(match.group(1))
        content = match.group(2)

        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        # Delete the markdown syntax and insert formatted text
        cursor.removeSelectedText()

        # Set block-level heading with spacing
        block_fmt = cursor.blockFormat()
        block_fmt.setHeadingLevel(level)
        block_fmt.setTopMargin(16)
        block_fmt.setBottomMargin(8)
        block_fmt.setLineHeight(150, 1)
        cursor.setBlockFormat(block_fmt)

        fmt = QTextCharFormat()
        sizes = {1: 24, 2: 20, 3: 16}
        fmt.setFontPointSize(sizes.get(level, 14))
        fmt.setFontWeight(QFont.Weight.Bold)

        cursor.insertText(content, fmt)

    def _format_bold(self, start, end, match):
        """Format bold **text**."""
        content = match.group(1)

        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        cursor.removeSelectedText()

        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold)
        cursor.insertText(content, fmt)

    def _format_italic(self, start, end, match):
        """Format italic *text*."""
        content = match.group(1)

        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        cursor.removeSelectedText()

        fmt = QTextCharFormat()
        fmt.setFontItalic(True)
        cursor.insertText(content, fmt)

    def _format_strikethrough(self, start, end, match):
        """Format strikethrough ~~text~~."""
        content = match.group(1)

        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        cursor.removeSelectedText()

        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(True)
        cursor.insertText(content, fmt)

    def _format_inline_code(self, start, end, match):
        """Format inline code `text`."""
        content = match.group(1)

        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        cursor.removeSelectedText()

        fmt = QTextCharFormat()
        fmt.setFontFamily("Courier New")
        fmt.setBackground(QColor(DARK_THEME['surface_light']))
        cursor.insertText(content, fmt)

    def _format_horizontal_rule(self, start, end, _match):
        """Format horizontal rule --- using HTML hr for proper markdown round-trip."""
        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        cursor.removeSelectedText()
        cursor.insertHtml(f'<hr style="border: none; border-top: 1px solid {DARK_THEME["border"]};" />')

    def _format_quote(self, start, end, match):
        """Format quote > text using proper blockquote for markdown round-trip."""
        content = match.group(1)

        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        cursor.removeSelectedText()

        # Use proper blockquote property so toMarkdown() serializes as >
        block_fmt = cursor.blockFormat()
        block_fmt.setProperty(QTextFormat.Property.BlockQuoteLevel, 1)
        block_fmt.setLeftMargin(20)
        cursor.setBlockFormat(block_fmt)

        # Set character format for visual styling
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(DARK_THEME['text_secondary']))
        fmt.setFontItalic(True)
        cursor.insertText(content, fmt)

    def _format_bullet(self, start, end, match):
        """Format bullet list - item."""
        content = match.group(1)

        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        cursor.removeSelectedText()

        # Create bullet list
        list_fmt = QTextListFormat()
        list_fmt.setStyle(QTextListFormat.Style.ListDisc)
        cursor.createList(list_fmt)

        cursor.insertText(content)

    def _format_numbered(self, start, end, match):
        """Format numbered list 1. item."""
        content = match.group(2)

        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        cursor.removeSelectedText()

        # Create numbered list
        list_fmt = QTextListFormat()
        list_fmt.setStyle(QTextListFormat.Style.ListDecimal)
        cursor.createList(list_fmt)

        cursor.insertText(content)

    def _new_document(self):
        """Create a new document."""
        if self._is_modified:
            reply = QMessageBox.question(
                self,
                "Save Changes?",
                "Do you want to save changes before creating a new document?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self._save_document()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        self.title_input.clear()
        self.editor.clear()
        self._current_file = None
        self._is_modified = False
        self.file_label.setText("New Document")
        self._update_status()
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet(f"color: {DARK_THEME['text_secondary']}; font-size: 11px;")

    def _apply_post_load_styling(self):
        """Re-apply visual styling after loading markdown content."""
        doc = self.editor.document()
        block = doc.begin()
        while block.isValid():
            cursor = QTextCursor(block)
            block_fmt = block.blockFormat()

            modified = False
            new_fmt = QTextBlockFormat(block_fmt)

            heading_level = block_fmt.headingLevel()
            if heading_level > 0:
                new_fmt.setTopMargin(16)
                new_fmt.setBottomMargin(8)
                new_fmt.setLineHeight(150, 1)
                # Select only block text content, not the block separator
                sizes = {1: 24, 2: 20, 3: 16}
                char_fmt = QTextCharFormat()
                char_fmt.setFontPointSize(sizes.get(heading_level, 14))
                char_fmt.setFontWeight(QFont.Weight.Bold)
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
                cursor.mergeCharFormat(char_fmt)
                modified = True

            quote_level = block_fmt.property(QTextFormat.Property.BlockQuoteLevel)
            if quote_level and quote_level > 0:
                new_fmt.setLeftMargin(20)
                char_fmt = QTextCharFormat()
                char_fmt.setForeground(QColor(DARK_THEME['text_secondary']))
                char_fmt.setFontItalic(True)
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
                cursor.mergeCharFormat(char_fmt)
                modified = True

            if not modified:
                new_fmt.setLineHeight(115, 1)

            cursor.setBlockFormat(new_fmt)
            block = block.next()

    def _load_markdown_content(self, content):
        """Load markdown content into the editor, preserving blank lines.

        Parses markdown line by line and builds the document directly so
        blank lines are preserved as empty blocks.
        """
        import re

        self.editor.clear()
        cursor = self.editor.textCursor()
        lines = content.split('\n')
        # Strip single trailing newline that our save adds
        if lines and lines[-1] == '':
            lines = lines[:-1]

        first_block = True

        # Default formats to reset to between blocks
        default_block_fmt = QTextBlockFormat()
        default_block_fmt.setLineHeight(115, 1)
        default_char_fmt = QTextCharFormat()
        default_char_fmt.setFontPointSize(14)
        default_char_fmt.setFontFamily("Georgia")
        default_char_fmt.setForeground(QColor(DARK_THEME['text_primary']))
        default_char_fmt.setFontWeight(QFont.Weight.Normal)
        default_char_fmt.setFontItalic(False)
        default_char_fmt.setFontStrikeOut(False)
        default_char_fmt.setFontUnderline(False)

        for line in lines:
            if not first_block:
                # Reset format before inserting new block to prevent leaking
                cursor.setCharFormat(default_char_fmt)
                cursor.insertBlock(default_block_fmt, default_char_fmt)
            first_block = False

            stripped = line.strip()

            # Empty line = blank line
            if not stripped:
                continue

            # Heading: # ## ###
            heading_match = re.match(r'^(#{1,3})\s+(.+)$', stripped)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2)
                block_fmt = cursor.blockFormat()
                block_fmt.setHeadingLevel(level)
                block_fmt.setTopMargin(16)
                block_fmt.setBottomMargin(8)
                block_fmt.setLineHeight(150, 1)
                cursor.setBlockFormat(block_fmt)
                fmt = QTextCharFormat()
                sizes = {1: 24, 2: 20, 3: 16}
                fmt.setFontPointSize(sizes.get(level, 14))
                fmt.setFontWeight(QFont.Weight.Bold)
                self._insert_inline_markdown(cursor, text, base_fmt=fmt)
                continue

            # Blockquote: > text
            quote_match = re.match(r'^>\s*(.*)$', stripped)
            if quote_match:
                text = quote_match.group(1)
                block_fmt = cursor.blockFormat()
                block_fmt.setProperty(QTextFormat.Property.BlockQuoteLevel, 1)
                block_fmt.setLeftMargin(20)
                cursor.setBlockFormat(block_fmt)
                fmt = QTextCharFormat()
                fmt.setForeground(QColor(DARK_THEME['text_secondary']))
                fmt.setFontItalic(True)
                fmt.setFontPointSize(14)
                cursor.insertText(text, fmt)
                continue

            # Horizontal rule: ---
            if re.match(r'^-{3,}$', stripped):
                cursor.insertHtml(
                    f'<hr style="border: none; border-top: 1px solid {DARK_THEME["border"]};" />'
                )
                continue

            # Unordered list: - or * item
            bullet_match = re.match(r'^[-*]\s+(.+)$', stripped)
            if bullet_match:
                text = bullet_match.group(1)
                list_fmt = QTextListFormat()
                list_fmt.setStyle(QTextListFormat.Style.ListDisc)
                cursor.createList(list_fmt)
                self._insert_inline_markdown(cursor, text)
                continue

            # Ordered list: 1. item
            num_match = re.match(r'^\d+\.\s+(.+)$', stripped)
            if num_match:
                text = num_match.group(1)
                list_fmt = QTextListFormat()
                list_fmt.setStyle(QTextListFormat.Style.ListDecimal)
                cursor.createList(list_fmt)
                self._insert_inline_markdown(cursor, text)
                continue

            # Regular paragraph with inline formatting
            self._insert_inline_markdown(cursor, stripped)

    def _insert_inline_markdown(self, cursor, text, base_fmt=None):
        """Parse inline markdown (bold, italic, strikethrough) and insert formatted text."""
        import re

        if base_fmt is None:
            base_fmt = QTextCharFormat()
            base_fmt.setFontPointSize(14)
            base_fmt.setFontFamily("Georgia")
            base_fmt.setForeground(QColor(DARK_THEME['text_primary']))

        # Pattern matches inline markdown formats or plain text
        pattern = re.compile(
            r'(`([^`]+)`)'            # inline code
            r'|(\*\*(.+?)\*\*)'      # bold
            r'|(\*(.+?)\*)'          # italic
            r'|(~~(.+?)~~)'          # strikethrough
            r'|(<u>(.+?)</u>)'       # underline
            r'|([^*~`<]+)'           # plain text
            r'|([*~`<])'            # leftover markers
        )

        for m in pattern.finditer(text):
            if m.group(2) is not None:
                # Inline code
                fmt = QTextCharFormat(base_fmt)
                fmt.setFontFamily("Courier New")
                fmt.setBackground(QColor(DARK_THEME['surface_light']))
                cursor.insertText(m.group(2), fmt)
            elif m.group(4) is not None:
                # Bold
                fmt = QTextCharFormat(base_fmt)
                fmt.setFontWeight(QFont.Weight.Bold)
                cursor.insertText(m.group(4), fmt)
            elif m.group(6) is not None:
                # Italic
                fmt = QTextCharFormat(base_fmt)
                fmt.setFontItalic(True)
                cursor.insertText(m.group(6), fmt)
            elif m.group(8) is not None:
                # Strikethrough
                fmt = QTextCharFormat(base_fmt)
                fmt.setFontStrikeOut(True)
                cursor.insertText(m.group(8), fmt)
            elif m.group(10) is not None:
                # Underline
                fmt = QTextCharFormat(base_fmt)
                fmt.setFontUnderline(True)
                cursor.insertText(m.group(10), fmt)
            elif m.group(11) is not None:
                # Plain text
                cursor.insertText(m.group(11), base_fmt)
            elif m.group(12) is not None:
                # Leftover marker char
                cursor.insertText(m.group(12), base_fmt)

    def _open_document(self):
        """Open an existing document (supports .md and .txt)."""
        if self._is_modified:
            reply = QMessageBox.question(
                self,
                "Save Changes?",
                "Do you want to save changes before opening another document?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self._save_document()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        notes_dir = CONFIG_DIR / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Note",
            str(notes_dir),
            "Markdown Files (*.md);;Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Block signals during load to prevent _apply_live_markdown interference
                self.editor.blockSignals(True)
                self._load_markdown_content(content)
                self.editor.blockSignals(False)

                # Extract title from filename
                from pathlib import Path
                self.title_input.setText(Path(file_path).stem)
                self._current_file = file_path
                self._is_modified = False
                self.file_label.setText(Path(file_path).name)
                self.status_label.setText("Opened")
                self.status_label.setStyleSheet(f"color: {DARK_THEME['success']}; font-size: 11px;")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")

    def _document_to_markdown(self):
        """Convert document to markdown by parsing the HTML output.

        Avoids all direct QTextDocument block/fragment iteration which
        causes segfaults in PyQt6. Uses toHtml() (safe) and converts
        the HTML to markdown by walking block-level elements in order.
        """
        import re
        from html import unescape

        html = self.editor.toHtml()

        # Extract body content
        body_match = re.search(r'<body[^>]*>(.*)</body>', html, re.DOTALL)
        if not body_match:
            return self.editor.toPlainText() + '\n'

        body = body_match.group(1).strip()
        lines = []

        # Match all block-level elements in document order
        block_re = re.compile(
            r'<(h[1-3])([^>]*)>(.*?)</\1>'
            r'|<(blockquote)[^>]*>(.*?)</\4>'
            r'|<(ol)[^>]*>(.*?)</\6>'
            r'|<(ul)[^>]*>(.*?)</\8>'
            r'|<(hr)[^>]*/?\s*>'
            r'|<(p)([^>]*)>(.*?)</p>',
            re.DOTALL
        )

        for m in block_re.finditer(body):
            # Heading h1-h3
            if m.group(1):
                tag = m.group(1)
                level = int(tag[1])
                inner = self._html_inline_to_md(m.group(3), skip_bold=True)
                lines.append(f'{"#" * level} {inner}')

            # Blockquote
            elif m.group(4):
                inner_html = m.group(5)
                paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', inner_html, re.DOTALL)
                if paragraphs:
                    for p in paragraphs:
                        inner = self._html_inline_to_md(p, skip_italic=True)
                        if inner:
                            lines.append(f'> {inner}')
                else:
                    inner = self._html_inline_to_md(inner_html, skip_italic=True)
                    if inner:
                        lines.append(f'> {inner}')

            # Ordered list
            elif m.group(6):
                items = re.findall(r'<li[^>]*>(.*?)</li>', m.group(7), re.DOTALL)
                for i, item in enumerate(items, 1):
                    inner = self._html_inline_to_md(item)
                    lines.append(f'{i}. {inner}')

            # Unordered list
            elif m.group(8):
                items = re.findall(r'<li[^>]*>(.*?)</li>', m.group(9), re.DOTALL)
                for item in items:
                    inner = self._html_inline_to_md(item)
                    lines.append(f'- {inner}')

            # Horizontal rule
            elif m.group(10):
                lines.append('---')

            # Paragraph
            elif m.group(11):
                inner = m.group(13)

                # Empty paragraph = blank line
                if not inner.strip() or inner.strip() in ('<br />', '<br/>', '<br>'):
                    lines.append('')
                    continue

                # Horizontal rule unicode
                plain = re.sub(r'<[^>]+>', '', inner).strip()
                if plain and all(c in '\u2500\u2501\u2502\u2503' for c in plain):
                    lines.append('---')
                    continue

                inner_md = self._html_inline_to_md(inner)
                lines.append(inner_md)

        if not lines:
            return self.editor.toPlainText() + '\n'

        # Strip trailing empty lines
        while lines and lines[-1] == '':
            lines.pop()

        return '\n'.join(lines) + '\n'

    def _html_inline_to_md(self, html_text, skip_bold=False, skip_italic=False):
        """Convert inline HTML formatting to markdown syntax."""
        import re
        from html import unescape

        text = html_text

        # Inline code (font-family monospace/courier)
        def code_repl(m):
            inner = re.sub(r'<[^>]+>', '', m.group(1))
            return f'`{inner}`'
        text = re.sub(r'<span[^>]*font-family:[^>]*[Cc]ourier[^>]*>(.*?)</span>', code_repl, text)

        # Bold
        if not skip_bold:
            def bold_repl(m):
                inner = re.sub(r'<[^>]+>', '', m.group(1))
                return f'**{inner}**'
            text = re.sub(r'<span[^>]*font-weight:(?:bold|[6-9]\d\d)[^>]*>(.*?)</span>', bold_repl, text)
            text = re.sub(r'<b>(.*?)</b>', bold_repl, text)
            text = re.sub(r'<strong>(.*?)</strong>', bold_repl, text)

        # Italic
        if not skip_italic:
            def italic_repl(m):
                inner = re.sub(r'<[^>]+>', '', m.group(1))
                return f'*{inner}*'
            text = re.sub(r'<span[^>]*font-style:italic[^>]*>(.*?)</span>', italic_repl, text)
            text = re.sub(r'<i>(.*?)</i>', italic_repl, text)
            text = re.sub(r'<em>(.*?)</em>', italic_repl, text)

        # Strikethrough
        def strike_repl(m):
            inner = re.sub(r'<[^>]+>', '', m.group(1))
            return f'~~{inner}~~'
        text = re.sub(r'<span[^>]*text-decoration:[^>]*line-through[^>]*>(.*?)</span>', strike_repl, text)
        text = re.sub(r'<s>(.*?)</s>', strike_repl, text)
        text = re.sub(r'<del>(.*?)</del>', strike_repl, text)

        # Underline
        def underline_repl(m):
            inner = re.sub(r'<[^>]+>', '', m.group(1))
            return f'<u>{inner}</u>'
        text = re.sub(r'<span[^>]*text-decoration:[^>]*underline[^>]*>(.*?)</span>', underline_repl, text)

        # Strip remaining span tags
        text = re.sub(r'</?span[^>]*>', '', text)
        # Strip br tags
        text = re.sub(r'<br\s*/?>', '', text)

        text = unescape(text)
        return text.strip()

    def _strip_formatted_spaces(self):
        """Strip leading/trailing spaces from bold/italic/strikethrough runs.

        Markdown requires markers like ** to be adjacent to text. If a user
        bolds ' hello ', toMarkdown() produces '** hello **' which is invalid.
        This trims spaces so it becomes ' **hello** ' instead.
        """
        doc = self.editor.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()

        block = doc.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid():
                    fmt = fragment.charFormat()
                    is_formatted = (
                        fmt.fontWeight() == QFont.Weight.Bold
                        or fmt.fontItalic()
                        or fmt.fontStrikeOut()
                    )
                    if is_formatted:
                        text = fragment.text()
                        stripped = text.strip()
                        if stripped and stripped != text:
                            lead = len(text) - len(text.lstrip())
                            trail = len(text) - len(text.rstrip())
                            frag_start = fragment.position()
                            frag_end = frag_start + fragment.length()

                            # Remove formatting from leading spaces
                            if lead > 0:
                                cursor.setPosition(frag_start)
                                cursor.setPosition(frag_start + lead, QTextCursor.MoveMode.KeepAnchor)
                                plain_fmt = QTextCharFormat()
                                plain_fmt.setFontWeight(QFont.Weight.Normal)
                                plain_fmt.setFontItalic(False)
                                plain_fmt.setFontStrikeOut(False)
                                cursor.setCharFormat(plain_fmt)

                            # Remove formatting from trailing spaces
                            if trail > 0:
                                cursor.setPosition(frag_end - trail)
                                cursor.setPosition(frag_end, QTextCursor.MoveMode.KeepAnchor)
                                plain_fmt = QTextCharFormat()
                                plain_fmt.setFontWeight(QFont.Weight.Normal)
                                plain_fmt.setFontItalic(False)
                                plain_fmt.setFontStrikeOut(False)
                                cursor.setCharFormat(plain_fmt)
                it += 1
            block = block.next()

        cursor.endEditBlock()

    def _save_document(self):
        """Save the current document as Markdown."""
        notes_dir = CONFIG_DIR / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)

        if self._current_file:
            file_path = self._current_file
        else:
            title = self.title_input.text().strip() or "Untitled"
            default_name = f"{title}.md"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Note",
                str(notes_dir / default_name),
                "Markdown Files (*.md);;Text Files (*.txt)"
            )

        if file_path:
            try:
                content = self._document_to_markdown()

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self._current_file = file_path
                self._is_modified = False
                from pathlib import Path
                self.file_label.setText(Path(file_path).name)
                # Update title box if it was empty
                if not self.title_input.text().strip():
                    self.title_input.setText(Path(file_path).stem)
                self.status_label.setText("Saved")
                self.status_label.setStyleSheet(f"color: {DARK_THEME['success']}; font-size: 11px;")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

class DownloadEntry(QFrame):
    """Single download item widget showing filename, progress, and actions."""

    def __init__(self, filename: str, directory: str, parent=None):
        super().__init__(parent)
        self.filename = filename
        self.directory = directory
        self.filepath = os.path.join(directory, filename)

        self.setFixedHeight(48)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {DARK_THEME['surface']};
                border-radius: 4px;
                border: 1px solid {DARK_THEME['border']};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # Status icon
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(12, 12)
        self.status_icon.setStyleSheet("background-color: #2196F3; border-radius: 6px; border: none;")
        layout.addWidget(self.status_icon)

        # Info column
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        self.name_label = QLabel(filename)
        self.name_label.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {DARK_THEME['text_primary']}; border: none;")
        info_layout.addWidget(self.name_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {DARK_THEME['background']};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: #2196F3;
                border-radius: 2px;
            }}
        """)
        info_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Downloading... 0%")
        self.status_label.setStyleSheet(f"font-size: 10px; color: {DARK_THEME['text_secondary']}; border: none;")
        info_layout.addWidget(self.status_label)

        layout.addLayout(info_layout, 1)

        # Action buttons
        btn_style = f"""
            QPushButton {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent']};
                border-color: {DARK_THEME['accent']};
            }}
        """

        self.open_file_btn = QPushButton("Open")
        self.open_file_btn.setFixedHeight(22)
        self.open_file_btn.setStyleSheet(btn_style)
        self.open_file_btn.clicked.connect(self._open_file)
        self.open_file_btn.hide()
        layout.addWidget(self.open_file_btn)

        self.open_folder_btn = QPushButton("Folder")
        self.open_folder_btn.setFixedHeight(22)
        self.open_folder_btn.setStyleSheet(btn_style)
        self.open_folder_btn.clicked.connect(self._open_folder)
        self.open_folder_btn.hide()
        layout.addWidget(self.open_folder_btn)

    def update_progress(self, percent: int):
        """Update the progress bar and label."""
        if percent >= 0:
            self.progress_bar.setValue(percent)
            self.status_label.setText(f"Downloading... {percent}%")
        else:
            self.progress_bar.setRange(0, 0)  # Indeterminate
            self.status_label.setText("Downloading...")

    def set_completed(self):
        """Mark as completed."""
        self.progress_bar.setValue(100)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {DARK_THEME['background']};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: #4CAF50;
                border-radius: 2px;
            }}
        """)
        self.status_icon.setStyleSheet("background-color: #4CAF50; border-radius: 6px; border: none;")
        self.status_label.setText("Completed")
        self.status_label.setStyleSheet("font-size: 10px; color: #4CAF50; border: none;")
        self.open_file_btn.show()
        self.open_folder_btn.show()

    def set_failed(self):
        """Mark as failed."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {DARK_THEME['background']};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: #F44336;
                border-radius: 2px;
            }}
        """)
        self.status_icon.setStyleSheet("background-color: #F44336; border-radius: 6px; border: none;")
        self.status_label.setText("Failed")
        self.status_label.setStyleSheet("font-size: 10px; color: #F44336; border: none;")
        self.open_folder_btn.show()

    def set_cancelled(self):
        """Mark as cancelled."""
        self.progress_bar.setRange(0, 100)
        self.status_icon.setStyleSheet("background-color: #FF9800; border-radius: 6px; border: none;")
        self.status_label.setText("Cancelled")
        self.status_label.setStyleSheet("font-size: 10px; color: #FF9800; border: none;")

    def _open_file(self):
        """Open the downloaded file with the system default app."""
        import subprocess
        if os.path.exists(self.filepath):
            subprocess.Popen(["open", self.filepath])

    def _open_folder(self):
        """Reveal the file in Finder."""
        import subprocess
        if os.path.exists(self.filepath):
            subprocess.Popen(["open", "-R", self.filepath])
        elif os.path.isdir(self.directory):
            subprocess.Popen(["open", self.directory])


class DownloadsTab(QWidget):
    """Downloads manager tab with list of downloads and folder settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: Dict[str, DownloadEntry] = {}
        self._setup_ui()
        PlatformBrowser.add_download_listener(self._on_download_event)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(f"background-color: {DARK_THEME['surface']};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Downloads")
        title.setStyleSheet(f"color: {DARK_THEME['text_primary']}; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        change_folder_btn = QPushButton("Change Folder")
        change_folder_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent']};
                border-color: {DARK_THEME['accent']};
            }}
        """)
        change_folder_btn.clicked.connect(self._change_folder)
        header_layout.addWidget(change_folder_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent']};
                border-color: {DARK_THEME['accent']};
            }}
        """)
        clear_btn.clicked.connect(self._clear_all)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        # Folder path display
        folder_frame = QFrame()
        folder_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DARK_THEME['background']};
                border-bottom: 1px solid {DARK_THEME['border']};
            }}
        """)
        folder_layout = QHBoxLayout(folder_frame)
        folder_layout.setContentsMargins(12, 6, 12, 6)

        folder_icon = QLabel("Folder:")
        folder_icon.setStyleSheet(f"font-size: 11px; color: {DARK_THEME['text_secondary']};")
        folder_layout.addWidget(folder_icon)

        self.folder_label = QLabel(PlatformBrowser.get_download_directory())
        self.folder_label.setStyleSheet(f"font-size: 11px; color: {DARK_THEME['text_primary']};")
        folder_layout.addWidget(self.folder_label, 1)

        layout.addWidget(folder_frame)

        # Scroll area for download entries
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
        self.entries_layout = QVBoxLayout(self.scroll_content)
        self.entries_layout.setContentsMargins(8, 8, 8, 8)
        self.entries_layout.setSpacing(6)
        self.entries_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state label
        self.empty_label = QLabel("No downloads yet")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {DARK_THEME['text_secondary']}; font-size: 12px; padding: 40px;")
        self.entries_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

    def _on_download_event(self, filename: str, state: str, percent: int):
        """Handle download events and update the list."""
        if state == "started":
            # Hide the empty label
            self.empty_label.hide()

            directory = PlatformBrowser.get_download_directory()
            entry = DownloadEntry(filename, directory)
            self._entries[filename] = entry
            # Insert at top (index 0)
            self.entries_layout.insertWidget(0, entry)

        elif state == "progress" and filename in self._entries:
            self._entries[filename].update_progress(percent)

        elif state == "completed" and filename in self._entries:
            self._entries[filename].set_completed()

        elif state == "failed" and filename in self._entries:
            self._entries[filename].set_failed()

        elif state == "cancelled" and filename in self._entries:
            self._entries[filename].set_cancelled()

    def _change_folder(self):
        """Open folder picker to change download directory."""
        current = PlatformBrowser.get_download_directory()
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder", current)
        if folder:
            PlatformBrowser.set_download_directory(folder)
            self.folder_label.setText(folder)
            # Persist the setting
            settings_file = CONFIG_DIR / "download_settings.txt"
            settings_file.write_text(folder)

    def _clear_all(self):
        """Remove all download entries from the list."""
        for entry in self._entries.values():
            entry.deleteLater()
        self._entries.clear()
        self.empty_label.show()

    def load_saved_directory(self):
        """Load the saved download directory from config."""
        settings_file = CONFIG_DIR / "download_settings.txt"
        if settings_file.exists():
            saved_dir = settings_file.read_text().strip()
            if saved_dir and os.path.isdir(saved_dir):
                PlatformBrowser.set_download_directory(saved_dir)
                self.folder_label.setText(saved_dir)


class BrowserTabs(QWidget):
    """Tabbed widget containing embedded browser views, logs, and notebook."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.platform_tabs: Dict[str, PlatformTab] = {}
        self.log_tab: Optional[LogTab] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {DARK_THEME['border']};
                background-color: {DARK_THEME['background']};
            }}
            QTabBar::tab {{
                padding: 10px 20px;
                background-color: {DARK_THEME['surface']};
                border: 1px solid {DARK_THEME['border']};
                border-bottom: none;
                margin-right: 2px;
                color: {DARK_THEME['text_secondary']};
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background-color: {DARK_THEME['background']};
                border-bottom: 2px solid {DARK_THEME['accent']};
                color: {DARK_THEME['accent']};
            }}
            QTabBar::tab:hover {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
            }}
        """)

        platform_names = {
            "chatgpt": "ChatGPT",
            "gemini": "Gemini",
            "perplexity": "Perplexity",
            "claude": "Claude",
            "google": "Google"
        }

        for platform, url in PLATFORMS.items():
            tab = PlatformTab(platform, url)
            tab.openInGoogleTab.connect(self._open_in_google_tab)
            self.platform_tabs[platform] = tab
            self.tabs.addTab(tab, platform_names.get(platform, platform.title()))

        # Add Downloads tab
        self.downloads_tab = DownloadsTab()
        self.downloads_tab.load_saved_directory()
        self.tabs.addTab(self.downloads_tab, "Downloads")

        # Add Log tab at the end
        self.log_tab = LogTab()
        self.tabs.addTab(self.log_tab, "Log")

        layout.addWidget(self.tabs)

    def get_browser(self, platform: str) -> Optional[PlatformBrowser]:
        """Get the browser for a platform."""
        if platform in self.platform_tabs:
            return self.platform_tabs[platform].browser
        return None

    def append_log(self, message: str, level: str = "INFO"):
        """Append a log message to the log tab."""
        if self.log_tab:
            self.log_tab.append_log(message, level)

    def set_platform_status(self, platform: str, status: str, is_ready: bool = False):
        """Set the status for a platform tab."""
        if platform in self.platform_tabs:
            self.platform_tabs[platform].set_status(status, is_ready)

    def show_platform_tab(self, platform: str):
        """Switch to a specific platform tab."""
        if platform in self.platform_tabs:
            index = list(self.platform_tabs.keys()).index(platform)
            self.tabs.setCurrentIndex(index)

    def _open_in_google_tab(self, url: str):
        """Open a URL in the Google tab browser."""
        if "google" in self.platform_tabs:
            google_tab = self.platform_tabs["google"]
            google_tab.browser.navigate(url)
            self.show_platform_tab("google")

    def show_log_tab(self):
        """Switch to the log tab (at the end)."""
        self.tabs.setCurrentIndex(len(self.platform_tabs) + 1)

    def show_downloads_tab(self):
        """Switch to the downloads tab."""
        self.tabs.setCurrentIndex(len(self.platform_tabs))

    def clear_logs(self):
        """Clear the log output."""
        if self.log_tab:
            self.log_tab.clear()

    def get_active_platform(self) -> str:
        """Return the name of the currently visible platform tab."""
        current_index = self.tabs.currentIndex()
        platform_list = list(self.platform_tabs.keys())

        if current_index < len(platform_list):
            return platform_list[current_index]
        return ""

    def get_active_browser(self) -> Optional[PlatformBrowser]:
        """Return the browser for the active platform tab."""
        platform = self.get_active_platform()
        if platform:
            return self.get_browser(platform)
        return None
