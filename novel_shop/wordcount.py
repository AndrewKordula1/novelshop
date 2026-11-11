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
"""Word count: pure functions over plain text, no GUI here.

One function in, counts out. The main window calls count_words() and
displays the result in the status bar.
"""

from dataclasses import dataclass


@dataclass
class WordCount:
    words: int
    characters: int
    lines: int

    def format(self) -> str:
        """'2 words · 11 characters · 1 line', with correct plurals."""
        return (
            f"{_plural(self.words, 'word')} · "
            f"{_plural(self.characters, 'character')} · "
            f"{_plural(self.lines, 'line')}"
        )


def _plural(n: int, singular: str) -> str:
    return f"{n} {singular}" if n == 1 else f"{n} {singular}s"


def count_words(text: str) -> WordCount:
    """Count words, characters, and lines in plain text."""
    if not text:
        return WordCount(words=0, characters=0, lines=0)
    words = len(text.split())
    characters = len(text)
    lines = text.count("\n") + 1
    return WordCount(words=words, characters=characters, lines=lines)
