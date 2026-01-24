"""Main entry point for ResearchBot."""

import logging
import sys
import traceback

# WebEngine must be imported before QApplication is created
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from config import APP_NAME, initialize_directories, setup_logging
from utils.local_storage import LocalStorage


def exception_hook(exc_type, exc_value, exc_traceback):
    """Global exception handler for uncaught exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = logging.getLogger(APP_NAME)
    logger.critical(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"Critical error:\n{error_msg}", file=sys.stderr)


def initialize_app() -> str:
    """Initialize application components and return session ID."""
    initialize_directories()

    storage = LocalStorage()
    session_id = storage.create_session()

    return session_id


def main():
    """Main application entry point."""
    sys.excepthook = exception_hook

    logger = setup_logging(logging.INFO)
    logger.info(f"Starting {APP_NAME}")

    try:
        session_id = initialize_app()
        logger.info(f"Initialized with session: {session_id}")
    except Exception as e:
        logger.error(f"Failed to initialize app: {e}")
        print(f"Error: Failed to initialize application: {e}")
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("ResearchBot")

    app.setStyle("Fusion")

    try:
        from ui.main_window import MainWindow
        window = MainWindow()
        window.show()

        logger.info("Application window shown")
        return app.exec()

    except Exception as e:
        logger.critical(f"Failed to start application: {e}")
        QMessageBox.critical(
            None,
            "Startup Error",
            f"Failed to start {APP_NAME}:\n\n{e}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
