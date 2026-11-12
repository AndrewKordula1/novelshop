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
"""Comments dialog: the notes pinned to the current document.

Lists every comment for the file — its note, the passage it is pinned
to, and when it was added. Double-click a comment (or Go To) to jump
to its passage in the editor. Add pins a note to the current
selection; Edit changes the note; Delete removes it. A comment whose
anchored passage was rewritten is still listed, marked orphaned,
because the note itself may still matter.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from novel_shop.comments import Comment, find_anchor


class CommentsDialog(QDialog):
    # Emitted when the user wants to jump to a comment's passage:
    # the anchor text to find in the editor.
    jump_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Comments")
        self.resize(560, 420)
        self._comments: list[Comment] = []
        self._document_text = ""
        self._selection = ""

        self._list = QListWidget()
        self._note_field = QTextEdit()
        self._note_field.setPlaceholderText("Write the note here…")
        self._note_field.setMaximumHeight(90)
        self._anchor_label = QLabel("No passage selected")
        self._anchor_label.setWordWrap(True)

        add_button = QPushButton("Add")
        add_button.clicked.connect(self._add_comment)
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(self._edit_comment)
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self._delete_comment)
        goto_button = QPushButton("Go To Passage")
        goto_button.clicked.connect(self._go_to_passage)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(add_button)
        buttons.addWidget(edit_button)
        buttons.addWidget(delete_button)
        buttons.addWidget(goto_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Notes pinned to this document:"))
        layout.addWidget(self._list, 1)
        layout.addWidget(self._anchor_label)
        layout.addWidget(self._note_field)
        layout.addLayout(buttons)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        self._list.itemDoubleClicked.connect(self._go_to_passage)

    # -- data ------------------------------------------------------------

    def set_comments(
        self, comments: list[Comment], document_text: str, selection: str
    ) -> None:
        """Fill the list from the file's comments."""
        self._comments = list(comments)
        self._document_text = document_text
        self._selection = selection
        self._refresh_list()
        if selection:
            self._anchor_label.setText(f"Pinned to: “{selection}”")
        else:
            self._anchor_label.setText(
                "Select a passage in the editor to pin a note to it."
            )

    def comments(self) -> list[Comment]:
        return list(self._comments)

    # -- actions -----------------------------------------------------------

    def _add_comment(self) -> None:
        note = self._note_field.toPlainText().strip()
        if not self._selection:
            QMessageBox.information(
                self,
                "Comments",
                "Select a passage in the editor first, then add a note.",
            )
            return
        if not note:
            QMessageBox.information(
                self, "Comments", "Write the note first."
            )
            return
        from datetime import datetime

        import uuid

        self._comments.append(
            Comment(
                anchor=self._selection,
                text=note,
                created=datetime.now().strftime("%Y-%m-%d %H:%M"),
                id=str(uuid.uuid4())[:8],
            )
        )
        self._note_field.clear()
        self._refresh_list()

    def _edit_comment(self) -> None:
        item = self._current_comment()
        if item is None:
            return
        note = self._note_field.toPlainText().strip()
        if not note:
            return
        item.text = note
        self._refresh_list()

    def _delete_comment(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._comments):
            return
        del self._comments[row]
        self._note_field.clear()
        self._refresh_list()

    def _go_to_passage(self, _item=None) -> None:
        comment = self._current_comment()
        if comment is None:
            return
        self.jump_requested.emit(comment.anchor)

    # -- internals ---------------------------------------------------------

    def _current_comment(self):
        row = self._list.currentRow()
        if row < 0 or row >= len(self._comments):
            return None
        return self._comments[row]

    def _on_selection_changed(self) -> None:
        comment = self._current_comment()
        if comment is None:
            self._note_field.clear()
            return
        self._note_field.setPlainText(comment.text)

    def _refresh_list(self) -> None:
        self._list.clear()
        for comment in self._comments:
            orphaned = (
                find_anchor(self._document_text, comment.anchor) < 0
            )
            anchor = comment.anchor.replace("\n", " ").replace("\u2029", " ")
            if len(anchor) > 60:
                anchor = anchor[:60] + "…"
            label = f"{comment.text} — “{anchor}”"
            if comment.created:
                label += f" ({comment.created})"
            if orphaned:
                label += " [passage rewritten]"
            item = QListWidgetItem(label)
            if orphaned:
                item.setForeground(Qt.GlobalColor.gray)
            self._list.addItem(item)
