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
"""Themes: the app's look, as a Qt style sheet.

Two themes, both Novelshop's own — no system theme. "Novelshop
Dark" is the near-black theme: flat near-black panels, near-white
text, and a solid blue (#1a73e8) accent for selections, the active
tab and primary buttons. The editor (the writing surface) is the
near-black content background, so the look holds while you write —
including in Focus Mode, where the chrome is hidden and only the
editor shows. "Novelshop Light" is the same design inverted: a
white writing surface, light grey chrome, near-black text, and the
same blue accent.

It is one style sheet, applied to the whole application. The
editor's font and the entity highlight colors are separate
preferences and are not touched by the theme. The window frame
and its minimize/maximize/close buttons are drawn by the OS.
"""

from pathlib import Path

from PySide6.QtWidgets import QApplication

from novel_shop.resources import resource_path

THEME_DARK = "novelshop-dark"
THEME_LIGHT = "novelshop-light"
THEME_NAMES = {
    THEME_DARK: "Novelshop Dark",
    THEME_LIGHT: "Novelshop Light",
}

# Dark palette: the main background is near-black, panels a touch
# lighter, and the accent is a solid blue.
_DARK = {
    "bg": "#0e0e0f",            # window background, editor, sidebar base
    "chrome": "#141415",        # menu bar, status bar, tab bar, tree
    "panel": "#1a1a1c",         # dialogs, menus, active tab, cards
    "input": "#232326",         # buttons, line edits, combo boxes
    "hover": "#2a2a2e",         # hover on buttons and inputs
    "border": "#2e2e32",        # input borders, subtle separators
    "text": "#e8e8ea",          # primary text, near-white
    "text_muted": "#9e9ea6",    # secondary text, muted grey
    "text_disabled": "#6e6e73",
    "accent": "#1a73e8",        # blue accent: selections, active tab, primary buttons
    "accent_hover": "#2b7de9",
    "accent_pressed": "#1765cc",
    "separator": "#262628",     # menu separators, tab pane and list borders
    "pressed": "#1e1e20",       # pressed buttons, tree hover, splitter handle
    "border_hover": "#3a3a3e",  # button hover border
    "scroll_hover": "#3f3f44",  # scrollbar handle hover
}

# Novelshop Light: the same design inverted — a white writing
# surface, light grey chrome, near-black text, the same blue accent.
_LIGHT = {
    "bg": "#ffffff",
    "chrome": "#f0f0f0",
    "panel": "#ffffff",
    "input": "#f5f5f5",
    "hover": "#e8e8e8",
    "border": "#d0d0d0",
    "text": "#1a1a1a",
    "text_muted": "#6e6e73",
    "text_disabled": "#a0a0a0",
    "accent": "#1a73e8",
    "accent_hover": "#2b7de9",
    "accent_pressed": "#1765cc",
    "separator": "#e0e0e0",
    "pressed": "#e0e0e0",
    "border_hover": "#b0b0b0",
    "scroll_hover": "#b0b0b0",
}

_PALETTES = {THEME_DARK: _DARK, THEME_LIGHT: _LIGHT}

# The combo-box arrow and the tab close mark. Once a style sheet
# touches a QComboBox or a tab bar, Qt stops drawing the native
# arrow / close mark, so the sheet has to supply them — small
# images shipped with the app. The paths are plain local paths
# with forward slashes (a file:// URL is unreliable in a style
# sheet on Windows).
def _image_path(name: str) -> str:
    return str(resource_path(f"novel_shop/{name}")).replace("\\", "/")


_DOWN_ARROW_PATH = _image_path("down_arrow.png")
_CLOSE_PATH = _image_path("close.png")

# The window's corner radius. Just enough to take the sharp
# square tip off (2px). The style sheet draws the background
# with this radius, so the menu bar's top corners and the status
# bar's bottom corners are anti-aliased — smooth, not pixelated.
DEFAULT_CORNER_RADIUS = 2


