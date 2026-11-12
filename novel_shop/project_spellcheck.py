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
"""Project-wide spellcheck: every misspelled word in the project.

One dialog for a proofread pass, instead of opening each file and
waiting for the red underlines. It scans every file in the folder
with the same rules as the editor's spellcheck (the dictionary, the
user's own words, and the entity terms are never flagged), counts
each misspelled word, and lists the files it appears in. Clicking a
word jumps to its first occurrence, so a typo can be fixed on the
spot. Modeless, so it stays open while you work through it.
"""

from collections import Counter

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from novel_shop.manuscript import collect_files, read_text_file
from novel_shop.spellcheck import misspelled_spans


def project_misspellings(
    folder: str, checker, known_words: set[str]
) -> list[tuple[str, int, list[tuple[str, int]]]]:
    """(word, count, [(file, first position)]) for the whole project.

    Sorted by count, most frequent first, then alphabetically. A word
    is listed once, with every file it appears in. Returns [] when
    the spell checker is not installed.
    """
    if checker is None:
        return []
    counts: Counter[str] = Counter()
    first_seen: dict[str, list[tuple[str, int]]] = {}
    for file in collect_files(folder):
        ok, text = read_text_file(file.path)
        if not ok:
            continue
        for start, end in misspelled_spans(text, checker, known_words):
            word = text[start:end].lower()
            counts[word] += 1
            seen = first_seen.setdefault(word, [])
            if not any(path == file.path for path, _pos in seen):
                seen.append((file.path, start))
    return [
        (word, counts[word], first_seen[word])
        for word in sorted(counts, key=lambda w: (-counts[w], w))
    ]


class ProjectSpellcheckDialog(QDialog):
    """The project's misspellings, one list, click to jump to one."""

    def __init__(
        self,
        folder: str,
        checker,
        known_words: set[str],
        before_refresh=None,
        jump_to=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Project Spellcheck")
        self.setModal(False)
        self._folder = folder
        self._checker = checker
        self._known_words = known_words
        self._before_refresh = before_refresh
        self._jump_to = jump_to
        self._words: list[tuple[str, int, list[tuple[str, int]]]] = []
        self._summary_label = QLabel("—")
        self._list = QListWidget()
        refresh_button = QPushButton("Refresh")
        close_button = QPushButton("Close")

        buttons = QHBoxLayout()
        buttons.addWidget(refresh_button)
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._list, 1)
        layout.addWidget(self._summary_label)
        layout.addLayout(buttons)
        self.resize(460, 420)

        refresh_button.clicked.connect(self.refresh)
        close_button.clicked.connect(self.close)
        self._list.itemDoubleClicked.connect(self._jump_to_selected)
        self.refresh()

    def set_folder(self, folder: str) -> None:
        """Point the dialog at a different folder and refresh."""
        self._folder = folder
        self.refresh()

    def refresh(self) -> None:
        """Save unsaved edits, then re-scan the folder."""
        if self._before_refresh is not None:
            self._before_refresh()
        self._words = project_misspellings(
            self._folder, self._checker, self._known_words
        )
        self._list.clear()
        for word, count, files in self._words:
            times = "time" if count == 1 else "times"
            names = ", ".join(
                _short_name(path) for path, _pos in files
            )
            self._list.addItem(f"{word} — {count} {times} in {names}")
        total = sum(count for _word, count, _files in self._words)
        distinct = len(self._words)
        if distinct == 0:
            self._summary_label.setText(
                "No misspellings found."
                if self._checker is not None
                else "Spellcheck is not installed."
            )
        else:
            self._summary_label.setText(
                f"{distinct} misspelled word"
                f"{'' if distinct == 1 else 's'}, {total} occurrence"
                f"{'' if total == 1 else 's'}"
            )

    def _jump_to_selected(self) -> None:
        """Open the selected word's first occurrence."""
        row = self._list.currentRow()
        if row < 0 or row >= len(self._words) or self._jump_to is None:
            return
        _word, _count, files = self._words[row]
        path, pos = files[0]
        self._jump_to(path, pos)


def _short_name(path: str) -> str:
    """The file's name, without its folder."""
    from pathlib import Path

    return Path(path).name
