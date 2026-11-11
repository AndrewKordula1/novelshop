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
"""Document tabs: one tab per open document.

Each tab holds an Editor and knows which file it belongs to (or None for
an untitled tab). This widget owns opening, saving, closing, and the
dirty marker in each tab's title. The main window just asks it for the
current editor and reacts to document_changed.
"""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFileDialog, QMessageBox, QTabWidget

from novel_shop.editor import Editor
from novel_shop.file_types import file_dialog_filter
from novel_shop.storage import read_text_file, write_text_file


class DocumentTabs(QTabWidget):
    document_changed = Signal()
    status_message = Signal(str)
    add_word_requested = Signal(str)  # word to add to the dictionary
    find_mentions_requested = Signal(str)  # word to find across the project

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(lambda _index: self.document_changed.emit())
        self._editor_font = QFont("Georgia")
        self._editor_font.setPixelSize(15)
        self._line_spacing = 1.0
        self._typewriter = False
        self._first_line_indent = False
        self._show_invisibles = False
        self._focus_sentence = False
        self._line_numbers = False
        self._highlight_rules: list[tuple[str, str]] = []
        self._spell_checker = None
        self._spell_known_words: set[str] = set()
        self._spell_enabled = True
        self._weasel_enabled = True
        self._smart_quotes_enabled = True
        self._auto_capitalize_enabled = True
        self._continue_lists_enabled = True
        self.new_tab()

    # -- tabs ----------------------------------------------------------

    def new_tab(self) -> Editor:
        editor = Editor()
        editor.setFont(self._editor_font)
        editor.set_line_spacing(self._line_spacing)
        editor.set_typewriter_enabled(self._typewriter)
        editor.set_first_line_indent_enabled(self._first_line_indent)
        editor.set_show_invisibles_enabled(self._show_invisibles)
        editor.set_focus_sentence_enabled(self._focus_sentence)
        editor.set_line_numbers_visible(self._line_numbers)
        editor.set_highlight_rules(self._highlight_rules)
        editor.set_spell_checker(self._spell_checker)
        editor.set_spell_known_words(self._spell_known_words)
        editor.set_spell_enabled(self._spell_enabled)
        editor.set_weasel_enabled(self._weasel_enabled)
        editor.set_smart_quotes_enabled(self._smart_quotes_enabled)
        editor.set_auto_capitalize_enabled(self._auto_capitalize_enabled)
        editor.set_continue_lists_enabled(self._continue_lists_enabled)
        editor.add_word_requested.connect(self.add_word_requested.emit)
        editor.find_mentions_requested.connect(
            self.find_mentions_requested.emit
        )
        editor.textChanged.connect(lambda: self._on_editor_changed(editor))
        editor.cursorPositionChanged.connect(lambda: self.document_changed.emit())
        index = self.addTab(editor, "Untitled")
        self.setCurrentIndex(index)
        return editor

    def current_editor(self) -> Editor | None:
        widget = self.currentWidget()
        return widget if isinstance(widget, Editor) else None

    def editors(self) -> list[Editor]:
        """All open editors, in tab order."""
        return [
            self.widget(index)
            for index in range(self.count())
            if isinstance(self.widget(index), Editor)
        ]

    def set_editor_font(self, font: QFont) -> None:
        """Set the writing font for all tabs, and for tabs opened later."""
        self._editor_font = QFont(font)
        for editor in self.editors():
            editor.setFont(self._editor_font)

    def set_line_spacing(self, factor: float) -> None:
        """Set the line spacing for all tabs, and for tabs opened later."""
        self._line_spacing = factor
        for editor in self.editors():
            editor.set_line_spacing(self._line_spacing)

    def set_typewriter_enabled(self, enabled: bool) -> None:
        """Set typewriter scrolling for all tabs, and for tabs opened later."""
        self._typewriter = enabled
        for editor in self.editors():
            editor.set_typewriter_enabled(self._typewriter)

    def set_first_line_indent_enabled(self, enabled: bool) -> None:
        """Set the first-line indent for all tabs, and for tabs opened later."""
        self._first_line_indent = enabled
        for editor in self.editors():
            editor.set_first_line_indent_enabled(self._first_line_indent)

    def set_show_invisibles_enabled(self, enabled: bool) -> None:
        """Set show-invisibles for all tabs, and for tabs opened later."""
        self._show_invisibles = enabled
        for editor in self.editors():
            editor.set_show_invisibles_enabled(self._show_invisibles)

    def set_focus_sentence_enabled(self, enabled: bool) -> None:
        """Set focus-sentence for all tabs, and for tabs opened later."""
        self._focus_sentence = enabled
        for editor in self.editors():
            editor.set_focus_sentence_enabled(self._focus_sentence)

    def set_line_numbers_visible(self, visible: bool) -> None:
        """Set line numbers for all tabs, and for tabs opened later."""
        self._line_numbers = visible
        for editor in self.editors():
            editor.set_line_numbers_visible(self._line_numbers)

    def set_highlight_rules(self, rules: list[tuple[str, str]]) -> None:
        """Set the (term, color) rules for all tabs, and for tabs opened later."""
        self._highlight_rules = list(rules)
        for editor in self.editors():
            editor.set_highlight_rules(self._highlight_rules)

    def set_spell_checker(self, checker) -> None:
        """Set the spell dictionary for all tabs, and for tabs opened later."""
        self._spell_checker = checker
        for editor in self.editors():
            editor.set_spell_checker(self._spell_checker)

    def set_spell_known_words(self, words) -> None:
        """Set the never-flagged words for all tabs, and for tabs opened later."""
        self._spell_known_words = {word.lower() for word in words}
        for editor in self.editors():
            editor.set_spell_known_words(self._spell_known_words)

    def set_spell_enabled(self, enabled: bool) -> None:
        """Turn the spell underlines on or off, for all tabs and later ones."""
        self._spell_enabled = enabled
        for editor in self.editors():
            editor.set_spell_enabled(self._spell_enabled)

    def set_weasel_enabled(self, enabled: bool) -> None:
        """Turn the overused-word underlines on or off, for all tabs and later ones."""
        self._weasel_enabled = enabled
        for editor in self.editors():
            editor.set_weasel_enabled(self._weasel_enabled)

    def set_smart_quotes_enabled(self, enabled: bool) -> None:
        """Turn as-you-type smart quotes on or off, for all tabs and later ones."""
        self._smart_quotes_enabled = enabled
        for editor in self.editors():
            editor.set_smart_quotes_enabled(self._smart_quotes_enabled)

    def set_auto_capitalize_enabled(self, enabled: bool) -> None:
        """Turn as-you-type capitalization on or off, for all tabs and later ones."""
        self._auto_capitalize_enabled = enabled
        for editor in self.editors():
            editor.set_auto_capitalize_enabled(self._auto_capitalize_enabled)

    def set_continue_lists_enabled(self, enabled: bool) -> None:
        """Turn list continuation on or off, for all tabs and later ones."""
        self._continue_lists_enabled = enabled
        for editor in self.editors():
            editor.set_continue_lists_enabled(self._continue_lists_enabled)

    def open_file(self, path: str) -> bool:
        """Open a file in a tab, switching to it if already open."""
        for index in range(self.count()):
            editor = self.widget(index)
            if isinstance(editor, Editor) and editor.file_path == path:
                self.setCurrentIndex(index)
                return True
        ok, text = read_text_file(path)
        if not ok:
            self.status_message.emit(text)
            return False
        editor = self._reusable_tab() or self.new_tab()
        editor.file_path = path
        editor.load_text(text)
        self._refresh_tab_title(editor)
        self.setCurrentWidget(editor)
        return True

    def rename_file(self, old_path: str, new_path: str) -> None:
        """Point any tab open on old_path at new_path instead.

        The on-disk content is unchanged, just under a new name, so
        the tab's saved text (and its dirty state) stay correct.
        """
        for index in range(self.count()):
            editor = self.widget(index)
            if isinstance(editor, Editor) and editor.file_path == old_path:
                editor.file_path = new_path
                self._refresh_tab_title(editor)
                return

    def reload_file(self, path: str) -> bool:
        """Reload an open tab's text from disk, discarding edits.

        Only for a file the caller knows is saved on disk (the
        project search saves tabs before replacing). False if the
        file is not open, or cannot be read.
        """
        for index in range(self.count()):
            editor = self.widget(index)
            if isinstance(editor, Editor) and editor.file_path == path:
                ok, text = read_text_file(path)
                if not ok:
                    return False
                editor.load_text(text)
                editor.mark_saved()
                self._refresh_tab_title(editor)
                return True
        return False

    def close_file(self, path: str) -> bool:
        """Close the tab for path, prompting if it is dirty.

        False if the user cancels the prompt; True if the tab closed
        or was never open.
        """
        for index in range(self.count()):
            editor = self.widget(index)
            if isinstance(editor, Editor) and editor.file_path == path:
                return self.close_tab(index)
        return True

    def open_files(self) -> list[str]:
        """File paths of all open tabs, in tab order."""
        files = []
        for index in range(self.count()):
            editor = self.widget(index)
            if isinstance(editor, Editor) and editor.file_path:
                files.append(editor.file_path)
        return files

    def active_index(self) -> int:
        return self.currentIndex()

    # -- saving ----------------------------------------------------------

    def save_current(self) -> bool:
        editor = self.current_editor()
        return self.save_editor(editor) if editor is not None else False

    def save_current_as(self) -> bool:
        editor = self.current_editor()
        if editor is None:
            return False
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save As",
            "",
            file_dialog_filter(),
        )
        if not path:
            return False
        editor.file_path = path
        return self._write_editor(editor)

    def save_editor(self, editor: Editor) -> bool:
        if editor.file_path is None:
            self.setCurrentWidget(editor)
            return self.save_current_as()
        return self._write_editor(editor)

    def autosave(self) -> int:
        """Save every dirty tab that has a file. Returns how many saved."""
        saved = 0
        for index in range(self.count()):
            editor = self.widget(index)
            if (
                isinstance(editor, Editor)
                and editor.file_path
                and editor.is_dirty()
            ):
                if self._write_editor(editor):
                    saved += 1
        return saved

    def _write_editor(self, editor: Editor) -> bool:
        assert editor.file_path is not None
        ok, message = write_text_file(editor.file_path, editor.current_text())
        if not ok:
            self.status_message.emit(message)
            return False
        editor.mark_saved()
        self._refresh_tab_title(editor)
        self.document_changed.emit()
        return True

    # -- closing ---------------------------------------------------------

    def close_tab(self, index: int, replace_last: bool = True) -> bool:
        editor = self.widget(index)
        if not isinstance(editor, Editor):
            return True
        if not self._maybe_discard(editor):
            return False
        self.removeTab(index)
        if self.count() == 0 and replace_last:
            self.new_tab()
        return True

    def close_current_tab(self) -> bool:
        return self.close_tab(self.currentIndex())

    def close_all(self) -> bool:
        """Close every tab, prompting for dirty ones. False if cancelled."""
        while self.count() > 0:
            if not self.close_tab(self.count() - 1, replace_last=False):
                return False
        return True

    def _maybe_discard(self, editor: Editor) -> bool:
        """True if it is safe to close this tab's document."""
        if not editor.is_dirty():
            return True
        name = Path(editor.file_path).name if editor.file_path else "Untitled"
        answer = QMessageBox.question(
            self,
            "Unsaved changes",
            f"Save changes to {name} before closing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save_editor(editor)
        if answer == QMessageBox.StandardButton.Discard:
            return True
        return False

    # -- internals -------------------------------------------------------

    def _reusable_tab(self) -> Editor | None:
        """The current tab, if it is an empty untitled one."""
        editor = self.current_editor()
        if (
            editor is not None
            and editor.file_path is None
            and editor.current_text() == ""
        ):
            return editor
        return None

    def _refresh_tab_title(self, editor: Editor) -> None:
        index = self.indexOf(editor)
        if index < 0:
            return
        name = Path(editor.file_path).name if editor.file_path else "Untitled"
        dirty = "*" if editor.is_dirty() else ""
        self.setTabText(index, f"{dirty}{name}")

    def _on_editor_changed(self, editor: Editor) -> None:
        self._refresh_tab_title(editor)
        self.document_changed.emit()
