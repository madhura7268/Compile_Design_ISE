"""
grammar.py - ToyLang CFG and LALR(1) Parser using PLY Yacc.

Member 2:
    - CFG grammar
    - Operator precedence
    - Parse tree generation
    - Syntax error interception
    - Parser error context
"""

import ply.yacc as yacc

from .tree_builder import (
    Node,
    identifier_node,
    literal_node,
    operator_node,
    unary_operator_node,
)

from ..lexer.tokens import tokens
from ..lexer.lexer import _lexer_instance, find_column


# ============================================================
# OPERATOR PRECEDENCE
# ============================================================

precedence = (
    ("left", "EQ", "NE"),
    ("left", "LT", "LE", "GT", "GE"),
    ("left", "PLUS", "MINUS"),
    ("left", "TIMES", "DIVIDE", "MOD"),
    ("right", "UMINUS"),
)


# ============================================================
# ERROR STORAGE
# ============================================================

_last_parser_error = None


# ============================================================
# PROGRAM
# ============================================================

def p_program(p):
    """
    program : statement_list
    """
    p[0] = Node(
        "Program",
        [p[1]]
    )


# ============================================================
# STATEMENT LIST
# ============================================================

def p_statement_list_multiple(p):
    """
    statement_list : statement_list statement
    """
    p[1].add_child(p[2])
    p[0] = p[1]


def p_statement_list_single(p):
    """
    statement_list : statement
    """
    p[0] = Node(
        "StatementList",
        [p[1]]
    )


def p_statement_list_empty(p):
    """
    statement_list : empty
    """
    p[0] = Node("StatementList")


# ============================================================
# STATEMENTS
# ============================================================

def p_statement(p):
    """
    statement : declaration_statement
              | assignment_statement
              | expression_statement
              | if_statement
              | while_statement
              | return_statement
              | print_statement
              | block
    """
    p[0] = p[1]


# ============================================================
# BLOCK
# ============================================================

def p_block(p):
    """
    block : LBRACE statement_list RBRACE
    """
    p[0] = Node(
        "Block",
        [p[2]]
    )


# ============================================================
# VARIABLE DECLARATIONS
# ============================================================

def p_declaration_statement(p):
    """
    declaration_statement : type ID SEMI
                          | type ID ASSIGN expression SEMI
    """

    datatype = p[1]
    identifier = p[2]

    if len(p) == 4:
        p[0] = Node(
            f"VarDeclaration ({datatype})",
            [
                identifier_node(identifier)
            ]
        )

    else:
        p[0] = Node(
            f"VarDeclaration ({datatype})",
            [
                identifier_node(identifier),
                p[4]
            ]
        )


def p_type(p):
    """
    type : INT
         | FLOAT
         | BOOL
    """
    p[0] = p[1]


# ============================================================
# ASSIGNMENT
# ============================================================

def p_assignment_statement(p):
    """
    assignment_statement : ID ASSIGN expression SEMI
    """
    p[0] = Node(
        "Assignment",
        [
            identifier_node(p[1]),
            p[3]
        ]
    )


# ============================================================
# EXPRESSION STATEMENT
# ============================================================

def p_expression_statement(p):
    """
    expression_statement : expression SEMI
    """
    p[0] = Node(
        "ExpressionStatement",
        [p[1]]
    )


# ============================================================
# IF / ELSE
# ============================================================

def p_if_statement(p):
    """
    if_statement : IF LPAREN expression RPAREN block
                | IF LPAREN expression RPAREN block ELSE block
    """

    if len(p) == 6:
        p[0] = Node(
            "IfStatement",
            [
                Node("Condition", [p[3]]),
                p[5]
            ]
        )

    else:
        p[0] = Node(
            "IfStatement",
            [
                Node("Condition", [p[3]]),
                Node("Then", [p[5]]),
                Node("Else", [p[7]])
            ]
        )


# ============================================================
# WHILE
# ============================================================

def p_while_statement(p):
    """
    while_statement : WHILE LPAREN expression RPAREN block
    """
    p[0] = Node(
        "WhileStatement",
        [
            Node("Condition", [p[3]]),
            p[5]
        ]
    )


# ============================================================
# RETURN
# ============================================================

def p_return_statement(p):
    """
    return_statement : RETURN SEMI
                     | RETURN expression SEMI
    """

    if len(p) == 3:
        p[0] = Node("ReturnStatement")

    else:
        p[0] = Node(
            "ReturnStatement",
            [p[2]]
        )


# ============================================================
# PRINT
# ============================================================

def p_print_statement(p):
    """
    print_statement : PRINT LPAREN expression RPAREN SEMI
    """
    p[0] = Node(
        "PrintStatement",
        [p[3]]
    )


# ============================================================
# EXPRESSIONS
# ============================================================

def p_expression_binary(p):
    """
    expression : expression PLUS expression
               | expression MINUS expression
               | expression TIMES expression
               | expression DIVIDE expression
               | expression MOD expression
               | expression EQ expression
               | expression NE expression
               | expression LT expression
               | expression LE expression
               | expression GT expression
               | expression GE expression
    """

    operators = {
        "PLUS": "+",
        "MINUS": "-",
        "TIMES": "*",
        "DIVIDE": "/",
        "MOD": "%",
        "EQ": "==",
        "NE": "!=",
        "LT": "<",
        "LE": "<=",
        "GT": ">",
        "GE": ">=",
    }

    operator = operators[p.slice[2].type]

    p[0] = operator_node(
        operator,
        p[1],
        p[3]
    )


