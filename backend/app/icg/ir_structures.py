"""ir_structures.py - Core intermediate representation data structures for ToyLang.

Defines:
- TempAllocator: Allocator for temporary registers (t0, t1, t2, ...)
- LabelGenerator: Generator for branch target labels (L0, L1, L2, ...)
- Quadruple: 4-tuple representation (op, arg1, arg2, result)
- Triple: 3-field indexed representation (index, op, arg1, arg2)
- ThreeAddressInstruction: High-level 3AC instruction model
- BasicBlock: Node in the Control Flow Graph (CFG)
- CFGEdge: Directed edge in the CFG with classification
- ControlFlowGraph: Graph structure containing Basic Blocks and directed edges
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple, Union


class InstructionType(str, Enum):
    """Categorization of Three-Address Code instructions."""
    ASSIGN = "ASSIGN"               # result = arg1
    BINARY_OP = "BINARY_OP"         # result = arg1 op arg2
    UNARY_OP = "UNARY_OP"           # result = op arg1
    LABEL = "LABEL"                 # L0:
    GOTO = "GOTO"                   # goto L1
    IF_FALSE_GOTO = "IF_FALSE_GOTO" # ifFalse arg1 goto L1
    IF_TRUE_GOTO = "IF_TRUE_GOTO"   # ifTrue arg1 goto L1
    IF_CMP_GOTO = "IF_CMP_GOTO"     # if arg1 relop arg2 goto L1
    PRINT = "PRINT"                 # print arg1
    RETURN = "RETURN"               # return arg1 / return


class TempAllocator:
    """Allocates temporary variables (t0, t1, t2, ...) sequentially."""

    def __init__(self, prefix: str = "t"):
        self.prefix = prefix
        self._counter: int = 0
        self._history: List[str] = []

    def new_temp(self) -> str:
        """Allocate and return the next temporary variable name."""
        name = f"{self.prefix}{self._counter}"
        self._counter += 1
        self._history.append(name)
        return name

    def peek_current(self) -> Optional[str]:
        """Return the most recently allocated temp without advancing."""
        return self._history[-1] if self._history else None

    def reset(self) -> None:
        """Reset the allocator counter and history."""
        self._counter = 0
        self._history.clear()

    @property
    def allocated(self) -> List[str]:
        """List of all allocated temporaries in order."""
        return list(self._history)

    def __len__(self) -> int:
        return self._counter


class LabelGenerator:
    """Generates unique labels (L0, L1, L2, ...) for control flow."""

    def __init__(self, prefix: str = "L"):
        self.prefix = prefix
        self._counter: int = 0
        self._history: List[str] = []

    def new_label(self) -> str:
        """Generate and return the next label."""
        name = f"{self.prefix}{self._counter}"
        self._counter += 1
        self._history.append(name)
        return name

    def reset(self) -> None:
        """Reset the label generator counter and history."""
        self._counter = 0
        self._history.clear()

    @property
    def generated(self) -> List[str]:
        """List of all generated labels in order."""
        return list(self._history)

    def __len__(self) -> int:
        return self._counter


@dataclass
class Quadruple:
    """Quadruple representation: 4-field tuple (op, arg1, arg2, result).
    
    Examples:
    - ('+', 'a', 'b', 't0')     -> t0 = a + b
    - ('=', 't0', None, 'x')    -> x = t0
    - ('uminus', 'x', None, 't1')-> t1 = - x
    - ('goto', None, None, 'L1')-> goto L1
    - ('ifFalse', 't0', None, 'L2') -> ifFalse t0 goto L2
    - ('label', None, None, 'L1') -> L1:
    """
    op: str
    arg1: Optional[str] = None
    arg2: Optional[str] = None
    result: Optional[str] = None
    index: Optional[int] = None

    def to_tuple(self) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
        return (self.op, self.arg1, self.arg2, self.result)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "op": self.op,
            "arg1": self.arg1,
            "arg2": self.arg2,
            "result": self.result,
        }

    def __str__(self) -> str:
        a1 = self.arg1 if self.arg1 is not None else "-"
        a2 = self.arg2 if self.arg2 is not None else "-"
        res = self.result if self.result is not None else "-"
        idx = f"{self.index:3d}: " if self.index is not None else ""
        return f"{idx}({self.op}, {a1}, {a2}, {res})"


@dataclass
class Triple:
    """Triple representation: 3-field indexed record (index, op, arg1, arg2).
    
    Instead of naming results explicitly with temporaries, the result of operation
    at index i is implicitly referenced by subsequent instructions as '(i)'.
    
    Examples:
    - (0) ('*', 'b', 'c')
    - (1) ('+', 'a', '(0)')
    - (2) ('=', 'x', '(1)')
    """
    index: int
    op: str
    arg1: str
    arg2: Optional[str] = None

    def to_tuple(self) -> Tuple[int, str, str, Optional[str]]:
        return (self.index, self.op, self.arg1, self.arg2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "op": self.op,
            "arg1": self.arg1,
            "arg2": self.arg2,
        }

    def __str__(self) -> str:
        a2 = self.arg2 if self.arg2 is not None else "-"
        return f"({self.index}) ({self.op}, {self.arg1}, {a2})"


@dataclass
class ThreeAddressInstruction:
    """Three-Address Code (3AC) linear instruction with rich metadata."""
    inst_type: InstructionType
    result: Optional[str] = None
    op: Optional[str] = None
    arg1: Optional[str] = None
    arg2: Optional[str] = None
    index: int = 0
    is_leader: bool = False
    source_line: Optional[int] = None
    comment: Optional[str] = None

    def format_code(self) -> str:
        """Render standard readable Three-Address Code string."""
        if self.inst_type == InstructionType.LABEL:
            return f"{self.result}:"
        elif self.inst_type == InstructionType.ASSIGN:
            return f"{self.result} = {self.arg1}"
        elif self.inst_type == InstructionType.BINARY_OP:
            return f"{self.result} = {self.arg1} {self.op} {self.arg2}"
        elif self.inst_type == InstructionType.UNARY_OP:
            return f"{self.result} = {self.op} {self.arg1}"
        elif self.inst_type == InstructionType.GOTO:
            return f"goto {self.result}"
        elif self.inst_type == InstructionType.IF_FALSE_GOTO:
            return f"ifFalse {self.arg1} goto {self.result}"
        elif self.inst_type == InstructionType.IF_TRUE_GOTO:
            return f"ifTrue {self.arg1} goto {self.result}"
        elif self.inst_type == InstructionType.IF_CMP_GOTO:
            return f"if {self.arg1} {self.op} {self.arg2} goto {self.result}"
        elif self.inst_type == InstructionType.PRINT:
            return f"print {self.arg1}"
        elif self.inst_type == InstructionType.RETURN:
            return f"return {self.arg1}" if self.arg1 else "return"
        else:
            return f"{self.result} = {self.arg1} {self.op} {self.arg2}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "type": self.inst_type.value,
            "code": self.format_code(),
            "result": self.result,
            "op": self.op,
            "arg1": self.arg1,
            "arg2": self.arg2,
            "is_leader": self.is_leader,
            "source_line": self.source_line,
            "comment": self.comment,
        }

    def __str__(self) -> str:
        leader_mark = "[LEADER] " if self.is_leader else "         "
        code = self.format_code()
        cmt = f"  # {self.comment}" if self.comment else ""
        return f"{self.index:3d}: {leader_mark}{code}{cmt}"


@dataclass
class CFGEdge:
    """Directed edge between basic blocks in a Control Flow Graph."""
    from_block: str
    to_block: str
    edge_type: str  # 'fall-through', 'branch-true', 'branch-false', 'unconditional-jump'
    condition: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_block,
            "to": self.to_block,
            "type": self.edge_type,
            "condition": self.condition,
        }


@dataclass
class BasicBlock:
    """A Basic Block in the Control Flow Graph.
    
    A maximal sequence of consecutive Three-Address Code instructions with:
    - Single entry point (instructions can only be entered at the beginning)
    - Single exit point (control leaves only at the end)
    """
    id: str                                        # e.g. "B0", "B1"
    instructions: List[ThreeAddressInstruction] = field(default_factory=list)
    predecessors: List[str] = field(default_factory=list)
    successors: List[str] = field(default_factory=list)
    is_entry: bool = False
    is_exit: bool = False

    @property
    def leader(self) -> Optional[ThreeAddressInstruction]:
        return self.instructions[0] if self.instructions else None

    @property
    def terminator(self) -> Optional[ThreeAddressInstruction]:
        return self.instructions[-1] if self.instructions else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "is_entry": self.is_entry,
            "is_exit": self.is_exit,
            "leader_index": self.leader.index if self.leader else None,
            "predecessors": self.predecessors,
            "successors": self.successors,
            "instructions": [inst.to_dict() for inst in self.instructions],
            "code_lines": [inst.format_code() for inst in self.instructions],
        }


@dataclass
class ControlFlowGraph:
    """Control Flow Graph containing partitioned basic blocks and directed edges."""
    blocks: Dict[str, BasicBlock] = field(default_factory=dict)
    edges: List[CFGEdge] = field(default_factory=list)
    entry_block_id: Optional[str] = None
    exit_block_ids: List[str] = field(default_factory=list)

    def get_block(self, block_id: str) -> Optional[BasicBlock]:
        return self.blocks.get(block_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_block": self.entry_block_id,
            "exit_blocks": self.exit_block_ids,
            "blocks": {bid: b.to_dict() for bid, b in self.blocks.items()},
            "edges": [e.to_dict() for e in self.edges],
        }
