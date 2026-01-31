# ResearchBot

A desktop research tool that lets you query multiple AI platforms, grab and organize responses, and export your findings from a single interface.

## Overview

ResearchBot embeds browser tabs for ChatGPT, Gemini, Perplexity, Claude, and Google side by side with a research workspace. You write prompts, send them to any platform, grab the responses back, categorize and organize them, then export everything when you are done.

## Features

### Multi-Platform Browsers
- Embedded browser tabs for ChatGPT, Gemini, Perplexity, Claude, and Google
- Persistent login sessions across restarts (cookies and storage preserved)
- Send prompts directly into any platform's input field
- Grab responses back into the workspace with one click
- Duplicate detection prevents grabbing the same response twice

### Research Workspace
- **Prompts** - Save, reuse, and combine reusable prompt templates
- **Responses** - Store grabbed AI responses with platform attribution
- **Summaries** - Generate cross-platform summaries from multiple responses

### Content Organization
- Color-coded pill UI in a responsive two-column grid
- Category system with defaults (Literature, Methodology, Data, Analysis, Results, etc.) and custom categories
- Six predefined colors plus custom hex color support
- Drag and drop reordering with smooth animations and persistent ordering
- Category and color filters with live item counts
- Multi-select with bulk delete, export, and move operations
- Move items between Prompts, Responses, and Summaries tabs

### File Upload
- Upload up to 5 files (50MB each) supporting 50+ formats (PDF, DOCX, TXT, MD, JSON, code files, and more)
- Extracted text is injected into prompts automatically
- File chips in the prompt box with individual remove buttons

### Export
- Export to PDF, Markdown, or plain text
- Export all items or only selected items
- Formatted PDF output with titles, metadata, and sections

### Markdown Notebook
- Built-in WYSIWYG editor with bold, italic, underline, strikethrough, headings, lists, and alignment
- Open and save Markdown files with automatic format conversion
- Real-time word and character count

### Downloads Manager
- Built-in download manager with progress bars and state tracking
- Configurable download folder

### Logging
- Color-coded log tab with timestamps (INFO, SUCCESS, WARNING, ERROR)
- Logs persisted to disk at `~/.researchbot/researchbot.log`

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| GUI Framework | PyQt6 |
| Embedded Browsers | PyQt6-WebEngine (QWebEngineView) |
| Database | SQLite |
| PDF Export | ReportLab |
| File Parsing | PyPDF2, python-docx |

## Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/ResearchBot.git
cd ResearchBot

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

On first launch the app creates its data directory at `~/.researchbot/` containing the SQLite database, logs, uploaded files, and session data.

### Quick Workflow

1. Open a browser tab (ChatGPT, Gemini, Perplexity, or Claude) and log in. Sessions persist across restarts.
2. Type or select saved prompts in the prompt box. Optionally attach files for context injection.
3. Click **Send** to fill the prompt into the active platform's input.
4. Click **Grab** to pull the response back into the Responses panel.
5. Repeat across platforms, then select multiple responses and click **Summarize** to request a cross-platform synthesis.
6. Organize with categories, colors, drag and drop, and filters.
7. **Export** your research to PDF, Markdown, or text.

## Project Structure

```
ResearchBot/
  main.py              # Application entry point
  config.py            # Settings, theme, platform URLs, defaults
  requirements.txt     # Python dependencies
  agents/              # Task analyzer, file injector, response merger
  ui/                  # PyQt6 widgets (main window, panels, editors, browsers)
  utils/               # Storage, models, browser controller
  instructions/        # Internal documentation
  tests/               # Test suite
```

## Configuration

All settings live in `config.py`:
- Platform URLs and timeouts
- File upload limits (count and size)
- Default categories and colors
- Dark theme color palette
- Model priority order for multi-platform queries

## Data Storage

Everything is stored locally:

| Path | Contents |
|------|----------|
| `~/.researchbot/researchbot.db` | SQLite database (prompts, responses, summaries, categories, sessions) |
| `~/.researchbot/researchbot.log` | Application logs |
| `~/.researchbot/uploads/` | Uploaded files for context injection |
| `~/.researchbot/sessions/` | Session data |

## License

This project is provided as-is for personal research use.
