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
    {
        "title": "Topic Search",
        "category": "Exploration",
        "color": "Blue",
        "content": (
            "You are a research intelligence analyst. Your task is to produce a "
            "comprehensive, well-sourced briefing on [TOPIC] that enables a researcher "
            "to go from zero knowledge to informed decision-making.\n\n"
            "Structure your response as follows:\n\n"
            "## 1. Executive Summary\n"
            "- One-paragraph definition of [TOPIC] and why it matters right now\n"
            "- The single most important thing a newcomer should understand\n\n"
            "## 2. Landscape Map\n"
            "- Break [TOPIC] into 3-5 major sub-domains or branches\n"
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
        "title": "Paper Analysis",
        "category": "Literature",
        "color": "Blue",
        "content": (
            "You are an expert peer reviewer. Perform a thorough, structured analysis of "
            "the following paper: [PAPER TITLE / URL / PASTE ABSTRACT].\n\n"
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
        "color": "Blue",
        "content": (
            "You are a systematic review specialist. Produce a structured literature "
            "survey on [TOPIC] that maps the research landscape and identifies patterns "
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
    {
        "title": "Compare Approaches",
        "category": "Methodology",
        "color": "Purple",
        "content": (
            "You are a methods expert tasked with producing a rigorous, decision-ready "
            "comparison. Compare the following approaches to [PROBLEM]:\n"
            "- Approach A: [APPROACH A]\n"
            "- Approach B: [APPROACH B]\n"
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
        "title": "Dataset Search",
        "category": "Data & Metrics",
        "color": "Green",
        "content": (
            "You are a data sourcing specialist. Find and evaluate the best available "
            "datasets and benchmarks for research in [RESEARCH AREA], specifically for "
            "the task of [SPECIFIC TASK].\n\n"
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
            "- Best dataset for [SPECIFIC TASK] with justification\n"
            "- Suggested preprocessing pipeline\n"
            "- If no perfect dataset exists, describe what an ideal one would look like "
            "and whether synthetic augmentation could fill gaps"
        ),
    },
    {
        "title": "Implementation Guide",
        "category": "Implementation",
        "color": "Green",
        "content": (
            "You are a senior engineer writing a practical implementation guide. "
            "Create a production-quality walkthrough for implementing [TECHNIQUE/METHOD] "
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
        "title": "Critical Review",
        "category": "Analysis",
        "color": "Orange",
        "content": (
            "You are a rigorous academic reviewer and critical thinker. Evaluate the "
            "following claim, paper, or method: [CLAIM/PAPER/METHOD].\n\n"
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
        "title": "SOTA Check",
        "category": "Exploration",
        "color": "Blue",
        "content": (
            "You are a competitive intelligence analyst for research. Provide a precise, "
            "up-to-date snapshot of the state-of-the-art for [TASK/PROBLEM].\n\n"
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
            "- What aspects of [TASK/PROBLEM] are current methods still bad at?\n"
            "- What is the theoretical upper bound or human-level performance?\n"
            "- What would a breakthrough in this area look like?\n\n"
            "## 6. Trajectory\n"
            "- Is progress accelerating, plateauing, or decelerating?\n"
            "- What emerging approaches could disrupt the current leaderboard?\n"
            "- What should a researcher entering this area focus on?"
        ),
    },
    {
        "title": "Draft Outline",
        "category": "Draft",
        "color": "Orange",
        "content": (
            "You are an experienced academic writer and research communicator. "
            "Create a publication-ready outline for a research document on [TOPIC].\n\n"
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
        "title": "Explain Concept",
        "category": "Reference",
        "color": "Gray",
        "content": (
            "You are a world-class educator. Explain [CONCEPT] in a way that builds "
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
