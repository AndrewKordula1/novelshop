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
"""A frameless window: no native title bar, so the menu bar is the
top bar, like Photoshop's.

The native title bar is drawn by Windows, not by Qt, so no style
sheet can theme it. The only way to make it seamless with the app
is to drop it. That means this file has to bring back the behaviour
the native bar used to provide for free:

- CaptionButton — one of the three buttons (minimize, maximize /
  restore, close), 46x38 like the menu bar, with its glyph painted
  by hand so it looks the same on any theme.
- DraggableMenuBar — the menu bar itself, taller than usual (38px,
  like PhotoCraft's) and carrying the three caption buttons on its
  right, as its corner widget. Drag its empty area to move the
  window, double-click it to maximize or restore, drag it to the
  top of the screen to maximize.
- EdgeResizer — an application-level event filter that gives a
  frameless window its resize handles back: drag any edge or
  corner, with the right cursor while you hover one. It stays out
  of the menu bar's way (the bar drags, the buttons click) and
  out of modal dialogs' way.
- enable_drop_shadow — asks Windows to draw a drop shadow around
  a frameless window again (it loses the native one), via the
  CS_DROPSHADOW window-class style. Windows only; a no-op
  elsewhere.

Nothing in here is Windows-only, though the sizes and the red
close-button hover are Windows' conventions.
"""

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt
from PySide6.QtGui import QCursor, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenuBar,
    QPushButton,
    QWidget,
)

_CAPTION_HEIGHT = 38
_CAPTION_BUTTON_WIDTH = 46
_MENU_BAR_HEIGHT = 38
_RESIZE_BORDER = 8
_TOP_RESIZE_BORDER = 5


def enable_drop_shadow(window) -> None:
    """Give a frameless window a native drop shadow (Windows only).

    A frameless window loses the shadow Windows draws around a
    normal window, so it sits flat against the desktop and looks
    pasted-on. The CS_DROPSHADOW window-class style asks Windows
    to draw the shadow back, without changing the window's layout
    or content at all. It is a no-op anywhere but Windows, and if
    it fails (or the style is already set) the window simply has
    no shadow — the app still works exactly as before.
    """
    import sys

    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        hwnd = int(window.winId())
        if not hwnd:
            return
        user32 = ctypes.windll.user32
        user32.GetClassLongPtrW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
        ]
        user32.GetClassLongPtrW.restype = ctypes.c_void_p
        user32.SetClassLongPtrW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
        ]
        user32.SetClassLongPtrW.restype = ctypes.c_void_p
        # GCL_STYLE is -26; CS_DROPSHADOW is 0x00020000.
        style = user32.GetClassLongPtrW(hwnd, -26)
        if not style:
            return
        style = int(style)
        if style & 0x00020000:
            return
        user32.SetClassLongPtrW(hwnd, -26, style | 0x00020000)
    except Exception:
        return


