"""ResearchBot configuration settings."""

import json
import logging
import os
import sys
from pathlib import Path

# Base path for app (works when frozen by PyInstaller or running from source)
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    APP_BASE_PATH = Path(sys._MEIPASS)
else:
    APP_BASE_PATH = Path(__file__).resolve().parent
ASSETS_DIR = APP_BASE_PATH / "assets"

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
    "chatgpt": "https://chatgpt.com",
    "gemini": "https://gemini.google.com",
    "perplexity": "https://www.perplexity.ai",
    "claude": "https://claude.ai",
    "google": "https://www.google.com"
}

# Browser automation timeouts (seconds)
BROWSER_TIMEOUT = 60
RESPONSE_WAIT_TIME = 180

# File handling limits
MAX_FILES = 3
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
# Text and document formats
SUPPORTED_FORMATS = [
    ".pdf", ".docx", ".txt", ".csv",  # Original formats
    ".xlsx", ".xls", ".tsv",  # Spreadsheet and tabular data
    ".sqlite", ".sqlite3", ".db",  # Database files
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
    "Exploration",
    "Literature",
    "Methodology",
    "Data & Metrics",
    "Architecture",
    "Implementation",
    "Analysis",
    "Draft",
    "Reference",
    "Uncategorized",
]

# Color palette for item labels (spread across hue wheel for max distinction)
COLOR_PALETTE = {
    "Gray": "#8B8FA3",
    "Blue": "#528BFF",
    "Purple": "#9B6DFF",
    "Green": "#2DA44E",
    "Orange": "#F2994A",
    "Red": "#EB5757",
}

