"""
Parser package for ToyLang.

Provides parsing and parse-tree generation functionality.
"""

from .grammar import parse, parse_with_ast

__all__ = ["parse", "parse_with_ast"]