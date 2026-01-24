"""PDF and Markdown export service for ResearchBot."""

import logging
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from utils.models import MergedResponse

logger = logging.getLogger(__name__)


class ExportService:
    """Handles exporting research results to PDF and Markdown formats."""

    DEFAULT_EXPORT_DIR = Path.home() / "Downloads"

    @staticmethod
    def get_default_filename(extension: str) -> str:
        """Generate a default filename with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"researchbot_report_{timestamp}.{extension}"

    @classmethod
    def export_pdf(
        cls,
        merged_response: MergedResponse,
        output_path: str = None
    ) -> bool:
        """Export the merged response to a PDF file."""
        if output_path is None:
            cls.DEFAULT_EXPORT_DIR.mkdir(exist_ok=True)
            output_path = str(cls.DEFAULT_EXPORT_DIR / cls.get_default_filename("pdf"))

        try:
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                rightMargin=0.75 * inch
            )

            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                spaceAfter=12
            )

            subtitle_style = ParagraphStyle(
                "CustomSubtitle",
                parent=styles["Normal"],
                fontSize=10,
                textColor="gray",
                spaceAfter=24
            )

            heading_style = ParagraphStyle(
                "CustomHeading",
                parent=styles["Heading2"],
                fontSize=14,
                spaceBefore=16,
                spaceAfter=8
            )

            body_style = ParagraphStyle(
                "CustomBody",
                parent=styles["Normal"],
                fontSize=11,
                leading=16,
                spaceAfter=8
            )

            story = []

            story.append(Paragraph("Research Report", title_style))

            timestamp = datetime.now().strftime("%B %d, %Y at %H:%M")
            story.append(Paragraph(f"Generated: {timestamp}", subtitle_style))

            story.append(Spacer(1, 0.25 * inch))

            lines = merged_response.merged_text.split("\n")

            for line in lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 0.1 * inch))
                elif line.startswith("# "):
                    text = cls._escape_html(line[2:])
                    story.append(Paragraph(text, title_style))
                elif line.startswith("## "):
                    text = cls._escape_html(line[3:])
                    story.append(Paragraph(text, heading_style))
                elif line.startswith("- "):
                    text = cls._escape_html(line[2:])
                    story.append(Paragraph(f"  * {text}", body_style))
                elif line == "---":
                    story.append(Spacer(1, 0.2 * inch))
                else:
                    text = cls._escape_html(line)
                    text = text.replace("**", "<b>").replace("**", "</b>")
                    story.append(Paragraph(text, body_style))

            story.append(Spacer(1, 0.5 * inch))

            if merged_response.attribution:
                story.append(Paragraph("Source Attribution", heading_style))
                for platform, data in merged_response.attribution.items():
                    word_count = data.get("word_count", 0)
                    text = f"{platform.title()}: {word_count} words contributed"
                    story.append(Paragraph(f"  * {text}", body_style))

            doc.build(story)

            logger.info(f"PDF exported to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export PDF: {e}")
            return False

    @classmethod
    def export_markdown(
        cls,
        merged_response: MergedResponse,
        output_path: str = None
    ) -> bool:
        """Export the merged response to a Markdown file."""
        if output_path is None:
            cls.DEFAULT_EXPORT_DIR.mkdir(exist_ok=True)
            output_path = str(cls.DEFAULT_EXPORT_DIR / cls.get_default_filename("md"))

        try:
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%B %d, %Y at %H:%M")

            content = f"""# Research Report

**Generated**: {timestamp}

---

{merged_response.merged_text}

---

## Export Information

- **Session ID**: {merged_response.session_id}
- **Query ID**: {merged_response.query_id}
- **Created**: {merged_response.created_at.strftime("%Y-%m-%d %H:%M:%S")}

### Platform Contributions

"""
            for platform, data in merged_response.attribution.items():
                word_count = data.get("word_count", 0)
                has_error = data.get("has_error", False)
                status = "with errors" if has_error else "successful"
                content += f"- **{platform.title()}**: {word_count} words ({status})\n"

            content += "\n---\n\n*Generated by ResearchBot*\n"

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Markdown exported to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export Markdown: {e}")
            return False

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters for PDF generation."""
        replacements = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    @classmethod
    def export_both(
        cls,
        merged_response: MergedResponse,
        base_path: str = None
    ) -> dict:
        """Export to both PDF and Markdown formats."""
        results = {"pdf": False, "markdown": False}

        if base_path:
            pdf_path = base_path.replace(".md", ".pdf").replace(".pdf", "") + ".pdf"
            md_path = base_path.replace(".pdf", ".md").replace(".md", "") + ".md"
        else:
            pdf_path = None
            md_path = None

        results["pdf"] = cls.export_pdf(merged_response, pdf_path)
        results["markdown"] = cls.export_markdown(merged_response, md_path)

        return results
