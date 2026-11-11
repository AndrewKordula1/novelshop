# Copyright (C) 2026 Andrew Kordula
#
# This file is part of Novelshop.
#
# Novelshop is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# Novelshop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with Novelshop; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#
"""Find in Project: search every file, click a result to jump to it.

A modeless dialog, so it stays open while the editor is used — click
a result, the file opens with the match selected, and the dialog is
still there for the next one. Close it with the window's close button.
Replace All writes the replacement into every matching file (after
asking first), and the main window reloads any open tabs.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from novel_shop.manuscript import ManuscriptFile
from novel_shop.project_search import (
    SearchResult,
    replace_in_files,
    search_files,
)

_EXCERPT_CHARS = 100


class ProjectSearchDialog(QDialog):
    result_opened = Signal(object)  # SearchResult
    files_changed = Signal()  # after a Replace All, so tabs reload

    def __init__(self, files: list[ManuscriptFile], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find in Project")
        self.setModal(False)
        self._files = list(files)
        self._results: list[SearchResult] = []

        self._query_field = QLineEdit()
        self._query_field.setPlaceholderText("Search all files")
        self._case_check = QCheckBox("Aa")
        self._case_check.setToolTip("Match case")
        search_button = QPushButton("Search")
        self._replace_field = QLineEdit()
        self._replace_field.setPlaceholderText("Replace with")
        replace_button = QPushButton("Replace All")
        self._results_list = QListWidget()
        self._status_label = QLabel("Type a word and press Enter")

        search_row = QHBoxLayout()
        search_row.addWidget(self._query_field, 1)
        search_row.addWidget(self._case_check)
        search_row.addWidget(search_button)

        replace_row = QHBoxLayout()
        replace_row.addWidget(self._replace_field, 1)
        replace_row.addWidget(replace_button)

        layout = QVBoxLayout(self)
        layout.addLayout(search_row)
        layout.addLayout(replace_row)
        layout.addWidget(self._results_list, 1)
        layout.addWidget(self._status_label)

        self._query_field.returnPressed.connect(self.run_search)
        search_button.clicked.connect(self.run_search)
        replace_button.clicked.connect(self._replace_all)
        self._results_list.itemActivated.connect(self._open_current)
        self._results_list.itemDoubleClicked.connect(self._open_current)
        self.resize(560, 420)

    # -- wiring ----------------------------------------------------------

    def set_files(self, files: list[ManuscriptFile]) -> None:
        self._files = list(files)

    def set_query(self, text: str) -> None:
        self._query_field.setText(text)
        self._query_field.selectAll()

    def set_case_sensitive(self, case_sensitive: bool) -> None:
        self._case_check.setChecked(case_sensitive)

    def run_search(self) -> None:
        """Search the files for the current query and list the matches."""
        query = self._query_field.text()
        if not query:
            self._results = []
            self._results_list.clear()
            self._status_label.setText("Type a word and press Enter")
            return
        results, skipped = search_files(
            self._files, query, self._case_check.isChecked()
        )
        self._results = results
        self._results_list.clear()
        for result in results:
            item = QListWidgetItem(
                f"{result.title} · line {result.line_no}\n"
                f"    {self._excerpt(result)}"
            )
            item.setData(Qt.ItemDataRole.UserRole, result)
            self._results_list.addItem(item)
        file_count = len({result.path for result in results})
        message = (
            f"{len(results)} match{'es' if len(results) != 1 else ''} "
            f"in {file_count} file{'s' if file_count != 1 else ''}"
            if results
            else "No matches"
        )
        if skipped:
            message += f" — skipped {len(skipped)} unreadable file(s)"
        self._status_label.setText(message)

    def _replace_all(self) -> None:
        """Replace the query with the replacement in every file.

        Counts first and asks, because this writes to every file
        that matches and cannot be undone in the editor. The files
        are re-searched after, so the list shows what is left.
        """
        query = self._query_field.text()
        if not query:
            self._status_label.setText("Type a word to replace first")
            return
        results, _skipped = search_files(
            self._files, query, self._case_check.isChecked()
        )
        if not results:
            self._status_label.setText("No matches to replace")
            return
        file_count = len({result.path for result in results})
        answer = QMessageBox.question(
            self,
            "Replace in Project",
            f"Replace {len(results)} match"
            f"{'es' if len(results) != 1 else ''} in "
            f"{file_count} file{'s' if file_count != 1 else ''} "
            f"with '{self._replace_field.text()}'?\n"
            "This writes to every matching file and can't be undone.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        replaced, changed, skipped = replace_in_files(
            self._files,
            query,
            self._replace_field.text(),
            self._case_check.isChecked(),
        )
        message = (
            f"Replaced {replaced} match{'es' if replaced != 1 else ''} "
            f"in {changed} file{'s' if changed != 1 else ''}"
        )
        if skipped:
            message += f" — skipped {len(skipped)} unreadable file(s)"
        self._status_label.setText(message)
        self.files_changed.emit()
        self.run_search()

    # -- internals ---------------------------------------------------------

    def _excerpt(self, result: SearchResult) -> str:
        """The matching line, trimmed to a window around the match."""
        line = result.line_text.strip()
        if len(line) <= _EXCERPT_CHARS:
            return line
        start = max(0, result.match_start - 40)
        end = start + _EXCERPT_CHARS
        excerpt = line[start:end]
        if start > 0:
            excerpt = "…" + excerpt
        if end < len(line):
            excerpt += "…"
        return excerpt

    def _open_current(self, item: QListWidgetItem) -> None:
        result = item.data(Qt.ItemDataRole.UserRole)
        if result is not None:
            self.result_opened.emit(result)
