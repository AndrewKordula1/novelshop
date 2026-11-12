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
"""Project search: find text across every file in the open folder.

One result per match (a line with the word twice gives two results),
in tree order. The match_index is the match's position among all the
matches in its file — the editor jumps to that occurrence, so a result
always lands on the right one even when a line matches more than once.
"""

import re
from dataclasses import dataclass

from novel_shop.manuscript import ManuscriptFile, collect_files
from novel_shop.storage import read_text_file, write_text_file


@dataclass(frozen=True)
class SearchResult:
    path: str
    title: str  # file stem, e.g. "Chapter 1"
    group: str  # tree section, e.g. "Chapters"
    line_no: int  # 1-based, for display
    line_text: str  # the file's line, as written
    match_start: int  # column offset of the match in the line
    match_end: int
    match_index: int  # which match in this file, 0-based, for jumping
    query: str
    case_sensitive: bool


def search_files(
    files: list[ManuscriptFile],
    query: str,
    case_sensitive: bool = False,
) -> tuple[list[SearchResult], list[str]]:
    """Search the files' text for query. Returns (results, skipped).

    A file that cannot be read is skipped and reported, not fatal.
    """
    if not query:
        return [], []
    needle = query if case_sensitive else query.lower()
    results: list[SearchResult] = []
    skipped: list[str] = []
    for file in files:
        ok, text = read_text_file(file.path)
        if not ok:
            skipped.append(file.path)
            continue
        match_index = 0
        for line_no, line in enumerate(text.split("\n"), start=1):
            haystack = line if case_sensitive else line.lower()
            start = 0
            while True:
                index = haystack.find(needle, start)
                if index < 0:
                    break
                results.append(
                    SearchResult(
                        path=file.path,
                        title=file.title,
                        group=file.group,
                        line_no=line_no,
                        line_text=line,
                        match_start=index,
                        match_end=index + len(query),
                        match_index=match_index,
                        query=query,
                        case_sensitive=case_sensitive,
                    )
                )
                match_index += 1
                start = index + len(query)
    return results, skipped


def search_folder(
    folder: str, query: str, case_sensitive: bool = False
) -> tuple[list[SearchResult], list[str]]:
    """Search every file the tree shows in the folder."""
    return search_files(collect_files(folder), query, case_sensitive)


def replace_in_files(
    files: list[ManuscriptFile],
    query: str,
    replacement: str,
    case_sensitive: bool = False,
) -> tuple[int, int, list[str]]:
    """Replace query with replacement in every file that contains it.

    Returns (replacements, files changed, skipped). A file is only
    written when it actually contains a match, and the replacement
    is literal text, never a pattern. The caller saves any open tabs
    first, so the files on disk are the current text.
    """
    if not query:
        return 0, 0, []
    pattern = re.compile(
        re.escape(query),
        0 if case_sensitive else re.IGNORECASE,
    )
    replaced = 0
    changed = 0
    skipped: list[str] = []
    for file in files:
        ok, text = read_text_file(file.path)
        if not ok:
            skipped.append(file.path)
            continue
        new_text, count = pattern.subn(lambda _match: replacement, text)
        if count == 0:
            continue
        ok, _message = write_text_file(file.path, new_text)
        if not ok:
            skipped.append(file.path)
            continue
        replaced += count
        changed += 1
    return replaced, changed, skipped
