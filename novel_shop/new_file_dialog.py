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
"""New File dialog: name a file and pick its type from a dropdown.

The dropdown is built from novel_shop/file_types.py, so a new type
shows up here with no changes to this dialog. "Custom..." lets the
user type any extension instead.
"""

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


class NewFileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New File")
        self.file_name = "Untitled"
        self.extension = NEW_FILE_TYPES[0].extension

        self._name_field = QLineEdit("Untitled")
        self._type_box = QComboBox()
        for file_type in NEW_FILE_TYPES:
            self._type_box.addItem(file_type.label, file_type.extension)
        self._type_box.addItem(CUSTOM_LABEL, None)
        self._custom_label = QLabel("Extension (without the dot):")
        self._custom_field = QLineEdit()
        self._custom_field.setPlaceholderText("e.g. spell")
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red")

        self._custom_label.hide()
        self._custom_field.hide()

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
        self.file_name = name
        self.extension = extension
        super().accept()
