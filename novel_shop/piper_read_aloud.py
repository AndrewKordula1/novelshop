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
"""Piper read aloud: a local neural voice, sentence by sentence.

Piper is a fast, offline neural text-to-speech engine (MIT). It
synthesizes a sentence to a WAV file in a fraction of a second, and
the app plays the WAVs in order through Qt's media player — so
reading starts almost at once and stopping is clean. The voice is
a model file (.onnx + .onnx.json) the user downloads once and picks
in the app; without one, this engine is unavailable and the system
voices are used instead.

Synthesis runs in a worker thread, so the editor stays responsive
while a chapter is being read. The worker synthesizes one sentence
at a time; the player starts on the first as soon as it is ready.
"""

import re
import wave
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

try:
    from piper import PiperVoice
except ImportError:  # piper-tts not installed
    PiperVoice = None

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“\(\[])")
_MARKDOWN = re.compile(r"\*\*\*|\*\*|\*|<u>|</u>")
# Titles and abbreviations that end with a full stop but are not the
# end of a sentence; a piece ending in one is glued to the next.
_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "st", "sr", "jr", "vs", "etc", "e.g", "i.e",
}


def strip_markdown(text: str) -> str:
    """Remove the bold/italic/underline markers, so they are not read."""
    return _MARKDOWN.sub("", text)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, on paragraph breaks and punctuation.

    A paragraph break always starts a new piece; inside a paragraph,
    a sentence ends at . ! or ? followed by a capital (or a quote or
    a bracket). A piece that ends in a title or abbreviation ("Mr.",
    "Dr.") is glued back to the next piece, so it is read as one.
    """
    pieces: list[str] = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        for piece in _SENTENCE_END.split(paragraph):
            piece = piece.strip()
            if piece:
                pieces.append(piece)
    sentences: list[str] = []
    for piece in pieces:
        last = sentences[-1].rstrip() if sentences else ""
        if last.endswith("."):
            # The word before the full stop, without it.
            word = last[:-1].rsplit(None, 1)[-1].lower()
            if word in _ABBREVIATIONS:
                sentences[-1] = sentences[-1] + " " + piece
                continue
        sentences.append(piece)
    return sentences


class _SynthesisWorker(QThread):
    """Synthesize sentences to WAV files, one at a time, in order."""

    chunk_ready = Signal(int, str)  # sentence index, WAV path
    done = Signal()

    def __init__(self, voice, sentences: list[str], folder: str):
        super().__init__()
        self._voice = voice
        self._sentences = sentences
        self._folder = folder
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    def run(self) -> None:
        for index, sentence in enumerate(self._sentences):
            if self._stop_requested:
                break
            path = str(Path(self._folder) / f"sentence_{index:04d}.wav")
            try:
                with wave.open(path, "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(self._voice.config.sample_rate)
                    for chunk in self._voice.synthesize(sentence):
                        wav.writeframes(chunk.audio_int16_bytes)
            except Exception:
                continue
            self.chunk_ready.emit(index, path)
        self.done.emit()


class PiperReadAloud(QObject):
    """A neural voice, read aloud through the media player."""

    finished = Signal()  # playback ended, naturally or by stopping

    def __init__(self, voice_path: str = ""):
        super().__init__()
        self._voice_path = voice_path
        self._voice = None  # loaded lazily, on the first speak
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._player.mediaStatusChanged.connect(
            self._on_media_status_changed
        )
        self._worker: _SynthesisWorker | None = None
        self._worker_done = True
        self._queue: list[tuple[int, str]] = []  # (index, WAV path)
        self._playing_index: int | None = None
        self._temp_dir = None
        self._speaking = False

    # -- availability ----------------------------------------------------

    @property
    def available(self) -> bool:
        """Whether Piper is installed and a voice file is set."""
        return PiperVoice is not None and self.voice_ready

    @property
    def voice_ready(self) -> bool:
        """Whether the voice file (and its config) exist."""
        if not self._voice_path:
            return False
        model = Path(self._voice_path)
        return model.is_file() and Path(str(model) + ".json").is_file()

    def set_voice(self, voice_path: str) -> None:
        """Point at a different voice file (.onnx)."""
        self._voice_path = voice_path
        self._voice = None  # reload it on the next speak

    # -- speaking ----------------------------------------------------------

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def speak(self, text: str) -> bool:
        """Read text aloud. False if there is nothing to speak with.

        Returns True once the first sentence is being prepared; the
        finished signal fires when the last one has been played.
        """
        if not self.available:
            return False
        sentences = split_sentences(strip_markdown(text))
        if not sentences:
            return False
        self.stop()
        self._load_voice()
        if self._voice is None:
            return False
        import tempfile

        self._temp_dir = tempfile.TemporaryDirectory(prefix="novel-shop-tts-")
        self._worker_done = False
        self._queue = []
        self._playing_index = None
        self._speaking = True
        self._worker = _SynthesisWorker(
            self._voice, sentences, self._temp_dir.name
        )
        self._worker.chunk_ready.connect(self._on_chunk_ready)
        self._worker.done.connect(self._on_worker_done)
        self._worker.start()
        return True

    def stop(self) -> None:
        """Stop speaking and drop whatever has not been played yet."""
        if self._worker is not None:
            self._worker.request_stop()
            self._worker.wait()
            self._worker = None
        self._player.stop()
        self._queue = []
        self._playing_index = None
        self._worker_done = True
        if self._speaking:
            self._speaking = False
            self.finished.emit()

    # -- internals ---------------------------------------------------------

    def _load_voice(self) -> None:
        """Load the voice model, once per voice file."""
        if self._voice is not None:
            return
        model = Path(self._voice_path)
        try:
            self._voice = PiperVoice.load(
                str(model), str(model) + ".json"
            )
        except Exception:
            self._voice = None

    def _on_chunk_ready(self, index: int, path: str) -> None:
        """A sentence is ready; queue it, and start playing if idle."""
        self._queue.append((index, path))
        self._queue.sort(key=lambda item: item[0])
        if self._playing_index is None:
            self._play_next()

    def _play_next(self) -> None:
        """Play the next queued sentence, or finish if there is none."""
        if not self._queue:
            self._playing_index = None
            if self._worker_done:
                self._speaking = False
                self.finished.emit()
            return
        index, path = self._queue.pop(0)
        self._playing_index = index
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()

    def _on_media_status_changed(self, status) -> None:
        """A sentence finished playing; move on to the next one."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._play_next()

    def _on_worker_done(self) -> None:
        """All sentences are synthesized; finish when the last plays."""
        self._worker_done = True
        if self._playing_index is None and not self._queue:
            self._speaking = False
            self.finished.emit()
