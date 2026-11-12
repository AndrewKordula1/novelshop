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
"""About dialog: the app's name, version, creator, and license.

Opened from Help → About Novelshop... It shows the four facts
and offers the full license text, read from the LICENSE file in
the project folder.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from novel_shop import __version__
from novel_shop.resources import resource_path

APP_NAME = "Novelshop"
APP_CREATOR = "Andrew Kordula"
APP_LICENSE = "GNU General Public License v3.0 (or later)"


def license_path() -> Path:
    """The LICENSE file in the project folder, next to main.py."""
    return resource_path("LICENSE")


def icon_path() -> Path:
    """The app icon, next to this module."""
    return resource_path("novel_shop/icon.png")


class AboutDialog(QDialog):
    """The app's name, version, creator, and license."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setModal(True)

        icon = QLabel()
        pixmap = QPixmap(str(icon_path()))
        if not pixmap.isNull():
            icon.setPixmap(
                pixmap.scaled(
                    64,
                    64,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        icon.setAlignment(Qt.AlignmentFlag.AlignTop)

        name = QLabel(APP_NAME)
        name_font = name.font()
        name_font.setPointSize(16)
        name_font.setBold(True)
        name.setFont(name_font)

        details = QVBoxLayout()
        details.addWidget(name)
        details.addWidget(QLabel(f"Version {__version__}"))
        details.addWidget(QLabel(f"Created by {APP_CREATOR}"))
        details.addWidget(QLabel(f"Licensed under the {APP_LICENSE}."))

        top = QHBoxLayout()
        top.addWidget(icon)
        top.addLayout(details)
        top.addStretch()

        license_button = QPushButton("View License")
        license_button.clicked.connect(self._show_license)
        if not license_path().is_file():
            license_button.setEnabled(False)
            license_button.setToolTip("LICENSE file not found")
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(license_button)
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addLayout(buttons)
        self.resize(380, 160)

    def _show_license(self) -> None:
        """Show the full license text in a scrollable window."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{APP_NAME} License")
        dialog.setModal(True)
        text = QTextEdit()
        text.setReadOnly(True)
        try:
            text.setPlainText(
                license_path().read_text(encoding="utf-8")
            )
        except OSError:
            text.setPlainText("The LICENSE file could not be read.")
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(close_button)
        layout = QVBoxLayout(dialog)
        layout.addWidget(text)
        layout.addLayout(buttons)
        dialog.resize(600, 450)
        dialog.exec()
