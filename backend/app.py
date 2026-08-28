import streamlit as st
import pandas as pd
from code_editor import code_editor
import difflib
import streamlit.components.v1 as components
import traceback

# Adjust imports based on the backend folder structure
from app.lexer.lexer import tokenize
from app.parser.grammar import parse
from tree_viz import generate_graphviz_tree
from ai_diagnostic import get_ai_diagnostic

def render_dataframe(df):
    try:
        # Attempt to use native streamlit dataframe (requires pyarrow)
        st.dataframe(df, use_container_width=True)
    except ImportError:
        # Fallback to HTML if pyarrow is blocked (e.g. by Windows App Control)
        html = f"""<style>
.fallback-table table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
.fallback-table th, .fallback-table td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
.fallback-table th {{ background-color: rgba(128, 128, 128, 0.1); }}
</style>
<div class="fallback-table">
{df.to_html(index=False)}
</div>"""
        st.markdown(html, unsafe_allow_html=True)

# --- Sample Programs ---
SAMPLES = {
    "Valid: Variable & Arithmetic": """int a = 10;
int b = 20;
int c = a + b * 2;
""",
    "Valid: If-Else & While Loop": """int count = 0;
while (count < 5) {
    if (count == 2) {
        count = count + 2;
    } else {
        count = count + 1;
    }
}
""",
    "Invalid: Missing Semicolon & Delimiter": """int a = 10
int b = 20;
a + b;
"""
}

def set_sample(sample_name):
    st.session_state.code = SAMPLES[sample_name]

def apply_fix(corrected_code):
    st.session_state.code = corrected_code
    lex_result = tokenize(corrected_code)
    parse_result = parse(corrected_code)
    st.session_state.parse_results = {
        "lex": lex_result,
        "parse": parse_result
    }

@st.dialog("Compiler Line-by-Line Visualizer", width="large")
def visualizer_modal():
    if "visualizer_step" not in st.session_state:
        st.session_state.visualizer_step = 0

    code = st.session_state.code
    lines = code.splitlines()
    total_lines = len(lines)
    
    res = st.session_state.get('parse_results', {})
    tokens = res.get("lex", {}).get("tokens", [])
    symbols = res.get("lex", {}).get("symbol_table", [])
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("Previous", disabled=(st.session_state.visualizer_step <= 0)):
            st.session_state.visualizer_step -= 1
    with col3:
        if st.button("Next", disabled=(st.session_state.visualizer_step >= total_lines - 1)):
            st.session_state.visualizer_step += 1
            
    step = st.session_state.visualizer_step
    current_line = step + 1
    
    st.markdown(f"**Processing Line {current_line} of {total_lines}**")
    
    st.divider()
    
    code_col, data_col = st.columns([1, 1])
    
    with code_col:
        st.markdown("**Source Code**")
        code_html = "<pre style='background-color: #1e1e1e; padding: 10px; border-radius: 5px; overflow-x: auto; font-family: monospace; font-size: 14px; margin: 0;'>"
        for i, line in enumerate(lines):
            line_no = i + 1
            safe_line = line.replace("<", "&lt;").replace(">", "&gt;")
            if line_no == current_line:
                code_html += f"<span style='background-color: rgba(79, 70, 229, 0.5); display: block; width: 100%; border-left: 3px solid #4F46E5; padding-left: 5px; color: #fff;'>{line_no:2d} | {safe_line}</span>"
            else:
                code_html += f"<span style='color: #888; display: block;'>{line_no:2d} | {safe_line}</span>"
        code_html += "</pre>"
        st.markdown(code_html, unsafe_allow_html=True)
        
    with data_col:
        st.markdown("**Lexical Analysis (Tokens)**")
        line_tokens = [t for t in tokens if t['line'] == current_line]
        if line_tokens:
            df_tok = pd.DataFrame(line_tokens)
            render_dataframe(df_tok)
        else:
            st.info("No tokens generated for this line.")
            
        st.markdown("**Semantic Analysis (Symbol Table)**")
        line_symbols = [s for s in symbols if s['line'] <= current_line]
        if line_symbols:
            df_sym = pd.DataFrame(line_symbols)
            render_dataframe(df_sym)
        else:
            st.info("Symbol table is empty at this step.")

