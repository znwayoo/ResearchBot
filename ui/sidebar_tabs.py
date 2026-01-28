"""Sidebar tabs widget with embedded browser views, logs, and markdown notebook."""

import time
from datetime import datetime
from typing import Dict, Optional

from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer, QEvent
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor, QAction, QTextListFormat

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


class PlatformBrowser(QWebEngineView):
    """Embedded browser for a platform."""

    responseReady = pyqtSignal(str)
    pageLoaded = pyqtSignal(str)

    # Shared profile for persistent cookies across all browsers
    _shared_profile = None

    def __init__(self, platform: str, parent=None):
        super().__init__(parent)
        self.platform = platform
        self._setup_browser()

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
        return cls._shared_profile

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

                    // Clear content by setting innerHTML
                    input.innerHTML = '';

                    // Set content directly - more reliable than execCommand
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
                    input.innerHTML = '';
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
        if self.platform == "google":
            self.browser.urlChanged.connect(self._on_url_changed)
        layout.addWidget(self.browser, 1)

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

        # Headers
        self.h1_btn = self._create_toolbar_btn("H1", lambda: self._set_heading(1))
        self.h2_btn = self._create_toolbar_btn("H2", lambda: self._set_heading(2))
        self.h3_btn = self._create_toolbar_btn("H3", lambda: self._set_heading(3))
        row1_layout.addWidget(self.h1_btn)
        row1_layout.addWidget(self.h2_btn)
        row1_layout.addWidget(self.h3_btn)

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

        row2_layout.addWidget(self._create_separator())

        # Alignment
        self.align_left_btn = self._create_toolbar_btn("Left", lambda: self._set_alignment(Qt.AlignmentFlag.AlignLeft))
        self.align_center_btn = self._create_toolbar_btn("Center", lambda: self._set_alignment(Qt.AlignmentFlag.AlignCenter))
        self.align_right_btn = self._create_toolbar_btn("Right", lambda: self._set_alignment(Qt.AlignmentFlag.AlignRight))
        row2_layout.addWidget(self.align_left_btn)
        row2_layout.addWidget(self.align_center_btn)
        row2_layout.addWidget(self.align_right_btn)

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
        self.editor.textChanged.connect(self._on_content_changed)
        # Note: Removed cursorPositionChanged signal - was causing crashes

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
        """Set the current paragraph as a heading."""
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)

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
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)

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

    def _set_alignment(self, alignment):
        """Set text alignment for current paragraph."""
        cursor = self.editor.textCursor()
        block_fmt = cursor.blockFormat()
        block_fmt.setAlignment(alignment)
        cursor.setBlockFormat(block_fmt)


    def _update_format_buttons(self):
        """Update toolbar button states - currently disabled to prevent crashes."""
        # This method is intentionally simplified - button states are not auto-updated
        # to prevent Qt signal/slot crashes during text editing
        pass

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

                # Check for header (large font) or special styling
                is_header = char_fmt.fontPointSize() >= 16
                has_margin = block_fmt.leftMargin() > 0

                if is_header or has_margin:
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
                    new_block_fmt.setIndent(0)
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
        """Format horizontal rule ---."""
        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        # Replace with a visual separator line using unicode
        cursor.removeSelectedText()

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(DARK_THEME['border']))
        cursor.insertText("─" * 50, fmt)

    def _format_quote(self, start, end, match):
        """Format quote > text."""
        content = match.group(1)

        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        cursor.removeSelectedText()

        # Set block format for quote
        block_fmt = cursor.blockFormat()
        block_fmt.setLeftMargin(20)
        cursor.setBlockFormat(block_fmt)

        # Set character format
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

                # Load as plain text - preserves the file content as-is
                self.editor.setPlainText(content)

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
                # Save plain text directly - preserves whatever the user typed as-is
                content = self.editor.toPlainText()

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self._current_file = file_path
                self._is_modified = False
                from pathlib import Path
                self.file_label.setText(Path(file_path).name)
                self.status_label.setText("Saved")
                self.status_label.setStyleSheet(f"color: {DARK_THEME['success']}; font-size: 11px;")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

class BrowserTabs(QWidget):
    """Tabbed widget containing embedded browser views, logs, and notebook."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.platform_tabs: Dict[str, PlatformTab] = {}
        self.log_tab: Optional[LogTab] = None
        self.notebook_tab: Optional[MarkdownNotebookTab] = None

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
            self.platform_tabs[platform] = tab
            self.tabs.addTab(tab, platform_names.get(platform, platform.title()))

        # Add Markdown Notebook tab
        self.notebook_tab = MarkdownNotebookTab()
        self.tabs.addTab(self.notebook_tab, "Notebook")

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

    def show_log_tab(self):
        """Switch to the log tab (at the end)."""
        self.tabs.setCurrentIndex(len(self.platform_tabs) + 1)

    def show_notebook_tab(self):
        """Switch to the notebook tab."""
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
