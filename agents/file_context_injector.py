"""File content extraction and query injection for ResearchBot."""

import csv
import logging
from pathlib import Path
from typing import List

from PyPDF2 import PdfReader
from docx import Document

from utils.models import UploadedFile

logger = logging.getLogger(__name__)


class FileContextInjector:
    """Handles file content extraction and injection into queries."""

    @staticmethod
    def extract_file_content(file_path: str) -> str:
        """Extract text content from a file based on its type."""
        path = Path(file_path)

        if not path.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()

        # Text-based file types that can be read directly
        text_types = {
            ".txt", ".md", ".markdown", ".json", ".xml", ".yaml", ".yml",
            ".html", ".htm", ".rtf", ".py", ".js", ".ts", ".jsx", ".tsx",
            ".java", ".c", ".cpp", ".h", ".hpp", ".css", ".scss", ".sass",
            ".sql", ".sh", ".bash", ".go", ".rs", ".rb", ".php",
            ".swift", ".kt", ".scala", ".r", ".ipynb",
            ".log", ".ini", ".conf", ".cfg", ".env", ".gitignore", ".dockerignore"
        }

        extractors = {
            ".pdf": FileContextInjector._extract_pdf,
            ".docx": FileContextInjector._extract_docx,
            ".csv": FileContextInjector._extract_csv
        }

        # Add all text types to use txt extractor
        for ext in text_types:
            extractors[ext] = FileContextInjector._extract_txt

        if suffix not in extractors:
            # Try to read as text anyway
            logger.warning(f"Unknown file type {suffix}, attempting to read as text")
            extractors[suffix] = FileContextInjector._extract_txt

        content = extractors[suffix](file_path)
        logger.info(f"Extracted {len(content)} characters from {path.name}")
        return content

    @staticmethod
    def _extract_pdf(file_path: str) -> str:
        """Extract text from a PDF file."""
        try:
            with open(file_path, "rb") as file:
                reader = PdfReader(file)
                text_parts = []
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                return "\n\n".join(text_parts).strip()
        except Exception as e:
            logger.error(f"Error extracting PDF: {e}")
            raise ValueError(f"Failed to extract PDF content: {e}")

    @staticmethod
    def _extract_docx(file_path: str) -> str:
        """Extract text from a DOCX file."""
        try:
            doc = Document(file_path)
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n\n".join(paragraphs).strip()
        except Exception as e:
            logger.error(f"Error extracting DOCX: {e}")
            raise ValueError(f"Failed to extract DOCX content: {e}")

    @staticmethod
    def _extract_txt(file_path: str) -> str:
        """Extract text from a plain text file."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read().strip()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as file:
                return file.read().strip()
        except Exception as e:
            logger.error(f"Error extracting TXT: {e}")
            raise ValueError(f"Failed to extract TXT content: {e}")

    @staticmethod
    def _extract_csv(file_path: str) -> str:
        """Extract CSV content and format as markdown table."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                reader = csv.reader(file)
                rows = list(reader)

            if not rows:
                return ""

            headers = rows[0]
            header_line = "| " + " | ".join(headers) + " |"
            separator = "|" + "|".join(["---"] * len(headers)) + "|"

            data_lines = []
            for row in rows[1:]:
                if len(row) == len(headers):
                    data_lines.append("| " + " | ".join(row) + " |")

            return "\n".join([header_line, separator] + data_lines)

        except Exception as e:
            logger.error(f"Error extracting CSV: {e}")
            raise ValueError(f"Failed to extract CSV content: {e}")

    @staticmethod
    def build_file_context(files: List[UploadedFile]) -> str:
        """Build combined context from multiple uploaded files."""
        if not files:
            return ""

        context_parts = ["## UPLOADED FILE CONTEXT\n"]

        for file in files:
            try:
                content = FileContextInjector.extract_file_content(file.path)
                context_parts.append(f"### File: {file.filename}")
                context_parts.append(content)
                context_parts.append("")
            except Exception as e:
                logger.warning(f"Skipping file {file.filename}: {e}")
                context_parts.append(f"### File: {file.filename}")
                context_parts.append(f"[Error extracting content: {e}]")
                context_parts.append("")

        return "\n".join(context_parts)

    @staticmethod
    def inject_into_query(query_text: str, file_context: str) -> str:
        """Inject file context into the query prompt."""
        if not file_context:
            return query_text

        return f"{file_context}\n\n## QUERY\n\n{query_text}"