def p_expression_unary_minus(p):
    """
    expression : MINUS expression %prec UMINUS
    """
    p[0] = unary_operator_node(
        "-",
        p[2]
    )


def p_expression_group(p):
    """
    expression : LPAREN expression RPAREN
    """
    p[0] = p[2]


# ============================================================
# IDENTIFIERS
# ============================================================

def p_expression_identifier(p):
    """
    expression : ID
    """
    p[0] = identifier_node(p[1])


# ============================================================
# INTEGER
# ============================================================

def p_expression_int(p):
    """
    expression : INT_NUM
    """
    p[0] = literal_node(p[1])


# ============================================================
# FLOAT
# ============================================================

def p_expression_float(p):
    """
    expression : FLOAT_NUM
    """
    p[0] = literal_node(p[1])


# ============================================================
# STRING
# ============================================================

def p_expression_string(p):
    """
    expression : STRING_LITERAL
    """
    p[0] = literal_node(p[1])


# ============================================================
# EMPTY
# ============================================================

def p_empty(p):
    """
    empty :
    """
    p[0] = None


# ============================================================
# SYNTAX ERROR HANDLER
# ============================================================

def p_error(p):
    """
    Capture parser syntax errors without crashing.
    """

    global _last_parser_error

    if p is None:
        _last_parser_error = {
            "error_type": "SyntaxError",
            "line": None,
            "column": None,
            "unexpected_token": "EOF",
            "expected": [],
            "message": "Unexpected end of input.",
            "parser_stack": [],
        }
        return

    parser = getattr(p, "parser", None)

    line = getattr(p, "lineno", None)

    try:
        column = find_column(
            p.lexer.lexdata,
            p.lexpos
        )
    except Exception:
        column = None

    # --------------------------------------------------------
    # Capture a small parser stack context.
    # --------------------------------------------------------

    parser_stack = []

    if parser is not None:
        try:
            for symbol in parser.symstack[-8:]:
                parser_stack.append(
                    getattr(symbol, "type", str(symbol))
                )
        except Exception:
            parser_stack = []

    # --------------------------------------------------------
    # Expected tokens.
    #
    # PLY does not directly expose a clean public list of
    # expected tokens, so we provide the parser context
    # rather than guessing.
    # --------------------------------------------------------

    _last_parser_error = {
        "error_type": "SyntaxError",
        "line": line,
        "column": column,
        "unexpected_token": p.value,
        "token_type": p.type,
        "expected": [],
        "message": (
            f"Unexpected token '{p.value}' "
            f"of type {p.type}."
        ),
        "parser_stack": parser_stack,
    }

    # Recover by discarding the offending token.
    if parser is not None:
        parser.errok()


# ============================================================
# BUILD PARSER
# ============================================================

_parser = yacc.yacc(
    start="program",
    debug=False,
    write_tables=False,
)


# ============================================================
# PARSER LEXER ADAPTER
# ============================================================

def _create_lexer(source_code):
    """
    Create a fresh PLY lexer for parser use.

    Member 1's tokenize() function formats tokens into
    dictionaries for the API.

    PLY Yacc, however, needs the original LexToken objects.

    Therefore we clone Member 1's existing lexer here.
    """

    lexer = _lexer_instance.clone()

    lexer.lineno = 1
    lexer.error_tokens = []

    lexer.input(source_code)

    return lexer


# ============================================================
# PUBLIC PARSE FUNCTION
# ============================================================

def parse(source_code):
    """
    Parse ToyLang source code.

    Returns:
        {
            "success": True/False,
            "parse_tree": {...},
            "error": {...}
        }
    """

    global _last_parser_error

    _last_parser_error = None

    if not isinstance(source_code, str):
        return {
            "success": False,
            "parse_tree": None,
            "error": {
                "error_type": "InputError",
                "message": "Source code must be a string."
            }
        }

    lexer = _create_lexer(source_code)

    try:
        tree = _parser.parse(
            source_code,
            lexer=lexer,
            tracking=True
        )

    except Exception as exc:
        return {
            "success": False,
            "parse_tree": None,
            "error": {
                "error_type": "ParserError",
                "message": str(exc)
            }
        }

    # --------------------------------------------------------
    # Check lexical errors generated by Member 1's lexer.
    # --------------------------------------------------------

    lexical_errors = getattr(
        lexer,
        "error_tokens",
        []
    )

    if lexical_errors:
        first_error = lexical_errors[0]

        return {
            "success": False,
            "parse_tree": None,
            "error": {
                "error_type": "LexicalError",
                "line": first_error.get("line"),
                "column": first_error.get("col"),
                "unexpected_token": first_error.get("value"),
                "message": first_error.get("message"),
            }
        }

    # --------------------------------------------------------
    # Parser error.
    # --------------------------------------------------------

    if _last_parser_error is not None:
        return {
            "success": False,
            "parse_tree": None,
            "error": _last_parser_error
        }

    # --------------------------------------------------------
    # Successful parse.
    # --------------------------------------------------------

    if tree is None:
        return {
            "success": False,
            "parse_tree": None,
            "error": {
                "error_type": "SyntaxError",
                "message": "Unable to generate parse tree."
            }
        }

    return {
        "success": True,
        "parse_tree": tree.to_d3_json(),
        "error": None
    }