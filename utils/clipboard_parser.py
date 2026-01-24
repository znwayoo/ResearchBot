"""Clipboard text parsing and validation for ResearchBot."""

import logging
import re

import pyperclip

logger = logging.getLogger(__name__)


class ClipboardParser:
    """Handles clipboard text extraction, validation, and cleaning."""

    ERROR_PATTERNS = [
        r"i can't",
        r"i cannot",
        r"error",
        r"404",
        r"500",
        r"something went wrong",
        r"try again",
        r"unable to",
        r"not available"
    ]

    @staticmethod
    def get_text() -> str:
        """Get text from system clipboard."""
        try:
            return pyperclip.paste()
        except Exception as e:
            logger.error(f"Failed to get clipboard: {e}")
            return ""

    @staticmethod
    def validate_response(text: str) -> bool:
        """Validate that the response is valid and useful."""
        if not text or not text.strip():
            logger.warning("Empty response")
            return False

        text_lower = text.lower()

        for pattern in ClipboardParser.ERROR_PATTERNS:
            if re.search(pattern, text_lower):
                if len(text) < 200:
                    logger.warning(f"Response appears to be an error: {text[:100]}")
                    return False

        if len(text.strip()) < 50:
            logger.warning("Response too short")
            return False

        if len(text) > 50000:
            logger.warning("Response too long, will be truncated")

        return True

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize response text."""
        if not text:
            return ""

        text = text.strip()

        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"\t+", " ", text)

        lines = text.split("\n")
        cleaned_lines = [line.rstrip() for line in lines]
        text = "\n".join(cleaned_lines)

        return text

    @staticmethod
    def detect_format(text: str) -> str:
        """Detect the format of the response text."""
        if not text:
            return "plain"

        has_headers = bool(re.search(r"^#{1,6}\s", text, re.MULTILINE))
        has_lists = bool(re.search(r"^[\-\*\+]\s", text, re.MULTILINE))
        has_numbered = bool(re.search(r"^\d+\.\s", text, re.MULTILINE))
        has_bold = bool(re.search(r"\*\*[^*]+\*\*", text))
        has_code = bool(re.search(r"```", text))

        markdown_indicators = sum([has_headers, has_lists, has_numbered, has_bold, has_code])

        if markdown_indicators >= 2:
            return "markdown"
        elif has_headers or has_lists:
            return "structured"
        else:
            return "plain"

    @staticmethod
    def extract_sections(text: str) -> dict:
        """Extract sections from structured text."""
        sections = {
            "title": "",
            "introduction": "",
            "body": "",
            "conclusion": ""
        }

        lines = text.split("\n")

        for i, line in enumerate(lines):
            if line.startswith("# ") and not sections["title"]:
                sections["title"] = line[2:].strip()
            elif line.startswith("## "):
                section_name = line[3:].strip().lower()
                content_lines = []
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("## ") or lines[j].startswith("# "):
                        break
                    content_lines.append(lines[j])

                if "intro" in section_name or "overview" in section_name:
                    sections["introduction"] = "\n".join(content_lines).strip()
                elif "conclu" in section_name or "summary" in section_name:
                    sections["conclusion"] = "\n".join(content_lines).strip()

        if not sections["body"]:
            sections["body"] = text

        return sections

    @staticmethod
    def truncate_text(text: str, max_length: int = 50000) -> str:
        """Truncate text to maximum length while preserving structure."""
        if len(text) <= max_length:
            return text

        truncated = text[:max_length]

        last_para = truncated.rfind("\n\n")
        if last_para > max_length * 0.8:
            truncated = truncated[:last_para]

        truncated += "\n\n[Response truncated due to length]"

        return truncated
