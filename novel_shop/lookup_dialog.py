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
"""The Define dialog: definitions, synonyms and antonyms for a word.

Read-only. The thesaurus action — clicking a synonym to replace the
word — lives in the right-click menu's Synonyms submenu, where the
word is right under the cursor. The Dictionary window reuses the
same results, with synonyms as links (click one to look it up).
"""

import html
from urllib.parse import quote

from PySide6.QtWidgets import QDialog, QTextBrowser, QVBoxLayout

_MAX_SENSES_SHOWN = 10


def senses_to_html(
    word: str, senses: list[dict], links: bool = False
) -> str:
    """The lookup results as HTML for the dialog.

    With links, synonyms are anchors (the Dictionary window uses
    them to look a synonym up); without, they are plain text.
    """
    if not senses:
        return f"<p>No definition found for <b>{html.escape(word)}</b>.</p>"
    parts = [f"<h2>{html.escape(word)}</h2>"]
    for sense in senses[:_MAX_SENSES_SHOWN]:
        parts.append(
            "<p><b>{pos}</b> — {definition}</p>".format(
                pos=html.escape(sense["pos"]),
                definition=html.escape(sense["definition"]),
            )
        )
        if sense["example"]:
            parts.append(f"<p><i>{html.escape(sense['example'])}</i></p>")
        if sense["synonyms"]:
            if links:
                rendered = ", ".join(
                    '<a href="{href}">{text}</a>'.format(
                        href=quote(synonym),
                        text=html.escape(synonym),
                    )
                    for synonym in sense["synonyms"]
                )
            else:
                rendered = ", ".join(
                    html.escape(s) for s in sense["synonyms"]
                )
            parts.append(f"<p>Synonyms: {rendered}</p>")
        if sense["antonyms"]:
            parts.append(
                "<p>Antonyms: {}</p>".format(
                    ", ".join(html.escape(a) for a in sense["antonyms"])
                )
            )
    if len(senses) > _MAX_SENSES_SHOWN:
        parts.append(
            f"<p>…and {len(senses) - _MAX_SENSES_SHOWN} more senses.</p>"
        )
    return "".join(parts)


class LookupDialog(QDialog):
    """Definitions, synonyms and antonyms for one word."""

    def __init__(self, word: str, senses: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Define '{word}'")
        self.resize(520, 420)
        browser = QTextBrowser(self)
        browser.setHtml(senses_to_html(word, senses))
        layout = QVBoxLayout(self)
        layout.addWidget(browser)
