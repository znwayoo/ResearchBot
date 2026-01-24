"""Main orchestrator coordinating the research workflow."""

import logging
import uuid
from datetime import datetime
from typing import Callable, Optional

from agents.file_context_injector import FileContextInjector
from agents.response_merger import ResponseMerger
from agents.task_analyzer import TaskAnalyzer
from utils.browser_controller import BrowserController
from utils.clipboard_parser import ClipboardParser
from utils.local_storage import LocalStorage
from utils.models import MergedResponse, PlatformResponse, PlatformType, UserQuery

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates the complete research workflow from query to merged response."""

    def __init__(
        self,
        storage: LocalStorage = None,
        browser: BrowserController = None,
        status_callback: Callable[[str], None] = None
    ):
        self.storage = storage or LocalStorage()
        self.browser = browser or BrowserController()
        self.merger = ResponseMerger()
        self.clipboard = ClipboardParser()
        self.status_callback = status_callback or (lambda x: logger.info(x))

    def _update_status(self, message: str):
        """Update status via callback."""
        logger.info(message)
        if self.status_callback:
            self.status_callback(message)

    def execute_query(self, user_query: UserQuery) -> Optional[MergedResponse]:
        """Execute the complete research workflow."""
        query_id = str(uuid.uuid4())
        self._update_status("Starting research query...")

        try:
            self.storage.save_query(user_query)
            self._update_status("Query saved to database")
        except Exception as e:
            logger.error(f"Failed to save query: {e}")

        platforms = TaskAnalyzer.get_platform_order(
            user_query.task.value,
            user_query.model_choice
        )
        self._update_status(f"Will query platforms: {', '.join(platforms)}")

        file_context = ""
        if user_query.files:
            self._update_status(f"Processing {len(user_query.files)} uploaded files...")
            try:
                file_context = FileContextInjector.build_file_context(user_query.files)
                self._update_status("File context extracted successfully")
            except Exception as e:
                logger.error(f"Error processing files: {e}")
                self._update_status(f"Warning: Error processing files: {e}")

        full_prompt = FileContextInjector.inject_into_query(
            user_query.query_text,
            file_context
        )

        responses = []
        for platform in platforms:
            self._update_status(f"Querying {platform}...")

            try:
                response = self._query_platform(
                    platform,
                    full_prompt,
                    user_query.task.value,
                    query_id
                )

                if response:
                    responses.append(response)
                    try:
                        self.storage.save_response(response)
                    except Exception as e:
                        logger.error(f"Failed to save response: {e}")

                    self._update_status(f"Received response from {platform}")
                else:
                    self._update_status(f"No valid response from {platform}")

            except Exception as e:
                logger.error(f"Error querying {platform}: {e}")
                self._update_status(f"Error querying {platform}: {e}")

        if not responses:
            self._update_status("No valid responses received from any platform")
            return None

        self._update_status("Merging responses...")
        try:
            merged = self.merger.merge_responses(
                responses,
                query_id,
                user_query.session_id
            )

            try:
                self.storage.save_merged(merged)
            except Exception as e:
                logger.error(f"Failed to save merged response: {e}")

            self._update_status("Research complete!")
            return merged

        except Exception as e:
            logger.error(f"Error merging responses: {e}")
            self._update_status(f"Error merging responses: {e}")
            return None

    def _query_platform(
        self,
        platform: str,
        prompt: str,
        task_type: str,
        query_id: str
    ) -> Optional[PlatformResponse]:
        """Query a single platform and return the response."""
        system_prompt = TaskAnalyzer.build_system_prompt(platform, task_type)
        combined_prompt = f"{system_prompt}\n\n{prompt}"

        if not self.browser.fill_chat_input(platform, combined_prompt):
            logger.error(f"Failed to fill input for {platform}")
            return None

        if not self.browser.click_send(platform):
            logger.error(f"Failed to send query to {platform}")
            return None

        if not self.browser.wait_for_response(platform):
            logger.error(f"Timeout waiting for {platform}")
            return PlatformResponse(
                platform=PlatformType(platform),
                query_id=query_id,
                response_text="",
                timestamp=datetime.now(),
                error="Timeout waiting for response"
            )

        self.browser.copy_response(platform)
        response_text = self.browser.get_clipboard_text()

        if not self.clipboard.validate_response(response_text):
            logger.warning(f"Invalid response from {platform}")
            return PlatformResponse(
                platform=PlatformType(platform),
                query_id=query_id,
                response_text=response_text,
                timestamp=datetime.now(),
                error="Invalid or empty response"
            )

        response_text = self.clipboard.clean_text(response_text)

        return PlatformResponse(
            platform=PlatformType(platform),
            query_id=query_id,
            response_text=response_text,
            timestamp=datetime.now()
        )

    def query_single_platform(
        self,
        platform: str,
        query_text: str,
        task_type: str = "initial"
    ) -> Optional[str]:
        """Query a single platform and return just the response text."""
        query_id = str(uuid.uuid4())

        response = self._query_platform(platform, query_text, task_type, query_id)

        if response and not response.error:
            return response.response_text

        return None

    def check_platform_status(self, platform: str) -> dict:
        """Check the status of a platform."""
        try:
            page = self.browser.get_page(platform)
            is_logged_in = self.browser.is_logged_in(platform)

            return {
                "platform": platform,
                "available": page is not None,
                "logged_in": is_logged_in,
                "url": page.url if page else None
            }
        except Exception as e:
            logger.error(f"Error checking {platform} status: {e}")
            return {
                "platform": platform,
                "available": False,
                "logged_in": False,
                "error": str(e)
            }

    def cleanup(self):
        """Clean up resources."""
        self._update_status("Cleaning up...")
        try:
            self.browser.close()
            logger.info("Orchestrator cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
