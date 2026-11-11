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
"""Exporters: write the manuscript out as DOCX, EPUB, or PDF.

All three take the same blocks (see novel_shop/manuscript.py): a level,
a heading, and plain text. DOCX uses python-docx, EPUB uses ebooklib,
PDF uses Qt's own printing — no extra library for PDF.
"""

import html

from novel_shop.manuscript import Block, aligned_paragraph, parse_inline, split_paragraphs


def export_docx(
    blocks: list[Block], title: str, author: str, path: str
) -> None:
    """Write a Word document: headings, paragraphs, new page per chapter."""
    from docx import Document

    doc = Document()
    doc.core_properties.title = title
    doc.core_properties.author = author
    for index, block in enumerate(blocks):
        if index > 0 and block.level == 1:
            doc.add_page_break()
        doc.add_heading(block.title, level=block.level)
        for paragraph in split_paragraphs(block.text):
            _add_docx_paragraph(doc, paragraph)
    doc.save(path)


def _heading_level(text: str) -> tuple[int, str]:
    """A # / ## heading line: its level (1, 2, or 0) and the text
    without the markers. Headings are lines, so only the first line
    of a paragraph can be one."""
    first = text.split("\n", 1)[0]
    if first.startswith("## "):
        return 2, first[3:]
    if first.startswith("# "):
        return 1, first[2:]
    return 0, text


def _blockquote_text(text: str) -> str | None:
    """A > block quote paragraph: its text without the markers.

    Returns None when the paragraph is not a quote. Every line of a
    quote starts with "> ", so the markers are stripped per line.
    """
    lines = text.split("\n")
    if not lines or not lines[0].startswith("> "):
        return None
    stripped = [
        line[2:] if line.startswith("> ") else line for line in lines
    ]
    return "\n".join(stripped)


def _add_docx_paragraph(doc, text: str) -> None:
    """One paragraph; single newlines become line breaks, not new paragraphs.

    **bold** and *italic* from the Markdown become bold and italic runs.
    A paragraph that is just *** is a scene break, centered. A line
    starting with # or ## is a heading, styled as one. A paragraph
    starting with > is a block quote, indented and italic. A paragraph
    wrapped in <div style="text-align: X;"> keeps that alignment.
    """
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches

    level, heading_text = _heading_level(text)
    quote_text = _blockquote_text(text)
    alignment_name, aligned_text = aligned_paragraph(text)
    paragraph = doc.add_paragraph()
    if level:
        paragraph.style = doc.styles[f"Heading {level}"]
        text = heading_text
    elif quote_text is not None:
        paragraph.paragraph_format.left_indent = Inches(0.5)
        text = quote_text
    if alignment_name is not None:
        paragraph.alignment = {
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        }[alignment_name]
        text = aligned_text
    if text.strip() == "***":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for line_index, line in enumerate(text.split("\n")):
        if line_index > 0:
            paragraph.add_run().add_break()
        for run_text, bold, italic, underline, strike, highlight in parse_inline(line):
            run = paragraph.add_run(run_text)
            run.bold = bold
            run.italic = italic or quote_text is not None
            run.underline = underline
            run.font.strike = strike
            if highlight:
                from docx.enum.text import WD_COLOR_INDEX

                run.font.highlight_color = WD_COLOR_INDEX.YELLOW


def _inline_html(text: str) -> str:
    """A line of Markdown emphasis as HTML: <strong>, <em>, <u>, <s>, <mark>."""
    parts = []
    for run_text, bold, italic, underline, strike, highlight in parse_inline(text):
        escaped = html.escape(run_text)
        if bold:
            escaped = f"<strong>{escaped}</strong>"
        if italic:
            escaped = f"<em>{escaped}</em>"
        if underline:
            escaped = f"<u>{escaped}</u>"
        if strike:
            escaped = f"<s>{escaped}</s>"
        if highlight:
            escaped = f"<mark>{escaped}</mark>"
        parts.append(escaped)
    return "".join(parts)


def _paragraphs_html(text: str) -> str:
    """Plain text as <p> elements; single newlines become <br/>.

    A paragraph that is just *** is a scene break, centered. A line
    starting with # or ## is a heading (<h1> / <h2>). A paragraph
    starting with > is a block quote (<blockquote>). A paragraph
    wrapped in <div style="text-align: X;"> keeps that alignment.
    """
    parts = []
    for paragraph in split_paragraphs(text):
        level, heading_text = _heading_level(paragraph)
        if level:
            parts.append(
                f"<h{level}>{_inline_html(heading_text)}</h{level}>"
            )
            # Any lines after the heading are a normal paragraph.
            rest = paragraph.split("\n", 1)[1] if "\n" in paragraph else ""
            if rest.strip():
                lines = "<br/>".join(
                    _inline_html(line) for line in rest.split("\n")
                )
                parts.append(f"<p>{lines}</p>")
            continue
        quote_text = _blockquote_text(paragraph)
        if quote_text is not None:
            lines = "<br/>".join(
                _inline_html(line) for line in quote_text.split("\n")
            )
            parts.append(f"<blockquote>{lines}</blockquote>")
            continue
        alignment_name, aligned_text = aligned_paragraph(paragraph)
        if alignment_name is not None:
            lines = "<br/>".join(
                _inline_html(line) for line in aligned_text.split("\n")
            )
            parts.append(
                f'<p style="text-align: {alignment_name};">{lines}</p>'
            )
            continue
        lines = "<br/>".join(
            _inline_html(line) for line in paragraph.split("\n")
        )
        if paragraph.strip() == "***":
            parts.append(f'<p style="text-align: center;">{lines}</p>')
        else:
            parts.append(f"<p>{lines}</p>")
    return "".join(parts)


