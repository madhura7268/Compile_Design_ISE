"""Comprehensive unit tests for Intermediate Code Generator (ICG) and CFG."""

import pytest
from app.parser.grammar import parse_with_ast
from app.icg.icg import IntermediateCodeGenerator, generate_icg
from app.icg.ir_structures import InstructionType


def compile_and_get_icg(source_code: str):
    parse_result, ast = parse_with_ast(source_code)
    assert parse_result["success"], f"Parse failed: {parse_result.get('error')}"
    return generate_icg(ast)


def test_arithmetic_expressions():
    code = "int c = a + b * 2;"
    result = compile_and_get_icg(code)

    assert result["success"] is True
    tac = result["three_address_code"]

    # Precedence: b * 2 should be computed first, then a + t0
    assert any("t0 = b * 2" in line for line in tac)
    assert any("t1 = a + t0" in line for line in tac)
    assert any("c = t1" in line for line in tac)

    # Check quadruples
    quads = result["quadruples"]
    assert len(quads) == 3
    assert quads[0]["op"] == "*"
    assert quads[0]["arg1"] == "b"
    assert quads[0]["arg2"] == "2"
    assert quads[0]["result"] == "t0"

    assert quads[1]["op"] == "+"
    assert quads[1]["arg1"] == "a"
    assert quads[1]["arg2"] == "t0"
    assert quads[1]["result"] == "t1"

    assert quads[2]["op"] == "="
    assert quads[2]["arg1"] == "t1"
    assert quads[2]["result"] == "c"

    # Check triples back-references
    triples = result["triples"]
    assert len(triples) == 3
    assert triples[0]["op"] == "*"
    assert triples[0]["arg1"] == "b"
    assert triples[0]["arg2"] == "2"

    assert triples[1]["op"] == "+"
    assert triples[1]["arg1"] == "a"
    assert triples[1]["arg2"] == "(0)"  # Refers to triple 0

    assert triples[2]["op"] == "="
    assert triples[2]["arg1"] == "c"
    assert triples[2]["arg2"] == "(1)"  # Refers to triple 1


def test_unary_minus():
    code = "int x = - a;"
    result = compile_and_get_icg(code)

    assert result["success"] is True
    tac = result["three_address_code"]
    assert any("t0 = - a" in line for line in tac)
    assert any("x = t0" in line for line in tac)


def test_if_else_control_flow():
    code = """
    if (a < b) {
        x = 1;
    } else {
        x = 2;
    }
    """
    result = compile_and_get_icg(code)
    assert result["success"] is True
    tac = result["three_address_code"]

    # Must contain conditional branch, goto, labels
    assert any("t0 = a < b" in line for line in tac)
    assert any("ifFalse t0 goto L0" in line for line in tac)
    assert any("goto L1" in line for line in tac)
    assert any("L0:" in line for line in tac)
    assert any("L1:" in line for line in tac)

    # Check CFG basic blocks
    cfg = result["cfg"]
    blocks = cfg["blocks"]
    assert len(blocks) >= 3  # Entry block, Then/Else blocks, Continuation block
    assert cfg["entry_block"] == "B0"

    # Verify edge types present
    edge_types = [e["type"] for e in cfg["edges"]]
    assert "branch-false" in edge_types
    assert "branch-true" in edge_types or "fall-through" in edge_types
    assert "unconditional-jump" in edge_types


def test_while_loop_control_flow():
    code = """
    int count = 0;
    while (count < 5) {
        count = count + 1;
    }
    """
    result = compile_and_get_icg(code)
    assert result["success"] is True
    tac = result["three_address_code"]

    # Must contain loop header label, condition check, loop back edge, loop exit label
    assert any("L0:" in line for line in tac)
    assert any("t0 = count < 5" in line for line in tac)
    assert any("ifFalse t0 goto L1" in line for line in tac)
    assert any("goto L0" in line for line in tac)
    assert any("L1:" in line for line in tac)

    # Check CFG loop back edge
    cfg = result["cfg"]
    edges = cfg["edges"]
    # There should be an unconditional-jump back to header
    assert any(e["type"] == "unconditional-jump" for e in edges)
    assert any(e["type"] == "branch-false" for e in edges)


def test_nested_control_flow():
    code = """
    int count = 0;
    while (count < 5) {
        if (count == 2) {
            count = count + 2;
        } else {
            count = count + 1;
        }
    }
    """
    result = compile_and_get_icg(code)
    assert result["success"] is True
    assert len(result["instructions"]) > 10
    assert len(result["cfg"]["blocks"]) >= 5
    assert len(result["steps"]) > 10


def test_json_ast_input():
    code = "int a = 10; int b = a * 2;"
    parse_result, ast = parse_with_ast(code)
    d3_json = ast.to_d3_json()

    # Pass dictionary directly
    generator = IntermediateCodeGenerator()
    res = generator.generate(d3_json)

    assert res["success"] is True
    assert len(res["three_address_code"]) == 3
    assert any("b = t0" in line for line in res["three_address_code"])


def test_stepper_trace_logging():
    code = "int x = 10 + 20;"
    result = compile_and_get_icg(code)
    steps = result["steps"]

    assert len(steps) > 0
    # Every step should have step, node_name, action, temps, labels
    for s in steps:
        assert "step" in s
        assert "node_name" in s
        assert "action" in s
        assert isinstance(s["temps"], list)
        assert isinstance(s["labels"], list)
