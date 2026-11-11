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
"""File tree (the binder): the left-hand pane, grouped by file type.

Starts empty: nothing appears until a folder is opened. Once a folder
is open, its files appear under section headers — Chapters, Scenes,
Characters, and so on — based on each file's extension (see
novel_shop/file_types.py). An extension with no built-in type gets a
section named after itself, so any niche idea works: a `.spell` file
appears under "Spell". The headers are spacers between sections,
not folders: bold text, no folder icon, collapsible with the arrow,
and open expanded by default.
A section only exists when files of that type are in the folder.
Files stay where they are on disk; only the tree groups them. Only
top-level files with an extension show; subfolders and hidden files
are skipped.
"""

from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QKeySequence,
    QShortcut,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import QHeaderView, QMenu, QTreeView

from novel_shop.file_types import group_for_extension, group_for_unknown_extension, groups_in_order
from novel_shop.icons import file_type_icon
from novel_shop.theme import style_popup_menu
from novel_shop.trash import list_trashed
from novel_shop.wordcount import count_words

# Item data role marking a Trash item (a trashed file, or the Trash
# section header). A file with a .trash extension would make a live
# group also called "Trash", so the section is told apart by this tag,
# not by its header text.
_TRASHED_ROLE = Qt.ItemDataRole.UserRole + 1


