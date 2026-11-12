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
"""Spellcheck: which words are misspelled, and what to suggest.

Uses pyspellchecker — pure Python, no C library, no dictionary files
to ship, and it loads in a fraction of a second. Words that are
defined entity terms (Aldric, Fireball) or in the user's own
dictionary are never flagged. The underlining itself lives in
highlighter.py: Qt only keeps one highlighter's formats per block, so
the spell underlines and the entity colors are applied by the same
highlighter. The checker only runs when pyspellchecker is installed;
without it the app starts as normal and spellcheck stays off.
"""

import re

_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_TAG_RE = re.compile(r"</?u>")


def load_spell_checker():
    """A SpellChecker, or None when pyspellchecker is not installed
    or its dictionary cannot be loaded."""
    try:
        from spellchecker import SpellChecker
    except ImportError:
        return None
    try:
        return SpellChecker()
    except (ValueError, OSError):
        # The dictionary data file is missing (a frozen build that
        # did not bundle it raises ValueError: the language does
        # not exist). Spellcheck stays off instead of crashing
        # the app at startup.
        return None


def is_misspelled(word: str, checker, known_words: set[str]) -> bool:
    """True if word is a spelling error: not known, not an acronym."""
    if not word or checker is None:
        return False
    if len(word) == 1:
        return word not in ("a", "A", "I")
    if word.isupper():
        return False  # acronyms (NASA) are not spelling errors
    lowered = word.lower()
    if lowered in known_words:
        return False
    return lowered not in checker


def misspelled_spans(
    text: str, checker, known_words: set[str]
) -> list[tuple[int, int]]:
    """(start, end) spans of the misspelled words in one line of text."""
    if checker is None:
        return []
    # Blank out <u> tags without moving the text: their "u" would read
    # as a word. The ** and * markers are not letters, so they are
    # already word boundaries.
    clean = _TAG_RE.sub(lambda match: " " * len(match.group(0)), text)
    candidates: list[tuple[str, int, int]] = []
    for match in _WORD_RE.finditer(clean):
        word = match.group(0)
        if len(word) == 1 and word not in ("a", "A", "I"):
            continue
        if word.isupper():
            continue
        if word.lower() in known_words:
            continue
        candidates.append((word.lower(), match.start(), match.end()))
    if not candidates:
        return []
    bad = checker.unknown([word for word, _start, _end in candidates])
    return [
        (start, end) for word, start, end in candidates if word in bad
    ]


def suggestions_for(word: str, checker, limit: int = 5) -> list[str]:
    """Likely corrections, best first. Empty when nothing is installed."""
    if checker is None or not word:
        return []
    best = checker.correction(word.lower())
    rest = sorted(checker.candidates(word.lower()))
    ordered = [best] if best else []
    ordered += [candidate for candidate in rest if candidate != best]
    return ordered[:limit]
