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
"""Dictionary and thesaurus, from WordNet (offline).

The words come from Princeton's WordNet, through the wn package and a
one-time data download (Open English WordNet). Everything is local
after that, so a lookup works with no internet. If wn is not
installed, or the data was never downloaded, the feature is off and
the menu items are greyed out — the same pattern as spellcheck.

Setup, once: pip install wn, then python -m wn download ewn:2020.
"""

_POS_LABELS = {
    "n": "noun",
    "v": "verb",
    "a": "adjective",
    "s": "adjective",  # satellite adjective: an adjective, worded by use
    "r": "adverb",
}

_wordnet = None
_wordnet_tried = False


def load_wordnet():
    """The WordNet object, or None if wn or its data is missing.

    Loaded once and kept. The wn import is lazy, so this module
    imports fine on a machine without wn installed.
    """
    global _wordnet, _wordnet_tried
    if _wordnet_tried:
        return _wordnet
    _wordnet_tried = True
    try:
        import wn
        from wn import morphy
    except ImportError:
        return None
    try:
        # All English lexicons, whichever version was downloaded,
        # with the lemmatizer so "running" finds "run".
        _wordnet = wn.Wordnet(lang="en", lemmatizer=morphy.morphy)
    except Exception:
        _wordnet = None
    return _wordnet


def is_available() -> bool:
    """True when WordNet is loaded and lookups will work."""
    return load_wordnet() is not None


def lookup(word: str) -> list[dict]:
    """Senses for a word, each with part of speech, definition, an
    example, synonyms and antonyms. Empty if the word is not in
    WordNet. Synonyms are the other words in the same synset, so they
    mean the same thing in that sense — not a flat list across
    senses."""
    wordnet = load_wordnet()
    if wordnet is None or not word:
        return []
    word_lower = word.lower()
    senses = []
    for synset in wordnet.synsets(word):
        synonyms = sorted(
            {
                lemma.replace("_", " ")
                for lemma in synset.lemmas()
                if lemma.replace("_", " ").lower() != word_lower
            }
        )
        antonyms = sorted(
            {
                ant.word().lemma().replace("_", " ")
                for sense in synset.senses()
                for ant in sense.get_related("antonym")
            }
        )
        examples = synset.examples()
        senses.append(
            {
                "pos": _POS_LABELS.get(synset.pos, synset.pos),
                "definition": synset.definition(),
                "example": examples[0] if examples else "",
                "synonyms": synonyms,
                "antonyms": antonyms,
            }
        )
    return senses


def synonyms(word: str, limit: int = 12) -> list[str]:
    """Synonyms for a word, across its senses, most common first.

    Deduplicated, the word itself left out, capped so the menu stays
    short."""
    word_lower = word.lower()
    found: list[str] = []
    seen = {word_lower}
    for sense in lookup(word):
        for synonym in sense["synonyms"]:
            if synonym.lower() not in seen:
                seen.add(synonym.lower())
                found.append(synonym)
                if len(found) >= limit:
                    return found
    return found
