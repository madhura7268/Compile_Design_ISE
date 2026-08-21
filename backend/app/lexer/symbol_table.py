"""
symbol_table.py - Simple Symbol Table for ToyLang.
Tracks identifier declarations, types, lines, and block scopes.
"""


class SymbolTable:
    def __init__(self):
        self.scope_stack = ["global"]
        self.block_counter = 0
        self.symbols = []

    def enter_scope(self):
        """Enter a new block scope upon '{'."""
        self.block_counter += 1
        scope_name = f"block_{self.block_counter}"
        self.scope_stack.append(scope_name)
        return scope_name

    def exit_scope(self):
        """Exit current scope upon '}'."""
        if len(self.scope_stack) > 1:
            return self.scope_stack.pop()
        return None

    def current_scope(self):
        """Return name of current active scope."""
        return self.scope_stack[-1]

    def add(self, name, datatype, line):
        """Add a variable declaration to the symbol table."""
        symbol = {
            "name": name,
            "type": datatype,
            "scope": self.current_scope(),
            "line": line,
        }
        self.symbols.append(symbol)
        return symbol

    def lookup(self, name):
        """Look up symbol in active scopes from current to global."""
        for scope in reversed(self.scope_stack):
            for symbol in reversed(self.symbols):
                if symbol["name"] == name and symbol["scope"] == scope:
                    return symbol
        return None

    def get_all(self):
        """Return all recorded symbols."""
        return self.symbols

    def clear(self):
        """Reset symbol table."""
        self.scope_stack = ["global"]
        self.block_counter = 0
        self.symbols = []
