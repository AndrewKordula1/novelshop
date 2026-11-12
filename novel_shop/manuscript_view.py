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
"""Manuscript view: read the whole book as one continuous document.

The open folder's story files (parts, chapters, scenes) in tree
order, each under its name as a heading — the same order and the
same files the export uses. It is read-only and modeless, so it
stays open while you write; Refresh re-reads the files if they
changed. For proofreading the book end to end, without exporting.
"""

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
)

from novel_shop.editor import Editor
from novel_shop.manuscript import collect_files, read_blocks


def assemble_manuscript_text(folder: str) -> str:
    """The story files as one Markdown document, in tree order."""
    files = [
        file for file in collect_files(folder) if file.include_by_default
    ]
    blocks, _skipped = read_blocks(files)
    parts: list[str] = []
    for block in blocks:
        heading = "#" * block.level + " " + block.title
        parts.append(heading)
        parts.append("")
        parts.append(block.text)
        parts.append("")
    return "\n".join(parts).strip() + "\n"


class ManuscriptView(QDialog):
    """The manuscript, read-only, in a window that stays open."""

    def __init__(self, folder: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manuscript")
        self.setModal(False)
        self._folder = folder
        self._editor = Editor()
        self._editor.setReadOnly(True)
        refresh_button = QPushButton("Refresh")
        close_button = QPushButton("Close")

        buttons = QHBoxLayout()
        buttons.addWidget(refresh_button)
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._editor, 1)
        layout.addLayout(buttons)
        self.resize(720, 560)

        refresh_button.clicked.connect(self.refresh)
        close_button.clicked.connect(self.close)
        self.refresh()

    def set_folder(self, folder: str) -> None:
        """Point the view at a different folder and refresh."""
        self._folder = folder
        self.refresh()

    def refresh(self) -> None:
        """Re-read the files and show the manuscript again."""
        text = assemble_manuscript_text(self._folder)
        self._editor.load_text(text)
        self._editor.mark_saved()
