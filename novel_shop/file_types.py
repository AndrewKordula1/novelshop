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
"""File types: custom extensions that categorize a document.

Every Novelshop document is a plain text file. Its extension says
what kind of document it is, and the file tree groups files by that
extension. Full words, not abbreviations: `.chapter` needs no decoding,
where `.ch` could be chapter or character. This module is the single
place that defines the types: add a new type here and the tree, the
New File dropdown, the file dialogs, and its badge icon all pick it up.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileType:
    extension: str  # without the dot, e.g. "chapter"
    label: str  # singular, e.g. "Chapter"
    group: str  # tree heading, e.g. "Chapters"
    badge_letters: str  # two letters on the type's badge icon, e.g. "Ch"
    badge_color: str  # badge background, e.g. "#1565c0"


FILE_TYPES: list[FileType] = [
    FileType("part", "Part", "Parts", "Pa", "#607d8b"),
    FileType("chapter", "Chapter", "Chapters", "Ch", "#1565c0"),
    FileType("scene", "Scene", "Scenes", "Sc", "#2e7d32"),
    FileType("draft", "Draft", "Drafts", "Dr", "#757575"),
    FileType("plot", "Plot", "Plots", "Pl", "#7b1fa2"),
    FileType("outline", "Outline", "Outlines", "Ou", "#00897b"),
    FileType("character", "Character", "Characters", "Ca", "#ef6c00"),
    FileType("location", "Location", "Locations", "Lo", "#795548"),
    FileType("language", "Language", "Languages", "La", "#3949ab"),
    FileType("culture", "Culture", "Cultures", "Cu", "#c2185b"),
    FileType("faction", "Faction", "Factions", "Fa", "#c62828"),
    FileType("species", "Species", "Species", "Sp", "#558b2f"),
    FileType("magic", "Magic", "Magic", "Ma", "#6a1b9a"),
    FileType("item", "Item", "Items", "It", "#00838f"),
    FileType("timeline", "Timeline", "Timelines", "Ti", "#546e7a"),
    FileType("glossary", "Glossary", "Glossaries", "Gl", "#827717"),
    FileType("research", "Research", "Research", "Re", "#e65100"),
    FileType("note", "Note", "Notes", "No", "#f57f17"),
    FileType("txt", "Document", "Documents", "Do", "#455a64"),
    FileType("md", "Document", "Documents", "Do", "#455a64"),
]

# Types in the New File dropdown (plain text files have none: open them
# from the tree or with Open File).
NEW_FILE_TYPES: list[FileType] = [
    file_type
    for file_type in FILE_TYPES
    if file_type.extension not in ("txt", "md")
]


def file_type_for_extension(extension: str) -> FileType | None:
    clean = extension.lower().lstrip(".")
    for file_type in FILE_TYPES:
        if file_type.extension == clean:
            return file_type
    return None


def group_for_extension(extension: str) -> str | None:
    file_type = file_type_for_extension(extension)
    return file_type.group if file_type is not None else None


def group_for_unknown_extension(extension: str) -> str:
    """Section name for an extension with no built-in type.

    Any extension can be used: a `.spell` file gets a "Spell" section.
    """
    clean = extension.lower().lstrip(".")
    return clean.capitalize()


def groups_in_order() -> list[str]:
    seen: list[str] = []
    for file_type in FILE_TYPES:
        if file_type.group not in seen:
            seen.append(file_type.group)
    return seen


def all_extensions() -> list[str]:
    return [file_type.extension for file_type in FILE_TYPES]


def file_dialog_filter() -> str:
    patterns = " ".join(f"*.{ext}" for ext in all_extensions())
    return f"Story files ({patterns});;All files (*)"


def unique_path(folder: str, stem: str, extension: str) -> str:
    """First free path folder/stem.extension, adding a number if taken."""
    candidate = Path(folder) / f"{stem}.{extension}"
    number = 2
    while candidate.exists():
        candidate = Path(folder) / f"{stem} {number}.{extension}"
        number += 1
    return str(candidate)
