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
"""Export dialog: pick a format, the files, and the title and author.

The file list comes in tree order (see novel_shop/manuscript.py).
Story files — parts, chapters, scenes — start ticked; reference
material starts unticked. At least one file and a title are required.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from novel_shop.manuscript import ManuscriptFile

FORMATS = [
    ("Word document (.docx)", "docx"),
    ("EPUB ebook (.epub)", "epub"),
    ("PDF (.pdf)", "pdf"),
]


class ExportDialog(QDialog):
    def __init__(
        self,
        files: list[ManuscriptFile],
        default_title: str,
        parent=None,
        check_all: bool = False,
    ):
        """Pick a format, the files, and the title and author.

        check_all ticks every file in the list, whatever its type —
        for exporting one file the user picked, so it starts ticked
        even when it is a reference file.
        """
        super().__init__(parent)
        self.setWindowTitle("Export")
        self._files = files
        self.format = "docx"
        self.title = default_title
        self.author = ""

        self._format_box = QComboBox()
        for label, value in FORMATS:
            self._format_box.addItem(label, value)
        self._title_field = QLineEdit(default_title)
        self._author_field = QLineEdit()
        self._author_field.setPlaceholderText("optional")
        self._file_list = QListWidget()
        for file in files:
            item = QListWidgetItem(f"{file.group} — {file.title}")
            item.setFlags(
                item.flags() | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(
                Qt.CheckState.Checked
                if check_all or file.include_by_default
                else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, file.path)
            self._file_list.addItem(item)
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red")

        form = QFormLayout()
        form.addRow("Format:", self._format_box)
        form.addRow("Title:", self._title_field)
        form.addRow("Author:", self._author_field)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel("Files to include:"))
        layout.addWidget(self._file_list)
        layout.addWidget(self._error_label)
        layout.addWidget(buttons)

    @property
    def selected_files(self) -> list[ManuscriptFile]:
        """The ticked files, in tree order."""
        selected_paths = {
            self._file_list.item(row).data(Qt.ItemDataRole.UserRole)
            for row in range(self._file_list.count())
            if self._file_list.item(row).checkState() == Qt.CheckState.Checked
        }
        return [file for file in self._files if file.path in selected_paths]

    def accept(self) -> None:
        title = self._title_field.text().strip()
        if not title:
            self._error_label.setText("Give the book a title.")
            return
        if not self.selected_files:
            self._error_label.setText("Tick at least one file to export.")
            return
        self.format = self._format_box.currentData()
        self.title = title
        self.author = self._author_field.text().strip()
        super().accept()
