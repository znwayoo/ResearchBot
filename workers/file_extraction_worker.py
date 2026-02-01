"""Background worker for async file content extraction."""

from typing import List

from PyQt6.QtCore import QThread, pyqtSignal

from agents.file_context_injector import FileContextInjector
from utils.models import UploadedFile


class FileExtractionWorker(QThread):
    """Extracts file content in a background thread."""

    progressUpdate = pyqtSignal(int, int, str)  # current, total, filename
    extractionComplete = pyqtSignal(str)  # full context string
    extractionError = pyqtSignal(str)

    def __init__(self, files: List[UploadedFile], parent=None):
        super().__init__(parent)
        self.files = files

    def run(self):
        try:
            total = len(self.files)
            context_parts = ["## UPLOADED FILE CONTEXT\n"]

            for i, file in enumerate(self.files):
                self.progressUpdate.emit(i + 1, total, file.filename)
                try:
                    content = FileContextInjector.extract_file_content(file.path)
                    context_parts.append(f"### File: {file.filename}")
                    context_parts.append(content)
                    context_parts.append("")
                except Exception as e:
                    context_parts.append(f"### File: {file.filename}")
                    context_parts.append(f"[Error extracting content: {e}]")
                    context_parts.append("")

            self.extractionComplete.emit("\n".join(context_parts))
        except Exception as e:
            self.extractionError.emit(str(e))
