"""Sidebar tabs widget with embedded browser views, logs, and Jupyter notebook."""

import time
from datetime import datetime
from typing import Dict, Optional

from PyQt6.QtCore import QUrl, pyqtSignal, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import CONFIG_DIR, DARK_THEME, PLATFORMS


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
        page = QWebEnginePage(profile, self)
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

        # Create and add the browser
        self.browser = PlatformBrowser(self.platform)
        self.browser.pageLoaded.connect(self._on_page_loaded)
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


class JupyterNotebookTab(QWidget):
    """Widget for embedded Jupyter Notebook using QWebEngineView."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.jupyter_process = None
        self.jupyter_url = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with URL input
        header = QFrame()
        header.setStyleSheet(f"background-color: {DARK_THEME['surface']}; border-bottom: 1px solid {DARK_THEME['border']};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)

        title = QLabel("Notebook:")
        title.setStyleSheet(f"color: {DARK_THEME['text_primary']}; font-weight: bold;")
        header_layout.addWidget(title)

        # URL input field
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter Jupyter URL (e.g., http://localhost:8888)")
        self.url_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {DARK_THEME['accent']};
            }}
        """)
        self.url_input.returnPressed.connect(self._connect_to_server)
        header_layout.addWidget(self.url_input, 1)

        # Connect button
        connect_btn = QPushButton("Connect")
        connect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['accent']};
                color: white;
                border-radius: 3px;
                padding: 4px 12px;
                border: none;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent_hover']};
            }}
        """)
        connect_btn.clicked.connect(self._connect_to_server)
        header_layout.addWidget(connect_btn)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border-radius: 3px;
                padding: 4px 12px;
                border: 1px solid {DARK_THEME['border']};
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent']};
            }}
        """)
        refresh_btn.clicked.connect(self._refresh_notebook)
        header_layout.addWidget(refresh_btn)

        # Auto-start button
        autostart_btn = QPushButton("Auto Start")
        autostart_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border-radius: 3px;
                padding: 4px 12px;
                border: 1px solid {DARK_THEME['border']};
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['success']};
            }}
        """)
        autostart_btn.clicked.connect(self._start_jupyter_server)
        header_layout.addWidget(autostart_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {DARK_THEME['text_secondary']}; font-size: 11px;")
        header_layout.addWidget(self.status_label)

        layout.addWidget(header)

        # Browser view for Jupyter
        self.browser = QWebEngineView()
        self.browser.setStyleSheet("background-color: #1e1e1e;")
        layout.addWidget(self.browser, 1)

        # Welcome page
        self._show_welcome_page()

    def _show_welcome_page(self):
        """Show welcome page with instructions."""
        self.browser.setHtml(f"""
            <html>
            <body style="background-color: #1e1e1e; color: #d4d4d4; font-family: sans-serif;
                         display: flex; justify-content: center; align-items: center; height: 100vh;">
                <div style="text-align: center; max-width: 600px;">
                    <h2 style="color: #2196F3;">Jupyter Notebook</h2>
                    <p>Connect to an existing Jupyter server or start a new one.</p>

                    <div style="background: #2d2d2d; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: left;">
                        <h3 style="color: #4CAF50; margin-top: 0;">Option 1: Connect to Existing Server</h3>
                        <p>If you already have Jupyter running, enter the URL above and click Connect.</p>
                        <code style="background: #1e1e1e; padding: 4px 8px; border-radius: 4px;">http://localhost:8888</code>
                    </div>

                    <div style="background: #2d2d2d; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: left;">
                        <h3 style="color: #FF9800; margin-top: 0;">Option 2: Start New Server</h3>
                        <p>Click "Auto Start" to launch a new Jupyter server.</p>
                        <p style="color: #888; font-size: 12px;">Requires: <code style="background: #1e1e1e; padding: 2px 6px; border-radius: 4px;">pip install jupyter notebook</code></p>
                    </div>

                    <div style="background: #2d2d2d; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: left;">
                        <h3 style="color: #9C27B0; margin-top: 0;">Option 3: Start Manually</h3>
                        <p>Run in terminal:</p>
                        <code style="background: #1e1e1e; padding: 8px 12px; border-radius: 4px; display: block; margin-top: 8px;">jupyter notebook --no-browser</code>
                        <p style="margin-top: 10px;">Then copy the URL and paste it above.</p>
                    </div>
                </div>
            </body>
            </html>
        """)

    def _connect_to_server(self):
        """Connect to a Jupyter server URL."""
        url = self.url_input.text().strip()
        if not url:
            self.status_label.setText("Enter a URL")
            self.status_label.setStyleSheet(f"color: {DARK_THEME['warning']}; font-size: 11px;")
            return

        if not url.startswith("http"):
            url = "http://" + url

        self.jupyter_url = url
        self.status_label.setText("Connecting...")
        self.status_label.setStyleSheet(f"color: {DARK_THEME['accent']}; font-size: 11px;")
        self.browser.setUrl(QUrl(url))

        # Update status after load
        self.browser.loadFinished.connect(self._on_load_finished)

    def _on_load_finished(self, success):
        """Handle page load completion."""
        if success:
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet(f"color: {DARK_THEME['success']}; font-size: 11px;")
        else:
            self.status_label.setText("Failed to connect")
            self.status_label.setStyleSheet(f"color: {DARK_THEME['error']}; font-size: 11px;")

    def _start_jupyter_server(self):
        """Start a Jupyter Notebook server in the background."""
        import subprocess
        import threading
        import sys

        self.status_label.setText("Starting server...")
        self.status_label.setStyleSheet(f"color: {DARK_THEME['warning']}; font-size: 11px;")

        def start_server():
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('', 0))
                port = sock.getsockname()[1]
                sock.close()

                notebooks_dir = CONFIG_DIR / "notebooks"
                notebooks_dir.mkdir(parents=True, exist_ok=True)

                python_exe = sys.executable

                self.jupyter_process = subprocess.Popen(
                    [
                        python_exe, "-m", "jupyter", "notebook",
                        "--no-browser",
                        f"--port={port}",
                        "--NotebookApp.token=''",
                        "--NotebookApp.password=''",
                        f"--notebook-dir={str(notebooks_dir)}",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(notebooks_dir)
                )

                url = f"http://localhost:{port}"
                time.sleep(3)

                if self.jupyter_process.poll() is not None:
                    output = self.jupyter_process.stdout.read() if self.jupyter_process.stdout else ""
                    QTimer.singleShot(0, lambda: self._on_server_error(f"Failed: {output[:300]}"))
                    return

                QTimer.singleShot(0, lambda: self._on_server_started(url))

            except Exception as e:
                QTimer.singleShot(0, lambda: self._on_server_error(str(e)))

        thread = threading.Thread(target=start_server, daemon=True)
        thread.start()

    def _on_server_started(self, url):
        """Called when server starts successfully."""
        self.jupyter_url = url
        self.url_input.setText(url)
        self.status_label.setText("Server running")
        self.status_label.setStyleSheet(f"color: {DARK_THEME['success']}; font-size: 11px;")
        self.browser.setUrl(QUrl(url))

    def _on_server_error(self, error_msg: str):
        """Called when server fails to start."""
        self.status_label.setText("Error")
        self.status_label.setStyleSheet(f"color: {DARK_THEME['error']}; font-size: 11px;")
        self.browser.setHtml(f"""
            <html>
            <body style="background-color: #1e1e1e; color: #d4d4d4; font-family: sans-serif;
                         display: flex; justify-content: center; align-items: center; height: 100vh;">
                <div style="text-align: center;">
                    <h2 style="color: #ff6b6b;">Failed to Start Jupyter Server</h2>
                    <p style="max-width: 500px;">{error_msg}</p>
                    <p style="color: #888;">Install Jupyter with:</p>
                    <code style="background: #2d2d2d; padding: 8px 16px; border-radius: 4px;">pip install jupyter notebook</code>
                </div>
            </body>
            </html>
        """)

    def _refresh_notebook(self):
        """Refresh the notebook view."""
        if self.jupyter_url:
            self.browser.reload()
        else:
            self._show_welcome_page()

    def _cleanup(self):
        """Clean up Jupyter server resources."""
        if self.jupyter_process:
            try:
                self.jupyter_process.terminate()
                self.jupyter_process.wait(timeout=5)
            except Exception:
                try:
                    self.jupyter_process.kill()
                except Exception:
                    pass
            self.jupyter_process = None
        self.jupyter_url = None

    def closeEvent(self, event):
        """Clean up when closing."""
        self._cleanup()
        super().closeEvent(event)


class BrowserTabs(QWidget):
    """Tabbed widget containing embedded browser views, logs, and Jupyter notebook."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.platform_tabs: Dict[str, PlatformTab] = {}
        self.log_tab: Optional[LogTab] = None
        self.jupyter_tab: Optional[JupyterNotebookTab] = None

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

        # Add Jupyter Notebook tab
        self.jupyter_tab = JupyterNotebookTab()
        self.tabs.addTab(self.jupyter_tab, "Notebook")

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
        """Switch to the Jupyter notebook tab."""
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
