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
"""Typography: smart quotes and dashes.

Two entry points: as-you-type (the editor calls smart_double_quote
and smart_single_quote for each keystroke) and fix_typography() for
existing text (the whole document or the selection).

Quotes: a double quote is an opening quote when it follows the
start of the text, whitespace, or opening punctuation; otherwise
it closes. A single quote between two letters is an apostrophe.
Dashes: "--" (or "---") becomes an em dash. A hyphen inside a
word ("well-known") is left alone.
"""

_OPENERS = set(" \t\n\u2028([{—–«“‘")


def _is_opening(text_before: str) -> bool:
    """Is a quote typed here an opening quote?"""
    if not text_before:
        return True
    return text_before[-1] in _OPENERS


def smart_double_quote(text_before: str) -> str:
    """The curly double quote to insert after text_before."""
    return "“" if _is_opening(text_before) else "”"


def smart_single_quote(text_before: str, text_after: str = "") -> str:
    """The curly single quote to insert here.

    Between two letters it is an apostrophe (don't); after
    whitespace or opening punctuation it opens; otherwise it closes.
    """
    if (
        text_before
        and text_before[-1].isalpha()
        and text_after
        and text_after[0].isalpha()
    ):
        return "’"
    if text_before and text_before[-1].isalpha():
        return "’"
    return "‘" if _is_opening(text_before) else "’"


def typography_edits(text: str) -> list[tuple[int, int, str]]:
    """(start, end, replacement) edits to fix quotes and dashes.

    Scans the text once, left to right. Each edit is a small,
    local replacement, so the editor can apply them one at a time
    (from the end back) without disturbing the formatting around
    them. An empty list means the text is already clean.
    """
    edits: list[tuple[int, int, str]] = []
    i = 0
    while i < len(text):
        char = text[i]
        if char == '"':
            before = text[:i]
            edits.append((i, i + 1, smart_double_quote(before)))
            i += 1
        elif char == "'":
            before = text[:i]
            after = text[i + 1:]
            edits.append((i, i + 1, smart_single_quote(before, after)))
            i += 1
        elif char == "-":
            # A run of two or more hyphens becomes one em dash.
            # A single hyphen (well-known) is left alone.
            run = 1
            while i + run < len(text) and text[i + run] == "-":
                run += 1
            if run >= 2:
                edits.append((i, i + run, "—"))
                i += run
            else:
                i += 1
        else:
            i += 1
    return edits


def fix_typography(text: str) -> str:
    """The text with straight quotes and double hyphens fixed."""
    edits = typography_edits(text)
    if not edits:
        return text
    parts: list[str] = []
    pos = 0
    for start, end, replacement in edits:
        parts.append(text[pos:start])
        parts.append(replacement)
        pos = end
    parts.append(text[pos:])
    return "".join(parts)
