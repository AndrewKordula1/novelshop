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
"""Word frequency: which words the book leans on most.

Counts every word in the story files (parts, chapters, scenes — the
files that make up the book, like the Project Word Count), and lists
the most frequent ones. Common function words (the, and, of) are
left out, so the list surfaces content words: names, verbs, the
words a writer reaches for without noticing. A filter box narrows
the list to one word. Modeless, so it stays open while you write.
"""

import re
from collections import Counter

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from novel_shop.manuscript import collect_files, read_text_file

_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
# Common function words, left out so the list shows content words.
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am",
    "an", "and", "any", "are", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by",
    "could", "did", "do", "does", "doing", "down", "during", "each",
    "few", "for", "from", "further", "had", "has", "have", "having",
    "he", "her", "here", "hers", "herself", "him", "himself", "his",
    "how", "i", "if", "in", "into", "is", "it", "its", "itself",
    "just", "me", "more", "most", "my", "myself", "no", "nor", "not",
    "now", "of", "off", "on", "once", "only", "or", "other", "our",
    "ours", "ourselves", "out", "over", "own", "same", "she", "should",
    "so", "some", "such", "than", "that", "the", "their", "theirs",
    "them", "themselves", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "very",
    "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "will", "with", "would", "you", "your",
    "yours", "yourself", "yourselves",
}
TOP_N = 50


def word_frequencies(folder: str) -> tuple[list[tuple[str, int]], int]:
    """(top words with counts, total words) for the story files.

    Counts are case-insensitive ("Allen" and "allen" are one word).
    Stopwords are excluded from the list but counted in the total.
    """
    counts: Counter[str] = Counter()
    total = 0
    for file in collect_files(folder):
        if not file.include_by_default:
            continue
        ok, text = read_text_file(file.path)
        if not ok:
            continue
        for match in _WORD_RE.finditer(text):
            word = match.group(0).lower()
            total += 1
            if word not in STOPWORDS:
                counts[word] += 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_N]
    return top, total


class WordFrequencyDialog(QDialog):
    """The book's most-used words, most frequent first."""

    def __init__(self, folder: str, before_refresh=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Word Frequency")
        self.setModal(False)
        self._folder = folder
        self._before_refresh = before_refresh
        self._top: list[tuple[str, int]] = []
        self._total = 0
        self._summary_label = QLabel("—")
        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filter words...")
        self._list = QListWidget()
        refresh_button = QPushButton("Refresh")
        close_button = QPushButton("Close")

        buttons = QHBoxLayout()
        buttons.addWidget(refresh_button)
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._filter)
        layout.addWidget(self._list, 1)
        layout.addWidget(self._summary_label)
        layout.addLayout(buttons)
        self.resize(380, 460)

        refresh_button.clicked.connect(self.refresh)
        close_button.clicked.connect(self.close)
        self._filter.textChanged.connect(self._apply_filter)
        self.refresh()

    def set_folder(self, folder: str) -> None:
        """Point the dialog at a different folder and refresh."""
        self._folder = folder
        self.refresh()

    def refresh(self) -> None:
        """Save unsaved edits, then re-read the files and recount."""
        if self._before_refresh is not None:
            self._before_refresh()
        self._top, self._total = word_frequencies(self._folder)
        self._apply_filter()

    def _apply_filter(self) -> None:
        """Show the top words, narrowed by the filter box."""
        needle = self._filter.text().strip().lower()
        self._list.clear()
        for word, count in self._top:
            if needle and needle not in word:
                continue
            percent = (count / self._total * 100) if self._total else 0
            self._list.addItem(
                f"{word} — {count:,} ({percent:.1f}%)"
            )
        shown = self._list.count()
        self._summary_label.setText(
            f"Top {len(self._top)} words of {self._total:,} total"
            + (f" — {shown} shown" if needle else "")
        )
