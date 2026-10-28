"""Compilation phase orchestration for the Streamlit application.

Orchestrates:
  Phase 1 - Lexical Analysis
  Phase 2 - Syntax Analysis (Parsing)
  Phase 3 - Semantic Analysis
  Phase 4 - Intermediate Code Generation (ICG)
  Phase 5 - Assembly Code Generation (x86-64 NASM)
"""

from ..lexer.lexer import tokenize
from ..parser.grammar import parse_with_ast
from .semantic_analyzer import analyze
from ..icg.icg import generate_icg
from ..codegen.assembly_generator import generate_assembly


def compile_source(source_code):
    """Run all five compilation phases and return a result dict.

    Returns:
        dict with keys:
            lex      - lexical analysis result
            parse    - syntax analysis result
            semantic - semantic analysis result (None if parse failed)
            icg      - ICG result (None if parse/semantic failed)
            assembly - assembly generation result (None if ICG did not succeed)
    """
    lex_result = tokenize(source_code)
    parse_result, ast = parse_with_ast(source_code)
    semantic_result = analyze(ast) if parse_result["success"] else None

    # Phase 4: Intermediate Code Generation
    icg_result = None
    if parse_result["success"] and (semantic_result is None or semantic_result.get("success", False)):
        try:
            icg_result = generate_icg(ast)
        except Exception as e:
            icg_result = {"success": False, "error": str(e)}

    # Phase 5: Assembly Code Generation (only when ICG succeeded)
    assembly_result = None
    if icg_result and icg_result.get("success", False):
        try:
            assembly_result = generate_assembly(icg_result)
        except Exception as e:
            assembly_result = {"success": False, "assembly": "", "target": "x86-64 (NASM)", "errors": [], "error": str(e)}

    return {
        "lex": lex_result,
        "parse": parse_result,
        "semantic": semantic_result,
        "icg": icg_result,
        "assembly": assembly_result,
    }
