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
"""Snapshot diff: show what changed between two versions of a text.

A unified diff, rendered as a page: added lines in green, removed
lines in red, the file headers in grey. Used by the Snapshots
dialog to compare two snapshots, or one snapshot with the current
document.
"""

import difflib
import html

from PySide6.QtWidgets import (
    QDialog,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)


def unified_diff(
    old_text: str,
    new_text: str,
    from_name: str,
    to_name: str,
) -> list[str]:
    """The lines that changed, in unified-diff form."""
    return list(
        difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            fromfile=from_name,
            tofile=to_name,
            lineterm="",
        )
    )


def diff_to_html(lines: list[str]) -> str:
    """A unified diff as a readable page: + green, - red."""
    if not lines:
        return "<p>No differences.</p>"
    parts = ['<p style="font-family: monospace;">']
    for line in lines:
        escaped = html.escape(line) or "&nbsp;"
        if line.startswith("+++") or line.startswith("---"):
            style = "color: #757575;"
        elif line.startswith("@@"):
            style = "color: #757575;"
        elif line.startswith("+"):
            style = "color: #2e7d32; background: #e8f5e9;"
        elif line.startswith("-"):
            style = "color: #c62828; background: #ffebee;"
        else:
            style = ""
        parts.append(f'<div style="{style}">{escaped}</div>')
    parts.append("</p>")
    return "".join(parts)


class DiffDialog(QDialog):
    """Show a diff, read-only. Modeless, so it stays open."""

    def __init__(self, title: str, lines: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(False)
        browser = QTextBrowser()
        browser.setHtml(diff_to_html(lines))
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout = QVBoxLayout(self)
        layout.addWidget(browser, 1)
        layout.addWidget(close_button)
        self.resize(640, 480)
