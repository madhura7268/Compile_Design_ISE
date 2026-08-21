"""
test_symbol_table.py - Pytest test cases for SymbolTable.
"""

from backend.app.lexer.symbol_table import SymbolTable


def test_symbol_table_global_scope():
    st = SymbolTable()
    assert st.current_scope() == "global"

    st.add("count", "int", line=1)
    st.add("price", "float", line=2)

    symbols = st.get_all()
    assert len(symbols) == 2
    assert symbols[0] == {"name": "count", "type": "int", "scope": "global", "line": 1}
    assert symbols[1] == {"name": "price", "type": "float", "scope": "global", "line": 2}


def test_symbol_table_lookup():
    st = SymbolTable()
    st.add("x", "int", line=1)

    result = st.lookup("x")
    assert result is not None
    assert result["name"] == "x"
    assert result["type"] == "int"

    assert st.lookup("unknown") is None


def test_symbol_table_nested_scopes():
    st = SymbolTable()
    st.add("g", "int", line=1)

    # Enter block scope 1
    new_scope = st.enter_scope()
    assert new_scope == "block_1"
    assert st.current_scope() == "block_1"

    st.add("local1", "float", line=3)
    assert st.lookup("local1")["scope"] == "block_1"
    # Scope resolution: outer global variable is also accessible from block_1
    assert st.lookup("g")["scope"] == "global"

    # Exit block scope 1 back to global
    exited = st.exit_scope()
    assert exited == "block_1"
    assert st.current_scope() == "global"

    # Now local1 is no longer in current scope hierarchy lookup
    assert st.lookup("local1") is None
