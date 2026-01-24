"""Task analysis and platform routing for ResearchBot."""

from typing import List

from config import MODEL_PRIORITY, SYSTEM_PROMPTS


class TaskAnalyzer:
    """Determines which platforms to query based on task type and mode."""

    @staticmethod
    def get_platform_order(task_type: str, model_choice: str) -> List[str]:
        """Get ordered list of platforms to query.

        Args:
            task_type: One of 'initial', 'targeted', or 'draft'
            model_choice: Either 'auto' or a specific platform name

        Returns:
            List of platform names in query order
        """
        if model_choice.lower() != "auto":
            return [model_choice.lower()]

        return MODEL_PRIORITY.get(task_type.lower(), MODEL_PRIORITY["initial"])

    @staticmethod
    def build_system_prompt(platform: str, task_type: str) -> str:
        """Build task-specific system prompt for a platform.

        Args:
            platform: Platform name (gemini, perplexity, chatgpt)
            task_type: Task type (initial, targeted, draft)

        Returns:
            System prompt string for the platform
        """
        task_prompts = SYSTEM_PROMPTS.get(task_type.lower(), SYSTEM_PROMPTS["initial"])
        prompt = task_prompts.get(platform.lower())

        if not prompt:
            return (
                "You are a research assistant. Provide comprehensive, "
                "well-structured responses to the query."
            )

        return prompt

    @staticmethod
    def get_task_description(task_type: str) -> str:
        """Get human-readable description of a task type."""
        descriptions = {
            "initial": "Initial Research - Broad exploration of the topic",
            "targeted": "Targeted Research - Deep dive into specific aspects",
            "draft": "Draft Generation - Create initial content structure"
        }
        return descriptions.get(task_type.lower(), "Research Task")

    @staticmethod
    def get_platform_specialty(platform: str) -> str:
        """Get description of what each platform specializes in."""
        specialties = {
            "perplexity": "Web search and factual research with sources",
            "gemini": "Analysis, reasoning, and multi-perspective insights",
            "chatgpt": "Strategic advice, writing, and creative solutions"
        }
        return specialties.get(platform.lower(), "General AI assistance")
