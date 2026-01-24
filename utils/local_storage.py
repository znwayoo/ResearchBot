"""SQLite database storage for ResearchBot."""

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import List

from config import DB_PATH
from utils.models import MergedResponse, PlatformResponse, UserQuery

logger = logging.getLogger(__name__)


class LocalStorage:
    """SQLite database manager for session and response storage."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._init_db()

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

            logger.info("Database initialized successfully")

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
