"""Main application window for ResearchBot."""

import uuid
from typing import Optional

from PyQt6.QtCore import QSettings, Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from agents.orchestrator import Orchestrator
from config import APP_NAME, APP_VERSION, WINDOW_HEIGHT, WINDOW_WIDTH
from ui.chat_widget import ChatWidget
from ui.input_panel import InputPanel
from ui.sidebar_tabs import BrowserTabs
from utils.export_service import ExportService
from utils.local_storage import LocalStorage
from utils.models import MergedResponse, ModeType, TaskType, UserQuery


class ResearchWorker(QThread):
    """Background worker for running research queries."""

    statusUpdate = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, orchestrator: Orchestrator, query: UserQuery):
        super().__init__()
        self.orchestrator = orchestrator
        self.query = query

    def run(self):
        try:
            self.orchestrator.status_callback = self.statusUpdate.emit
            result = self.orchestrator.execute_query(self.query)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.storage = LocalStorage()
        self.orchestrator = Orchestrator(storage=self.storage)
        self.current_session_id = self.storage.create_session()
        self.current_response: Optional[MergedResponse] = None
        self.worker: Optional[ResearchWorker] = None

        self._setup_ui()
        self._setup_menu()
        self._connect_signals()
        self._load_settings()

    def _setup_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1200, 700)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 4, 8)

        self.chat_widget = ChatWidget()
        left_layout.addWidget(self.chat_widget, 1)

        self.input_panel = InputPanel()
        left_layout.addWidget(self.input_panel)

        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 8, 8, 8)

        self.browser_tabs = BrowserTabs()
        right_layout.addWidget(self.browser_tabs)

        splitter.addWidget(right_widget)

        splitter.setSizes([WINDOW_WIDTH // 2, WINDOW_WIDTH // 2])

        main_layout.addWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        self.chat_widget.add_bot_message(
            "Welcome to ResearchBot! I can help you research topics across "
            "multiple AI platforms simultaneously.\n\n"
            "Upload files, type your query, and click Send to begin."
        )

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

        clear_chat_action = edit_menu.addAction("Clear Chat")
        clear_chat_action.triggered.connect(self._clear_chat)

        clear_files_action = edit_menu.addAction("Clear Files")
        clear_files_action.triggered.connect(self.input_panel.clear_files)

        help_menu = menubar.addMenu("Help")

        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self._show_about)

    def _connect_signals(self):
        self.input_panel.sendClicked.connect(self._on_send)
        self.input_panel.exportClicked.connect(self._on_export)
        self.browser_tabs.launchBrowserRequested.connect(self._on_launch_browser)

    def _load_settings(self):
        settings = QSettings(APP_NAME, APP_NAME)
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def _save_settings(self):
        settings = QSettings(APP_NAME, APP_NAME)
        settings.setValue("geometry", self.saveGeometry())

    def _on_launch_browser(self, platform: str):
        """Launch browser for a platform so user can login."""
        self.status_bar.showMessage(f"Opening {platform.title()} browser...")
        self.browser_tabs.append_log(f"Launching {platform} browser...", "INFO")

        try:
            page = self.orchestrator.browser.get_page(platform)
            if page:
                self.browser_tabs.set_platform_status(platform, "Browser open", True)
                self.browser_tabs.append_log(f"{platform.title()} browser opened successfully", "SUCCESS")
                self.status_bar.showMessage(f"{platform.title()} browser opened - please login if needed")
            else:
                self.browser_tabs.append_log(f"Failed to open {platform} browser", "ERROR")
                self.status_bar.showMessage(f"Failed to open {platform.title()} browser")
        except Exception as e:
            self.browser_tabs.append_log(f"Error opening {platform}: {e}", "ERROR")
            self.status_bar.showMessage(f"Error: {e}")

    def _on_send(self):
        query_text = self.input_panel.get_query()
        if not query_text:
            return

        self.chat_widget.add_user_message(query_text)

        task_map = {
            "initial": TaskType.INITIAL,
            "targeted": TaskType.TARGETED,
            "draft": TaskType.DRAFT
        }

        mode_map = {
            "auto": ModeType.AUTO,
            "manual": ModeType.MANUAL
        }

        user_query = UserQuery(
            session_id=self.current_session_id,
            query_text=query_text,
            files=self.input_panel.get_files(),
            model_choice=self.input_panel.get_model(),
            mode=mode_map.get(self.input_panel.get_mode(), ModeType.AUTO),
            task=task_map.get(self.input_panel.get_task(), TaskType.INITIAL)
        )

        self.input_panel.set_send_enabled(False)
        self.input_panel.set_status("Researching...", "#FF9800")

        self.worker = ResearchWorker(self.orchestrator, user_query)
        self.worker.statusUpdate.connect(self._on_status_update)
        self.worker.finished.connect(self._on_research_complete)
        self.worker.error.connect(self._on_research_error)
        self.worker.start()

        self.input_panel.clear_input()

    def _on_status_update(self, message: str):
        self.status_bar.showMessage(message)
        self.browser_tabs.append_log(message, "INFO")

    def _on_research_complete(self, result: Optional[MergedResponse]):
        self.input_panel.set_send_enabled(True)

        if result:
            self.current_response = result
            self.chat_widget.add_bot_message(result.merged_text)
            self.input_panel.set_status("Done", "#4CAF50")
            self.input_panel.set_export_enabled(True)
            self.browser_tabs.append_log("Research complete!", "SUCCESS")
        else:
            self.chat_widget.add_bot_message(
                "Sorry, I could not get responses from the AI platforms. "
                "Please make sure you are logged in to each platform."
            )
            self.input_panel.set_status("Failed", "#F44336")
            self.browser_tabs.append_log("Research failed", "ERROR")

        self.status_bar.showMessage("Ready")

    def _on_research_error(self, error: str):
        self.input_panel.set_send_enabled(True)
        self.input_panel.set_status("Error", "#F44336")

        self.chat_widget.add_bot_message(f"An error occurred: {error}")
        self.browser_tabs.append_log(f"Error: {error}", "ERROR")
        self.status_bar.showMessage("Ready")

    def _on_export(self):
        if self.current_response:
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
            "Start a new session? Current chat will be cleared.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.current_session_id = self.storage.create_session()
            self.current_response = None
            self.chat_widget.clear_chat()
            self.input_panel.clear_files()
            self.input_panel.set_export_enabled(False)
            self.browser_tabs.clear_logs()

            self.chat_widget.add_bot_message(
                "New session started. Ready to research!"
            )

    def _clear_chat(self):
        self.chat_widget.clear_chat()
        self.chat_widget.add_bot_message(
            "Chat cleared. Ready for new queries."
        )

    def _show_about(self):
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "A multi-platform AI research orchestration tool.\n\n"
            "Query Gemini, Perplexity, and ChatGPT simultaneously "
            "and get merged, deduplicated responses.\n\n"
            "Built with Python, PyQt6, and Playwright."
        )

    def closeEvent(self, event):
        self._save_settings()

        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()

        try:
            self.orchestrator.cleanup()
        except Exception:
            pass

        event.accept()