def theme_background(theme: str) -> str:
    """The theme's editor/window background colour (for paintEvent)."""
    return _PALETTES.get(theme, _LIGHT)["bg"]


def novelshop_stylesheet(
    theme: str = THEME_DARK, corner_radius: int = DEFAULT_CORNER_RADIUS
) -> str:
    """A Novelshop theme's style sheet, with the window's corner radius.

    The radius rounds the main window's background, the menu bar's
    top corners, and the status bar's bottom corners. The window
    frame itself is drawn by the OS.
    """
    p = _PALETTES.get(theme, _LIGHT)
    return f"""
QMainWindow, QDialog {{
    background-color: {p["bg"]};
    color: {p["text"]};
    border-radius: {corner_radius}px;
}}
QMenuBar {{
    background-color: {p["chrome"]};
    color: {p["text"]};
    border-top-left-radius: {corner_radius}px;
    border-top-right-radius: {corner_radius}px;
}}
QMenuBar::item {{
    padding: 10px 7px;
    border-radius: 6px;
}}
QMenuBar::item:selected {{
    background-color: {p["input"]};
    border-radius: 6px;
}}
QMenuBar::item:pressed {{
    background-color: {p["input"]};
    border-radius: 6px;
}}
QMenuBar::item:disabled {{
    color: {p["text_disabled"]};
}}
QMenu {{
    background-color: {p["panel"]};
    color: {p["text"]};
    border: none;
    border-radius: 8px;
}}
QMenu::item {{
    margin: 1px 5px;
    padding-top: 4px;
    padding-bottom: 4px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background-color: {p["accent"]};
    color: white;
    border-radius: 6px;
}}
QMenu::item:disabled {{
    color: {p["text_disabled"]};
}}
QMenu::separator {{
    height: 1px;
    background: {p["separator"]};
    margin: 4px 8px;
}}
QToolBar {{
    background-color: {p["chrome"]};
    border: none;
    spacing: 4px;
}}
QToolButton {{
    background: transparent;
    color: {p["text"]};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px;
}}
QToolButton:hover {{
    background-color: {p["input"]};
    border: 1px solid {p["border"]};
}}
QToolButton:checked {{
    background-color: {p["input"]};
    border: 1px solid {p["accent"]};
}}
QToolButton:disabled {{
    color: {p["text_disabled"]};
}}
QTreeView {{
    background-color: {p["chrome"]};
    color: {p["text"]};
    border: none;
    outline: none;
}}
QTreeView::item {{
    padding-top: 3px;
    padding-bottom: 3px;
}}
QTreeView::item:selected {{
    background-color: {p["accent"]};
    color: white;
}}
QTreeView::item:hover {{
    background-color: {p["pressed"]};
}}
QTreeView::branch {{
    background: {p["chrome"]};
}}
QTabWidget::pane {{
    border: 1px solid {p["separator"]};
    background: {p["chrome"]};
}}
QTabBar {{
    background: {p["chrome"]};
}}
QTabBar::tab {{
    background: transparent;
    color: {p["text_muted"]};
    padding: 6px 12px;
    border: none;
    border-top: 2px solid transparent;
}}
QTabBar::tab:selected {{
    background: {p["panel"]};
    color: {p["text"]};
    border-top: 2px solid {p["accent"]};
}}
QTabBar::tab:hover {{
    background: {p["panel"]};
    color: {p["text"]};
}}
QTabBar::close-button {{
    image: url({_CLOSE_PATH});
    width: 12px;
    height: 12px;
}}
QTabBar::close-button:hover {{
    background: #e81123;
    border-radius: 3px;
}}
QStatusBar {{
    background-color: {p["chrome"]};
    color: {p["text_muted"]};
    border-bottom-left-radius: {corner_radius}px;
    border-bottom-right-radius: {corner_radius}px;
}}
QStatusBar::item {{
    border: none;
}}
QPushButton {{
    background-color: {p["input"]};
    color: {p["text"]};
    border: 1px solid {p["border"]};
    border-radius: 6px;
    padding: 6px 14px;
    min-height: 30px;
}}
QPushButton:hover {{
    background-color: {p["hover"]};
    border: 1px solid {p["border_hover"]};
}}
QPushButton:pressed {{
    background-color: {p["pressed"]};
}}
QPushButton:disabled {{
    color: {p["text_disabled"]};
    background-color: {p["pressed"]};
}}
QPushButton:default {{
    background-color: {p["accent"]};
    color: white;
    border: none;
}}
QPushButton:default:hover {{
    background-color: {p["accent_hover"]};
}}
QPushButton:default:pressed {{
    background-color: {p["accent_pressed"]};
}}
QLineEdit, QComboBox {{
    background-color: {p["input"]};
    color: {p["text"]};
    border: 1px solid {p["border"]};
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: {p["accent"]};
    selection-color: white;
}}
QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {p["accent"]};
}}
QComboBox::drop-down {{
    border: none;
    background: {p["input"]};
    width: 24px;
}}
QComboBox::down-arrow {{
    image: url({_DOWN_ARROW_PATH});
    width: 12px;
    height: 12px;
}}
QComboBox:editable {{
    background-color: {p["input"]};
    color: {p["text"]};
}}
QComboBox QLineEdit {{
    background-color: transparent;
    color: {p["text"]};
    border: none;
}}
QComboBox QAbstractItemView {{
    background-color: {p["panel"]};
    color: {p["text"]};
    selection-background-color: {p["accent"]};
    selection-color: white;
}}
QCheckBox {{
    color: {p["text"]};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {p["border"]};
    border-radius: 3px;
    background: {p["input"]};
}}
QCheckBox::indicator:checked {{
    background: {p["accent"]};
    border: 1px solid {p["accent"]};
}}
QCheckBox::indicator:disabled {{
    background: {p["panel"]};
}}
QListWidget {{
    background-color: {p["panel"]};
    color: {p["text"]};
    border: 1px solid {p["separator"]};
    border-radius: 6px;
    outline: none;
}}
QListWidget::item {{
    padding: 4px 8px;
}}
QListWidget::item:selected {{
    background-color: {p["accent"]};
    color: white;
}}
QListWidget::item:hover {{
    background-color: {p["input"]};
}}
QTextEdit {{
    background-color: {p["bg"]};
    color: {p["text"]};
    border: none;
    selection-background-color: {p["accent"]};
    selection-color: white;
}}
QLabel {{
    color: {p["text"]};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {p["border"]};
    min-height: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p["scroll_hover"]};
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {p["border"]};
    min-width: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {p["scroll_hover"]};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    border: none;
    background: none;
}}
QSplitter::handle {{
    background: {p["pressed"]};
}}
QDialogButtonBox QPushButton {{
    min-width: 80px;
    min-height: 30px;
}}
"""


# The default-radius sheets, for anything that only needs to read
# them (the smoke test asserts on their rules).
DARK_STYLESHEET = novelshop_stylesheet(THEME_DARK)
LIGHT_STYLESHEET = novelshop_stylesheet(THEME_LIGHT)


def style_popup_menu(menu) -> None:
    """Let a pop-up menu render borderless with rounded corners.

    Two separate things draw a border around a menu, and the style
    sheet only removes one of them. The sheet's border-radius
    needs a translucent window to show (otherwise the corners stay
    square, filled with the menu's background). And the light
    border around the menu is the native Windows frame, which no
    style sheet can touch — dropping the frame removes it. Both
    are set here, before the menu is first shown.
    """
    from PySide6.QtCore import Qt

    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    menu.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)


def apply_theme(theme: str, corner_radius: int = DEFAULT_CORNER_RADIUS) -> None:
    """Apply a Novelshop theme to the whole application.

    Unknown names fall back to Novelshop Light. The corner radius
    rounds the window's corners (0 when maximized, so it fills the
    screen).
    """
    app = QApplication.instance()
    if app is None:
        return
    app.setStyleSheet(novelshop_stylesheet(theme, corner_radius))
