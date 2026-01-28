"""Main application window for ResearchBot."""

import uuid
from datetime import datetime
from typing import Optional, List

from PyQt6.QtCore import QSettings, Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from agents.file_context_injector import FileContextInjector
from agents.response_merger import ResponseMerger
from agents.task_analyzer import TaskAnalyzer
from config import APP_NAME, APP_VERSION, DARK_THEME, WINDOW_HEIGHT, WINDOW_WIDTH
from ui.research_workspace import ResearchWorkspace
from ui.sidebar_tabs import BrowserTabs
from utils.clipboard_parser import ClipboardParser
from utils.export_service import ExportService
from utils.local_storage import LocalStorage
from utils.models import (
    MergedResponse,
    ModeType,
    PlatformResponse,
    PlatformType,
    TaskType,
    UserQuery,
)


class ResearchController(QObject):
    """Controller for managing research queries across platforms."""

    statusUpdate = pyqtSignal(str)
    platformQueried = pyqtSignal(str, str)  # platform, response
    allQueriesComplete = pyqtSignal(object)  # MergedResponse or None
    error = pyqtSignal(str)

    def __init__(self, browser_tabs: BrowserTabs, parent=None):
        super().__init__(parent)
        self.browser_tabs = browser_tabs
        self.storage = LocalStorage()
        self.merger = ResponseMerger()
        self.clipboard = ClipboardParser()

        self.current_query: Optional[UserQuery] = None
        self.platforms_to_query: List[str] = []
        self.current_platform_index = 0
        self.responses: List[PlatformResponse] = []
        self.query_id = ""

        self.response_check_timer = QTimer()
        self.response_check_timer.timeout.connect(self._check_for_response)
        self.response_check_count = 0
        self.max_response_checks = 30  # 60 seconds max wait per platform (30 checks * 2 seconds)
        self.last_response_length = 0
        self.stable_response_count = 0  # Count how many times response stayed same length

        # Track previous responses for duplicate detection
        self.previous_responses: dict = {}  # platform -> last response text

    def start_query(self, user_query: UserQuery):
        """Start a research query across platforms."""
        self.current_query = user_query
        self.query_id = str(uuid.uuid4())
        self.responses = []
        self.current_platform_index = 0

        try:
            self.storage.save_query(user_query)
        except Exception as e:
            self.statusUpdate.emit(f"Warning: Could not save query: {e}")

        self.platforms_to_query = TaskAnalyzer.get_platform_order(
            user_query.task.value,
            user_query.model_choice
        )

        self.statusUpdate.emit(f"Will query: {', '.join(self.platforms_to_query)}")

        file_context = ""
        if user_query.files:
            try:
                file_context = FileContextInjector.build_file_context(user_query.files)
            except Exception as e:
                self.statusUpdate.emit(f"Warning: Error processing files: {e}")

        self.full_prompt = FileContextInjector.inject_into_query(
            user_query.query_text,
            file_context
        )

        # Store files for potential direct upload (like PDFs to Gemini)
        self.current_files = user_query.files

        # Navigate to new chats on all platforms first
        self._navigate_to_new_chats()

    def _navigate_to_new_chats(self):
        """Navigate all platforms to new chat before starting queries."""
        self.statusUpdate.emit("Preparing new chats on all platforms...")
        self._new_chat_index = 0
        self._navigate_next_new_chat()

    def _navigate_next_new_chat(self):
        """Navigate to new chat for the next platform."""
        if self._new_chat_index >= len(self.platforms_to_query):
            # All platforms navigated, start querying
            self.statusUpdate.emit("Starting queries...")
            QTimer.singleShot(1000, self._query_next_platform)
            return

        platform = self.platforms_to_query[self._new_chat_index]
        browser = self.browser_tabs.get_browser(platform)

        if browser:
            self.statusUpdate.emit(f"Opening new chat on {platform}...")

            def on_new_chat_done(result):
                print(f"{platform} new chat: {result}")
                self._new_chat_index += 1
                # Wait a bit for the page to load
                QTimer.singleShot(1500, self._navigate_next_new_chat)

            browser.navigate_to_new_chat(on_new_chat_done)
        else:
            self._new_chat_index += 1
            QTimer.singleShot(100, self._navigate_next_new_chat)

    def _query_next_platform(self):
        """Query the next platform in the list."""
        if self.current_platform_index >= len(self.platforms_to_query):
            self._finish_queries()
            return

        platform = self.platforms_to_query[self.current_platform_index]
        self.statusUpdate.emit(f"Querying {platform}...")

        browser = self.browser_tabs.get_browser(platform)
        if not browser:
            self.statusUpdate.emit(f"Browser not available for {platform}")
            self.current_platform_index += 1
            QTimer.singleShot(500, self._query_next_platform)
            return

        self.browser_tabs.show_platform_tab(platform)

        system_prompt = TaskAnalyzer.build_system_prompt(platform, self.current_query.task.value)
        combined_prompt = f"{system_prompt}\n\n{self.full_prompt}"

        # Debug: log what's being sent
        self.statusUpdate.emit(f"Debug: Sending to {platform}, prompt length: {len(combined_prompt)}")
        print(f"Debug {platform}: system_prompt length: {len(system_prompt)}, full_prompt length: {len(self.full_prompt)}, combined length: {len(combined_prompt)}")

        # Store the prompt for potential retry
        self._current_combined_prompt = combined_prompt
        self._send_retry_count = 0

        # Check if page is ready before sending
        self._check_page_ready_and_send(browser, platform, combined_prompt)

    def _check_page_ready_and_send(self, browser, platform, combined_prompt):
        """Check if the page is ready and then send the query."""
        check_script = """
        (function() {
            // Check if there's an input element ready
            const selectors = [
                'textarea',
                'div[contenteditable="true"]',
                '#prompt-textarea'
            ];

            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el && el.offsetParent !== null) {
                    return 'ready';
                }
            }
            return 'not ready';
        })();
        """

        def on_check_result(result):
            if result == 'ready':
                browser.fill_input_and_send(combined_prompt, self._on_query_sent)
            else:
                self._send_retry_count += 1
                if self._send_retry_count < 5:
                    # Wait and retry
                    self.statusUpdate.emit(f"Waiting for {platform} page to be ready...")
                    QTimer.singleShot(1000, lambda: self._check_page_ready_and_send(browser, platform, combined_prompt))
                else:
                    # Give up and try anyway
                    self.statusUpdate.emit(f"Page may not be ready, attempting to send to {platform}...")
                    browser.fill_input_and_send(combined_prompt, self._on_query_sent)

        browser.execute_js(check_script, on_check_result)

    def _on_query_sent(self, result):
        """Handle query sent callback."""
        platform = self.platforms_to_query[self.current_platform_index]

        # Handle different result types
        if result is None:
            result = "unknown error"
        
        result_str = str(result) if result else "no result"
        
        if result_str == "sent" or result_str.startswith("sent"):
            self.statusUpdate.emit(f"Query sent to {platform}, waiting for response...")
            self.response_check_count = 0
            self.last_response_length = 0
            self.stable_response_count = 0
            # Wait a bit before starting to check for response
            self.response_check_count = 0  # Reset counter for new platform
            QTimer.singleShot(3000, lambda: self.response_check_timer.start(2000))
        else:
            error_msg = f"Failed to send query to {platform}"
            if result_str.startswith("error:"):
                error_msg += f": {result_str}"
            elif result_str != "unknown error":
                error_msg += f": {result_str}"
            self.statusUpdate.emit(error_msg)
            self.browser_tabs.append_log(f"{platform} send failed: {result_str}", "ERROR")
            self.current_platform_index += 1
            QTimer.singleShot(1000, self._query_next_platform)

    def _check_for_response(self):
        """Check if response is available."""
        self.response_check_count += 1

        if self.response_check_count >= self.max_response_checks:
            self.response_check_timer.stop()
            platform = self.platforms_to_query[self.current_platform_index]
            self.statusUpdate.emit(f"Timeout waiting for {platform}")
            self.current_platform_index += 1
            QTimer.singleShot(500, self._query_next_platform)
            return

        platform = self.platforms_to_query[self.current_platform_index]
        browser = self.browser_tabs.get_browser(platform)

        if browser:
            browser.get_response_text(self._on_response_received)

    def _on_response_received(self, response_text):
        """Handle response received from browser."""
        platform = self.platforms_to_query[self.current_platform_index]
        current_length = len(response_text.strip()) if response_text else 0

        # Check if we have a response and it has stabilized (AI finished generating)
        if current_length > 50:
            if current_length == self.last_response_length:
                self.stable_response_count += 1
            else:
                self.stable_response_count = 0
                self.last_response_length = current_length

            # Response is stable if same length for 2 consecutive checks (4 seconds) - reduced for faster processing
            if self.stable_response_count >= 2:
                if self.clipboard.validate_response(response_text):
                    cleaned_text = self.clipboard.clean_text(response_text)

                    # Check for duplicate response
                    previous = self.previous_responses.get(platform, "")
                    if previous and self._is_duplicate_response(previous, cleaned_text):
                        self.response_check_timer.stop()
                        self.statusUpdate.emit(f"Duplicate response detected from {platform}, skipping...")
                        self.browser_tabs.append_log(f"{platform}: Duplicate response detected (same as previous)", "WARNING")
                        self.current_platform_index += 1
                        QTimer.singleShot(1000, self._query_next_platform)
                        return

                    self.response_check_timer.stop()

                    # Store this response for future duplicate detection
                    self.previous_responses[platform] = cleaned_text

                    response = PlatformResponse(
                        platform=PlatformType(platform),
                        query_id=self.query_id,
                        response_text=cleaned_text,
                        timestamp=datetime.now()
                    )

                    self.responses.append(response)

                    try:
                        self.storage.save_response(response)
                    except Exception:
                        pass

                    self.statusUpdate.emit(f"Received response from {platform} ({current_length} chars)")
                    self.platformQueried.emit(platform, response_text[:100] + "...")

                    self.current_platform_index += 1
                    QTimer.singleShot(2000, self._query_next_platform)
                    return
            else:
                # Still generating, log progress
                if self.response_check_count % 5 == 0:
                    self.statusUpdate.emit(f"Waiting for {platform} response... ({current_length} chars so far)")

        # If we get here and no response yet, continue checking
        if current_length == 0:
            if self.response_check_count % 10 == 0:
                self.statusUpdate.emit(f"Still waiting for {platform} response... (check {self.response_check_count}/{self.max_response_checks})")
            # Don't return - continue checking
            return

        # If we have some response but it's not stable yet, continue checking
        if current_length > 0 and current_length < 50:
            if self.response_check_count % 5 == 0:
                self.statusUpdate.emit(f"Waiting for {platform} to generate more... ({current_length} chars so far)")
            return

    def _is_duplicate_response(self, previous: str, current: str) -> bool:
        """Check if the current response is a duplicate of the previous one."""
        # Normalize for comparison
        prev_normalized = previous.strip().lower()[:500]
        curr_normalized = current.strip().lower()[:500]

        # If they're very similar (90%+ match in first 500 chars), consider duplicate
        if prev_normalized == curr_normalized:
            return True

        # Check if first 200 chars match exactly
        if len(prev_normalized) > 200 and len(curr_normalized) > 200:
            if prev_normalized[:200] == curr_normalized[:200]:
                return True

        return False

    def _finish_queries(self):
        """Finish the query process and merge responses."""
        self.response_check_timer.stop()

        if not self.responses:
            self.statusUpdate.emit("No valid responses received")
            self.allQueriesComplete.emit(None)
            return

        self.statusUpdate.emit("Merging responses...")

        try:
            merged = self.merger.merge_responses(
                self.responses,
                self.query_id,
                self.current_query.session_id
            )

            try:
                self.storage.save_merged(merged)
            except Exception:
                pass

            self.statusUpdate.emit("Research complete!")
            self.allQueriesComplete.emit(merged)

        except Exception as e:
            self.statusUpdate.emit(f"Error merging responses: {e}")
            self.allQueriesComplete.emit(None)

    def stop(self):
        """Stop ongoing query."""
        self.response_check_timer.stop()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.storage = LocalStorage()
        self.current_session_id = self.storage.create_session()
        self.current_response: Optional[MergedResponse] = None
        self.research_controller: Optional[ResearchController] = None

        self._setup_ui()
        self._setup_menu()
        self._connect_signals()
        self._load_settings()

    def _setup_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1200, 700)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {DARK_THEME['background']};
            }}
            QWidget {{
                background-color: {DARK_THEME['background']};
                color: {DARK_THEME['text_primary']};
            }}
            QMenuBar {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border-bottom: 1px solid {DARK_THEME['border']};
            }}
            QMenuBar::item:selected {{
                background-color: {DARK_THEME['surface_light']};
            }}
            QMenu {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
            }}
            QMenu::item:selected {{
                background-color: {DARK_THEME['surface_light']};
            }}
            QStatusBar {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_secondary']};
                border-top: 1px solid {DARK_THEME['border']};
            }}
            QSplitter::handle {{
                background-color: {DARK_THEME['border']};
            }}
            QMessageBox {{
                background-color: {DARK_THEME['surface']};
            }}
            QMessageBox QLabel {{
                color: {DARK_THEME['text_primary']};
            }}
            QMessageBox QPushButton {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                padding: 6px 16px;
                border-radius: 4px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {DARK_THEME['accent']};
            }}
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 4, 8)

        self.browser_tabs = BrowserTabs()

        self.workspace = ResearchWorkspace(self.storage, self.browser_tabs)
        left_layout.addWidget(self.workspace, 1)

        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 8, 8, 8)

        right_layout.addWidget(self.browser_tabs)

        splitter.addWidget(right_widget)

        # Left side (workspace) gets 1/3, right side (browsers) gets 2/3
        splitter.setSizes([WINDOW_WIDTH // 3, WINDOW_WIDTH * 2 // 3])

        main_layout.addWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        self.research_controller = ResearchController(self.browser_tabs, self)
        self.research_controller.statusUpdate.connect(self._on_status_update)
        self.research_controller.allQueriesComplete.connect(self._on_research_complete)

        self.workspace.statusUpdate.connect(self._on_workspace_status)

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        new_session_action = file_menu.addAction("New Session")
        new_session_action.triggered.connect(self._new_session)

        file_menu.addSeparator()

        export_pdf_action = file_menu.addAction("Export to PDF")
        export_pdf_action.triggered.connect(lambda: self._export("pdf"))

        export_md_action = file_menu.addAction("Export to Markdown")
        export_md_action.triggered.connect(lambda: self._export("markdown"))

        file_menu.addSeparator()

        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        edit_menu = menubar.addMenu("Edit")

        clear_files_action = edit_menu.addAction("Clear Files")
        clear_files_action.triggered.connect(self.workspace.clear_files)

        help_menu = menubar.addMenu("Help")

        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self._show_about)

    def _connect_signals(self):
        pass

    def _load_settings(self):
        settings = QSettings(APP_NAME, APP_NAME)
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def _save_settings(self):
        settings = QSettings(APP_NAME, APP_NAME)
        settings.setValue("geometry", self.saveGeometry())

    def _on_workspace_status(self, message: str):
        """Handle status updates from workspace."""
        self.status_bar.showMessage(message)
        self.browser_tabs.append_log(message, "INFO")

    def _on_status_update(self, message: str):
        self.status_bar.showMessage(message)
        self.browser_tabs.append_log(message, "INFO")

    def _on_research_complete(self, result: Optional[MergedResponse]):
        if result:
            self.current_response = result
            self.browser_tabs.append_log("Research complete!", "SUCCESS")
        else:
            self.browser_tabs.append_log("Research failed - no valid responses", "ERROR")

        self.status_bar.showMessage("Ready")

    def _on_export(self):
        self._export("both")

    def _export(self, format_type: str):
        if not self.current_response:
            QMessageBox.warning(
                self,
                "No Response",
                "There is no response to export. Run a query first."
            )
            return

        if format_type == "pdf":
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF", "", "PDF Files (*.pdf)"
            )
            if file_path:
                success = ExportService.export_pdf(self.current_response, file_path)
                if success:
                    self.status_bar.showMessage(f"Exported to {file_path}")
                else:
                    QMessageBox.warning(self, "Export Failed", "Failed to export PDF.")

        elif format_type == "markdown":
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Markdown", "", "Markdown Files (*.md)"
            )
            if file_path:
                success = ExportService.export_markdown(self.current_response, file_path)
                if success:
                    self.status_bar.showMessage(f"Exported to {file_path}")
                else:
                    QMessageBox.warning(self, "Export Failed", "Failed to export Markdown.")

        elif format_type == "both":
            results = ExportService.export_both(self.current_response)
            if results["pdf"] and results["markdown"]:
                self.status_bar.showMessage("Exported to Downloads folder")
                self.browser_tabs.append_log("Exported PDF and Markdown", "SUCCESS")
            else:
                QMessageBox.warning(self, "Export Failed", "Some exports failed.")

    def _new_session(self):
        reply = QMessageBox.question(
            self,
            "New Session",
            "Start a new session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.current_session_id = self.storage.create_session()
            self.current_response = None
            self.workspace.clear_files()
            self.browser_tabs.clear_logs()
            self.status_bar.showMessage("New session started")

    def _show_about(self):
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "A multi-platform AI research orchestration tool.\n\n"
            "Query Gemini, Perplexity, and ChatGPT simultaneously "
            "and get merged, deduplicated responses.\n\n"
            "Built with Python and PyQt6."
        )

    def closeEvent(self, event):
        self._save_settings()

        if self.research_controller:
            self.research_controller.stop()

        event.accept()