class FileTree(QTreeView):
    file_opened = Signal(str)
    file_split_requested = Signal(str)  # open in the split pane
    file_rename_requested = Signal(str)
    file_delete_requested = Signal(str)
    file_duplicate_requested = Signal(str)
    file_restore_requested = Signal(str)
    file_delete_permanently_requested = Signal(str)
    empty_trash_requested = Signal()
    refreshed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._folder: str | None = None
        self._model = QStandardItemModel(self)
        self.setModel(self._model)
        self.setHeaderHidden(True)
        # Column sizing lives in refresh(): the header has no
        # sections until the model does, so modes set here are lost
        # when the model is rebuilt.
        # Word counts, cached by file so a refresh only re-reads
        # files that changed: path -> (mtime, size, words).
        self._word_counts: dict[str, tuple[float, int, int]] = {}
        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(lambda _path: self.refresh())
        self.doubleClicked.connect(self._on_double_clicked)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        rename_shortcut = QShortcut(QKeySequence("F2"), self)
        rename_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        rename_shortcut.activated.connect(self._rename_current)
        delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        delete_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        delete_shortcut.activated.connect(self._delete_current)

    def set_folder(self, folder: str) -> None:
        """Point the tree at a folder. Only that folder's files appear."""
        if not Path(folder).is_dir():
            return
        if self._folder:
            self._watcher.removePaths([self._folder])
        self._folder = folder
        self._watcher.addPath(folder)
        self.refresh()

    def refresh(self) -> None:
        """Rebuild the groups from the folder's current files.

        Sections open expanded by default. A section the user closed
        by hand stays closed across rebuilds.
        """
        if self._folder is None:
            return
        files = self._scan()
        collapsed = {
            self._model.item(row).text()
            for row in range(self._model.rowCount())
            if self._model.item(row) is not None
            and not self.isExpanded(self._model.item(row).index())
        }
        self._model.clear()
        self._model.setHorizontalHeaderLabels(["Name", "Words"])
        # Column sizing: the name column stretches to take whatever
        # space is left, the word-count column stays fixed at 40px.
        # The header has no sections until the model does, and a
        # model rebuild resets the modes to Interactive, so this
        # runs on every refresh. Without it, the header's
        # stretchLastSection default stretches the *last* column
        # (the counts) and squeezes the names down to "...".
        _header = self.header()
        _header.setStretchLastSection(False)
        _header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        _header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(1, 40)
        known_order = groups_in_order()
        order = known_order + sorted(
            group for group in files if group not in known_order
        )
        for group in order:
            files_in_group = files.get(group, [])
            if not files_in_group:
                continue  # a section only exists when its files do
            group_item = QStandardItem(group)
            group_item.setEditable(False)
            # No icon: a section spacer, not a folder.
            font = group_item.font()
            font.setBold(True)
            group_item.setFont(font)
            for path in files_in_group:
                item = QStandardItem(path.name)
                item.setEditable(False)
                item.setIcon(file_type_icon(path.suffix))
                item.setData(str(path), Qt.ItemDataRole.UserRole)
                count_item = QStandardItem(self._word_count_text(path))
                count_item.setEditable(False)
                count_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter
                )
                count_item.setForeground(QColor("#9e9ea6"))
                group_item.appendRow([item, count_item])
            self._model.appendRow(group_item)
            if group not in collapsed:
                self.setExpanded(group_item.index(), True)
        # The Trash section, last: the files in the folder's .trash.
        # It only exists when something is in it, like any section.
        trashed = list_trashed(self._folder)
        if trashed:
            trash_item = QStandardItem("Trash")
            trash_item.setEditable(False)
            trash_item.setData(True, _TRASHED_ROLE)
            font = trash_item.font()
            font.setBold(True)
            trash_item.setFont(font)
            for path in trashed:
                item = QStandardItem(path.name)
                item.setEditable(False)
                item.setIcon(file_type_icon(path.suffix))
                item.setData(str(path), Qt.ItemDataRole.UserRole)
                item.setData(True, _TRASHED_ROLE)
                trash_item.appendRow(item)
            self._model.appendRow(trash_item)
            if "Trash" not in collapsed:
                self.setExpanded(trash_item.index(), True)
        self.refreshed.emit()

    def _word_count_text(self, path: Path) -> str:
        """The file's word count, formatted, cached by mtime/size."""
        key = str(path)
        try:
            stat = path.stat()
        except OSError:
            return ""
        cached = self._word_counts.get(key)
        if cached and cached[0] == stat.st_mtime and cached[1] == stat.st_size:
            return f"{cached[2]:,}"
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""
        words = count_words(text).words
        self._word_counts[key] = (stat.st_mtime, stat.st_size, words)
        return f"{words:,}"

    def _scan(self) -> dict[str, list[Path]]:
        """Top-level files in the folder, grouped by extension.

        Known extensions use their built-in group; any other extension
        gets a section named after itself. A folder that no longer
        exists (deleted out from under the app) reads as empty.
        """
        grouped: dict[str, list[Path]] = {}
        folder = Path(self._folder)
        if not folder.is_dir():
            return grouped
        for child in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_file() or child.name.startswith("."):
                continue
            if not child.suffix:
                continue  # no extension: nothing to categorize by
            group = group_for_extension(child.suffix)
            if group is None:
                group = group_for_unknown_extension(child.suffix)
            grouped.setdefault(group, []).append(child)
        return grouped

    def _on_double_clicked(self, index) -> None:
        if not index.isValid():
            return
        # A trashed file does not open: Restore is the way back.
        if index.data(_TRASHED_ROLE):
            return
        path = index.data(Qt.ItemDataRole.UserRole)
        if path:
            self.file_opened.emit(path)

    def _show_context_menu(self, position) -> None:
        """Right-click menu, different for live and trashed files.

        A live file gets Rename and Delete (Delete moves it to the
        Trash). A trashed file gets Restore and Delete Permanently.
        The Trash section header gets Empty Trash. Other section
        headers have no menu.
        """
        index = self.indexAt(position)
        if not index.isValid():
            return
        path = index.data(Qt.ItemDataRole.UserRole)
        is_trashed = bool(index.data(_TRASHED_ROLE))
        menu = QMenu(self)
        style_popup_menu(menu)
        if path and is_trashed:
            restore_action = menu.addAction("Restore")
            delete_action = menu.addAction("Delete Permanently")
            chosen = menu.exec(self.viewport().mapToGlobal(position))
            if chosen == restore_action:
                self._restore_at(index)
            elif chosen == delete_action:
                self._delete_permanently_at(index)
        elif path:
            open_split_action = menu.addAction("Open in Split")
            rename_action = menu.addAction("Rename...")
            duplicate_action = menu.addAction("Duplicate")
            delete_action = menu.addAction("Delete")
            chosen = menu.exec(self.viewport().mapToGlobal(position))
            if chosen == open_split_action:
                self.file_split_requested.emit(path)
            elif chosen == rename_action:
                self._rename_at(index)
            elif chosen == duplicate_action:
                self.file_duplicate_requested.emit(path)
            elif chosen == delete_action:
                self._delete_at(index)
        elif is_trashed:
            empty_action = menu.addAction("Empty Trash")
            if menu.exec(self.viewport().mapToGlobal(position)) == empty_action:
                self.empty_trash_requested.emit()

    def _rename_at(self, index) -> None:
        """Ask the main window to rename the file at this index."""
        if not index.isValid():
            return
        path = index.data(Qt.ItemDataRole.UserRole)
        if path:
            self.file_rename_requested.emit(path)

    def _rename_current(self) -> None:
        """F2: rename the selected file, if one is selected."""
        self._rename_at(self.currentIndex())

    def _delete_at(self, index) -> None:
        """Ask the main window to move the file at this index to Trash."""
        if not index.isValid():
            return
        path = index.data(Qt.ItemDataRole.UserRole)
        if path and not index.data(_TRASHED_ROLE):
            self.file_delete_requested.emit(path)

    def _delete_current(self) -> None:
        """Delete key: move the selected file to the Trash."""
        self._delete_at(self.currentIndex())

    def _restore_at(self, index) -> None:
        """Ask the main window to restore the trashed file at this index."""
        if not index.isValid():
            return
        path = index.data(Qt.ItemDataRole.UserRole)
        if path and index.data(_TRASHED_ROLE):
            self.file_restore_requested.emit(path)

    def _delete_permanently_at(self, index) -> None:
        """Ask the main window to permanently delete the file at this index."""
        if not index.isValid():
            return
        path = index.data(Qt.ItemDataRole.UserRole)
        if path and index.data(_TRASHED_ROLE):
            self.file_delete_permanently_requested.emit(path)
