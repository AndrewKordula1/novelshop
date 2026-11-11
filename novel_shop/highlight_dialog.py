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
"""Highlight Colors dialog: pick a color per category, or turn it off."""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QPushButton,
    QVBoxLayout,
)


class HighlightDialog(QDialog):
    def __init__(
        self,
        groups: list[str],
        colors: dict[str, str],
        enabled: dict[str, bool],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Highlight Colors")
        self._groups = groups
        self._colors = {
            group: colors.get(group, "#757575") for group in groups
        }
        self._boxes: dict[str, QCheckBox] = {}
        self._swatches: dict[str, QPushButton] = {}

        form = QFormLayout()
        for group in groups:
            check = QCheckBox(group)
            check.setChecked(enabled.get(group, True))
            swatch = QPushButton()
            swatch.setFixedSize(28, 20)
            self._paint_swatch(swatch, self._colors[group])
            swatch.clicked.connect(
                lambda _checked=False, g=group: self._pick_color(g)
            )
            form.addRow(check, swatch)
            self._boxes[group] = check
            self._swatches[group] = swatch

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _paint_swatch(self, button: QPushButton, color: str) -> None:
        button.setStyleSheet(
            f"background: {color}; border: 1px solid #888;"
        )

    def _pick_color(self, group: str) -> None:
        color = QColorDialog.getColor(
            QColor(self._colors[group]), self, f"Color for {group}"
        )
        if color.isValid():
            self._colors[group] = color.name()
            self._paint_swatch(self._swatches[group], color.name())

    @property
    def colors(self) -> dict[str, str]:
        return self._colors

    @property
    def enabled(self) -> dict[str, bool]:
        return {
            group: self._boxes[group].isChecked() for group in self._groups
        }