def main():
    st.set_page_config(page_title="Smart Syntax & Grammar Debugger", layout="wide")
    
    st.title("Smart Syntax & Grammar Debugger")
    
    if 'code' not in st.session_state:
        st.session_state.code = SAMPLES["Valid: Variable & Arithmetic"]
        
    if 'selected_sample' not in st.session_state:
        st.session_state.selected_sample = "Valid: Variable & Arithmetic"

    # --- Sidebar ---
    with st.sidebar:
        st.header("Samples")
        selected = st.selectbox("Choose a sample program:", list(SAMPLES.keys()), 
                                index=list(SAMPLES.keys()).index(st.session_state.selected_sample))
        if selected != st.session_state.selected_sample:
            st.session_state.selected_sample = selected
            set_sample(selected)
            if 'parse_results' in st.session_state:
                del st.session_state['parse_results']
            st.rerun()

    # --- Main Layout ---
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Source Code Editor")
        
        # Inject CSS for dark theme monospace code editor styling
        st.markdown("""
        <style>
        .stTextArea textarea {
            font-family: 'Fira Code', 'Consolas', 'Courier New', monospace !important;
            background-color: #1e1e2e !important;
            color: #cdd6f4 !important;
            font-size: 14px !important;
            border-radius: 6px !important;
            border: 1px solid #45475a !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Native Streamlit text area - guarantees synchronous state flush on button click!
        code_input = st.text_area(
            "Source Code",
            value=st.session_state.code,
            height=220,
            label_visibility="collapsed"
        )
        st.session_state.code = code_input

        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            compile_clicked = st.button("Compile", use_container_width=True, type="primary")
        with col_btn2:
            visualize_clicked = st.button("Visualize Pipeline", use_container_width=True)
        with col_btn3:
            reset_clicked = st.button("Reset", use_container_width=True)
            
        if reset_clicked:
            set_sample(st.session_state.selected_sample)
            if 'parse_results' in st.session_state:
                del st.session_state['parse_results']
            st.rerun()

        if compile_clicked or visualize_clicked:
            lex_result = tokenize(st.session_state.code)
            parse_result = parse(st.session_state.code)
            st.session_state.parse_results = {
                "lex": lex_result,
                "parse": parse_result
            }
            if visualize_clicked:
                st.session_state.visualizer_step = 0
                visualizer_modal()

        # Handle Diagnostics & Errors
        if 'parse_results' in st.session_state:
            res = st.session_state.parse_results
            parse_res = res["parse"]
            
            if not parse_res.get("success", False) and parse_res.get("error"):
                err = parse_res["error"]
                line_no = err.get("line") or len(st.session_state.code.splitlines())
                
                # Fetch AI diagnostics
                with st.spinner("Analyzing error with AI..."):
                    diagnostic = get_ai_diagnostic(
                        code=st.session_state.code,
                        error_msg=err.get("message", "Unknown syntax error"),
                        line=line_no
                    )
                
                st.error(f"**{err.get('error_type', 'Error')} detected at Line {line_no}:** {err.get('message', '')}")
                
                with st.expander("AI Diagnostic Details", expanded=True):
                    st.markdown(f"**Explanation:** {diagnostic.get('explanation')}")
                    st.markdown(f"**Suggested Fix:** {diagnostic.get('suggested_fix')}")
                    
                    # Compute diff
                    corrected = diagnostic.get("corrected_code", st.session_state.code)
                    if corrected and corrected.strip() != st.session_state.code.strip():
                        diff = difflib.unified_diff(
                            st.session_state.code.splitlines(),
                            corrected.splitlines(),
                            fromfile="Current Code",
                            tofile="Corrected Code",
                            lineterm=""
                        )
                        diff_str = "\n".join(diff)
                        if diff_str:
                            st.markdown("**Diff:**")
                            st.code(diff_str, language="diff")
                            
                        st.button("Apply AI Auto-Fix", on_click=apply_fix, args=(corrected,), type="primary")
            elif parse_res.get("success", False):
                st.success("Compilation successful! Parse tree generated.")

    with col2:
        st.subheader("Analysis")
        tab1, tab2, tab3 = st.tabs(["Parse Tree", "Token Stream", "Symbol Table"])
        
        if 'parse_results' in st.session_state:
            res = st.session_state.parse_results
            
            with tab1:
                if res["parse"].get("success", False):
                    parse_tree_dict = res["parse"].get("parse_tree")
                    if parse_tree_dict:
                        dot = generate_graphviz_tree(parse_tree_dict)
                        st.graphviz_chart(dot, use_container_width=True)
                else:
                    st.info("Parse tree is not available due to syntax errors.")
                    
            with tab2:
                tokens = res["lex"].get("tokens", [])
                if tokens:
                    df_tokens = pd.DataFrame(tokens)
                    render_dataframe(df_tokens)
                else:
                    st.info("No tokens to display.")
                    
            with tab3:
                symbols = res["lex"].get("symbol_table", [])
                if symbols:
                    df_symbols = pd.DataFrame(symbols)
                    render_dataframe(df_symbols)
                else:
                    st.info("Symbol table is empty.")
        else:
            with tab1:
                st.info("Click 'Compile & Parse' to generate the parse tree.")
            with tab2:
                st.info("Click 'Compile & Parse' to generate the token stream.")
            with tab3:
                st.info("Click 'Compile & Parse' to generate the symbol table.")

if __name__ == "__main__":
    main()
