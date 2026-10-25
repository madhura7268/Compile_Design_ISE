"""Unit tests for IR structures, allocators, and models."""

import pytest
from app.icg.ir_structures import (
    TempAllocator,
    LabelGenerator,
    Quadruple,
    Triple,
    ThreeAddressInstruction,
    InstructionType,
    BasicBlock,
    CFGEdge,
    ControlFlowGraph,
)


def test_temp_allocator():
    allocator = TempAllocator()
    assert allocator.new_temp() == "t0"
    assert allocator.new_temp() == "t1"
    assert allocator.new_temp() == "t2"
    assert len(allocator) == 3
    assert allocator.allocated == ["t0", "t1", "t2"]
    assert allocator.peek_current() == "t2"

    allocator.reset()
    assert len(allocator) == 0
    assert allocator.new_temp() == "t0"


def test_label_generator():
    generator = LabelGenerator()
    assert generator.new_label() == "L0"
    assert generator.new_label() == "L1"
    assert len(generator) == 2
    assert generator.generated == ["L0", "L1"]

    generator.reset()
    assert len(generator) == 0
    assert generator.new_label() == "L0"


def test_quadruple_representation():
    quad = Quadruple(op="+", arg1="a", arg2="b", result="t0", index=0)
    assert quad.to_tuple() == ("+", "a", "b", "t0")
    assert quad.to_dict() == {
        "index": 0,
        "op": "+",
        "arg1": "a",
        "arg2": "b",
        "result": "t0",
    }
    assert "(+, a, b, t0)" in str(quad)


def test_triple_representation():
    trip = Triple(index=1, op="*", arg1="b", arg2="c")
    assert trip.to_tuple() == (1, "*", "b", "c")
    assert trip.to_dict() == {
        "index": 1,
        "op": "*",
        "arg1": "b",
        "arg2": "c",
    }
    assert "(1) (*, b, c)" == str(trip)


def test_three_address_instruction_formatting():
    inst1 = ThreeAddressInstruction(
        inst_type=InstructionType.BINARY_OP,
        result="t0",
        op="*",
        arg1="b",
        arg2="c",
        index=0,
    )
    assert inst1.format_code() == "t0 = b * c"

    inst2 = ThreeAddressInstruction(
        inst_type=InstructionType.ASSIGN,
        result="x",
        arg1="t0",
        index=1,
    )
    assert inst2.format_code() == "x = t0"

    inst3 = ThreeAddressInstruction(
        inst_type=InstructionType.LABEL,
        result="L1",
        index=2,
    )
    assert inst3.format_code() == "L1:"

    inst4 = ThreeAddressInstruction(
        inst_type=InstructionType.IF_FALSE_GOTO,
        arg1="t1",
        result="L2",
        index=3,
    )
    assert inst4.format_code() == "ifFalse t1 goto L2"


def test_basic_block_and_cfg():
    bb = BasicBlock(id="B0")
    inst = ThreeAddressInstruction(
        inst_type=InstructionType.ASSIGN,
        result="x",
        arg1="10",
        index=0,
        is_leader=True,
    )
    bb.instructions.append(inst)
    assert bb.leader == inst
    assert bb.terminator == inst

    edge = CFGEdge(from_block="B0", to_block="B1", edge_type="fall-through")
    cfg = ControlFlowGraph()
    cfg.blocks["B0"] = bb
    cfg.edges.append(edge)
    cfg.entry_block_id = "B0"

    cfg_dict = cfg.to_dict()
    assert cfg_dict["entry_block"] == "B0"
    assert len(cfg_dict["edges"]) == 1
    assert cfg_dict["edges"][0]["type"] == "fall-through"
