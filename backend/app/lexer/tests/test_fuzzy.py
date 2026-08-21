"""
test_fuzzy.py - Pytest test cases for fuzzy keyword matching logic.
"""

from backend.app.lexer.fuzzy_match import suggest_keyword


def test_fuzzy_keyword_suggestions():
    # Test valid typos of reserved keywords
    assert suggest_keyword("whlie") == "while"
    assert suggest_keyword("retrun") == "return"
    assert suggest_keyword("itn") == "int"


def test_fuzzy_unrelated_identifiers():
    # Test normal identifiers that should NOT generate keyword suggestions
    assert suggest_keyword("count") is None
    assert suggest_keyword("price") is None
    assert suggest_keyword("active") is None
    assert suggest_keyword("my_var") is None


def test_fuzzy_exact_keywords():
    # Test exact keywords - should return None since they are valid keywords
    assert suggest_keyword("while") is None
    assert suggest_keyword("return") is None
    assert suggest_keyword("int") is None
