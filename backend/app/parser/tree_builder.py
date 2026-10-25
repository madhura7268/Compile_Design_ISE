"""
tree_builder.py - Parse Tree / AST Node Builder for ToyLang.
"""


class Node:
    """
    Simple recursive tree node.

    Each node contains:
        name     -> text displayed in the tree
        children -> child Node objects
    """

    def __init__(self, name, children=None, line=None, column=None):
        self.name = name
        self.children = children if children is not None else []
        self.line = line
        self.column = column

    def add_child(self, child):
        """Add one child node."""
        if child is not None:
            self.children.append(child)

    def to_d3_json(self):
        """
        Convert this node into the JSON structure expected
        by react-d3-tree.
        """

        result = {
            "name": self.name
        }

        if self.children:
            result["children"] = [
                child.to_d3_json()
                for child in self.children
            ]

        return result


def identifier_node(name, line=None, column=None):
    """Create an identifier node."""
    return Node(f"Identifier: {name}", line=line, column=column)


def literal_node(value, line=None, column=None):
    """Create a literal node."""
    return Node(f"Literal: {value}", line=line, column=column)


def operator_node(operator, left, right, line=None, column=None):
    """Create a binary operator node."""
    return Node(
        f"Operator: {operator}",
        [left, right],
        line=line,
        column=column,
    )


def unary_operator_node(operator, operand, line=None, column=None):
    """Create a unary operator node."""
    return Node(
        f"Unary: {operator}",
        [operand],
        line=line,
        column=column,
    )