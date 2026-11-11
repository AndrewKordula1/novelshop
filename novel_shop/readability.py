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
"""Readability: Flesch-Kincaid grade and reading ease for a document.

It only measures two things — how long the sentences are and how
long the words are — and plugs them into the Flesch-Kincaid
formulas. It has no idea if a word is obscure or a sentence is
clear, so the grade is a rough gauge for "is this passage dense or
light", not a judgment of quality.

Syllables are counted by a rule of thumb, not a dictionary: a run
of vowels is one syllable, with corrections for a silent "e" and
for "-ed" after a t or d. That gets most ordinary words right, but
it is approximate — especially for fantasy names and invented
words, which it just sounds out by the same rules.
"""

import re
from dataclasses import dataclass

_VOWELS = "aeiouy"
# Abbreviations that end in a period but do not end a sentence.
_ABBREVIATIONS = (
    "mr", "mrs", "ms", "dr", "st", "sr", "jr", "vs", "etc", "e.g",
    "i.e", "prof", "gen", "col", "capt", "lt", "sgt", "rev", "hon",
)


@dataclass
class ReadabilityStats:
    words: int
    sentences: int
    syllables: int
    avg_words_per_sentence: float
    avg_syllables_per_word: float
    flesch_ease: float
    flesch_kincaid_grade: float

    def grade_label(self) -> str:
        """'Grade 7.2' — or '—' when there is nothing to measure."""
        if self.words == 0:
            return "—"
        return f"Grade {self.flesch_kincaid_grade:.1f}"

    def ease_label(self) -> str:
        """'Reading ease 72.4 (fairly easy)' — or '—' when empty."""
        if self.words == 0:
            return "—"
        if self.flesch_ease >= 90:
            word = "very easy"
        elif self.flesch_ease >= 80:
            word = "easy"
        elif self.flesch_ease >= 70:
            word = "fairly easy"
        elif self.flesch_ease >= 60:
            word = "standard"
        elif self.flesch_ease >= 50:
            word = "fairly difficult"
        elif self.flesch_ease >= 30:
            word = "difficult"
        else:
            word = "very difficult"
        return f"{self.flesch_ease:.1f} ({word})"


def count_syllables(word: str) -> int:
    """Syllables in one word, by the vowel-group rule of thumb.

    A run of vowels is one syllable; a final silent "e" is not one,
    but a final "-le" after a consonant is ("table", "simple").
    """
    word = word.lower().strip(".,;:!?\"'()[]{}")
    if not word:
        return 0
    count = 0
    prev_vowel = False
    for char in word:
        is_vowel = char in _VOWELS
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if len(word) > 2 and word.endswith("e"):
        count -= 1  # silent "e"
    if len(word) > 2 and word.endswith("ed") and word[-3] not in ("t", "d"):
        count -= 1  # "-ed" after anything but t/d is silent ("walked")
    if (
        len(word) > 2
        and word.endswith("le")
        and word[-3] not in _VOWELS
    ):
        count += 1  # "-le" after a consonant is a syllable
    return max(count, 1)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, keeping abbreviations glued.

    A sentence ends at a ".", "!" or "?" that is followed by a
    space and a capital (or the end of the text). "Mr. Aldric left."
    stays one sentence.
    """
    text = " ".join(text.split())
    if not text:
        return []
    sentences: list[str] = []
    start = 0
    for match in re.finditer(r"[.!?]+", text):
        end = match.end()
        # What follows the punctuation: a space, then a capital or
        # the end of the text means a sentence boundary.
        rest = text[end:].lstrip()
        if rest and not rest[0].isupper():
            continue
        # But not if the word before the period is an abbreviation.
        before = text[start:match.start()].strip().rsplit(" ", 1)
        if before and before[-1].lower().rstrip(".") in _ABBREVIATIONS:
            continue
        sentence = text[start:end].strip()
        if sentence:
            sentences.append(sentence)
        start = end
    tail = text[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def readability_stats(text: str) -> ReadabilityStats:
    """Flesch-Kincaid grade and reading ease for a document."""
    # Markdown markers are not words; strip them before counting.
    plain = re.sub(r"[*_`<>\[\]]", " ", text)
    words = [word for word in plain.split() if word.strip(".,;:!?\"'")]
    sentences = split_sentences(plain)
    word_count = len(words)
    sentence_count = len(sentences)
    syllable_count = sum(count_syllables(word) for word in words)
    if word_count == 0 or sentence_count == 0:
        return ReadabilityStats(
            words=word_count,
            sentences=sentence_count,
            syllables=syllable_count,
            avg_words_per_sentence=0.0,
            avg_syllables_per_word=0.0,
            flesch_ease=0.0,
            flesch_kincaid_grade=0.0,
        )
    avg_words = word_count / sentence_count
    avg_syllables = syllable_count / word_count
    ease = 206.835 - 1.015 * avg_words - 84.6 * avg_syllables
    grade = 0.39 * avg_words + 11.8 * avg_syllables - 15.59
    return ReadabilityStats(
        words=word_count,
        sentences=sentence_count,
        syllables=syllable_count,
        avg_words_per_sentence=avg_words,
        avg_syllables_per_word=avg_syllables,
        flesch_ease=ease,
        flesch_kincaid_grade=grade,
    )
