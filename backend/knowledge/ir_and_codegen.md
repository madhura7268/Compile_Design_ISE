# Phase 4 (ICG) & Phase 5 (Assembly Code Generation) Specification

## Phase 4: Intermediate Code Generation (ICG)

### Purpose of Intermediate Representation
Intermediate Code Generation translates the AST into a machine-independent linear representation, bridging the gap between high-level language constructs and machine-specific assembly.

### Representation Formats
ToyLang supports three classical IR representations:
1. **Three-Address Code (3AC)**: Linear instructions of the form `result = arg1 op arg2`.
2. **Quadruples**: Structured 4-tuples `(operator, argument_1, argument_2, result)`.
3. **Triples**: 3-tuples without explicit temporary names, where results are referenced by index `(i)`.

### Quadruple Table Structure
| Operator | Argument 1 | Argument 2 | Result | Meaning |
|---|---|---|---|---|
| `=` | `val` | `None` | `x` | Direct assignment `x = val` |
| `+`, `-`, `*`, `/`, `%` | `a` | `b` | `t0` | Arithmetic binary operation |
| `==`, `!=`, `<`, `<=`, `>`, `>=` | `a` | `b` | `t0` | Relational test, result is boolean |
| `uminus` | `a` | `None` | `t0` | Unary negation `t0 = -a` |
| `ifFalse` | `t0` | `None` | `L1` | Conditional branch if false |
| `ifTrue` | `t0` | `None` | `L1` | Conditional branch if true |
| `goto` | `None` | `None` | `L2` | Unconditional jump to label |
| `label` | `None` | `None` | `L1` | Target label marker |
| `print` | `x` | `None` | `None` | Runtime print call |
| `return` | `x` | `None` | `None` | Return statement |

### Control Flow Graph (CFG)
- **Basic Blocks**: Maximal sequences of consecutive instructions with single-entry and single-exit.
- **Leaders**:
  1. The first instruction of the program.
  2. Any target of a conditional or unconditional jump (`L1`, `L2`).
  3. Any instruction immediately following a conditional or unconditional jump.
- **Edges**: Directed flow between basic blocks (fall-through edges, taken branch edges).

---

## Phase 5: Assembly Code Generation (NASM x86-64)

### Target Architecture & ABI
- **Target Architecture**: x86-64 (AMD64), NASM assembly syntax.
- **Calling Convention**: Linux System V AMD64 ABI.
- **Runtime Library**: glibc (provides `printf` and `exit`).

### Memory Layout
- **Section `.bss`**: All variables (user-declared identifiers and compiler temporaries `t0, t1, ...`) are allocated 8 bytes as QWORD:
  ```nasm
  section .bss
      a resq 1
      b resq 1
      t0 resq 1
  ```
- **Section `.rodata`**: Contains format strings for output:
  ```nasm
  section .rodata
      fmt_int db "%ld", 10, 0
  ```
- **Section `.text`**: Contains executable machine instructions starting at `global main`.

### Translation Rules: 3AC to x86-64 NASM

| IR Instruction | Generated x86-64 NASM | Rationale |
|---|---|---|
| `x = 42` | `mov rax, 42`<br>`mov [x], rax` | Immediate loaded into register then stored to memory |
| `t0 = a + b` | `mov rax, [a]`<br>`mov rbx, [b]`<br>`add rax, rbx`<br>`mov [t0], rax` | rax holds accumulator, rbx holds second operand |
| `t0 = a - b` | `mov rax, [a]`<br>`mov rbx, [b]`<br>`sub rax, rbx`<br>`mov [t0], rax` | Subtraction in rax |
| `t0 = a * b` | `mov rax, [a]`<br>`mov rbx, [b]`<br>`imul rax, rbx`<br>`mov [t0], rax` | Signed integer multiplication |
| `t0 = a / b` | `mov rax, [a]`<br>`mov rbx, [b]`<br>`cqo`<br>`idiv rbx`<br>`mov [t0], rax` | `cqo` sign-extends rax into rdx:rax; quotient is in rax |
| `t0 = a % b` | `mov rax, [a]`<br>`mov rbx, [b]`<br>`cqo`<br>`idiv rbx`<br>`mov [t0], rdx` | Remainder of `idiv` is in rdx |
| `t0 = a < b` | `mov rax, [a]`<br>`mov rbx, [b]`<br>`cmp rax, rbx`<br>`setl al`<br>`movzx rax, al`<br>`mov [t0], rax` | Comparison sets flags; `setl` captures signed less-than |
| `ifFalse t0 goto L` | `mov rax, [t0]`<br>`cmp rax, 0`<br>`je L` | Jump if false (zero) |
| `ifTrue t0 goto L` | `mov rax, [t0]`<br>`cmp rax, 0`<br>`jne L` | Jump if true (non-zero) |
| `goto L` | `jmp L` | Unconditional jump |
| `print(x)` | `mov rsi, [x]`<br>`lea rdi, [rel fmt_int]`<br>`xor eax, eax`<br>`call printf` | System V ABI: rdi=format, rsi=value, eax=0 for variadic call |
| `return x` | `mov rdi, [x]`<br>`call exit` | Pass exit code in rdi and invoke glibc exit |
