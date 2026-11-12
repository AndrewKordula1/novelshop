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
"""Formatting toolbar: font, size, bold, italic, underline, strikethrough.

The font and size set the writing font for the whole editor — an app
preference, not part of the document, because Markdown cannot store
a font. Bold, italic, underline, and strikethrough format the
selection and are saved in the file as Markdown; clicking a toggle
again turns its formatting off.
"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFontComboBox,
    QToolBar,
    QToolButton,
)

FONT_SIZES = [
    "8",
    "9",
    "10",
    "11",
    "12",
    "14",
    "16",
    "18",
    "20",
    "24",
    "28",
    "36",
    "48",
    "72",
]


class FormatToolbar(QToolBar):
    font_changed = Signal(str, int)  # family, size in pixels
    bold_triggered = Signal()
    italic_triggered = Signal()
    underline_triggered = Signal()
    strikethrough_triggered = Signal()
    highlight_triggered = Signal()
    dictionary_requested = Signal()

    def __init__(self, parent=None):
        super().__init__("Formatting", parent)
        self._font_box = QFontComboBox()
        self._font_box.currentFontChanged.connect(self._on_font_changed)
        self._size_box = QComboBox()
        self._size_box.setEditable(True)
        # Wide enough for the number and the drop-down arrow. The
        # theme gives every combo box 8px of side padding, which
        # leaves almost no room for the digits in a box this small,
        # so the size box uses 4px instead.
        self._size_box.setMinimumWidth(72)
        self._size_box.setStyleSheet("QComboBox { padding: 4px 4px; }")
        self._size_box.addItems(FONT_SIZES)
        self._size_box.activated.connect(self._on_font_changed)
        self._bold_button = self._make_toggle("B", bold=True)
        self._bold_button.toggled.connect(lambda _c: self.bold_triggered.emit())
        self._italic_button = self._make_toggle("I", italic=True)
        self._italic_button.toggled.connect(
            lambda _c: self.italic_triggered.emit()
        )
        self._underline_button = self._make_toggle("U", underline=True)
        self._underline_button.toggled.connect(
            lambda _c: self.underline_triggered.emit()
        )
        self._strike_button = self._make_toggle("S", strike=True)
        self._strike_button.toggled.connect(
            lambda _c: self.strikethrough_triggered.emit()
        )
        # Highlight: a toggle with a pale yellow background, the
        # highlighter mark, for passages to come back to.
        self._highlight_button = self._make_toggle("H")
        self._highlight_button.setStyleSheet(
            "QToolButton:checked { background: #fff59d; color: black; }"
        )
        self._highlight_button.toggled.connect(
            lambda _c: self.highlight_triggered.emit()
        )
        # A plain button, not a toggle: it opens the Dictionary window,
        # a general lookup that is not tied to the editor.
        self._dictionary_button = QToolButton()
        self._dictionary_button.setText("Dictionary")
        self._dictionary_button.clicked.connect(
            lambda _c: self.dictionary_requested.emit()
        )
        self.addWidget(self._font_box)
        self.addWidget(self._size_box)
        self.addSeparator()
        self.addWidget(self._bold_button)
        self.addWidget(self._italic_button)
        self.addWidget(self._underline_button)
        self.addWidget(self._strike_button)
        self.addWidget(self._highlight_button)
        self.addSeparator()
        self.addWidget(self._dictionary_button)

    def _make_toggle(
        self,
        text: str,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        strike: bool = False,
    ) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        font = button.font()
        font.setBold(bold)
        font.setItalic(italic)
        font.setUnderline(underline)
        font.setStrikeOut(strike)
        button.setFont(font)
        button.setCheckable(True)
        return button

    def _on_font_changed(self) -> None:
        try:
            size = int(self._size_box.currentText())
        except ValueError:
            return
        self.font_changed.emit(self._font_box.currentFont().family(), size)

    def set_editor_font(self, family: str, size: int) -> None:
        """Show the current editor font without emitting font_changed."""
        self._font_box.blockSignals(True)
        self._size_box.blockSignals(True)
        self._font_box.setCurrentFont(QFont(family))
        self._size_box.setCurrentText(str(size))
        self._font_box.blockSignals(False)
        self._size_box.blockSignals(False)

    def set_bold_active(self, active: bool) -> None:
        self._bold_button.blockSignals(True)
        self._bold_button.setChecked(active)
        self._bold_button.blockSignals(False)

    def set_italic_active(self, active: bool) -> None:
        self._italic_button.blockSignals(True)
        self._italic_button.setChecked(active)
        self._italic_button.blockSignals(False)

    def set_underline_active(self, active: bool) -> None:
        self._underline_button.blockSignals(True)
        self._underline_button.setChecked(active)
        self._underline_button.blockSignals(False)

    def set_strikethrough_active(self, active: bool) -> None:
        self._strike_button.blockSignals(True)
        self._strike_button.setChecked(active)
        self._strike_button.blockSignals(False)

    def set_highlight_active(self, active: bool) -> None:
        self._highlight_button.blockSignals(True)
        self._highlight_button.setChecked(active)
        self._highlight_button.blockSignals(False)
