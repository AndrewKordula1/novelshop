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
"""The Dictionary window: a general lookup, not tied to the editor.

Opened by the Dictionary button in the toolbar. Type any word and
search it; the results are the same definitions, synonyms and
antonyms as the right-click Define dialog. Synonyms are links —
clicking one looks it up. Tick "Reverse search" to describe a word
instead ("a fear of heights") and get the words that match. It
never reads from or writes to the editor: it is a standalone
reference window, and it stays open while you write.
"""

import html
from urllib.parse import quote, unquote

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from novel_shop import lexicon, reverse
from novel_shop.lookup_dialog import senses_to_html

_WORDNET_MISSING = (
    "<p>WordNet data is not installed — pip install wn, "
    "then python -m wn download ewn:2020.</p>"
)


def reverse_to_html(results: list[dict]) -> str:
    """Render reverse-search candidates as a list of links.

    Each candidate is a word with its part of speech and definition;
    clicking the word looks it up. Empty means nothing matched.
    """
    if not results:
        return (
            "<p>No words found. Try fewer or different words — "
            "the search matches the words in a definition.</p>"
        )
    parts = ["<p>Words that match:</p>"]
    for result in results:
        word = html.escape(result["word"])
        pos = html.escape(result["pos"])
        definition = html.escape(result["definition"])
        parts.append(
            f'<p><b><a href="{quote(result["word"])}">{word}</a></b> '
            f"({pos}) — {definition}</p>"
        )
    return "".join(parts)


class LookupWindow(QDialog):
    """A general dictionary search. Modeless; stays open."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dictionary")
        self.resize(520, 420)
        self._search_field = QLineEdit(self)
        self._search_field.setPlaceholderText("Look up a word…")
        self._search_field.returnPressed.connect(self._search)
        self._reverse_box = QCheckBox("Reverse search", self)
        self._reverse_box.setToolTip(
            "Describe the word instead of typing it"
        )
        self._reverse_box.toggled.connect(self._set_reverse)
        search_button = QPushButton("Search", self)
        search_button.clicked.connect(self._search)
        search_row = QHBoxLayout()
        search_row.addWidget(self._search_field, 1)
        search_row.addWidget(self._reverse_box)
        search_row.addWidget(search_button)
        self._browser = QTextBrowser(self)
        self._browser.setOpenExternalLinks(False)
        self._browser.anchorClicked.connect(self._follow_link)
        layout = QVBoxLayout(self)
        layout.addLayout(search_row)
        layout.addWidget(self._browser, 1)

    def focus_search(self) -> None:
        """Put the cursor in the search field, ready to type."""
        self._search_field.setFocus()
        self._search_field.selectAll()

    def _set_reverse(self, checked: bool) -> None:
        """Switch between looking a word up and describing one."""
        if checked:
            self._search_field.setPlaceholderText(
                "Describe the word… (e.g. a fear of heights)"
            )
            self.setWindowTitle("Dictionary — Reverse")
        else:
            self._search_field.setPlaceholderText("Look up a word…")
            self.setWindowTitle("Dictionary")

    def _search(self) -> None:
        text = self._search_field.text().strip()
        if not text:
            return
        if self._reverse_box.isChecked():
            self._search_reverse(text)
        else:
            self.lookup(text)

    def lookup(self, word: str) -> None:
        """Look a word up and show the results."""
        self._reverse_box.setChecked(False)
        self._search_field.setText(word)
        self._browser.setHtml(
            senses_to_html(word, lexicon.lookup(word), links=True)
        )
        self.setWindowTitle(f"Dictionary — {word}")

    def _search_reverse(self, description: str) -> None:
        """Find the words that match a description."""
        if not lexicon.is_available():
            self._browser.setHtml(_WORDNET_MISSING)
            return
        if not reverse.is_ready():
            self._browser.setHtml("<p>Building the reverse index…</p>")
            QApplication.processEvents()
        results = reverse.reverse_lookup(description)
        self._browser.setHtml(reverse_to_html(results))
        self.setWindowTitle(f"Dictionary — Reverse: {description}")

    def _follow_link(self, url) -> None:
        """A link (a synonym, or a reverse-search candidate):
        look that word up."""
        self.lookup(unquote(url.toString()))
