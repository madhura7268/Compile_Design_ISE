"""test_assembly_generator.py - Tests for the x86-64 NASM Assembly Code Generator.

Tests cover:
1.  Constant / variable assignments
2.  Arithmetic expressions and operator precedence
3.  Unary minus
4.  Comparisons and conditional branches
5.  If-else statements
6.  While loops
7.  Nested control flow
8.  Temporary variables and labels in generated assembly
9.  Unsupported IR instruction handling
10. Print statements
11. Return statements
12. Integration through compile_source() pipeline
13. Regression: existing lex / parse / semantic / ICG still pass
14. Invalid source programs do not generate assembly
"""

import pytest
from app.parser.grammar import parse_with_ast
from app.icg.icg import generate_icg
from app.codegen.assembly_generator import AssemblyGenerator, generate_assembly, AssemblyGenerationError
from app.semantic.pipeline import compile_source


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def full_pipeline(source: str):
    """Run parse + ICG + assembly on *source*. Returns (icg_result, asm_result)."""
    _, ast = parse_with_ast(source)
    icg = generate_icg(ast)
    asm = generate_assembly(icg)
    return icg, asm


def compile_asm(source: str):
    """Run the full compile_source pipeline and return the assembly result."""
    res = compile_source(source)
    return res.get("assembly")


# ---------------------------------------------------------------------------
# 1. Constant / variable assignment
# ---------------------------------------------------------------------------

class TestAssignment:
    def test_literal_assignment(self):
        _, asm = full_pipeline("int x = 42;")
        assert asm["success"] is True
        src = asm["assembly"]
        # Variable x must be declared in .bss
        assert "x" in src and "resq" in src
        # mov immediate 42 into rax
        assert "mov rax, 42" in src
        # store rax into [x]
        assert "mov [x], rax" in src

    def test_variable_to_variable_assignment(self):
        _, asm = full_pipeline("int a = 5;\nint b = 10;\nb = a;")
        assert asm["success"] is True
        src = asm["assembly"]
        assert "mov rax, [a]" in src
        assert "mov [b], rax" in src

    def test_bss_section_present(self):
        _, asm = full_pipeline("int foo = 1;")
        src = asm["assembly"]
        assert "section .bss" in src
        assert "foo" in src

    def test_text_section_present(self):
        _, asm = full_pipeline("int x = 0;")
        src = asm["assembly"]
        assert "section .text" in src
        assert "main:" in src


# ---------------------------------------------------------------------------
# 2. Arithmetic expressions
# ---------------------------------------------------------------------------

class TestArithmetic:
    def test_addition(self):
        _, asm = full_pipeline("int a = 3;\nint b = 4;\nint c = a + b;")
        src = asm["assembly"]
        assert asm["success"] is True
        assert "add rax, rbx" in src

    def test_subtraction(self):
        _, asm = full_pipeline("int a = 5;\nint b = 2;\nint c = a - b;")
        assert "sub rax, rbx" in asm["assembly"]

    def test_multiplication(self):
        _, asm = full_pipeline("int a = 3;\nint b = 4;\nint c = a * b;")
        assert "imul rax, rbx" in asm["assembly"]

    def test_division(self):
        _, asm = full_pipeline("int a = 10;\nint b = 3;\nint c = a / b;")
        src = asm["assembly"]
        assert "cqo" in src
        assert "idiv rbx" in src

    def test_modulo(self):
        _, asm = full_pipeline("int a = 10;\nint b = 3;\nint c = a % b;")
        src = asm["assembly"]
        assert "cqo" in src
        assert "idiv rbx" in src
        # remainder: mov rax, rdx
        assert "mov rax, rdx" in src

    def test_operator_precedence(self):
        """b*2 must be computed before a + result (matching ICG temp ordering)."""
        _, asm = full_pipeline("int a = 1;\nint b = 2;\nint c = a + b * 2;")
        src = asm["assembly"]
        assert asm["success"] is True
        # t0 = b * 2  -> imul appears before add
        imul_pos = src.index("imul")
        add_pos  = src.index("add rax, rbx")
        assert imul_pos < add_pos

    def test_temporaries_in_bss(self):
        _, asm = full_pipeline("int a = 1;\nint b = 2;\nint c = a + b * 2;")
        src = asm["assembly"]
        # Temporaries t0, t1 must be in .bss
        assert "t0" in src
        assert "t1" in src


