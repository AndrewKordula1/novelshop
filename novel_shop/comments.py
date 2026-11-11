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
"""Comments: notes pinned to a passage, without changing the text.

A comment is a note about a passage — "fix this scene", "check the
timeline" — for revision. Comments live in a sidecar JSON file next
to the document (Chapter 1.comments.json), so the story file stays
plain text and the notes travel with the project. A comment is
anchored by the exact text it was pinned to; when the document is
shown, the anchor is found again by searching for that text, so a
note follows its passage when the words around it move. If the
anchored text is gone (rewritten), the comment is orphaned: it stays
in the list but cannot jump to its passage.
"""

import json
from dataclasses import dataclass, field


@dataclass
class Comment:
    """One note pinned to a passage."""

    anchor: str  # the exact passage text the note is pinned to
    text: str  # the note itself
    created: str = ""  # "yyyy-MM-dd HH:MM" when it was added
    id: str = ""  # unique within the file, for edit/delete


def comments_path(file_path: str) -> str:
    """The sidecar JSON path for a document."""
    return f"{file_path}.comments.json"


def load_comments(file_path: str) -> list[Comment]:
    """The comments pinned to a document (empty when there are none)."""
    import os

    path = comments_path(file_path)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return []
    comments = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        anchor = item.get("anchor", "")
        text = item.get("text", "")
        if not anchor or not text:
            continue
        comments.append(
            Comment(
                anchor=anchor,
                text=text,
                created=item.get("created", ""),
                id=item.get("id", ""),
            )
        )
    return comments


def save_comments(file_path: str, comments: list[Comment]) -> None:
    """Write a document's comments to its sidecar JSON file."""
    data = [
        {
            "id": comment.id,
            "anchor": comment.anchor,
            "text": comment.text,
            "created": comment.created,
        }
        for comment in comments
    ]
    with open(comments_path(file_path), "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def find_anchor(document_text: str, anchor: str) -> int:
    """Where the anchored passage sits in the document, or -1.

    The anchor is the exact passage text, so a plain search finds it
    again after the words around it move. The first match wins.
    """
    if not anchor:
        return -1
    return document_text.find(anchor)
