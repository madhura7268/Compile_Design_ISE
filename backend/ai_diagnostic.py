import os
import json
from dotenv import load_dotenv
from groq import Groq

def get_client():
    load_dotenv(override=True)
    api_key = os.getenv("GROQ_API_KEY")
    if api_key and api_key.strip() and api_key.strip() != "your_groq_api_key_here":
        return Groq(api_key=api_key.strip())
    return None

def heuristic_fix(code: str, error_msg: str, line: int) -> str:
    lines = code.splitlines()
    target_idx = (line - 1) if (line and isinstance(line, int) and 0 <= line - 1 < len(lines)) else len(lines) - 1
    
    corrected_lines = list(lines)
    
    # Check target line
    if 0 <= target_idx < len(corrected_lines):
        curr = corrected_lines[target_idx].rstrip()
        if not curr.endswith(";") and not curr.endswith("}"):
            corrected_lines[target_idx] = curr + ";"
            return "\n".join(corrected_lines)
            
    # Check previous line if target line already ends with semicolon (e.g. line 3 error caused by line 2 missing semicolon)
    if target_idx - 1 >= 0 and target_idx - 1 < len(corrected_lines):
        prev = corrected_lines[target_idx - 1].rstrip()
        if not prev.endswith(";") and not prev.endswith("}"):
            corrected_lines[target_idx - 1] = prev + ";"
            return "\n".join(corrected_lines)

    # Check for unclosed brace
    if "end of input" in error_msg.lower():
        corrected_lines.append("}")
        return "\n".join(corrected_lines)

    # Check any line missing semicolon
    for idx, l_text in enumerate(corrected_lines):
        s_text = l_text.rstrip()
        if s_text and not s_text.endswith(";") and not s_text.endswith("{") and not s_text.endswith("}"):
            corrected_lines[idx] = s_text + ";"
            return "\n".join(corrected_lines)

    return code + ";"

def get_ai_diagnostic(code: str, error_msg: str, line: int = 1) -> dict:
    """
    Sends the broken code and parser error message to the LLM (or uses fallback).
    Returns a structured dictionary containing explanation, fix, and corrected code.
    """
    client = get_client()
    
    if not client:
        corrected_code = heuristic_fix(code, error_msg, line)
        return {
            "explanation": f"Parser syntax error detected near line {line}: {error_msg} (Offline mode - GROQ_API_KEY missing or invalid in .env)",
            "suggested_fix": f"Add missing semicolon or brace around line {line if line else 1}.",
            "corrected_code": corrected_code
        }

    system_prompt = """
    You are an expert compiler syntax diagnostics assistant for an educational C-like Toy language.
    Analyze the syntax/grammar error produced by the LALR parser.
    You must output ONLY valid JSON matching this exact structure (no markdown fences, no extra text):
    {
      "explanation": "A concise 1-2 sentence explanation of why the parser failed.",
      "suggested_fix": "The exact modification required (e.g., 'Add missing semicolon at line 2').",
      "corrected_code": "The full source code with the error fixed."
    }
    """

    user_content = f"""
    Source Code:
    {code}

    Parser Error Details:
    - Message: {error_msg}
    - Location: Around Line {line}
    """

    try:
        # Try active Groq models (groq/compound-mini, qwen/qwen3.6-27b)
        model_name = "groq/compound-mini"
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
        except Exception:
            model_name = "qwen/qwen3.6-27b"
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
        res_json = json.loads(response.choices[0].message.content)
        if "corrected_code" not in res_json or not res_json["corrected_code"]:
            res_json["corrected_code"] = heuristic_fix(code, error_msg, line)
        return res_json

    except Exception as e:
        corrected_code = heuristic_fix(code, error_msg, line)
        return {
            "explanation": f"Parser syntax error detected near line {line}: {error_msg} (API error: {str(e)})",
            "suggested_fix": f"Add missing semicolon or brace around line {line if line else 1}.",
            "corrected_code": corrected_code
        }