"""Sidebar tabs widget with embedded browser views and logs."""

from datetime import datetime
from typing import Dict, Optional

from PyQt6.QtCore import QUrl, pyqtSignal, QTimer
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
            from config import CONFIG_DIR
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
        from PyQt6.QtWebEngineCore import QWebEnginePage

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
        import time
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
                    // For contenteditable, clear first
                    input.focus();
                    input.textContent = '';
                    document.execCommand('selectAll', false, null);
                    document.execCommand('delete', false, null);
                    
                    // Insert text character by character to ensure it all gets in
                    // (some browsers limit execCommand insertText length)
                    const chunks = text.match(/.{{1,1000}}/g) || [text];
                    for (let chunk of chunks) {{
                        document.execCommand('insertText', false, chunk);
                    }}

                    // Verify the text was inserted
                    if (!input.textContent || input.textContent.length < text.length / 2) {{
                        console.log('Gemini: execCommand may have failed, trying textContent');
                        input.textContent = text;
                    }}

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
                    // Try to find any visible textarea or contenteditable
                    const allTextareas = document.querySelectorAll('textarea, div[contenteditable="true"]');
                    const info = [];
                    allTextareas.forEach((t, idx) => {{
                        if (idx < 5) {{
                            const visible = t.offsetParent !== null;
                            const placeholder = t.placeholder || t.getAttribute('placeholder') || 'no-ph';
                            const role = t.getAttribute('role') || 'no-role';
                            info.push('el' + idx + ':' + t.tagName + ':ph=' + placeholder + ':role=' + role + ':visible=' + visible);
                        }}
                    }});
                    return 'input not found. Found: ' + info.join(', ');
                }}

                // Focus and click the input
                textarea.focus();
                textarea.click();

                const text = '{escaped_text}';

                // Clear existing content first - be more aggressive
                if (textarea.tagName === 'TEXTAREA' || textarea.tagName === 'INPUT') {{
                    // Clear using native setter first
                    const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value'
                    ).set;
                    nativeTextAreaValueSetter.call(textarea, '');
                    textarea.select();
                }} else {{
                    // For contenteditable, clear innerHTML
                    textarea.textContent = '';
                }}
                
                // Double-check clear with execCommand
                document.execCommand('selectAll', false, null);
                document.execCommand('delete', false, null);

                // Set the value - use only ONE method to avoid duplication
                if (textarea.tagName === 'TEXTAREA' || textarea.tagName === 'INPUT') {{
                    // For textarea/input, use native setter (most reliable)
                    const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value'
                    ).set;
                    nativeTextAreaValueSetter.call(textarea, text);

                    // Dispatch React-compatible events
                    const inputEvent = new Event('input', {{ bubbles: true, cancelable: true }});
                    Object.defineProperty(inputEvent, 'target', {{ value: textarea }});
                    textarea.dispatchEvent(inputEvent);
                    textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }} else {{
                    // For contenteditable divs, use execCommand
                    document.execCommand('insertText', false, text);
                    
                    // Trigger input events
                    textarea.dispatchEvent(new InputEvent('input', {{
                        bubbles: true,
                        cancelable: true,
                        inputType: 'insertText',
                        data: text
                    }}));
                }}

                window._perplexityTextarea = textarea;
                return 'filled';
            }} catch (error) {{
                console.error('Perplexity fill error:', error);
                return 'error: ' + error.message;
            }}
        }})();
        """

        def on_fill_result(result):
            # Debug: log the result
            print(f"Perplexity fill result: {result}")
            if result and result != 'filled':
                # If there's an error (like "input not found"), pass it to callback
                if callback:
                    callback(result)
                return
            
            # Step 2: Wait a bit, then click send
            def click_send():
                send_script = """
                (function() {
                    try {
                        const textarea = window._perplexityTextarea;
                        if (!textarea) {
                            return 'no textarea';
                        }

                        console.log('Perplexity: Textarea value length:', textarea.value ? textarea.value.length : 0);

                        const sendSelectors = [
                            'button[aria-label*="Submit"]',
                            'button[aria-label*="submit"]',
                            'button[aria-label*="Send"]',
                            'button[type="submit"]',
                            'button[class*="bg-super"]',
                            'button[class*="submit"]',
                            'button[class*="send"]'
                        ];

                        let sendBtn = null;
                        for (const sel of sendSelectors) {
                            const btn = document.querySelector(sel);
                            if (btn && !btn.disabled && btn.offsetParent !== null) {
                                sendBtn = btn;
                                console.log('Perplexity: Found send button with selector:', sel);
                                break;
                            }
                        }

                        if (!sendBtn) {
                            const form = textarea.closest('form');
                            if (form) {
                                sendBtn = form.querySelector('button[type="submit"], button:last-of-type');
                                if (sendBtn) console.log('Perplexity: Found send button in form');
                            }
                        }

                        if (!sendBtn) {
                            const parent = textarea.parentElement?.parentElement;
                            if (parent) {
                                const buttons = parent.querySelectorAll('button');
                                for (const btn of buttons) {
                                    if (!btn.disabled && btn.offsetParent !== null) {
                                        sendBtn = btn;
                                        console.log('Perplexity: Found send button in parent');
                                        break;
                                    }
                                }
                            }
                        }

                        if (sendBtn) {
                            console.log('Perplexity: Clicking send button');
                            sendBtn.click();
                            return 'sent';
                        } else {
                            console.log('Perplexity: No button found, trying Enter key');
                            textarea.dispatchEvent(new KeyboardEvent('keydown', {
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
                           .replace("\r", "\\r"))

        script = f"""
        (function() {{
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

            // Wait and click send
            return new Promise((resolve) => {{
                setTimeout(() => {{
                    const sendSelectors = [
                        'button[data-testid="send-button"]',
                        'button[aria-label*="Send message"]',
                        'button[aria-label*="Send prompt"]',
                        'button[aria-label*="Send"]',
                        'form button[type="submit"]'
                    ];

                    let sendBtn = null;
                    for (const sel of sendSelectors) {{
                        const btn = document.querySelector(sel);
                        if (btn && !btn.disabled && btn.offsetParent !== null) {{
                            sendBtn = btn;
                            break;
                        }}
                    }}

                    if (sendBtn) {{
                        console.log('ChatGPT: Clicking send button');
                        sendBtn.click();
                        resolve('sent');
                    }} else {{
                        // Try Ctrl+Enter or just Enter
                        input.dispatchEvent(new KeyboardEvent('keydown', {{
                            key: 'Enter',
                            code: 'Enter',
                            keyCode: 13,
                            which: 13,
                            ctrlKey: false,
                            bubbles: true,
                            cancelable: true
                        }}));
                        resolve('sent via enter');
                    }}
                }}, 500);
            }});
        }})();
        """

        if callback:
            self.execute_js(script, callback)
        else:
            self.execute_js(script)

    def get_response_text(self, callback):
        """Extract response text from the page."""
        if self.platform == "gemini":
            self._get_gemini_response(callback)
        elif self.platform == "perplexity":
            self._get_perplexity_response(callback)
        elif self.platform == "chatgpt":
            self._get_chatgpt_response(callback)
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
        else:
            script = "return false;"

        self.execute_js(script, callback)

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
        return """
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
        from PyQt6.QtWidgets import QMessageBox

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
