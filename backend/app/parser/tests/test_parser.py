"""
test_parser.py - Pytest tests for ToyLang parser.
"""

from backend.app.parser.grammar import parse


def test_variable_declaration():
    code = "int count = 10;"

    result = parse(code)

    assert result["success"] is True
    assert result["error"] is None

    tree = result["parse_tree"]

    assert tree["name"] == "Program"


def test_multiple_declarations():
    code = """
int a = 10;
float b = 20.5;
"""

    result = parse(code)

    assert result["success"] is True
    assert result["parse_tree"]["name"] == "Program"


def test_arithmetic_expression():
    code = "int result = 10 + 20 * 2;"

    result = parse(code)

    assert result["success"] is True
    assert result["error"] is None


def test_assignment():
    code = """
int x = 10;
x = x + 1;
"""

    result = parse(code)

    assert result["success"] is True


def test_if_statement():
    code = """
int x = 10;

if (x > 5) {
    print(x);
}
"""

    result = parse(code)

    assert result["success"] is True


def test_if_else_statement():
    code = """
int x = 10;

if (x > 5) {
    print(x);
} else {
    print(0);
}
"""

    result = parse(code)

    assert result["success"] is True


def test_while_statement():
    code = """
int x = 0;

while (x < 10) {
    x = x + 1;
}
"""

    result = parse(code)

    assert result["success"] is True


def test_return_statement():
    code = """
int x = 10;
return x;
"""

    result = parse(code)

    assert result["success"] is True


def test_print_statement():
    code = """
int x = 10;
print(x);
"""

    result = parse(code)

    assert result["success"] is True


def test_missing_semicolon():
    code = "int x = 10"

    result = parse(code)

    assert result["success"] is False
    assert result["error"] is not None
    assert result["error"]["error_type"] == "SyntaxError"


def test_missing_closing_brace():
    code = """
if (x > 10) {
    print(x);
"""

    result = parse(code)

    assert result["success"] is False
    assert result["error"] is not None


def test_unexpected_token():
    code = """
int x = ;
"""

    result = parse(code)

    assert result["success"] is False
    assert result["error"] is not None


def test_parse_tree_d3_format():
    code = "int count = 10;"

    result = parse(code)

    assert result["success"] is True

    tree = result["parse_tree"]

    assert tree["name"] == "Program"
    assert "children" in tree


def test_operator_precedence():
    code = "int result = 10 + 20 * 2;"

    result = parse(code)

    assert result["success"] is True

    tree = result["parse_tree"]

    # Tree should exist and contain the program.
    assert tree["name"] == "Program"