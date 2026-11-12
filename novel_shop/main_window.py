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
"""Main window: wires the pieces together.

Layout is a splitter: file tree on the left, document tabs on the
right, status bar along the bottom. This file owns the menus, the
autosave timer, and the window title. Everything else lives in its own
module.
"""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QTimer
from PySide6.QtGui import (
    QActionGroup,
    QFont,
    QKeySequence,
    QShortcut,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from novel_shop.about import AboutDialog
from novel_shop.comments import load_comments, save_comments
from novel_shop.comments_dialog import CommentsDialog
from novel_shop.document_tabs import DocumentTabs
from novel_shop.editor import Editor
from novel_shop.export_dialog import ExportDialog
from novel_shop.exporters import export_docx, export_epub, export_pdf
from novel_shop.file_tree import FileTree
from novel_shop.format_toolbar import FormatToolbar
from novel_shop.highlight_dialog import HighlightDialog
from novel_shop.file_types import file_dialog_filter, unique_path
from novel_shop.find_bar import FindBar
from novel_shop.manuscript import (
    NON_TERM_GROUPS,
    collect_files,
    collect_terms,
    read_blocks,
    term_groups,
)
from novel_shop.new_file_dialog import NewFileDialog
from novel_shop.preferences import load_preferences, save_preferences
from novel_shop.rename_dialog import RenameFileDialog
from novel_shop.lookup_window import LookupWindow
from novel_shop.manuscript_view import ManuscriptView
from novel_shop.piper_read_aloud import PiperReadAloud
from novel_shop.project_spellcheck import ProjectSpellcheckDialog
from novel_shop.project_stats import ProjectStatsDialog
from novel_shop.quick_open import QuickOpenDialog
from novel_shop.read_aloud import ReadAloud
from novel_shop.readability_dialog import ReadabilityDialog
from novel_shop.search_dialog import ProjectSearchDialog
from novel_shop.theme import (
    DEFAULT_CORNER_RADIUS,
    THEME_DARK,
    THEME_LIGHT,
    apply_theme,
    style_popup_menu,
)
from novel_shop.session import load_session, save_session
from novel_shop.snapshot_dialog import SnapshotDialog
from novel_shop.snapshots import create_snapshot
from novel_shop.spellcheck import load_spell_checker
from novel_shop.storage import read_text_file, write_text_file
from novel_shop.trash import (
    empty_trash,
    list_trashed,
    restore_file,
    trash_file,
)
from novel_shop.word_frequency import WordFrequencyDialog
from novel_shop.wordcount import count_words

AUTOSAVE_DELAY_MS = 2000


class MainWindow(QMainWindow):
    def __init__(self, session_path: str | None = None):
        super().__init__()
        # A native window frame on every platform. The frameless
        # custom chrome (a Qt-drawn title bar, caption buttons, edge
        # resizer) did not work with Linux or macOS window managers
        # — the menu bar never appeared there — so all three
        # platforms use the OS title bar and a standard menu bar
        # below it, for one unified look and behaviour.
        # A native window has an OS minimum; keep it resizable to
        # something usable.
        self.setMinimumSize(500, 350)
        self._folder: str | None = None
        self._session_path = session_path

        self._tabs = DocumentTabs()
        self._tree = FileTree()
        self._find_bar = FindBar()
        self._find_bar.hide()
        self._counts_label = QLabel()
        self._file_label = QLabel()

        # Split view: a second editor beside the tabs, for a reference
        # file (a character sheet, a plot outline) while writing.
        self._split_editor = Editor()
        self._split_editor.file_path = None
        self._split_label = QLabel("No file in split view")
        split_close = QPushButton("×")
        split_close.setToolTip("Close split view")
        split_close.clicked.connect(self._close_split)
        split_header = QHBoxLayout()
        split_header.addWidget(self._split_label, 1)
        split_header.addWidget(split_close)
        split_pane_layout = QVBoxLayout()
        split_pane_layout.setContentsMargins(0, 0, 0, 0)
        split_pane_layout.addLayout(split_header)
        split_pane_layout.addWidget(self._split_editor, 1)
        self._split_pane = QWidget()
        self._split_pane.setLayout(split_pane_layout)
        self._split_pane.hide()
        self._split_file: str | None = None
        self._split_was_visible = False

        self._editor_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._editor_splitter.addWidget(self._tabs)
        self._editor_splitter.addWidget(self._split_pane)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self._editor_splitter, 1)
        right_layout.addWidget(self._find_bar)
        self._right_container = right

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._tree)
        splitter.addWidget(right)
        splitter.setSizes([240, 760])
        self._tree.setMinimumWidth(180)
        self._tree.setMaximumWidth(320)
        self.setCentralWidget(splitter)
        self._search_dialog: ProjectSearchDialog | None = None
        self._lookup_window: LookupWindow | None = None
        self._manuscript_view: ManuscriptView | None = None
        self._readability_dialog: ReadabilityDialog | None = None
        self._project_stats_dialog: ProjectStatsDialog | None = None
        self._project_spellcheck_dialog: ProjectSpellcheckDialog | None = None
        self._word_frequency_dialog: WordFrequencyDialog | None = None
        self._read_aloud = ReadAloud()
        self._piper_read_aloud: PiperReadAloud | None = None
        self._focus_mode = False
        self._toolbar_was_visible = True

        status = self.statusBar()
        status.addPermanentWidget(self._counts_label, 1)
        status.addPermanentWidget(self._file_label)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._autosave)

        # Preferences and the spell dictionary first: the menus below
        # read the spellcheck setting and whether a dictionary exists.
        self._preferences = load_preferences()
        # The window's corners are rounded (both Novelshop themes)
        # in the style sheet. A native frame draws its own shape,
        # so the radius here only rounds the menu bar's top corners
        # and the status bar's bottom corners inside the window.
        self._corner_radius = DEFAULT_CORNER_RADIUS
        _theme = self._preferences.get("theme", THEME_LIGHT)
        apply_theme(_theme, self._corner_radius)
        self._spell_checker = load_spell_checker()
        self._piper_read_aloud = PiperReadAloud(
            self._preferences.get("piper_voice_path", "")
        )

        # The menu bar sits below the native title bar, a standard
        # one so the menus work on every platform. It is created
        # before the menus so they are built into it.
        self._menu_bar = QMenuBar(self)
        self.setMenuBar(self._menu_bar)
        self._build_menus()
        # The menu bar's menus, so their corners render rounded.
        for _menu in self._menu_bar.findChildren(QMenu):
            style_popup_menu(_menu)
        self._format_toolbar = FormatToolbar()
        self.addToolBar(self._format_toolbar)
        self._format_toolbar.font_changed.connect(self._on_editor_font_changed)
        self._format_toolbar.bold_triggered.connect(self._toggle_bold)
        self._format_toolbar.italic_triggered.connect(self._toggle_italic)
        self._format_toolbar.underline_triggered.connect(self._toggle_underline)
        self._format_toolbar.strikethrough_triggered.connect(
            self._toggle_strikethrough
        )
        self._format_toolbar.highlight_triggered.connect(
            self._toggle_highlight
        )
        self._format_toolbar.dictionary_requested.connect(
            self._show_lookup_window
        )
        self._apply_editor_font()
        self._apply_line_spacing()
        self._tabs.set_typewriter_enabled(
            self._preferences.get("typewriter", False)
        )
        self._split_editor.set_typewriter_enabled(
            self._preferences.get("typewriter", False)
        )
        self._tabs.set_first_line_indent_enabled(
            self._preferences.get("first_line_indent", False)
        )
        self._split_editor.set_first_line_indent_enabled(
            self._preferences.get("first_line_indent", False)
        )
        self._tabs.set_show_invisibles_enabled(
            self._preferences.get("show_invisibles", False)
        )
        self._split_editor.set_show_invisibles_enabled(
            self._preferences.get("show_invisibles", False)
        )
        self._tabs.set_focus_sentence_enabled(
            self._preferences.get("focus_sentence", False)
        )
        self._split_editor.set_focus_sentence_enabled(
            self._preferences.get("focus_sentence", False)
        )
        self._tabs.set_line_numbers_visible(
            self._preferences.get("line_numbers", False)
        )
        self._split_editor.set_line_numbers_visible(
            self._preferences.get("line_numbers", False)
        )
        self._tabs.set_spell_checker(self._spell_checker)
        self._tabs.set_spell_enabled(
            self._preferences.get("spellcheck_enabled", True)
        )
        self._tabs.set_weasel_enabled(
            self._preferences.get("weasel_enabled", True)
        )
        self._tabs.set_smart_quotes_enabled(
            self._preferences.get("smart_quotes", True)
        )
        self._tabs.set_auto_capitalize_enabled(
            self._preferences.get("auto_capitalize", True)
        )
        self._tabs.set_continue_lists_enabled(
            self._preferences.get("continue_lists", True)
        )
        self._split_editor.set_spell_checker(self._spell_checker)
        self._split_editor.set_spell_enabled(
            self._preferences.get("spellcheck_enabled", True)
        )
        self._split_editor.set_weasel_enabled(
            self._preferences.get("weasel_enabled", True)
        )
        self._split_editor.set_smart_quotes_enabled(
            self._preferences.get("smart_quotes", True)
        )
        self._split_editor.set_auto_capitalize_enabled(
            self._preferences.get("auto_capitalize", True)
        )
        self._split_editor.set_continue_lists_enabled(
            self._preferences.get("continue_lists", True)
        )
        self._split_editor.textChanged.connect(self._on_document_changed)
        self._split_editor.add_word_requested.connect(
            self._add_word_to_dictionary
        )
        self._split_editor.find_mentions_requested.connect(
            self._find_mentions
        )
        self._tabs.add_word_requested.connect(self._add_word_to_dictionary)
        self._tabs.find_mentions_requested.connect(self._find_mentions)
        self._tree.refreshed.connect(self._rebuild_highlights)
        bold_shortcut = QShortcut(QKeySequence("Ctrl+B"), self)
        bold_shortcut.activated.connect(self._toggle_bold)
        italic_shortcut = QShortcut(QKeySequence("Ctrl+I"), self)
        italic_shortcut.activated.connect(self._toggle_italic)
        underline_shortcut = QShortcut(QKeySequence("Ctrl+U"), self)
        underline_shortcut.activated.connect(self._toggle_underline)
        strike_shortcut = QShortcut(QKeySequence("Ctrl+Shift+X"), self)
        strike_shortcut.activated.connect(self._toggle_strikethrough)
        highlight_shortcut = QShortcut(QKeySequence("Ctrl+Shift+H"), self)
        highlight_shortcut.activated.connect(self._toggle_highlight)
        regular_shortcut = QShortcut(QKeySequence("Ctrl+Space"), self)
        regular_shortcut.activated.connect(self._clear_formatting)
        zoom_in_shortcut = QShortcut(QKeySequence("Ctrl+="), self)
        zoom_in_shortcut.activated.connect(self._zoom_in)
        zoom_out_shortcut = QShortcut(QKeySequence("Ctrl+-"), self)
        zoom_out_shortcut.activated.connect(self._zoom_out)
        zoom_reset_shortcut = QShortcut(QKeySequence("Ctrl+0"), self)
        zoom_reset_shortcut.activated.connect(self._zoom_reset)
        paste_plain_shortcut = QShortcut(QKeySequence("Ctrl+Shift+V"), self)
        paste_plain_shortcut.activated.connect(self._paste_plain_text)
        duplicate_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        duplicate_shortcut.activated.connect(self._duplicate_paragraph)
        move_up_shortcut = QShortcut(QKeySequence("Alt+Up"), self)
        move_up_shortcut.activated.connect(
            lambda: self._move_paragraph(-1)
        )
        move_down_shortcut = QShortcut(QKeySequence("Alt+Down"), self)
        move_down_shortcut.activated.connect(
            lambda: self._move_paragraph(1)
        )
        align_left_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        align_left_shortcut.activated.connect(
            lambda: self._set_alignment("left")
        )
        align_center_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        align_center_shortcut.activated.connect(
            lambda: self._set_alignment("center")
        )
        align_right_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        align_right_shortcut.activated.connect(
            lambda: self._set_alignment("right")
        )
        align_justify_shortcut = QShortcut(QKeySequence("Ctrl+J"), self)
        align_justify_shortcut.activated.connect(
            lambda: self._set_alignment("justify")
        )
        comments_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        comments_shortcut.activated.connect(self._show_comments)
        self._tabs.document_changed.connect(self._on_document_changed)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._tabs.status_message.connect(
            lambda message: self.statusBar().showMessage(message, 5000)
        )
        self._tree.file_opened.connect(self.open_file)
        self._tree.file_split_requested.connect(self._show_split_file)
        self._tree.file_rename_requested.connect(self._show_rename_dialog)
        self._tree.file_delete_requested.connect(self._delete_file)
        self._tree.file_duplicate_requested.connect(self._duplicate_file)
        self._tree.file_restore_requested.connect(self._restore_file)
        self._tree.file_delete_permanently_requested.connect(
            self._delete_permanently
        )
        self._tree.empty_trash_requested.connect(self._empty_trash)

        self.resize(1000, 700)
        self._update_title()
        self._update_status()
        self._file_label.setText("Open a folder to begin")
        self._restore_session()

    # -- session ---------------------------------------------------------

    def _restore_session(self) -> None:
        """Reopen the last folder and files from the last run, if still there."""
        session = load_session(self._session_path)
        folder = session.get("folder")
        if folder and Path(folder).is_dir():
            self._folder = folder
            self._tree.set_folder(folder)
            self._file_label.setText(folder)
            self._record_recent_folder(folder)
        files = session.get("files") or []
        active = session.get("active") or 0
        for path in files:
            if Path(path).is_file():
                self._tabs.open_file(path)
        if 0 <= active < self._tabs.count():
            self._tabs.setCurrentIndex(active)
        self._update_title()
        self._update_status()
        editor = self._tabs.current_editor()
        if editor is not None and editor.file_path:
            self._file_label.setText(editor.file_path)

    # -- menus -----------------------------------------------------------

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("New File...", "Ctrl+Shift+N", self._show_new_file_dialog)
        file_menu.addAction("Open Folder...", "Ctrl+Shift+O", self.open_folder)
        file_menu.addAction("Open File...", "Ctrl+O", self.open_file_dialog)
        file_menu.addAction("Quick Open...", "Ctrl+P", self._show_quick_open)
        file_menu.addAction("Save", "Ctrl+S", self.save_file)
        file_menu.addAction("Save As...", "Ctrl+Shift+S", self.save_file_as)
        file_menu.addAction("Take Snapshot", "Ctrl+Shift+T", self.take_snapshot)
        file_menu.addAction("Snapshots...", self.show_snapshots)
        file_menu.addAction("Export...", "Ctrl+E", self._export)
        file_menu.addAction(
            "Export Current File...", self._export_current_file
        )
        file_menu.addAction("Close Tab", "Ctrl+W", self._tabs.close_current_tab)
        file_menu.addAction("Back Up Project...", self._backup_project)
        self._recent_folders_menu = file_menu.addMenu("Recent Folders")
        self._recent_folders_menu.aboutToShow.connect(
            self._refresh_recent_folders_menu
        )
        file_menu.addSeparator()
        file_menu.addAction("Quit", "Ctrl+Q", self.close)

        edit_menu = self.menuBar().addMenu("&Edit")
        edit_menu.addAction("Find...", "Ctrl+F", self._show_find)
        edit_menu.addAction("Replace...", "Ctrl+H", self._show_replace)
        # A lambda, not the method itself: the action passes a
        # "checked" bool, which would land in _show_project_search's
        # query parameter.
        edit_menu.addAction(
            "Find in Project...",
            "Ctrl+Shift+F",
            lambda: self._show_project_search(),
        )
        edit_menu.addAction("Go to Line...", "Ctrl+G", self._go_to_line)
        edit_menu.addAction(
            "Go to Heading...", "Ctrl+Shift+G", self._go_to_heading
        )
        edit_menu.addAction(
            "Toggle Bookmark", "Ctrl+F2", self._toggle_bookmark
        )
        edit_menu.addAction(
            "Go to Bookmark", "Shift+F2", self._go_to_bookmark
        )
        edit_menu.addSeparator()
        insert_menu = edit_menu.addMenu("Insert")
        insert_menu.addAction(
            "Scene Break",
            "Ctrl+Shift+Return",
            self._insert_scene_break,
        )
        insert_menu.addAction(
            "Heading",
            "Ctrl+1",
            lambda: self._insert_heading(1),
        )
        insert_menu.addAction(
            "Subheading",
            "Ctrl+2",
            lambda: self._insert_heading(2),
        )
        insert_menu.addAction(
            "Block Quote",
            lambda: self._insert_block_quote(),
        )
        edit_menu.addAction(
            "Comments…", "Ctrl+Shift+C", self._show_comments
        )
        edit_menu.addAction(
            "Copy as Plain Text", self._copy_plain_text
        )
        edit_menu.addAction(
            "Split File at Cursor", self._split_file_at_cursor
        )
        edit_menu.addAction(
            "Merge Files...", self._merge_file
        )
        edit_menu.addAction(
            "Join Paragraph", "Ctrl+Shift+J", self._join_paragraph
        )
        edit_menu.addAction(
            "Select All Occurrences",
            "Ctrl+Shift+L",
            self._select_all_occurrences,
        )

        format_menu = self.menuBar().addMenu("Fo&rmat")
        align_menu = format_menu.addMenu("Align")
        align_menu.addAction(
            "Left", "Ctrl+L", lambda: self._set_alignment("left")
        )
        align_menu.addAction(
            "Center", "Ctrl+E", lambda: self._set_alignment("center")
        )
        align_menu.addAction(
            "Right", "Ctrl+R", lambda: self._set_alignment("right")
        )
        align_menu.addAction(
            "Justify", "Ctrl+J", lambda: self._set_alignment("justify")
        )
        case_menu = format_menu.addMenu("Change Case")
        case_menu.addAction(
            "UPPERCASE", lambda: self._change_case("upper")
        )
        case_menu.addAction(
            "lowercase", lambda: self._change_case("lower")
        )
        case_menu.addAction(
            "Title Case", lambda: self._change_case("title")
        )
        case_menu.addAction(
            "Sentence case", lambda: self._change_case("sentence")
        )
        format_menu.addSeparator()
        spacing_menu = format_menu.addMenu("Line Spacing")
        spacing_group = QActionGroup(self)
        spacing_group.setExclusive(True)
        self._spacing_actions: dict[float, object] = {}
        for factor, label in (
            (1.0, "Single"),
            (1.5, "1.5 Lines"),
            (2.0, "Double"),
        ):
            action = spacing_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(
                self._preferences.get("line_spacing", 1.0) == factor
            )
            action.triggered.connect(
                lambda _checked=False, f=factor: self._set_line_spacing(f)
            )
            spacing_group.addAction(action)
            self._spacing_actions[factor] = action
        self._typewriter_action = format_menu.addAction(
            "Typewriter Scrolling"
        )
        self._typewriter_action.setCheckable(True)
        self._typewriter_action.setChecked(
            self._preferences.get("typewriter", False)
        )
        self._typewriter_action.setToolTip(
            "Keep the line being typed centered on screen"
        )
        self._typewriter_action.triggered.connect(self._toggle_typewriter)
        self._indent_action = format_menu.addAction("First-Line Indent")
        self._indent_action.setCheckable(True)
        self._indent_action.setChecked(
            self._preferences.get("first_line_indent", False)
        )
        self._indent_action.setToolTip(
            "Indent the first line of each paragraph, like a printed novel"
        )
        self._indent_action.triggered.connect(self._toggle_first_line_indent)
        self._invisibles_action = format_menu.addAction("Show Invisibles ¶")
        self._invisibles_action.setCheckable(True)
        self._invisibles_action.setChecked(
            self._preferences.get("show_invisibles", False)
        )
        self._invisibles_action.setToolTip(
            "Show spaces, tabs, and paragraph marks"
        )
        self._invisibles_action.triggered.connect(
            self._toggle_show_invisibles
        )
        self._focus_sentence_action = format_menu.addAction("Focus Sentence")
        self._focus_sentence_action.setCheckable(True)
        self._focus_sentence_action.setChecked(
            self._preferences.get("focus_sentence", False)
        )
        self._focus_sentence_action.setToolTip(
            "Dim everything except the sentence being written"
        )
        self._focus_sentence_action.triggered.connect(
            self._toggle_focus_sentence
        )
        self._line_numbers_action = format_menu.addAction("Line Numbers")
        self._line_numbers_action.setCheckable(True)
        self._line_numbers_action.setChecked(
            self._preferences.get("line_numbers", False)
        )
        self._line_numbers_action.setToolTip(
            "Show a line-number margin on the left of the editor"
        )
        self._line_numbers_action.triggered.connect(
            self._toggle_line_numbers
        )
        format_menu.addSeparator()
        self._smart_quotes_action = format_menu.addAction("Smart Quotes")
        self._smart_quotes_action.setCheckable(True)
        self._smart_quotes_action.setChecked(
            self._preferences.get("smart_quotes", True)
        )
        self._smart_quotes_action.setToolTip(
            "Straight quotes become curly ones as you type, "
            "and -- becomes an em dash"
        )
        self._smart_quotes_action.triggered.connect(
            self._toggle_smart_quotes
        )
        self._auto_capitalize_action = format_menu.addAction(
            "Auto-Capitalize Sentences"
        )
        self._auto_capitalize_action.setCheckable(True)
        self._auto_capitalize_action.setChecked(
            self._preferences.get("auto_capitalize", True)
        )
        self._auto_capitalize_action.setToolTip(
            "Capitalize the first letter of a sentence as you type"
        )
        self._auto_capitalize_action.triggered.connect(
            self._toggle_auto_capitalize
        )
        self._continue_lists_action = format_menu.addAction(
            "Continue Lists on Enter"
        )
        self._continue_lists_action.setCheckable(True)
        self._continue_lists_action.setChecked(
            self._preferences.get("continue_lists", True)
        )
        self._continue_lists_action.setToolTip(
            "Enter on a list item starts the next one; an empty item ends the list"
        )
        self._continue_lists_action.triggered.connect(
            self._toggle_continue_lists
        )
        format_menu.addAction("Fix Typography", self._fix_typography)
        format_menu.addSeparator()
        format_menu.addAction(
            "Highlight Colors...", self._show_highlight_colors
        )
        self._weasel_action = format_menu.addAction("Overused Words")
        self._weasel_action.setCheckable(True)
        self._weasel_action.setChecked(
            self._preferences.get("weasel_enabled", True)
        )
        self._weasel_action.setToolTip(
            "Underline filler words like very, just, really"
        )
        self._weasel_action.triggered.connect(self._toggle_weasel)
        self._toolbar_action = format_menu.addAction("Formatting Toolbar")
        self._toolbar_action.setCheckable(True)
        self._toolbar_action.setChecked(True)
        self._toolbar_action.triggered.connect(self._toggle_format_toolbar)

        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction("Manuscript", "Ctrl+Shift+M", self._show_manuscript_view)
        view_menu.addAction("Readability...", self._show_readability)
        view_menu.addAction(
            "Project Word Count...", self._show_project_stats
        )
        view_menu.addAction(
            "Project Spellcheck...", self._show_project_spellcheck
        )
        view_menu.addAction(
            "Word Frequency...", self._show_word_frequency
        )
        view_menu.addAction(
            "Next File", "Ctrl+PgDown", lambda: self._step_file(1)
        )
        view_menu.addAction(
            "Previous File", "Ctrl+PgUp", lambda: self._step_file(-1)
        )
        self._spellcheck_action = view_menu.addAction("Spellcheck")
        self._spellcheck_action.setCheckable(True)
        self._spellcheck_action.setChecked(
            self._preferences.get("spellcheck_enabled", True)
        )
        self._spellcheck_action.setEnabled(self._spell_checker is not None)
        if self._spell_checker is None:
            self._spellcheck_action.setToolTip(
                "Install pyspellchecker to enable spellcheck"
            )
        self._spellcheck_action.triggered.connect(self._toggle_spellcheck)
        self._focus_action = view_menu.addAction("Focus Mode", "F11")
        self._focus_action.setCheckable(True)
        self._focus_action.setChecked(False)
        self._focus_action.triggered.connect(self._toggle_focus_mode)
        self._split_action = view_menu.addAction("Split View", "Ctrl+\\")
        self._split_action.setCheckable(True)
        self._split_action.setChecked(False)
        self._split_action.triggered.connect(self._toggle_split_view)
        self._read_action = view_menu.addAction("Read Aloud", "Ctrl+Shift+R")
        self._read_action.setCheckable(True)
        self._read_action.setChecked(False)
        self._read_action.setEnabled(
            self._read_aloud.available
            or self._piper_read_aloud.available
        )
        if not self._read_aloud.available:
            self._read_action.setToolTip(
                "Text-to-speech is not in this Qt build"
            )
        self._read_action.triggered.connect(self._toggle_read_aloud)
        self._read_aloud.finished.connect(self._on_read_aloud_finished)
        self._piper_read_aloud.finished.connect(
            self._on_read_aloud_finished
        )
        voice_menu = view_menu.addMenu("Read Aloud Voice")
        engine_group = QActionGroup(self)
        engine_group.setExclusive(True)
        self._system_voice_action = voice_menu.addAction("System voices")
        self._system_voice_action.setCheckable(True)
        self._system_voice_action.setChecked(
            self._preferences.get("read_aloud_engine", "system") == "system"
        )
        self._system_voice_action.triggered.connect(
            lambda: self._set_read_aloud_engine("system")
        )
        engine_group.addAction(self._system_voice_action)
        self._piper_voice_action = voice_menu.addAction("Piper (neural)")
        self._piper_voice_action.setCheckable(True)
        self._piper_voice_action.setChecked(
            self._preferences.get("read_aloud_engine", "system") == "piper"
        )
        if not self._piper_read_aloud.available:
            self._piper_voice_action.setToolTip(
                "Install piper-tts and choose a voice file to use Piper"
            )
        self._piper_voice_action.triggered.connect(
            lambda: self._set_read_aloud_engine("piper")
        )
        engine_group.addAction(self._piper_voice_action)
        voice_menu.addSeparator()
        voice_menu.addAction(
            "Choose Piper voice file...",
            self._choose_piper_voice,
        )
        theme_menu = view_menu.addMenu("Theme")
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        self._light_theme_action = theme_menu.addAction("Novelshop Light")
        self._light_theme_action.setCheckable(True)
        self._light_theme_action.setChecked(
            self._preferences.get("theme", THEME_LIGHT) == THEME_LIGHT
        )
        self._light_theme_action.setToolTip(
            "A white writing surface with light grey chrome"
        )
        self._light_theme_action.triggered.connect(
            lambda: self._set_theme(THEME_LIGHT)
        )
        theme_group.addAction(self._light_theme_action)
        self._dark_theme_action = theme_menu.addAction("Novelshop Dark")
        self._dark_theme_action.setCheckable(True)
        self._dark_theme_action.setChecked(
            self._preferences.get("theme", THEME_LIGHT) == THEME_DARK
        )
        self._dark_theme_action.setToolTip(
            "Dark, in the style of Photoshop and the Creative Cloud apps"
        )
        self._dark_theme_action.triggered.connect(
            lambda: self._set_theme(THEME_DARK)
        )
        theme_group.addAction(self._dark_theme_action)

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction("About Novelshop...", self._show_about)

    # -- file operations ---------------------------------------------------

    def _show_new_file_dialog(self) -> None:
        if not self._folder:
            self.statusBar().showMessage(
                "Open a folder first to create a file", 5000
            )
            return
        dialog = NewFileDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._new_typed_file(dialog.extension, dialog.file_name)

    def _show_rename_dialog(self, path: str) -> None:
        """Rename a file in the tree, name and type."""
        if not self._folder:
            return
        dialog = RenameFileDialog(self._folder, path, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        new_path = str(
            Path(self._folder) / f"{dialog.file_name}.{dialog.extension}"
        )
        if new_path == path:
            return  # nothing changed
        self._rename_file(path, new_path)

    def _rename_file(self, old_path: str, new_path: str) -> None:
        """Move the file on disk and point everything at the new name.

        Snapshots need nothing: they are timestamp-named in the
        folder's .snapshots, not named after the file. The tree refresh
        rebuilds the sections, so a type change moves the file — and
        its highlight term, if it had one — to the right place.
        """
        try:
            Path(old_path).rename(new_path)
        except OSError as exc:
            self.statusBar().showMessage(f"Could not rename: {exc}", 5000)
            return
        self._tabs.rename_file(old_path, new_path)
        self._tree.refresh()
        editor = self._tabs.current_editor()
        if editor is not None and editor.file_path:
            self._file_label.setText(editor.file_path)
        self._update_title()
        self._update_status()
        self.statusBar().showMessage(
            f"Renamed to {Path(new_path).name}", 5000
        )

    # -- trash -------------------------------------------------------------

    def _delete_file(self, path: str) -> None:
        """Move a file to the project's Trash folder. No confirmation:
        it is recoverable with Restore, so deleting is one click."""
        if not self._folder:
            return
        # Close its tab first, so a dirty file prompts to save and the
        # trashed copy is up to date; a Cancel leaves it alone.
        if not self._tabs.close_file(path):
            return
        ok, result = trash_file(self._folder, path)
        if not ok:
            self.statusBar().showMessage(result, 5000)
            return
        self._tree.refresh()
        self._update_title()
        self._update_status()
        self.statusBar().showMessage(
            f"Moved {Path(path).name} to Trash", 5000
        )

    def _duplicate_file(self, path: str) -> None:
        """Copy a file, for trying a rewrite without losing the
        original. The copy is named "<name> copy" (numbered when
        taken), opens in a tab, and takes the original's comments
        sidecar with it when there is one.
        """
        import shutil

        from novel_shop.comments import comments_path
        from novel_shop.file_types import unique_path

        if not self._folder:
            return
        source = Path(path)
        target = Path(
            unique_path(
                self._folder,
                f"{source.stem} copy",
                source.suffix.lstrip("."),
            )
        )
        try:
            shutil.copy2(source, target)
        except OSError as exc:
            self.statusBar().showMessage(
                f"Could not duplicate {source.name}: {exc}", 5000
            )
            return
        sidecar = Path(comments_path(path))
        if sidecar.exists():
            try:
                shutil.copy2(sidecar, comments_path(str(target)))
            except OSError:
                pass
        self._tree.refresh()
        self._tabs.open_file(str(target))
        self.statusBar().showMessage(
            f"Duplicated as {target.name}", 5000
        )

    def _restore_file(self, trashed_path: str) -> None:
        """Move a trashed file back to the folder."""
        if not self._folder:
            return
        ok, result = restore_file(self._folder, trashed_path)
        if not ok:
            self.statusBar().showMessage(result, 5000)
            return
        self._tree.refresh()
        self._update_title()
        self._update_status()
        self.statusBar().showMessage(
            f"Restored {Path(result).name}", 5000
        )

    def _delete_permanently(self, path: str) -> None:
        """Permanently delete one trashed file. This one asks first."""
        answer = QMessageBox.warning(
            self,
            "Delete permanently",
            f"Permanently delete '{Path(path).name}'?\n"
            "This can't be undone.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            Path(path).unlink()
        except OSError as exc:
            self.statusBar().showMessage(f"Could not delete: {exc}", 5000)
            return
        self._tree.refresh()
        self.statusBar().showMessage(
            f"Deleted {Path(path).name}", 5000
        )

    def _empty_trash(self) -> None:
        """Permanently delete everything in the Trash. Asks first."""
        if not self._folder:
            return
        trashed = list_trashed(self._folder)
        if not trashed:
            return
        answer = QMessageBox.warning(
            self,
            "Empty Trash",
            f"Permanently delete {len(trashed)} file(s) in the Trash?\n"
            "This can't be undone.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        count, errors = empty_trash(self._folder)
        self._tree.refresh()
        message = f"Emptied Trash ({count} file(s))"
        if errors:
            message += f" — {len(errors)} could not be deleted"
        self.statusBar().showMessage(message, 5000)

    def _new_typed_file(self, extension: str, stem: str = "Untitled") -> None:
        """Create an empty file of a type in the open folder, and open it."""
        if not self._folder:
            self.statusBar().showMessage(
                "Open a folder first to create a file", 5000
            )
            return
        path = unique_path(self._folder, stem, extension)
        ok, message = write_text_file(path, "")
        if not ok:
            self.statusBar().showMessage(message, 5000)
            return
        self._tree.refresh()
        self.open_file(path)

    def _folder_dialog(self) -> QFileDialog:
        """Folder picker that shows the folder's text files.

        Qt's own dialog, not the native one: the native folder picker
        hides files, so the folder looks empty. This one lists them.
        """
        dialog = QFileDialog(self, "Open Folder")
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setNameFilters(file_dialog_filter().split(";;"))
        if self._folder:
            dialog.setDirectory(self._folder)
        else:
            # No folder open yet: start in Documents, where stories live.
            documents = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.DocumentsLocation
            )
            if documents:
                dialog.setDirectory(documents)
        return dialog

    def open_folder(self) -> None:
        dialog = self._folder_dialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            folders = dialog.selectedFiles()
            if folders:
                folder = folders[0]
                self._folder = folder
                self._tree.set_folder(folder)
                self._file_label.setText(folder)
                self._record_recent_folder(folder)

    def _record_recent_folder(self, folder: str) -> None:
        """Remember a folder in the Recent Folders list (newest
        first, at most five)."""
        recent = [
            f
            for f in self._preferences.get("recent_folders", [])
            if f != folder
        ]
        recent.insert(0, folder)
        self._preferences["recent_folders"] = recent[:5]
        save_preferences(self._preferences)

    def _refresh_recent_folders_menu(self) -> None:
        """Rebuild the Recent Folders submenu from the saved list,
        each time it is about to open, so it is always current."""
        menu = self._recent_folders_menu
        menu.clear()
        recent = [
            folder
            for folder in self._preferences.get("recent_folders", [])
            if Path(folder).is_dir()
        ]
        if not recent:
            action = menu.addAction("(no recent folders)")
            action.setEnabled(False)
            return
        for folder in recent:
            action = menu.addAction(Path(folder).name)
            action.setData(folder)
            action.triggered.connect(
                lambda _checked=False, f=folder: self._open_recent_folder(f)
            )

    def _open_recent_folder(self, folder: str) -> None:
        """Open a folder from the Recent Folders list."""
        if not Path(folder).is_dir():
            self.statusBar().showMessage(
                f"Folder no longer exists: {folder}", 5000
            )
            return
        self._folder = folder
        self._tree.set_folder(folder)
        self._file_label.setText(folder)
        self._record_recent_folder(folder)

    def _backup_project(self) -> None:
        """Zip the whole project folder, as a safety net for the
        book. The user picks where the zip goes; it includes the
        documents, snapshots, and Trash, but not __pycache__.
        """
        import zipfile
        from datetime import datetime

        if not self._folder:
            self.statusBar().showMessage(
                "Open a folder first to back it up", 5000
            )
            return
        folder = Path(self._folder)
        default_name = (
            f"{folder.name}_{datetime.now():%Y-%m-%d_%H%M}.zip"
        )
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Back Up Project",
            str(folder.parent / default_name),
            "Zip files (*.zip)",
        )
        if not target:
            return
        if not target.endswith(".zip"):
            target += ".zip"
        try:
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in sorted(folder.rglob("*")):
                    if "__pycache__" in path.parts:
                        continue
                    if path.is_file():
                        zf.write(path, path.relative_to(folder.parent))
        except OSError as exc:
            self.statusBar().showMessage(
                f"Could not write the backup: {exc}", 5000
            )
            return
        self.statusBar().showMessage(
            f"Backed up to {Path(target).name}", 5000
        )

    def open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            file_dialog_filter(),
        )
        if path:
            self.open_file(path)

    def _show_quick_open(self) -> None:
        """Quick Open: jump to a file in the folder by typing its name."""
        if not self._folder:
            self.statusBar().showMessage(
                "Open a folder first to jump to a file", 5000
            )
            return
        dialog = QuickOpenDialog(collect_files(self._folder), self)
        dialog.focus_filter()
        if (
            dialog.exec() == QDialog.DialogCode.Accepted
            and dialog.selected_path is not None
        ):
            self.open_file(dialog.selected_path)

    def open_file(self, path: str) -> None:
        if self._tabs.open_file(path):
            self._file_label.setText(path)
        self._update_title()
        self._update_status()

    def save_file(self) -> bool:
        if self._tabs.save_current():
            editor = self._tabs.current_editor()
            if editor is not None and editor.file_path:
                self._file_label.setText(editor.file_path)
            return True
        return False

    def save_file_as(self) -> bool:
        if self._tabs.save_current_as():
            editor = self._tabs.current_editor()
            if editor is not None and editor.file_path:
                self._file_label.setText(editor.file_path)
            self._tree.refresh()
            return True
        return False

    # -- snapshots ---------------------------------------------------------

    def take_snapshot(self) -> None:
        editor = self._tabs.current_editor()
        if editor is None or editor.file_path is None:
            self.statusBar().showMessage(
                "Save the document first to take a snapshot", 5000
            )
            return
        ok, result = create_snapshot(editor.file_path, editor.current_text())
        if ok:
            self.statusBar().showMessage("Snapshot saved", 5000)
        else:
            self.statusBar().showMessage(result, 5000)

    def show_snapshots(self) -> None:
        editor = self._tabs.current_editor()
        if editor is None or editor.file_path is None:
            self.statusBar().showMessage(
                "Save the document first to view snapshots", 5000
            )
            return
        dialog = SnapshotDialog(
            editor.file_path, editor.current_text(), self
        )
        if (
            dialog.exec() == QDialog.DialogCode.Accepted
            and dialog.restored_text is not None
        ):
            # Load as unsaved changes, and hold autosave off so nothing is
            # written until the user saves or edits further.
            editor.replace_text(dialog.restored_text)
            self._autosave_timer.stop()
            self.statusBar().showMessage(
                "Snapshot restored — press Ctrl+S to keep it", 5000
            )

    def _export(self) -> None:
        """Export the manuscript as DOCX, EPUB, or PDF."""
        if not self._folder:
            self.statusBar().showMessage(
                "Open a folder first to export", 5000
            )
            return
        self._tabs.autosave()  # save unsaved changes first, so none are missed
        files = collect_files(self._folder)
        if not files:
            self.statusBar().showMessage(
                "Nothing to export in this folder", 5000
            )
            return
        self._run_export(files, Path(self._folder).name)

    def _export_current_file(self) -> None:
        """Export only the document you are working in.

        The same dialog, with just this one file in it — ticked,
        whatever its type — and the title defaulting to the file's
        name. A file that was never saved has nothing on disk to
        export, so it asks to be saved first.
        """
        editor = self._focused_editor()
        if editor is None or not editor.file_path:
            self.statusBar().showMessage(
                "Save the file first to export it", 5000
            )
            return
        self._tabs.autosave()
        if editor is self._split_editor:
            self._save_split_editor()
        path = editor.file_path
        files = [
            file for file in collect_files(self._folder)
            if file.path == path
        ]
        if not files:
            # Opened from outside the folder (or an unknown type):
            # build its entry from the path itself.
            from novel_shop.file_types import (
                group_for_extension,
                group_for_unknown_extension,
            )
            from novel_shop.manuscript import ManuscriptFile

            extension = Path(path).suffix.lower().lstrip(".")
            group = group_for_extension(extension)
            if group is None:
                group = group_for_unknown_extension(extension)
            files = [
                ManuscriptFile(
                    path=path,
                    title=Path(path).stem,
                    group=group,
                    level=1 if extension in ("part", "chapter") else 2,
                    include_by_default=False,
                )
            ]
        self._run_export(
            files, Path(path).stem, check_all=True
        )

    def _run_export(
        self,
        files: list,
        default_title: str,
        check_all: bool = False,
    ) -> None:
        """The Export dialog, then the save prompt and the file write."""
        dialog = ExportDialog(
            files, default_title, self, check_all=check_all
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        blocks, skipped = read_blocks(dialog.selected_files)
        if not blocks:
            self.statusBar().showMessage("Nothing to export", 5000)
            return
        filters = {
            "docx": "Word documents (*.docx)",
            "epub": "EPUB ebooks (*.epub)",
            "pdf": "PDF files (*.pdf)",
        }
        default_path = str(
            Path(self._folder) / f"{dialog.title}.{dialog.format}"
        )
        path, _selected = QFileDialog.getSaveFileName(
            self, "Export", default_path, filters[dialog.format]
        )
        if not path:
            return
        writers = {
            "docx": export_docx,
            "epub": export_epub,
            "pdf": export_pdf,
        }
        try:
            writers[dialog.format](
                blocks, dialog.title, dialog.author, path
            )
        except Exception as exc:
            self.statusBar().showMessage(f"Export failed: {exc}", 8000)
            return
        message = f"Exported {path}"
        if skipped:
            message += f" — skipped {len(skipped)} unreadable file(s)"
        self.statusBar().showMessage(message, 8000)

    # -- find ------------------------------------------------------------

    def _show_find(self) -> None:
        self._find_bar.show_for(self._focused_editor())

    def _show_replace(self) -> None:
        self._find_bar.show_for(self._focused_editor(), focus_replace=True)

    def _go_to_line(self) -> None:
        """Jump to a line number in the editor you are working in."""
        editor = self._focused_editor()
        if editor is None:
            return
        total = editor.line_count()
        line, ok = QInputDialog.getInt(
            self,
            "Go to Line",
            f"Line number (1–{total}):",
            editor.current_line(),
            1,
            total,
        )
        if not ok:
            return
        editor.go_to_line(line)

    def _go_to_heading(self) -> None:
        """Jump to a heading in the document you are working in."""
        from PySide6.QtWidgets import QDialog, QListWidget, QVBoxLayout

        editor = self._focused_editor()
        if editor is None:
            return
        headings = editor.headings()
        if not headings:
            self.statusBar().showMessage(
                "No headings in this document", 5000
            )
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Go to Heading")
        layout = QVBoxLayout(dialog)
        list_widget = QListWidget(dialog)
        for level, text, line_no in headings:
            indent = "    " if level == 2 else ""
            list_widget.addItem(f"{indent}{text}  (line {line_no})")
        list_widget.setCurrentRow(0)
        layout.addWidget(list_widget)
        list_widget.itemDoubleClicked.connect(dialog.accept)
        list_widget.itemActivated.connect(dialog.accept)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        row = list_widget.currentRow()
        if row < 0:
            return
        editor.go_to_line(headings[row][2])

    def _copy_plain_text(self) -> None:
        """Copy the selection to the clipboard without Markdown."""
        editor = self._focused_editor()
        if editor is not None:
            editor.copy_plain_text()

    def _split_file_at_cursor(self) -> None:
        """Split the current file into two at the cursor's paragraph.

        The text from the cursor's paragraph onward becomes a new
        file, named in a dialog (defaulting to the same type as the
        current file). The current file keeps the text before it.
        Both are saved; the new file opens in a tab.
        """
        from PySide6.QtWidgets import QInputDialog

        editor = self._focused_editor()
        if editor is None or editor.file_path is None:
            self.statusBar().showMessage(
                "Save the file first to split it", 5000
            )
            return
        split = editor.split_text_at_cursor()
        if split is None:
            self.statusBar().showMessage(
                "Nothing to split here — put the cursor in a later "
                "paragraph",
                5000,
            )
            return
        before, after = split
        folder = str(Path(editor.file_path).parent)
        stem = Path(editor.file_path).stem
        suffix = Path(editor.file_path).suffix
        name, ok = QInputDialog.getText(
            self,
            "Split File",
            "Name for the new file (the text from here on):",
            text=f"{stem} (continued)",
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        if not name.endswith(suffix):
            name = name + suffix
        target = Path(folder) / name
        if target.exists():
            self.statusBar().showMessage(
                f"A file called {name} already exists", 5000
            )
            return
        # The current file keeps the text before the split.
        editor.replace_text(before)
        self._tabs.save_current()
        # The new file gets the text from the split onward.
        target.write_text(after, encoding="utf-8")
        self._tree.refresh()
        self._tabs.open_file(str(target))
        self.statusBar().showMessage(f"Split into {name}", 5000)

    def _merge_file(self) -> None:
        """Merge another file into the current one.

        The chosen file's text is appended to the current file
        (after a blank line), the current file is saved, and the
        merged file is moved to the Trash — recoverable with Restore,
        like any deleted file. The counterpart to Split File at Cursor.
        """
        from PySide6.QtWidgets import QInputDialog

        editor = self._focused_editor()
        if editor is None or editor.file_path is None:
            self.statusBar().showMessage(
                "Save the file first to merge into it", 5000
            )
            return
        if not self._folder:
            self.statusBar().showMessage("Open a folder first", 5000)
            return
        files = [
            f
            for f in collect_files(self._folder)
            if f.path != editor.file_path
        ]
        if not files:
            self.statusBar().showMessage(
                "No other file to merge", 5000
            )
            return
        names = [Path(f.path).name for f in files]
        name, ok = QInputDialog.getItem(
            self,
            "Merge Files",
            "Merge this file into the current one:",
            names,
            0,
            False,
        )
        if not ok or not name:
            return
        source = next(f for f in files if Path(f.path).name == name)
        try:
            source_text = Path(source.path).read_text(encoding="utf-8")
        except OSError:
            self.statusBar().showMessage(
                f"Could not read {name}", 5000
            )
            return
        current = editor.current_text()
        joined = current.rstrip("\n") + "\n\n" + source_text.strip("\n")
        editor.replace_text(joined)
        self._tabs.save_current()
        # Close its tab first (it prompts to save if dirty), then
        # trash it — the same path deleting a file takes.
        if not self._tabs.close_file(source.path):
            return
        ok, result = trash_file(self._folder, source.path)
        if not ok:
            self.statusBar().showMessage(result, 5000)
            return
        self._tree.refresh()
        self.statusBar().showMessage(
            f"Merged {name} into {Path(editor.file_path).name}; "
            f"{name} is in the Trash",
            5000,
        )

    def _join_paragraph(self) -> None:
        """Join the current paragraph with the next one."""
        editor = self._focused_editor()
        if editor is not None and not editor.join_paragraph():
            self.statusBar().showMessage(
                "No next paragraph to join", 5000
            )

    def _select_all_occurrences(self) -> None:
        """Select every occurrence of the word under the cursor and
        edit them all together. Type to replace them all; Escape,
        Enter, an arrow key, or a click ends it."""
        editor = self._focused_editor()
        if editor is None:
            return
        count = editor.select_all_occurrences()
        if count == 0:
            self.statusBar().showMessage(
                "No word under the cursor", 5000
            )
        else:
            word = "occurrence" if count == 1 else "occurrences"
            self.statusBar().showMessage(
                f"{count} {word} selected — type to replace them all, "
                "Esc to stop",
                5000,
            )

    def _toggle_bookmark(self) -> None:
        """Mark the cursor's spot in this file, or clear it.

        One bookmark per file, remembered between runs. The marked
        line gets a faint mark in the editor.
        """
        editor = self._focused_editor()
        if editor is None or editor.file_path is None:
            self.statusBar().showMessage(
                "Save the file first to bookmark it", 5000
            )
            return
        bookmarks = dict(self._preferences.get("bookmarks", {}))
        path = editor.file_path
        pos = editor.textCursor().position()
        if path in bookmarks and abs(bookmarks[path] - pos) < 5:
            del bookmarks[path]
            editor.set_bookmark_position(None)
            self.statusBar().showMessage("Bookmark cleared", 5000)
        else:
            bookmarks[path] = pos
            editor.set_bookmark_position(pos)
            self.statusBar().showMessage("Bookmarked", 5000)
        self._preferences["bookmarks"] = bookmarks
        save_preferences(self._preferences)

    def _go_to_bookmark(self) -> None:
        """Jump to this file's bookmark, if it has one."""
        editor = self._focused_editor()
        if editor is None or editor.file_path is None:
            return
        pos = self._preferences.get("bookmarks", {}).get(
            editor.file_path
        )
        if pos is None:
            self.statusBar().showMessage(
                "No bookmark in this file", 5000
            )
            return
        cursor = editor.textCursor()
        cursor.setPosition(min(pos, len(editor.toPlainText())))
        editor.setTextCursor(cursor)
        editor.setFocus()
        editor.ensureCursorVisible()

    def _refresh_bookmark_highlight(self) -> None:
        """Show the current file's bookmark mark (or clear it)."""
        editor = self._tabs.current_editor()
        if editor is None or editor.file_path is None:
            return
        pos = self._preferences.get("bookmarks", {}).get(
            editor.file_path
        )
        editor.set_bookmark_position(pos)

    def _insert_scene_break(self) -> None:
        """Insert a centered *** scene break in the editor you are working in."""
        editor = self._focused_editor()
        if editor is not None:
            editor.insert_scene_break()

    def _insert_heading(self, level: int) -> None:
        """Turn the current paragraph into a # / ## heading (or back)."""
        editor = self._focused_editor()
        if editor is not None:
            editor.insert_heading(level)

    def _insert_block_quote(self) -> None:
        """Turn the current paragraph into a > block quote (or back)."""
        editor = self._focused_editor()
        if editor is not None:
            editor.insert_block_quote()

    def _show_comments(self) -> None:
        """Open the Comments dialog for the current document."""
        editor = self._focused_editor()
        if editor is None or editor.file_path is None:
            self.statusBar().showMessage(
                "Save the file first to add comments to it", 3000
            )
            return
        file_path = editor.file_path
        dialog = CommentsDialog(self)
        dialog.set_comments(
            load_comments(file_path),
            editor.toPlainText(),
            editor.textCursor().selectedText(),
        )
        dialog.jump_requested.connect(
            lambda anchor: self._jump_to_anchor(editor, anchor)
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            save_comments(file_path, dialog.comments())
            self._refresh_comment_highlights()

    def _jump_to_anchor(self, editor, anchor: str) -> None:
        """Select the anchored passage in the editor."""
        normalized = anchor.replace("\u2029", "\n")
        cursor = editor.document().find(normalized)
        if not cursor.isNull():
            editor.setTextCursor(cursor)
            editor.setFocus()
            editor.ensureCursorVisible()

    def _refresh_comment_highlights(self) -> None:
        """Re-apply the comment marks for the current document."""
        editor = self._tabs.current_editor()
        if editor is None or editor.file_path is None:
            return
        comments = load_comments(editor.file_path)
        editor.set_comment_anchors([c.anchor for c in comments])

    def _set_alignment(self, name: str) -> None:
        """Set the current paragraph's alignment."""
        from PySide6.QtCore import Qt

        alignment = {
            "left": Qt.AlignmentFlag.AlignLeft,
            "center": Qt.AlignmentFlag.AlignHCenter,
            "right": Qt.AlignmentFlag.AlignRight,
            "justify": Qt.AlignmentFlag.AlignJustify,
        }[name]
        editor = self._focused_editor()
        if editor is not None:
            editor.set_alignment(alignment)

    def _change_case(self, mode: str) -> None:
        """Change the case of the selection (or the current word)."""
        editor = self._focused_editor()
        if editor is not None:
            editor.change_case(mode)

    def _show_project_search(
        self, query: str | None = None, case_sensitive: bool = False
    ) -> None:
        """Find in Project: search every file in the open folder.

        When a query is given (from "Find all mentions"), it is used
        instead of the current selection, and the search is
        case-sensitive so a name matches only itself.
        """
        if not self._folder:
            self.statusBar().showMessage(
                "Open a folder first to search it", 5000
            )
            return
        # Flush unsaved edits so the search sees the current text.
        self._tabs.autosave()
        files = collect_files(self._folder)
        if self._search_dialog is None:
            self._search_dialog = ProjectSearchDialog(files, self)
            self._search_dialog.result_opened.connect(self._open_search_result)
            self._search_dialog.files_changed.connect(
                self._reload_open_files
            )
        else:
            self._search_dialog.set_files(files)
        if query is not None:
            self._search_dialog.set_query(query)
            self._search_dialog.set_case_sensitive(case_sensitive)
        else:
            editor = self._tabs.current_editor()
            if editor is not None:
                selected = editor.textCursor().selectedText()
                if selected:
                    self._search_dialog.set_query(selected)
        self._search_dialog.show()
        self._search_dialog.raise_()
        self._search_dialog.activateWindow()
        self._search_dialog.run_search()

    def _find_mentions(self, word: str) -> None:
        """Find every mention of a word across the project.

        From the editor's right-click menu. Case-sensitive, so a
        name matches only itself ("Aldric", not "aldric").
        """
        self._show_project_search(query=word, case_sensitive=True)

    def _show_lookup_window(self) -> None:
        """Open the Dictionary window (or bring it to the front).

        A general lookup, not tied to the editor: the search box
        starts empty. The window is created once and reused, so
        clicking the button again just brings it back.
        """
        if self._lookup_window is None:
            self._lookup_window = LookupWindow(self)
        self._lookup_window.show()
        self._lookup_window.raise_()
        self._lookup_window.activateWindow()
        self._lookup_window.focus_search()

    def _show_manuscript_view(self) -> None:
        """Open the Manuscript view (or bring it to the front).

        The whole book as one document, read-only. The view is
        created once and reused; opening it again refreshes it.
        """
        if not self._folder:
            self.statusBar().showMessage(
                "Open a folder first to read its manuscript", 5000
            )
            return
        if self._manuscript_view is None:
            self._manuscript_view = ManuscriptView(self._folder, self)
        else:
            self._manuscript_view.set_folder(self._folder)
        self._manuscript_view.show()
        self._manuscript_view.raise_()
        self._manuscript_view.activateWindow()

    def _show_about(self) -> None:
        """Open the About dialog: name, version, creator, license."""
        AboutDialog(self).exec()

    def _show_readability(self) -> None:
        """Open the Readability dialog (or bring it to the front).

        Modeless, so it stays open while you write; Refresh re-reads
        the document you are working in. Created once and reused.
        """
        if self._readability_dialog is None:
            self._readability_dialog = ReadabilityDialog(
                self._readability_text, self
            )
        else:
            self._readability_dialog.refresh()
        self._readability_dialog.show()
        self._readability_dialog.raise_()
        self._readability_dialog.activateWindow()

    def _readability_text(self) -> str:
        """The text the Readability dialog measures: the focused editor."""
        editor = self._focused_editor()
        return editor.current_text() if editor is not None else ""

    def _show_project_stats(self) -> None:
        """Open the Project Word Count dialog (or bring it to the front).

        Modeless, so it stays open while you write; Refresh saves
        unsaved edits and recounts. Created once and reused.
        """
        if not self._folder:
            self.statusBar().showMessage(
                "Open a folder first to count its words", 5000
            )
            return
        if self._project_stats_dialog is None:
            self._project_stats_dialog = ProjectStatsDialog(
                self._folder, before_refresh=self._tabs.autosave, parent=self
            )
        else:
            self._project_stats_dialog.set_folder(self._folder)
        self._project_stats_dialog.show()
        self._project_stats_dialog.raise_()
        self._project_stats_dialog.activateWindow()

    def _show_project_spellcheck(self) -> None:
        """Open the Project Spellcheck dialog (or bring it to the front).

        Modeless; Refresh saves unsaved edits and re-scans. Clicking
        a word in the list jumps to its first occurrence.
        """
        if not self._folder:
            self.statusBar().showMessage(
                "Open a folder first to spellcheck it", 5000
            )
            return
        if self._spell_checker is None:
            self.statusBar().showMessage(
                "Spellcheck is not installed (pyspellchecker)", 5000
            )
            return
        if self._project_spellcheck_dialog is None:
            self._project_spellcheck_dialog = ProjectSpellcheckDialog(
                self._folder,
                self._spell_checker,
                self._spell_known_words(),
                before_refresh=self._tabs.autosave,
                jump_to=self._jump_to_spelling,
                parent=self,
            )
        else:
            self._project_spellcheck_dialog.set_folder(self._folder)
        self._project_spellcheck_dialog.show()
        self._project_spellcheck_dialog.raise_()
        self._project_spellcheck_dialog.activateWindow()

    def _spell_known_words(self) -> set[str]:
        """The words the spellcheck never flags: entity terms plus
        the user's own dictionary."""
        custom_words = {
            word.lower()
            for word in self._preferences.get("custom_words", [])
        }
        if not self._folder:
            return custom_words
        rules = collect_terms(
            collect_files(self._folder),
            self._preferences["highlight_colors"],
            self._preferences["highlight_enabled"],
        )
        return {term.lower() for term, _color in rules} | custom_words

    def _jump_to_spelling(self, path: str, pos: int) -> None:
        """Open a file and put the cursor on a misspelled word."""
        self.open_file(path)
        editor = self._tabs.current_editor()
        if editor is None:
            return
        cursor = editor.textCursor()
        cursor.setPosition(min(pos, len(editor.toPlainText())))
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        editor.setTextCursor(cursor)
        editor.setFocus()
        editor.ensureCursorVisible()

    def _show_word_frequency(self) -> None:
        """Open the Word Frequency dialog (or bring it to the front).

        Modeless; Refresh saves unsaved edits and recounts.
        """
        if not self._folder:
            self.statusBar().showMessage(
                "Open a folder first to count its words", 5000
            )
            return
        if self._word_frequency_dialog is None:
            self._word_frequency_dialog = WordFrequencyDialog(
                self._folder, before_refresh=self._tabs.autosave, parent=self
            )
        else:
            self._word_frequency_dialog.set_folder(self._folder)
        self._word_frequency_dialog.show()
        self._word_frequency_dialog.raise_()
        self._word_frequency_dialog.activateWindow()

    def _step_file(self, direction: int) -> None:
        """Open the next (+1) or previous (-1) file in tree order,
        wrapping around at the ends. For reading a draft straight
        through.
        """
        if not self._folder:
            return
        files = [f.path for f in collect_files(self._folder)]
        if not files:
            return
        editor = self._tabs.current_editor()
        current = editor.file_path if editor is not None else None
        if current in files:
            index = (files.index(current) + direction) % len(files)
        else:
            index = 0 if direction > 0 else len(files) - 1
        self.open_file(files[index])

    # -- split view ------------------------------------------------------

    def _focused_editor(self):
        """The editor the user is working in.

        The split editor, if the split pane is open and it has the
        focus; otherwise the current tab's editor. Formatting, find,
        and read aloud act on this one.
        """
        if self._split_pane.isVisible() and self._split_editor.hasFocus():
            return self._split_editor
        return self._tabs.current_editor()

    def _toggle_split_view(self, checked: bool) -> None:
        """Show or hide the split pane beside the tabs.

        Hiding keeps the file (it is still there when the pane is
        shown again); it only prompts if the file has unsaved edits.
        """
        if checked:
            self._split_pane.show()
            self._editor_splitter.setSizes(
                [self.width() // 2, self.width() // 2]
            )
            if self._split_file is None:
                self._split_label.setText("No file in split view")
        else:
            if not self._maybe_discard_split():
                self._split_action.setChecked(True)
                return
            self._split_pane.hide()
        self._split_action.setChecked(self._split_pane.isVisible())

    def _show_split_file(self, path: str) -> None:
        """Open a file in the split pane, showing it if it was hidden."""
        if self._split_file == path:
            self._split_pane.show()
            self._split_action.setChecked(True)
            return
        if not self._maybe_discard_split():
            return
        ok, text = read_text_file(path)
        if not ok:
            self.statusBar().showMessage(text, 5000)
            return
        self._split_editor.file_path = path
        self._split_editor.load_text(text)
        self._split_editor.mark_saved()
        self._split_file = path
        self._split_label.setText(Path(path).name)
        self._split_pane.show()
        self._editor_splitter.setSizes(
            [self.width() // 2, self.width() // 2]
        )
        self._split_action.setChecked(True)

    def _close_split(self) -> None:
        """Close the split pane (the × in its header)."""
        self._toggle_split_view(False)

    def _save_split_editor(self) -> bool:
        """Save the split file if it is dirty. True if nothing to save."""
        editor = self._split_editor
        if not editor.is_dirty() or editor.file_path is None:
            return True
        ok, message = write_text_file(
            editor.file_path, editor.current_text()
        )
        if not ok:
            self.statusBar().showMessage(message, 5000)
            return False
        editor.mark_saved()
        return True

    def _maybe_discard_split(self) -> bool:
        """True if it is safe to replace or close the split file."""
        editor = self._split_editor
        if not editor.is_dirty():
            return True
        name = (
            Path(editor.file_path).name
            if editor.file_path
            else "Untitled"
        )
        answer = QMessageBox.question(
            self,
            "Unsaved changes",
            f"Save changes to {name} before closing the split view?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self._save_split_editor()
        if answer == QMessageBox.StandardButton.Discard:
            return True
        return False

    def _open_search_result(self, result) -> None:
        """Open the result's file and select the match in it."""
        if self._tabs.open_file(result.path):
            self._file_label.setText(result.path)
        editor = self._tabs.current_editor()
        if editor is not None:
            editor.reveal_match(
                result.query, result.match_index, result.case_sensitive
            )
        self._update_title()
        self._update_status()

    def _reload_open_files(self) -> None:
        """Reload every open tab from disk (after a project replace).

        The search dialog saves tabs before replacing, so nothing
        unsaved is lost; the tabs just show the new text.
        """
        for path in self._tabs.open_files():
            self._tabs.reload_file(path)
        self._update_title()
        self._update_status()

    def _on_tab_changed(self, _index: int) -> None:
        self._find_bar.set_editor(self._tabs.current_editor())
        self._update_format_buttons()
        self._refresh_comment_highlights()
        self._refresh_bookmark_highlight()

    # -- formatting and highlighting -------------------------------------

    def _apply_editor_font(self) -> None:
        """Apply the saved writing font to the tabs and the toolbar."""
        family = self._preferences["font_family"]
        size = int(self._preferences["font_size"])
        font = QFont(family)
        font.setPixelSize(size)
        self._tabs.set_editor_font(font)
        self._split_editor.setFont(font)
        self._format_toolbar.set_editor_font(family, size)

    def _apply_line_spacing(self) -> None:
        """Apply the saved line spacing to the tabs and the split editor."""
        factor = self._preferences.get("line_spacing", 1.0)
        self._tabs.set_line_spacing(factor)
        self._split_editor.set_line_spacing(factor)

    def _set_line_spacing(self, factor: float) -> None:
        """Set the line spacing everywhere and remember it."""
        self._preferences["line_spacing"] = factor
        self._apply_line_spacing()

    def _on_editor_font_changed(self, family: str, size: int) -> None:
        self._preferences["font_family"] = family
        self._preferences["font_size"] = size
        save_preferences(self._preferences)
        font = QFont(family)
        font.setPixelSize(size)
        self._tabs.set_editor_font(font)
        self._split_editor.setFont(font)

    def _toggle_bold(self) -> None:
        editor = self._focused_editor()
        if editor is not None:
            editor.toggle_bold()
            self._update_format_buttons()

    def _toggle_italic(self) -> None:
        editor = self._focused_editor()
        if editor is not None:
            editor.toggle_italic()
            self._update_format_buttons()

    def _toggle_underline(self) -> None:
        editor = self._focused_editor()
        if editor is not None:
            editor.toggle_underline()
            self._update_format_buttons()

    def _toggle_strikethrough(self) -> None:
        editor = self._focused_editor()
        if editor is not None:
            editor.toggle_strikethrough()
            self._update_format_buttons()

    def _toggle_highlight(self) -> None:
        editor = self._focused_editor()
        if editor is not None:
            editor.toggle_highlight()
            self._update_format_buttons()

    def _clear_formatting(self) -> None:
        editor = self._focused_editor()
        if editor is not None:
            editor.clear_formatting()
            self._update_format_buttons()

    def _zoom_in(self) -> None:
        """Enlarge the text a step (display only; the saved font is untouched)."""
        editor = self._focused_editor()
        if editor is not None:
            editor.zoom_in()

    def _zoom_out(self) -> None:
        """Shrink the text a step (display only; the saved font is untouched)."""
        editor = self._focused_editor()
        if editor is not None:
            editor.zoom_out()

    def _zoom_reset(self) -> None:
        """Back to the saved writing font size."""
        self._apply_editor_font()

    def _paste_plain_text(self) -> None:
        """Paste the clipboard as plain text, without its formatting."""
        editor = self._focused_editor()
        if editor is not None:
            editor.paste_plain_text()

    def _duplicate_paragraph(self) -> None:
        """Copy the current paragraph below itself."""
        editor = self._focused_editor()
        if editor is not None:
            editor.duplicate_paragraph()

    def _move_paragraph(self, direction: int) -> None:
        """Move the current paragraph up (-1) or down (+1)."""
        editor = self._focused_editor()
        if editor is not None:
            editor.move_paragraph(direction)

    def _update_format_buttons(self) -> None:
        editor = self._focused_editor()
        if editor is None:
            return
        self._format_toolbar.set_bold_active(editor.is_bold())
        self._format_toolbar.set_italic_active(editor.is_italic())
        self._format_toolbar.set_underline_active(editor.is_underline())
        self._format_toolbar.set_strikethrough_active(editor.is_strikethrough())
        self._format_toolbar.set_highlight_active(editor.is_highlight())

    def _toggle_format_toolbar(self, checked: bool) -> None:
        self._format_toolbar.setVisible(checked)

    # -- focus mode ------------------------------------------------------

    def _toggle_focus_mode(self, checked: bool) -> None:
        self._set_focus_mode(checked)

    def _set_focus_mode(self, on: bool) -> None:
        """Hide the chrome and center the page; F11 or Esc to leave."""
        self._focus_mode = on
        if on:
            self._toolbar_was_visible = self._format_toolbar.isVisible()
            self._format_toolbar.setVisible(False)
            # The split pane would break the centered page; hide it
            # and bring it back when focus mode ends.
            self._split_was_visible = self._split_pane.isVisible()
            self._split_pane.hide()
            self.statusBar().showMessage(
                "Focus mode — F11 or Esc to exit", 5000
            )
        else:
            self._format_toolbar.setVisible(self._toolbar_was_visible)
            self._toolbar_action.setChecked(self._toolbar_was_visible)
            if self._split_was_visible:
                self._split_pane.show()
        self._tree.setVisible(not on)
        self._menu_bar.setVisible(not on)
        self._focus_action.setChecked(on)
        self._update_focus_margins()
        if on:
            editor = self._tabs.current_editor()
            if editor is not None:
                editor.setFocus()

    def _update_focus_margins(self) -> None:
        """Center the editor with wide margins in focus mode, else none."""
        layout = self._right_container.layout()
        if layout is None:
            return
        if self._focus_mode:
            margin = max(40, (self.width() - 750) // 2)
            layout.setContentsMargins(margin, 0, margin, 0)
        else:
            layout.setContentsMargins(0, 0, 0, 0)

    # -- read aloud ------------------------------------------------------

    def _active_read_aloud_engine(self):
        """The read-aloud engine the preference names: Piper or system."""
        if self._preferences.get("read_aloud_engine") == "piper":
            return self._piper_read_aloud
        return self._read_aloud

    def _toggle_read_aloud(self, checked: bool) -> None:
        """Read the selection (or the whole document) aloud, or stop."""
        if not checked:
            self._read_aloud.stop()
            self._piper_read_aloud.stop()
            return
        editor = self._focused_editor()
        if editor is None:
            self._read_action.setChecked(False)
            return
        selected = editor.textCursor().selectedText()
        text = selected if selected.strip() else editor.current_text()
        engine = self._active_read_aloud_engine()
        if not engine.speak(text):
            self._read_action.setChecked(False)
            if engine is self._piper_read_aloud:
                if not self._piper_read_aloud.voice_ready:
                    self.statusBar().showMessage(
                        "Choose a Piper voice file first "
                        "(View → Read Aloud Voice)",
                        5000,
                    )
                else:
                    self.statusBar().showMessage(
                        "Could not start Piper — is piper-tts installed?",
                        5000,
                    )
            else:
                self.statusBar().showMessage(
                    "No speech voices available on this system", 5000
                )
            return
        self.statusBar().showMessage("Reading aloud…", 5000)

    def _on_read_aloud_finished(self) -> None:
        """Follow the speech engine: uncheck when it finishes."""
        self._read_action.setChecked(False)

    def _set_read_aloud_engine(self, engine: str) -> None:
        """Switch between the system voices and Piper (neural)."""
        self._preferences["read_aloud_engine"] = engine
        save_preferences(self._preferences)
        self._system_voice_action.setChecked(engine == "system")
        self._piper_voice_action.setChecked(engine == "piper")
        if engine == "piper" and not self._piper_read_aloud.voice_ready:
            self._choose_piper_voice()

    def _choose_piper_voice(self) -> None:
        """Pick the Piper voice model file (.onnx).

        The matching .onnx.json config sits next to it, with the
        same name plus ".json". The path is saved, so the voice is
        still there next time the app starts.
        """
        # Start the dialog where the voice is likely to be: the folder
        # of the voice already saved in preferences, or Downloads
        # (where a browser download lands). Without a start folder
        # Qt opens the app's working directory, which on his machine
        # was C:\Windows\System32.
        saved = str(self._preferences.get("piper_voice_path", ""))
        if saved:
            start_dir = str(Path(saved).parent)
        else:
            start_dir = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.DownloadLocation
            )
            if not start_dir:
                start_dir = QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.HomeLocation
                )
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Piper voice file",
            start_dir,
            "Piper voice models (*.onnx)",
        )
        if not path:
            return
        if not Path(str(path) + ".json").is_file():
            self.statusBar().showMessage(
                "That voice is missing its .onnx.json config file", 5000
            )
            return
        self._preferences["piper_voice_path"] = path
        save_preferences(self._preferences)
        self._piper_read_aloud.set_voice(path)
        self._read_action.setEnabled(
            self._read_aloud.available
            or self._piper_read_aloud.available
        )
        self.statusBar().showMessage(
            f"Piper voice: {Path(path).name}", 5000
        )

    def keyPressEvent(self, event) -> None:
        # Esc leaves focus mode. The find bar's own Esc hides the bar
        # first when it has focus, so this only fires once it is gone.
        if event.key() == Qt.Key.Key_Escape and self._focus_mode:
            self._set_focus_mode(False)
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._focus_mode:
            self._update_focus_margins()

    def _rebuild_highlights(self) -> None:
        """Rebuild the (term, color) rules from the open folder's files.

        The same terms are also the spellchecker's never-flagged words,
        together with the user's own dictionary.
        """
        custom_words = {
            word.lower()
            for word in self._preferences.get("custom_words", [])
        }
        if not self._folder:
            self._tabs.set_highlight_rules([])
            self._tabs.set_spell_known_words(custom_words)
            self._split_editor.set_highlight_rules([])
            self._split_editor.set_spell_known_words(custom_words)
            return
        files = collect_files(self._folder)
        rules = collect_terms(
            files,
            self._preferences["highlight_colors"],
            self._preferences["highlight_enabled"],
        )
        self._tabs.set_highlight_rules(rules)
        known = {term.lower() for term, _color in rules} | custom_words
        self._tabs.set_spell_known_words(known)
        self._split_editor.set_highlight_rules(rules)
        self._split_editor.set_spell_known_words(known)

    def _toggle_spellcheck(self, checked: bool) -> None:
        self._preferences["spellcheck_enabled"] = checked
        save_preferences(self._preferences)
        self._tabs.set_spell_enabled(checked)
        self._split_editor.set_spell_enabled(checked)

    def _toggle_weasel(self, checked: bool) -> None:
        self._preferences["weasel_enabled"] = checked
        save_preferences(self._preferences)
        self._tabs.set_weasel_enabled(checked)
        self._split_editor.set_weasel_enabled(checked)

    def _toggle_typewriter(self, checked: bool) -> None:
        self._preferences["typewriter"] = checked
        save_preferences(self._preferences)
        self._tabs.set_typewriter_enabled(checked)
        self._split_editor.set_typewriter_enabled(checked)

    def _toggle_first_line_indent(self, checked: bool) -> None:
        self._preferences["first_line_indent"] = checked
        save_preferences(self._preferences)
        self._tabs.set_first_line_indent_enabled(checked)
        self._split_editor.set_first_line_indent_enabled(checked)

    def _toggle_show_invisibles(self, checked: bool) -> None:
        self._preferences["show_invisibles"] = checked
        save_preferences(self._preferences)
        self._tabs.set_show_invisibles_enabled(checked)
        self._split_editor.set_show_invisibles_enabled(checked)

    def _toggle_focus_sentence(self, checked: bool) -> None:
        self._preferences["focus_sentence"] = checked
        save_preferences(self._preferences)
        self._tabs.set_focus_sentence_enabled(checked)
        self._split_editor.set_focus_sentence_enabled(checked)

    def _toggle_line_numbers(self, checked: bool) -> None:
        self._preferences["line_numbers"] = checked
        save_preferences(self._preferences)
        self._tabs.set_line_numbers_visible(checked)
        self._split_editor.set_line_numbers_visible(checked)

    def _toggle_smart_quotes(self, checked: bool) -> None:
        self._preferences["smart_quotes"] = checked
        save_preferences(self._preferences)
        self._tabs.set_smart_quotes_enabled(checked)
        self._split_editor.set_smart_quotes_enabled(checked)

    def _toggle_auto_capitalize(self, checked: bool) -> None:
        self._preferences["auto_capitalize"] = checked
        save_preferences(self._preferences)
        self._tabs.set_auto_capitalize_enabled(checked)
        self._split_editor.set_auto_capitalize_enabled(checked)

    def _toggle_continue_lists(self, checked: bool) -> None:
        self._preferences["continue_lists"] = checked
        save_preferences(self._preferences)
        self._tabs.set_continue_lists_enabled(checked)
        self._split_editor.set_continue_lists_enabled(checked)

    def _apply_theme_with_radius(self) -> None:
        """Re-apply the current theme with the current corner radius.

        Used when the theme is switched.
        """
        theme = self._preferences.get("theme", THEME_LIGHT)
        apply_theme(theme, self._corner_radius)

    def _set_theme(self, theme: str) -> None:
        """Switch the theme and remember it for next time."""
        self._preferences["theme"] = theme
        save_preferences(self._preferences)
        self._apply_theme_with_radius()
        self._light_theme_action.setChecked(theme == THEME_LIGHT)
        self._dark_theme_action.setChecked(theme == THEME_DARK)

    def _fix_typography(self) -> None:
        """Fix straight quotes and double hyphens, selection or document."""
        editor = self._focused_editor()
        if editor is None:
            return
        count = editor.fix_typography()
        if count:
            self.statusBar().showMessage(
                f"Fixed {count} quote{'s' if count != 1 else ''} "
                f"or dash{'es' if count != 1 else ''}",
                5000,
            )
        else:
            self.statusBar().showMessage(
                "Typography is already clean", 5000
            )

    def _add_word_to_dictionary(self, word: str) -> None:
        """Save a word to the user's dictionary and stop flagging it."""
        custom = self._preferences.setdefault("custom_words", [])
        if word.lower() not in [saved.lower() for saved in custom]:
            custom.append(word)
            save_preferences(self._preferences)
        self._rebuild_highlights()
        self.statusBar().showMessage(
            f"Added '{word}' to dictionary", 3000
        )

    def _show_highlight_colors(self) -> None:
        groups = term_groups()
        if self._folder:
            for file in collect_files(self._folder):
                if (
                    file.group not in groups
                    and file.group not in NON_TERM_GROUPS
                ):
                    groups.append(file.group)
        dialog = HighlightDialog(
            groups,
            self._preferences["highlight_colors"],
            self._preferences["highlight_enabled"],
            self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._preferences["highlight_colors"].update(dialog.colors)
            self._preferences["highlight_enabled"].update(dialog.enabled)
            save_preferences(self._preferences)
            self._rebuild_highlights()

    # -- autosave ----------------------------------------------------------

    def _on_document_changed(self) -> None:
        # Any activity resets the idle clock; autosave fires 2s after the
        # last change, and only writes tabs that are dirty.
        self._autosave_timer.start(AUTOSAVE_DELAY_MS)
        self._update_title()
        self._update_status()
        self._update_format_buttons()

    def _autosave(self) -> None:
        saved = self._tabs.autosave()
        if self._split_editor.is_dirty():
            if self._save_split_editor():
                saved += 1
        if saved:
            now = datetime.now().strftime("%H:%M")
            self.statusBar().showMessage(f"Autosaved {now}", 3000)

    # -- closing -----------------------------------------------------------

    def closeEvent(self, event) -> None:
        # The split file first: it is not a tab, so close_all() would
        # miss it. A Cancel leaves the window open.
        if not self._maybe_discard_split():
            event.ignore()
            return
        # Capture the session first: close_all() empties the tabs.
        files = self._tabs.open_files()
        active = self._tabs.active_index()
        if self._tabs.close_all():
            save_session(self._folder, files, active, self._session_path)
            event.accept()
        else:
            event.ignore()

    # -- status and title --------------------------------------------------

    def _update_title(self) -> None:
        editor = self._tabs.current_editor()
        if editor is None:
            self.setWindowTitle("Novelshop")
            return
        name = Path(editor.file_path).name if editor.file_path else "Untitled"
        dirty = "*" if editor.is_dirty() else ""
        self.setWindowTitle(f"{dirty}{name} — Novelshop")

    def _update_status(self) -> None:
        editor = self._tabs.current_editor()
        if editor is None:
            self._counts_label.setText("No document open")
            return
        counts = count_words(editor.current_text())
        line, col = editor.cursor_line_col()
        text = f"{counts.format()} · Line {line}, Col {col}"
        selected = editor.textCursor().selectedText()
        if selected:
            sel_words = len(selected.split())
            word = "word" if sel_words == 1 else "words"
            text += f" · {sel_words} {word} selected"
        self._counts_label.setText(text)
