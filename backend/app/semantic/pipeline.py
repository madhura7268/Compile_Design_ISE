"""Compilation phase orchestration for the Streamlit application.

Orchestrates Phase 1 (Lexical), Phase 2 (Syntax), Phase 3 (Semantic),
and Phase 4 (Intermediate Code Generation).
"""

from ..lexer.lexer import tokenize
from ..parser.grammar import parse_with_ast
from .semantic_analyzer import analyze
from ..icg.icg import generate_icg


def compile_source(source_code):
    """Run lexical, syntax, semantic, and intermediate code generation phases."""
    lex_result = tokenize(source_code)
    parse_result, ast = parse_with_ast(source_code)
    semantic_result = analyze(ast) if parse_result["success"] else None
    
    # Generate Intermediate Code only if syntax and semantic analysis succeeded
    icg_result = None
    if parse_result["success"] and (semantic_result is None or semantic_result.get("success", False)):
        try:
            icg_result = generate_icg(ast)
        except Exception as e:
            icg_result = {"success": False, "error": str(e)}

    return {
        "lex": lex_result,
        "parse": parse_result,
        "semantic": semantic_result,
        "icg": icg_result,
    }
