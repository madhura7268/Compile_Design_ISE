"""Test end-to-end integration of Phase 4 ICG in compilation pipeline."""

import pytest
from app.semantic.pipeline import compile_source


def test_pipeline_integration_valid_code():
    code = """
    int a = 10;
    int b = 20;
    int c = a + b * 2;
    """
    res = compile_source(code)

    assert len(res["lex"]["tokens"]) > 0
    assert res["parse"]["success"] is True
    assert res["semantic"]["success"] is True

    # Phase 4 ICG
    assert res["icg"] is not None
    assert res["icg"]["success"] is True
    assert len(res["icg"]["instructions"]) == 5
    assert len(res["icg"]["quadruples"]) == 5
    assert len(res["icg"]["triples"]) == 5
    assert "B0" in res["icg"]["cfg"]["blocks"]


def test_pipeline_integration_syntax_error():
    # Syntax error: missing semicolon
    code = "int a = 10"
    res = compile_source(code)

    assert res["parse"]["success"] is False
    # ICG should not run if parsing failed
    assert res["icg"] is None


def test_pipeline_integration_semantic_error():
    # Semantic error: undeclared variable
    code = "x = 10;"
    res = compile_source(code)

    assert res["parse"]["success"] is True
    assert res["semantic"]["success"] is False
    # ICG should not run if semantic analysis failed
    assert res["icg"] is None


def test_pipeline_control_flow():
    code = """
    int i = 0;
    while (i < 3) {
        i = i + 1;
    }
    """
    res = compile_source(code)

    assert res["parse"]["success"] is True
    assert res["semantic"]["success"] is True
    assert res["icg"]["success"] is True
    assert len(res["icg"]["cfg"]["blocks"]) >= 3


def test_graphviz_cfg_generation():
    from cfg_viz import generate_graphviz_cfg
    code = """
    int x = 5;
    if (x > 0) {
        x = x + 1;
    } else {
        x = x - 1;
    }
    """
    res = compile_source(code)
    assert res["icg"]["success"] is True
    dot = generate_graphviz_cfg(res["icg"]["cfg"])
    assert dot is not None
    source = dot.source
    # Verify blocks and edges are present in Graphviz source
    assert "B0" in source
    assert "ENTRY" in source
    assert "EXIT" in source
    assert "branch-true" in source or "true" in source
    assert "branch-false" in source or "false" in source