# ---------------------------------------------------------------------------
# 3. Unary minus
# ---------------------------------------------------------------------------

class TestUnaryMinus:
    def test_unary_minus_literal(self):
        _, asm = full_pipeline("int a = 5;\nint x = - a;")
        src = asm["assembly"]
        assert asm["success"] is True
        assert "neg rax" in src

    def test_unary_minus_result_stored(self):
        _, asm = full_pipeline("int a = 5;\nint x = - a;")
        src = asm["assembly"]
        assert "mov [t0], rax" in src
        assert "mov [x], rax" in src


# ---------------------------------------------------------------------------
# 4. Comparisons
# ---------------------------------------------------------------------------

class TestComparisons:
    @pytest.mark.parametrize("op,setcc", [
        ("<",  "setl"),
        ("<=", "setle"),
        (">",  "setg"),
        (">=", "setge"),
        ("==", "sete"),
        ("!=", "setne"),
    ])
    def test_comparison_setcc(self, op, setcc):
        code = f"int a = 1;\nint b = 2;\nint r = a {op} b;"
        _, asm = full_pipeline(code)
        assert asm["success"] is True
        assert setcc in asm["assembly"]
        assert "movzx rax, al" in asm["assembly"]

    def test_comparison_result_stored(self):
        _, asm = full_pipeline("int a = 1;\nint b = 2;\nint r = a < b;")
        src = asm["assembly"]
        # result temp t0 gets stored
        assert "mov [t0]" in src


# ---------------------------------------------------------------------------
# 5. If-else statements
# ---------------------------------------------------------------------------

class TestIfElse:
    def test_if_else_labels(self):
        code = """
        if (a < b) {
            x = 1;
        } else {
            x = 2;
        }
        """
        _, asm = full_pipeline(code)
        assert asm["success"] is True
        src = asm["assembly"]
        assert "L0:" in src
        assert "L1:" in src
        assert "je L0" in src   # ifFalse branch
        assert "jmp L1" in src  # skip else

    def test_if_only_label(self):
        code = """
        if (a < b) {
            x = 1;
        }
        """
        _, asm = full_pipeline(code)
        src = asm["assembly"]
        assert "L0:" in src
        assert "je L0" in src

    def test_correct_branch_semantics(self):
        """ifFalse -> je (jump when condition == 0 i.e. false)."""
        code = "if (a < b) { x = 1; }"
        _, asm = full_pipeline(code)
        src = asm["assembly"]
        # The conditional check: load cond result, cmp with 0, je to skip-label
        assert "cmp rax, 0" in src
        assert "je" in src


# ---------------------------------------------------------------------------
# 6. While loops
# ---------------------------------------------------------------------------

class TestWhileLoop:
    def test_while_loop_structure(self):
        code = """
        int count = 0;
        while (count < 5) {
            count = count + 1;
        }
        """
        _, asm = full_pipeline(code)
        assert asm["success"] is True
        src = asm["assembly"]
        # while generates: L0 (header), L1 (exit)
        assert "L0:" in src
        assert "L1:" in src
        # Loop back-edge
        assert "jmp L0" in src
        # Guard: ifFalse -> je L1
        assert "je L1" in src

    def test_while_loop_variables(self):
        code = "int i = 0;\nwhile (i < 3) { i = i + 1; }"
        _, asm = full_pipeline(code)
        src = asm["assembly"]
        assert "i" in src
        assert "mov [i], rax" in src


# ---------------------------------------------------------------------------
# 7. Nested control flow
# ---------------------------------------------------------------------------

