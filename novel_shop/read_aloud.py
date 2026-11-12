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
"""Read aloud: hear the current document (or selection) spoken.

Uses Qt's text-to-speech, which speaks through the system's own
voices — on Windows that is the built-in Windows voices, so there
is nothing to install and no internet. It reads the selected text
if there is a selection, otherwise the whole document. If the
system has no speech voices, speaking does nothing and the caller
is told so; the app still starts and runs as normal.
"""

from PySide6.QtCore import QObject, Signal

try:
    from PySide6.QtTextToSpeech import QTextToSpeech
except ImportError:  # Qt built without text-to-speech
    QTextToSpeech = None


class ReadAloud(QObject):
    """A thin wrapper around Qt's text-to-speech engine."""

    finished = Signal()  # speaking ended, naturally or by stopping

    def __init__(self):
        super().__init__()
        self._engine = QTextToSpeech() if QTextToSpeech is not None else None
        if self._engine is not None:
            self._engine.stateChanged.connect(self._on_state_changed)

    @property
    def available(self) -> bool:
        """Whether text-to-speech exists in this Qt build."""
        return self._engine is not None

    @property
    def has_voices(self) -> bool:
        """Whether the system has a voice to speak with."""
        return bool(self._engine and self._engine.availableVoices())

    @property
    def is_speaking(self) -> bool:
        return bool(
            self._engine
            and self._engine.state() == QTextToSpeech.State.Speaking
        )

    @property
    def state_changed(self):
        """Signal fired when speaking starts, stops, or errors."""
        return self._engine.stateChanged if self._engine is not None else None

    def speak(self, text: str) -> bool:
        """Speak text. False if there is nothing to speak with.

        Returns True if speaking started (or was attempted with a
        voice); False when there is no engine or no voice.
        """
        if self._engine is None or not text.strip():
            return False
        if not self.has_voices:
            return False
        self._engine.say(text)
        return True

    def stop(self) -> None:
        """Stop speaking, if anything is being spoken."""
        if self._engine is not None:
            self._engine.stop()

    def _on_state_changed(self, state) -> None:
        """Follow the engine: finished when it goes back to Ready."""
        if state == QTextToSpeech.State.Ready:
            self.finished.emit()
