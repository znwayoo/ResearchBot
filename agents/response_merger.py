"""Response merging and deduplication for ResearchBot."""

import logging
import re
from typing import Dict, List

from utils.models import MergedResponse, PlatformResponse

logger = logging.getLogger(__name__)


class ResponseMerger:
    """Merges and deduplicates responses from multiple AI platforms."""

    SECTION_KEYWORDS = {
        "introduction": ["intro", "overview", "summary", "background", "context"],
        "findings": ["found", "data", "result", "discover", "evidence", "fact", "statistic"],
        "analysis": ["analysis", "analyze", "implication", "insight", "interpretation", "significance"],
        "recommendations": ["recommend", "suggest", "should", "action", "next step", "consider", "advise"]
    }

    def merge_responses(
        self,
        responses: List[PlatformResponse],
        query_id: str,
        session_id: str = ""
    ) -> MergedResponse:
        """Merge multiple platform responses into a single coherent response."""
        if not responses:
            raise ValueError("No responses to merge")

        logger.info(f"Merging {len(responses)} responses")

        unique_content = self._deduplicate(responses)
        structure = self._organize_sections(unique_content)
        attribution = self._add_attribution(responses)
        merged_text = self._build_merged_text(structure, attribution)

        if not self._validate_merged(merged_text):
            logger.warning("Merged response failed validation, using fallback")
            merged_text = self._build_fallback_text(responses)

        return MergedResponse(
            session_id=session_id,
            query_id=query_id,
            original_responses=responses,
            merged_text=merged_text,
            structure=structure,
            attribution=attribution
        )

    def _deduplicate(self, responses: List[PlatformResponse]) -> Dict[str, str]:
        """Remove duplicate sentences across responses."""
        seen_sentences = {}
        normalized_seen = set()

        for response in responses:
            sentences = self._split_sentences(response.response_text)

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence or len(sentence) < 10:
                    continue

                normalized = self._normalize_sentence(sentence)
                if normalized not in normalized_seen:
                    normalized_seen.add(normalized)
                    seen_sentences[sentence] = response.platform.value

        logger.info(f"Deduplicated to {len(seen_sentences)} unique sentences")
        return seen_sentences

    def _normalize_sentence(self, sentence: str) -> str:
        """Normalize a sentence for comparison."""
        normalized = sentence.lower()
        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _organize_sections(self, unique_content: Dict[str, str]) -> dict:
        """Organize content into standard sections."""
        structure = {
            "introduction": [],
            "findings": [],
            "analysis": [],
            "recommendations": []
        }

        for sentence, source in unique_content.items():
            sentence_lower = sentence.lower()
            categorized = False

            for section, keywords in self.SECTION_KEYWORDS.items():
                if any(kw in sentence_lower for kw in keywords):
                    structure[section].append({"text": sentence, "source": source})
                    categorized = True
                    break

            if not categorized:
                structure["findings"].append({"text": sentence, "source": source})

        for section in structure:
            logger.info(f"Section '{section}': {len(structure[section])} items")

        return structure

    def _add_attribution(self, responses: List[PlatformResponse]) -> dict:
        """Create attribution data for each platform."""
        attribution = {}

        for response in responses:
            platform = response.platform.value
            word_count = len(response.response_text.split())

            attribution[platform] = {
                "word_count": word_count,
                "timestamp": response.timestamp.isoformat(),
                "has_error": bool(response.error)
            }

        return attribution

    def _build_merged_text(self, structure: dict, attribution: dict) -> str:
        """Build final merged response text."""
        sections = []

        sections.append("# Research Summary\n")

        if structure["introduction"]:
            sections.append("## Introduction\n")
            intro_texts = [item["text"] for item in structure["introduction"][:3]]
            sections.append(" ".join(intro_texts) + "\n")

        if structure["findings"]:
            sections.append("## Key Findings\n")
            for item in structure["findings"][:7]:
                sections.append(f"- {item['text']}")
            sections.append("")

        if structure["analysis"]:
            sections.append("## Analysis\n")
            analysis_texts = [item["text"] for item in structure["analysis"][:4]]
            sections.append(" ".join(analysis_texts) + "\n")

        if structure["recommendations"]:
            sections.append("## Recommendations\n")
            for item in structure["recommendations"][:5]:
                sections.append(f"- {item['text']}")
            sections.append("")

        sections.append("---\n")
        sections.append("## Sources\n")

        for platform, contrib in attribution.items():
            status = "contributed" if not contrib.get("has_error") else "error"
            sections.append(f"- **{platform.title()}**: {contrib['word_count']} words ({status})")

        return "\n".join(sections)

    def _build_fallback_text(self, responses: List[PlatformResponse]) -> str:
        """Build fallback text when merging fails."""
        sections = ["# Research Results\n"]

        for response in responses:
            if response.error:
                continue

            platform = response.platform.value.title()
            sections.append(f"## Response from {platform}\n")

            text = response.response_text
            if len(text) > 3000:
                text = text[:3000] + "\n\n[Truncated]"

            sections.append(text + "\n")

        return "\n".join(sections)

    def _validate_merged(self, text: str) -> bool:
        """Validate merged response quality."""
        if not text or len(text.strip()) < 100:
            logger.warning("Merged text too short")
            return False

        if len(text) > 50000:
            logger.warning("Merged text too long")
            return False

        if text.count("\n") < 3:
            logger.warning("Merged text lacks structure")
            return False

        return True

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]
