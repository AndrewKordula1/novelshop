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
"""Overused words: filler and intensifier words worth a second look.

A small curated list of the words writers are told to cut — "very",
"just", "really", "suddenly" — matched whole-word and
case-insensitively, so "Very" at the start of a sentence counts too.
The highlighter paints them; this module only knows the words and
where they are. Deliberately a short list of adverbs and
intensifiers, not common verbs like "get" — those would light up
every paragraph.
"""

import re

WEASEL_WORDS = (
    "actually",
    "amazingly",
    "basically",
    "certainly",
    "clearly",
    "definitely",
    "extremely",
    "fortunately",
    "honestly",
    "incredibly",
    "indeed",
    "just",
    "literally",
    "merely",
    "obviously",
    "perhaps",
    "probably",
    "quite",
    "rather",
    "really",
    "simply",
    "somehow",
    "somewhat",
    "suddenly",
    "surprisingly",
    "truly",
    "unfortunately",
    "very",
)

_PATTERN = re.compile(
    r"\b(?:" + "|".join(WEASEL_WORDS) + r")\b", re.IGNORECASE
)


def weasel_spans(text: str) -> list[tuple[int, int]]:
    """(start, end) spans of overused words in text."""
    return [(m.start(), m.end()) for m in _PATTERN.finditer(text)]
