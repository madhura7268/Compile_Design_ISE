# ToyLang Compiler

A full educational compiler for **ToyLang** — a small, statically-typed language — built as an Integrated Software Engineering project.  
The compiler covers all five classical phases: Lexical Analysis → Syntax Analysis → Semantic Analysis → Intermediate Code Generation → **Assembly Code Generation (Phase 5, x86-64 NASM)**.

---

## Language Features (ToyLang)

| Construct              | Syntax example                                      |
|------------------------|-----------------------------------------------------|
| Integer declaration    | `int x = 10;`                                       |
| Float declaration      | `float y = 3.14;`                                   |
| Assignment             | `x = x + 1;`                                        |
| Arithmetic             | `+  -  *  /  %`                                     |
| Comparison             | `<  <=  >  >=  ==  !=`                              |
| Unary minus            | `int z = -x;`                                       |
| If statement           | `if (x > 0) { ... }`                                |
| If-else statement      | `if (x > 0) { ... } else { ... }`                   |
| While loop             | `while (x < 10) { ... }`                            |
| Print                  | `print(x);`                                         |
| Return                 | `return x;` or `return;`                            |
| Block scoping          | `{ ... }`                                           |

---

## Compiler Phases

```
Source Code
    │
    ▼ Phase 1 ─ Lexical Analysis (PLY lex)
    │            Tokens, Symbol Table
    ▼ Phase 2 ─ Syntax Analysis (PLY LALR(1))
    │            Parse Tree (AST)
    ▼ Phase 3 ─ Semantic Analysis
    │            Type checking, scope resolution
    ▼ Phase 4 ─ Intermediate Code Generation
    │            3AC, Quadruples, Triples, CFG
    ▼ Phase 5 ─ Assembly Code Generation  ← NEW
                 x86-64 NASM (Linux System V AMD64 ABI)
```

---

## Assembly Code Generation (Phase 5)

### Target Architecture
**x86-64, NASM syntax, Linux System V AMD64 ABI**

### Supported IR Operations → Assembly

| IR Instruction          | Generated Assembly                                 |
|-------------------------|----------------------------------------------------|
| `x = 42`                | `mov rax, 42` / `mov [x], rax`                     |
| `t0 = a + b`            | `mov rax,[a]` / `mov rbx,[b]` / `add rax,rbx`     |
| `t0 = a - b`            | `sub rax, rbx`                                     |
| `t0 = a * b`            | `imul rax, rbx`                                    |
| `t0 = a / b`            | `cqo` / `idiv rbx` → quotient in rax               |
| `t0 = a % b`            | `cqo` / `idiv rbx` → `mov rax, rdx` (remainder)   |
| `t0 = -a`               | `neg rax`                                          |
| `t0 = a < b`            | `cmp rax,rbx` / `setl al` / `movzx rax,al`        |
| `t0 = a == b`           | `sete al` / `movzx rax,al`                         |
| `ifFalse t0 goto L`     | `cmp rax,0` / `je L`                               |
| `ifTrue t0 goto L`      | `cmp rax,0` / `jne L`                              |
| `goto L`                | `jmp L`                                            |
| `L:`                    | `L:`                                               |
| `print(x)`              | `mov rsi,[x]` / `lea rdi,[rel fmt_int]` / `call printf` |
| `return x`              | `mov rdi,rax` / `call exit`                        |

### Variables Storage
All variables (user-declared and temporaries `t0, t1, ...`) are stored as 8-byte `QWORD` in the `.bss` section.

### Build & Run
```bash
# 1. Assemble
nasm -f elf64 output.asm -o output.o

# 2. Link (GCC provides glibc automatically)
gcc -no-pie output.o -o output

# 3. Run
./output
```

> **Platform:** Linux x86-64. On Windows, use WSL 2 with Ubuntu.

---

## Sample: Arithmetic Program

**ToyLang Source:**
```c
int a = 10;
int b = 3;
int c = a + b * 2;
```

**Generated 3AC:**
```
 0: a = 10
 1: b = 3
 2: t0 = b * 2
 3: t1 = a + t0
 4: c = t1
```

