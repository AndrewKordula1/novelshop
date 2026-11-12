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
"""Reverse dictionary: describe a word, get the word.

An inverted index over WordNet definitions, built once and kept.
For each synset, the words in its definition (and its lemmas) are
indexed; a description is tokenized the same way, and synsets are
ranked by how many of the description's words they contain, weighted
by how rare those words are across definitions (a word that appears
in few definitions counts more). It works best for short
descriptions whose words appear in a definition — "a fear of
heights" finds acrophobia, "false belief" finds misbelieve. A
natural sentence whose wording differs from the definition will not
match: the index only knows the words in a definition, so
"someone who is lying but does not know they are" does not find
confabulate, whose definition says "unconsciously replace fact with
fantasy". That is the limit of a keyword index, and it is why a
reverse dictionary is not a thesaurus.

The index is built by reading WordNet's own SQLite database in
bulk, which takes a few seconds the first time it is used in a
session. (Asking wn for each synset one at a time takes over a
minute.) If the database layout ever changes, it falls back to
building through wn, which is slow but works.
"""

import math
import re
import sqlite3
from collections import defaultdict

from novel_shop import lexicon

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "for",
    "with", "by", "at", "from", "as", "is", "are", "was", "were", "be",
    "been", "it", "its", "they", "them", "their", "he", "she", "his",
    "her", "who", "whom", "that", "which", "what", "when", "where",
    "someone", "something", "one", "two", "not", "no", "do", "does",
    "did", "you", "your", "we", "our", "this", "these", "those",
    "have", "has", "had", "will", "would", "can", "could", "should",
    "may", "might", "must", "about", "into", "over", "under", "out",
    "up", "down", "off", "again", "then", "than", "so", "such", "very",
    "just", "also", "more", "most", "other", "some", "any", "all",
    "each", "both", "either", "neither", "only", "own", "same", "too",
    "being", "am", "person", "people",
}

_POS_LABELS = {
    "n": "noun",
    "v": "verb",
    "a": "adjective",
    "s": "adjective",
    "r": "adverb",
}

_index = None  # (postings, idf, entries) once built


def _tokens(text: str) -> list[str]:
    return [
        word
        for word in re.findall(r"[a-z]+", text.lower())
        if word not in _STOPWORDS
    ]


def _build_index_sql():
    """Build the index by reading WordNet's database in bulk.

    Returns (postings, idf, entries) where postings maps a word to
    the synsets whose definition or lemmas contain it, idf weights
    each word by rarity, and entries holds (word, part of speech,
    definition) per synset. Raises if the layout is not as expected.
    """
    import wn

    db_path = wn.config.data_directory / "wn.db"
    connection = sqlite3.connect(db_path)
    try:
        synset_rows = connection.execute(
            "SELECT rowid, pos FROM synsets"
        ).fetchall()
        # One definition per synset (the synset-level one).
        definitions = {
            rowid: definition
            for rowid, definition in connection.execute(
                "SELECT synset_rowid, definition FROM definitions "
                "WHERE sense_rowid IS NULL"
            ).fetchall()
        }
        # The lemmas of each synset, most common first.
        lemmas = defaultdict(list)
        for synset_rowid, form in connection.execute(
            "SELECT s.synset_rowid, f.form FROM senses s "
            "JOIN forms f ON f.entry_rowid = s.entry_rowid "
            "AND f.rank = 0 ORDER BY s.synset_rank"
        ).fetchall():
            lemmas[synset_rowid].append(form)
    finally:
        connection.close()
    entries = []
    postings: dict[str, set[int]] = defaultdict(set)
    for index, (rowid, pos) in enumerate(synset_rows):
        definition = definitions.get(rowid, "")
        forms = lemmas.get(rowid, [])
        word = forms[0] if forms else ""
        entries.append(
            (word, _POS_LABELS.get(pos, pos), definition)
        )
        words = set(_tokens(definition))
        for form in forms:
            words.update(_tokens(form))
        for token in words:
            postings[token].add(index)
    total = len(entries)
    idf = {
        token: math.log(total / len(synsets))
        for token, synsets in postings.items()
    }
    return postings, idf, entries


def _build_index_api():
    """Build the index through wn, one synset at a time.

    Slow (over a minute), but it works whatever the database looks
    like. Only used if the bulk read fails.
    """
    wordnet = lexicon.load_wordnet()
    synsets = list(wordnet.synsets())
    entries = []
    postings: dict[str, set[int]] = defaultdict(set)
    for index, synset in enumerate(synsets):
        forms = synset.lemmas()
        word = forms[0] if forms else ""
        entries.append(
            (
                word,
                _POS_LABELS.get(synset.pos, synset.pos),
                synset.definition(),
            )
        )
        words = set(_tokens(synset.definition()))
        for form in forms:
            words.update(_tokens(form))
        for token in words:
            postings[token].add(index)
    total = len(entries)
    idf = {
        token: math.log(total / len(synsets))
        for token, synsets in postings.items()
    }
    return postings, idf, entries


def _get_index():
    """The reverse index, built once and kept for the session."""
    global _index
    if _index is not None:
        return _index
    try:
        _index = _build_index_sql()
    except Exception:
        _index = _build_index_api()
    return _index


def is_ready() -> bool:
    """Whether the index is already built (so a search is instant)."""
    return _index is not None


def reverse_lookup(query: str, limit: int = 10) -> list[dict]:
    """Words whose definitions match a description, best first.

    Each result is a word, its part of speech, and its definition.
    Empty if WordNet is not available, or nothing matches.
    """
    if not query or lexicon.load_wordnet() is None:
        return []
    query_words = set(_tokens(query))
    if not query_words:
        return []
    postings, idf, entries = _get_index()
    scores: dict[int, float] = defaultdict(float)
    matched: dict[int, int] = defaultdict(int)
    for word in query_words:
        for index in postings.get(word, set()):
            scores[index] += idf.get(word, 0.0)
            matched[index] += 1
    ranked = sorted(
        scores.items(),
        key=lambda item: (matched[item[0]], item[1]),
        reverse=True,
    )
    results = []
    seen: set[str] = set()
    for index, _score in ranked:
        word, pos, definition = entries[index]
        if not word or word.lower() in seen:
            continue
        seen.add(word.lower())
        results.append(
            {"word": word, "pos": pos, "definition": definition}
        )
        if len(results) >= limit:
            break
    return results
