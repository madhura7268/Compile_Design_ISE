"""icg.py - Intermediate Code Generator (ICG) for ToyLang.

Implements recursive Syntax-Directed Definition (SDD) tree-walking translation to produce:
1. Linear Three-Address Code (3AC)
2. Quadruples table
3. Triples table (with indexed back-references)
4. Execution stepping trace for interactive visualizations
5. Control Flow Graph (CFG) decomposition
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from .ir_structures import (
    TempAllocator,
    LabelGenerator,
    Quadruple,
    Triple,
    ThreeAddressInstruction,
    InstructionType,
    ControlFlowGraph,
)
from .cfg import build_cfg_from_instructions


class IntermediateCodeGenerator:
    """Translates an Abstract Syntax Tree (AST) into 3AC, Quadruples, Triples, and CFG."""

    def __init__(self):
        self.temp_allocator = TempAllocator()
        self.label_generator = LabelGenerator()
        self.instructions: List[ThreeAddressInstruction] = []
        self.quadruples: List[Quadruple] = []
        self.triples: List[Triple] = []
        self.steps: List[Dict[str, Any]] = []
        self._temp_to_triple_idx: Dict[str, int] = {}

    def reset(self) -> None:
        """Reset internal state for a fresh compilation run."""
        self.temp_allocator.reset()
        self.label_generator.reset()
        self.instructions.clear()
        self.quadruples.clear()
        self.triples.clear()
        self.steps.clear()
        self._temp_to_triple_idx.clear()

    def generate(self, ast: Any) -> Dict[str, Any]:
        """Main translation entrypoint.
        
        Args:
            ast: Either a Node object, or a D3 JSON dict with {"name": ..., "children": ...}
            
        Returns:
            Dictionary containing instructions (3AC), quadruples, triples, CFG, and stepping trace.
        """
        self.reset()

        if ast is not None:
            self._log_step(
                node_name=self._get_name(ast),
                action="Starting intermediate code generation from AST root.",
            )
            self._visit_node(ast)

        # Build Control Flow Graph from the generated linear 3AC
        cfg = build_cfg_from_instructions(self.instructions)

        return {
            "success": True,
            "instructions": [inst.to_dict() for inst in self.instructions],
            "three_address_code": [inst.format_code() for inst in self.instructions],
            "quadruples": [q.to_dict() for q in self.quadruples],
            "triples": [t.to_dict() for t in self.triples],
            "cfg": cfg.to_dict(),
            "steps": list(self.steps),
            "temp_count": len(self.temp_allocator),
            "label_count": len(self.label_generator),
        }

    # -------------------------------------------------------------
    # AST Node Abstraction Helpers (supports Node objects & dicts)
    # -------------------------------------------------------------

    def _get_name(self, node: Any) -> str:
        if isinstance(node, dict):
            return node.get("name", "")
        return getattr(node, "name", "")

    def _get_children(self, node: Any) -> List[Any]:
        if isinstance(node, dict):
            return node.get("children", [])
        return getattr(node, "children", [])

    def _get_line(self, node: Any) -> Optional[int]:
        if isinstance(node, dict):
            return node.get("line")
        return getattr(node, "line", None)

    # -------------------------------------------------------------
    # Trace & Step Logging
    # -------------------------------------------------------------

    def _log_step(
        self,
        node_name: str,
        action: str,
        instruction: Optional[ThreeAddressInstruction] = None,
        quad: Optional[Quadruple] = None,
        trip: Optional[Triple] = None,
    ) -> None:
        step_entry = {
            "step": len(self.steps) + 1,
            "node_name": node_name,
            "action": action,
            "instruction": instruction.format_code() if instruction else None,
            "instruction_index": instruction.index if instruction else None,
            "quadruple": quad.to_dict() if quad else None,
            "triple": trip.to_dict() if trip else None,
            "temps": self.temp_allocator.allocated,
            "labels": self.label_generator.generated,
            "current_ir_length": len(self.instructions),
        }
        self.steps.append(step_entry)

    # -------------------------------------------------------------
    # Emission Helpers
    # -------------------------------------------------------------

    def _format_triple_arg(self, arg: Optional[str]) -> Optional[str]:
        """Convert a temporary variable into an indexed triple reference (i) if applicable."""
        if arg is None:
            return None
        if arg in self._temp_to_triple_idx:
            return f"({self._temp_to_triple_idx[arg]})"
        return str(arg)

    def _emit(
        self,
        inst_type: InstructionType,
        result: Optional[str] = None,
        op: Optional[str] = None,
        arg1: Optional[str] = None,
        arg2: Optional[str] = None,
        source_line: Optional[int] = None,
        comment: Optional[str] = None,
        node_name: str = "",
        action_desc: str = "",
    ) -> ThreeAddressInstruction:
        idx = len(self.instructions)
        inst = ThreeAddressInstruction(
            inst_type=inst_type,
            result=result,
            op=op,
            arg1=arg1,
            arg2=arg2,
            index=idx,
            source_line=source_line,
            comment=comment,
        )
        self.instructions.append(inst)

        # Quadruple emission
        quad_op = op or inst_type.value.lower()
        if inst_type == InstructionType.LABEL:
            quad_op = "label"
            quad = Quadruple(op=quad_op, arg1=None, arg2=None, result=result, index=idx)
        elif inst_type == InstructionType.GOTO:
            quad_op = "goto"
            quad = Quadruple(op=quad_op, arg1=None, arg2=None, result=result, index=idx)
        elif inst_type in {InstructionType.IF_FALSE_GOTO, InstructionType.IF_TRUE_GOTO}:
            quad_op = "ifFalse" if inst_type == InstructionType.IF_FALSE_GOTO else "ifTrue"
            quad = Quadruple(op=quad_op, arg1=arg1, arg2=None, result=result, index=idx)
        elif inst_type == InstructionType.ASSIGN:
            quad = Quadruple(op="=", arg1=arg1, arg2=None, result=result, index=idx)
        elif inst_type == InstructionType.UNARY_OP:
            quad = Quadruple(op=op or "-", arg1=arg1, arg2=None, result=result, index=idx)
        elif inst_type == InstructionType.PRINT:
            quad = Quadruple(op="print", arg1=arg1, arg2=None, result=None, index=idx)
        elif inst_type == InstructionType.RETURN:
            quad = Quadruple(op="return", arg1=arg1, arg2=None, result=None, index=idx)
        else:
            quad = Quadruple(op=op or "=", arg1=arg1, arg2=arg2, result=result, index=idx)

        self.quadruples.append(quad)

        # Triple emission
        trip_idx = len(self.triples)
        trip_a1 = self._format_triple_arg(arg1)
        trip_a2 = self._format_triple_arg(arg2)

        if inst_type == InstructionType.LABEL:
            trip = Triple(index=trip_idx, op="label", arg1=result, arg2=None)
        elif inst_type == InstructionType.GOTO:
            trip = Triple(index=trip_idx, op="goto", arg1=result, arg2=None)
        elif inst_type in {InstructionType.IF_FALSE_GOTO, InstructionType.IF_TRUE_GOTO}:
            op_name = "ifFalse" if inst_type == InstructionType.IF_FALSE_GOTO else "ifTrue"
            trip = Triple(index=trip_idx, op=op_name, arg1=trip_a1 or "", arg2=result)
        elif inst_type == InstructionType.ASSIGN:
            trip = Triple(index=trip_idx, op="=", arg1=result or "", arg2=trip_a1)
        elif inst_type == InstructionType.PRINT:
            trip = Triple(index=trip_idx, op="print", arg1=trip_a1 or "", arg2=None)
        elif inst_type == InstructionType.RETURN:
            trip = Triple(index=trip_idx, op="return", arg1=trip_a1 or "", arg2=None)
        else:
            trip = Triple(index=trip_idx, op=op or "=", arg1=trip_a1 or "", arg2=trip_a2)

        self.triples.append(trip)

        # If a temporary result was generated, map it to this triple's index
        if result and result.startswith(self.temp_allocator.prefix):
            self._temp_to_triple_idx[result] = trip_idx

        self._log_step(
            node_name=node_name or inst_type.value,
            action=action_desc or f"Emitted instruction: {inst.format_code()}",
            instruction=inst,
            quad=quad,
            trip=trip,
        )

        return inst

    # -------------------------------------------------------------
    # Recursive SDD Traversal
    # -------------------------------------------------------------

    def _visit_node(self, node: Any) -> Optional[str]:
        """Visit an AST node and return its computed value/temporary or None."""
        if node is None:
            return None

        name = self._get_name(node)
        children = self._get_children(node)

        # 1. Structural / Sequencing nodes
        if name in {"Program", "StatementList"}:
            for child in children:
                self._visit_node(child)
            return None

        if name == "Block":
            for child in children:
                self._visit_node(child)
            return None

        # 2. Variable Declaration: VarDeclaration (type)
        if name.startswith("VarDeclaration ("):
            ident_node = children[0]
            var_name = self._extract_identifier(ident_node)
            if len(children) > 1:
                # Initializer expression present
                expr_val = self._visit_node(children[1])
                self._emit(
                    inst_type=InstructionType.ASSIGN,
                    result=var_name,
                    arg1=expr_val,
                    source_line=self._get_line(node),
                    comment=f"Initialize variable '{var_name}'",
                    node_name=name,
                    action_desc=f"Declared and initialized variable '{var_name}' with value '{expr_val}'.",
                )
            else:
                self._log_step(
                    node_name=name,
                    action=f"Declared variable '{var_name}' (uninitialized).",
                )
            return None

        # 3. Assignment
        if name == "Assignment":
            ident_node = children[0]
            var_name = self._extract_identifier(ident_node)
            expr_val = self._visit_node(children[1])
            self._emit(
                inst_type=InstructionType.ASSIGN,
                result=var_name,
                arg1=expr_val,
                source_line=self._get_line(node),
                comment=f"Assign expression to '{var_name}'",
                node_name="Assignment",
                action_desc=f"Assigned value '{expr_val}' to variable '{var_name}'.",
            )
            return None

        # 4. If Statement (with or without else)
        if name == "IfStatement":
            self._translate_if(node)
            return None

        # 5. While Statement
        if name == "WhileStatement":
            self._translate_while(node)
            return None

        # 6. Print Statement
        if name == "PrintStatement":
            if children:
                val = self._visit_node(children[0])
                self._emit(
                    inst_type=InstructionType.PRINT,
                    arg1=val,
                    source_line=self._get_line(node),
                    node_name="PrintStatement",
                    action_desc=f"Emit print statement for '{val}'.",
                )
            return None

        # 7. Return Statement
        if name == "ReturnStatement":
            val = self._visit_node(children[0]) if children else None
            self._emit(
                inst_type=InstructionType.RETURN,
                arg1=val,
                source_line=self._get_line(node),
                node_name="ReturnStatement",
                action_desc=f"Emit return statement ({val or 'void'}).",
            )
            return None

        # 8. Expression Statement
        if name == "ExpressionStatement":
            if children:
                self._visit_node(children[0])
            return None

        # 9. Binary Operations: Operator: + / - / * / / / < / == etc.
        if name.startswith("Operator: "):
            op = name[len("Operator: "):].strip()
            left_val = self._visit_node(children[0])
            right_val = self._visit_node(children[1])
            temp = self.temp_allocator.new_temp()
            self._emit(
                inst_type=InstructionType.BINARY_OP,
                result=temp,
                op=op,
                arg1=left_val,
                arg2=right_val,
                source_line=self._get_line(node),
                node_name=name,
                action_desc=f"Evaluated binary operation '{op}' on '{left_val}' and '{right_val}' -> allocated temp '{temp}'.",
            )
            return temp

        # 10. Unary Operations: Unary: -
        if name.startswith("Unary: "):
            op = name[len("Unary: "):].strip()
            operand_val = self._visit_node(children[0])
            temp = self.temp_allocator.new_temp()
            self._emit(
                inst_type=InstructionType.UNARY_OP,
                result=temp,
                op=op,
                arg1=operand_val,
                source_line=self._get_line(node),
                node_name=name,
                action_desc=f"Evaluated unary '{op}' on '{operand_val}' -> allocated temp '{temp}'.",
            )
            return temp

        # 11. Identifiers
        if name.startswith("Identifier: "):
            return name[len("Identifier: "):].strip()

        # 12. Literals
        if name.startswith("Literal: "):
            return name[len("Literal: "):].strip()

        # Fallback: visit all children
        for child in children:
            self._visit_node(child)
        return None

    # -------------------------------------------------------------
    # Control Flow Handlers
    # -------------------------------------------------------------

    def _translate_if(self, node: Any) -> None:
        """Translate if-else and single-branch if constructs."""
        children = self._get_children(node)
        cond_node = None
        then_node = None
        else_node = None

        for child in children:
            cname = self._get_name(child)
            if cname == "Condition":
                cond_node = child
            elif cname == "Then":
                then_node = child
            elif cname == "Else":
                else_node = child
            elif cname == "Block":
                # Single-branch if without Then/Else wrapper
                then_node = child

        # Evaluate condition expression
        cond_val = None
        if cond_node and self._get_children(cond_node):
            cond_val = self._visit_node(self._get_children(cond_node)[0])

        if else_node is not None:
            # If-Then-Else construct
            label_else = self.label_generator.new_label()
            label_after = self.label_generator.new_label()

            # False condition jumps to else branch
            self._emit(
                inst_type=InstructionType.IF_FALSE_GOTO,
                arg1=cond_val,
                result=label_else,
                node_name="IfStatement",
                action_desc=f"Generated conditional branch: if !({cond_val}) goto {label_else}",
            )

            # Then branch
            self._visit_node(then_node)

            # Jump over else branch
            self._emit(
                inst_type=InstructionType.GOTO,
                result=label_after,
                node_name="IfStatement",
                action_desc=f"Jump to end of if-else: goto {label_after}",
            )

            # Else label
            self._emit(
                inst_type=InstructionType.LABEL,
                result=label_else,
                node_name="Else",
                action_desc=f"Defined else target label: {label_else}:",
            )

            # Else branch
            self._visit_node(else_node)

            # After label
            self._emit(
                inst_type=InstructionType.LABEL,
                result=label_after,
                node_name="IfStatement",
                action_desc=f"Defined continuation label: {label_after}:",
            )

        else:
            # Single-branch if construct
            label_after = self.label_generator.new_label()

            self._emit(
                inst_type=InstructionType.IF_FALSE_GOTO,
                arg1=cond_val,
                result=label_after,
                node_name="IfStatement",
                action_desc=f"Generated conditional branch: if !({cond_val}) goto {label_after}",
            )

            # Then branch
            self._visit_node(then_node)

            # After label
            self._emit(
                inst_type=InstructionType.LABEL,
                result=label_after,
                node_name="IfStatement",
                action_desc=f"Defined continuation label: {label_after}:",
            )

    def _translate_while(self, node: Any) -> None:
        """Translate while loop constructs."""
        children = self._get_children(node)
        cond_node = None
        body_node = None

        for child in children:
            cname = self._get_name(child)
            if cname == "Condition":
                cond_node = child
            elif cname == "Block":
                body_node = child

        label_start = self.label_generator.new_label()
        label_exit = self.label_generator.new_label()

        # Start of loop
        self._emit(
            inst_type=InstructionType.LABEL,
            result=label_start,
            node_name="WhileStatement",
            action_desc=f"Defined loop header label: {label_start}:",
        )

        # Evaluate condition
        cond_val = None
        if cond_node and self._get_children(cond_node):
            cond_val = self._visit_node(self._get_children(cond_node)[0])

        # Jump out if condition is false
        self._emit(
            inst_type=InstructionType.IF_FALSE_GOTO,
            arg1=cond_val,
            result=label_exit,
            node_name="WhileStatement",
            action_desc=f"Loop guard: if !({cond_val}) goto {label_exit}",
        )

        # Loop body
        if body_node:
            self._visit_node(body_node)

        # Loop back to header
        self._emit(
            inst_type=InstructionType.GOTO,
            result=label_start,
            node_name="WhileStatement",
            action_desc=f"Loop back edge: goto {label_start}",
        )

        # Exit label
        self._emit(
            inst_type=InstructionType.LABEL,
            result=label_exit,
            node_name="WhileStatement",
            action_desc=f"Defined loop exit label: {label_exit}:",
        )

    def _extract_identifier(self, node: Any) -> str:
        name = self._get_name(node)
        if name.startswith("Identifier: "):
            return name[len("Identifier: "):].strip()
        return name


def generate_icg(ast: Any) -> Dict[str, Any]:
    """Helper function to run intermediate code generation on an AST."""
    return IntermediateCodeGenerator().generate(ast)
