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
"""Bundled resources: files shipped with the app.

When the app runs from source, resources live in the project
folder. When it runs as a PyInstaller bundle, they live in the
bundle folder (sys._MEIPASS). This module resolves a resource
path in both cases, so the app finds its icon, images, and the
LICENSE file either way.
"""

import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    """Path to a file shipped with the app.

    `relative` is the path inside the project folder, e.g.
    "LICENSE" or "novel_shop/icon.png". In a PyInstaller bundle
    the same file sits at the same relative path under the
    bundle folder.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    return Path(__file__).resolve().parent.parent / relative
