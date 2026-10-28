"""assembly_generator.py - x86-64 NASM Assembly Code Generator for ToyLang.

Translates the Three-Address Code (3AC) produced by the ICG phase into valid
x86-64 NASM assembly.  The generated code targets Linux x86-64 and uses the
System V AMD64 ABI.

Supported IR instruction types
-------------------------------
    ASSIGN        : var = src             -> mov rax, src  /  mov [var], rax
    BINARY_OP     : result = a OP b       -> +, -, *, /  (integer)
                                             <, <=, >, >=, ==, !=  (compare -> 0/1)
    UNARY_OP      : result = - a          -> neg
    LABEL         : Lx:                   -> Lx:
    GOTO          : goto Lx               -> jmp Lx
    IF_FALSE_GOTO : ifFalse t goto Lx     -> cmp [t], 0  / je Lx
    IF_TRUE_GOTO  : ifTrue  t goto Lx     -> cmp [t], 0  / jne Lx
    IF_CMP_GOTO   : if a OP b goto Lx     -> cmp + conditional jump
    PRINT         : print var             -> printf via C stdlib wrapper
    RETURN        : return / return val   -> mov rax, val / ret

Variables are stored as 8-byte (QWORD) locals in the .bss or stack section.
All integer variables are treated as 64-bit signed integers (int64).
Float variables declared in the source are silently treated as int64 in this
phase (matching the existing ICG behaviour).

Runtime dependency
------------------
The generated NASM file requires linking against the C standard library so
that printf / exit are available.  Typical build commands:

    nasm -f elf64 output.asm -o output.o
    gcc -no-pie output.o -o output
    ./output

Architecture notes
------------------
* All variables (user variables and temporaries) are stored as QWORD in .bss.
* Arithmetic uses rax / rbx scratch registers.
* Division: uses idiv which requires rdx:rax / cqo sign-extension.
* Comparisons: result of a comparison is stored as 0 or 1 (int64).
* print: calls C printf with format string "%ld\\n".
"""

from typing import List, Dict, Any, Optional, Set


# ---------------------------------------------------------------------------
# Operator mappings
# ---------------------------------------------------------------------------

# Arithmetic binary operators (result = a OP b)
_ARITH_OPS: Set[str] = {"+", "-", "*", "/", "%"}

# Relational / comparison operators -> produce 0 or 1 in result
_CMP_OPS: Set[str] = {"<", "<=", ">", ">=", "==", "!="}

# Map comparison operator -> NASM conditional set instruction
_SETCC: Dict[str, str] = {
    "<":  "setl",
    "<=": "setle",
    ">":  "setg",
    ">=": "setge",
    "==": "sete",
    "!=": "setne",
}

# Map comparison operator -> conditional *jump* instruction (for IF_CMP_GOTO)
_JCC: Dict[str, str] = {
    "<":  "jl",
    "<=": "jle",
    ">":  "jg",
    ">=": "jge",
    "==": "je",
    "!=": "jne",
}


class AssemblyGenerationError(Exception):
    """Raised when the assembly generator cannot translate an IR instruction."""


