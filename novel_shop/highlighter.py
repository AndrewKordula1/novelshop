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
"""Manuscript highlighter: colors mentions of defined things, and
underlines misspelled words.

Like a code editor's syntax highlighting: when a word in the text
matches a term from the open folder — a character's name, a spell, a
place — it is drawn in that category's color. Misspelled words get a
red wavy underline. The colors and underlines are display only: they
are never written into the file.

Both jobs live in this one highlighter on purpose: Qt only keeps one
highlighter's formats per block, so two highlighters on the same
document clobber each other — the second one's formats replace the
first's. The spell logic itself (the dictionary, which words are
misspelled) lives in spellcheck.py.
"""

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

from novel_shop.spellcheck import misspelled_spans
from novel_shop.weasel_words import WEASEL_WORDS


class ManuscriptHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._colors: dict[str, QColor] = {}
        self._pattern: QRegularExpression | None = None
        self._spell_checker = None
        self._spell_known_words: set[str] = set()
        self._spell_enabled = True
        self._weasel_enabled = True
        escaped = "|".join(
            QRegularExpression.escape(word) for word in WEASEL_WORDS
        )
        self._weasel_pattern = QRegularExpression(
            f"\\b(?:{escaped})\\b",
            QRegularExpression.PatternOption.CaseInsensitiveOption,
        )

    def set_rules(self, rules: list[tuple[str, str]]) -> None:
        """Set the (term, color) rules and re-highlight the document.

        Terms match whole words, case-sensitively, longest first, so
        "Aldric" wins over "Al" and "Aldricson" does not match at all.
        """
        terms = sorted((term for term, _ in rules), key=len, reverse=True)
        self._colors = {term: QColor(color) for term, color in rules}
        if not terms:
            self._pattern = None
        else:
            escaped = "|".join(
                QRegularExpression.escape(term) for term in terms
            )
            self._pattern = QRegularExpression(f"\\b(?:{escaped})\\b")
        self.rehighlight()

    def set_spell_checker(self, checker) -> None:
        """The dictionary for spell underlines (None: no underlines)."""
        self._spell_checker = checker
        self.rehighlight()

    def set_spell_known_words(self, words) -> None:
        """Words never underlined: entity terms and the user's dictionary."""
        self._spell_known_words = {word.lower() for word in words}
        self.rehighlight()

    def set_spell_enabled(self, enabled: bool) -> None:
        self._spell_enabled = enabled
        self.rehighlight()

    def set_weasel_enabled(self, enabled: bool) -> None:
        """Turn the overused-word underlines on or off."""
        self._weasel_enabled = enabled
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        # A heading: a line starting with # or ##. The markers get a
        # muted color so they fade, and the heading text is larger and
        # bold. The sizes are relative to the document's font, so they
        # follow the writing font the user picked.
        heading_level = 0
        marker_len = 0
        if text.startswith("## "):
            heading_level, marker_len = 2, 3
        elif text.startswith("# "):
            heading_level, marker_len = 1, 2
        if heading_level:
            base = self.document().defaultFont()
            scale = 1.6 if heading_level == 1 else 1.3
            font = QFont(base)
            if base.pixelSize() > 0:
                font.setPixelSize(round(base.pixelSize() * scale))
            else:
                font.setPointSizeF(base.pointSizeF() * scale)
            heading = QTextCharFormat()
            heading.setFont(font)
            heading.setFontWeight(QFont.Weight.Bold)
            self.setFormat(marker_len, len(text) - marker_len, heading)
            marker = QTextCharFormat()
            marker.setForeground(QColor("#6e6e73"))
            self.setFormat(0, marker_len, marker)
        # A block quote: a line starting with > . The marker fades and
        # the quoted text is italic, like a printed block quotation.
        if text.startswith("> "):
            quote = QTextCharFormat()
            quote.setFontItalic(True)
            self.setFormat(2, len(text) - 2, quote)
            marker = QTextCharFormat()
            marker.setForeground(QColor("#6e6e73"))
            self.setFormat(0, 2, marker)
        if self._pattern is not None:
            iterator = self._pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                color = self._colors.get(match.captured())
                if color is None:
                    continue
                fmt = QTextCharFormat()
                fmt.setForeground(color)
                self.setFormat(
                    match.capturedStart(), match.capturedLength(), fmt
                )
        if self._spell_enabled and self._spell_checker is not None:
            underline = QTextCharFormat()
            underline.setUnderlineStyle(
                QTextCharFormat.UnderlineStyle.SpellCheckUnderline
            )
            underline.setUnderlineColor(Qt.GlobalColor.red)
            for start, end in misspelled_spans(
                text, self._spell_checker, self._spell_known_words
            ):
                self.setFormat(start, end - start, underline)
        if self._weasel_enabled:
            # A dotted orange underline, distinct from the red wavy
            # spellcheck underline and from the entity text colors.
            weasel = QTextCharFormat()
            weasel.setUnderlineStyle(
                QTextCharFormat.UnderlineStyle.DotLine
            )
            weasel.setUnderlineColor(QColor("#c47a00"))
            iterator = self._weasel_pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(
                    match.capturedStart(), match.capturedLength(), weasel
                )
