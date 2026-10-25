"""Name and type checking for the ToyLang parse tree.

Assignments require exact types; mixed int/float arithmetic produces float.
Remainder requires integers, relational comparisons require numeric operands,
and equality accepts matching types or mixed numeric operands. Conditions must
be bool. The grammar has no boolean literals or function return types.
"""

import re

from ..lexer.symbol_table import SymbolTable
from ..parser.tree_builder import Node


_UNKNOWN = None
_NUMERIC_TYPES = {"int", "float"}
_ARITHMETIC_OPERATORS = {"+", "-", "*", "/", "%"}
_RELATIONAL_OPERATORS = {"<", "<=", ">", ">="}
_EQUALITY_OPERATORS = {"==", "!="}


class SemanticAnalyzer:
    """Analyze a parser Node tree with an isolated scoped symbol table."""

    def __init__(self):
        self._reset()

    def _reset(self):
        self.symbol_table = SymbolTable()
        self.errors = []

    def analyze(self, tree):
        if not isinstance(tree, Node):
            raise TypeError("Semantic analysis requires a parser Node tree.")

        self._reset()
        self._visit_statement(tree)
        symbols = [dict(symbol) for symbol in self.symbol_table.get_all()]
        return {
            "success": not self.errors,
            "errors": list(self.errors),
            "error": self.errors[0] if self.errors else None,
            "symbol_table": symbols,
        }

    def _add_error(self, node, code, message, variable_name=None):
        error = {
            "error_type": "SemanticError",
            "code": code,
            "message": message,
        }
        if node.line is not None:
            error["line"] = node.line
        if node.column is not None:
            error["column"] = node.column
        if variable_name is not None:
            error["variable_name"] = variable_name
        self.errors.append(error)

    def _visit_statement(self, node):
        name = node.name

        if name in {"Program", "StatementList"}:
            for child in node.children:
                self._visit_statement(child)
        elif name.startswith("VarDeclaration ("):
            self._visit_declaration(node)
        elif name == "Assignment":
            self._visit_assignment(node)
        elif name == "Block":
            self.symbol_table.enter_scope()
            try:
                for child in node.children:
                    self._visit_statement(child)
            finally:
                self.symbol_table.exit_scope()
        elif name == "IfStatement":
            self._visit_if(node)
        elif name == "WhileStatement":
            self._visit_while(node)
        elif name == "Condition":
            self._check_condition(node)
        elif name in {"Then", "Else"}:
            for child in node.children:
                self._visit_statement(child)
        elif name == "PrintStatement":
            for child in node.children:
                self._infer_expression(child)
        elif name == "ReturnStatement":
            for child in node.children:
                self._infer_expression(child)
        elif name == "ExpressionStatement":
            for child in node.children:
                self._infer_expression(child)

    def _visit_declaration(self, node):
        datatype = node.name[len("VarDeclaration ("):-1]
        identifier = node.children[0]
        variable_name = identifier.name[len("Identifier: "):]
        current_scope = self.symbol_table.current_scope()
        duplicate = any(
            symbol["name"] == variable_name and symbol["scope"] == current_scope
            for symbol in self.symbol_table.get_all()
        )

        if duplicate:
            self._add_error(
                identifier,
                "DUPLICATE_DECLARATION",
                f"Variable '{variable_name}' is already declared in this scope.",
                variable_name,
            )
        else:
            self.symbol_table.add(variable_name, datatype, identifier.line)

        if len(node.children) > 1:
            expression_type = self._infer_expression(node.children[1])
            if expression_type is not _UNKNOWN and expression_type != datatype:
                self._add_error(
                    node.children[1],
                    "INCOMPATIBLE_INITIALIZER",
                    f"Cannot initialize '{variable_name}' of type {datatype} "
                    f"with an expression of type {expression_type}.",
                    variable_name,
                )

    def _visit_assignment(self, node):
        identifier, expression = node.children
        variable_name = identifier.name[len("Identifier: "):]
        symbol = self.symbol_table.lookup(variable_name)
        expression_type = self._infer_expression(expression)

        if symbol is None:
            self._add_error(
                identifier,
                "UNDECLARED_VARIABLE",
                f"Variable '{variable_name}' is not declared in this scope.",
                variable_name,
            )
        elif expression_type is not _UNKNOWN and expression_type != symbol["type"]:
            self._add_error(
                expression,
                "INCOMPATIBLE_ASSIGNMENT",
                f"Cannot assign an expression of type {expression_type} to "
                f"variable '{variable_name}' of type {symbol['type']}.",
                variable_name,
            )

    def _visit_if(self, node):
        for child in node.children:
            if child.name == "Condition":
                self._check_condition(child)
            else:
                self._visit_statement(child)

    def _visit_while(self, node):
        for child in node.children:
            if child.name == "Condition":
                self._check_condition(child)
            else:
                self._visit_statement(child)

    def _check_condition(self, node):
        if not node.children:
            return
        expression = node.children[0]
        expression_type = self._infer_expression(expression)
        if expression_type is not _UNKNOWN and expression_type != "bool":
            self._add_error(
                expression,
                "INVALID_CONDITION_TYPE",
                f"Condition must have type bool, not {expression_type}.",
            )

    def _infer_expression(self, node):
        name = node.name

        if name.startswith("Identifier: "):
            variable_name = name[len("Identifier: "):]
            symbol = self.symbol_table.lookup(variable_name)
            if symbol is None:
                self._add_error(
                    node,
                    "UNDECLARED_VARIABLE",
                    f"Variable '{variable_name}' is not declared in this scope.",
                    variable_name,
                )
                return _UNKNOWN
            return symbol["type"]

        if name.startswith("Literal: "):
            value = name[len("Literal: "):]
            if value.startswith('"') and value.endswith('"'):
                return "string"
            if re.fullmatch(r"\d+", value):
                return "int"
            if re.fullmatch(r"\d+\.\d+", value):
                return "float"
            return _UNKNOWN

        if name.startswith("Unary: "):
            operand_type = self._infer_expression(node.children[0])
            if operand_type is _UNKNOWN:
                return _UNKNOWN
            if operand_type not in _NUMERIC_TYPES:
                self._add_error(
                    node,
                    "INVALID_UNARY_OPERAND",
                    f"Unary '-' requires a numeric operand, not {operand_type}.",
                )
                return _UNKNOWN
            return operand_type

        if name.startswith("Operator: "):
            return self._infer_binary_expression(node)

        return _UNKNOWN

    def _infer_binary_expression(self, node):
        operator = node.name[len("Operator: "):]
        left_type = self._infer_expression(node.children[0])
        right_type = self._infer_expression(node.children[1])

        if left_type is _UNKNOWN or right_type is _UNKNOWN:
            return _UNKNOWN

        if operator in _ARITHMETIC_OPERATORS:
            valid_operands = (
                left_type in _NUMERIC_TYPES
                and right_type in _NUMERIC_TYPES
                and (operator != "%" or (left_type == right_type == "int"))
            )
            if not valid_operands:
                requirement = (
                    "integer operands" if operator == "%"
                    else "numeric operands"
                )
                self._add_error(
                    node,
                    "INVALID_ARITHMETIC_OPERANDS",
                    f"Operator '{operator}' requires {requirement}; "
                    f"received {left_type} and {right_type}.",
                )
                return _UNKNOWN
            return "float" if "float" in {left_type, right_type} else "int"

        if operator in _RELATIONAL_OPERATORS:
            if left_type not in _NUMERIC_TYPES or right_type not in _NUMERIC_TYPES:
                self._add_error(
                    node,
                    "INCOMPATIBLE_COMPARISON",
                    f"Operator '{operator}' requires numeric operands; "
                    f"received {left_type} and {right_type}.",
                )
                return _UNKNOWN
            return "bool"

        if operator in _EQUALITY_OPERATORS:
            compatible = (
                left_type == right_type
                or (left_type in _NUMERIC_TYPES and right_type in _NUMERIC_TYPES)
            )
            if not compatible:
                self._add_error(
                    node,
                    "INCOMPATIBLE_COMPARISON",
                    f"Operator '{operator}' cannot compare {left_type} and "
                    f"{right_type}.",
                )
                return _UNKNOWN
            return "bool"

        return _UNKNOWN


def analyze(tree):
    """Run one semantic-analysis pass and return its diagnostics and symbols."""
    return SemanticAnalyzer().analyze(tree)
