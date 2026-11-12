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
"""Readability dialog: the current document's reading level.

Modeless, so it stays open while you write; Refresh re-reads the
current document if it changed. It shows the Flesch-Kincaid grade,
the reading-ease score, and the two averages that drive them, so
you can see whether long sentences or long words are doing the
work. It is a rough gauge, not a judgment — it only measures
sentence length and word length.
"""

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from novel_shop.readability import readability_stats


class ReadabilityDialog(QDialog):
    """The current document's readability, in a window that stays open."""

    def __init__(self, get_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Readability")
        self.setModal(False)
        self._get_text = get_text
        self._grade = QLabel("—")
        self._ease = QLabel("—")
        self._words = QLabel("—")
        self._sentences = QLabel("—")
        self._avg_sentence = QLabel("—")
        self._avg_syllables = QLabel("—")

        form = QFormLayout()
        form.addRow("Flesch-Kincaid grade:", self._grade)
        form.addRow("Reading ease:", self._ease)
        form.addRow("Words:", self._words)
        form.addRow("Sentences:", self._sentences)
        form.addRow("Words per sentence:", self._avg_sentence)
        form.addRow("Syllables per word:", self._avg_syllables)

        refresh_button = QPushButton("Refresh")
        close_button = QPushButton("Close")
        buttons = QHBoxLayout()
        buttons.addWidget(refresh_button)
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)
        self.resize(340, 220)

        refresh_button.clicked.connect(self.refresh)
        close_button.clicked.connect(self.close)
        self.refresh()

    def refresh(self) -> None:
        """Re-read the current document and show its stats again."""
        stats = readability_stats(self._get_text())
        self._grade.setText(stats.grade_label())
        self._ease.setText(stats.ease_label())
        self._words.setText(str(stats.words))
        self._sentences.setText(str(stats.sentences))
        if stats.words:
            self._avg_sentence.setText(
                f"{stats.avg_words_per_sentence:.1f}"
            )
            self._avg_syllables.setText(
                f"{stats.avg_syllables_per_word:.2f}"
            )
        else:
            self._avg_sentence.setText("—")
            self._avg_syllables.setText("—")
