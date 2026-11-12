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
"""Novelshop — a plain, focused writing app.

Entry point. Creates the application and shows the main window. All
real work lives in the novel_shop package, one concern per file.

By default no style is forced: Qt uses the platform's native style,
so the app looks like a Windows app on Windows, a Mac app on a Mac,
and follows the system light/dark setting. View → Theme →
Novelshop Dark switches to a dark theme, remembered between runs.
"""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from novel_shop.main_window import MainWindow
from novel_shop.resources import resource_path


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Novelshop")

    # One-time move: the app used to be called "Novel Shop", so its
    # settings and session lived in an AppData folder of that name.
    # Rename the folder so the theme, font, recent folders, and open
    # files carry over instead of resetting to defaults.
    _migrate_app_data_folder()

    # The "NS" tile: the taskbar icon and the icon in the title bar.
    # The guard keeps the app starting if the icon file is ever missing.
    icon_path = resource_path("novel_shop/icon.ico")
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()
    return app.exec()


def _migrate_app_data_folder() -> None:
    """Rename the old "Novel Shop" AppData folder to "Novelshop".

    Runs once, the first time the renamed app starts. If the new
    folder already exists, or the old one is gone, there is nothing
    to do. A failure leaves the app working on defaults.
    """
    from PySide6.QtCore import QStandardPaths

    new_folder = Path(
        QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
    )
    old_folder = new_folder.parent / "Novel Shop"
    if new_folder.exists() or not old_folder.is_dir():
        return
    try:
        old_folder.rename(new_folder)
    except OSError:
        pass


if __name__ == "__main__":
    sys.exit(main())
