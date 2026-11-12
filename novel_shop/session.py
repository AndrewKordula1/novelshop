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
"""Session: remember the open folder and files between runs.

A small JSON file in the platform's app-data location holds the last
open files. Everything here is forgiving: a missing or broken session
file just means "start fresh", never an error.
"""

import json
from pathlib import Path

from PySide6.QtCore import QStandardPaths


def default_session_path() -> str:
    folder = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    return str(Path(folder) / "session.json")


def save_session(
    folder: str | None,
    files: list[str],
    active: int = 0,
    path: str | None = None,
) -> None:
    """Save the open folder, open files, and active tab index."""
    target = Path(path) if path else Path(default_session_path())
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps({"folder": folder, "files": files, "active": active}),
            encoding="utf-8",
        )
    except OSError:
        pass


def load_session(path: str | None = None) -> dict:
    """Load the saved session. Returns {} when there is none.

    Also understands the old single-file format ({"folder", "file"}).
    """
    target = Path(path) if path else Path(default_session_path())
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    if "files" in data:
        return {
            "folder": data.get("folder"),
            "files": data.get("files") or [],
            "active": data.get("active") or 0,
        }
    if "file" in data:
        old_file = data.get("file")
        return {
            "folder": data.get("folder"),
            "files": [old_file] if old_file else [],
            "active": 0,
        }
    return {}
