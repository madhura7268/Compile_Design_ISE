"""
rag_engine.py - Retrieval-Augmented Generation (RAG) engine for ToyLang Compiler.

Provides:
1. Pure Python Inverted Index & BM25-style document retrieval over ToyLang compiler specs.
2. Context augmentation for error diagnostics (Phase 1-5).
3. "Ask the Compiler" AI Tutor that answers theoretical and implementation questions grounded
   in the retrieved language specifications and live compilation state.
"""

import os
import re
import math
import json
from collections import Counter
from typing import List, Dict, Any, Optional

try:
    from ai_diagnostic import get_client
except ImportError:
    from .ai_diagnostic import get_client


class KnowledgeChunk:
    def __init__(self, chunk_id: str, doc_name: str, title: str, content: str):
        self.chunk_id = chunk_id
        self.doc_name = doc_name
        self.title = title
        self.content = content.strip()
        self.tokens = self._tokenize(f"{title} {self.content}")
        self.token_counts = Counter(self.tokens)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        # Normalize code tokens and text words
        clean = re.sub(r'[`*_{}\[\]()#=;:,+\-/%]', ' ', text.lower())
        words = re.findall(r'[a-z0-9_]{2,}', clean)
        # Keep important compiler symbols as words
        if ';' in text:
            words.extend(["semi", "semicolon"])
        if '=' in text:
            words.extend(["assign", "assignment", "initializer"])
        if '{' in text or '}' in text:
            words.extend(["brace", "block", "scope"])
        if '(' in text or ')' in text:
            words.extend(["paren", "parenthesis"])
        return words


