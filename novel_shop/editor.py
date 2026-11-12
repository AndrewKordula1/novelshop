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
"""Editor: the writing surface.

The file is Markdown, and the editor reads and writes it with a
small parser of its own (paragraphs, **bold**, *italic*) instead of
Qt's Markdown support — Qt collapses a single newline inside a
paragraph to a space, which would silently rewrite the file. Here
the file round-trips exactly: what is on disk is what you see, and
what you save is what you wrote. A highlighter colors mentions of
defined things; the colors are display only.
"""

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPalette,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import QTextEdit, QWidget

from novel_shop import lexicon
from novel_shop.highlighter import ManuscriptHighlighter
from novel_shop.lookup_dialog import LookupDialog
from novel_shop.manuscript import aligned_paragraph, parse_inline, split_paragraphs
from novel_shop.spellcheck import is_misspelled, suggestions_for
from novel_shop.theme import style_popup_menu
from novel_shop.typography import (
    smart_double_quote,
    smart_single_quote,
    typography_edits,
)

_LINE_BREAK = "\u2028"  # line break inside a paragraph, not a new one
SCENE_BREAK = "***"  # a paragraph of just this is a scene break
FIRST_LINE_INDENT = 36  # the traditional novel paragraph indent, in points
HIGHLIGHT_COLOR = "#fff59d"  # pale yellow, the classic highlighter mark
# Words ending in a period that do not end a sentence, for
# auto-capitalize (the same set the read-aloud splitter uses).
_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "st", "sr", "jr", "vs", "etc", "e.g", "i.e",
}
COMMENT_MARK_COLOR = "#dbeafe"  # light blue, a passage with a comment
FIND_MATCH_COLOR = QColor(26, 115, 232, 100)  # translucent accent blue
FOCUS_DIM_COLOR = "#808080"  # mid-grey: dim on dark and light alike
BOOKMARK_MARK_COLOR = QColor(26, 115, 232, 40)  # faint accent, a bookmarked line
MULTI_EDIT_COLOR = QColor(245, 158, 11, 80)  # translucent amber, multi-edit ranges


def _insert_markdown(cursor: QTextCursor, text: str) -> None:
    """Insert Markdown text at the cursor, parsing **bold**, *italic*,
    ~~struck~~, ==highlighted==, and <u>underlined</u>.

    Paragraphs are separated by a blank line; a single newline inside
    a paragraph is a line break. The cursor's format is reset at each
    paragraph so formatting never leaks across one. A paragraph wrapped
    in <div style="text-align: X;"> is inserted with that alignment.
    """
    default_format = QTextCharFormat()
    cursor.beginEditBlock()
    try:
        cursor.setCharFormat(default_format)
        for para_index, paragraph in enumerate(split_paragraphs(text)):
            if para_index > 0:
                cursor.insertBlock()
                cursor.setCharFormat(default_format)
            alignment_name, paragraph = aligned_paragraph(paragraph)
            # Always set the alignment explicitly: a new block inherits
            # the previous block's format, so without this a centered
            # paragraph would make every paragraph after it centered.
            alignment = {
                "center": Qt.AlignmentFlag.AlignHCenter,
                "right": Qt.AlignmentFlag.AlignRight,
                "justify": Qt.AlignmentFlag.AlignJustify,
            }.get(alignment_name, Qt.AlignmentFlag.AlignLeft)
            block_format = QTextBlockFormat()
            block_format.setAlignment(alignment)
            cursor.mergeBlockFormat(block_format)
            for line_index, line in enumerate(paragraph.split("\n")):
                if line_index > 0:
                    cursor.insertText(_LINE_BREAK)
                for run_text, bold, italic, underline, strike, highlight in parse_inline(line):
                    fmt = QTextCharFormat()
                    if bold:
                        fmt.setFontWeight(QFont.Weight.Bold)
                    if italic:
                        fmt.setFontItalic(True)
                    if underline:
                        fmt.setFontUnderline(True)
                    if strike:
                        fmt.setFontStrikeOut(True)
                    if highlight:
                        fmt.setBackground(QColor(HIGHLIGHT_COLOR))
                    cursor.insertText(run_text, fmt)
    finally:
        cursor.endEditBlock()


def _serialize_runs(runs: list[tuple[str, bool, bool, bool, bool, bool]]) -> str:
    """Runs on one line as Markdown.

    Runs that share bold/italic merge into one group, with underline,
    strikethrough, and highlight marked inside it — so **bold
    <u>under</u>** stays one bold group instead of fragmenting into
    **bold ****<u>under</u>**, and **bold ~~both~~** stays one group
    too.
    """
    out: list[str] = []
    index = 0
    while index < len(runs):
        bold, italic = runs[index][1], runs[index][2]
        parts: list[str] = []
        while (
            index < len(runs)
            and runs[index][1] == bold
            and runs[index][2] == italic
        ):
            text, _bold, _italic, underline, strike, highlight = runs[index]
            if strike:
                text = f"~~{text}~~"
            if underline:
                text = f"<u>{text}</u>"
            if highlight:
                text = f"=={text}=="
            parts.append(text)
            index += 1
        group = "".join(parts)
        if bold and italic:
            group = f"***{group}***"
        elif bold:
            group = f"**{group}**"
        elif italic:
            group = f"*{group}*"
        out.append(group)
    return "".join(out)


def _set_block_markdown(block, markdown: str) -> None:
    """Replace one block's text with Markdown, keeping the block itself.

    The block's format (alignment, line height, indent) stays; only
    its text is replaced. Used to swap two paragraphs' contents.
    Selects the block's text explicitly (start to end of block),
    because BlockUnderCursor can span the paragraph break and merge
    neighbouring blocks when the text is replaced.
    """
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
    cursor.movePosition(
        QTextCursor.MoveOperation.EndOfBlock,
        QTextCursor.MoveMode.KeepAnchor,
    )
    _insert_markdown(cursor, markdown)


