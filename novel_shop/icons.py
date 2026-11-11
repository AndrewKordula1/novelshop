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
"""Icons: every icon in Novelshop comes from Qt.

Rule: never use an OS-provided icon (file-type associations, desktop
theme icons). Icons come from Qt in two ways: a standard pixmap from
the current style, or a badge drawn with QPainter. If a new icon is
needed anywhere in the app, add it here, so the look stays the same
on every machine.
"""

from PySide6.QtCore import QFileInfo, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QApplication, QFileIconProvider, QStyle

from novel_shop.file_types import file_type_for_extension

BADGE_SIZE = 32
_UNKNOWN_BADGE_COLOR = "#757575"


def standard_icon(pixmap: QStyle.StandardPixmap) -> QIcon:
    """A Qt standard icon from the current style."""
    return QApplication.style().standardIcon(pixmap)


def file_type_icon(extension: str) -> QIcon:
    """Badge icon for a file type: a colored square with two letters.

    Qt's standard set has no glyph for a chapter or a spell, so each
    type gets a badge drawn with QPainter instead — still Qt, never
    the OS. An extension with no built-in type gets a grey badge made
    from its own letters.
    """
    file_type = file_type_for_extension(extension)
    if file_type is not None:
        letters, color = file_type.badge_letters, file_type.badge_color
    else:
        clean = extension.strip().lstrip(".").lower()
        letters = clean[:2].capitalize() if clean else "?"
        color = _UNKNOWN_BADGE_COLOR
    pixmap = QPixmap(BADGE_SIZE, BADGE_SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    badge = QPainterPath()
    badge.addRoundedRect(QRectF(1, 1, BADGE_SIZE - 2, BADGE_SIZE - 2), 6, 6)
    painter.fillPath(badge, QColor(color))
    font = QFont()
    font.setBold(True)
    font.setPixelSize(13)
    painter.setFont(font)
    text_color = (
        Qt.GlobalColor.black
        if QColor(color).lightness() > 150
        else Qt.GlobalColor.white
    )
    painter.setPen(text_color)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, letters)
    painter.end()
    return QIcon(pixmap)


class FileIconProvider(QFileIconProvider):
    """File and folder icons from Qt's standard set, not the OS."""

    def icon(self, info) -> QIcon:
        # Two overloads: one takes a QFileInfo, one takes an IconType.
        if isinstance(info, QFileInfo):
            if info.isDir():
                return standard_icon(QStyle.StandardPixmap.SP_DirIcon)
            return standard_icon(QStyle.StandardPixmap.SP_FileIcon)
        return self._icon_for_type(info)

    def _icon_for_type(self, icon_type) -> QIcon:
        mapping = {
            QFileIconProvider.IconType.Computer: QStyle.StandardPixmap.SP_ComputerIcon,
            QFileIconProvider.IconType.Desktop: QStyle.StandardPixmap.SP_DesktopIcon,
            QFileIconProvider.IconType.Trashcan: QStyle.StandardPixmap.SP_TrashIcon,
            QFileIconProvider.IconType.Network: QStyle.StandardPixmap.SP_DriveNetIcon,
            QFileIconProvider.IconType.Drive: QStyle.StandardPixmap.SP_DriveHDIcon,
            QFileIconProvider.IconType.Folder: QStyle.StandardPixmap.SP_DirIcon,
            QFileIconProvider.IconType.File: QStyle.StandardPixmap.SP_FileIcon,
        }
        pixmap = mapping.get(icon_type, QStyle.StandardPixmap.SP_FileIcon)
        return standard_icon(pixmap)