class ToyLangRAGEngine:
    def __init__(self, knowledge_dir: Optional[str] = None):
        if knowledge_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            knowledge_dir = os.path.join(base_dir, "knowledge")
        self.knowledge_dir = knowledge_dir
        self.chunks: List[KnowledgeChunk] = []
        self.doc_freqs: Dict[str, int] = Counter()
        self.avg_doc_len: float = 0.0
        self.load_knowledge_base()

    def load_knowledge_base(self):
        """Parse markdown documents in the knowledge directory into semantic chunks."""
        self.chunks = []
        if not os.path.isdir(self.knowledge_dir):
            return

        for filename in sorted(os.listdir(self.knowledge_dir)):
            if not filename.endswith(".md"):
                continue

            filepath = os.path.join(self.knowledge_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue

            # Split document by headers (## or ###)
            sections = re.split(r'\n(?=#{2,3}\s+)', text)
            for idx, sec in enumerate(sections):
                lines = sec.strip().splitlines()
                if not lines:
                    continue
                header_line = lines[0]
                title = re.sub(r'^#{2,3}\s+', '', header_line).strip()
                body = "\n".join(lines[1:]).strip() if len(lines) > 1 else header_line
                chunk_id = f"{filename}::{title or f'part_{idx}'}"
                chunk = KnowledgeChunk(chunk_id, filename, title, f"{header_line}\n{body}")
                self.chunks.append(chunk)

        # Compute document frequencies and average length for BM25
        self.doc_freqs = Counter()
        total_len = 0
        for chunk in self.chunks:
            unique_terms = set(chunk.tokens)
            for t in unique_terms:
                self.doc_freqs[t] += 1
            total_len += len(chunk.tokens)

        self.avg_doc_len = (total_len / len(self.chunks)) if self.chunks else 1.0

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        BM25-style keyword and semantic retrieval over ToyLang knowledge chunks.
        """
        if not self.chunks:
            return []

        query_tokens = KnowledgeChunk._tokenize(query)
        if not query_tokens:
            return []

        k1 = 1.5
        b = 0.75
        N = len(self.chunks)
        scores = []

        for chunk in self.chunks:
            doc_len = len(chunk.tokens)
            score = 0.0

            for q in query_tokens:
                tf = chunk.token_counts.get(q, 0)
                if tf == 0:
                    continue
                df = self.doc_freqs.get(q, 1)
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_len / self.avg_doc_len))
                score += idf * (numerator / denominator)

            # Boost exact title matches
            title_lower = chunk.title.lower()
            for q in query_tokens:
                if q in title_lower:
                    score += 1.5

            if score > 0:
                scores.append((score, chunk))

        scores.sort(key=lambda x: x[0], reverse=True)
        top_results = scores[:top_k]

        return [
            {
                "id": chunk.chunk_id,
                "title": chunk.title,
                "document": chunk.doc_name,
                "content": chunk.content,
                "score": round(score, 3)
            }
            for score, chunk in top_results
        ]

    def format_retrieved_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved knowledge chunks for LLM prompt augmentation."""
        if not chunks:
            return "No specific ToyLang rule matched."

        parts = []
        for i, c in enumerate(chunks, 1):
            parts.append(
                f"[Source Rule {i}: {c['title']} ({c['document']})]\n{c['content']}"
            )
        return "\n\n".join(parts)

    def ask_tutor(self, user_query: str, compiler_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Answers student questions about compiler design and the active ToyLang code,
        grounded in the retrieved language specifications and compiler state.
        """
        retrieved_chunks = self.retrieve(user_query, top_k=3)
        retrieved_context_str = self.format_retrieved_context(retrieved_chunks)

        # Build live compiler context summary
        code_str = ""
        ast_summary = "Not available"
        sym_summary = "Not available"
        icg_summary = "Not available"
        asm_summary = "Not available"

        if compiler_context:
            code_str = compiler_context.get("source_code", "")
            if "parse_tree" in compiler_context and compiler_context["parse_tree"]:
                ast_summary = "Parse tree successfully constructed."
            elif compiler_context.get("parse_error"):
                ast_summary = f"Parse Error: {compiler_context['parse_error']}"

            if "symbols" in compiler_context:
                sym_list = compiler_context["symbols"]
                sym_summary = f"{len(sym_list)} symbols recorded: {sym_list[:10]}"

            if "ir_code" in compiler_context and compiler_context["ir_code"]:
                ir_lines = compiler_context["ir_code"].splitlines()
                icg_summary = f"{len(ir_lines)} 3AC instructions:\n" + "\n".join(ir_lines[:15])

            if "asm_code" in compiler_context and compiler_context["asm_code"]:
                asm_lines = compiler_context["asm_code"].splitlines()
                asm_summary = f"{len(asm_lines)} NASM instructions:\n" + "\n".join(asm_lines[:20])

        system_prompt = f"""
You are an expert, encouraging Compiler Design Teaching Assistant for the educational language 'ToyLang'.
You explain compiler theory (Lexical Analysis, Syntax / LALR parsing, Semantic Analysis, Intermediate Code Generation, and x86-64 NASM Assembly).

IMPORTANT GROUNDING RULES:
1. Always ground your explanation in the official ToyLang specifications retrieved below.
2. Cite the relevant rule or section name (e.g., 'According to ToyLang Grammar Section 3: Variable Declarations...').
3. Keep answers clear, educational, and concise (2-4 paragraphs). Use markdown formatting and code snippets.
4. If referring to the student's current code or compiler output, quote it directly.

=== RETRIEVED TOYLANG SPECIFICATIONS (RAG) ===
{retrieved_context_str}
"""

        user_content = f"""
Student Question:
{user_query}

Current Compilation Session State:
- Source Code:
```c
{code_str}
```
- AST / Parser Status: {ast_summary}
- Symbol Table: {sym_summary}
- Intermediate Code (3AC):
```
{icg_summary}
```
- Generated x86-64 Assembly:
```nasm
{asm_summary}
```
"""

        client = get_client()
        if not client:
            return {
                "answer": (
                    f"**Offline Mode**: Unable to contact LLM (GROQ_API_KEY missing in .env).\n\n"
                    f"**Relevant ToyLang Rules Retrieved via RAG:**\n\n{retrieved_context_str}"
                ),
                "retrieved_chunks": retrieved_chunks,
                "model_used": "offline-rag"
            }

        candidate_models = [
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ]

        try:
            remote_models = [m.id for m in client.models.list().data]
            active = [m for m in candidate_models if m in remote_models]
            if active:
                candidate_models = active
        except Exception:
            pass

        last_error = None
        for model in candidate_models:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.2
                )
                answer_text = resp.choices[0].message.content
                return {
                    "answer": answer_text,
                    "retrieved_chunks": retrieved_chunks,
                    "model_used": model
                }
            except Exception as e:
                last_error = e
                continue

        return {
            "answer": (
                f"**API Connection Error**: All models failed to respond ({last_error}).\n\n"
                f"**Retrieved Rules for your question:**\n\n{retrieved_context_str}"
            ),
            "retrieved_chunks": retrieved_chunks,
            "model_used": "fallback-rag"
        }


# Global singleton engine
_global_rag_engine: Optional[ToyLangRAGEngine] = None

def get_rag_engine() -> ToyLangRAGEngine:
    global _global_rag_engine
    if _global_rag_engine is None:
        _global_rag_engine = ToyLangRAGEngine()
    return _global_rag_engine
