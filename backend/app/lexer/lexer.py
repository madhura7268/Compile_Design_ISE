"""
lexer.py - PLY Lexical Analyzer for ToyLang.
"""

import ply.lex as lex
from .tokens import KEYWORDS, tokens
from .fuzzy_match import suggest_keyword
from .symbol_table import SymbolTable


def find_column(input_str, lexpos):
    """Calculate 1-based column position of a token."""
    last_newline = input_str.rfind("\n", 0, lexpos)
    if last_newline < 0:
        return lexpos + 1
    return lexpos - last_newline


# Operators
t_EQ = r"=="
t_NE = r"!="
t_LE = r"<="
t_GE = r">="
t_LT = r"<"
t_GT = r">"
t_ASSIGN = r"="

t_PLUS = r"\+"
t_MINUS = r"-"
t_TIMES = r"\*"
t_DIVIDE = r"/"
t_MOD = r"%"

# Delimiters
t_LPAREN = r"\("
t_RPAREN = r"\)"
t_LBRACE = r"\{"
t_RBRACE = r"\}"
t_SEMI = r";"
t_COMMA = r","

# Ignored characters
t_ignore = " \t\r"


def t_COMMENT_MULTI(t):
    r"/\*[\s\S]*?\*/"
    t.lexer.lineno += t.value.count("\n")


def t_COMMENT_SINGLE(t):
    r"//.*"


def t_FLOAT_NUM(t):
    r"\d+\.\d+"
    return t


def t_INT_NUM(t):
    r"\d+"
    return t


def t_STRING_LITERAL(t):
    r'"([^"\\]|\\.)*"'
    t.lexer.lineno += t.value.count("\n")
    return t


def t_ID(t):
    r"[A-Za-z_][A-Za-z0-9_]*"
    if t.value in KEYWORDS:
        t.type = KEYWORDS[t.value]
    else:
        suggestion = suggest_keyword(t.value)
        if suggestion:
            t.warning = f"Did you mean '{suggestion}'?"
            t.suggested = suggestion
    return t


def t_newline(t):
    r"\n+"
    t.lexer.lineno += len(t.value)


def t_error(t):
    col = find_column(t.lexer.lexdata, t.lexpos)
    err_obj = {
        "type": "LEXICAL_ERROR",
        "value": t.value[0],
        "line": t.lexer.lineno,
        "col": col,
        "message": f"Illegal character '{t.value[0]}'",
    }
    t.lexer.error_tokens.append(err_obj)
    t.lexer.skip(1)


# Instantiate PLY lexer instance
_lexer_instance = lex.lex(optimize=0)


def tokenize(source_code):
    """Tokenize source code into tokens list and symbol table."""
    lexer = _lexer_instance.clone()
    lexer.lineno = 1
    lexer.error_tokens = []
    lexer.input(source_code)

    formatted_tokens = []

    while True:
        tok = lexer.token()

        if lexer.error_tokens:
            formatted_tokens.extend(lexer.error_tokens)
            lexer.error_tokens = []

        if not tok:
            break

        col = find_column(source_code, tok.lexpos)
        token_obj = {
            "type": tok.type,
            "value": tok.value,
            "line": tok.lineno,
            "col": col,
        }

        if hasattr(tok, "warning"):
            token_obj["warning"] = tok.warning
            token_obj["suggested"] = tok.suggested

        formatted_tokens.append(token_obj)

    # Simple declaration extraction for SymbolTable
    symbol_table = SymbolTable()
    i = 0
    n = len(formatted_tokens)
    while i < n:
        tok = formatted_tokens[i]
        t_type = tok["type"]

        if t_type == "LBRACE":
            symbol_table.enter_scope()
        elif t_type == "RBRACE":
            symbol_table.exit_scope()
        elif t_type in ("INT", "FLOAT", "BOOL"):
            datatype = tok["value"]
            i += 1
            in_assignment = False
            while i < n:
                curr = formatted_tokens[i]
                curr_type = curr["type"]
                if curr_type == "SEMI":
                    break
                elif curr_type in ("LBRACE", "RBRACE"):
                    i -= 1
                    break
                elif curr_type == "ASSIGN":
                    in_assignment = True
                elif curr_type == "COMMA":
                    in_assignment = False
                elif curr_type == "ID" and not in_assignment:
                    symbol_table.add(curr["value"], datatype, curr["line"])
                i += 1
        i += 1

    return {
        "tokens": formatted_tokens,
        "symbol_table": symbol_table.get_all(),
    }
