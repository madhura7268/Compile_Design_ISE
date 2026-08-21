"""
Package initializer for backend.app.lexer.
Exposes key module entry points: tokenize function and SymbolTable class.
"""

from .lexer import tokenize
from .symbol_table import SymbolTable
from .fuzzy_match import suggest_keyword

__all__ = ["tokenize", "SymbolTable", "suggest_keyword"]
