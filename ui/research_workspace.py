"""Research workspace widget that combines prompts, responses, and prompt management."""

import hashlib
from datetime import datetime
from typing import List, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.item_editor import ItemEditorDialog
from ui.items_panel import ItemsPanel
from ui.prompt_box import PromptManagementBox
from utils.local_storage import LocalStorage
from utils.models import CategoryType, ColorLabel, PromptItem, ResponseItem


class ResearchWorkspace(QWidget):
    """Main workspace widget with prompts, responses, and management controls."""

    statusUpdate = pyqtSignal(str)

    def __init__(self, storage: LocalStorage, browser_tabs, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.browser_tabs = browser_tabs

        self._setup_ui()
        self._connect_signals()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E0E0E0;
                background-color: #FAFAFA;
                border-radius: 4px;
            }
            QTabBar::tab {
                padding: 8px 16px;
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-bottom: none;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #FAFAFA;
                border-bottom: 2px solid #9C27B0;
                color: #9C27B0;
            }
            QTabBar::tab:hover {
                background-color: #E8E8E8;
            }
        """)

        self.prompts_panel = ItemsPanel(item_type="prompt")
        self.tabs.addTab(self.prompts_panel, "Prompts")

        self.responses_panel = ItemsPanel(item_type="response")
        self.tabs.addTab(self.responses_panel, "Responses")

        layout.addWidget(self.tabs, 1)

        self.prompt_box = PromptManagementBox()
        layout.addWidget(self.prompt_box)

    def _connect_signals(self):
        self.prompts_panel.itemClicked.connect(self._on_prompt_clicked)
        self.prompts_panel.deleteRequested.connect(self._on_prompt_delete)
        self.prompts_panel.orderChanged.connect(self._on_prompt_order_changed)

        self.responses_panel.itemClicked.connect(self._on_response_clicked)
        self.responses_panel.deleteRequested.connect(self._on_response_delete)
        self.responses_panel.orderChanged.connect(self._on_response_order_changed)

        self.prompt_box.sendRequested.connect(self._on_send)
        self.prompt_box.grabRequested.connect(self._on_grab)
        self.prompt_box.summarizeRequested.connect(self._on_summarize)
        self.prompt_box.savePromptRequested.connect(self._on_save_prompt)

    def _load_data(self):
        prompts = self.storage.get_all_prompts()
        self.prompts_panel.set_items(prompts)

        responses = self.storage.get_all_response_items()
        self.responses_panel.set_items(responses)

    def _on_prompt_clicked(self, item: PromptItem):
        dialog = ItemEditorDialog(item, item_type="prompt", parent=self)
        if dialog.exec():
            result = dialog.get_result()
            if result:
                self.storage.update_prompt(result)
                self.prompts_panel.update_item(result)
                self.statusUpdate.emit("Prompt updated")

    def _on_prompt_delete(self, item: PromptItem):
        reply = QMessageBox.question(
            self,
            "Delete Prompt",
            f"Delete prompt '{item.title[:50]}...'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.storage.delete_prompt(item.id)
            self.prompts_panel.remove_item(item)
            self.statusUpdate.emit("Prompt deleted")

    def _on_prompt_order_changed(self, item: PromptItem, new_order: int):
        self.storage.update_prompt_order(item.id, new_order)

    def _on_response_clicked(self, item: ResponseItem):
        dialog = ItemEditorDialog(item, item_type="response", parent=self)
        if dialog.exec():
            result = dialog.get_result()
            if result:
                self.storage.update_response_item(result)
                self.responses_panel.update_item(result)
                self.statusUpdate.emit("Response updated")

    def _on_response_delete(self, item: ResponseItem):
        reply = QMessageBox.question(
            self,
            "Delete Response",
            f"Delete response '{item.title[:50]}...'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.storage.delete_response_item(item.id)
            self.responses_panel.remove_item(item)
            self.statusUpdate.emit("Response deleted")

    def _on_response_order_changed(self, item: ResponseItem, new_order: int):
        self.storage.update_response_order(item.id, new_order)

    def _on_send(self):
        browser = self.browser_tabs.get_active_browser()
        if not browser:
            self.statusUpdate.emit("No active browser tab")
            return

        selected_prompts = self.prompts_panel.get_selected_items()
        box_text = self.prompt_box.get_text()

        combined_parts = []

        for prompt in selected_prompts:
            combined_parts.append(prompt.content)

        if box_text:
            combined_parts.append(box_text)

        if not combined_parts:
            self.statusUpdate.emit("No text to send")
            return

        combined_text = "\n\n---\n\n".join(combined_parts)

        files = self.prompt_box.get_files()
        upload_mode = self.prompt_box.get_upload_mode()

        if files and upload_mode == "inject":
            from agents.file_context_injector import FileContextInjector
            try:
                file_context = FileContextInjector.build_file_context(files)
                combined_text = FileContextInjector.inject_into_query(combined_text, file_context)
            except Exception as e:
                self.statusUpdate.emit(f"Error processing files: {e}")

        platform = self.browser_tabs.get_active_platform()
        self.statusUpdate.emit(f"Sending to {platform}...")

        def on_fill_complete(result):
            if result and ("sent" in str(result).lower() or "filled" in str(result).lower()):
                self.statusUpdate.emit(f"Text sent to {platform}")
                self.prompt_box.clear_text()
                self.prompts_panel.clear_selection()
            else:
                self.statusUpdate.emit(f"Failed to send: {result}")

        browser.fill_input_only(combined_text, on_fill_complete)

    def _on_grab(self):
        browser = self.browser_tabs.get_active_browser()
        if not browser:
            self.statusUpdate.emit("No active browser tab")
            return

        platform = self.browser_tabs.get_active_platform()
        self.statusUpdate.emit(f"Grabbing response from {platform}...")

        def on_response_received(response_text):
            if not response_text or len(response_text.strip()) < 10:
                self.statusUpdate.emit("No response found")
                return

            content_hash = hashlib.sha256(response_text.encode()).hexdigest()

            if self.storage.response_hash_exists(content_hash):
                self.statusUpdate.emit("Response already grabbed (duplicate)")
                return

            title = response_text[:80].replace("\n", " ").strip()
            if len(response_text) > 80:
                title += "..."

            response_item = ResponseItem(
                title=title,
                content=response_text,
                category=CategoryType.UNCATEGORIZED,
                color=ColorLabel.BLUE,
                platform=platform,
                content_hash=content_hash,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            response_id = self.storage.save_response_item(response_item)
            response_item.id = response_id

            self.responses_panel.add_item(response_item)
            self.tabs.setCurrentIndex(1)
            self.statusUpdate.emit(f"Response grabbed from {platform}")

        browser.get_response_text(on_response_received)

    def _on_summarize(self):
        selected_responses = self.responses_panel.get_selected_items()

        if not selected_responses:
            self.statusUpdate.emit("Select at least one response to summarize")
            return

        browser = self.browser_tabs.get_active_browser()
        if not browser:
            self.statusUpdate.emit("No active browser tab")
            return

        summary_parts = ["Please provide a comprehensive summary of the following responses:\n"]

        for i, response in enumerate(selected_responses, 1):
            source = f" (from {response.platform})" if response.platform else ""
            summary_parts.append(f"\n--- Response {i}{source} ---\n")
            summary_parts.append(response.content)

        summary_parts.append("\n\n---\n\nPlease synthesize the key points, identify common themes, and highlight any contradictions or unique insights from these responses.")

        combined_text = "\n".join(summary_parts)

        platform = self.browser_tabs.get_active_platform()
        self.statusUpdate.emit(f"Sending summarization request to {platform}...")

        def on_fill_complete(result):
            if result and ("sent" in str(result).lower() or "filled" in str(result).lower()):
                self.statusUpdate.emit(f"Summarization request sent to {platform}")
            else:
                self.statusUpdate.emit(f"Failed to send: {result}")

        browser.fill_input_only(combined_text, on_fill_complete)

    def _on_save_prompt(self):
        text = self.prompt_box.get_text()

        if not text:
            self.statusUpdate.emit("No text to save as prompt")
            return

        title = text[:80].replace("\n", " ").strip()
        if len(text) > 80:
            title += "..."

        prompt_item = PromptItem(
            title=title,
            content=text,
            category=CategoryType.UNCATEGORIZED,
            color=ColorLabel.PURPLE,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        prompt_id = self.storage.save_prompt(prompt_item)
        prompt_item.id = prompt_id

        self.prompts_panel.add_item(prompt_item)
        self.tabs.setCurrentIndex(0)
        self.prompt_box.clear_text()
        self.statusUpdate.emit("Prompt saved")

    def get_prompt_box(self) -> PromptManagementBox:
        return self.prompt_box

    def clear_files(self):
        self.prompt_box.clear_files()
