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
"""Snapshot dialog: browse a document's snapshots, restore or delete.

Lists snapshots newest first with their date and word count. Restore
loads the snapshot's text into the editor (as unsaved changes — nothing
is written until the user saves). Delete removes the snapshot file.
Compare shows what changed: select two snapshots to diff them, or one
to diff it against the current document.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from novel_shop.diff import DiffDialog, unified_diff
from novel_shop.snapshots import (
    Snapshot,
    delete_snapshot,
    list_snapshots,
    read_snapshot,
)
from novel_shop.wordcount import count_words


class SnapshotDialog(QDialog):
    def __init__(
        self, file_path: str, current_text: str = "", parent=None
    ):
        super().__init__(parent)
        self._file_path = file_path
        self._current_text = current_text
        self.restored_text: str | None = None
        self.setWindowTitle(f"Snapshots — {Path(file_path).name}")
        self.resize(480, 320)

        self._info_label = QLabel()
        self._list = QListWidget()
        self._list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self._restore_button = QPushButton("Restore")
        self._delete_button = QPushButton("Delete")
        self._compare_button = QPushButton("Compare")
        close_button = QPushButton("Close")

        buttons = QHBoxLayout()
        buttons.addWidget(self._restore_button)
        buttons.addWidget(self._delete_button)
        buttons.addWidget(self._compare_button)
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._info_label)
        layout.addWidget(self._list)
        layout.addLayout(buttons)

        self._list.currentItemChanged.connect(lambda *_: self._update_buttons())
        self._list.itemSelectionChanged.connect(self._update_buttons)
        self._restore_button.clicked.connect(self._on_restore)
        self._delete_button.clicked.connect(self._on_delete)
        self._compare_button.clicked.connect(self._on_compare)
        close_button.clicked.connect(self.reject)

        self._refresh_list()

    def _refresh_list(self) -> None:
        self._list.clear()
        snapshots = list_snapshots(self._file_path)
        for snap in snapshots:
            ok, text = read_snapshot(snap.path)
            words = count_words(text).words if ok else 0
            item = QListWidgetItem(f"{snap.display} · {words} words")
            item.setData(Qt.ItemDataRole.UserRole, snap.path)
            self._list.addItem(item)
        if snapshots:
            self._info_label.setText(f"{len(snapshots)} snapshot(s)")
        else:
            self._info_label.setText(
                "No snapshots yet — take one from the File menu."
            )
        self._update_buttons()

    def _update_buttons(self) -> None:
        has_selection = self._list.currentItem() is not None
        self._restore_button.setEnabled(has_selection)
        self._delete_button.setEnabled(has_selection)
        # Compare: one snapshot against the current document, or two
        # snapshots against each other.
        selected = len(self._list.selectedItems())
        self._compare_button.setEnabled(selected in (1, 2))

    def _on_compare(self) -> None:
        """Diff the selected snapshots, or one against the document."""
        items = self._list.selectedItems()
        if len(items) == 2:
            snaps = [self._snapshot_for(item) for item in items]
            snaps.sort(key=lambda snap: snap.taken_at)
            older, newer = snaps
            ok_old, old_text = read_snapshot(older.path)
            ok_new, new_text = read_snapshot(newer.path)
            if not (ok_old and ok_new):
                return
            lines = unified_diff(
                old_text, new_text, older.display, newer.display
            )
            title = f"Snapshot diff — {older.display} → {newer.display}"
        elif len(items) == 1:
            snap = self._snapshot_for(items[0])
            ok, old_text = read_snapshot(snap.path)
            if not ok:
                return
            lines = unified_diff(
                old_text, self._current_text, snap.display, "Current"
            )
            title = f"Snapshot diff — {snap.display} → Current"
        else:
            return
        self._diff_dialog = DiffDialog(title, lines, self)
        self._diff_dialog.show()

    def _snapshot_for(self, item: QListWidgetItem) -> Snapshot:
        """The snapshot an item stands for, by its stored path."""
        path = item.data(Qt.ItemDataRole.UserRole)
        for snap in list_snapshots(self._file_path):
            if snap.path == path:
                return snap
        raise KeyError(path)

    def _on_restore(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        ok, text = read_snapshot(item.data(Qt.ItemDataRole.UserRole))
        if not ok:
            return
        self.restored_text = text
        self.accept()

    def _on_delete(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        delete_snapshot(item.data(Qt.ItemDataRole.UserRole))
        self._refresh_list()
