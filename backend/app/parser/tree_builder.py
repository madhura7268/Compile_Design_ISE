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

    def __init__(self, name, children=None):
        self.name = name
        self.children = children if children is not None else []

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


def identifier_node(name):
    """Create an identifier node."""
    return Node(f"Identifier: {name}")


def literal_node(value):
    """Create a literal node."""
    return Node(f"Literal: {value}")


def operator_node(operator, left, right):
    """Create a binary operator node."""
    return Node(
        f"Operator: {operator}",
        [left, right]
    )


def unary_operator_node(operator, operand):
    """Create a unary operator node."""
    return Node(
        f"Unary: {operator}",
        [operand]
    )