"""
test_rag.py - Unit tests for ToyLang RAG Engine and Augmented Diagnostics.
"""

import sys
import os

# Ensure backend folder is in path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from rag_engine import ToyLangRAGEngine, get_rag_engine
from ai_diagnostic import get_ai_diagnostic


def test_rag_knowledge_base_loading():
    engine = ToyLangRAGEngine()
    assert len(engine.chunks) > 0, "RAG engine should load knowledge chunks from backend/knowledge"


def test_rag_syntax_error_retrieval():
    engine = get_rag_engine()
    results = engine.retrieve("Unexpected token semicolon in variable declaration", top_k=3)
    assert len(results) > 0
    # Should retrieve grammar or error catalog
    doc_names = [r["document"] for r in results]
    assert any("grammar" in d or "error" in d for d in doc_names)


def test_rag_semantic_error_retrieval():
    engine = get_rag_engine()
    results = engine.retrieve("Undeclared variable used in assignment", top_k=3)
    assert len(results) > 0
    doc_names = [r["document"] for r in results]
    assert any("semantic" in d or "error" in d for d in doc_names)


def test_rag_codegen_retrieval():
    engine = get_rag_engine()
    results = engine.retrieve("x86-64 NASM division idiv cqo", top_k=3)
    assert len(results) > 0
    doc_names = [r["document"] for r in results]
    assert any("codegen" in d or "ir" in d for d in doc_names)


def test_get_ai_diagnostic_with_rag():
    code = "int a = 10;\nint b = ;\n"
    res = get_ai_diagnostic(code, "Unexpected token ';' of type SEMI.", line=2, phase="syntax")
    assert "explanation" in res
    assert "suggested_fix" in res
    assert "corrected_code" in res
    assert "retrieved_rules" in res
    assert len(res["retrieved_rules"]) > 0
