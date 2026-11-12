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
"""Storage: reading and writing text files, nothing else.

Plain functions in, plain results out. Errors are reported as a
(False, message) pair instead of raising, so the main window can show
them in the status bar without try/except blocks everywhere.
"""

from pathlib import Path


def read_text_file(path: str) -> tuple[bool, str]:
    """Read a file as UTF-8 text. Returns (ok, text or error message)."""
    try:
        return True, Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return False, f"Could not open {path}: {exc}"


def write_text_file(path: str, text: str) -> tuple[bool, str]:
    """Write text to a file as UTF-8. Returns (ok, error message or '')."""
    try:
        Path(path).write_text(text, encoding="utf-8")
        return True, ""
    except OSError as exc:
        return False, f"Could not save {path}: {exc}"
