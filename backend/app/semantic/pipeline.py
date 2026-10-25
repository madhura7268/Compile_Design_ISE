"""Compilation phase orchestration for the Streamlit application."""

from ..lexer.lexer import tokenize
from ..parser.grammar import parse_with_ast
from .semantic_analyzer import analyze


def compile_source(source_code):
    """Run semantics only after lexing and parsing have succeeded."""
    lex_result = tokenize(source_code)
    parse_result, ast = parse_with_ast(source_code)
    semantic_result = analyze(ast) if parse_result["success"] else None
    return {
        "lex": lex_result,
        "parse": parse_result,
        "semantic": semantic_result,
    }
