"""ResearchBot configuration settings."""

import os
import logging
from pathlib import Path

# Application paths
CONFIG_DIR = Path.home() / ".researchbot"
DB_PATH = CONFIG_DIR / "researchbot.db"
SESSION_DIR = CONFIG_DIR / "sessions"
UPLOAD_DIR = CONFIG_DIR / "uploads"
LOG_PATH = CONFIG_DIR / "researchbot.log"

# Application settings
APP_NAME = "ResearchBot"
APP_VERSION = "1.0.0"
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900

# Platform URLs (ordered: ChatGPT, Gemini, Perplexity, Claude, Google)
PLATFORMS = {
    "chatgpt": "https://chat.openai.com",
    "gemini": "https://gemini.google.com",
    "perplexity": "https://www.perplexity.ai",
    "claude": "https://claude.ai",
    "google": "https://www.google.com"
}

# Browser automation timeouts (seconds)
BROWSER_TIMEOUT = 60
RESPONSE_WAIT_TIME = 180

# File handling limits
MAX_FILES = 5
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
# Text and document formats
SUPPORTED_FORMATS = [
    ".pdf", ".docx", ".txt", ".csv",  # Original formats
    ".md", ".markdown",  # Markdown
    ".json", ".xml", ".yaml", ".yml",  # Data formats
    ".html", ".htm",  # Web formats
    ".rtf",  # Rich text
    ".py", ".js", ".ts", ".jsx", ".tsx",  # Code files
    ".java", ".c", ".cpp", ".h", ".hpp",
    ".css", ".scss", ".sass",
    ".sql", ".sh", ".bash",
    ".go", ".rs", ".rb", ".php",
    ".swift", ".kt", ".scala",
    ".r", ".R", ".ipynb",
    ".log", ".ini", ".conf", ".cfg",  # Config files
    ".env", ".gitignore", ".dockerignore",
]

# Model priority for task-based routing
MODEL_PRIORITY = {
    "initial": ["perplexity", "gemini", "chatgpt"],
    "targeted": ["perplexity", "gemini", "chatgpt"],
    "draft": ["chatgpt"]
}

# Default categories for prompts/responses
DEFAULT_CATEGORIES = [
    "Literature Review",
    "Methodology / Methods",
    "Data Extraction",
    "Analysis / Interpretation",
    "Results Synthesis",
    "Limitations / Risks",
    "Future Work / Ideas",
    "Project Management",
    "Background / Theory",
    "Uncategorized",
]

# Color palette for item labels
COLOR_PALETTE = {
    "Blue": "#2196F3",
    "Green": "#4CAF50",
    "Yellow": "#FFC107",
    "Red": "#F44336",
    "Purple": "#9C27B0",
    "Gray": "#757575",
}

# Dark theme colors
DARK_THEME = {
    "background": "#1E1E1E",
    "surface": "#2D2D2D",
    "surface_light": "#3D3D3D",
    "border": "#404040",
    "text_primary": "#E0E0E0",
    "text_secondary": "#A0A0A0",
    "accent": "#2196F3",
    "accent_hover": "#1976D2",
    "success": "#4CAF50",
    "warning": "#FF9800",
    "error": "#F44336",
}

# System prompts for each platform and task type
SYSTEM_PROMPTS = {
    "initial": {
        "perplexity": (
            "You are a research expert. Provide comprehensive overview of the topic "
            "with key facts, statistics, and credible sources."
        ),
        "gemini": (
            "You are an AI analyst. Provide structured analysis covering multiple "
            "perspectives and emerging trends."
        ),
        "chatgpt": (
            "You are a strategic advisor. Provide actionable insights, best practices, "
            "and strategic implications."
        )
    },
    "targeted": {
        "perplexity": (
            "You are a specialist researcher. Deep-dive into specific aspects "
            "with technical depth."
        ),
        "gemini": (
            "You are a domain expert. Analyze current state-of-the-art "
            "and latest developments."
        ),
        "chatgpt": (
            "You are a business strategist. Provide competitive analysis "
            "and strategic recommendations."
        )
    },
    "draft": {
        "chatgpt": (
            "You are a writer. Draft initial outline and structure for the topic."
        )
    }
}


def initialize_directories():
    """Create required directories if they do not exist."""
    CONFIG_DIR.mkdir(exist_ok=True)
    SESSION_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)


def setup_logging(level: int = logging.INFO):
    """Configure application logging."""
    initialize_directories()

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(APP_NAME)


# Initialize directories on import
initialize_directories()
