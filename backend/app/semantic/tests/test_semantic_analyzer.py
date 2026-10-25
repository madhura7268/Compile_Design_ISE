import pytest

from backend.app.parser.grammar import parse, parse_with_ast
from backend.app.semantic.pipeline import compile_source
from backend.app.semantic.semantic_analyzer import SemanticAnalyzer, analyze


def analyze_source(source):
    parse_result, tree = parse_with_ast(source)
    assert parse_result["success"] is True
    return analyze(tree)


def error_codes(result):
    return [error["code"] for error in result["errors"]]


def test_valid_declaration_and_use():
    result = analyze_source("int count = 1;\ncount = count + 2;\nprint(count);")

    assert result["success"] is True
    assert result["errors"] == []
    assert result["symbol_table"] == [
        {"name": "count", "type": "int", "scope": "global", "line": 1}
    ]


@pytest.mark.parametrize(
    "source, expected_line",
    [
        ("print(missing);", 1),
        ("int value = missing;", 1),
        ("if (missing == 1) { }", 1),
        ("return missing;", 1),
    ],
)
def test_undeclared_variable_references(source, expected_line):
    result = analyze_source(source)

    assert result["success"] is False
    assert "UNDECLARED_VARIABLE" in error_codes(result)
    assert result["errors"][0]["line"] == expected_line
    assert result["errors"][0]["variable_name"] == "missing"


def test_assignment_to_undeclared_variable():
    result = analyze_source("value = 1;")

    assert error_codes(result) == ["UNDECLARED_VARIABLE"]
    assert result["errors"][0]["variable_name"] == "value"


def test_duplicate_declaration_in_same_scope():
    result = analyze_source("int value = 1;\nfloat value = 2.0;")

    assert error_codes(result) == ["DUPLICATE_DECLARATION"]
    assert result["symbol_table"] == [
        {"name": "value", "type": "int", "scope": "global", "line": 1}
    ]


def test_outer_variable_is_visible_in_nested_scope():
    result = analyze_source(
        "int outer = 1;\n"
        "{\n"
        "  outer = outer + 1;\n"
        "  print(outer);\n"
        "}\n"
    )

    assert result["success"] is True


def test_nested_scope_can_shadow_outer_variable():
    result = analyze_source(
        "int value = 1;\n"
        "{\n"
        "  float value = 2.0;\n"
        "  print(value);\n"
        "}\n"
        "print(value);\n"
    )

    assert result["success"] is True
    assert [symbol["scope"] for symbol in result["symbol_table"]] == [
        "global",
        "block_1",
    ]


def test_inner_variable_is_not_visible_after_scope_exit():
    result = analyze_source("{ int local = 1; }\nprint(local);")

    assert error_codes(result) == ["UNDECLARED_VARIABLE"]
    assert result["errors"][0]["line"] == 2


@pytest.mark.parametrize(
    "source",
    [
        "int value = 1; value = 2;",
        "float value = 1.5; value = value + 2.5;",
        "int left = 1; int right = 2; int total = left + right * 2;",
        "float value = 2.5; value = value / 0.5;",
        "int value = 5 % 2;",
    ],
)
def test_compatible_numeric_types_and_arithmetic(source):
    assert analyze_source(source)["success"] is True


def test_incompatible_initializer_type():
    result = analyze_source('int value = "text";')

    assert error_codes(result) == ["INCOMPATIBLE_INITIALIZER"]


def test_incompatible_assignment_type():
    result = analyze_source("int value = 1; value = 2.5;")

    assert error_codes(result) == ["INCOMPATIBLE_ASSIGNMENT"]


@pytest.mark.parametrize(
    "source",
    [
        'int value = 1 + "text";',
        "int value = 4.0 % 2;",
        'int value = -"text";',
    ],
)
def test_invalid_arithmetic_types(source):
    result = analyze_source(source)

    assert result["success"] is False
    assert any(
        code in error_codes(result)
        for code in ("INVALID_ARITHMETIC_OPERANDS", "INVALID_UNARY_OPERAND")
    )


def test_conditions_require_boolean_values():
    valid = analyze_source(
        "int value = 1;\n"
        "bool ready = value < 2;\n"
        "if (ready) { print(value); } else { return; }\n"
        "while (value < 2) { value = value + 1; }\n"
    )
    invalid = analyze_source("if (1) { }")

    assert valid["success"] is True
    assert error_codes(invalid) == ["INVALID_CONDITION_TYPE"]


def test_invalid_comparison_types():
    result = analyze_source('bool result = "a" < "b";')

    assert error_codes(result) == ["INCOMPATIBLE_COMPARISON"]


def test_multiple_semantic_errors_are_returned():
    result = analyze_source("missing = 1;\nint value = 1.5;\nprint(other);")

    assert error_codes(result) == [
        "UNDECLARED_VARIABLE",
        "INCOMPATIBLE_INITIALIZER",
        "UNDECLARED_VARIABLE",
    ]


def test_empty_program_and_no_error_program():
    empty = analyze_source("")
    valid = analyze_source("print(1); return;")

    assert empty["success"] is True
    assert valid["success"] is True


def test_source_locations_are_available_without_changing_d3_json():
    source = "int value = 1;\nprint(missing);"
    parse_result, tree = parse_with_ast(source)
    result = analyze(tree)

    assert parse_result["parse_tree"] == parse(source)["parse_tree"]
    assert result["errors"][0]["line"] == 2
    assert result["errors"][0]["column"] == 7
    assert "line" not in parse_result["parse_tree"]


def test_analyzer_reuse_does_not_leak_symbols_or_errors():
    parser_result, first_tree = parse_with_ast("int value = 1;")
    second_parser_result, second_tree = parse_with_ast("print(value);")
    analyzer = SemanticAnalyzer()

    assert parser_result["success"] is True
    first = analyzer.analyze(first_tree)
    second = analyzer.analyze(second_tree)

    assert first["success"] is True
    assert error_codes(second) == ["UNDECLARED_VARIABLE"]
    assert second["symbol_table"] == []


@pytest.mark.parametrize(
    "source, error_type",
    [
        ("int value = @;", "LexicalError"),
        ("int value = ;", "SyntaxError"),
    ],
)
def test_lexical_and_syntax_failures_remain_parser_errors(source, error_type):
    result, tree = parse_with_ast(source)

    assert result["success"] is False
    assert result["error"]["error_type"] == error_type
    assert tree is None


def test_parser_remains_syntax_only_for_undeclared_names():
    result = parse("print(missing);")

    assert result["success"] is True


@pytest.mark.parametrize(
    "source, expected_error",
    [
        ("int value = @;", "LexicalError"),
        ("int value = ;", "SyntaxError"),
    ],
)
def test_pipeline_stops_before_semantics_for_lexical_or_syntax_errors(
    source, expected_error
):
    result = compile_source(source)

    assert result["parse"]["success"] is False
    assert result["parse"]["error"]["error_type"] == expected_error
    assert result["semantic"] is None


def test_pipeline_returns_semantic_diagnostics_without_changing_parse_result():
    result = compile_source("print(missing);")

    assert result["parse"]["success"] is True
    assert result["parse"]["parse_tree"]["name"] == "Program"
    assert result["semantic"]["success"] is False
    assert error_codes(result["semantic"]) == ["UNDECLARED_VARIABLE"]


def test_pipeline_reports_success_after_all_phases():
    result = compile_source("int value = 1; print(value);")

    assert result["parse"]["success"] is True
    assert result["semantic"]["success"] is True
    assert result["semantic"]["errors"] == []