def _block_markdown(block) -> str:
    """One paragraph as Markdown: line breaks as single newlines.

    A paragraph whose alignment is not left is wrapped in an HTML
    div, the Markdown way to store alignment: <div style="text-align:
    center;">...</div>. Left-aligned text stays unwrapped.
    """
    lines: list[list[tuple[str, bool, bool, bool, bool, bool]]] = [[]]
    iterator = block.begin()
    while not iterator.atEnd():
        fragment = iterator.fragment()
        fmt = fragment.charFormat()
        bold = fmt.fontWeight() == QFont.Weight.Bold
        italic = fmt.fontItalic()
        underline = fmt.fontUnderline()
        strike = fmt.fontStrikeOut()
        highlight = (
            fmt.background().color().name().lower()
            == HIGHLIGHT_COLOR
        )
        for index, part in enumerate(fragment.text().split(_LINE_BREAK)):
            if index > 0:
                lines.append([])
            if part:
                lines[-1].append(
                    (part, bold, italic, underline, strike, highlight)
                )
        iterator += 1
    text = "\n".join(_serialize_runs(line) for line in lines)
    alignment = block.blockFormat().alignment()
    # A scene break *** is centered by its content alone (the loader
    # re-derives it), so it is never wrapped in a div.
    if text.strip() == SCENE_BREAK:
        return text
    if alignment == Qt.AlignmentFlag.AlignHCenter:
        return f'<div style="text-align: center;">{text}</div>'
    if alignment == Qt.AlignmentFlag.AlignRight:
        return f'<div style="text-align: right;">{text}</div>'
    if alignment == Qt.AlignmentFlag.AlignJustify:
        return f'<div style="text-align: justify;">{text}</div>'
    return text


class _LineNumberArea(QWidget):
    """The line-number margin on the left of the editor.

    A plain widget the Editor paints into (Qt's Code Editor Example
    pattern). It is only as wide as the largest line number needs,
    and it scrolls with the text because the Editor repaints it on
    every updateRequest.
    """

    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.paint_line_numbers(event)


