"""
fuzzy_match.py - Fuzzy Keyword Correction using difflib.
"""

import difflib
from .tokens import KEYWORDS

RESERVED_KEYWORDS = list(KEYWORDS.keys())


def suggest_keyword(word):
    """Suggest reserved keyword corrections for mistyped identifiers."""
    if word in RESERVED_KEYWORDS:
        return None

    matches = difflib.get_close_matches(word, RESERVED_KEYWORDS, n=1, cutoff=0.65)
    if matches:
        return matches[0]

    return None