**Generated x86-64 NASM Assembly:**
```nasm
; ToyLang x86-64 NASM Assembly Output
; Build: nasm -f elf64 output.asm -o output.o && gcc -no-pie output.o -o output

extern exit

section .bss
    a                resq 1    ; int64 variable 'a'
    b                resq 1    ; int64 variable 'b'
    c                resq 1    ; int64 variable 'c'
    t0               resq 1    ; int64 variable 't0'
    t1               resq 1    ; int64 variable 't1'

section .text
    global main

main:
    push rbp
    mov rbp, rsp

    ; a = 10
    mov rax, 10
    mov [a], rax

    ; b = 3
    mov rax, 3
    mov [b], rax

    ; t0 = b * 2
    mov rax, [b]
    mov rbx, 2
    imul rax, rbx
    mov [t0], rax

    ; t1 = a + t0
    mov rax, [a]
    mov rbx, [t0]
    add rax, rbx
    mov [t1], rax

    ; c = t1
    mov rax, [t1]
    mov [c], rax

    ; --- program exit ---
    xor rdi, rdi
    call exit
```

---

## Sample: While Loop + Print

**ToyLang Source:**
```c
int i = 0;
while (i < 3) {
    i = i + 1;
}
print(i);
```

**Generated x86-64 NASM Assembly (excerpt):**
```nasm
    ; i = 0
    mov rax, 0
    mov [i], rax

L0:
    ; t0 = i < 3
    mov rax, [i]
    mov rbx, 3
    cmp rax, rbx
    setl al
    movzx rax, al
    mov [t0], rax

    ; ifFalse t0 goto L1
    mov rax, [t0]
    cmp rax, 0
    je L1

    ; i = i + 1
    ...
    ; goto L0
    jmp L0

L1:
    ; print(i)
    sub rsp, 8
    mov rsi, [i]
    lea rdi, [rel fmt_int]
    xor eax, eax
    call printf
    add rsp, 8

    xor rdi, rdi
    call exit
```

---

## Setup

### Requirements
- Python 3.10+
- NASM 2.14+ (optional — only needed to assemble output)
- GCC (optional — only needed to link)
- WSL 2 or Linux (for assembling and running)

### Install Python Dependencies
```bash
pip install -r backend/requirements.txt
```

### Run the Main Compiler UI
```bash
# Windows
run_app.bat

# Or directly
streamlit run backend/app.py --server.address 127.0.0.1 --server.port 8501
```

### Run the Dedicated ICG + Assembly Visualizer
```bash
# Windows
run_visualizer.bat

# Or directly
streamlit run backend/icg_app.py --server.address 127.0.0.1 --server.port 8502
```

### Run Tests
```bash
python -m pytest backend -v
```

---

## Project Structure

```
Compile_Design_ISE/
├── backend/
│   ├── app.py                     # Main Streamlit UI (5 analysis tabs)
│   ├── icg_app.py                 # Dedicated ICG + Assembly visualizer
│   ├── requirements.txt
│   └── app/
│       ├── lexer/                 # Phase 1: Lexical Analysis
│       │   ├── lexer.py
│       │   ├── tokens.py
│       │   └── symbol_table.py
│       ├── parser/                # Phase 2: Syntax Analysis
│       │   ├── grammar.py
│       │   └── tree_builder.py
│       ├── semantic/              # Phase 3: Semantic Analysis
│       │   ├── semantic_analyzer.py
│       │   └── pipeline.py        # compile_source() — all 5 phases
│       ├── icg/                   # Phase 4: Intermediate Code Generation
│       │   ├── icg.py
│       │   ├── ir_structures.py
│       │   └── cfg.py
│       └── codegen/               # Phase 5: Assembly Code Generation ← NEW
│           ├── assembly_generator.py
│           └── tests/
│               └── test_assembly_generator.py
├── visualizer/                    # JavaScript-based standalone visualizer
├── run_app.bat
└── run_visualizer.bat
```

---

## Test Coverage

| Phase                     | Tests |
|---------------------------|-------|
| Lexer                     | 14    |
| Parser                    | 14    |
| Semantic Analyzer         | 33    |
| ICG (Quadruples/Triples)  | 18    |
| **Assembly Generator**    | **55**|
| **Total**                 | **134**|

All 134 tests pass (`python -m pytest backend -v`).

---

## Notes

- **NASM assembly validation:** The assembly syntax was verified by inspection against the NASM manual and x86-64 System V ABI documentation. Full end-to-end execution testing (assemble → link → run) requires NASM + GCC on Linux x86-64 or WSL 2, which was not available in the current environment.
- **Float variables** declared with `float` are treated as `int64` in the assembly output (matching the ICG behaviour — no floating-point registers are used).
- **Unsupported IR operations** produce a clear comment `; UNSUPPORTED: ...` and an error entry in the result, rather than silent incorrect output.
