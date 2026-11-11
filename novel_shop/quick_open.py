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
"""Quick Open: jump to any file in the folder by typing its name.

A small picker (Ctrl+P): the folder's files in tree order, a filter
box on top. Type a few letters and the list narrows; Enter or a
double-click opens the file. It only lists files — it never reads
them — so it is instant even in a big folder.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from novel_shop.manuscript import ManuscriptFile


class QuickOpenDialog(QDialog):
    def __init__(self, files: list[ManuscriptFile], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Open")
        self.setModal(True)
        self.selected_path: str | None = None
        self._files = list(files)

        self._filter_field = QLineEdit()
        self._filter_field.setPlaceholderText("Type a file name…")
        self._list = QListWidget()

        layout = QVBoxLayout(self)
        layout.addWidget(self._filter_field)
        layout.addWidget(self._list, 1)
        self.resize(480, 360)

        self._filter_field.textChanged.connect(self._refilter)
        self._filter_field.returnPressed.connect(self._open_current)
        self._list.itemActivated.connect(self._open_item)
        self._list.itemDoubleClicked.connect(self._open_item)
        self._refilter()

    # -- filtering -------------------------------------------------------

    def _refilter(self) -> None:
        """Show the files whose name contains the filter text."""
        needle = self._filter_field.text().strip().lower()
        self._list.clear()
        for file in self._files:
            if needle and needle not in file.title.lower():
                continue
            item = QListWidgetItem(f"{file.title} · {file.group}")
            item.setData(Qt.ItemDataRole.UserRole, file.path)
            self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    # -- opening ---------------------------------------------------------

    def _open_current(self) -> None:
        item = self._list.currentItem()
        if item is not None:
            self._open_item(item)

    def _open_item(self, item: QListWidgetItem) -> None:
        self.selected_path = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def focus_filter(self) -> None:
        """Put the cursor in the filter box, ready to type."""
        self._filter_field.setFocus()
        self._filter_field.selectAll()
