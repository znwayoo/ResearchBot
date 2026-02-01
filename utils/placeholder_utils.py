"""Utilities for extracting and substituting placeholders in prompt content."""

import re
from typing import Dict, List


# Matches [/NAME] in prompt content (the placeholder definition)
PLACEHOLDER_PATTERN = re.compile(r'\[/([A-Z_]+)\]')

# Matches [/NAME]="value" in user input
PLACEHOLDER_VALUE_PATTERN = re.compile(r'\[/([A-Z_]+)\]="([^"]*)"')


def extract_placeholders(content: str) -> List[str]:
    """Extract unique placeholder names from prompt content."""
    return list(dict.fromkeys(PLACEHOLDER_PATTERN.findall(content)))


def substitute_placeholders(content: str, values: Dict[str, str]) -> str:
    """Replace [/NAME] placeholders with user-provided values."""
    result = content
    for name, value in values.items():
        result = result.replace(f"[/{name}]", value)
    return result


def parse_placeholder_values(text: str) -> Dict[str, str]:
    """Parse [/NAME]="value" entries from user input text."""
    return dict(PLACEHOLDER_VALUE_PATTERN.findall(text))


def strip_placeholder_entries(text: str) -> str:
    """Remove [/NAME]="value" entries from user input text."""
    result = PLACEHOLDER_VALUE_PATTERN.sub('', text)
    # Clean up extra blank lines left behind
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()
