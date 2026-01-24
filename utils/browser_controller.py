"""Playwright browser automation controller for ResearchBot."""

import logging
import time
from typing import Dict, Optional

import pyperclip
from playwright.sync_api import Page, sync_playwright, TimeoutError as PlaywrightTimeout

from config import PLATFORMS, BROWSER_TIMEOUT, RESPONSE_WAIT_TIME

logger = logging.getLogger(__name__)


class BrowserController:
    """Singleton browser controller for automating AI platform interactions."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._playwright = None
        self._browser = None
        self._contexts: Dict[str, any] = {}
        self._pages: Dict[str, Page] = {}
        self._initialized = True

        self._selectors = {
            "perplexity": {
                "input": [
                    'textarea[placeholder="Ask anything..."]',
                    'textarea[placeholder="Ask follow-up..."]',
                    'div[contenteditable="true"]'
                ],
                "send": [
                    'button[aria-label="Submit"]',
                    'button[type="submit"]',
                    'button:has-text("Submit")'
                ],
                "response": [
                    'div[data-testid="response-container"]',
                    'div.prose',
                    'div[class*="answer"]'
                ],
                "copy": [
                    'button[title="Copy"]',
                    'button[aria-label="Copy"]',
                    'button:has-text("Copy")'
                ]
            },
            "gemini": {
                "input": [
                    'div[contenteditable="true"]',
                    'rich-textarea',
                    'textarea'
                ],
                "send": [
                    'button[aria-label="Send message"]',
                    'button[mattooltip="Send message"]',
                    'button.send-button'
                ],
                "response": [
                    'message-content',
                    'div[class*="response"]',
                    'div.model-response'
                ],
                "copy": [
                    'button[aria-label="Copy response"]',
                    'button[mattooltip="Copy"]',
                    'button:has-text("Copy")'
                ]
            },
            "chatgpt": {
                "input": [
                    'textarea[id="prompt-textarea"]',
                    'div[contenteditable="true"]',
                    'textarea'
                ],
                "send": [
                    'button[data-testid="send-button"]',
                    'button[aria-label="Send prompt"]',
                    'button:has-text("Send")'
                ],
                "response": [
                    'div[data-message-author-role="assistant"]',
                    'div[class*="markdown"]',
                    'div.agent-turn'
                ],
                "copy": [
                    'button[aria-label="Copy"]',
                    'button:has-text("Copy")',
                    'button[class*="copy"]'
                ]
            }
        }

    def start(self):
        """Start the Playwright browser."""
        if self._browser:
            return

        logger.info("Starting Playwright browser")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        logger.info("Browser started successfully")

    def get_page(self, platform: str) -> Optional[Page]:
        """Get or create a page for a platform."""
        if not self._browser:
            self.start()

        platform = platform.lower()
        if platform not in PLATFORMS:
            logger.error(f"Unknown platform: {platform}")
            return None

        if platform not in self._pages:
            logger.info(f"Creating new page for {platform}")
            context = self._browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = context.new_page()
            page.goto(PLATFORMS[platform], timeout=BROWSER_TIMEOUT * 1000)
            self._contexts[platform] = context
            self._pages[platform] = page
            time.sleep(2)

        return self._pages[platform]

    def _find_element(self, page: Page, selectors: list, timeout: int = 5000) -> Optional[any]:
        """Try multiple selectors to find an element."""
        for selector in selectors:
            try:
                element = page.wait_for_selector(selector, timeout=timeout)
                if element:
                    return element
            except PlaywrightTimeout:
                continue
        return None

    def fill_chat_input(self, platform: str, text: str) -> bool:
        """Fill the chat input field with query text."""
        page = self.get_page(platform)
        if not page:
            return False

        try:
            selectors = self._selectors[platform]["input"]
            element = self._find_element(page, selectors)

            if element:
                element.click()
                time.sleep(0.3)
                element.fill(text)
                logger.info(f"Filled input for {platform}")
                return True

            logger.warning(f"Could not find input field for {platform}")
            return False

        except Exception as e:
            logger.error(f"Error filling input for {platform}: {e}")
            return False

    def click_send(self, platform: str) -> bool:
        """Click the send button."""
        page = self.get_page(platform)
        if not page:
            return False

        try:
            selectors = self._selectors[platform]["send"]
            element = self._find_element(page, selectors)

            if element:
                element.click()
                logger.info(f"Clicked send for {platform}")
                return True

            page.keyboard.press("Enter")
            logger.info(f"Sent via Enter key for {platform}")
            return True

        except Exception as e:
            logger.error(f"Error clicking send for {platform}: {e}")
            return False

    def wait_for_response(self, platform: str, timeout: int = None) -> bool:
        """Wait for a response to appear."""
        if timeout is None:
            timeout = RESPONSE_WAIT_TIME

        page = self.get_page(platform)
        if not page:
            return False

        try:
            selectors = self._selectors[platform]["response"]

            for selector in selectors:
                try:
                    page.wait_for_selector(selector, timeout=timeout * 1000)
                    time.sleep(3)
                    logger.info(f"Response detected for {platform}")
                    return True
                except PlaywrightTimeout:
                    continue

            logger.warning(f"Timeout waiting for response from {platform}")
            return False

        except Exception as e:
            logger.error(f"Error waiting for response from {platform}: {e}")
            return False

    def copy_response(self, platform: str) -> bool:
        """Click copy button to copy response to clipboard."""
        page = self.get_page(platform)
        if not page:
            return False

        try:
            selectors = self._selectors[platform]["copy"]
            element = self._find_element(page, selectors, timeout=3000)

            if element:
                element.click()
                time.sleep(0.5)
                logger.info(f"Copied response from {platform}")
                return True

            logger.warning(f"Copy button not found for {platform}, attempting manual selection")
            return self._manual_copy_response(page, platform)

        except Exception as e:
            logger.error(f"Error copying response from {platform}: {e}")
            return False

    def _manual_copy_response(self, page: Page, platform: str) -> bool:
        """Manually select and copy response text."""
        try:
            selectors = self._selectors[platform]["response"]
            element = self._find_element(page, selectors)

            if element:
                text = element.inner_text()
                pyperclip.copy(text)
                logger.info(f"Manually copied response from {platform}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error in manual copy for {platform}: {e}")
            return False

    def get_clipboard_text(self) -> str:
        """Get text from system clipboard."""
        try:
            return pyperclip.paste()
        except Exception as e:
            logger.error(f"Error getting clipboard: {e}")
            return ""

    def is_logged_in(self, platform: str) -> bool:
        """Check if user is logged in to a platform."""
        page = self.get_page(platform)
        if not page:
            return False

        try:
            login_indicators = {
                "perplexity": ['button:has-text("Sign In")', 'a:has-text("Log in")'],
                "gemini": ['button:has-text("Sign in")', 'a:has-text("Sign in")'],
                "chatgpt": ['button:has-text("Log in")', 'a:has-text("Sign up")']
            }

            selectors = login_indicators.get(platform, [])
            for selector in selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=2000)
                    if element and element.is_visible():
                        return False
                except PlaywrightTimeout:
                    continue

            return True

        except Exception:
            return True

    def close_page(self, platform: str):
        """Close a specific platform page."""
        platform = platform.lower()
        if platform in self._pages:
            try:
                self._pages[platform].close()
                del self._pages[platform]
            except Exception as e:
                logger.error(f"Error closing page for {platform}: {e}")

        if platform in self._contexts:
            try:
                self._contexts[platform].close()
                del self._contexts[platform]
            except Exception as e:
                logger.error(f"Error closing context for {platform}: {e}")

    def close(self):
        """Close all browser resources."""
        logger.info("Closing browser")

        for platform in list(self._pages.keys()):
            self.close_page(platform)

        if self._browser:
            try:
                self._browser.close()
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            self._browser = None

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception as e:
                logger.error(f"Error stopping Playwright: {e}")
            self._playwright = None

        BrowserController._instance = None
        self._initialized = False
        logger.info("Browser closed")