class CaptionButton(QPushButton):
    """One caption button, its glyph painted by hand.

    ``kind`` is "min", "max", "restore", or "close". The glyph is
    drawn with the button's text color, so the theme's style sheet
    controls it. The background (including the red close hover)
    comes from the style sheet too — this class only draws the mark.
    """

    def __init__(self, kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._kind = kind
        self.setFixedSize(_CAPTION_BUTTON_WIDTH, _CAPTION_HEIGHT)
        self.setObjectName(f"caption{kind.capitalize()}Button")
        self.setFlat(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_kind(self, kind: str) -> None:
        """Switch the glyph (maximize <-> restore)."""
        self._kind = kind
        self.setObjectName(f"caption{kind.capitalize()}Button")
        self.update()

    def paintEvent(self, event) -> None:
        # The background first, from the style sheet.
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self.palette().color(QPalette.ColorRole.ButtonText)
        painter.setPen(QPen(color, 1))
        cx = self.width() // 2
        cy = self.height() // 2
        half = 5
        if self._kind == "min":
            # A short line, low in the box, like Windows'.
            painter.drawLine(cx - half, cy + 3, cx + half, cy + 3)
        elif self._kind == "max":
            painter.drawRect(cx - half, cy - half, 2 * half, 2 * half)
        elif self._kind == "restore":
            # Two overlapping squares: the back one top-right, the
            # front one bottom-left, filled with the button's
            # background so the back square's lines stop at its edge.
            painter.drawRect(cx - 1, cy - half, 7, 7)
            bg = self.palette().color(QPalette.ColorRole.Button)
            painter.fillRect(cx - half, cy - 1, 7, 7, bg)
            painter.drawRect(cx - half, cy - 1, 7, 7)
        elif self._kind == "close":
            painter.drawLine(cx - half, cy - half, cx + half, cy + half)
            painter.drawLine(cx + half, cy - half, cx - half, cy + half)


class DraggableMenuBar(QMenuBar):
    """The menu bar as the window's top bar, like Photoshop's.

    ``window`` is the main window it belongs to. It is taller than
    a standard menu bar (32px) and carries the three caption
    buttons (minimize, maximize/restore, close) on its right, as
    its corner widget. Drag its empty area to move the window,
    double-click it to maximize or restore, drag it to the top of
    the screen to maximize. Clicking a menu still opens the menu;
    only the empty area drags.
    """

    def __init__(self, window, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._window = window
        self.setFixedHeight(_MENU_BAR_HEIGHT)
        # The app's name, centered in the bar like a native title.
        # It ignores the mouse, so clicks pass through to the bar
        # and dragging still works from anywhere on it.
        self._title_label = QLabel("Novelshop", self)
        self._title_label.setObjectName("titleBarLabel")
        self._title_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._min_button = CaptionButton("min", self)
        self._min_button.setToolTip("Minimize")
        self._min_button.setFixedHeight(_MENU_BAR_HEIGHT)
        self._min_button.clicked.connect(window.showMinimized)
        self._max_button = CaptionButton("max", self)
        self._max_button.setToolTip("Maximize")
        self._max_button.setFixedHeight(_MENU_BAR_HEIGHT)
        self._max_button.clicked.connect(self._toggle_maximize)
        self._close_button = CaptionButton("close", self)
        self._close_button.setToolTip("Close")
        self._close_button.setFixedHeight(_MENU_BAR_HEIGHT)
        self._close_button.clicked.connect(window.close)
        buttons = QWidget(self)
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(0)
        buttons_layout.addWidget(self._min_button)
        buttons_layout.addWidget(self._max_button)
        buttons_layout.addWidget(self._close_button)
        self.setCornerWidget(buttons, Qt.Corner.TopRightCorner)
        self._drag_pos: QPoint | None = None
        self.update_maximize_button()
        self._center_title()

    def _center_title(self) -> None:
        """Put the app name in the middle of the bar."""
        label = self._title_label
        width = label.sizeHint().width()
        x = (self.width() - width) // 2
        label.setGeometry(x, 0, width, self.height())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._center_title()

    def is_dragging(self) -> bool:
        """True while the user is dragging the window by this bar."""
        return self._drag_pos is not None

    def is_over_button(self, global_pos: QPoint) -> bool:
        """True if a screen position is on one of the three buttons."""
        for button in (self._min_button, self._max_button, self._close_button):
            top_left = button.mapToGlobal(QPoint(0, 0))
            if QRect(top_left, button.size()).contains(global_pos):
                return True
        return False

    def update_maximize_button(self) -> None:
        """Show restore when maximized, maximize when not."""
        if self._window.isMaximized():
            self._max_button.set_kind("restore")
            self._max_button.setToolTip("Restore")
        else:
            self._max_button.set_kind("max")
            self._max_button.setToolTip("Maximize")

    def _toggle_maximize(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()
        self.update_maximize_button()

    def _on_empty_area(self, event) -> bool:
        """True if a mouse event lands on the bar's empty area (not
        on a menu item). Only the empty area drags or maximizes."""
        return self.actionAt(event.position().toPoint()) is None

    def mousePressEvent(self, event) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not self._window.isMaximized()
            and self._on_empty_area(event)
        ):
            self._drag_pos = event.globalPosition().toPoint()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint()
            # Dragged to the top of the screen: maximize, like Windows.
            if new_pos.y() <= 0:
                self._drag_pos = None
                self._window.showMaximized()
                self.update_maximize_button()
                return
            self._window.move(self._window.pos() + (new_pos - self._drag_pos))
            self._drag_pos = new_pos
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._on_empty_area(event)
        ):
            self._toggle_maximize()
            return
        super().mouseDoubleClickEvent(event)


class EdgeResizer(QObject):
    """Gives a frameless window its resize handles back.

    An application-level event filter: the window's edges are
    covered by the central widget, so the window itself never sees
    the mouse there. It watches every mouse move and press, and
    when one lands within a few pixels of an edge or corner it
    starts a resize, with the matching cursor while hovering.
    """

    def __init__(self, window) -> None:
        super().__init__(window)
        self._window = window
        self._resize_dir: set[str] | None = None
        self._start_pos: QPoint | None = None
        self._start_geom: QRect | None = None
        self._cursor_override: Qt.CursorShape | None = None
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def _edge_at(self, global_pos: QPoint) -> set[str] | None:
        """Which edges a screen position is within the resize zone of."""
        window = self._window
        if window.isMaximized() or window.isMinimized():
            return None
        if not window.geometry().contains(global_pos):
            return None
        # A modal dialog owns the mouse; leave the window alone.
        if QApplication.activeModalWidget() is not None:
            return None
        title_bar = getattr(window, "_menu_bar", None)
        if title_bar is not None:
            if title_bar.is_dragging():
                return None
            if title_bar.is_over_button(global_pos):
                return None
            # The menu bar drags the window; only its top strip
            # (a few pixels) resizes, like the native bar.
            pos = window.mapFromGlobal(global_pos)
            top_left = title_bar.mapTo(window, QPoint(0, 0))
            if (
                QRect(top_left, title_bar.size()).contains(pos)
                and pos.y() >= _TOP_RESIZE_BORDER
            ):
                return None
        pos = window.mapFromGlobal(global_pos)
        rect = window.rect()
        edges: set[str] = set()
        if pos.x() < _RESIZE_BORDER:
            edges.add("left")
        if pos.x() > rect.width() - _RESIZE_BORDER:
            edges.add("right")
        if pos.y() < _TOP_RESIZE_BORDER:
            edges.add("top")
        if pos.y() > rect.height() - _RESIZE_BORDER:
            edges.add("bottom")
        return edges if edges else None

    @staticmethod
    def _cursor_for(edges: set[str]) -> Qt.CursorShape:
        if ("left" in edges and "top" in edges) or (
            "right" in edges and "bottom" in edges
        ):
            return Qt.CursorShape.SizeFDiagCursor
        if ("right" in edges and "top" in edges) or (
            "left" in edges and "bottom" in edges
        ):
            return Qt.CursorShape.SizeBDiagCursor
        if "left" in edges or "right" in edges:
            return Qt.CursorShape.SizeHorCursor
        return Qt.CursorShape.SizeVerCursor

    def _set_override_cursor(self, shape: Qt.CursorShape | None) -> None:
        # The override cursor is a stack: push once per shape, and
        # pop before pushing a different one, so it never leaks.
        if self._cursor_override == shape:
            return
        if self._cursor_override is not None:
            QApplication.restoreOverrideCursor()
        if shape is not None:
            QApplication.setOverrideCursor(QCursor(shape))
        self._cursor_override = shape

    def eventFilter(self, obj, event) -> bool:
        try:
            return self._filter_event(event)
        except RuntimeError:
            # The window is gone (shutting down); stop filtering.
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
            return False

    def _filter_event(self, event) -> bool:
        window = self._window
        if window.isMinimized():
            self._set_override_cursor(None)
            return False
        if event.type() == QEvent.Type.MouseMove:
            if self._resize_dir is not None:
                self._do_resize(event.globalPosition().toPoint())
                return False
            edges = self._edge_at(event.globalPosition().toPoint())
            if edges:
                self._set_override_cursor(self._cursor_for(edges))
            else:
                self._set_override_cursor(None)
        elif event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                edges = self._edge_at(event.globalPosition().toPoint())
                if edges:
                    self._resize_dir = edges
                    self._start_pos = event.globalPosition().toPoint()
                    self._start_geom = window.geometry()
                    return True
        elif event.type() == QEvent.Type.MouseButtonRelease:
            if self._resize_dir is not None:
                self._resize_dir = None
                self._set_override_cursor(None)
                return True
        return False

    def _do_resize(self, global_pos: QPoint) -> None:
        delta = global_pos - self._start_pos
        geom = QRect(self._start_geom)
        min_w = max(self._window.minimumWidth(), 1)
        min_h = max(self._window.minimumHeight(), 1)
        if "left" in self._resize_dir:
            geom.setLeft(min(geom.left() + delta.x(), geom.right() - min_w + 1))
        if "right" in self._resize_dir:
            geom.setRight(max(geom.right() + delta.x(), geom.left() + min_w - 1))
        if "top" in self._resize_dir:
            geom.setTop(min(geom.top() + delta.y(), geom.bottom() - min_h + 1))
        if "bottom" in self._resize_dir:
            geom.setBottom(max(geom.bottom() + delta.y(), geom.top() + min_h - 1))
        self._window.setGeometry(geom)
