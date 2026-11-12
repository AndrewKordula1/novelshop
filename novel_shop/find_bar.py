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
"""Find bar: find and replace in the current document.

Sits under the tabs, hidden until Ctrl+F (find) or Ctrl+H (replace).
Find Next wraps around the document; Replace acts on the current match;
Replace All reports how many it replaced. Esc hides the bar.
"""

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class FindBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._editor = None

        self.find_field = QLineEdit()
        self.find_field.setPlaceholderText("Find")
        self.replace_field = QLineEdit()
        self.replace_field.setPlaceholderText("Replace with")
        self._case_check = QCheckBox("Aa")
        self._case_check.setToolTip("Match case")
        self._regex_check = QCheckBox(".*")
        self._regex_check.setToolTip(
            "Treat the find text as a regular expression"
        )
        self._whole_word_check = QCheckBox("W")
        self._whole_word_check.setToolTip(
            "Match whole words only (cat, not catalogue)"
        )
        self._status_label = QLabel()
        prev_button = QPushButton("↑")
        next_button = QPushButton("↓")
        replace_button = QPushButton("Replace")
        replace_all_button = QPushButton("Replace All")
        self._replace_in_selection_button = QPushButton(
            "Replace in Selection"
        )
        self._replace_in_selection_button.setToolTip(
            "Replace every match inside the selected text only"
        )
        close_button = QPushButton("✕")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(QLabel("Find:"))
        layout.addWidget(self.find_field, 1)
        layout.addWidget(QLabel("Replace:"))
        layout.addWidget(self.replace_field, 1)
        layout.addWidget(self._case_check)
        layout.addWidget(self._regex_check)
        layout.addWidget(self._whole_word_check)
        layout.addWidget(prev_button)
        layout.addWidget(next_button)
        layout.addWidget(replace_button)
        layout.addWidget(replace_all_button)
        layout.addWidget(self._replace_in_selection_button)
        layout.addWidget(self._status_label)
        layout.addWidget(close_button)

        self.find_field.textChanged.connect(self._on_find_text_changed)
        self.find_field.returnPressed.connect(self.find_next)
        self.replace_field.returnPressed.connect(self.replace)
        self._case_check.toggled.connect(self._on_find_text_changed)
        self._regex_check.toggled.connect(self._on_find_text_changed)
        self._whole_word_check.toggled.connect(self._on_find_text_changed)
        prev_button.clicked.connect(self.find_previous)
        next_button.clicked.connect(self.find_next)
        replace_button.clicked.connect(self.replace)
        replace_all_button.clicked.connect(self.replace_all)
        self._replace_in_selection_button.clicked.connect(
            self.replace_in_selection
        )
        close_button.clicked.connect(self.hide_bar)

        escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        escape.activated.connect(self.hide_bar)

    # -- wiring ----------------------------------------------------------

    def set_editor(self, editor) -> None:
        if self._editor is not None:
            try:
                self._editor.textChanged.disconnect(self._update_status)
            except (RuntimeError, TypeError):
                pass
            try:
                self._editor.textChanged.disconnect(
                    self._update_find_matches
                )
            except (RuntimeError, TypeError):
                pass
        self._editor = editor
        if editor is not None:
            editor.textChanged.connect(self._update_status)
            editor.textChanged.connect(self._update_find_matches)
            self._update_status()
            self._update_find_matches()

    def show_for(self, editor, focus_replace: bool = False) -> None:
        self.set_editor(editor)
        if editor is None:
            return
        selected = editor.textCursor().selectedText()
        if selected:
            # Pre-fill without searching: the selection is already the
            # current match, and searching would skip past it.
            self.find_field.blockSignals(True)
            self.find_field.setText(selected)
            self.find_field.blockSignals(False)
        self.show()
        if focus_replace:
            self.replace_field.setFocus()
            self.replace_field.selectAll()
        else:
            self.find_field.setFocus()
            self.find_field.selectAll()
        self._update_status()
        self._update_find_matches()

    def hide_bar(self) -> None:
        self.hide()
        if self._editor is not None:
            self._editor.set_find_matches([])
            self._editor.setFocus()

    # -- find ------------------------------------------------------------

    def find_next(self) -> None:
        self._find(backward=False)

    def find_previous(self) -> None:
        self._find(backward=True)

    def _find(self, backward: bool) -> None:
        editor = self._editor
        needle = self.find_field.text()
        if editor is None or not needle:
            return
        flags = self._flags()
        if backward:
            flags |= QTextDocument.FindFlag.FindBackward
        pattern = self._regex()
        if pattern is not None and not pattern.isValid():
            self._status_label.setText("Invalid pattern")
            return
        found = (
            editor.find(pattern, flags)
            if pattern is not None
            else editor.find(needle, flags)
        )
        if found:
            self._update_status()
            return
        # Wrap around and try once more.
        cursor = editor.textCursor()
        if backward:
            cursor.movePosition(QTextCursor.MoveOperation.End)
        else:
            cursor.movePosition(QTextCursor.MoveOperation.Start)
        editor.setTextCursor(cursor)
        found = (
            editor.find(pattern, flags)
            if pattern is not None
            else editor.find(needle, flags)
        )
        if found:
            self._update_status()
        else:
            self._status_label.setText("Not found")

    # -- replace -----------------------------------------------------------

    def replace(self) -> None:
        editor = self._editor
        needle = self.find_field.text()
        if editor is None or not needle:
            return
        cursor = editor.textCursor()
        if cursor.hasSelection() and self._selection_matches(
            cursor.selectedText(), needle
        ):
            replacement = self._expand_replacement(
                cursor.selectedText(), self.replace_field.text()
            )
            cursor.insertText(replacement)
            editor.setTextCursor(cursor)
        self.find_next()

    def replace_all(self) -> int:
        editor = self._editor
        needle = self.find_field.text()
        if editor is None or not needle:
            return 0
        document = editor.document()
        flags = self._flags()
        pattern = self._regex()
        if pattern is not None and not pattern.isValid():
            self._status_label.setText("Invalid pattern")
            return 0
        count = 0
        cursor = QTextCursor(document)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        while True:
            found = (
                document.find(pattern, cursor, flags)
                if pattern is not None
                else document.find(needle, cursor, flags)
            )
            if found.isNull():
                break
            replacement = self._expand_replacement(
                found.selectedText(), self.replace_field.text()
            )
            found.insertText(replacement)
            count += 1
            cursor = found
        if count:
            self._status_label.setText(f"Replaced {count}")
        else:
            self._status_label.setText("Not found")
        return count

    def replace_in_selection(self) -> int:
        """Replace every match inside the selected text only.

        The selection is replaced as one undoable edit, so Ctrl+Z
        puts it all back. Returns how many were replaced. Nothing
        is selected, nothing happens.
        """
        editor = self._editor
        needle = self.find_field.text()
        if editor is None or not needle:
            return 0
        cursor = editor.textCursor()
        if not cursor.hasSelection():
            self._status_label.setText("Select some text first")
            return 0
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        selected = cursor.selectedText().replace("\u2029", "\n")
        if self._regex_check.isChecked():
            import re

            flags = 0 if self._case_check.isChecked() else re.IGNORECASE
            pattern = self._whole_word_pattern(needle)
            try:
                compiled = re.compile(pattern, flags)
            except re.error:
                self._status_label.setText("Invalid pattern")
                return 0
            matches = list(compiled.finditer(selected))
            if not matches:
                self._status_label.setText("Not found")
                return 0
            replacement = self.replace_field.text()
            new_text = compiled.sub(
                lambda m: m.expand(replacement), selected
            )
            count = len(matches)
        else:
            if self._case_check.isChecked():
                haystack = selected
            else:
                haystack, needle = selected.lower(), needle.lower()
            spans = []
            at = 0
            while True:
                index = haystack.find(needle, at)
                if index < 0:
                    break
                if self._whole_word_check.isChecked() and not (
                    self._is_word_start(selected, index)
                    and self._is_word_end(selected, index + len(needle))
                ):
                    at = index + 1
                    continue
                spans.append((index, index + len(needle)))
                at = index + len(needle)
            if not spans:
                self._status_label.setText("Not found")
                return 0
            replacement = self.replace_field.text()
            new_text = selected
            for s, e in reversed(spans):
                new_text = new_text[:s] + replacement + new_text[e:]
            count = len(spans)
        cursor.beginEditBlock()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(new_text)
        cursor.endEditBlock()
        editor.setTextCursor(cursor)
        self._status_label.setText(f"Replaced {count}")
        return count

    # -- internals ---------------------------------------------------------

    def _whole_word_pattern(self, pattern: str) -> str:
        """Wrap a regex so it only matches whole words, if enabled."""
        if self._whole_word_check.isChecked():
            return r"\b(?:" + pattern + r")\b"
        return pattern

    def _is_word_start(self, text: str, index: int) -> bool:
        """True when index starts a word: the start of the text, or
        the character before it is not a letter, digit, or underscore."""
        if index <= 0:
            return True
        char = text[index - 1]
        return not (char.isalnum() or char == "_")

    def _is_word_end(self, text: str, index: int) -> bool:
        """True when index ends a word: the end of the text, or the
        character at it is not a letter, digit, or underscore."""
        if index >= len(text):
            return True
        char = text[index]
        return not (char.isalnum() or char == "_")

    def _regex(self):
        """The find text as a QRegularExpression, or None if plain text."""
        if not self._regex_check.isChecked():
            return None
        pattern = QRegularExpression(
            self._whole_word_pattern(self.find_field.text())
        )
        if not self._case_check.isChecked():
            pattern.setPatternOptions(
                QRegularExpression.PatternOption.CaseInsensitiveOption
            )
        return pattern

    def _expand_replacement(self, match_text: str, replacement: str) -> str:
        """Expand \\1, \\2 backreferences using the match's groups."""
        if not self._regex_check.isChecked():
            return replacement
        import re

        flags = 0 if self._case_check.isChecked() else re.IGNORECASE
        try:
            compiled = re.compile(self.find_field.text(), flags)
        except re.error:
            return replacement
        match = compiled.search(match_text)
        if match is None:
            return replacement
        try:
            return match.expand(replacement)
        except re.error:
            return replacement

    def _flags(self) -> QTextDocument.FindFlags:
        flags = QTextDocument.FindFlags()
        if self._case_check.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self._whole_word_check.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        return flags

    def _selection_matches(self, selected: str, needle: str) -> bool:
        if self._regex_check.isChecked():
            import re

            flags = 0 if self._case_check.isChecked() else re.IGNORECASE
            try:
                return re.fullmatch(needle, selected, flags) is not None
            except re.error:
                return False
        if self._case_check.isChecked():
            return selected == needle
        return selected.lower() == needle.lower()

    def _matches(self) -> list[tuple[int, int]]:
        """All match spans in the document, in order."""
        editor = self._editor
        needle = self.find_field.text()
        if editor is None or not needle:
            return []
        text = editor.toPlainText()
        if self._regex_check.isChecked():
            import re

            flags = 0 if self._case_check.isChecked() else re.IGNORECASE
            try:
                compiled = re.compile(
                    self._whole_word_pattern(needle), flags
                )
            except re.error:
                return []
            return [
                (m.start(), m.end()) for m in compiled.finditer(text)
            ]
        if self._case_check.isChecked():
            haystack = text
        else:
            haystack, needle = text.lower(), needle.lower()
        spans = []
        start = 0
        while True:
            index = haystack.find(needle, start)
            if index < 0:
                return spans
            if self._whole_word_check.isChecked() and not (
                self._is_word_start(text, index)
                and self._is_word_end(text, index + len(needle))
            ):
                start = index + 1
                continue
            spans.append((index, index + len(needle)))
            start = index + len(needle)

    def _update_find_matches(self) -> None:
        """Highlight every match in the editor (the current match is
        the solid selection, so it stands out). Cleared when the bar
        hides or the find text is empty."""
        if self._editor is None:
            return
        if not self.isVisible() or not self.find_field.text():
            self._editor.set_find_matches([])
            return
        self._editor.set_find_matches(self._matches())

    def _on_find_text_changed(self) -> None:
        if not self.find_field.text():
            self._status_label.setText("")
            self._update_find_matches()
            return
        self.find_next()
        self._update_find_matches()

    def _update_status(self) -> None:
        editor = self._editor
        needle = self.find_field.text()
        if editor is None or not needle:
            self._status_label.setText("")
            return
        spans = self._matches()
        if not spans:
            self._status_label.setText("Not found")
            return
        cursor = editor.textCursor()
        if cursor.hasSelection():
            start = cursor.selectionStart()
            for index, (span_start, _span_end) in enumerate(spans):
                if span_start == start:
                    self._status_label.setText(f"{index + 1} of {len(spans)}")
                    return
        self._status_label.setText(f"{len(spans)} matches")