# Default prompt pills for first-time users
DEFAULT_PROMPTS = [
    # --- Exploration ---
    {
        "title": "Topic Search",
        "category": "Exploration",
        "color": "Blue",
        "content": (
            "You are a research intelligence analyst. Your task is to produce a "
            "comprehensive, well-sourced briefing on [/TOPIC] that enables a researcher "
            "to go from zero knowledge to informed decision-making.\n\n"
            "Structure your response as follows:\n\n"
            "## 1. Executive Summary\n"
            "- One-paragraph definition of [/TOPIC] and why it matters right now\n"
            "- The single most important thing a newcomer should understand\n\n"
            "## 2. Landscape Map\n"
            "- Break [/TOPIC] into 3-5 major sub-domains or branches\n"
            "- For each: one-sentence description, key differentiator, and maturity level "
            "(emerging / growing / mature / declining)\n"
            "- Show how these sub-domains relate to each other (dependencies, tensions, overlaps)\n\n"
            "## 3. Key Players and Seminal Work\n"
            "- Top 5-8 researchers or groups driving progress, with their affiliations\n"
            "- For each: their signature contribution and most-cited paper (title + year)\n"
            "- Notable industry players and their role in the ecosystem\n\n"
            "## 4. Current State of Knowledge\n"
            "- What is well-established and broadly accepted\n"
            "- What is promising but still contested\n"
            "- What remains unknown or poorly understood\n\n"
            "## 5. Open Questions and Active Debates\n"
            "- List 3-5 unresolved questions ranked by potential research impact\n"
            "- For each: why it matters, who is working on it, current leading hypotheses\n\n"
            "## 6. Recommended Deep-Dive Paths\n"
            "- Suggest 3-5 specific follow-up research directions\n"
            "- For each: a concrete starting query, 2-3 papers to read first, "
            "and what you would learn from pursuing it\n\n"
            "Formatting rules: Use precise language. Cite specific names, dates, and numbers "
            "rather than vague qualifiers. If information is uncertain, say so explicitly. "
            "Prioritize recency - weight findings from the last 3 years more heavily."
        ),
    },
    {
        "title": "SOTA Check",
        "category": "Exploration",
        "color": "Purple",
        "content": (
            "You are a competitive intelligence analyst for research. Provide a precise, "
            "up-to-date snapshot of the state-of-the-art for [/TASK_PROBLEM].\n\n"
            "Be concrete. Cite exact numbers, method names, and dates. "
            "Do not use vague terms like 'recent advances' without specifics.\n\n"
            "## 1. Leaderboard Snapshot\n"
            "Create a ranked table of top methods with columns:\n"
            "- Rank, Method Name, Key Paper (authors + year), Score on primary metric, "
            "Score on secondary metric, Open-source (yes/no)\n"
            "- Include at least the top 5 methods\n"
            "- Note which benchmark and metric you are using\n\n"
            "## 2. Benchmark Landscape\n"
            "- Which benchmarks are considered standard and why?\n"
            "- Are any benchmarks becoming saturated (near-perfect scores)?\n"
            "- Are there newer, harder benchmarks gaining traction?\n\n"
            "## 3. Recent Breakthroughs (last 12-24 months)\n"
            "- What changed and when (specific paper, month/year)\n"
            "- What technique or insight drove the improvement\n"
            "- How large was the gain over the previous SOTA (absolute numbers)\n\n"
            "## 4. Technique Breakdown\n"
            "- What key techniques do top methods have in common?\n"
            "- What differentiates the #1 method from the #2-5 methods?\n"
            "- Are improvements coming from architecture, data, training, or all three?\n\n"
            "## 5. Remaining Gaps\n"
            "- What aspects of [/TASK_PROBLEM] are current methods still bad at?\n"
            "- What is the theoretical upper bound or human-level performance?\n"
            "- What would a breakthrough in this area look like?\n\n"
            "## 6. Trajectory\n"
            "- Is progress accelerating, plateauing, or decelerating?\n"
            "- What emerging approaches could disrupt the current leaderboard?\n"
            "- What should a researcher entering this area focus on?"
        ),
    },
    {
        "title": "Paper Extract: Step 1 - Core Intel",
        "category": "Exploration",
        "color": "Green",
        "content": (
            "You are a research extraction specialist. Perform a first-pass extraction of "
            "the essential facts, claims, methodology, and results from [/PAPER_SOURCE]. "
            "Pure extraction only - no judgment or critique at this stage.\n\n"
            "## 1. Paper Identity\n"
            "- Full title, authors, affiliations, venue, year\n"
            "- Paper type (empirical, theoretical, survey, system, position)\n"
            "- DOI or URL if available\n\n"
            "## 2. Problem Statement\n"
            "- What specific problem does the paper address?\n"
            "- What gap or limitation in prior work motivates this?\n"
            "- Quote the authors' own framing of the problem\n\n"
            "## 3. Approach\n"
            "- Describe the methodology step by step\n"
            "- Key assumptions the method relies on\n"
            "- What is novel vs. borrowed from prior work\n\n"
            "## 4. Key Results\n"
            "- List all quantitative results with exact numbers\n"
            "- Primary metric and performance on it\n"
            "- Secondary metrics and their values\n"
            "- Statistical measures reported (p-values, confidence intervals, error bars)\n\n"
            "## 5. Datasets and Baselines\n"
            "- Every dataset used: name, size, source\n"
            "- Every baseline compared against: name, source, reported performance\n"
            "- Evaluation protocol (splits, cross-validation, held-out test)\n\n"
            "## 6. Limitations (Author-Stated)\n"
            "- What limitations do the authors themselves acknowledge?\n"
            "- What future work do they suggest?\n\n"
            "## 7. Key Figures and Tables\n"
            "- For each important figure/table: number, what it shows, key takeaway\n\n"
            "Output this as a clean, structured reference document that can feed "
            "into deeper analysis in subsequent steps."
        ),
    },
    {
        "title": "Paper Extract: Step 2 - Cross-Ref",
        "category": "Exploration",
        "color": "Purple",
        "content": (
            "You are a research cross-referencing analyst. Take the extracted findings "
            "from [/PAPER_SOURCE] and cross-reference them against the broader field of "
            "[/FIELD].\n\n"
            "Your goal is to validate claims, contextualize results, and map where this "
            "work sits in the research landscape.\n\n"
            "## 1. Claim Validation\n"
            "- For each major claim in the paper, check:\n"
            "  - Is this consistent with other published results?\n"
            "  - Are there papers reporting contradictory findings? If so, which?\n"
            "  - How do the reported numbers compare to established benchmarks?\n\n"
            "## 2. Novelty Assessment\n"
            "- What is genuinely novel in this work?\n"
            "- What is incremental improvement over existing methods?\n"
            "- What has been done before under a different name or framing?\n"
            "- Cite the closest prior work for each claimed contribution\n\n"
            "## 3. Research Timeline Positioning\n"
            "- Where does this paper sit in the evolution of the field?\n"
            "- What were the key precursor papers that enabled this work?\n"
            "- What subsequent work has built on or cited this paper?\n"
            "- Is this on the main trajectory of the field or a side branch?\n\n"
            "## 4. Methodological Context\n"
            "- How does the methodology compare to current best practices?\n"
            "- Are the baselines they chose still relevant, or are there stronger ones?\n"
            "- Are the datasets they used considered adequate by current standards?\n\n"
            "## 5. Conflicting Evidence\n"
            "- List specific papers or results that challenge this work's conclusions\n"
            "- For each conflict: what differs (data, method, assumptions) and why it matters\n"
            "- Is there a resolution, or is this an open disagreement?\n\n"
            "## 6. Field Consensus Map\n"
            "- What aspects of this paper align with field consensus?\n"
            "- What aspects go against prevailing views?\n"
            "- What aspects address questions the field has not settled yet?"
        ),
    },
    {
        "title": "Paper Extract: Step 3 - Value Map",
        "category": "Exploration",
        "color": "Orange",
        "content": (
            "You are a research strategist. Synthesize the extraction and cross-referencing "
            "of [/PAPER_SOURCE] into actionable research value in the context of "
            "[/RESEARCH_GOAL].\n\n"
            "Transform analysis into strategy. What should the researcher do with this paper?\n\n"
            "## 1. Key Takeaways for Your Research\n"
            "- Top 3-5 ideas from this paper directly relevant to [/RESEARCH_GOAL]\n"
            "- For each: what it is, why it matters for your work, how to apply it\n\n"
            "## 2. Ideas to Adopt\n"
            "- Techniques, methods, or frameworks worth incorporating\n"
            "- For each: what to adopt, how to adapt it to your context, expected benefit\n"
            "- Implementation complexity (low / medium / high) for each\n\n"
            "## 3. Ideas to Challenge\n"
            "- Claims or assumptions in this paper that warrant skepticism\n"
            "- For each: what to challenge, why, and what alternative to test\n"
            "- Could challenging these lead to a publishable contribution?\n\n"
            "## 4. Experiments to Run Next\n"
            "- Concrete experiments inspired by this paper\n"
            "- For each: hypothesis, method, expected outcome, required resources\n"
            "- Priority ranking based on potential impact and feasibility\n\n"
            "## 5. Building on This Work\n"
            "- Gaps this paper leaves open that you could fill\n"
            "- Extensions that would strengthen or generalize the findings\n"
            "- Combinations with other work that could yield novel contributions\n\n"
            "## 6. Citation and Positioning Strategy\n"
            "- How to cite this paper in your own work (what context)\n"
            "- How your research would relate to, extend, or differ from this paper\n"
            "- Key phrases or framings from this paper useful for your writing\n\n"
            "## 7. Action Items\n"
            "- Prioritized list of concrete next steps based on this paper\n"
            "- Quick wins (can do immediately)\n"
            "- Medium-term actions (require some setup)\n"
            "- Long-term opportunities (require significant effort)"
        ),
    },
    # --- Literature ---
    {
        "title": "Paper Analysis",
        "category": "Literature",
        "color": "Orange",
        "content": (
            "You are an expert peer reviewer. Perform a thorough, structured analysis of "
            "the following paper: [/PAPER_TITLE].\n\n"
            "Approach this as if you are writing a detailed review for a top-tier venue. "
            "Be specific, cite sections/figures/tables by number, and distinguish between "
            "what the authors claim and what the evidence actually supports.\n\n"
            "## 1. Paper Identity\n"
            "- Full title, authors, venue, year\n"
            "- Paper type (empirical study, theoretical, survey, system, position paper)\n"
            "- One-sentence summary of the core contribution\n\n"
            "## 2. Research Question and Motivation\n"
            "- What specific problem does the paper address?\n"
            "- What gap in prior work motivates this research?\n"
            "- Is the motivation convincing? Are there stronger motivations the authors missed?\n\n"
            "## 3. Methodology Deep-Dive\n"
            "- Describe the approach step by step\n"
            "- What assumptions does the method rely on? Are they stated explicitly?\n"
            "- What are the independent/dependent variables and controls?\n"
            "- Could you reproduce this from the description alone? What details are missing?\n\n"
            "## 4. Results and Evidence Quality\n"
            "- Summarize key quantitative results with specific numbers\n"
            "- Are baselines appropriate and fairly compared?\n"
            "- Statistical significance: are error bars, p-values, or confidence intervals reported?\n"
            "- Do the results actually support the claims made in the abstract/conclusion?\n\n"
            "## 5. Strengths (be specific)\n"
            "- List 3-5 concrete strengths with evidence from the paper\n\n"
            "## 6. Weaknesses and Blind Spots\n"
            "- List 3-5 concrete weaknesses, each with a suggested fix\n"
            "- Identify any threats to validity (internal, external, construct)\n"
            "- What experiments or analyses are missing?\n\n"
            "## 7. Positioning in the Field\n"
            "- How does this compare to the closest 2-3 related works?\n"
            "- What does this paper enable that was not possible before?\n"
            "- Who should read this paper and why?\n\n"
            "## 8. Follow-Up Questions\n"
            "- List 3-5 research questions this paper opens up\n"
            "- What would a strong follow-up study look like?"
        ),
    },
    {
        "title": "Literature Survey",
        "category": "Literature",
        "color": "Red",
        "content": (
            "You are a systematic review specialist. Produce a structured literature "
            "survey on [/TOPIC] that maps the research landscape and identifies patterns "
            "across the body of work.\n\n"
            "Do not just list papers. Synthesize, compare, and identify trends.\n\n"
            "## 1. Scope and Search Strategy\n"
            "- Define the boundaries of this survey (what is included/excluded and why)\n"
            "- Key search terms and venues where this work appears\n\n"
            "## 2. Foundational Works (pre-2020 or field-specific cutoff)\n"
            "- 3-5 papers that established the field's foundations\n"
            "- For each: authors, year, core idea, why it is foundational, citation count if known\n\n"
            "## 3. Thematic Grouping\n"
            "- Organize the literature into 3-5 thematic clusters\n"
            "- For each cluster:\n"
            "  - Name and one-sentence description of the approach\n"
            "  - 3-5 representative papers with year and key finding\n"
            "  - Shared assumptions and common methodology\n"
            "  - Known limitations of this line of work\n\n"
            "## 4. Evolution Timeline\n"
            "- Trace how ideas evolved: what led to what, and why the field shifted\n"
            "- Identify 2-3 inflection points where the field changed direction\n\n"
            "## 5. Consensus vs. Disagreement\n"
            "- What do most researchers agree on?\n"
            "- Where are there active disagreements? Who holds which position and why?\n\n"
            "## 6. Gaps and Opportunities\n"
            "- What has been under-explored or systematically ignored?\n"
            "- What combinations of existing ideas have not been tried?\n"
            "- Rank gaps by potential impact and feasibility\n\n"
            "## 7. Recommended Reading Path\n"
            "- If someone had time for only 5 papers, which 5 and in what order?\n"
            "- Brief justification for each selection\n\n"
            "Formatting: Use a consistent citation style (Author, Year). "
            "Include a summary table of all mentioned papers at the end with columns: "
            "Title, Authors, Year, Cluster, Key Contribution."
        ),
    },
    # --- Methodology ---
    {
        "title": "Research Design",
        "category": "Methodology",
        "color": "Purple",
        "content": (
            "You are an expert research methodologist. Design a rigorous methodology "
            "for investigating [/RESEARCH_QUESTION] in the domain of [/DOMAIN].\n\n"
            "The design should be detailed enough for a competent researcher to execute "
            "without ambiguity.\n\n"
            "## 1. Research Framework\n"
            "- Research paradigm (quantitative, qualitative, mixed methods) and justification\n"
            "- Theoretical framework or model underpinning the study\n"
            "- Key constructs and how they will be operationalized\n\n"
            "## 2. Hypotheses / Research Questions\n"
            "- Primary hypothesis or question (formal statement)\n"
            "- Secondary hypotheses or sub-questions\n"
            "- Null hypotheses where applicable\n\n"
            "## 3. Study Design\n"
            "- Design type (experimental, quasi-experimental, observational, etc.)\n"
            "- Independent, dependent, and control variables\n"
            "- Confounding variables and how they will be handled\n"
            "- Comparison groups or conditions\n\n"
            "## 4. Sampling Strategy\n"
            "- Target population and sampling frame\n"
            "- Sampling method and justification\n"
            "- Sample size calculation with assumptions\n"
            "- Inclusion and exclusion criteria\n\n"
            "## 5. Data Collection\n"
            "- Instruments, tools, or procedures for data collection\n"
            "- Data types and formats\n"
            "- Timeline and sequencing of data collection\n"
            "- Quality assurance measures during collection\n\n"
            "## 6. Analysis Plan\n"
            "- Statistical tests or analytical methods for each hypothesis\n"
            "- Assumptions to check before analysis\n"
            "- How to handle missing data, outliers, and violations\n"
            "- Software and tools to use\n\n"
            "## 7. Validity and Limitations\n"
            "- Threats to internal, external, and construct validity\n"
            "- Mitigation strategies for each threat\n"
            "- Known limitations and their impact on conclusions\n\n"
            "## 8. Ethical Considerations\n"
            "- IRB or ethics review requirements\n"
            "- Informed consent, privacy, and data handling protocols"
        ),
    },
    {
        "title": "Compare Approaches",
        "category": "Methodology",
        "color": "Orange",
        "content": (
            "You are a methods expert tasked with producing a rigorous, decision-ready "
            "comparison. Compare the following approaches to [/PROBLEM]:\n"
            "- Approach A: [/APPROACH_A]\n"
            "- Approach B: [/APPROACH_B]\n"
            "(Add more approaches as needed)\n\n"
            "Your analysis should help a practitioner choose the right approach for their "
            "specific situation, not just list differences.\n\n"
            "## 1. Approach Profiles\n"
            "For each approach:\n"
            "- Core mechanism in 2-3 sentences (how it actually works, not marketing)\n"
            "- Theoretical foundation and key assumptions\n"
            "- Original paper/source and when it was introduced\n\n"
            "## 2. Head-to-Head Comparison Matrix\n"
            "Create a comparison table with these dimensions:\n"
            "- Accuracy / quality of results (cite specific benchmarks)\n"
            "- Computational cost (time complexity, memory, hardware requirements)\n"
            "- Scalability (how performance changes with data size / problem complexity)\n"
            "- Ease of implementation (library support, documentation quality)\n"
            "- Data requirements (minimum samples, label needs, data quality sensitivity)\n"
            "- Interpretability (can you explain why it gives a particular output?)\n"
            "- Robustness (behavior on edge cases, noisy data, distribution shift)\n\n"
            "## 3. When to Use Which\n"
            "- Define 3-5 concrete scenarios with specific constraints\n"
            "- For each scenario: which approach wins and why, with quantitative evidence\n"
            "- Are there cases where combining approaches outperforms either alone?\n\n"
            "## 4. Hidden Trade-offs\n"
            "- What costs or risks are not immediately obvious?\n"
            "- What do practitioners often get wrong when choosing between these?\n"
            "- Are there failure modes unique to each approach?\n\n"
            "## 5. Verdict\n"
            "- Clear recommendation with stated assumptions\n"
            "- Under what conditions would your recommendation change?\n"
            "- If you had to pick one as a default starting point, which and why?"
        ),
    },
    {
        "title": "Experiment Design",
        "category": "Methodology",
        "color": "Purple",
        "content": (
            "You are an experimental design specialist. Design a rigorous experiment "
            "to test the hypothesis: [/HYPOTHESIS].\n\n"
            "The experiment should be reproducible, well-controlled, and produce "
            "conclusive results.\n\n"
            "## 1. Hypothesis Formalization\n"
            "- Restate [/HYPOTHESIS] as a testable, falsifiable statement\n"
            "- Null hypothesis (H0) and alternative hypothesis (H1)\n"
            "- What specific outcome would confirm vs. refute the hypothesis?\n\n"
            "## 2. Experimental Setup\n"
            "- Independent variable(s) and their levels/conditions\n"
            "- Dependent variable(s) and how they will be measured\n"
            "- Control variables and how they will be held constant\n"
            "- Control group or baseline condition\n\n"
            "## 3. Protocol\n"
            "- Step-by-step procedure for running the experiment\n"
            "- Randomization and blinding procedures if applicable\n"
            "- Number of trials, repetitions, or epochs\n"
            "- Data recording format and frequency\n\n"
            "## 4. Resources Required\n"
            "- Hardware, software, and compute requirements\n"
            "- Datasets or data generation procedures\n"
            "- Human participants (if applicable): recruitment, sample size, compensation\n\n"
            "## 5. Statistical Analysis Plan\n"
            "- Primary statistical test and justification\n"
            "- Power analysis for sample size determination\n"
            "- Significance threshold and multiple comparison corrections\n"
            "- Effect size of interest and how to interpret results\n\n"
            "## 6. Threats to Validity\n"
            "- Potential confounds and how to mitigate each\n"
            "- Selection bias, measurement bias, survivorship bias risks\n"
            "- What could make the results misleading even if statistically significant?\n\n"
            "## 7. Expected Outcomes\n"
            "- What results would you expect if H1 is true?\n"
            "- What results would you expect if H0 is true?\n"
            "- What ambiguous outcomes are possible and how to resolve them?\n\n"
            "## 8. Timeline and Milestones\n"
            "- Pilot study plan\n"
            "- Full experiment phases\n"
            "- Go/no-go decision points"
        ),
    },
    # --- Data & Metrics ---
    {
        "title": "Data Audit",
        "category": "Data & Metrics",
        "color": "Green",
        "content": (
            "You are a data quality specialist. Perform a comprehensive audit of the "
            "dataset or data pipeline for [/PROJECT].\n\n"
            "Be practical and checklist-driven. Flag issues with severity levels and "
            "provide actionable fixes.\n\n"
            "## 1. Data Overview\n"
            "- Dataset dimensions (rows, columns, size on disk)\n"
            "- Data types and schema summary\n"
            "- Source(s) and collection methodology\n"
            "- Date range and freshness\n\n"
            "## 2. Completeness Audit\n"
            "- Missing value analysis per column (percentage and pattern)\n"
            "- Are missing values random (MCAR), systematic (MAR), or informative (MNAR)?\n"
            "- Recommended handling strategy for each pattern\n\n"
            "## 3. Consistency Checks\n"
            "- Duplicate records (exact and fuzzy)\n"
            "- Format inconsistencies (dates, strings, encodings)\n"
            "- Referential integrity across related tables\n"
            "- Unit consistency (currencies, measurements, time zones)\n\n"
            "## 4. Distribution Analysis\n"
            "- Outlier detection for numeric columns\n"
            "- Class balance for categorical targets\n"
            "- Unexpected values or categories\n"
            "- Temporal patterns (seasonality, trends, drift)\n\n"
            "## 5. Data Leakage Check\n"
            "- Features that could leak target information\n"
            "- Temporal leakage in train/test splits\n"
            "- Proxy variables that encode protected attributes\n\n"
            "## 6. Pipeline Health\n"
            "- Data freshness and update reliability\n"
            "- Schema evolution and breaking change risks\n"
            "- Error handling and recovery mechanisms\n"
            "- Monitoring and alerting coverage\n\n"
            "## 7. Issue Summary\n"
            "- Prioritized table: Issue, Severity (critical/high/medium/low), Impact, Fix\n"
            "- Quick wins vs. structural problems\n"
            "- Estimated data quality score (0-100)"
        ),
    },
    {
        "title": "Dataset Search",
        "category": "Data & Metrics",
        "color": "Blue",
        "content": (
            "You are a data sourcing specialist. Find and evaluate the best available "
            "datasets and benchmarks for research in [/RESEARCH_AREA], specifically for "
            "the task of [/SPECIFIC_TASK].\n\n"
            "Go beyond simple listing. Evaluate fitness for purpose and flag risks.\n\n"
            "## 1. Tier 1: Standard Benchmarks\n"
            "For each of the top 3-5 most widely used datasets:\n"
            "- Name, creator, year released, current version\n"
            "- Size (samples, features, storage), format, and access method (URL/API/request)\n"
            "- License and usage restrictions\n"
            "- Standard evaluation metrics used with this dataset\n"
            "- Current SOTA performance on this benchmark (method + score + year)\n"
            "- Known issues: labeling errors, biases, data leakage, saturation\n\n"
            "## 2. Tier 2: Underutilized Alternatives\n"
            "- 3-5 lesser-known datasets that deserve more attention\n"
            "- For each: what makes it valuable, why it is underused, quality assessment\n\n"
            "## 3. Evaluation Protocol\n"
            "- Standard train/val/test split conventions for this domain\n"
            "- Which metrics are standard, which are more informative, and why they differ\n"
            "- Common evaluation pitfalls specific to this task\n\n"
            "## 4. Data Quality Checklist\n"
            "- For each recommended dataset, flag:\n"
            "  - Class imbalance severity\n"
            "  - Missing data patterns\n"
            "  - Temporal relevance (is the data outdated?)\n"
            "  - Geographic or demographic representation gaps\n"
            "  - Known adversarial or problematic samples\n\n"
            "## 5. Recommendation\n"
            "- Best dataset for [/SPECIFIC_TASK] with justification\n"
            "- Suggested preprocessing pipeline\n"
            "- If no perfect dataset exists, describe what an ideal one would look like "
            "and whether synthetic augmentation could fill gaps"
        ),
    },
    {
        "title": "KPI Framework",
        "category": "Data & Metrics",
        "color": "Purple",
        "content": (
            "You are a metrics and measurement strategist. Build a comprehensive KPI "
            "framework for [/BUSINESS_OBJECTIVE].\n\n"
            "Metrics should be actionable, measurable, and tied to outcomes, not vanity.\n\n"
            "## 1. Objective Decomposition\n"
            "- Break [/BUSINESS_OBJECTIVE] into 3-5 measurable sub-objectives\n"
            "- For each: what success looks like, what failure looks like\n"
            "- Causal chain: how sub-objectives drive the overall objective\n\n"
            "## 2. KPI Hierarchy\n"
            "For each sub-objective, define:\n"
            "- Primary KPI: the single most important metric\n"
            "- Supporting KPIs: 2-3 metrics that provide context and early signals\n"
            "- For each KPI: definition, formula, data source, update frequency\n\n"
            "## 3. Targets and Thresholds\n"
            "- Baseline: current performance level\n"
            "- Target: desired performance level with timeframe\n"
            "- Threshold: minimum acceptable level (red/yellow/green zones)\n"
            "- Stretch goal: aspirational but achievable\n\n"
            "## 4. Leading vs. Lagging Indicators\n"
            "- Identify which KPIs are leading (predictive) vs. lagging (outcome)\n"
            "- For leading indicators: what action to take when they move\n"
            "- For lagging indicators: what leading indicators predict them\n\n"
            "## 5. Counter-Metrics\n"
            "- For each primary KPI, define a counter-metric that prevents gaming\n"
            "- Example: if KPI is speed, counter-metric is quality\n"
            "- How to detect and prevent Goodhart's Law effects\n\n"
            "## 6. Dashboard Design\n"
            "- Recommended visualization for each KPI\n"
            "- Grouping and hierarchy for executive vs. operational views\n"
            "- Alert conditions and escalation triggers\n\n"
            "## 7. Review Cadence\n"
            "- Which metrics to review daily, weekly, monthly, quarterly\n"
            "- Decision rules: what metric movements trigger what actions"
        ),
    },
    # --- Architecture ---
    {
        "title": "System Design",
        "category": "Architecture",
        "color": "Orange",
        "content": (
            "You are a senior systems architect. Design the technical architecture "
            "for [/SYSTEM].\n\n"
            "The design should balance practical constraints with scalability. "
            "Justify every major decision.\n\n"
            "## 1. Requirements Analysis\n"
            "- Functional requirements (what the system must do)\n"
            "- Non-functional requirements (performance, reliability, security, cost)\n"
            "- Constraints (team size, timeline, existing infrastructure, budget)\n"
            "- Scale targets (users, requests/sec, data volume, growth rate)\n\n"
            "## 2. High-Level Architecture\n"
            "- System components and their responsibilities\n"
            "- Data flow between components\n"
            "- External dependencies and integrations\n"
            "- Deployment topology (cloud, on-prem, hybrid)\n\n"
            "## 3. Component Deep-Dive\n"
            "For each major component:\n"
            "- Technology choice and justification (why this over alternatives)\n"
            "- Internal architecture and key abstractions\n"
            "- API contract (inputs, outputs, error handling)\n"
            "- Scaling strategy (horizontal, vertical, auto-scaling triggers)\n\n"
            "## 4. Data Architecture\n"
            "- Data models and storage choices\n"
            "- Read/write patterns and optimization strategies\n"
            "- Caching layers and invalidation policies\n"
            "- Data consistency model (strong, eventual, causal)\n\n"
            "## 5. Reliability and Operations\n"
            "- Failure modes and recovery strategies\n"
            "- Monitoring, alerting, and observability plan\n"
            "- Backup and disaster recovery\n"
            "- SLA targets and error budgets\n\n"
            "## 6. Security Architecture\n"
            "- Authentication and authorization model\n"
            "- Data encryption (at rest, in transit)\n"
            "- Network security and access controls\n"
            "- Compliance requirements\n\n"
            "## 7. Trade-offs and Alternatives\n"
            "- Key decisions made and what was traded away\n"
            "- Under what conditions you would redesign\n"
            "- Migration path from current state to proposed architecture"
        ),
    },
    {
        "title": "ML Pipeline Design",
        "category": "Architecture",
        "color": "Red",
        "content": (
            "You are an ML systems architect. Design an end-to-end ML pipeline "
            "for [/ML_TASK].\n\n"
            "Cover the full lifecycle from data ingestion to production monitoring. "
            "This should be production-grade, not a notebook prototype.\n\n"
            "## 1. Problem Framing\n"
            "- ML task type (classification, regression, ranking, generation, etc.)\n"
            "- Input/output specification with concrete examples\n"
            "- Success criteria: what metric at what threshold means production-ready\n"
            "- Baseline: simplest possible approach and its expected performance\n\n"
            "## 2. Data Pipeline\n"
            "- Data sources and ingestion strategy\n"
            "- Feature engineering pipeline (transformations, aggregations, embeddings)\n"
            "- Feature store architecture if applicable\n"
            "- Data validation and schema enforcement\n"
            "- Handling data drift and distribution shift\n\n"
            "## 3. Model Architecture\n"
            "- Recommended model family and justification\n"
            "- Architecture details (layers, hyperparameters, training strategy)\n"
            "- Alternative architectures considered and why rejected\n"
            "- Transfer learning or pre-training strategy if applicable\n\n"
            "## 4. Training Infrastructure\n"
            "- Compute requirements (GPU type, memory, training time estimate)\n"
            "- Distributed training strategy if needed\n"
            "- Experiment tracking and versioning\n"
            "- Hyperparameter optimization approach\n\n"
            "## 5. Evaluation Framework\n"
            "- Offline evaluation: metrics, test sets, slice-based analysis\n"
            "- Online evaluation: A/B testing, shadow mode, canary deployment\n"
            "- Fairness and bias evaluation\n"
            "- Error analysis methodology\n\n"
            "## 6. Serving Architecture\n"
            "- Inference mode (batch, real-time, streaming)\n"
            "- Model serving infrastructure (containers, serverless, dedicated)\n"
            "- Latency and throughput requirements\n"
            "- Model compression or optimization for serving\n\n"
            "## 7. Monitoring and Maintenance\n"
            "- Model performance monitoring (accuracy degradation, drift detection)\n"
            "- Data quality monitoring in production\n"
            "- Retraining triggers and cadence\n"
            "- Rollback strategy and model versioning\n\n"
            "## 8. Cost Analysis\n"
            "- Training cost estimate\n"
            "- Serving cost estimate at target scale\n"
            "- Cost optimization opportunities"
        ),
    },
    # --- Implementation ---
    {
        "title": "Implementation Guide",
        "category": "Implementation",
        "color": "Green",
        "content": (
            "You are a senior engineer writing a practical implementation guide. "
            "Create a production-quality walkthrough for implementing [/TECHNIQUE_METHOD] "
            "that takes someone from concept to working code.\n\n"
            "Assume the reader is technically competent but new to this specific method. "
            "Prioritize working code over theory.\n\n"
            "## 1. Prerequisites\n"
            "- Required knowledge (be specific: not just 'ML basics' but 'gradient descent, "
            "backpropagation, basic PyTorch tensor operations')\n"
            "- Hardware requirements (GPU VRAM, RAM, disk space)\n"
            "- Software stack with exact versions that are known to work together\n\n"
            "## 2. Environment Setup\n"
            "- Step-by-step installation commands\n"
            "- Dependency management (requirements.txt / environment.yml contents)\n"
            "- Verification command to confirm setup is correct\n\n"
            "## 3. Architecture Overview\n"
            "- Describe the system in a top-down manner: major components and data flow\n"
            "- Explain the key algorithmic steps in plain language before showing code\n"
            "- Call out the 2-3 most critical design decisions and why they matter\n\n"
            "## 4. Step-by-Step Implementation\n"
            "For each major component:\n"
            "- What it does and why it is needed\n"
            "- Code with inline comments explaining non-obvious choices\n"
            "- Expected input/output shapes and types\n"
            "- How to verify this component works in isolation\n\n"
            "## 5. Common Pitfalls\n"
            "- Top 5 mistakes practitioners make, each with:\n"
            "  - The symptom (what you observe)\n"
            "  - The root cause (why it happens)\n"
            "  - The fix (exact code change or config adjustment)\n\n"
            "## 6. Testing and Validation\n"
            "- How to verify correctness beyond 'it runs without errors'\n"
            "- Expected performance range on standard benchmarks\n"
            "- Debugging strategy: what to check when results are wrong\n\n"
            "## 7. Production Considerations\n"
            "- Performance optimization tips (batching, caching, hardware utilization)\n"
            "- Scaling considerations\n"
            "- Links to reference implementations and further reading"
        ),
    },
    {
        "title": "Production Review",
        "category": "Implementation",
        "color": "Orange",
        "content": (
            "You are a senior production engineer. Review [/COMPONENT] for production "
            "readiness and identify risks before deployment.\n\n"
            "Be thorough but practical. Prioritize issues by blast radius.\n\n"
            "## 1. Functionality Review\n"
            "- Does the component do what it claims to do?\n"
            "- Edge cases: what inputs or conditions could cause unexpected behavior?\n"
            "- Error handling: are all failure modes handled gracefully?\n"
            "- Input validation: is all external input sanitized and validated?\n\n"
            "## 2. Performance Assessment\n"
            "- Expected throughput and latency under normal load\n"
            "- Behavior under peak load (2x, 5x, 10x normal)\n"
            "- Resource consumption (CPU, memory, disk, network)\n"
            "- Bottlenecks and optimization opportunities\n\n"
            "## 3. Reliability Check\n"
            "- Single points of failure\n"
            "- Dependency health: what happens when each dependency fails?\n"
            "- Timeout and retry configurations\n"
            "- Circuit breaker and fallback mechanisms\n"
            "- Graceful degradation strategy\n\n"
            "## 4. Security Review\n"
            "- Authentication and authorization coverage\n"
            "- Data handling: encryption, PII, compliance\n"
            "- Common vulnerability check (injection, XSS, CSRF, etc.)\n"
            "- Dependency vulnerabilities (outdated packages)\n\n"
            "## 5. Observability\n"
            "- Logging: are important events logged with context?\n"
            "- Metrics: are key performance indicators instrumented?\n"
            "- Tracing: can you follow a request through the system?\n"
            "- Alerting: will you know when something breaks?\n\n"
            "## 6. Deployment Readiness\n"
            "- Configuration management (no hardcoded secrets or environments)\n"
            "- Database migrations and backward compatibility\n"
            "- Rollback plan and procedure\n"
            "- Documentation for on-call engineers\n\n"
            "## 7. Verdict\n"
            "- Go / No-Go recommendation with justification\n"
            "- Blockers that must be fixed before deployment\n"
            "- Risks accepted with mitigation plans"
        ),
    },
    # --- Analysis ---
    {
        "title": "Critical Review",
        "category": "Analysis",
        "color": "Red",
        "content": (
            "You are a rigorous academic reviewer and critical thinker. Evaluate the "
            "following claim, paper, or method: [/CLAIM_PAPER_METHOD].\n\n"
            "Your job is to stress-test this work. Be respectful but unsparing. "
            "Every criticism must be specific and accompanied by a constructive suggestion. "
            "Avoid generic complaints.\n\n"
            "## 1. Claim Reconstruction\n"
            "- Restate the central claim in your own words, as precisely as possible\n"
            "- Identify the implicit claims (things assumed but not stated)\n"
            "- What would need to be true for this claim to hold?\n\n"
            "## 2. Evidence Audit\n"
            "- List each piece of evidence presented\n"
            "- For each: assess quality (anecdotal / correlational / causal / formal proof)\n"
            "- Is the evidence sufficient for the strength of the claim?\n"
            "- What evidence is conspicuously absent?\n\n"
            "## 3. Methodology Stress Test\n"
            "- Are the experimental conditions appropriate for the claim?\n"
            "- Identify confounding variables that were not controlled\n"
            "- Would the results change under different (reasonable) experimental choices?\n"
            "- Check for common statistical issues: p-hacking, multiple comparisons, "
            "cherry-picked metrics, small sample sizes\n\n"
            "## 4. Alternative Explanations\n"
            "- For each key finding, propose at least one alternative explanation\n"
            "- What experiment would distinguish the authors' explanation from yours?\n\n"
            "## 5. Reproducibility Assessment\n"
            "- Could an independent team reproduce this work from the paper alone?\n"
            "- Are code, data, and hyperparameters publicly available?\n"
            "- Are there implementation details that could significantly affect results?\n\n"
            "## 6. Generalizability\n"
            "- Under what conditions would these results NOT hold?\n"
            "- How sensitive are the conclusions to the specific setup used?\n\n"
            "## 7. Bottom Line\n"
            "- Overall confidence in the claim (high / moderate / low) with justification\n"
            "- The single strongest and weakest aspects of this work\n"
            "- What would upgrade your confidence the most?"
        ),
    },
    {
        "title": "Business Case Analysis",
        "category": "Analysis",
        "color": "Orange",
        "content": (
            "You are a strategic analyst. Analyze the business case for [/INITIATIVE] "
            "with rigorous, data-driven reasoning.\n\n"
            "Balance optimism with realism. Quantify where possible, qualify where not.\n\n"
            "## 1. Initiative Summary\n"
            "- What is [/INITIATIVE] and what problem does it solve?\n"
            "- Who benefits and how?\n"
            "- Current state vs. proposed state\n\n"
            "## 2. Market and Opportunity Analysis\n"
            "- Total addressable market (TAM) and serviceable market (SAM)\n"
            "- Market trends supporting or opposing this initiative\n"
            "- Competitive landscape: who else is doing this and how?\n\n"
            "## 3. Value Proposition\n"
            "- Quantified benefits (revenue, cost savings, efficiency gains)\n"
            "- Qualitative benefits (brand, morale, strategic positioning)\n"
            "- Time to value: when do benefits start materializing?\n\n"
            "## 4. Cost Analysis\n"
            "- Upfront costs (development, infrastructure, hiring)\n"
            "- Ongoing costs (operations, maintenance, support)\n"
            "- Hidden costs (opportunity cost, technical debt, organizational disruption)\n\n"
            "## 5. Risk Assessment\n"
            "- Technical risks: what could go wrong in execution?\n"
            "- Market risks: what if assumptions about demand are wrong?\n"
            "- Organizational risks: do we have the capability to execute?\n"
            "- For each risk: probability, impact, mitigation strategy\n\n"
            "## 6. Financial Model\n"
            "- ROI calculation with assumptions stated\n"
            "- Break-even timeline\n"
            "- Sensitivity analysis: which assumptions matter most?\n"
            "- Best case, expected case, worst case scenarios\n\n"
            "## 7. Recommendation\n"
            "- Go / No-Go / Conditional-Go with clear justification\n"
            "- Key conditions or milestones for proceeding\n"
            "- What would change your recommendation?"
        ),
    },
    # --- Draft ---
    {
        "title": "Draft Outline",
        "category": "Draft",
        "color": "Purple",
        "content": (
            "You are an experienced academic writer and research communicator. "
            "Create a publication-ready outline for a research document on [/TOPIC].\n\n"
            "This outline should be detailed enough that a knowledgeable collaborator could "
            "write a full draft from it with minimal back-and-forth.\n\n"
            "## 1. Document Metadata\n"
            "- Proposed title (concise, specific, searchable)\n"
            "- 2-3 candidate alternative titles\n"
            "- Target venue or audience\n"
            "- Document type (conference paper, journal article, technical report, blog post)\n\n"
            "## 2. Abstract Draft\n"
            "- Write a complete 150-250 word abstract covering: problem, approach, "
            "key results, and significance\n\n"
            "## 3. Thesis Statement\n"
            "- One clear sentence stating the central argument or contribution\n"
            "- What is the reader supposed to believe or understand after reading?\n\n"
            "## 4. Section-by-Section Outline\n"
            "For each section provide:\n"
            "- Section title and estimated word count / page fraction\n"
            "- 3-5 bullet points describing the content and argument flow\n"
            "- Key evidence, data, or citations to include\n"
            "- Transition: how this section connects to the next\n\n"
            "Typical structure (adapt as appropriate):\n"
            "- Introduction (problem, motivation, contribution summary)\n"
            "- Related Work (positioning, what is different about this work)\n"
            "- Method / Approach (technical details)\n"
            "- Experiments / Evaluation (setup, results, analysis)\n"
            "- Discussion (implications, limitations, broader impact)\n"
            "- Conclusion (summary, future work)\n\n"
            "## 5. Visual Elements Plan\n"
            "- List every figure, table, and diagram needed\n"
            "- For each: description of what it shows, which section it belongs to, "
            "and why it is essential (what claim does it support?)\n\n"
            "## 6. Reference Skeleton\n"
            "- Group planned citations by section\n"
            "- For each: what claim or context it supports\n"
            "- Flag any claims that currently lack a citation"
        ),
    },
    {
        "title": "Executive Brief",
        "category": "Draft",
        "color": "Green",
        "content": (
            "You are an executive communications specialist. Write a concise, "
            "high-impact briefing on [/TOPIC] for [/AUDIENCE].\n\n"
            "Executives have limited time. Every sentence must earn its place. "
            "Lead with conclusions, support with evidence, end with actions.\n\n"
            "## 1. Bottom Line Up Front (BLUF)\n"
            "- One paragraph: what is happening, why it matters, what to do about it\n"
            "- The single most important takeaway\n\n"
            "## 2. Context\n"
            "- Background the reader needs (and nothing more)\n"
            "- How this connects to current priorities or strategy\n"
            "- What triggered this briefing (event, data, request)\n\n"
            "## 3. Key Findings\n"
            "- 3-5 findings, each as a bold assertion followed by supporting evidence\n"
            "- Use specific numbers and comparisons, not vague qualifiers\n"
            "- Distinguish between facts, estimates, and opinions\n\n"
            "## 4. Implications\n"
            "- What these findings mean for [/AUDIENCE] specifically\n"
            "- Opportunities to capture\n"
            "- Risks to mitigate\n"
            "- What happens if no action is taken\n\n"
            "## 5. Options and Recommendation\n"
            "- 2-3 options with pros, cons, and resource requirements\n"
            "- Clear recommendation with justification\n"
            "- Quick win available immediately\n\n"
            "## 6. Next Steps\n"
            "- 3-5 concrete action items\n"
            "- For each: who, what, by when\n"
            "- Decision needed from the reader (if any)\n\n"
            "Formatting: Keep total length under 2 pages equivalent. "
            "Use bullet points, bold key phrases, and white space liberally. "
            "No jargon unless the audience expects it."
        ),
    },
    # --- Reference ---
    {
        "title": "Explain Concept",
        "category": "Reference",
        "color": "Gray",
        "content": (
            "You are a world-class educator. Explain [/CONCEPT] in a way that builds "
            "genuine understanding, not just surface familiarity.\n\n"
            "Layer the explanation from intuitive to rigorous. The reader should finish "
            "with both intuition and precision.\n\n"
            "## 1. One-Sentence Definition\n"
            "- Plain language, no jargon, a smart 12-year-old could understand it\n\n"
            "## 2. Intuitive Explanation\n"
            "- Explain the core idea using a concrete analogy or real-world parallel\n"
            "- Walk through a simple, specific example step by step\n"
            "- What problem does this concept solve? What would go wrong without it?\n\n"
            "## 3. Formal Definition\n"
            "- Precise technical definition with all necessary notation\n"
            "- Mathematical formulation if applicable (define every symbol)\n"
            "- State the key properties, invariants, or guarantees\n\n"
            "## 4. How It Works Mechanically\n"
            "- Step-by-step walkthrough of the process/algorithm/mechanism\n"
            "- Trace through a concrete numerical example showing intermediate values\n"
            "- What are the inputs, outputs, and internal state at each step?\n\n"
            "## 5. Connections and Context\n"
            "- How does this relate to [list 3-5 related concepts]?\n"
            "- What is it a special case of? What is a special case of it?\n"
            "- Historical context: who introduced it, when, and why\n\n"
            "## 6. Practical Significance\n"
            "- Where is this used in practice? Give 2-3 concrete applications\n"
            "- When would you choose to use this over alternatives?\n"
            "- What are the practical limitations or failure modes?\n\n"
            "## 7. Common Misconceptions\n"
            "- List 3-5 things people frequently get wrong about this concept\n"
            "- For each: the misconception, why it is wrong, and the correct understanding\n\n"
            "## 8. Test Your Understanding\n"
            "- Pose 3 questions of increasing difficulty that test genuine comprehension\n"
            "- Provide answers with explanations"
        ),
    },
    {
        "title": "Glossary Builder",
        "category": "Reference",
        "color": "Blue",
        "content": (
            "You are a technical lexicographer. Build a comprehensive glossary for "
            "the domain of [/DOMAIN].\n\n"
            "Each entry should be useful for both newcomers and practitioners who "
            "need precise definitions.\n\n"
            "## 1. Core Terms (15-25 entries)\n"
            "For each term provide:\n"
            "- **Term**: The canonical name\n"
            "- **Definition**: 1-2 sentence precise definition\n"
            "- **Plain English**: What it means in simple terms\n"
            "- **Example**: A concrete example of the term in use\n"
            "- **Related terms**: 2-3 terms that are commonly confused or associated\n"
            "- **Common misuse**: How the term is frequently misapplied (if applicable)\n\n"
            "## 2. Acronyms and Abbreviations\n"
            "- Alphabetical list of common acronyms in [/DOMAIN]\n"
            "- Full expansion and brief definition for each\n\n"
            "## 3. Concept Relationships\n"
            "- Group related terms into clusters\n"
            "- Show hierarchies (is-a relationships)\n"
            "- Show dependencies (requires understanding of)\n"
            "- Note terms that are often confused with each other and how to distinguish them\n\n"
            "## 4. Domain-Specific Usage Notes\n"
            "- Terms that mean different things in different contexts\n"
            "- Terms borrowed from other fields with shifted meaning\n"
            "- Evolving terminology (old term vs. current preferred term)\n\n"
            "## 5. Learning Order\n"
            "- Suggested order for learning these terms (prerequisites first)\n"
            "- Group into beginner, intermediate, and advanced tiers\n\n"
            "Formatting: Alphabetize entries within each section. "
            "Use consistent formatting throughout. Bold the defined term in each entry."
        ),
    },
]

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


