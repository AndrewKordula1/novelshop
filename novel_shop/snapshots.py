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
"""Snapshots: dated backups of a document's text.

One .txt file per snapshot in a `.snapshots` folder next to the
document, named `yyyy-MM-dd_HH-MM-SS.txt` (a -2, -3 suffix when two
land in the same second). The dot-folder keeps them out of the file
tree, and they travel with the document's folder.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from novel_shop.storage import read_text_file, write_text_file

_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})(?:-\d+)?.txt$")


@dataclass
class Snapshot:
    path: str
    taken_at: datetime

    @property
    def display(self) -> str:
        return self.taken_at.strftime("%b %d, %Y, %I:%M %p")


def snapshot_folder(file_path: str) -> Path:
    return Path(file_path).parent / ".snapshots"


def create_snapshot(file_path: str, text: str) -> tuple[bool, str]:
    """Save the text as a new snapshot. Returns (ok, path or error)."""
    folder = snapshot_folder(file_path)
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"Could not create snapshot folder: {exc}"
    base = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name = f"{base}.txt"
    counter = 2
    while (folder / name).exists():
        name = f"{base}-{counter}.txt"
        counter += 1
    ok, message = write_text_file(str(folder / name), text)
    if not ok:
        return False, message
    return True, str(folder / name)


def list_snapshots(file_path: str) -> list[Snapshot]:
    """Snapshots for a document, newest first."""
    folder = snapshot_folder(file_path)
    if not folder.is_dir():
        return []
    found = []
    for child in folder.iterdir():
        match = _NAME_RE.match(child.name)
        if not match:
            continue
        try:
            taken_at = datetime.strptime(match.group(1), "%Y-%m-%d_%H-%M-%S")
        except ValueError:
            continue
        found.append(Snapshot(path=str(child), taken_at=taken_at))
    found.sort(key=lambda snap: snap.taken_at, reverse=True)
    return found


def read_snapshot(path: str) -> tuple[bool, str]:
    return read_text_file(path)


def delete_snapshot(path: str) -> bool:
    try:
        Path(path).unlink()
        return True
    except OSError:
        return False
