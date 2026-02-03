"""Research workspace widget that combines prompts, responses, summaries, and management."""

import hashlib
from datetime import datetime
from typing import List, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import DARK_THEME, get_last_dialog_path, save_dialog_path
from utils.placeholder_utils import (
    extract_placeholders,
    parse_placeholder_values,
    strip_placeholder_entries,
    substitute_placeholders,
)
from ui.item_editor import ItemEditorDialog
from ui.sidebar_tabs import MarkdownNotebookTab
from ui.items_panel import ItemsPanel
from ui.prompt_box import PromptManagementBox
from utils.local_storage import LocalStorage
from utils.models import PromptItem, ResponseItem, SummaryItem
from workers.file_extraction_worker import FileExtractionWorker


class ResearchWorkspace(QWidget):
    """Main workspace widget with prompts, responses, summaries, and management controls."""

    statusUpdate = pyqtSignal(str)

    def __init__(self, storage: LocalStorage, browser_tabs, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.browser_tabs = browser_tabs
        self._known_file_paths = set()
        self._file_workers = []

        self._setup_ui()
        self._connect_signals()
        self._load_data()
        self.prompt_box.set_active_tab(0)

    def _setup_ui(self):
        self.setStyleSheet(f"background-color: {DARK_THEME['background']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {DARK_THEME['border']};
                background-color: {DARK_THEME['background']};
                border-radius: 4px;
            }}
            QTabBar::tab {{
                padding: 8px 16px;
                background-color: {DARK_THEME['surface']};
                border: 1px solid {DARK_THEME['border']};
                border-bottom: none;
                margin-right: 2px;
                font-weight: bold;
                color: {DARK_THEME['text_secondary']};
            }}
            QTabBar::tab:selected {{
                background-color: {DARK_THEME['background']};
                border-bottom: 2px solid {DARK_THEME['accent']};
                color: {DARK_THEME['accent']};
            }}
            QTabBar::tab:hover {{
                background-color: {DARK_THEME['surface_light']};
                color: {DARK_THEME['text_primary']};
            }}
        """)

        self.prompts_panel = ItemsPanel(item_type="prompt", storage=self.storage)
        self.tabs.addTab(self.prompts_panel, "Prompts")

        self.responses_panel = ItemsPanel(item_type="response", storage=self.storage)
        self.tabs.addTab(self.responses_panel, "Responses")

        self.summaries_panel = ItemsPanel(item_type="summary", storage=self.storage)
        self.tabs.addTab(self.summaries_panel, "Summaries")

        self.notebook_tab = MarkdownNotebookTab()
        self.tabs.addTab(self.notebook_tab, "Notebook")

        layout.addWidget(self.tabs, 1)

        # Action bar: Export, Delete, selection count
        action_bar = QWidget()
        action_bar.setFixedHeight(36)
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(8, 0, 8, 0)
        action_layout.setSpacing(8)

        btn_style = f"""
            QPushButton {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['surface_light']};
            }}
        """

        self.export_btn = QPushButton("Export")
        self.export_btn.setStyleSheet(btn_style)
        self.export_btn.setFixedHeight(28)
        self.export_btn.clicked.connect(self._on_action_export)
        action_layout.addWidget(self.export_btn)

        self.move_btn = QPushButton("Move")
        self.move_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['accent']};
                color: white;
            }}
            QPushButton:disabled {{
                color: {DARK_THEME['text_secondary']};
                background-color: {DARK_THEME['surface']};
            }}
        """)
        self.move_btn.setFixedHeight(28)
        self.move_btn.setEnabled(False)
        self.move_btn.clicked.connect(self._on_action_move)
        action_layout.addWidget(self.move_btn)

        self.clear_sel_btn = QPushButton("Clear Selection")
        self.clear_sel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['surface_light']};
            }}
            QPushButton:disabled {{
                color: {DARK_THEME['text_secondary']};
                background-color: {DARK_THEME['surface']};
            }}
        """)
        self.clear_sel_btn.setFixedHeight(28)
        self.clear_sel_btn.setEnabled(False)
        self.clear_sel_btn.clicked.connect(self._on_clear_selection)
        action_layout.addWidget(self.clear_sel_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['error']};
                color: white;
            }}
            QPushButton:disabled {{
                color: {DARK_THEME['text_secondary']};
                background-color: {DARK_THEME['surface']};
            }}
        """)
        self.delete_btn.setFixedHeight(28)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_action_delete)
        action_layout.addWidget(self.delete_btn)

        action_layout.addStretch()

        self.selection_label = QLabel("")
        self.selection_label.setStyleSheet(
            f"color: {DARK_THEME['accent']}; font-size: 12px; font-weight: bold;"
        )
        action_layout.addWidget(self.selection_label)

        self.action_bar = action_bar
        layout.addWidget(self.action_bar)

        self.prompt_box = PromptManagementBox()
        layout.addWidget(self.prompt_box)

    def _connect_signals(self):
        self.prompts_panel.itemClicked.connect(self._on_prompt_clicked)
        self.prompts_panel.deleteRequested.connect(self._on_prompt_delete)
        self.prompts_panel.selectionChanged.connect(self._on_selection_changed)
        self.prompts_panel.deleteSelectedRequested.connect(self._on_bulk_delete_prompts)
        self.prompts_panel.orderChanged.connect(self._on_prompt_order_changed)
        self.prompts_panel.exportRequested.connect(self._on_export_prompts)
        self.prompts_panel.categoriesChanged.connect(self._refresh_all_category_filters)

        self.responses_panel.itemClicked.connect(self._on_response_clicked)
        self.responses_panel.deleteRequested.connect(self._on_response_delete)
        self.responses_panel.selectionChanged.connect(self._on_selection_changed)
        self.responses_panel.deleteSelectedRequested.connect(self._on_bulk_delete_responses)
        self.responses_panel.orderChanged.connect(self._on_response_order_changed)
        self.responses_panel.exportRequested.connect(self._on_export_responses)
        self.responses_panel.categoriesChanged.connect(self._refresh_all_category_filters)

        self.summaries_panel.itemClicked.connect(self._on_summary_clicked)
        self.summaries_panel.deleteRequested.connect(self._on_summary_delete)
        self.summaries_panel.selectionChanged.connect(self._on_selection_changed)
        self.summaries_panel.deleteSelectedRequested.connect(self._on_bulk_delete_summaries)
        self.summaries_panel.orderChanged.connect(self._on_summary_order_changed)
        self.summaries_panel.exportRequested.connect(self._on_export_summaries)
        self.summaries_panel.categoriesChanged.connect(self._refresh_all_category_filters)

        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.prompt_box.sendRequested.connect(self._on_send)
        self.prompt_box.grabRequested.connect(self._on_grab)
        self.prompt_box.summarizeRequested.connect(self._on_summarize)
        self.prompt_box.savePromptRequested.connect(self._on_save_prompt)
        self.prompt_box.deleteSelectedRequested.connect(self._on_delete_selected)
        self.prompt_box.filesChanged.connect(self._on_files_changed)
        self.prompt_box.convertRequested.connect(self._on_convert_files)
        self.notebook_tab.createPromptRequested.connect(self._on_notebook_create_prompt)

    def _load_data(self):
        prompts = self.storage.get_all_prompts()
        self.prompts_panel.set_items(prompts)

        responses = self.storage.get_all_response_items()
        self.responses_panel.set_items(responses)

        summaries = self.storage.get_all_summaries()
        self.summaries_panel.set_items(summaries)

    def _on_prompt_clicked(self, item: PromptItem):
        dialog = ItemEditorDialog(item, item_type="prompt", storage=self.storage, parent=self)
        dialog.deleteRequested.connect(self._on_prompt_delete)
        if dialog.exec():
            result = dialog.get_result()
            if result:
                self.storage.update_prompt(result)
                self.prompts_panel.update_item(result)
                self._refresh_all_category_filters()
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

    def _on_response_clicked(self, item: ResponseItem):
        dialog = ItemEditorDialog(item, item_type="response", storage=self.storage, parent=self)
        dialog.deleteRequested.connect(self._on_response_delete)
        if dialog.exec():
            result = dialog.get_result()
            if result:
                self.storage.update_response_item(result)
                self.responses_panel.update_item(result)
                self._refresh_all_category_filters()
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

    def _on_summary_clicked(self, item: SummaryItem):
        dialog = ItemEditorDialog(item, item_type="summary", storage=self.storage, parent=self)
        dialog.deleteRequested.connect(self._on_summary_delete)
        if dialog.exec():
            result = dialog.get_result()
            if result:
                self.storage.update_summary(result)
                self.summaries_panel.update_item(result)
                self._refresh_all_category_filters()
                self.statusUpdate.emit("Summary updated")

    def _on_summary_delete(self, item: SummaryItem):
        reply = QMessageBox.question(
            self,
            "Delete Summary",
            f"Delete summary '{item.title[:50]}...'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.storage.delete_summary(item.id)
            self.summaries_panel.remove_item(item)
            self.statusUpdate.emit("Summary deleted")

    def _on_send(self):
        browser = self.browser_tabs.get_active_browser()
        if not browser:
            self.statusUpdate.emit("No active browser tab")
            return

        selected_prompts = self.prompts_panel.get_selected_items()
        box_text = self.prompt_box.get_text()

        # Parse placeholder values from box text and substitute into prompts
        placeholder_values = parse_placeholder_values(box_text)
        clean_box_text = strip_placeholder_entries(box_text) if placeholder_values else box_text

        combined_parts = []

        for prompt in selected_prompts:
            content = prompt.content
            if placeholder_values:
                content = substitute_placeholders(content, placeholder_values)
            combined_parts.append(content)

        if clean_box_text:
            combined_parts.append(clean_box_text)

        if not combined_parts:
            self.statusUpdate.emit("No text to send")
            return

        combined_text = "\n\n---\n\n".join(combined_parts)
        self._finish_send(combined_text)

    def _finish_send(self, combined_text):
        """Complete the send after file extraction (or immediately if no files)."""
        self.prompt_box.set_send_enabled(True)
        browser = self.browser_tabs.get_active_browser()
        if not browser:
            self.statusUpdate.emit("No active browser tab")
            return

        platform = self.browser_tabs.get_active_platform()
        self.statusUpdate.emit(f"Sending to {platform}...")

        def on_fill_complete(result):
            if result and ("sent" in str(result).lower() or "filled" in str(result).lower()):
                self.statusUpdate.emit(f"Text sent to {platform}")
            else:
                self.statusUpdate.emit(f"Failed to send: {result}")

        browser.fill_input_only(combined_text, on_fill_complete)

    def _on_files_changed(self, files):
        """Track uploaded files (no longer auto-converts)."""
        self._known_file_paths = {f.path for f in files}
        if files:
            self.statusUpdate.emit(f"{len(files)} file(s) ready - click Convert to create pills")

    def _on_convert_files(self):
        """Convert uploaded files to prompt pills when Convert button is clicked."""
        files = self.prompt_box.get_files()
        if not files:
            return

        self.statusUpdate.emit(f"Converting {len(files)} file(s)...")

        for file in files:
            worker = FileExtractionWorker([file])
            self._file_workers.append(worker)

            def make_handler(f, w):
                def on_complete(context):
                    # Strip the header wrapper, get raw content
                    lines = context.split("\n")
                    content_lines = []
                    for line in lines:
                        if line.startswith("## UPLOADED FILE CONTEXT") or line.startswith("### File:"):
                            continue
                        content_lines.append(line)
                    raw_content = "\n".join(content_lines).strip()

                    # Check if extraction produced empty content
                    if not raw_content or len(raw_content) < 10:
                        self.statusUpdate.emit(f"Warning: {f.filename} extracted with little/no content")

                    # Strip references section if checkbox is checked
                    if self.prompt_box.is_no_reference():
                        raw_content = self._strip_references(raw_content)

                    title = f.filename[:60]
                    prompt_item = PromptItem(
                        title=title,
                        content=raw_content,
                        category="Uncategorized",
                        color="Purple",
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                    )
                    prompt_id = self.storage.save_prompt(prompt_item)
                    prompt_item.id = prompt_id
                    self.prompts_panel.add_item(prompt_item)
                    self.statusUpdate.emit(f"Created prompt from {f.filename}")

                    # Remove the file chip after conversion
                    self._known_file_paths.discard(f.path)
                    self.prompt_box._remove_file(f.filename)

                    if w in self._file_workers:
                        self._file_workers.remove(w)
                return on_complete
            worker.extractionComplete.connect(make_handler(file, worker))
            worker.extractionError.connect(
                lambda err, fn=file.filename: self.statusUpdate.emit(
                    f"Failed to extract {fn}: {err}"
                )
            )
            worker.start()

    def _on_notebook_create_prompt(self, title: str, content: str):
        """Create a prompt pill from the notebook content."""
        prompt_item = PromptItem(
            title=title,
            content=content,
            category="Uncategorized",
            color="Gray",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        prompt_id = self.storage.save_prompt(prompt_item)
        prompt_item.id = prompt_id
        self.prompts_panel.add_item(prompt_item)
        self.tabs.setCurrentIndex(0)
        self.statusUpdate.emit("Prompt created from notebook")

    def _strip_references(self, text: str) -> str:
        """Strip bibliography/references section from extracted text."""
        import re
        lines = text.split("\n")
        # Match various reference section headers:
        # - Optional numbering like "7." or "VII."
        # - Optional markdown headers (#, ##, ###)
        # - The word References/Bibliography/Works Cited
        # - Optional punctuation like colon or period
        ref_pattern = re.compile(
            r'^\s*(?:#{1,3}\s*)?'  # Optional markdown headers
            r'(?:[0-9]+\.?\s*|[IVXLC]+\.?\s*)?'  # Optional numbering (arabic or roman)
            r'(references|bibliography|works\s*cited|cited\s*works|literature\s*cited)'
            r'\s*[:\.]?\s*$',  # Optional colon/period at end
            re.IGNORECASE,
        )
        for i, line in enumerate(lines):
            if ref_pattern.match(line):
                return "\n".join(lines[:i]).rstrip()
        return text

    def _on_grab(self):
        browser = self.browser_tabs.get_active_browser()
        if not browser:
            self.statusUpdate.emit("No active browser tab")
            return

        platform = self.browser_tabs.get_active_platform()
        current_tab = self.tabs.currentIndex()

        if current_tab == 2:
            self.statusUpdate.emit(f"Grabbing summary from {platform}...")
        else:
            self.statusUpdate.emit(f"Grabbing response from {platform}...")

        def on_response_received(response_text):
            if not response_text or len(response_text.strip()) < 10:
                self.statusUpdate.emit("No response found")
                return

            content_hash = hashlib.sha256(response_text.encode()).hexdigest()

            title = response_text[:80].replace("\n", " ").strip()
            if len(response_text) > 80:
                title += "..."

            if current_tab == 2:
                source_ids = getattr(self, '_pending_summary_sources', [])

                summary_item = SummaryItem(
                    title=title,
                    content=response_text,
                    category="Uncategorized",
                    color="Green",
                    source_responses=source_ids,
                    platform=platform,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )

                summary_id = self.storage.save_summary(summary_item)
                summary_item.id = summary_id

                self.summaries_panel.add_item(summary_item)
                self.statusUpdate.emit(f"Summary grabbed from {platform}")
            else:
                if self.storage.response_hash_exists(content_hash):
                    self.statusUpdate.emit("Response already grabbed (duplicate)")
                    return

                response_item = ResponseItem(
                    title=title,
                    content=response_text,
                    category="Uncategorized",
                    color="Blue",
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

        source_ids = []
        for i, response in enumerate(selected_responses, 1):
            source = f" (from {response.platform})" if response.platform else ""
            summary_parts.append(f"\n--- Response {i}{source} ---\n")
            summary_parts.append(response.content)
            if response.id:
                source_ids.append(response.id)

        summary_parts.append("\n\n---\n\nPlease synthesize the key points, identify common themes, and highlight any contradictions or unique insights from these responses.")

        combined_text = "\n".join(summary_parts)

        platform = self.browser_tabs.get_active_platform()
        self.statusUpdate.emit(f"Sending summarization request to {platform}...")

        self._pending_summary_sources = source_ids
        self._pending_summary_platform = platform

        def on_fill_complete(result):
            if result and ("sent" in str(result).lower() or "filled" in str(result).lower()):
                self.statusUpdate.emit(f"Summarization request sent to {platform}")
            else:
                self.statusUpdate.emit(f"Failed to send: {result}")

        browser.fill_input_only(combined_text, on_fill_complete)

    def grab_summary(self):
        """Grab the current response as a summary."""
        browser = self.browser_tabs.get_active_browser()
        if not browser:
            self.statusUpdate.emit("No active browser tab")
            return

        platform = self.browser_tabs.get_active_platform()
        self.statusUpdate.emit(f"Grabbing summary from {platform}...")

        def on_response_received(response_text):
            if not response_text or len(response_text.strip()) < 10:
                self.statusUpdate.emit("No response found")
                return

            title = response_text[:80].replace("\n", " ").strip()
            if len(response_text) > 80:
                title += "..."

            source_ids = getattr(self, '_pending_summary_sources', [])

            summary_item = SummaryItem(
                title=title,
                content=response_text,
                category="Uncategorized",
                color="Green",
                source_responses=source_ids,
                platform=platform,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            summary_id = self.storage.save_summary(summary_item)
            summary_item.id = summary_id

            self.summaries_panel.add_item(summary_item)
            self.tabs.setCurrentIndex(2)
            self.statusUpdate.emit(f"Summary grabbed from {platform}")

        browser.get_response_text(on_response_received)

    def _on_tab_changed(self):
        """Handle tab switching, hiding action bar and prompt box for Notebook."""
        tab_index = self.tabs.currentIndex()
        is_notebook = tab_index == 3
        self.action_bar.setVisible(not is_notebook)
        self.prompt_box.setVisible(not is_notebook)
        if not is_notebook:
            self.prompt_box.set_active_tab(tab_index)
            self._on_selection_changed([])

    def _on_selection_changed(self, selected_items: List):
        """Update action bar and prompt box based on selections."""
        current_panel = self._get_active_panel()
        count = len(current_panel.get_selected_items()) if current_panel else 0

        self.delete_btn.setEnabled(count > 0)
        self.move_btn.setEnabled(count > 0)
        self.clear_sel_btn.setEnabled(count > 0)
        if count > 0:
            self.selection_label.setText(f"{count} selected")
        else:
            self.selection_label.setText("")

        total_selected = (
            len(self.prompts_panel.get_selected_items()) +
            len(self.responses_panel.get_selected_items()) +
            len(self.summaries_panel.get_selected_items())
        )
        self.prompt_box.set_selection_active(total_selected > 0)

        # Extract placeholders from selected items in the active tab
        all_placeholders = []
        if current_panel:
            for item in current_panel.get_selected_items():
                for ph in extract_placeholders(item.content):
                    if ph not in all_placeholders:
                        all_placeholders.append(ph)
        self.prompt_box.update_placeholders(all_placeholders)

    def _on_clear_selection(self):
        """Clear selections on all panels."""
        self.prompts_panel.clear_selection()
        self.responses_panel.clear_selection()
        self.summaries_panel.clear_selection()

    def _get_active_panel(self) -> Optional[ItemsPanel]:
        """Return the currently active items panel, or None for Notebook."""
        idx = self.tabs.currentIndex()
        if idx == 3:
            return None
        return [self.prompts_panel, self.responses_panel, self.summaries_panel][idx]

    def _on_action_export(self):
        """Trigger export on the active panel."""
        panel = self._get_active_panel()
        if not panel:
            return
        panel._on_export()

    def _on_action_delete(self):
        """Trigger delete on the active panel."""
        panel = self._get_active_panel()
        if not panel:
            return
        panel.delete_selected()

    def _on_action_move(self):
        """Show menu to move selected items to another tab."""
        panel = self._get_active_panel()
        if not panel:
            return
        selected = panel.get_selected_items()
        if not selected:
            return

        tab_names = ["Prompts", "Responses", "Summaries"]
        tab_types = ["prompt", "response", "summary"]
        current_idx = self.tabs.currentIndex()

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {DARK_THEME['surface']};
                color: {DARK_THEME['text_primary']};
                border: 1px solid {DARK_THEME['border']};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
            }}
            QMenu::item:selected {{
                background-color: {DARK_THEME['accent']};
                color: white;
            }}
        """)

        for i, name in enumerate(tab_names):
            if i == current_idx:
                continue
            action = menu.addAction(f"Move to {name}")
            action.setData(i)

        chosen = menu.exec(self.move_btn.mapToGlobal(self.move_btn.rect().topRight()))
        if chosen:
            target_idx = chosen.data()
            self._move_items(selected, tab_types[current_idx], tab_types[target_idx], target_idx)

    def _move_items(self, items, source_type, target_type, target_tab_idx):
        """Move items from one tab type to another."""
        now = datetime.now()
        source_panel = self._get_active_panel()
        target_panel = [self.prompts_panel, self.responses_panel, self.summaries_panel][target_tab_idx]

        for item in items:
            shared = {
                "title": item.title,
                "content": item.content,
                "category": item.category,
                "color": item.color,
                "custom_color_hex": item.custom_color_hex,
                "created_at": item.created_at,
                "updated_at": now,
            }
            platform = getattr(item, "platform", None)

            if target_type == "prompt":
                new_item = PromptItem(**shared)
                new_id = self.storage.save_prompt(new_item)
                new_item.id = new_id
            elif target_type == "response":
                content_hash = hashlib.sha256(item.content.encode()).hexdigest()
                new_item = ResponseItem(**shared, platform=platform, content_hash=content_hash)
                new_id = self.storage.save_response_item(new_item)
                new_item.id = new_id
            else:
                new_item = SummaryItem(**shared, platform=platform, source_responses=[])
                new_id = self.storage.save_summary(new_item)
                new_item.id = new_id

            # Delete from source
            if source_type == "prompt":
                self.storage.delete_prompt(item.id)
            elif source_type == "response":
                self.storage.delete_response_item(item.id)
            else:
                self.storage.delete_summary(item.id)

            source_panel.remove_item(item)
            target_panel.add_item(new_item)

        source_panel.clear_selection()
        self.tabs.setCurrentIndex(target_tab_idx)
        tab_name = ["Prompts", "Responses", "Summaries"][target_tab_idx]
        self.statusUpdate.emit(f"Moved {len(items)} item(s) to {tab_name}")

    def _on_delete_selected(self):
        """Delete all selected items from the current active tab."""
        current_tab = self.tabs.currentIndex()
        if current_tab == 0:
            self.prompts_panel.delete_selected()
        elif current_tab == 1:
            self.responses_panel.delete_selected()
        elif current_tab == 2:
            self.summaries_panel.delete_selected()

    def _on_bulk_delete_prompts(self, items: List[PromptItem]):
        """Handle bulk deletion of prompts."""
        if not items:
            return

        reply = QMessageBox.question(
            self,
            "Delete Prompts",
            f"Delete {len(items)} selected prompt(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for item in items:
                self.storage.delete_prompt(item.id)
                self.prompts_panel.remove_item(item)
            self.statusUpdate.emit(f"{len(items)} prompt(s) deleted")
            self.prompt_box.set_selection_active(False)

    def _on_bulk_delete_responses(self, items: List[ResponseItem]):
        """Handle bulk deletion of responses."""
        if not items:
            return

        reply = QMessageBox.question(
            self,
            "Delete Responses",
            f"Delete {len(items)} selected response(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for item in items:
                self.storage.delete_response_item(item.id)
                self.responses_panel.remove_item(item)
            self.statusUpdate.emit(f"{len(items)} response(s) deleted")
            self.prompt_box.set_selection_active(False)

    def _on_bulk_delete_summaries(self, items: List[SummaryItem]):
        """Handle bulk deletion of summaries."""
        if not items:
            return

        reply = QMessageBox.question(
            self,
            "Delete Summaries",
            f"Delete {len(items)} selected summary(ies)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for item in items:
                self.storage.delete_summary(item.id)
                self.summaries_panel.remove_item(item)
            self.statusUpdate.emit(f"{len(items)} summary(ies) deleted")
            self.prompt_box.set_selection_active(False)

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
            category="Uncategorized",
            color="Purple",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        prompt_id = self.storage.save_prompt(prompt_item)
        prompt_item.id = prompt_id

        self.prompts_panel.add_item(prompt_item)
        self.tabs.setCurrentIndex(0)
        self.prompt_box.clear_text()
        self.statusUpdate.emit("Prompt saved")

    def _on_prompt_order_changed(self, item, new_order: int):
        """Handle prompt reorder."""
        for i, prompt in enumerate(self.prompts_panel.items):
            self.storage.update_prompt_order(prompt.id, i)
        self.statusUpdate.emit("Prompt order updated")

    def _on_response_order_changed(self, item, new_order: int):
        """Handle response reorder."""
        for i, response in enumerate(self.responses_panel.items):
            self.storage.update_response_order(response.id, i)
        self.statusUpdate.emit("Response order updated")

    def _on_summary_order_changed(self, item, new_order: int):
        """Handle summary reorder."""
        for i, summary in enumerate(self.summaries_panel.items):
            self.storage.update_summary_order(summary.id, i)
        self.statusUpdate.emit("Summary order updated")

    def _refresh_all_category_filters(self):
        """Refresh category filters and sync in-memory items after category changes."""
        # Reload items from DB so deleted categories show as Uncategorized
        self._reload_all_items()
        self.prompts_panel.refresh_categories()
        self.responses_panel.refresh_categories()
        self.summaries_panel.refresh_categories()

    def _reload_all_items(self):
        """Reload all items from storage to pick up category changes."""
        # _selected_ids are preserved automatically since set_items doesn't clear them
        prompts = self.storage.get_all_prompts()
        self.prompts_panel.set_items(prompts)

        responses = self.storage.get_all_response_items()
        self.responses_panel.set_items(responses)

        summaries = self.storage.get_all_summaries()
        self.summaries_panel.set_items(summaries)

    def _on_export_prompts(self, items: List[PromptItem]):
        """Export prompts to a text file."""
        self._export_items(items, "prompts")

    def _on_export_responses(self, items: List[ResponseItem]):
        """Export responses to a text file."""
        self._export_items(items, "responses")

    def _on_export_summaries(self, items: List[SummaryItem]):
        """Export summaries to a text file."""
        self._export_items(items, "summaries")

    def _export_items(self, items: List, item_type: str):
        """Export items to a file."""
        if not items:
            self.statusUpdate.emit("No items to export")
            return

        from pathlib import Path
        last_path = get_last_dialog_path("export_items")
        default_filename = f"{item_type}_export.pdf"
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            f"Export {item_type.title()}",
            str(Path(last_path) / default_filename),
            "PDF Files (*.pdf);;Text Files (*.txt);;Markdown Files (*.md);;All Files (*)"
        )

        if not file_path:
            return

        save_dialog_path("export_items", file_path)

        try:
            if file_path.endswith('.pdf') or 'PDF' in selected_filter:
                self._export_to_pdf(items, item_type, file_path)
            else:
                self._export_to_text(items, item_type, file_path)

            self.statusUpdate.emit(f"Exported {len(items)} {item_type} to {file_path}")
        except Exception as e:
            self.statusUpdate.emit(f"Export failed: {e}")

    def _export_to_text(self, items: List, item_type: str, file_path: str):
        """Export items to text/markdown file."""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {item_type.title()} Export\n\n")
            for i, item in enumerate(items, 1):
                f.write(f"## {i}. {item.title}\n")
                f.write(f"Category: {item.category}\n")
                if hasattr(item, 'platform') and item.platform:
                    f.write(f"Platform: {item.platform}\n")
                f.write(f"\n{item.content}\n")
                f.write("\n---\n\n")

    def _export_to_pdf(self, items: List, item_type: str, file_path: str):
        """Export items to a nicely formatted PDF."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
            from reportlab.lib.enums import TA_LEFT, TA_CENTER
        except ImportError:
            # Fallback to text if reportlab not installed
            self.statusUpdate.emit("PDF export requires reportlab. Installing...")
            import subprocess
            subprocess.run(["pip", "install", "reportlab"], capture_output=True)
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
            from reportlab.lib.enums import TA_LEFT, TA_CENTER

        doc = SimpleDocTemplate(
            file_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=20,
            textColor=colors.HexColor('#2196F3'),
            alignment=TA_CENTER
        )

        item_title_style = ParagraphStyle(
            'ItemTitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#1E1E1E'),
            fontName='Helvetica-Bold'
        )

        meta_style = ParagraphStyle(
            'Meta',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            spaceAfter=10
        )

        content_style = ParagraphStyle(
            'Content',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            spaceAfter=15,
            textColor=colors.HexColor('#333333')
        )

        story = []

        # Title
        story.append(Paragraph(f"{item_type.title()} Export", title_style))
        story.append(Spacer(1, 0.3*inch))

        # Items
        for i, item in enumerate(items, 1):
            # Item title
            story.append(Paragraph(f"{i}. {item.title}", item_title_style))

            # Metadata
            meta_parts = [f"Category: {item.category}"]
            if hasattr(item, 'platform') and item.platform:
                meta_parts.append(f"Platform: {item.platform}")
            if hasattr(item, 'created_at') and item.created_at:
                meta_parts.append(f"Date: {item.created_at.strftime('%Y-%m-%d %H:%M')}")
            story.append(Paragraph(" | ".join(meta_parts), meta_style))

            # Content - handle special characters
            content = item.content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            content = content.replace('\n', '<br/>')
            story.append(Paragraph(content, content_style))

            # Separator
            if i < len(items):
                story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E0E0E0')))

        doc.build(story)

    def get_prompt_box(self) -> PromptManagementBox:
        return self.prompt_box

    def clear_files(self):
        self.prompt_box.clear_files()