# Dialog path persistence
DIALOG_PATHS_FILE = CONFIG_DIR / "dialog_paths.json"


def get_last_dialog_path(dialog_key: str, default: str = None) -> str:
    """Get the last used path for a specific dialog.

    Args:
        dialog_key: Unique identifier for the dialog (e.g., 'file_upload', 'notebook_open')
        default: Default path to return if no saved path exists

    Returns:
        The last used path or the default path
    """
    if default is None:
        default = str(Path.home())

    try:
        if DIALOG_PATHS_FILE.exists():
            with open(DIALOG_PATHS_FILE, 'r', encoding='utf-8') as f:
                paths = json.load(f)
                saved_path = paths.get(dialog_key)
                if saved_path and os.path.isdir(saved_path):
                    return saved_path
    except (json.JSONDecodeError, IOError):
        pass

    return default


def save_dialog_path(dialog_key: str, file_path: str) -> None:
    """Save the directory of the selected file for a specific dialog.

    Args:
        dialog_key: Unique identifier for the dialog
        file_path: The full path of the file selected (directory will be extracted)
    """
    try:
        path = Path(file_path)
        directory = str(path.parent if path.is_file() else path)

        paths = {}
        if DIALOG_PATHS_FILE.exists():
            try:
                with open(DIALOG_PATHS_FILE, 'r', encoding='utf-8') as f:
                    paths = json.load(f)
            except (json.JSONDecodeError, IOError):
                paths = {}

        paths[dialog_key] = directory

        with open(DIALOG_PATHS_FILE, 'w', encoding='utf-8') as f:
            json.dump(paths, f, indent=2)
    except (IOError, OSError):
        pass
