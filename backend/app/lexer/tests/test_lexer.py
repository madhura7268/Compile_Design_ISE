"""
test_lexer.py - Pytest test cases for ToyLang Lexical Engine.
"""

from backend.app.lexer.lexer import tokenize


def test_example_int_count():
    code = "int count = 10;"
    result = tokenize(code)

    tokens = result["tokens"]
    symbol_table = result["symbol_table"]

    # Verify token types
    token_types = [t["type"] for t in tokens]
    assert token_types == ["INT", "ID", "ASSIGN", "INT_NUM", "SEMI"]

    # Verify line and column numbers
    assert tokens[0] == {"type": "INT", "value": "int", "line": 1, "col": 1}
    assert tokens[1] == {"type": "ID", "value": "count", "line": 1, "col": 5}
    assert tokens[2] == {"type": "ASSIGN", "value": "=", "line": 1, "col": 11}
    assert tokens[3] == {"type": "INT_NUM", "value": "10", "line": 1, "col": 13}
    assert tokens[4] == {"type": "SEMI", "value": ";", "line": 1, "col": 15}

    # Verify symbol table entry
    assert symbol_table == [
        {"name": "count", "type": "int", "scope": "global", "line": 1}
    ]


def test_all_keywords():
    code = "int float bool if else while return print"
    result = tokenize(code)
    types = [t["type"] for t in result["tokens"]]
    assert types == [
        "INT",
        "FLOAT",
        "BOOL",
        "IF",
        "ELSE",
        "WHILE",
        "RETURN",
        "PRINT",
    ]


def test_literals_and_identifiers():
    code = 'count 10 25.5 "hello world"'
    result = tokenize(code)
    tokens = result["tokens"]
    assert len(tokens) == 4
    assert tokens[0]["type"] == "ID"
    assert tokens[0]["value"] == "count"
    assert tokens[1]["type"] == "INT_NUM"
    assert tokens[1]["value"] == "10"
    assert tokens[2]["type"] == "FLOAT_NUM"
    assert tokens[2]["value"] == "25.5"
    assert tokens[3]["type"] == "STRING_LITERAL"
    assert tokens[3]["value"] == '"hello world"'


def test_operators_and_delimiters():
    code = "+ - * / % == != <= >= < > = ( ) { } ; ,"
    result = tokenize(code)
    types = [t["type"] for t in result["tokens"]]
    assert types == [
        "PLUS",
        "MINUS",
        "TIMES",
        "DIVIDE",
        "MOD",
        "EQ",
        "NE",
        "LE",
        "GE",
        "LT",
        "GT",
        "ASSIGN",
        "LPAREN",
        "RPAREN",
        "LBRACE",
        "RBRACE",
        "SEMI",
        "COMMA",
    ]


def test_comments_stripping():
    code = """
    // Single line comment
    int a = 5; /* Multi line
    comment */ float b = 10.0;
    """
    result = tokenize(code)
    types = [t["type"] for t in result["tokens"]]
    assert types == [
        "INT",
        "ID",
        "ASSIGN",
        "INT_NUM",
        "SEMI",
        "FLOAT",
        "ID",
        "ASSIGN",
        "FLOAT_NUM",
        "SEMI",
    ]


def test_fuzzy_warning_token():
    code = "whlie count = 5;"
    result = tokenize(code)
    tok = result["tokens"][0]

    assert tok["type"] == "ID"
    assert tok["value"] == "whlie"
    assert tok["warning"] == "Did you mean 'while'?"
    assert tok["suggested"] == "while"


def test_lexical_error_handling():
    code = "int @ count = 10;"
    result = tokenize(code)
    tokens = result["tokens"]

    err_token = tokens[1]
    assert err_token["type"] == "LEXICAL_ERROR"
    assert err_token["value"] == "@"
    assert err_token["line"] == 1
    assert err_token["col"] == 5
    assert err_token["message"] == "Illegal character '@'"


def test_multiline_line_col_tracking():
    code = "int a = 1;\nfloat b = 2.0;"
    result = tokenize(code)
    tokens = result["tokens"]

    # float should be on line 2, col 1
    float_tok = tokens[5]
    assert float_tok["type"] == "FLOAT"
    assert float_tok["line"] == 2
    assert float_tok["col"] == 1
