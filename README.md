# ResearchBot

A desktop prompt management and research tool for working with multiple AI platforms from a single interface.

## Overview

ResearchBot embeds ChatGPT, Gemini, Perplexity, Claude, and Google Search in browser tabs alongside a workspace where you build, organize, and reuse prompts. Send the same prompt to multiple platforms without retyping, grab responses back into your workspace, and keep everything organized with categories and colors.

## Features

### Prompt Management
- Save prompts as reusable pills with categories and color labels
- Select multiple pills to combine them into a single prompt before sending
- Placeholder variables using `[/NAME]` syntax with slash-completion popup for building templates like `Analyze [/TOPIC] using [/METHOD]`
- Persistent selections across platform tabs
- Drag and drop reordering to control prompt composition order
- Category and color filters for organizing large prompt libraries
- Built-in research prompt templates (Topic Search, SOTA Check, Paper Analysis, Literature Survey, Research Design, and more)

### File to Prompt Conversion
- Upload PDF, DOCX, Excel, CSV, and 50+ other file formats
- Files are automatically extracted and converted into prompt pills
- Spreadsheet and database files (XLSX, CSV, TSV, SQLite) are formatted as markdown tables
- "No Reference" toggle strips bibliography and references sections from academic papers
- Convert button for manual conversion control

### Multi-Platform Send and Grab
- Send prompts directly into ChatGPT, Gemini, Perplexity, or Claude with formatting preserved
- Grab responses back into the workspace with platform attribution
- Duplicate detection prevents grabbing the same response twice
- External links from AI platforms open in the Google tab
- Persistent browser sessions across application restarts

### Notebook
- Rich text editor with Word-like formatting toolbar (bold, italic, underline, strikethrough)
- Heading levels, bullet lists, and numbered lists
- Code blocks with syntax formatting
- New, Open, and Save operations for markdown files
- Create Prompt button converts notebook content directly into a prompt pill

### Organization and Export
- Four tabs: Prompts, Responses, Summaries, and Notebook
- Move items between Prompts, Responses, and Summaries tabs
- Categories: Exploration, Literature, Methodology, Data and Metrics, Architecture, Implementation, Analysis, Draft, Reference, Uncategorized
- Six color labels: Gray, Blue, Purple, Green, Orange, Red
- Custom categories support
- Export selected items to PDF, Markdown, or plain text
- Bulk selection and deletion

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| GUI | PyQt6 + PyQt6-WebEngine |
| Database | SQLite |
| Data Validation | Pydantic |
| PDF Export | ReportLab |
| File Parsing | PyPDF2, python-docx, openpyxl |
| Clipboard | pyperclip |

## Supported File Formats

| Category | Extensions |
|----------|------------|
| Documents | `.pdf`, `.docx`, `.txt`, `.rtf`, `.md`, `.markdown` |
| Spreadsheets | `.xlsx`, `.xls`, `.csv`, `.tsv` |
| Databases | `.sqlite`, `.sqlite3`, `.db` |
| Data | `.json`, `.xml`, `.yaml`, `.yml` |
| Web | `.html`, `.htm` |
| Code | `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.java`, `.c`, `.cpp`, `.h`, `.hpp`, `.css`, `.scss`, `.sass`, `.sql`, `.sh`, `.bash`, `.go`, `.rs`, `.rb`, `.php`, `.swift`, `.kt`, `.scala`, `.r`, `.ipynb` |
| Config | `.log`, `.ini`, `.conf`, `.cfg`, `.env`, `.gitignore`, `.dockerignore` |

Spreadsheet and database files are automatically converted to markdown tables for AI platform readability.

## Installation

```bash
git clone https://github.com/znwayoo/ResearchBot.git
cd ResearchBot
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### macOS Additional Dependency

On macOS, the application uses `pyobjc-framework-Cocoa` for native menu bar integration, which is automatically installed via requirements.txt.

## Usage

```bash
python main.py
```

On first launch the app creates its data directory at `~/.researchbot/` containing the SQLite database, uploaded files, browser session data, and logs.

### Workflow

1. Log in to your AI platforms in the browser tabs. Sessions persist across restarts.
2. Build prompts in the Prompts tab or upload files to auto-create prompt pills.
3. Select the pills you want, optionally fill in placeholder values, and click **Send**.
4. Switch to another platform tab and send the same selection again.
5. Click **Grab** to pull responses back into your workspace.
6. Select multiple responses and send them to any platform for cross-platform summarization.
7. Organize with categories and filters, then **Export** to PDF or Markdown.

## Project Structure

```
ResearchBot/
├── main.py                    # Application entry point
├── config.py                  # Settings, themes, platform URLs, default prompts
├── requirements.txt           # Python dependencies
├── LICENSE                    # MIT No-Derivatives License
├── agents/
│   ├── file_context_injector.py   # File content extraction (PDF, DOCX, Excel, etc.)
│   ├── response_merger.py         # Response merging and summarization
│   └── task_analyzer.py           # Task type analysis and platform routing
├── ui/
│   ├── main_window.py         # Main application window and research controller
│   ├── research_workspace.py  # Workspace with tabs for prompts/responses/summaries
│   ├── items_panel.py         # Scrollable panel with filtering and drag-drop
│   ├── item_button.py         # Individual prompt/response pill widget
│   ├── item_editor.py         # Dialog for editing items
│   ├── prompt_box.py          # Prompt composition box with file upload
│   ├── sidebar_tabs.py        # Browser tabs, notebook editor, platform browsers
│   ├── input_panel.py         # Query input controls
│   └── chat_widget.py         # Chat interface widget
├── utils/
│   ├── local_storage.py       # SQLite database operations
│   ├── models.py              # Pydantic data models
│   ├── export_service.py      # PDF and Markdown export
│   ├── clipboard_parser.py    # Clipboard text parsing
│   └── placeholder_utils.py   # Placeholder variable handling
├── workers/
│   └── file_extraction_worker.py  # Background file processing
├── assets/
│   ├── ResearchBot.icns       # macOS app icon
│   ├── ResearchBot.ico        # Windows app icon
│   └── ResearchBot.png        # Application icon
├── .github/
│   └── workflows/
│       └── build-release.yml  # GitHub Actions build workflow
├── ResearchBot.spec           # PyInstaller spec for macOS
└── ResearchBot-windows.spec   # PyInstaller spec for Windows
```

## Data Storage

All data is stored locally in `~/.researchbot/`:

| Path | Contents |
|------|----------|
| `researchbot.db` | SQLite database with prompts, responses, summaries, categories, and sessions |
| `uploads/` | Uploaded files for content extraction |
| `sessions/` | Browser session data |
| `browser_data/` | Persistent browser cookies and storage |
| `browser_cache/` | Browser cache |
| `researchbot.log` | Application logs |

## Building

### macOS

```bash
./build_mac.sh
```

### Windows

```powershell
.\build_windows.ps1
```

Or using the batch file:

```cmd
build_windows.bat
```

## License

MIT No-Derivatives License. Free to use, copy, and redistribute. Modification and distribution of modified versions requires prior written permission. See [LICENSE](LICENSE) for details.
