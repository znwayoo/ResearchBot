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
