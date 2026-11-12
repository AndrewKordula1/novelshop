# Copyright (C) 2026 Andrew Kordula
#
# This file is part of Novelshop.
#
# Novelshop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Novelshop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Novelshop; if not, see <https://www.gnu.org/licenses/>.
#
"""Project word count: the whole book's words, file by file.

The story files (parts, chapters, scenes — the same files the
export and the manuscript view use) in tree order, each with its
word count, and a total at the bottom. Just a total, no target.
Modeless, so it stays open while you write; Refresh re-reads the
files. Unsaved edits are saved first, so the counts are current.
"""

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from novel_shop.manuscript import collect_files
from novel_shop.storage import read_text_file
from novel_shop.wordcount import count_words


def project_word_counts(folder: str) -> tuple[list[tuple[str, int]], int]:
    """(per-file (title, words), total words) for the story files."""
    rows: list[tuple[str, int]] = []
    total = 0
    for file in collect_files(folder):
        if not file.include_by_default:
            continue
        ok, text = read_text_file(file.path)
        if not ok:
            continue
        words = count_words(text).words
        rows.append((file.title, words))
        total += words
    return rows, total


class ProjectStatsDialog(QDialog):
    """The book's word count, file by file, in a window that stays open."""

    def __init__(self, folder: str, before_refresh=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project Word Count")
        self.setModal(False)
        self._folder = folder
        self._before_refresh = before_refresh
        self._total_label = QLabel("—")
        self._list = QListWidget()
        refresh_button = QPushButton("Refresh")
        close_button = QPushButton("Close")

        buttons = QHBoxLayout()
        buttons.addWidget(refresh_button)
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._list, 1)
        layout.addWidget(self._total_label)
        layout.addLayout(buttons)
        self.resize(380, 420)

        refresh_button.clicked.connect(self.refresh)
        close_button.clicked.connect(self.close)
        self.refresh()

    def set_folder(self, folder: str) -> None:
        """Point the dialog at a different folder and refresh."""
        self._folder = folder
        self.refresh()

    def refresh(self) -> None:
        """Save unsaved edits, then re-read the files and recount."""
        if self._before_refresh is not None:
            self._before_refresh()
        rows, total = project_word_counts(self._folder)
        self._list.clear()
        for title, words in rows:
            self._list.addItem(f"{title} — {words:,} words")
        self._total_label.setText(f"Total: {total:,} words")
