"""SQLite database storage for ResearchBot."""

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import List

from config import DB_PATH, DEFAULT_PROMPTS
from utils.models import (
    CategoryType,
    ColorLabel,
    MergedResponse,
    PlatformResponse,
    PromptItem,
    ResponseItem,
    SummaryItem,
    UserQuery,
)

logger = logging.getLogger(__name__)


class LocalStorage:
    """SQLite database manager for session and response storage."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._init_db()
        self._seed_default_prompts()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Create database tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS queries (
                    query_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    files_json TEXT,
                    model_choice TEXT,
                    mode TEXT,
                    task TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform_responses (
                    response_id TEXT PRIMARY KEY,
                    query_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    response_text TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error TEXT,
                    FOREIGN KEY (query_id) REFERENCES queries(query_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merged_responses (
                    merged_id TEXT PRIMARY KEY,
                    query_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    merged_text TEXT,
                    structure_json TEXT,
                    attribution_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (query_id) REFERENCES queries(query_id),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_queries_session ON queries(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_responses_query ON platform_responses(query_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_merged_query ON merged_responses(query_id)")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'Uncategorized',
                    color TEXT DEFAULT 'Blue',
                    custom_color_hex TEXT,
                    display_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            try:
                cursor.execute("ALTER TABLE prompts ADD COLUMN custom_color_hex TEXT")
            except sqlite3.OperationalError:
                pass

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS response_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'Uncategorized',
                    color TEXT DEFAULT 'Blue',
                    custom_color_hex TEXT,
                    platform TEXT,
                    tab_id TEXT,
                    content_hash TEXT NOT NULL UNIQUE,
                    display_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            try:
                cursor.execute("ALTER TABLE response_items ADD COLUMN custom_color_hex TEXT")
            except sqlite3.OperationalError:
                pass

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prompts_order ON prompts(display_order)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_response_items_order ON response_items(display_order)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_response_items_hash ON response_items(content_hash)")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'Uncategorized',
                    color TEXT DEFAULT 'Green',
                    custom_color_hex TEXT,
                    source_responses TEXT,
                    platform TEXT,
                    display_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            try:
                cursor.execute("ALTER TABLE summaries ADD COLUMN custom_color_hex TEXT")
            except sqlite3.OperationalError:
                pass

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_colors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    hex_value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_summaries_order ON summaries(display_order)")

            logger.info("Database initialized successfully")

    def _seed_default_prompts(self):
        """Insert default prompts if the prompts table is empty (first-time users)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM prompts")
            count = cursor.fetchone()[0]
            if count > 0:
                return

            now = datetime.now().isoformat()
            for order, prompt_data in enumerate(DEFAULT_PROMPTS):
                cursor.execute("""
                    INSERT INTO prompts (title, content, category, color, display_order, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    prompt_data["title"],
                    prompt_data["content"],
                    prompt_data["category"],
                    prompt_data["color"],
                    order,
                    now,
                    now,
                ))
            logger.info(f"Seeded {len(DEFAULT_PROMPTS)} default prompts")

    def create_session(self) -> str:
        """Create a new session and return session_id."""
        session_id = str(uuid.uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (session_id) VALUES (?)",
                (session_id,)
            )
        logger.info(f"Created session: {session_id}")
        return session_id

    def save_query(self, query: UserQuery) -> str:
        """Save a user query and return query_id."""
        query_id = str(uuid.uuid4())
        files_json = json.dumps([f.model_dump(mode="json") for f in query.files])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO queries (query_id, session_id, query_text, files_json, model_choice, mode, task, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query_id,
                query.session_id,
                query.query_text,
                files_json,
                query.model_choice,
                query.mode.value,
                query.task.value,
                query.created_at.isoformat()
            ))

        logger.info(f"Saved query: {query_id}")
        return query_id

    def save_response(self, response: PlatformResponse) -> str:
        """Save a platform response and return response_id."""
        response_id = str(uuid.uuid4())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO platform_responses (response_id, query_id, platform, response_text, timestamp, error)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                response_id,
                response.query_id,
                response.platform.value,
                response.response_text,
                response.timestamp.isoformat(),
                response.error
            ))

        logger.info(f"Saved response from {response.platform.value}: {response_id}")
        return response_id

    def save_merged(self, merged: MergedResponse) -> str:
        """Save a merged response and return merged_id."""
        merged_id = str(uuid.uuid4())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO merged_responses (merged_id, query_id, session_id, merged_text, structure_json, attribution_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                merged_id,
                merged.query_id,
                merged.session_id,
                merged.merged_text,
                json.dumps(merged.structure),
                json.dumps(merged.attribution),
                merged.created_at.isoformat()
            ))

        logger.info(f"Saved merged response: {merged_id}")
        return merged_id

    def get_session_history(self, session_id: str) -> List[dict]:
        """Retrieve all queries for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT q.*, m.merged_text, m.structure_json, m.attribution_json
                FROM queries q
                LEFT JOIN merged_responses m ON q.query_id = m.query_id
                WHERE q.session_id = ?
                ORDER BY q.created_at ASC
            """, (session_id,))
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def get_platform_responses(self, query_id: str) -> List[dict]:
        """Get all platform responses for a query."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM platform_responses
                WHERE query_id = ?
                ORDER BY timestamp ASC
            """, (query_id,))
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def get_all_sessions(self) -> List[dict]:
        """Get all sessions."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, COUNT(q.query_id) as query_count
                FROM sessions s
                LEFT JOIN queries q ON s.session_id = q.session_id
                GROUP BY s.session_id
                ORDER BY s.updated_at DESC
            """)
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def update_session(self, session_id: str, status: str = None):
        """Update session status and timestamp."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("""
                    UPDATE sessions SET updated_at = ?, status = ?
                    WHERE session_id = ?
                """, (datetime.now().isoformat(), status, session_id))
            else:
                cursor.execute("""
                    UPDATE sessions SET updated_at = ?
                    WHERE session_id = ?
                """, (datetime.now().isoformat(), session_id))

    def cleanup_session(self, session_id: str):
        """Delete a session and all related data."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM platform_responses
                WHERE query_id IN (SELECT query_id FROM queries WHERE session_id = ?)
            """, (session_id,))

            cursor.execute("DELETE FROM merged_responses WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM queries WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

        logger.info(f"Cleaned up session: {session_id}")

    def save_prompt(self, prompt: PromptItem) -> int:
        """Save a new prompt and return its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(MAX(display_order), -1) + 1 FROM prompts
            """)
            next_order = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO prompts (title, content, category, color, custom_color_hex, display_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prompt.title,
                prompt.content,
                prompt.category,
                prompt.color,
                prompt.custom_color_hex,
                next_order,
                prompt.created_at.isoformat(),
                prompt.updated_at.isoformat()
            ))
            prompt_id = cursor.lastrowid

        logger.info(f"Saved prompt: {prompt_id}")
        return prompt_id

    def update_prompt(self, prompt: PromptItem) -> bool:
        """Update an existing prompt."""
        if prompt.id is None:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE prompts
                SET title = ?, content = ?, category = ?, color = ?, custom_color_hex = ?, updated_at = ?
                WHERE id = ?
            """, (
                prompt.title,
                prompt.content,
                prompt.category,
                prompt.color,
                prompt.custom_color_hex,
                datetime.now().isoformat(),
                prompt.id
            ))

        logger.info(f"Updated prompt: {prompt.id}")
        return True

    def delete_prompt(self, prompt_id: int) -> bool:
        """Delete a prompt by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))

        logger.info(f"Deleted prompt: {prompt_id}")
        return True

    def get_all_prompts(self) -> List[PromptItem]:
        """Get all prompts ordered by display_order."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, content, category, color, custom_color_hex, display_order, created_at, updated_at
                FROM prompts
                ORDER BY display_order ASC
            """)
            rows = cursor.fetchall()

        prompts = []
        for row in rows:
            prompts.append(PromptItem(
                id=row["id"],
                title=row["title"],
                content=row["content"],
                category=row["category"] or "Uncategorized",
                color=row["color"] or "Blue",
                custom_color_hex=row["custom_color_hex"],
                display_order=row["display_order"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now()
            ))
        return prompts

    def update_prompt_order(self, prompt_id: int, new_order: int) -> bool:
        """Update the display order of a prompt."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE prompts SET display_order = ?, updated_at = ?
                WHERE id = ?
            """, (new_order, datetime.now().isoformat(), prompt_id))

        return True

    def save_response_item(self, response: ResponseItem) -> int:
        """Save a new response item and return its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(MAX(display_order), -1) + 1 FROM response_items
            """)
            next_order = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO response_items (title, content, category, color, custom_color_hex, platform, tab_id, content_hash, display_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                response.title,
                response.content,
                response.category,
                response.color,
                response.custom_color_hex,
                response.platform,
                response.tab_id,
                response.content_hash,
                next_order,
                response.created_at.isoformat(),
                response.updated_at.isoformat()
            ))
            response_id = cursor.lastrowid

        logger.info(f"Saved response item: {response_id}")
        return response_id

    def update_response_item(self, response: ResponseItem) -> bool:
        """Update an existing response item."""
        if response.id is None:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE response_items
                SET title = ?, content = ?, category = ?, color = ?, custom_color_hex = ?, updated_at = ?
                WHERE id = ?
            """, (
                response.title,
                response.content,
                response.category,
                response.color,
                response.custom_color_hex,
                datetime.now().isoformat(),
                response.id
            ))

        logger.info(f"Updated response item: {response.id}")
        return True

    def delete_response_item(self, response_id: int) -> bool:
        """Delete a response item by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM response_items WHERE id = ?", (response_id,))

        logger.info(f"Deleted response item: {response_id}")
        return True

    def get_all_response_items(self) -> List[ResponseItem]:
        """Get all response items ordered by display_order."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, content, category, color, custom_color_hex, platform, tab_id, content_hash, display_order, created_at, updated_at
                FROM response_items
                ORDER BY display_order ASC
            """)
            rows = cursor.fetchall()

        responses = []
        for row in rows:
            responses.append(ResponseItem(
                id=row["id"],
                title=row["title"],
                content=row["content"],
                category=row["category"] or "Uncategorized",
                color=row["color"] or "Blue",
                custom_color_hex=row["custom_color_hex"],
                platform=row["platform"],
                tab_id=row["tab_id"],
                content_hash=row["content_hash"],
                display_order=row["display_order"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now()
            ))
        return responses

    def response_hash_exists(self, content_hash: str) -> bool:
        """Check if a response with the given hash already exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM response_items WHERE content_hash = ? LIMIT 1
            """, (content_hash,))
            return cursor.fetchone() is not None

    def update_response_order(self, response_id: int, new_order: int) -> bool:
        """Update the display order of a response item."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE response_items SET display_order = ?, updated_at = ?
                WHERE id = ?
            """, (new_order, datetime.now().isoformat(), response_id))

        return True

    def save_summary(self, summary: SummaryItem) -> int:
        """Save a new summary and return its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(MAX(display_order), -1) + 1 FROM summaries
            """)
            next_order = cursor.fetchone()[0]

            source_json = json.dumps(summary.source_responses)

            cursor.execute("""
                INSERT INTO summaries (title, content, category, color, custom_color_hex, source_responses, platform, display_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                summary.title,
                summary.content,
                summary.category,
                summary.color,
                summary.custom_color_hex,
                source_json,
                summary.platform,
                next_order,
                summary.created_at.isoformat(),
                summary.updated_at.isoformat()
            ))
            summary_id = cursor.lastrowid

        logger.info(f"Saved summary: {summary_id}")
        return summary_id

    def update_summary(self, summary: SummaryItem) -> bool:
        """Update an existing summary."""
        if summary.id is None:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE summaries
                SET title = ?, content = ?, category = ?, color = ?, custom_color_hex = ?, updated_at = ?
                WHERE id = ?
            """, (
                summary.title,
                summary.content,
                summary.category,
                summary.color,
                summary.custom_color_hex,
                datetime.now().isoformat(),
                summary.id
            ))

        logger.info(f"Updated summary: {summary.id}")
        return True

    def delete_summary(self, summary_id: int) -> bool:
        """Delete a summary by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM summaries WHERE id = ?", (summary_id,))

        logger.info(f"Deleted summary: {summary_id}")
        return True

    def get_all_summaries(self) -> List[SummaryItem]:
        """Get all summaries ordered by display_order."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, content, category, color, custom_color_hex, source_responses, platform, display_order, created_at, updated_at
                FROM summaries
                ORDER BY display_order ASC
            """)
            rows = cursor.fetchall()

        summaries = []
        for row in rows:
            source_responses = json.loads(row["source_responses"]) if row["source_responses"] else []
            summaries.append(SummaryItem(
                id=row["id"],
                title=row["title"],
                content=row["content"],
                category=row["category"] or "Uncategorized",
                color=row["color"] or "Green",
                custom_color_hex=row["custom_color_hex"],
                source_responses=source_responses,
                platform=row["platform"],
                display_order=row["display_order"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now()
            ))
        return summaries

    def update_summary_order(self, summary_id: int, new_order: int) -> bool:
        """Update the display order of a summary."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE summaries SET display_order = ?, updated_at = ?
                WHERE id = ?
            """, (new_order, datetime.now().isoformat(), summary_id))

        return True

    def add_custom_category(self, name: str) -> int:
        """Add a custom category and return its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO custom_categories (name, created_at)
                VALUES (?, ?)
            """, (name, datetime.now().isoformat()))
            return cursor.lastrowid

    def get_custom_categories(self) -> List[str]:
        """Get all custom categories."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM custom_categories ORDER BY name")
            rows = cursor.fetchall()
        return [row["name"] for row in rows]

    def rename_custom_category(self, old_name: str, new_name: str) -> bool:
        """Rename a custom category and update all items using it."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE custom_categories SET name = ? WHERE name = ?",
                (new_name, old_name)
            )
            cursor.execute(
                "UPDATE prompts SET category = ? WHERE category = ?",
                (new_name, old_name)
            )
            cursor.execute(
                "UPDATE response_items SET category = ? WHERE category = ?",
                (new_name, old_name)
            )
            cursor.execute(
                "UPDATE summaries SET category = ? WHERE category = ?",
                (new_name, old_name)
            )
        logger.info(f"Renamed category '{old_name}' to '{new_name}'")
        return True

    def delete_custom_category(self, name: str) -> bool:
        """Delete a custom category and set items to Uncategorized."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM custom_categories WHERE name = ?", (name,))
            cursor.execute(
                "UPDATE prompts SET category = 'Uncategorized' WHERE category = ?",
                (name,)
            )
            cursor.execute(
                "UPDATE response_items SET category = 'Uncategorized' WHERE category = ?",
                (name,)
            )
            cursor.execute(
                "UPDATE summaries SET category = 'Uncategorized' WHERE category = ?",
                (name,)
            )
        logger.info(f"Deleted category '{name}'")
        return True

    def add_custom_color(self, name: str, hex_value: str) -> int:
        """Add a custom color and return its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO custom_colors (name, hex_value, created_at)
                VALUES (?, ?, ?)
            """, (name, hex_value, datetime.now().isoformat()))
            return cursor.lastrowid

    def get_custom_colors(self) -> List[dict]:
        """Get all custom colors."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, hex_value FROM custom_colors ORDER BY created_at")
            rows = cursor.fetchall()
        return [{"name": row["name"], "hex": row["hex_value"]} for row in rows]
