import os
import re
import json
from dotenv import load_dotenv
from groq import Groq

def get_client():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_env_paths = [
        os.path.join(base_dir, ".env"),
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.getcwd(), "backend", ".env"),
    ]
    for p in possible_env_paths:
        if os.path.isfile(p):
            load_dotenv(dotenv_path=p, override=True)
            break
    else:
        load_dotenv(override=True)

    api_key = os.getenv("GROQ_API_KEY")
    if api_key and api_key.strip() and api_key.strip() != "your_groq_api_key_here":
        return Groq(api_key=api_key.strip())
    return None

def heuristic_fix(code: str, error_msg: str, line: int) -> str:
    lines = code.splitlines()
    target_idx = (line - 1) if (line and isinstance(line, int) and 0 <= line - 1 < len(lines)) else len(lines) - 1
    corrected_lines = list(lines)
    
    # 1. Missing initializer expression (e.g., 'int b = ;' -> 'int b = 0;')
    if 0 <= target_idx < len(corrected_lines) and re.search(r'=\s*;', corrected_lines[target_idx]):
        corrected_lines[target_idx] = re.sub(r'=\s*;', '= 0;', corrected_lines[target_idx])
        return "\n".join(corrected_lines)

    # 2. Duplicate or extra semicolons (e.g., ';;' -> ';')
    if 0 <= target_idx < len(corrected_lines) and re.search(r';;+', corrected_lines[target_idx]):
        cleaned = re.sub(r';;+', ';', corrected_lines[target_idx])
        # If line was solely ';;', removing the duplicate leaves just ';' or empty
        corrected_lines[target_idx] = cleaned
        return "\n".join(corrected_lines)

    # 3. Target line missing semicolon
    if 0 <= target_idx < len(corrected_lines):
        curr = corrected_lines[target_idx].rstrip()
        if curr and not curr.endswith(";") and not curr.endswith("{") and not curr.endswith("}"):
            corrected_lines[target_idx] = curr + ";"
            return "\n".join(corrected_lines)
            
    # 4. Check previous line if target line error was caused by previous line
    if target_idx - 1 >= 0 and target_idx - 1 < len(corrected_lines):
        prev = corrected_lines[target_idx - 1].rstrip()
        if prev and not prev.endswith(";") and not prev.endswith("{") and not prev.endswith("}"):
            corrected_lines[target_idx - 1] = prev + ";"
            return "\n".join(corrected_lines)

    # 5. Check for unclosed brace
    if "end of input" in error_msg.lower():
        corrected_lines.append("}")
        return "\n".join(corrected_lines)

    # 6. Check any line missing semicolon
    for idx, l_text in enumerate(corrected_lines):
        s_text = l_text.rstrip()
        if s_text and not s_text.endswith(";") and not s_text.endswith("{") and not s_text.endswith("}"):
            corrected_lines[idx] = s_text + ";"
            return "\n".join(corrected_lines)

    return code

def get_ai_diagnostic(code: str, error_msg: str, line: int = 1, phase: str = "syntax", **kwargs) -> dict:
    """
    Sends the broken code, parser/semantic error, and RAG-retrieved ToyLang specifications
    to the LLM (or uses heuristic fallback).
    Returns a structured dictionary containing explanation, suggested fix, corrected code,
    and retrieved formal rules.
    """
    # Retrieve relevant ToyLang rules via RAG
    retrieved_rules = []
    retrieved_rules_str = ""
    try:
        from rag_engine import get_rag_engine
        rag = get_rag_engine()
        query = f"{phase} error: {error_msg} around line {line}"
        retrieved_rules = rag.retrieve(query, top_k=2)
        retrieved_rules_str = rag.format_retrieved_context(retrieved_rules)
    except Exception:
        pass

    client = get_client()
    
    if not client:
        corrected_code = heuristic_fix(code, error_msg, line)
        fix_desc = "Add missing semicolon or brace around line"
        if re.search(r'=\s*;', code):
            fix_desc = "Provide an expression or value before the semicolon on line"
        return {
            "explanation": f"Compiler {phase} error detected near line {line}: {error_msg} (Offline mode - GROQ_API_KEY missing or invalid in .env)",
            "suggested_fix": f"{fix_desc} {line if line else 1}.",
            "corrected_code": corrected_code,
            "retrieved_rules": retrieved_rules
        }

    system_prompt = f"""
    You are an expert compiler diagnostics assistant for an educational C-like Toy language called 'ToyLang'.
    Analyze the {phase} error produced by the compiler.

    === RELEVANT TOYLANG SPECIFICATIONS RETRIEVED VIA RAG ===
    {retrieved_rules_str if retrieved_rules_str else "General ToyLang syntax rules apply."}

    Diagnostic Instructions:
    1. Ground your explanation in the retrieved ToyLang rules and cite the rule/section name where helpful.
    2. Provide the exact modification required.
    3. Output the complete corrected source code.
    
    You must output ONLY valid JSON matching this exact structure (no markdown fences, no extra text):
    {{
      "explanation": "A concise 1-2 sentence explanation of why the compiler failed, citing ToyLang grammar/semantic rules.",
      "suggested_fix": "The exact modification required (e.g., 'Initialize variable b with a value on line 2').",
      "corrected_code": "The full source code with the error fixed."
    }}
    """

    user_content = f"""
    Source Code:
    {code}

    Compiler {phase.capitalize()} Error Details:
    - Message: {error_msg}
    - Location: Around Line {line}
    """

    # Candidate models to try in order
    candidate_models = [
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ]

    try:
        remote_models = [m.id for m in client.models.list().data]
        # Prioritize candidate models that exist on the server
        active_candidates = [m for m in candidate_models if m in remote_models]
        if active_candidates:
            candidate_models = active_candidates + [m for m in candidate_models if m not in active_candidates]
        elif remote_models:
            chat_candidates = [m for m in remote_models if "whisper" not in m and "guard" not in m]
            if chat_candidates:
                candidate_models = chat_candidates + candidate_models
    except Exception:
        pass

    last_error = None
    for model_name in candidate_models:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            raw_content = response.choices[0].message.content
            res_json = json.loads(raw_content)
            if "corrected_code" not in res_json or not res_json["corrected_code"]:
                res_json["corrected_code"] = heuristic_fix(code, error_msg, line)
            res_json["retrieved_rules"] = retrieved_rules
            return res_json
        except Exception as e:
            last_error = e
            continue

    # If all models failed, fall back to heuristic
    corrected_code = heuristic_fix(code, error_msg, line)
    return {
        "explanation": f"Compiler {phase} error detected near line {line}: {error_msg} (API error: {str(last_error)})",
        "suggested_fix": f"Add missing semicolon, value, or brace around line {line if line else 1}.",
        "corrected_code": corrected_code,
        "retrieved_rules": retrieved_rules
    }