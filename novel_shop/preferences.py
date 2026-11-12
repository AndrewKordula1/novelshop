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
"""Preferences: editor font and highlight colors, kept in AppData.

A small JSON file next to session.json. Everything here is forgiving:
a missing or broken file just means defaults.
"""

import json
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from novel_shop.file_types import FILE_TYPES
from novel_shop.manuscript import term_groups

DEFAULT_FONT_FAMILY = "Georgia"
DEFAULT_FONT_SIZE = 15
_UNKNOWN_HIGHLIGHT_COLOR = "#757575"


def default_preferences_path() -> str:
    folder = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    return str(Path(folder) / "preferences.json")


def default_highlight_colors() -> dict[str, str]:
    """One color per highlight group, from the type's badge color."""
    colors: dict[str, str] = {}
    for group in term_groups():
        colors[group] = _UNKNOWN_HIGHLIGHT_COLOR
    for file_type in FILE_TYPES:
        if file_type.group in colors:
            colors[file_type.group] = file_type.badge_color
    return colors


def default_preferences() -> dict:
    return {
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE,
        "highlight_colors": default_highlight_colors(),
        "highlight_enabled": {},
        "custom_words": [],
        "spellcheck_enabled": True,
        "weasel_enabled": True,
        "smart_quotes": True,
        "auto_capitalize": True,  # capitalize a sentence's first letter as typed
        "continue_lists": True,  # Enter on a list item continues it
        "bookmarks": {},  # file path -> cursor position, one per file
        "recent_folders": [],  # last opened project folders, newest first (max 5)
        "line_spacing": 1.0,  # 1.0, 1.5, or 2.0 — display only, not in the file
        "typewriter": False,  # typewriter scrolling — display only
        "first_line_indent": False,  # novel paragraph indent — display only
        "show_invisibles": False,  # ¶ marks for spaces/tabs/breaks — display only
        "focus_sentence": False,  # dim everything but the sentence — display only
        "line_numbers": False,  # line-number margin — display only
        "theme": "novelshop-light",  # "novelshop-dark" or "novelshop-light"
        "read_aloud_engine": "system",  # "system" or "piper"
        "piper_voice_path": "",
    }


def load_preferences(path: str | None = None) -> dict:
    """Load preferences, merged over the defaults."""
    prefs = default_preferences()
    target = Path(path) if path else Path(default_preferences_path())
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return prefs
    if not isinstance(data, dict):
        return prefs
    for key in ("font_family", "font_size"):
        if key in data:
            prefs[key] = data[key]
    saved_colors = data.get("highlight_colors")
    if isinstance(saved_colors, dict):
        prefs["highlight_colors"].update(
            {k: v for k, v in saved_colors.items() if isinstance(v, str)}
        )
    saved_enabled = data.get("highlight_enabled")
    if isinstance(saved_enabled, dict):
        prefs["highlight_enabled"] = {
            k: bool(v) for k, v in saved_enabled.items()
        }
    saved_words = data.get("custom_words")
    if isinstance(saved_words, list):
        prefs["custom_words"] = [
            word for word in saved_words if isinstance(word, str)
        ]
    if isinstance(data.get("spellcheck_enabled"), bool):
        prefs["spellcheck_enabled"] = data["spellcheck_enabled"]
    if isinstance(data.get("weasel_enabled"), bool):
        prefs["weasel_enabled"] = data["weasel_enabled"]
    if isinstance(data.get("smart_quotes"), bool):
        prefs["smart_quotes"] = data["smart_quotes"]
    if isinstance(data.get("auto_capitalize"), bool):
        prefs["auto_capitalize"] = data["auto_capitalize"]
    if isinstance(data.get("continue_lists"), bool):
        prefs["continue_lists"] = data["continue_lists"]
    if isinstance(data.get("bookmarks"), dict):
        prefs["bookmarks"] = {
            str(k): int(v)
            for k, v in data["bookmarks"].items()
            if isinstance(v, int)
        }
    if isinstance(data.get("recent_folders"), list):
        prefs["recent_folders"] = [
            str(f) for f in data["recent_folders"][:5]
        ]
    if data.get("line_spacing") in (1.0, 1.5, 2.0):
        prefs["line_spacing"] = data["line_spacing"]
    if isinstance(data.get("typewriter"), bool):
        prefs["typewriter"] = data["typewriter"]
    if isinstance(data.get("first_line_indent"), bool):
        prefs["first_line_indent"] = data["first_line_indent"]
    if isinstance(data.get("show_invisibles"), bool):
        prefs["show_invisibles"] = data["show_invisibles"]
    if isinstance(data.get("focus_sentence"), bool):
        prefs["focus_sentence"] = data["focus_sentence"]
    if isinstance(data.get("line_numbers"), bool):
        prefs["line_numbers"] = data["line_numbers"]
    # Old theme name, migrated: "system" was replaced by Novelshop Light.
    saved_theme = data.get("theme")
    if saved_theme in ("novelshop-dark", "novelshop-light"):
        prefs["theme"] = saved_theme
    elif saved_theme == "system":
        prefs["theme"] = "novelshop-light"
    if data.get("read_aloud_engine") in ("system", "piper"):
        prefs["read_aloud_engine"] = data["read_aloud_engine"]
    if isinstance(data.get("piper_voice_path"), str):
        prefs["piper_voice_path"] = data["piper_voice_path"]
    return prefs


def save_preferences(prefs: dict, path: str | None = None) -> None:
    target = Path(path) if path else Path(default_preferences_path())
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
    except OSError:
        pass


def highlight_color(prefs: dict, group: str) -> str:
    """The highlight color for a group, grey when unknown."""
    return prefs["highlight_colors"].get(group, _UNKNOWN_HIGHLIGHT_COLOR)


def highlight_enabled(prefs: dict, group: str) -> bool:
    """Whether a group is highlighted; on unless turned off."""
    return prefs["highlight_enabled"].get(group, True)
