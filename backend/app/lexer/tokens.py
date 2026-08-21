"""
tokens.py - Token Specifications for ToyLang Lexical Engine.

Defines reserved keywords and complete token tuples required by PLY (ply.lex).
"""

# Reserved keywords dictionary mapping keyword string -> token type
KEYWORDS = {
    "int": "INT",
    "float": "FLOAT",
    "bool": "BOOL",
    "if": "IF",
    "else": "ELSE",
    "while": "WHILE",
    "return": "RETURN",
    "print": "PRINT",
}

# Complete token specification for PLY lexer
tokens = (
    # Keyword token types
    "INT",
    "FLOAT",
    "BOOL",
    "IF",
    "ELSE",
    "WHILE",
    "RETURN",
    "PRINT",
    # Literals and Identifiers
    "ID",
    "INT_NUM",
    "FLOAT_NUM",
    "STRING_LITERAL",
    # Arithmetic Operators
    "PLUS",
    "MINUS",
    "TIMES",
    "DIVIDE",
    "MOD",
    # Relational & Assignment Operators
    "EQ",
    "NE",
    "LE",
    "GE",
    "LT",
    "GT",
    "ASSIGN",
    # Delimiters
    "LPAREN",
    "RPAREN",
    "LBRACE",
    "RBRACE",
    "SEMI",
    "COMMA",
)
