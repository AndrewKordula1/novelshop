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
"""Manuscript: assemble the story files into an exportable manuscript.

The manuscript is the open folder's files in tree order — sections in
their defined order, files by name inside each section — so the chapter
order comes from the file names ("Chapter 1", "Chapter 2", ...). Each
file becomes one block: its name is the heading, its text the content.
Parts and chapters are level 1; scenes and anything else are level 2.
"""

from dataclasses import dataclass
from pathlib import Path

from novel_shop.file_types import (
    group_for_extension,
    group_for_unknown_extension,
    groups_in_order,
)
from novel_shop.storage import read_text_file

# Extensions that are the story itself, included in an export unless
# the user unticks them. Anything else is reference material.
STORY_EXTENSIONS = ("part", "chapter", "scene")

# Groups whose files define highlight terms: every group except the
# story groups and Documents. A character file named Aldric makes
# "Aldric" a term; a spell file named Fireball makes "Fireball" one.
NON_TERM_GROUPS = {"Parts", "Chapters", "Scenes", "Drafts", "Documents"}


@dataclass(frozen=True)
class ManuscriptFile:
    path: str
    title: str  # file stem, e.g. "Chapter 1"
    group: str  # tree section, e.g. "Chapters"
    level: int  # 1 = part/chapter, 2 = everything else
    include_by_default: bool


@dataclass(frozen=True)
class Block:
    level: int
    title: str
    text: str


def _level_for(extension: str) -> int:
    return 1 if extension in ("part", "chapter") else 2


def collect_files(folder: str) -> list[ManuscriptFile]:
    """The folder's files in tree order, with their export defaults.

    Same rules as the tree: top-level files only, hidden files and
    files with no extension skipped. A folder that no longer exists
    (deleted out from under the app) reads as empty.
    """
    grouped: dict[str, list[Path]] = {}
    if not Path(folder).is_dir():
        return []
    for child in sorted(Path(folder).iterdir(), key=lambda p: p.name.lower()):
        if not child.is_file() or child.name.startswith("."):
            continue
        if not child.suffix:
            continue
        group = group_for_extension(child.suffix)
        if group is None:
            group = group_for_unknown_extension(child.suffix)
        grouped.setdefault(group, []).append(child)
    known_order = groups_in_order()
    order = known_order + sorted(
        group for group in grouped if group not in known_order
    )
    files: list[ManuscriptFile] = []
    for group in order:
        for child in grouped.get(group, []):
            extension = child.suffix.lower().lstrip(".")
            files.append(
                ManuscriptFile(
                    path=str(child),
                    title=child.stem,
                    group=group,
                    level=_level_for(extension),
                    include_by_default=extension in STORY_EXTENSIONS,
                )
            )
    return files


def read_blocks(
    files: list[ManuscriptFile],
) -> tuple[list[Block], list[str]]:
    """Read the selected files into blocks. Returns (blocks, skipped).

    A file that cannot be read is skipped and reported, not fatal.
    """
    blocks: list[Block] = []
    skipped: list[str] = []
    for file in files:
        ok, text = read_text_file(file.path)
        if not ok:
            skipped.append(file.path)
            continue
        blocks.append(Block(file.level, file.title, text))
    return blocks, skipped


def term_groups() -> list[str]:
    """Groups whose files define highlight terms, in tree order."""
    return [group for group in groups_in_order() if group not in NON_TERM_GROUPS]


def collect_terms(
    files: list[ManuscriptFile],
    colors: dict[str, str],
    enabled: dict[str, bool],
) -> list[tuple[str, str]]:
    """(term, color) highlight rules from the reference files.

    The term is the file's name: Aldric.character makes "Aldric" a
    term, in the Characters color. Story files and Documents define
    no terms; a category turned off in the preferences is skipped.
    """
    return [
        (file.title, colors.get(file.group, "#757575"))
        for file in files
        if file.group not in NON_TERM_GROUPS
        and enabled.get(file.group, True)
    ]


def parse_inline(text: str) -> list[tuple[str, bool, bool, bool, bool, bool]]:
    """Split a line into (text, bold, italic, underline, strike, highlight) runs.

    ***both***, **bold**, *italic*, ~~struck~~, ==highlighted==, and
    <u>underlined</u> are recognized; markers nest (bold around an
    underline, and so on), and anything else, including an unmatched
    *, stays literal text. A line that is just *** is a scene break,
    literal text — without this, the italic pattern would read it as
    an italic * (the * between the two outer *s).
    """
    import re

    if text.strip() == "***":
        return [(text, False, False, False, False, False)]

    pattern = re.compile(
        r"\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*|<u>(.+?)</u>|~~(.+?)~~|==(.+?)=="
    )
    runs: list[tuple[str, bool, bool, bool, bool, bool]] = []
    pos = 0
    for match in pattern.finditer(text):
        if match.start() > pos:
            runs.append(
                (text[pos:match.start()], False, False, False, False, False)
            )
        if match.group(1) is not None:
            content, flags = match.group(1), (True, True, False, False, False)
        elif match.group(2) is not None:
            content, flags = match.group(2), (True, False, False, False, False)
        elif match.group(3) is not None:
            content, flags = match.group(3), (False, True, False, False, False)
        elif match.group(4) is not None:
            content, flags = match.group(4), (False, False, True, False, False)
        elif match.group(5) is not None:
            content, flags = match.group(5), (False, False, False, True, False)
        else:
            content, flags = match.group(6), (False, False, False, False, True)
        # Markers nest: parse the inside, carrying the outer flags in.
        for sub_text, bold, italic, underline, strike, highlight in parse_inline(content):
            runs.append(
                (
                    sub_text,
                    bold or flags[0],
                    italic or flags[1],
                    underline or flags[2],
                    strike or flags[3],
                    highlight or flags[4],
                )
            )
        pos = match.end()
    if pos < len(text):
        runs.append((text[pos:], False, False, False, False, False))
    return runs


def split_paragraphs(text: str) -> list[str]:
    """Split plain text into paragraphs on blank lines."""
    import re

    return [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]


def aligned_paragraph(paragraph: str):
    """A <div style="text-align: X;"> paragraph: its alignment
    ("center", "right", or "justify") and inner text, or (None,
    paragraph) when it is not one.

    Alignment is stored in the file as an HTML div because Markdown
    has no alignment syntax. Only center, right, and justify are
    wrapped; left-aligned text is the default and stays unwrapped.
    """
    import re

    match = re.fullmatch(
        r'<div style="text-align: (center|right|justify);">(.*)</div>',
        paragraph,
        re.DOTALL,
    )
    if match is None:
        return None, paragraph
    return match.group(1), match.group(2)