class Editor(QTextEdit):
    add_word_requested = Signal(str)  # word to add to the dictionary
    find_mentions_requested = Signal(str)  # word to find across the project

    def __init__(self, parent=None):
        super().__init__(parent)
        self._saved_text = ""
        self._line_spacing = 1.0  # display only; see set_line_spacing
        self._typewriter = False  # display only; see set_typewriter_enabled
        self._first_line_indent = False  # display only; see below
        self.file_path: str | None = None
        self.setAcceptRichText(True)
        editor_font = QFont("Georgia")
        editor_font.setPixelSize(15)
        self.setFont(editor_font)
        self._highlighter = ManuscriptHighlighter(self.document())
        self.cursorPositionChanged.connect(self._maybe_center_cursor)
        self.cursorPositionChanged.connect(self._update_focus_sentence)
        self._spell_checker = None
        self._spell_known_words: set[str] = set()
        self._smart_quotes_enabled = True
        self._auto_capitalize_enabled = True
        self._continue_lists_enabled = True
        # Multi-edit (select all occurrences): the ranges being
        # edited together, the text typed into them, and which one
        # the cursor sits in. _multi_typed is False until the first
        # character, which replaces the word (VS Code style) instead
        # of appending to it.
        self._multi_ranges: list[tuple[int, int]] = []
        self._multi_text = ""
        self._multi_primary = 0
        self._multi_editing = False
        self._multi_typed = False
        self._bookmark_pos: int | None = None
        # ExtraSelections state: comment anchors, find matches, and
        # the focused sentence share one list (see below).
        self._comment_anchors: list[str] = []
        self._find_match_spans: list[tuple[int, int]] = []
        self._focus_sentence_enabled = False
        self._focus_sentence_span: tuple[int, int] | None = None
        # Line numbers: a margin on the left, off by default.
        self._line_numbers_visible = False
        self._line_number_area = _LineNumberArea(self)
        self.document().blockCountChanged.connect(
            self._update_line_number_area_width
        )
        # QTextEdit has no updateRequest signal in this Qt build, so
        # the margin is scrolled by scrollContentsBy and repainted
        # whenever the text changes.
        self.textChanged.connect(self._line_number_area.update)
        self._update_line_number_area_width()

    def set_smart_quotes_enabled(self, enabled: bool) -> None:
        """Turn as-you-type smart quotes and dashes on or off."""
        self._smart_quotes_enabled = enabled

    def set_auto_capitalize_enabled(self, enabled: bool) -> None:
        """Turn as-you-type sentence capitalization on or off."""
        self._auto_capitalize_enabled = enabled

    def set_continue_lists_enabled(self, enabled: bool) -> None:
        """Turn list continuation on Enter on or off."""
        self._continue_lists_enabled = enabled

    def set_bookmark_position(self, pos: int | None) -> None:
        """Mark the line at this document position, or clear it.

        The bookmarked line gets a faint mark, display only. None
        clears it.
        """
        self._bookmark_pos = pos
        self._refresh_extra_selections()

    def keyPressEvent(self, event) -> None:
        """As-you-type smart quotes, dashes, capitalization, and lists.

        A straight quote becomes the curly one that fits where it
        lands (opening or closing, or an apostrophe), and a second
        hyphen turns the pair into an em dash. A lowercase letter
        starting a sentence is capitalized. Enter on a list item
        continues the list. In multi-edit mode (select all
        occurrences) every typed character replaces all the marked
        occurrences at once, and Escape, Enter, an arrow key, or a
        click ends it. Anything else, and keys held with Ctrl or Alt
        (shortcuts), go through as usual.
        """
        if self._multi_editing:
            key = event.key()
            if key in (
                Qt.Key.Key_Escape,
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
                Qt.Key.Key_Up,
                Qt.Key.Key_Down,
                Qt.Key.Key_Left,
                Qt.Key.Key_Right,
                Qt.Key.Key_Home,
                Qt.Key.Key_End,
                Qt.Key.Key_PageUp,
                Qt.Key.Key_PageDown,
            ):
                self._exit_multi_edit()
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    super().keyPressEvent(event)
                return
            if key == Qt.Key.Key_Backspace and not event.modifiers() & (
                Qt.KeyboardModifier.ControlModifier
                | Qt.KeyboardModifier.AltModifier
            ):
                # Before anything is typed, Backspace trims one
                # character off the word; after that it trims the
                # text typed so far.
                self._multi_text = self._multi_text[:-1]
                self._multi_typed = True
                self._apply_multi_text()
                return
            char = event.text()
            if (
                len(char) == 1
                and char.isprintable()
                and not event.modifiers()
                & (
                    Qt.KeyboardModifier.ControlModifier
                    | Qt.KeyboardModifier.AltModifier
                )
            ):
                # The first character replaces the word (the ranges
                # are selected, VS Code style); later ones append.
                if not self._multi_typed:
                    self._multi_text = char
                    self._multi_typed = True
                else:
                    self._multi_text += char
                self._apply_multi_text()
                return
            self._exit_multi_edit()
        if (
            self._continue_lists_enabled
            and event.key()
            in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and not event.modifiers()
            & (
                Qt.KeyboardModifier.ControlModifier
                | Qt.KeyboardModifier.AltModifier
            )
        ):
            if self._continue_list():
                return
        if self._smart_quotes_enabled and not event.modifiers() & (
            Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.AltModifier
        ):
            char = event.text()
            if char in ('"', "'"):
                cursor = self.textCursor()
                start = cursor.selectionStart()
                plain = self.toPlainText()
                before = plain[:start]
                if char == '"':
                    replacement = smart_double_quote(before)
                else:
                    replacement = smart_single_quote(
                        before, plain[cursor.selectionEnd():]
                    )
                cursor.insertText(replacement)
                self.setTextCursor(cursor)
                return
            if char == "-" and not self.textCursor().hasSelection():
                cursor = self.textCursor()
                pos = cursor.position()
                plain = self.toPlainText()
                if pos > 0 and plain[pos - 1] == "-":
                    cursor.beginEditBlock()
                    cursor.deletePreviousChar()
                    cursor.insertText("—")
                    cursor.endEditBlock()
                    self.setTextCursor(cursor)
                    return
        if (
            self._auto_capitalize_enabled
            and len(event.text()) == 1
            and event.text().islower()
            and not event.modifiers()
            & (
                Qt.KeyboardModifier.ControlModifier
                | Qt.KeyboardModifier.AltModifier
            )
            and self._should_capitalize()
        ):
            cursor = self.textCursor()
            cursor.insertText(event.text().upper())
            self.setTextCursor(cursor)
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        # A click moves the cursor, which ends a multi-edit.
        self._exit_multi_edit()
        super().mousePressEvent(event)

    def fix_typography(self) -> int:
        """Fix straight quotes and double hyphens, selection or document.

        Returns how many fixes were made. One undo step, and the
        formatting around each fix is kept, because each fix is a
        small replacement at its own spot.
        """
        cursor = self.textCursor()
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            text = self.toPlainText()[start:end]
            offset = start
        else:
            text = self.toPlainText()
            offset = 0
        edits = typography_edits(text)
        if not edits:
            return 0
        edit_cursor = QTextCursor(self.document())
        edit_cursor.beginEditBlock()
        for s, e, replacement in reversed(edits):
            edit_cursor.setPosition(offset + s)
            edit_cursor.setPosition(
                offset + e, QTextCursor.MoveMode.KeepAnchor
            )
            edit_cursor.insertText(replacement)
        edit_cursor.endEditBlock()
        return len(edits)

    def load_text(self, text: str) -> None:
        """Put text in the editor and treat it as saved."""
        self.clear()
        _insert_markdown(self.textCursor(), text)
        self._center_scene_breaks()
        self._apply_line_spacing()
        self._apply_first_line_indent()
        self.mark_saved()

    def set_line_spacing(self, factor: float) -> None:
        """Line spacing for the whole document: 1.0, 1.5, or 2.0.

        Display only — the file is Markdown, which cannot store it —
        so it is an app preference, re-applied whenever text is loaded.
        """
        self._line_spacing = factor
        self._apply_line_spacing()

    def set_typewriter_enabled(self, enabled: bool) -> None:
        """Typewriter scrolling: keep the line being typed centered.

        Display only, an app preference. When on, the view scrolls
        so the cursor sits in the middle of the editor, so the eyes
        do not have to travel as the text grows.
        """
        self._typewriter = enabled
        if enabled:
            self._center_cursor()

    def set_first_line_indent_enabled(self, enabled: bool) -> None:
        """First-line indent: the traditional novel paragraph indent.

        Display only — the file is Markdown, which cannot store it —
        so it is an app preference, re-applied whenever text is loaded.
        Each paragraph's first line is indented; wrapped lines are not.
        """
        self._first_line_indent = enabled
        self._apply_first_line_indent()

    def set_show_invisibles_enabled(self, enabled: bool) -> None:
        """Show invisible characters: spaces as dots, tabs as arrows,
        paragraph and line breaks as marks — like Word's ¶ button.

        Display only, an app preference. Useful for spotting double
        spaces, trailing whitespace, and stray blank lines.
        """
        from PySide6.QtGui import QTextOption

        option = self.document().defaultTextOption()
        flags = option.flags()
        show = (
            QTextOption.Flag.ShowTabsAndSpaces
            | QTextOption.Flag.ShowLineAndParagraphSeparators
        )
        if enabled:
            flags |= show
        else:
            flags &= ~show
        option.setFlags(flags)
        self.document().setDefaultTextOption(option)

    def _apply_first_line_indent(self) -> None:
        """Set the stored first-line indent on every block, keeping the rest."""
        indent = FIRST_LINE_INDENT if getattr(self, "_first_line_indent", False) else 0
        block = self.document().begin()
        while block.isValid():
            cursor = QTextCursor(block)
            fmt = QTextBlockFormat()
            fmt.setTextIndent(indent)
            cursor.mergeBlockFormat(fmt)
            block = block.next()

    def _center_cursor(self) -> None:
        """Scroll so the cursor line sits in the middle of the viewport."""
        rect = self.cursorRect()
        viewport_height = self.viewport().height()
        bar = self.verticalScrollBar()
        delta = rect.y() - viewport_height // 2 + rect.height() // 2
        bar.setValue(bar.value() + delta)

    def _maybe_center_cursor(self) -> None:
        if self._typewriter:
            self._center_cursor()

    def _apply_line_spacing(self) -> None:
        """Set the stored line spacing on every block, keeping alignment."""
        factor = getattr(self, "_line_spacing", 1.0)
        height = int(round(factor * 100))
        block = self.document().begin()
        while block.isValid():
            cursor = QTextCursor(block)
            fmt = QTextBlockFormat()
            fmt.setLineHeight(
                float(height),
                QTextBlockFormat.LineHeightTypes.ProportionalHeight.value,
            )
            cursor.mergeBlockFormat(fmt)
            block = block.next()

    def insert_scene_break(self) -> None:
        """Insert a centered *** scene break, then a fresh paragraph.

        The break is its own paragraph containing only ***; the
        cursor lands in the empty paragraph after it, ready for the
        next scene. If the cursor is mid-paragraph, the paragraph
        is split first so the break sits on its own line.
        """
        cursor = self.textCursor()
        cursor.beginEditBlock()
        try:
            # Split the paragraph if the cursor is not at its start,
            # so the break does not land mid-sentence.
            if cursor.positionInBlock() > 0:
                cursor.insertBlock()
            # A blank paragraph before the break (unless already blank).
            block = cursor.block()
            if block.text().strip():
                cursor.insertBlock()
            # The break itself, centered.
            fmt = QTextBlockFormat()
            fmt.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            cursor.mergeBlockFormat(fmt)
            cursor.insertText(SCENE_BREAK)
            # A fresh, left-aligned paragraph after it, cursor there.
            cursor.insertBlock()
            left = QTextBlockFormat()
            left.setAlignment(Qt.AlignmentFlag.AlignLeft)
            cursor.mergeBlockFormat(left)
            self.setTextCursor(cursor)
        finally:
            cursor.endEditBlock()

    def set_alignment(self, alignment) -> None:
        """Set the current paragraph's alignment (left, center, right,
        or justify). The alignment is stored in the file as an HTML
        div, so it survives a reload and reaches the export."""
        cursor = self.textCursor()
        block_format = QTextBlockFormat()
        block_format.setAlignment(alignment)
        cursor.mergeBlockFormat(block_format)

    def alignment(self):
        """The current paragraph's alignment."""
        return self.textCursor().blockFormat().alignment()

    def insert_block_quote(self) -> None:
        """Turn the current paragraph into a > block quote (or back).

        Prefixes the paragraph with "> "; if it already starts with
        it, the prefix comes off again. The highlighter renders the
        quoted text italic with the marker faded, and the export
        turns it into a real block quotation.
        """
        cursor = self.textCursor()
        cursor.beginEditBlock()
        try:
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            text = cursor.block().text()
            if text.startswith("> "):
                cursor.movePosition(
                    QTextCursor.MoveOperation.Right,
                    QTextCursor.MoveMode.KeepAnchor,
                    2,
                )
                cursor.removeSelectedText()
            else:
                cursor.insertText("> ")
            self.setTextCursor(cursor)
        finally:
            cursor.endEditBlock()

    def insert_heading(self, level: int) -> None:
        """Turn the current paragraph into a # / ## heading (or back).

        Inserts the markers at the start of the paragraph; if it is
        already a heading of that level, the markers come off again.
        The highlighter renders the line larger and bold, and the
        export turns it into a real heading.
        """
        cursor = self.textCursor()
        cursor.beginEditBlock()
        try:
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            text = cursor.block().text()
            marker = "# " if level == 1 else "## "
            if text.startswith(marker):
                # Already this level: toggle it off.
                cursor.movePosition(
                    QTextCursor.MoveOperation.Right,
                    QTextCursor.MoveMode.KeepAnchor,
                    len(marker),
                )
                cursor.removeSelectedText()
            else:
                # Strip any other level's markers, then add this one.
                if text.startswith("## "):
                    cursor.movePosition(
                        QTextCursor.MoveOperation.Right,
                        QTextCursor.MoveMode.KeepAnchor,
                        3,
                    )
                    cursor.removeSelectedText()
                elif text.startswith("# "):
                    cursor.movePosition(
                        QTextCursor.MoveOperation.Right,
                        QTextCursor.MoveMode.KeepAnchor,
                        2,
                    )
                    cursor.removeSelectedText()
                cursor.insertText(marker)
            self.setTextCursor(cursor)
        finally:
            cursor.endEditBlock()

    def _center_scene_breaks(self) -> None:
        """Center every paragraph that is just *** (a scene break).

        Alignment is display-only — the file stores plain *** — so
        it is re-derived from the content whenever text is loaded.
        Merged, not set, so the line spacing survives.
        """
        block = self.document().begin()
        while block.isValid():
            if block.text().strip() == SCENE_BREAK:
                cursor = QTextCursor(block)
                fmt = QTextBlockFormat()
                fmt.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                cursor.mergeBlockFormat(fmt)
            block = block.next()

    def current_text(self) -> str:
        """The document as Markdown, exactly as it would be saved."""
        paragraphs = []
        block = self.document().begin()
        while block.isValid():
            paragraphs.append(_block_markdown(block))
            block = block.next()
        # A fresh document has one empty block; that is not a paragraph.
        while paragraphs and paragraphs[-1] == "":
            paragraphs.pop()
        return "\n\n".join(paragraphs)

    def is_dirty(self) -> bool:
        return self.current_text() != self._saved_text

    def mark_saved(self) -> None:
        self._saved_text = self.current_text()

    def replace_text(self, text: str) -> None:
        """Replace the whole text as one undoable edit (Ctrl+Z undoes it)."""
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        _insert_markdown(cursor, text)

    def cursor_line_col(self) -> tuple[int, int]:
        """1-based line and column of the text cursor."""
        cursor = self.textCursor()
        return cursor.blockNumber() + 1, cursor.columnNumber() + 1

    def line_count(self) -> int:
        """Logical lines (rows) in the document.

        A row is a line in the file: a paragraph break and a single
        newline inside a paragraph both start a new row. A trailing
        separator does not start an extra empty row.
        """
        plain = self.toPlainText()
        if not plain:
            return 1
        count = plain.count("\n") + plain.count("\u2028") + 1
        if plain[-1] in ("\n", "\u2028"):
            count -= 1
        return count

    def current_line(self) -> int:
        """The 1-based logical line the cursor is on."""
        plain = self.toPlainText()
        pos = self.textCursor().position()
        return (
            plain[:pos].count("\n")
            + plain[:pos].count("\u2028")
            + 1
        )

    def go_to_line(self, line_no: int) -> bool:
        """Move the cursor to the start of a logical line (1-based).

        Returns False if the line does not exist.
        """
        plain = self.toPlainText()
        starts = [0]
        for i, char in enumerate(plain):
            if char in ("\n", "\u2028"):
                starts.append(i + 1)
        if starts and starts[-1] == len(plain):
            starts.pop()
        if line_no < 1 or line_no > len(starts):
            return False
        cursor = self.textCursor()
        cursor.setPosition(starts[line_no - 1])
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self.setFocus()
        return True

    def headings(self) -> list[tuple[int, str, int]]:
        """The document's headings, as (level, text, line number).

        A line starting with `# ` is level 1, `## ` level 2 — the
        same headings the editor renders and the export turns into
        real headings. The text is the heading without its markers.
        """
        found = []
        for line_no, line in enumerate(self.toPlainText().split("\n"), 1):
            if line.startswith("# "):
                found.append((1, line[2:], line_no))
            elif line.startswith("## "):
                found.append((2, line[3:], line_no))
        return found

    def copy_plain_text(self) -> None:
        """Copy the selection to the clipboard without Markdown.

        The markers (**bold**, *italic*, ==highlight==, ~~strike~~,
        # headings, > quotes, <u>) are stripped, so pasting into
        email or chat gives clean text. Nothing is selected, nothing
        is copied.
        """
        import re

        from PySide6.QtWidgets import QApplication

        cursor = self.textCursor()
        if not cursor.hasSelection():
            return
        text = cursor.selectedText().replace("\u2029", "\n")
        # Markers at the start of a line: headings and block quotes.
        text = re.sub(r"^#{1,2} ", "", text, flags=re.MULTILINE)
        text = re.sub(r"^> ", "", text, flags=re.MULTILINE)
        # Inline markers: bold/italic, underline, strike, highlight.
        text = re.sub(r"\*\*\*|\*\*|\*|<u>|</u>|~~|==", "", text)
        QApplication.clipboard().setText(text)

    def split_text_at_cursor(self) -> tuple[str, str] | None:
        """Split the document at the cursor's paragraph, or None.

        Returns (before, after): the Markdown up to the paragraph
        the cursor is in, and that paragraph plus everything after
        it. The split is at a paragraph boundary, so no paragraph
        is cut in half. None when there is nothing on one side —
        the cursor is in the first paragraph, or there is nothing
        after it.
        """
        cursor = self.textCursor()
        block_no = cursor.blockNumber()
        blocks = []
        block = self.document().begin()
        while block.isValid():
            blocks.append(_block_markdown(block))
            block = block.next()
        # A fresh document has one empty block; that is not a paragraph.
        while blocks and blocks[-1] == "":
            blocks.pop()
        if block_no == 0 or block_no >= len(blocks):
            return None
        before = "\n\n".join(blocks[:block_no])
        after = "\n\n".join(blocks[block_no:])
        if not before.strip() or not after.strip():
            return None
        return (before, after)

    def reveal_match(
        self, query: str, match_index: int, case_sensitive: bool
    ) -> None:
        """Select the match_index-th occurrence of query in this document.

        The search runs on the file's text; the document's text is the
        same words with the Markdown markers rendered away, so the
        occurrences line up in the same order. A query split across a
        formatting boundary is the one exception — then this lands on a
        nearby occurrence of the same word instead.
        """
        if not query:
            return
        text = self.toPlainText()
        haystack = text if case_sensitive else text.lower()
        needle = query if case_sensitive else query.lower()
        spans: list[tuple[int, int]] = []
        start = 0
        while True:
            index = haystack.find(needle, start)
            if index < 0:
                break
            spans.append((index, index + len(needle)))
            start = index + len(needle)
        if not spans:
            return
        start, end = spans[min(match_index, len(spans) - 1)]
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self.setFocus()

    def toggle_bold(self) -> None:
        """Bold on/off for the selection (or the next typed text)."""
        weight = (
            QFont.Weight.Normal
            if self.fontWeight() == QFont.Weight.Bold
            else QFont.Weight.Bold
        )
        self.setFontWeight(weight)

    def toggle_italic(self) -> None:
        """Italic on/off for the selection (or the next typed text)."""
        self.setFontItalic(not self.fontItalic())

    def toggle_underline(self) -> None:
        """Underline on/off for the selection (or the next typed text)."""
        self.setFontUnderline(not self.fontUnderline())

    def toggle_highlight(self) -> None:
        """Highlight on/off for the selection (or the next typed text).

        A pale yellow background, the classic highlighter mark, for
        passages to come back to while revising. Stored in the file
        as ==highlighted==, so it survives into DOCX/EPUB/PDF export.
        """
        from PySide6.QtGui import QColor

        fmt = QTextCharFormat()
        if self.currentCharFormat().background().color().name().lower() == HIGHLIGHT_COLOR:
            fmt.setBackground(QColor("transparent"))
        else:
            fmt.setBackground(QColor(HIGHLIGHT_COLOR))
        self.mergeCurrentCharFormat(fmt)

    def is_highlight(self) -> bool:
        return (
            self.currentCharFormat().background().color().name().lower()
            == HIGHLIGHT_COLOR
        )

    def toggle_strikethrough(self) -> None:
        """Strikethrough on/off for the selection (or the next typed text).

        QTextEdit has setFontUnderline but no setFontStrikeOut, so
        this merges a char format the same way setFontUnderline does.
        """
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(not self.currentCharFormat().fontStrikeOut())
        self.mergeCurrentCharFormat(fmt)

    def set_comment_anchors(self, anchors: list[str]) -> None:
        """Highlight the passages that have comments pinned to them.

        A light blue background, display only — it never touches the
        file. Each anchor is the exact passage text a comment was
        pinned to; it is found again in the document, so the mark
        follows its passage when the words around it move. An anchor
        that is gone (rewritten) simply gets no mark.
        """
        self._comment_anchors = list(anchors)
        self._refresh_extra_selections()

    def set_find_matches(self, spans: list[tuple[int, int]]) -> None:
        """Highlight every match of the current find text.

        A translucent blue background, display only. The current
        match is the solid text selection, so it stands out from
        the rest. An empty list clears the marks.
        """
        self._find_match_spans = list(spans)
        self._refresh_extra_selections()

    def set_focus_sentence_enabled(self, enabled: bool) -> None:
        """Focus sentence: dim everything except the sentence being
        written, iA Writer style. Display only; the file is untouched.

        The dimming is re-derived whenever the cursor moves to a
        different sentence.
        """
        self._focus_sentence_enabled = enabled
        if not enabled:
            self._focus_sentence_span = None
        self._refresh_extra_selections()

    def _refresh_extra_selections(self) -> None:
        """Rebuild the editor's ExtraSelections from all three sources.

        Comment anchors, find matches, and the focused sentence share
        this one list, so one feature cannot clobber another's marks.
        """
        selections: list[QTextEdit.ExtraSelection] = []
        for anchor in self._comment_anchors:
            # selectedText() marks paragraph breaks with \u2029; the
            # document's find wants a plain newline there.
            normalized = anchor.replace("\u2029", "\n")
            cursor = self.document().find(normalized)
            if cursor.isNull():
                continue
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format.setBackground(QColor(COMMENT_MARK_COLOR))
            selections.append(selection)
        for start, end in self._find_match_spans:
            cursor = QTextCursor(self.document())
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format.setBackground(FIND_MATCH_COLOR)
            selections.append(selection)
        if self._focus_sentence_enabled and self._focus_sentence_span:
            start, end = self._focus_sentence_span
            for before_start, before_end in ((0, start), (end, len(self.toPlainText()))):
                if before_start >= before_end:
                    continue
                cursor = QTextCursor(self.document())
                cursor.setPosition(before_start)
                cursor.setPosition(
                    before_end, QTextCursor.MoveMode.KeepAnchor
                )
                selection = QTextEdit.ExtraSelection()
                selection.cursor = cursor
                selection.format.setForeground(QColor(FOCUS_DIM_COLOR))
                selections.append(selection)
        if self._bookmark_pos is not None:
            cursor = QTextCursor(self.document())
            cursor.setPosition(self._bookmark_pos)
            block = cursor.block()
            mark = QTextCursor(self.document())
            mark.setPosition(block.position())
            mark.setPosition(
                block.position() + len(block.text()),
                QTextCursor.MoveMode.KeepAnchor,
            )
            selection = QTextEdit.ExtraSelection()
            selection.cursor = mark
            selection.format.setBackground(BOOKMARK_MARK_COLOR)
            selections.append(selection)
        for start, end in self._multi_ranges:
            cursor = QTextCursor(self.document())
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format.setBackground(MULTI_EDIT_COLOR)
            selections.append(selection)
        self.setExtraSelections(selections)

    def _current_sentence_span(self) -> tuple[int, int] | None:
        """The (start, end) of the sentence the cursor is in, or None.

        A sentence ends at ., !, or ? followed by a space or the end
        of the text; a paragraph break is a sentence boundary too.
        The span is the sentence's text, without the trailing space.
        """
        plain = self.toPlainText()
        if not plain:
            return None
        pos = self.textCursor().position()
        # Backwards to the previous sentence end (or the start).
        start = 0
        i = pos - 1
        while i >= 0:
            if plain[i] in (".", "!", "?"):
                # A sentence end needs a space, a line break, or the
                # end of the text after it (so "Mr." does not split).
                if i + 1 >= len(plain) or plain[i + 1] in (
                    " ",
                    "\n",
                    "\u2028",
                ):
                    start = i + 1
                    break
            if plain[i] in ("\n", "\u2028"):
                start = i + 1
                break
            i -= 1
        while start < len(plain) and plain[start] == " ":
            start += 1
        # Forwards to the next sentence end (or the end).
        end = len(plain)
        i = pos
        while i < len(plain):
            if plain[i] in (".", "!", "?"):
                if i + 1 >= len(plain) or plain[i + 1] in (
                    " ",
                    "\n",
                    "\u2028",
                ):
                    end = i + 1
                    break
            if plain[i] in ("\n", "\u2028"):
                end = i
                break
            i += 1
        if start >= end:
            return None
        return (start, end)

    def _update_focus_sentence(self) -> None:
        """Re-derive the focused sentence when the cursor moves.

        Only rebuilds the marks when the sentence actually changed,
        so typing inside one sentence does not repaint the dimming.
        """
        if not self._focus_sentence_enabled:
            return
        span = self._current_sentence_span()
        if span == self._focus_sentence_span:
            return
        self._focus_sentence_span = span
        self._refresh_extra_selections()

    # -- line numbers ----------------------------------------------------

    def set_line_numbers_visible(self, visible: bool) -> None:
        """Show or hide the line-number margin on the left.

        Display only, an app preference. The numbers are the file's
        logical lines (the same rows Go to Line counts): a paragraph
        break and a single newline inside a paragraph both start a
        new row, and a wrapped line does not.
        """
        self._line_numbers_visible = visible
        self._update_line_number_area_width()

    def line_number_area_width(self) -> int:
        """How wide the line-number margin needs to be, in pixels."""
        if not self._line_numbers_visible:
            return 0
        digits = len(str(max(1, self.line_count())))
        return self.fontMetrics().horizontalAdvance("9") * digits + 12

    def _update_line_number_area_width(self) -> None:
        """Re-set the left viewport margin when the width changes."""
        self.setViewportMargins(
            self.line_number_area_width(), 0, 0, 0
        )

    def _update_line_number_area(self, rect, dy: int) -> None:
        """Keep the margin in step when the text scrolls or changes."""
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width()

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        """Scroll the line-number margin with the text."""
        super().scrollContentsBy(dx, dy)
        self._line_number_area.scroll(0, dy)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        rect = self.contentsRect()
        self._line_number_area.setGeometry(
            rect.left(),
            rect.top(),
            self.line_number_area_width(),
            rect.height(),
        )

    def paint_line_numbers(self, event) -> None:
        """Paint the line numbers for the visible blocks.

        One number per logical line: a block can hold several (a
        single newline inside a paragraph is a row), and a wrapped
        line gets none. The layout's lines tell the two apart — a
        logical line starts at the block's start or right after a
        \\u2028, a wrap continuation does not.
        """
        painter = QPainter(self._line_number_area)
        painter.fillRect(
            event.rect(),
            self.palette().color(QPalette.ColorRole.Base),
        )
        painter.setPen(QColor(FOCUS_DIM_COLOR))
        painter.setFont(self.font())
        # QTextEdit has no firstVisibleBlock, blockBoundingGeometry,
        # or contentOffset (those are QPlainTextEdit), so the first
        # visible block is the one under the viewport's top-left
        # corner, and a block's top comes from cursorRect — which
        # already accounts for scrolling and the viewport margins.
        # A layout line's y() is its offset from its block's top.
        block = self.cursorForPosition(QPoint(0, 0)).block()
        if not block.isValid():
            return
        text = self.toPlainText()
        logical = (
            text[: block.position()].count("\n")
            + text[: block.position()].count("\u2028")
            + 1
        )
        while block.isValid():
            block_top = self.cursorRect(QTextCursor(block)).top()
            if block_top > event.rect().bottom():
                break
            block_layout = block.layout()
            block_text = block.text()
            for i in range(block_layout.lineCount()):
                line = block_layout.lineAt(i)
                start = line.textStart()
                is_logical = start == 0 or (
                    start > 0 and block_text[start - 1] == "\u2028"
                )
                if is_logical:
                    y = block_top + line.y()
                    painter.drawText(
                        0,
                        int(y),
                        self._line_number_area.width() - 6,
                        self.fontMetrics().height(),
                        Qt.AlignmentFlag.AlignRight,
                        str(logical),
                    )
                    logical += 1
            block = block.next()

    def zoom_in(self) -> None:
        """Enlarge the text a step (display only; the saved font is untouched).

        QTextEdit.zoomIn/zoomOut misbehave when the font is set by
        pixel size (as ours is), so this steps the pixel size directly.
        """
        font = self.font()
        font.setPixelSize(font.pixelSize() + 1)
        self.setFont(font)

    def zoom_out(self) -> None:
        """Shrink the text a step (display only), not below 8px."""
        font = self.font()
        font.setPixelSize(max(8, font.pixelSize() - 1))
        self.setFont(font)

    def paste_plain_text(self) -> None:
        """Paste the clipboard as plain text, without its formatting.

        A paste from the web or another app brings its fonts and
        colors with it; this one keeps only the words, in the
        editor's own formatting.
        """
        from PySide6.QtWidgets import QApplication

        text = QApplication.clipboard().text()
        if text:
            self.insertPlainText(text)

    def change_case(self, mode: str) -> None:
        """Change the case of the selection (or the current word).

        mode is "upper", "lower", "title", or "sentence". With no
        selection, the word under the cursor is changed instead.
        """
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        if not cursor.hasSelection():
            return
        text = cursor.selectedText()
        if mode == "upper":
            changed = text.upper()
        elif mode == "lower":
            changed = text.lower()
        elif mode == "title":
            changed = text.title()
        elif mode == "sentence":
            import re

            def _cap(match):
                return match.group(1) + match.group(2).upper()

            changed = re.sub(
                r"(^|[.!?]\s+)([a-z])", _cap, text
            )
            # Capitalize the very first letter too.
            if changed and changed[0].islower():
                changed = changed[0].upper() + changed[1:]
        else:
            return
        if changed == text:
            return
        cursor.beginEditBlock()
        try:
            cursor.insertText(changed)
        finally:
            cursor.endEditBlock()
        self.setTextCursor(cursor)

    def duplicate_paragraph(self) -> None:
        """Copy the current paragraph below itself, cursor in the copy."""
        cursor = self.textCursor()
        block = cursor.block()
        markdown = _block_markdown(block)
        if not markdown:
            return
        cursor.beginEditBlock()
        try:
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            cursor.insertBlock()
            _insert_markdown(cursor, markdown)
            self.setTextCursor(cursor)
        finally:
            cursor.endEditBlock()

    def move_paragraph(self, direction: int) -> None:
        """Move the current paragraph up (-1) or down (+1), swapping
        its text with the neighbouring paragraph. The cursor follows
        the moved paragraph. Display formats (scene-break centering,
        line spacing, indent) are re-derived from the content after
        the swap, so a moved *** stays centered."""
        cursor = self.textCursor()
        block = cursor.block()
        target = block.previous() if direction < 0 else block.next()
        if not target.isValid():
            return
        # Block handles go stale once the document changes, so work
        # by block number and re-fetch before each replacement.
        doc = self.document()
        block_no = block.blockNumber()
        target_no = target.blockNumber()
        current_md = _block_markdown(block)
        target_md = _block_markdown(target)
        cursor.beginEditBlock()
        try:
            _set_block_markdown(doc.findBlockByNumber(block_no), target_md)
            _set_block_markdown(doc.findBlockByNumber(target_no), current_md)
            self._center_scene_breaks()
            self._apply_line_spacing()
            self._apply_first_line_indent()
            # Put the cursor in the block the paragraph moved to.
            new_cursor = QTextCursor(doc.findBlockByNumber(target_no))
            new_cursor.movePosition(
                QTextCursor.MoveOperation.StartOfBlock
            )
            self.setTextCursor(new_cursor)
        finally:
            cursor.endEditBlock()

    def join_paragraph(self) -> bool:
        """Join the current paragraph with the next one.

        The paragraph break between them is removed, so the two
        become one paragraph, with a space where the break was
        (unless one side already has whitespace). Returns False
        when there is no next paragraph (the cursor is in the last
        one).
        """
        cursor = self.textCursor()
        block = cursor.block()
        next_block = block.next()
        if not next_block.isValid():
            return False
        # The end of the block's text; the paragraph separator
        # follows it. Deleting that separator joins the blocks.
        pos = block.position() + block.length() - 1
        before = self.toPlainText()[pos - 1] if pos > 0 else " "
        after = next_block.text()[:1] if next_block.text() else " "
        cursor.setPosition(pos)
        cursor.deleteChar()
        if not before.isspace() and not after.isspace():
            cursor.insertText(" ")
        self.setTextCursor(cursor)
        return True

    # -- select all occurrences (multi-edit) ---------------------------

    def select_all_occurrences(self) -> int:
        """Select every occurrence of the word under the cursor (or
        the selection) and edit them all together, VS Code style.

        The occurrences are whole words, case-sensitive — so renaming
        "Allen" does not touch "Allens" or "allen". Every character
        typed replaces all of them at once, until Escape, Enter, an
        arrow key, or a click ends the multi-edit. Returns how many
        occurrences were found (0 when there is no word to match).
        """
        import re

        cursor = self.textCursor()
        if cursor.hasSelection():
            word = cursor.selectedText()
            primary_pos = cursor.selectionStart()
        else:
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            word = cursor.selectedText()
            primary_pos = cursor.selectionStart()
        if not word or not word.strip():
            return 0
        text = self.toPlainText()
        pattern = re.compile(r"\b" + re.escape(word) + r"\b")
        ranges = [(m.start(), m.end()) for m in pattern.finditer(text)]
        if not ranges:
            return 0
        self._multi_ranges = ranges
        self._multi_text = word
        self._multi_typed = False
        self._multi_primary = next(
            (i for i, (s, e) in enumerate(ranges) if s == primary_pos),
            0,
        )
        self._multi_editing = True
        self._refresh_extra_selections()
        cursor.setPosition(ranges[self._multi_primary][1])
        self.setTextCursor(cursor)
        return len(ranges)

    def _apply_multi_text(self) -> None:
        """Replace every multi-edit range with the text typed so far.

        One undo step per keystroke. The ranges are replaced last to
        first, so an edit never shifts a range that is still to come;
        each edit also shifts the ranges already done (they sit
        after it) by the change in length, so the stored positions
        stay true.
        """
        if not self._multi_ranges:
            return
        new_text = self._multi_text
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        for i in range(len(self._multi_ranges) - 1, -1, -1):
            start, end = self._multi_ranges[i]
            delta = len(new_text) - (end - start)
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(new_text)
            self._multi_ranges[i] = (start, start + len(new_text))
            for j in range(i + 1, len(self._multi_ranges)):
                s, e = self._multi_ranges[j]
                self._multi_ranges[j] = (s + delta, e + delta)
        cursor.endEditBlock()
        self._refresh_extra_selections()
        if self._multi_ranges:
            cursor = self.textCursor()
            cursor.setPosition(
                self._multi_ranges[self._multi_primary][1]
            )
            self.setTextCursor(cursor)

    def _exit_multi_edit(self) -> None:
        """Leave multi-edit mode, clearing the marks."""
        if not self._multi_editing:
            return
        self._multi_editing = False
        self._multi_ranges = []
        self._multi_text = ""
        self._multi_typed = False
        self._refresh_extra_selections()

    def _should_capitalize(self) -> bool:
        """True when the letter being typed starts a sentence.

        The start of the document or a paragraph, or after a
        sentence-ending punctuation and spaces — unless that
        punctuation ends an abbreviation (Mr., Dr., etc.), which
        does not start a sentence.
        """
        import re

        plain = self.toPlainText()
        pos = self.textCursor().position()
        before = plain[:pos]
        if not before or before[-1] in ("\n", "\u2028"):
            return True
        match = re.search(r"([.!?])\s*$", before)
        if not match:
            return False
        word = re.search(r"([A-Za-z]+)$", before[: match.start(1)])
        if word and word.group(1).lower() in _ABBREVIATIONS:
            return False
        return True

    def _continue_list(self) -> bool:
        """Continue a list on Enter, or end it on an empty item.

        Only when the cursor is at the end of a `- `, `* `, or
        numbered (`1. `, `2) `) item. An empty item loses its marker
        and the list ends; otherwise the next line gets the same
        bullet or the next number. Returns True when it handled the
        key.
        """
        import re

        cursor = self.textCursor()
        if cursor.hasSelection():
            return False
        block = cursor.block()
        if cursor.position() != block.position() + len(block.text()):
            return False
        text = block.text()
        match = re.match(r"^(\s*)([-*]|\d+[.)])\s*(.*)$", text)
        if not match:
            return False
        indent, marker, rest = (
            match.group(1),
            match.group(2),
            match.group(3),
        )
        if not rest.strip():
            # An empty item: drop the marker and end the list. The
            # block becomes a plain empty paragraph; no new line is
            # needed, the cursor is already on it.
            cursor.setPosition(block.position())
            cursor.setPosition(
                block.position() + len(text),
                QTextCursor.MoveMode.KeepAnchor,
            )
            cursor.removeSelectedText()
            self.setTextCursor(cursor)
            return True
        if marker[0].isdigit():
            number = int(marker[:-1]) + 1
            next_marker = f"{number}{marker[-1]}"
        else:
            next_marker = marker
        cursor.insertText(f"\n{indent}{next_marker} ")
        self.setTextCursor(cursor)
        return True

    def clear_formatting(self) -> None:
        """Back to regular text: no bold, italic, underline, strike, or highlight."""
        from PySide6.QtGui import QColor

        self.setFontWeight(QFont.Weight.Normal)
        self.setFontItalic(False)
        self.setFontUnderline(False)
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(False)
        fmt.setBackground(QColor("transparent"))
        self.mergeCurrentCharFormat(fmt)

    def is_bold(self) -> bool:
        return self.fontWeight() == QFont.Weight.Bold

    def is_italic(self) -> bool:
        return self.fontItalic()

    def is_underline(self) -> bool:
        return self.fontUnderline()

    def is_strikethrough(self) -> bool:
        return self.currentCharFormat().fontStrikeOut()

    def set_highlight_rules(self, rules: list[tuple[str, str]]) -> None:
        """(term, color) rules for coloring mentions in this document."""
        self._highlighter.set_rules(rules)

    # -- spellcheck --------------------------------------------------------

    def set_spell_checker(self, checker) -> None:
        """The dictionary for underlining and suggestions (None: off)."""
        self._spell_checker = checker
        self._highlighter.set_spell_checker(checker)

    def set_spell_known_words(self, words) -> None:
        """Words never flagged: entity terms and the user's dictionary."""
        self._spell_known_words = {word.lower() for word in words}
        self._highlighter.set_spell_known_words(self._spell_known_words)

    def set_spell_enabled(self, enabled: bool) -> None:
        self._highlighter.set_spell_enabled(enabled)

    def set_weasel_enabled(self, enabled: bool) -> None:
        """Turn the overused-word underlines on or off."""
        self._highlighter.set_weasel_enabled(enabled)

    def is_word_misspelled(self, word: str) -> bool:
        return is_misspelled(
            word, self._spell_checker, self._spell_known_words
        )

    def contextMenuEvent(self, event) -> None:
        menu = self._build_context_menu(event)
        menu.exec(event.globalPos())

    def _build_context_menu(self, event):
        """The right-click menu, built so tests can inspect it.

        Spelling help for a misspelled word, then the dictionary:
        a Synonyms submenu (click one to replace the word) and a
        Define action that opens the dialog. When WordNet is not
        installed, Define is greyed out and there are no synonyms.
        """
        menu = self.createStandardContextMenu()
        style_popup_menu(menu)
        cursor = self.cursorForPosition(event.pos())
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cursor.selectedText()
        actions = menu.actions()
        first = actions[0] if actions else None
        if word and self.is_word_misspelled(word):
            for suggestion in suggestions_for(word, self._spell_checker):
                action = menu.addAction(suggestion)
                action.triggered.connect(
                    lambda _checked, s=suggestion, c=QTextCursor(cursor):
                        self._replace_word(c, s)
                )
                menu.insertAction(first, action)
            add_action = menu.addAction(f"Add '{word}' to dictionary")
            add_action.triggered.connect(
                lambda _checked: self.add_word_requested.emit(word)
            )
            menu.insertAction(first, add_action)
            menu.insertSeparator(first)
        if word:
            synonyms = lexicon.synonyms(word)
            if synonyms:
                submenu = menu.addMenu("Synonyms")
                for synonym in synonyms:
                    action = submenu.addAction(synonym)
                    action.triggered.connect(
                        lambda _checked, s=synonym, c=QTextCursor(cursor):
                            self._replace_word(c, s)
                    )
                menu.insertMenu(first, submenu)
            define_action = menu.addAction(f"Define '{word}'")
            define_action.triggered.connect(
                lambda _checked, w=word: self._show_definition(w)
            )
            if not lexicon.is_available():
                define_action.setEnabled(False)
                define_action.setToolTip(
                    "WordNet data is not installed — pip install wn, "
                    "then python -m wn download ewn:2020"
                )
            menu.insertAction(first, define_action)
            mentions_action = menu.addAction(f"Find all mentions of '{word}'")
            mentions_action.triggered.connect(
                lambda _checked, w=word: self.find_mentions_requested.emit(w)
            )
            menu.insertAction(first, mentions_action)
        return menu

    def _show_definition(self, word: str) -> None:
        """Open the Define dialog for a word."""
        dialog = LookupDialog(word, lexicon.lookup(word), self)
        dialog.exec()

    def _replace_word(self, cursor: QTextCursor, replacement: str) -> None:
        """Replace the word the cursor has selected, as one undoable edit."""
        self.setTextCursor(cursor)
        cursor.insertText(replacement)
        self.setTextCursor(cursor)
