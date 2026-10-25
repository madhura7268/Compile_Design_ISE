"""Intermediate Code Generation (ICG) phase for ToyLang educational compiler.

Phase 4 of the compiler pipeline:
- Three-Address Code (3AC) generation
- Quadruples table generation
- Triples table generation
- Control Flow Graph (CFG) basic block partitioning and edge discovery
"""

from .ir_structures import (
    Quadruple,
    Triple,
    ThreeAddressInstruction,
    InstructionType,
    BasicBlock,
    CFGEdge,
    ControlFlowGraph,
    TempAllocator,
    LabelGenerator,
)

__all__ = [
    "Quadruple",
    "Triple",
    "ThreeAddressInstruction",
    "InstructionType",
    "BasicBlock",
    "CFGEdge",
    "ControlFlowGraph",
    "TempAllocator",
    "LabelGenerator",
]