def export_epub(
    blocks: list[Block], title: str, author: str, path: str
) -> None:
    """Write an ebook: one file per level-1 block, table of contents."""
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier(f"urn:novel-shop:{title}")
    book.set_title(title)
    book.set_language("en")
    if author:
        book.add_author(author)

    style = (
        "body { font-family: Georgia, serif; line-height: 1.5; }"
        " h1 { font-size: 1.5em; margin-top: 2em; }"
        " h2 { font-size: 1.2em; margin-top: 1.5em; }"
    )
    css = epub.EpubItem(
        uid="style",
        file_name="style.css",
        media_type="text/css",
        content=style,
    )
    book.add_item(css)

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    chapters: list = []
    current = None
    for block in blocks:
        if block.level == 1 or current is None:
            current = epub.EpubHtml(
                title=block.title,
                file_name=f"chap_{len(chapters) + 1}.xhtml",
                lang="en",
            )
            current.content = ""
            current.add_link(href="style.css", rel="stylesheet", type="text/css")
            book.add_item(current)
            chapters.append(current)
        heading = "h1" if block.level == 1 else "h2"
        current.content += (
            f"<{heading}>{html.escape(block.title)}</{heading}>"
            + _paragraphs_html(block.text)
        )

    book.toc = chapters
    book.spine = ["nav"] + chapters
    epub.write_epub(path, book)


def export_pdf(
    blocks: list[Block], title: str, author: str, path: str
) -> None:
    """Write a PDF with Qt's printing: headings, new page per chapter.

    `author` is accepted for the shared writer signature; Qt's PDF
    output has no author field, so it is not written.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtGui import (
        QFont,
        QTextBlockFormat,
        QTextCharFormat,
        QTextCursor,
        QTextDocument,
        QTextFormat,
    )
    from PySide6.QtPrintSupport import QPrinter

    doc = QTextDocument()
    doc.setMetaInformation(QTextDocument.MetaInformation.DocumentTitle, title)
    doc.setDefaultFont(QFont("Georgia", 12))

    heading_format = QTextCharFormat()
    heading_format.setFont(QFont("Georgia", 20, QFont.Weight.Bold))
    subheading_format = QTextCharFormat()
    subheading_format.setFont(QFont("Georgia", 15, QFont.Weight.Bold))

    cursor = QTextCursor(doc)
    first = True
    for block in blocks:
        block_format = QTextBlockFormat()
        if not first and block.level == 1:
            block_format.setPageBreakPolicy(
                QTextFormat.PageBreakFlag.PageBreak_AlwaysBefore
            )
        if first:
            cursor.setBlockFormat(block_format)
            first = False
        else:
            cursor.insertBlock(block_format)
        heading = heading_format if block.level == 1 else subheading_format
        cursor.insertText(block.title, heading)
        for paragraph in split_paragraphs(block.text):
            para_format = QTextBlockFormat()
            if paragraph.strip() == "***":
                para_format.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            quote_text = _blockquote_text(paragraph)
            is_quote = quote_text is not None
            if is_quote:
                para_format.setLeftMargin(36)
                paragraph = quote_text
            alignment_name, aligned_text = aligned_paragraph(paragraph)
            if alignment_name is not None:
                para_format.setAlignment(
                    {
                        "center": Qt.AlignmentFlag.AlignHCenter,
                        "right": Qt.AlignmentFlag.AlignRight,
                        "justify": Qt.AlignmentFlag.AlignJustify,
                    }[alignment_name]
                )
                paragraph = aligned_text
            cursor.insertBlock(para_format)
            level, heading_text = _heading_level(paragraph)
            if level:
                # A heading line: larger bold text, markers stripped.
                # The rest of the paragraph (if any) follows as normal text.
                fmt = heading_format if level == 1 else subheading_format
                cursor.insertText(heading_text, fmt)
                rest = paragraph.split("\n", 1)[1] if "\n" in paragraph else ""
                if rest.strip():
                    cursor.insertBlock(QTextBlockFormat())
                    paragraph = rest
                else:
                    continue
            for line_index, line in enumerate(paragraph.split("\n")):
                if line_index > 0:
                    cursor.insertText("\u2028")  # line break, not a new paragraph
                for run_text, bold, italic, underline, strike, highlight in parse_inline(line):
                    run_format = QTextCharFormat()
                    run_font = QFont("Georgia", 12)
                    run_font.setBold(bold)
                    run_font.setItalic(italic or is_quote)
                    run_font.setUnderline(underline)
                    run_font.setStrikeOut(strike)
                    run_format.setFont(run_font)
                    if highlight:
                        from PySide6.QtGui import QColor

                        run_format.setBackground(QColor("#fff59d"))
                    cursor.insertText(run_text, run_format)

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    printer.setDocName(title)
    printer.setCreator("Novelshop")
    doc.print_(printer)
