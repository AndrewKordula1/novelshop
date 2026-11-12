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
"""Rename File dialog: a new name and type for a file in the tree.

The name is the stem; the type is the extension, picked from the same
dropdown as New File (built from novel_shop/file_types.py), with a
Custom option for any other extension. The target must not already
exist in the folder, and the name must be a legal file name. A name
typed with its extension on ("Chapter 2.chapter") is the stem: the
extension is stripped so it is not doubled.
"""

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from novel_shop.file_types import NEW_FILE_TYPES

CUSTOM_LABEL = "Custom..."
_ILLEGAL_NAME_CHARS = '<>:"/\\|?*'


class RenameFileDialog(QDialog):
    def __init__(self, folder: str, current_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rename File")
        self._folder = folder
        self._current_path = current_path
        current = Path(current_path)
        self.file_name = current.stem
        self.extension = current.suffix.lstrip(".").lower()

        self._name_field = QLineEdit(current.stem)
        self._type_box = QComboBox()
        for file_type in NEW_FILE_TYPES:
            self._type_box.addItem(file_type.label, file_type.extension)
        self._type_box.addItem(CUSTOM_LABEL, None)
        # Pre-select the file's current type; an extension the dropdown
        # does not list (.txt, .md, or a custom one) gets the Custom
        # row with its own field filled in.
        current_index = self._type_box.findData(self.extension)
        if current_index >= 0:
            self._type_box.setCurrentIndex(current_index)
        else:
            self._type_box.setCurrentIndex(self._type_box.count() - 1)
        self._custom_label = QLabel("Extension (without the dot):")
        self._custom_field = QLineEdit()
        self._custom_field.setPlaceholderText("e.g. spell")
        if current_index < 0:
            self._custom_field.setText(self.extension)
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red")

        self._custom_label.setVisible(current_index < 0)
        self._custom_field.setVisible(current_index < 0)

        form = QFormLayout()
        form.addRow("Name:", self._name_field)
        form.addRow("Type:", self._type_box)
        form.addRow(self._custom_label, self._custom_field)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._error_label)
        layout.addWidget(buttons)

        self._type_box.currentIndexChanged.connect(self._on_type_changed)
        self._name_field.selectAll()

    def _on_type_changed(self) -> None:
        is_custom = self._type_box.currentData() is None
        self._custom_label.setVisible(is_custom)
        self._custom_field.setVisible(is_custom)
        if is_custom:
            self._custom_field.setFocus()

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)

    def accept(self) -> None:
        name = self._name_field.text().strip()
        if not name:
            self._show_error("Give the file a name.")
            return
        if any(char in name for char in _ILLEGAL_NAME_CHARS):
            self._show_error("That name can't be a file name.")
            return
        if self._type_box.currentData() is None:
            extension = self._custom_field.text().strip().lstrip(".").lower()
            if not extension or not all(
                char.isalnum() or char in "-_" for char in extension
            ):
                self._show_error(
                    "Use letters, numbers, - or _ for an extension."
                )
                return
        else:
            extension = self._type_box.currentData()
        if name.lower().endswith(f".{extension}"):
            name = name[: -len(extension) - 1]
            if not name:
                self._show_error("Give the file a name.")
                return
        target = Path(self._folder) / f"{name}.{extension}"
        # normcase: a rename that only changes the case is the same
        # file, not a clash with an existing one.
        if target.exists() and os.path.normcase(
            str(target)
        ) != os.path.normcase(self._current_path):
            self._show_error("A file with that name already exists.")
            return
        self.file_name = name
        self.extension = extension
        super().accept()