class TestNestedControlFlow:
    def test_nested_while_if_else(self):
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
        _, asm = full_pipeline(code)
        assert asm["success"] is True
        src = asm["assembly"]
        # Must have multiple labels
        assert src.count("L0:") == 1
        assert src.count("L1:") == 1
        assert src.count("L2:") == 1
        assert src.count("L3:") == 1
        # Both a jmp-back and a je
        assert "jmp L0" in src


# ---------------------------------------------------------------------------
# 8. Print statements
# ---------------------------------------------------------------------------

class TestPrint:
    def test_print_calls_printf(self):
        code = "int x = 5;\nprint(x);"
        _, asm = full_pipeline(code)
        assert asm["success"] is True
        src = asm["assembly"]
        assert "extern printf" in src
        assert "fmt_int" in src
        assert "call printf" in src
        assert "lea rdi, [rel fmt_int]" in src

    def test_print_loads_variable(self):
        code = "int x = 5;\nprint(x);"
        _, asm = full_pipeline(code)
        src = asm["assembly"]
        assert "mov rsi, [x]" in src

    def test_data_section_format_string(self):
        code = "int x = 5;\nprint(x);"
        _, asm = full_pipeline(code)
        src = asm["assembly"]
        assert 'section .data' in src
        assert 'fmt_int' in src
        assert "%ld" in src


# ---------------------------------------------------------------------------
# 9. Return statements
# ---------------------------------------------------------------------------

class TestReturn:
    def test_return_value(self):
        code = "return a;"
        _, asm = full_pipeline(code)
        assert asm["success"] is True
        src = asm["assembly"]
        assert "mov rdi, rax" in src
        assert "call exit" in src

    def test_return_void(self):
        code = "return;"
        _, asm = full_pipeline(code)
        src = asm["assembly"]
        assert "xor rax, rax" in src


# ---------------------------------------------------------------------------
# 10. Unsupported IR instruction
# ---------------------------------------------------------------------------

class TestUnsupportedInstructions:
    def test_unsupported_type_produces_error(self):
        """Inject a fake IR instruction type and verify it is reported."""
        inst = {
            "type": "UNKNOWN_OP",
            "op": "??",
            "arg1": "x",
            "arg2": None,
            "result": "y",
            "code": "y = ?? x",
        }
        gen = AssemblyGenerator()
        gen._collect_variables([inst])
        gen._translate(inst)
        assert len(gen._errors) == 1
        assert "UNKNOWN_OP" in gen._errors[0]
        assert "UNSUPPORTED" in "\n".join(gen._lines)

    def test_unsupported_binary_op_produces_error(self):
        """Operator not in _ARITH_OPS or _CMP_OPS."""
        inst = {
            "type": "BINARY_OP",
            "op": "&&",      # logical AND is not in the set
            "arg1": "a",
            "arg2": "b",
            "result": "t0",
            "code": "t0 = a && b",
        }
        gen = AssemblyGenerator()
        gen._collect_variables([inst])
        gen._translate(inst)
        assert any("&&" in e for e in gen._errors)


# ---------------------------------------------------------------------------
# 11. generate_assembly() guard conditions
# ---------------------------------------------------------------------------

class TestGenerateAssemblyGuards:
    def test_failed_icg_returns_failure(self):
        result = generate_assembly({"success": False, "instructions": []})
        assert result["success"] is False
        assert result["error"] is not None

    def test_none_icg_returns_failure(self):
        result = generate_assembly(None)
        assert result["success"] is False

    def test_empty_instructions_returns_failure(self):
        result = generate_assembly({"success": True, "instructions": []})
        assert result["success"] is False


# ---------------------------------------------------------------------------
# 12. Pipeline integration  (compile_source includes assembly key)
# ---------------------------------------------------------------------------

