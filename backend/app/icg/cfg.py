"""cfg.py - Control Flow Graph (CFG) builder and Basic Block partitioner.

Implements the standard Dragon Book algorithm for basic block decomposition:
1. Identify leaders:
   - Instruction 0 is a leader.
   - Any instruction that is the target of a branch/goto (labels) is a leader.
   - Any instruction immediately following a conditional or unconditional jump is a leader.
2. Form basic blocks from each leader up to the next leader.
3. Compute directed control flow edges:
   - 'fall-through'
   - 'branch-true'
   - 'branch-false'
   - 'unconditional-jump'
"""

from typing import List, Dict, Optional, Set
from .ir_structures import (
    ThreeAddressInstruction,
    InstructionType,
    BasicBlock,
    CFGEdge,
    ControlFlowGraph,
)


def build_cfg_from_instructions(instructions: List[ThreeAddressInstruction]) -> ControlFlowGraph:
    """Decompose linear 3AC instructions into Basic Blocks and build a Control Flow Graph."""
    cfg = ControlFlowGraph()
    if not instructions:
        return cfg

    n = len(instructions)

    # -------------------------------------------------------------
    # Step 1: Identify Leaders
    # -------------------------------------------------------------
    # Build a lookup of label name -> instruction index
    label_to_index: Dict[str, int] = {}
    for idx, inst in enumerate(instructions):
        if inst.inst_type == InstructionType.LABEL and inst.result:
            label_to_index[inst.result] = idx

    leader_indices: Set[int] = set()

    # Rule 1: First instruction is a leader
    leader_indices.add(0)

    # Rule 2 & 3:
    for idx, inst in enumerate(instructions):
        if inst.inst_type in {
            InstructionType.GOTO,
            InstructionType.IF_FALSE_GOTO,
            InstructionType.IF_TRUE_GOTO,
            InstructionType.IF_CMP_GOTO,
        }:
            target_label = inst.result
            if target_label in label_to_index:
                # Rule 2: Target of branch is a leader
                leader_indices.add(label_to_index[target_label])

            # Rule 3: Instruction immediately following a jump is a leader
            if idx + 1 < n:
                leader_indices.add(idx + 1)

        elif inst.inst_type == InstructionType.RETURN:
            # Instruction following return is also a leader if it exists
            if idx + 1 < n:
                leader_indices.add(idx + 1)

        elif inst.inst_type == InstructionType.LABEL:
            # Labels represent branch targets
            leader_indices.add(idx)

    # Mark is_leader on each instruction
    sorted_leaders = sorted(leader_indices)
    for idx in sorted_leaders:
        instructions[idx].is_leader = True

    # -------------------------------------------------------------
    # Step 2: Partition into Basic Blocks
    # -------------------------------------------------------------
    # Map instruction index to block ID
    inst_to_block: Dict[int, str] = {}
    label_to_block: Dict[str, str] = {}

    for b_idx, start_idx in enumerate(sorted_leaders):
        block_id = f"B{b_idx}"
        end_idx = sorted_leaders[b_idx + 1] if b_idx + 1 < len(sorted_leaders) else n

        block_instructions = instructions[start_idx:end_idx]
        block = BasicBlock(
            id=block_id,
            instructions=block_instructions,
            is_entry=(b_idx == 0),
        )

        for i in range(start_idx, end_idx):
            inst_to_block[i] = block_id
            if instructions[i].inst_type == InstructionType.LABEL and instructions[i].result:
                label_to_block[instructions[i].result] = block_id

        cfg.blocks[block_id] = block

    cfg.entry_block_id = "B0" if cfg.blocks else None

    # -------------------------------------------------------------
    # Step 3: Compute Directed Edges
    # -------------------------------------------------------------
    num_blocks = len(sorted_leaders)

    for b_idx, start_idx in enumerate(sorted_leaders):
        block_id = f"B{b_idx}"
        block = cfg.blocks[block_id]
        if not block.instructions:
            continue

        terminator = block.terminator
        next_block_id = f"B{b_idx + 1}" if b_idx + 1 < num_blocks else None

        if terminator.inst_type == InstructionType.GOTO:
            target_label = terminator.result
            target_block_id = label_to_block.get(target_label)
            if target_block_id:
                _add_edge(cfg, block_id, target_block_id, "unconditional-jump")

        elif terminator.inst_type == InstructionType.IF_FALSE_GOTO:
            target_label = terminator.result
            target_block_id = label_to_block.get(target_label)
            # False branch: jumps to target
            if target_block_id:
                _add_edge(cfg, block_id, target_block_id, "branch-false", condition=f"!({terminator.arg1})")
            # True branch: falls through to next block
            if next_block_id:
                _add_edge(cfg, block_id, next_block_id, "branch-true", condition=str(terminator.arg1))

        elif terminator.inst_type == InstructionType.IF_TRUE_GOTO:
            target_label = terminator.result
            target_block_id = label_to_block.get(target_label)
            if target_block_id:
                _add_edge(cfg, block_id, target_block_id, "branch-true", condition=str(terminator.arg1))
            if next_block_id:
                _add_edge(cfg, block_id, next_block_id, "branch-false", condition=f"!({terminator.arg1})")

        elif terminator.inst_type == InstructionType.RETURN:
            # Function termination - no successors
            pass

        else:
            # Fall-through to next block
            if next_block_id:
                _add_edge(cfg, block_id, next_block_id, "fall-through")

    # Mark exit blocks (blocks with no successors)
    for block_id, block in cfg.blocks.items():
        if not block.successors:
            block.is_exit = True
            cfg.exit_block_ids.append(block_id)

    return cfg


def _add_edge(
    cfg: ControlFlowGraph,
    from_id: str,
    to_id: str,
    edge_type: str,
    condition: Optional[str] = None,
) -> None:
    """Helper to safely register directed CFG edges and adjacency."""
    edge = CFGEdge(from_block=from_id, to_block=to_id, edge_type=edge_type, condition=condition)
    cfg.edges.append(edge)

    from_block = cfg.blocks.get(from_id)
    to_block = cfg.blocks.get(to_id)

    if from_block and to_id not in from_block.successors:
        from_block.successors.append(to_id)
    if to_block and from_id not in to_block.predecessors:
        to_block.predecessors.append(from_id)
