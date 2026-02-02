# ResearchBot

A desktop prompt management and research tool for working with multiple AI platforms from a single interface.

## What It Does

ResearchBot sits between you and the AI platforms you already use. It embeds ChatGPT, Gemini, Perplexity, Claude, and Google in browser tabs alongside a workspace where you build, organize, and reuse prompts. You send the same prompt to multiple platforms without retyping, grab the responses back, and keep everything organized.

## Features

### Prompt Management
- Save prompts as reusable pills with categories and colors
- Select multiple pills to combine them into a single prompt before sending
- Placeholder variables using `[/NAME]` syntax with a slash-completion popup, so you can build templates like `Analyze [/TOPIC] using [/METHOD]` and fill in the values at send time
- Persistent selections let you send the same set of prompts to one platform, switch tabs, and send again to another without re-selecting
- Drag and drop reordering to control prompt composition order
- Category and color filters to organize large prompt libraries

### File to Prompt Conversion
- Upload PDF, DOCX, TXT, and 50+ other formats
- Files are automatically extracted and converted into prompt pills
- "No Reference" toggle strips bibliography and references sections from academic papers before creating the pill

### Multi-Platform Send and Grab
- Send prompts directly into ChatGPT, Gemini, Perplexity, or Claude with formatting preserved
- Grab responses back into the workspace with platform attribution
- Duplicate detection prevents grabbing the same response twice
- Select multiple responses and send them to any platform for cross-platform summarization

### Notebook
- Markdown editor with formatting toolbar
- Create Prompt button converts notebook content directly into a prompt pill with markdown formatting preserved

### Organization and Export
- Three tabs: Prompts, Responses, and Summaries with move operations between them
- Categories (Literature, Methodology, Data, Analysis, Results, and custom) with color coding
- Export selected items to PDF, Markdown, or plain text

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| GUI | PyQt6 + PyQt6-WebEngine |
| Database | SQLite |
| PDF Export | ReportLab |
| File Parsing | PyPDF2, python-docx |

## Installation

```bash
git clone https://github.com/<your-username>/ResearchBot.git
cd ResearchBot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

On first launch the app creates its data directory at `~/.researchbot/` containing the SQLite database, uploaded files, and session data.

### Workflow

1. Log in to your AI platforms in the browser tabs. Sessions persist across restarts.
2. Build prompts in the Prompts tab or upload files to auto-create prompt pills.
3. Select the pills you want, optionally fill in placeholder values, and click **Send**.
4. Switch to another platform tab and send the same selection again.
5. Click **Grab** to pull responses back. Select multiple responses and click **Summarize** for cross-platform synthesis.
6. Organize with categories and filters, then **Export** to PDF or Markdown.

## Project Structure

```
ResearchBot/
  main.py              # Entry point
  config.py            # Settings, theme, platform URLs
  agents/              # Task analyzer, file injector, response merger
  ui/                  # PyQt6 widgets
  utils/               # Storage, models, clipboard
  workers/             # Background file extraction threads
```

## Data Storage

Everything is stored locally in `~/.researchbot/`:

| Path | Contents |
|------|----------|
| `researchbot.db` | Prompts, responses, summaries, categories, sessions |
| `uploads/` | Uploaded files for extraction |
| `researchbot.log` | Application logs |

## License

Free to use and redistribute. Modification and distribution of modified versions is not permitted without permission. See [LICENSE](LICENSE) for details.