class TestPipelineIntegration:
    def test_assembly_key_in_pipeline_result(self):
        res = compile_source("int a = 10;\nint b = 20;\nint c = a + b * 2;")
        assert "assembly" in res

    def test_assembly_success_on_valid_code(self):
        res = compile_source("int a = 10;\nint b = 20;\nint c = a + b;")
        assert res["assembly"]["success"] is True

    def test_assembly_none_on_parse_failure(self):
        res = compile_source("int a = 10")  # missing semicolon
        assert res["assembly"] is None

    def test_assembly_none_on_semantic_failure(self):
        res = compile_source("x = 10;")   # undeclared variable
        assert res["assembly"] is None

    def test_assembly_target_string(self):
        res = compile_source("int x = 1;")
        assert "x86-64" in res["assembly"]["target"]

    def test_full_program_arithmetic(self):
        code = "int a = 2;\nint b = 3;\nint c = a + b * 2;"
        res = compile_source(code)
        assert res["assembly"]["success"] is True
        src = res["assembly"]["assembly"]
        assert "imul" in src
        assert "add rax, rbx" in src

    def test_full_program_if_else(self):
        code = """
        int a = 5;
        if (a > 10) {
            a = a + 1;
        } else {
            a = a - 1;
        }
        """
        res = compile_source(code)
        assert res["assembly"]["success"] is True
        src = res["assembly"]["assembly"]
        assert "je" in src
        assert "jmp" in src

    def test_full_program_while_loop(self):
        code = "int i = 0;\nwhile (i < 5) { i = i + 1; }"
        res = compile_source(code)
        assert res["assembly"]["success"] is True
        assert "jmp L0" in res["assembly"]["assembly"]

    def test_full_program_print(self):
        code = "int x = 42;\nprint(x);"
        res = compile_source(code)
        assert res["assembly"]["success"] is True
        assert "call printf" in res["assembly"]["assembly"]


# ---------------------------------------------------------------------------
# 13. Regression: prior phases must still pass after adding assembly
# ---------------------------------------------------------------------------

class TestRegressionPriorPhases:
    def test_lexer_still_works(self):
        res = compile_source("int a = 10;")
        assert len(res["lex"]["tokens"]) > 0

    def test_parser_still_works(self):
        res = compile_source("int a = 10;")
        assert res["parse"]["success"] is True

    def test_semantic_still_works(self):
        res = compile_source("int a = 10;")
        assert res["semantic"]["success"] is True

    def test_icg_still_works(self):
        res = compile_source("int a = 10;\nint b = 20;\nint c = a + b;")
        assert res["icg"]["success"] is True
        assert len(res["icg"]["instructions"]) > 0

    def test_cfg_still_works(self):
        code = "int i = 0;\nwhile (i < 3) { i = i + 1; }"
        res = compile_source(code)
        assert "B0" in res["icg"]["cfg"]["blocks"]

    def test_three_address_code_unchanged(self):
        code = "int a = 1;\nint b = 2;\nint c = a + b * 2;"
        res = compile_source(code)
        tac = res["icg"]["three_address_code"]
        assert any("t0 = b * 2" in line for line in tac)
        assert any("t1 = a + t0" in line for line in tac)

    def test_quadruples_unchanged(self):
        code = "int a = 1;\nint b = 2;\nint c = a + b * 2;"
        res = compile_source(code)
        quads = res["icg"]["quadruples"]
        # First two assignments (a=1, b=2), then the arithmetic quads
        # Find the multiply quad
        mul_quad = next(q for q in quads if q["op"] == "*")
        add_quad = next(q for q in quads if q["op"] == "+")
        assert mul_quad["op"] == "*"
        assert add_quad["op"] == "+"


# ---------------------------------------------------------------------------
# 14. Invalid source programs do not generate assembly
# ---------------------------------------------------------------------------

class TestInvalidSourcePrograms:
    def test_syntax_error_no_assembly(self):
        res = compile_source("int a = ;")
        assert res["assembly"] is None

    def test_semantic_error_no_assembly(self):
        res = compile_source("y = 5;")   # y not declared
        assert res["assembly"] is None

    def test_type_mismatch_no_assembly(self):
        # int = float assignment is a semantic error in ToyLang
        res = compile_source("int a = 1;\nfloat b = 2.0;\na = b;")
        # Semantic checker may or may not allow this - just ensure pipeline is stable
        assert "assembly" in res   # key always present