class AssemblyGenerator:
    """Translates a list of ThreeAddressInstruction dicts into x86-64 NASM assembly.

    Usage::

        gen = AssemblyGenerator()
        result = gen.generate(icg_result["instructions"])
        print(result["assembly"])
    """

    TARGET = "x86-64 (NASM, Linux System V AMD64 ABI)"

    def __init__(self) -> None:
        self._lines: List[str] = []        # Body of the .text section
        self._variables: Set[str] = set()  # All variable/temp names seen
        self._errors: List[str] = []       # Non-fatal error messages
        self._print_used: bool = False     # Whether printf is needed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, instructions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate x86-64 NASM assembly from a list of serialised 3AC dicts.

        Args:
            instructions: The list of ``inst.to_dict()`` items from the ICG.

        Returns:
            A dict with keys:
                success   : bool
                assembly  : str   (the full NASM source)
                target    : str   (human-readable architecture string)
                errors    : list  (any non-fatal warnings / unsupported ops)
                error     : str | None  (first fatal error, or None)
        """
        self._reset()

        try:
            # First pass: collect all variable / temporary names
            self._collect_variables(instructions)

            # Second pass: translate each instruction
            for inst in instructions:
                self._translate(inst)

        except AssemblyGenerationError as exc:
            return {
                "success": False,
                "assembly": "",
                "target": self.TARGET,
                "errors": self._errors,
                "error": str(exc),
            }

        asm = self._build_asm_source()
        return {
            "success": True,
            "assembly": asm,
            "target": self.TARGET,
            "errors": self._errors,
            "error": None,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        self._lines = []
        self._variables = set()
        self._errors = []
        self._print_used = False

    def _emit(self, line: str) -> None:
        self._lines.append(line)

    def _collect_variables(self, instructions: List[Dict[str, Any]]) -> None:
        """First-pass: register every variable name that will need storage."""
        for inst in instructions:
            inst_type = inst.get("type", "")
            result = inst.get("result")
            arg1   = inst.get("arg1")
            arg2   = inst.get("arg2")

            # Labels and goto targets are not variables
            if inst_type == "LABEL":
                continue
            if inst_type == "GOTO":
                continue

            # result is a variable for most instruction types
            if result and inst_type not in ("GOTO", "LABEL", "IF_FALSE_GOTO",
                                             "IF_TRUE_GOTO", "IF_CMP_GOTO",
                                             "PRINT", "RETURN"):
                if not self._is_literal(result):
                    self._variables.add(result)

            # arg1 / arg2 might be previously undeclared temps from prior ICG runs
            for arg in (arg1, arg2):
                if arg and not self._is_literal(arg):
                    self._variables.add(arg)

    @staticmethod
    def _is_literal(value: str) -> bool:
        """Return True if *value* is an integer or float literal."""
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            pass
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            pass
        return False

    @staticmethod
    def _operand(value: str) -> str:
        """Return NASM operand string for a variable or literal.

        Literals become raw integer constants; variables become memory refs.
        Float literals from ToyLang are truncated to int (matching ICG).
        """
        if value is None:
            return "0"
        # Integer literal
        try:
            return str(int(value))
        except (ValueError, TypeError):
            pass
        # Float literal -> truncate to int
        try:
            return str(int(float(value)))
        except (ValueError, TypeError):
            pass
        # Variable / temporary: 64-bit memory reference
        return f"[{value}]"

    def _load_to_rax(self, value: str) -> None:
        """Emit instruction(s) to load *value* into rax."""
        if self._is_literal(value):
            lit = str(int(float(value)))
            self._emit(f"    mov rax, {lit}")
        else:
            self._emit(f"    mov rax, [{value}]")

    def _load_to_rbx(self, value: str) -> None:
        """Emit instruction(s) to load *value* into rbx."""
        if self._is_literal(value):
            lit = str(int(float(value)))
            self._emit(f"    mov rbx, {lit}")
        else:
            self._emit(f"    mov rbx, [{value}]")

    def _store_rax_to(self, dest: str) -> None:
        """Store rax into a named variable."""
        self._emit(f"    mov [{dest}], rax")

    # ------------------------------------------------------------------
    # Instruction translators
    # ------------------------------------------------------------------

    def _translate(self, inst: Dict[str, Any]) -> None:
        inst_type = inst.get("type", "")
        handler = {
            "ASSIGN":        self._tr_assign,
            "BINARY_OP":     self._tr_binary_op,
            "UNARY_OP":      self._tr_unary_op,
            "LABEL":         self._tr_label,
            "GOTO":          self._tr_goto,
            "IF_FALSE_GOTO": self._tr_if_false_goto,
            "IF_TRUE_GOTO":  self._tr_if_true_goto,
            "IF_CMP_GOTO":   self._tr_if_cmp_goto,
            "PRINT":         self._tr_print,
            "RETURN":        self._tr_return,
        }.get(inst_type)

        if handler is None:
            msg = (
                f"Unsupported IR instruction type '{inst_type}' "
                f"(code: {inst.get('code', '?')}). Skipped."
            )
            self._errors.append(msg)
            self._emit(f"    ; UNSUPPORTED: {inst.get('code', inst_type)}")
            return

        # Emit a readable comment showing the original 3AC line
        tac_code = inst.get("code", "")
        if tac_code:
            self._emit(f"    ; {tac_code}")

        handler(inst)
        self._emit("")  # blank line for readability

    # --- ASSIGN ---
    def _tr_assign(self, inst: Dict[str, Any]) -> None:
        dest = inst["result"]
        src  = inst["arg1"]
        self._load_to_rax(src)
        self._store_rax_to(dest)

    # --- BINARY_OP ---
    def _tr_binary_op(self, inst: Dict[str, Any]) -> None:
        op     = inst["op"]
        result = inst["result"]
        left   = inst["arg1"]
        right  = inst["arg2"]

        if op in _ARITH_OPS:
            self._emit_arith(op, left, right, result)
        elif op in _CMP_OPS:
            self._emit_compare(op, left, right, result)
        else:
            msg = (
                f"Unknown binary operator '{op}' in instruction "
                f"'{inst.get('code', '?')}'. Skipped."
            )
            self._errors.append(msg)
            self._emit(f"    ; UNSUPPORTED OPERATOR: {op}")

    def _emit_arith(self, op: str, left: str, right: str, result: str) -> None:
        self._load_to_rax(left)
        self._load_to_rbx(right)

        if op == "+":
            self._emit("    add rax, rbx")
        elif op == "-":
            self._emit("    sub rax, rbx")
        elif op == "*":
            self._emit("    imul rax, rbx")
        elif op in ("/", "%"):
            # idiv: rdx:rax / rbx  -> quotient rax, remainder rdx
            self._emit("    cqo")              # sign-extend rax into rdx:rax
            self._emit("    idiv rbx")
            if op == "%":
                self._emit("    mov rax, rdx")  # remainder is in rdx

        self._store_rax_to(result)

    def _emit_compare(self, op: str, left: str, right: str, result: str) -> None:
        """Emit comparison; store 1 in result if true, 0 otherwise."""
        self._load_to_rax(left)
        self._load_to_rbx(right)
        self._emit("    cmp rax, rbx")
        setcc = _SETCC[op]
        self._emit(f"    {setcc} al")         # set al to 0 or 1
        self._emit("    movzx rax, al")       # zero-extend al into rax
        self._store_rax_to(result)

    # --- UNARY_OP ---
    def _tr_unary_op(self, inst: Dict[str, Any]) -> None:
        op     = inst["op"]
        result = inst["result"]
        arg    = inst["arg1"]

        if op in ("-", "uminus"):
            self._load_to_rax(arg)
            self._emit("    neg rax")
            self._store_rax_to(result)
        else:
            msg = f"Unsupported unary operator '{op}'. Skipped."
            self._errors.append(msg)
            self._emit(f"    ; UNSUPPORTED UNARY: {op}")

    # --- LABEL ---
    def _tr_label(self, inst: Dict[str, Any]) -> None:
        label = inst["result"]
        # Remove trailing comment added by _translate()
        # Pop the last comment line we emitted (we want label on its own line)
        if self._lines and self._lines[-1].startswith(f"    ; {label}:"):
            self._lines.pop()
        self._emit(f"{label}:")

    # --- GOTO ---
    def _tr_goto(self, inst: Dict[str, Any]) -> None:
        label = inst["result"]
        self._emit(f"    jmp {label}")

    # --- IF_FALSE_GOTO ---
    def _tr_if_false_goto(self, inst: Dict[str, Any]) -> None:
        """ifFalse arg1 goto label  ->  jump if arg1 == 0"""
        condition = inst["arg1"]
        label     = inst["result"]
        self._load_to_rax(condition)
        self._emit("    cmp rax, 0")
        self._emit(f"    je {label}")

    # --- IF_TRUE_GOTO ---
    def _tr_if_true_goto(self, inst: Dict[str, Any]) -> None:
        """ifTrue arg1 goto label  ->  jump if arg1 != 0"""
        condition = inst["arg1"]
        label     = inst["result"]
        self._load_to_rax(condition)
        self._emit("    cmp rax, 0")
        self._emit(f"    jne {label}")

    # --- IF_CMP_GOTO ---
    def _tr_if_cmp_goto(self, inst: Dict[str, Any]) -> None:
        """if arg1 OP arg2 goto label"""
        left  = inst["arg1"]
        right = inst["arg2"]
        op    = inst["op"]
        label = inst["result"]

        if op not in _JCC:
            msg = f"Unsupported comparison operator '{op}' in IF_CMP_GOTO. Skipped."
            self._errors.append(msg)
            self._emit(f"    ; UNSUPPORTED IF_CMP_GOTO op: {op}")
            return

        self._load_to_rax(left)
        self._load_to_rbx(right)
        self._emit("    cmp rax, rbx")
        self._emit(f"    {_JCC[op]} {label}")

    # --- PRINT ---
    def _tr_print(self, inst: Dict[str, Any]) -> None:
        """print arg1  ->  call printf with "%ld\n" format"""
        arg = inst["arg1"]
        self._print_used = True

        # printf(fmt_str, value)
        # System V AMD64: rdi = 1st arg (fmt ptr), rsi = 2nd arg (value)
        # We need to respect the 16-byte stack alignment requirement.
        self._emit("    sub rsp, 8          ; align stack to 16 bytes")
        if self._is_literal(arg):
            lit = str(int(float(arg)))
            self._emit(f"    mov rsi, {lit}")
        else:
            self._emit(f"    mov rsi, [{arg}]")
        self._emit("    lea rdi, [rel fmt_int]")
        self._emit("    xor eax, eax        ; no XMM registers used")
        self._emit("    call printf")
        self._emit("    add rsp, 8          ; restore stack")

    # --- RETURN ---
    def _tr_return(self, inst: Dict[str, Any]) -> None:
        arg = inst.get("arg1")
        if arg:
            self._load_to_rax(arg)
        else:
            self._emit("    xor rax, rax")
        # In our standalone entry point (_start / main) we call exit()
        self._emit("    ; return -> store value, then jump to _exit_program")
        self._emit("    mov rdi, rax")
        self._emit("    call exit")

    # ------------------------------------------------------------------
    # Final assembly source builder
    # ------------------------------------------------------------------

    def _build_asm_source(self) -> str:
        parts: List[str] = []

        # ----- Header comment -----
        parts.append("; ============================================================")
        parts.append("; ToyLang x86-64 NASM Assembly Output")
        parts.append("; Target  : x86-64 Linux (System V AMD64 ABI)")
        parts.append("; Build   : nasm -f elf64 output.asm -o output.o")
        parts.append(";           gcc -no-pie output.o -o output")
        parts.append(";           ./output")
        parts.append("; ============================================================")
        parts.append("")

        # ----- Extern declarations -----
        if self._print_used:
            parts.append('extern printf')
        parts.append('extern exit')
        parts.append("")

        # ----- .data section (format strings) -----
        parts.append("section .data")
        if self._print_used:
            parts.append('    fmt_int  db "%ld", 10, 0   ; "%ld\n" for printf')
        parts.append("")

        # ----- .bss section (uninitialised variable storage) -----
        parts.append("section .bss")
        # Emit in sorted order for determinism
        for var in sorted(self._variables):
            parts.append(f"    {var:<16} resq 1    ; int64 variable '{var}'")
        if not self._variables:
            parts.append("    ; (no variables)")
        parts.append("")

        # ----- .text section -----
        parts.append("section .text")
        parts.append("    global main")
        parts.append("")
        parts.append("main:")
        parts.append("    push rbp")
        parts.append("    mov rbp, rsp")
        parts.append("")

        # Insert translated body
        for line in self._lines:
            parts.append(line)

        # Epilogue: normal exit (fall-through when no explicit return)
        parts.append("    ; --- program exit ---")
        parts.append("    xor rdi, rdi")
        parts.append("    call exit")
        parts.append("")

        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Public convenience wrapper
# ---------------------------------------------------------------------------

def generate_assembly(icg_result: Dict[str, Any]) -> Dict[str, Any]:
    """Translate an ICG result dict into x86-64 NASM assembly.

    Args:
        icg_result: The dict returned by ``generate_icg()`` / ``icg.generate()``.
                    Must have ``success == True`` and an ``instructions`` list.

    Returns:
        A result dict with keys:
            success   : bool
            assembly  : str
            target    : str
            errors    : list[str]
            error     : str | None
    """
    if not icg_result or not icg_result.get("success", False):
        return {
            "success": False,
            "assembly": "",
            "target": AssemblyGenerator.TARGET,
            "errors": [],
            "error": "Cannot generate assembly: ICG phase did not succeed.",
        }

    instructions = icg_result.get("instructions", [])
    if not instructions:
        return {
            "success": False,
            "assembly": "",
            "target": AssemblyGenerator.TARGET,
            "errors": [],
            "error": "Cannot generate assembly: ICG produced no instructions.",
        }

    return AssemblyGenerator().generate(instructions)
