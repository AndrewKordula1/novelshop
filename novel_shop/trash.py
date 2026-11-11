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
"""Trash: deleted files go here, inside the project folder.

A .trash folder next to the documents. Deleting a file moves it there
instead of removing it, so a cut scene or chapter is recoverable with
one right-click (Restore) instead of a trip to the Recycle Bin. The
folder travels with the project, and the tree hides it like any other
dot-folder — it only shows up as the Trash section. A file deleted
twice, or restored over an existing file, gets a number ("Chapter 1
2.chapter") so nothing is ever overwritten. Emptying the Trash is the
one permanent delete, and it asks first.
"""

from pathlib import Path

from novel_shop.file_types import unique_path

TRASH_FOLDER_NAME = ".trash"


def trash_folder(folder: str) -> Path:
    return Path(folder) / TRASH_FOLDER_NAME


def trash_file(folder: str, path: str) -> tuple[bool, str]:
    """Move a file into the Trash. Returns (ok, new path or error)."""
    source = Path(path)
    target_folder = trash_folder(folder)
    try:
        target_folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"Could not create Trash folder: {exc}"
    target = Path(
        unique_path(
            str(target_folder), source.stem, source.suffix.lstrip(".")
        )
    )
    try:
        source.rename(target)
    except OSError as exc:
        return False, f"Could not move to Trash: {exc}"
    return True, str(target)


def list_trashed(folder: str) -> list[Path]:
    """Files in the Trash, by name."""
    target_folder = trash_folder(folder)
    if not target_folder.is_dir():
        return []
    return sorted(
        (child for child in target_folder.iterdir() if child.is_file()),
        key=lambda child: child.name.lower(),
    )


def restore_file(folder: str, trashed_path: str) -> tuple[bool, str]:
    """Move a trashed file back to the folder. Returns (ok, path or error)."""
    source = Path(trashed_path)
    target = Path(
        unique_path(folder, source.stem, source.suffix.lstrip("."))
    )
    try:
        source.rename(target)
    except OSError as exc:
        return False, f"Could not restore: {exc}"
    return True, str(target)


def empty_trash(folder: str) -> tuple[int, list[str]]:
    """Permanently delete every file in the Trash. Returns (count, errors)."""
    deleted = 0
    errors: list[str] = []
    for child in list_trashed(folder):
        try:
            child.unlink()
            deleted += 1
        except OSError as exc:
            errors.append(f"Could not delete {child.name}: {exc}")
    return deleted, errors
