import streamlit as st
import pandas as pd
from code_editor import code_editor
import difflib
import streamlit.components.v1 as components
import traceback

# Adjust imports based on the backend folder structure
from app.semantic.pipeline import compile_source
from tree_viz import generate_graphviz_tree
import importlib
import ai_diagnostic
import rag_engine
importlib.reload(ai_diagnostic)
importlib.reload(rag_engine)
from ai_diagnostic import get_ai_diagnostic
from rag_engine import get_rag_engine
from cfg_viz import generate_graphviz_cfg

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
    st.session_state.parse_results = compile_source(corrected_code)
    st.session_state.pop("cached_diagnostic", None)
    st.session_state.pop("cached_sem_diagnostic", None)

@st.dialog("Compiler Line-by-Line Visualizer", width="large")
def visualizer_modal():
    if "visualizer_step" not in st.session_state:
        st.session_state.visualizer_step = 0

    code = st.session_state.code
    lines = code.splitlines()
    total_lines = len(lines)
    
    res = st.session_state.get('parse_results', {})
    tokens = res.get("lex", {}).get("tokens", [])
    semantic_result = res.get("semantic")
    symbols = (
        semantic_result.get("symbol_table", [])
        if semantic_result is not None
        else res.get("lex", {}).get("symbol_table", [])
    )
    
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

@st.dialog("Phase 4: Intermediate Code Generation Visualizer", width="large")
def icg_stepper_modal():
    res = st.session_state.get('parse_results', {})
    icg_res = res.get("icg")
    if not icg_res or not icg_res.get("success", False):
        st.warning("Please click 'Compile' to generate intermediate code first.")
        return

    steps = icg_res.get("steps", [])
    total_steps = len(steps)
    if total_steps == 0:
        st.info("No stepping steps available.")
        return

    if "icg_step" not in st.session_state:
        st.session_state.icg_step = 0

    # Ensure step is within valid range
    if st.session_state.icg_step >= total_steps:
        st.session_state.icg_step = total_steps - 1
    if st.session_state.icg_step < 0:
        st.session_state.icg_step = 0

    # Controls Row
    col_prev, col_status, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("Previous", disabled=(st.session_state.icg_step <= 0), use_container_width=True, key="icg_btn_prev"):
            st.session_state.icg_step = max(0, st.session_state.icg_step - 1)
            st.session_state.icg_slider_val = st.session_state.icg_step

    with col_next:
        if st.button("Next", disabled=(st.session_state.icg_step >= total_steps - 1), use_container_width=True, key="icg_btn_next"):
            st.session_state.icg_step = min(total_steps - 1, st.session_state.icg_step + 1)
            st.session_state.icg_slider_val = st.session_state.icg_step

    if "icg_slider_val" not in st.session_state or st.session_state.icg_slider_val != st.session_state.icg_step:
        st.session_state.icg_slider_val = st.session_state.icg_step

    def on_slider_change():
        st.session_state.icg_step = st.session_state.icg_slider_val

    if total_steps > 1:
        st.slider(
            "Step Timeline Slider",
            min_value=0,
            max_value=total_steps - 1,
            key="icg_slider_val",
            on_change=on_slider_change,
            label_visibility="collapsed"
        )

    curr_idx = st.session_state.icg_step
    step_data = steps[curr_idx]

    with col_status:
        st.markdown(
            f"<div style='text-align:center; font-weight:700; font-size:15px; padding-top:6px;'>"
            f"Step {curr_idx + 1} of {total_steps}"
            f"</div>",
            unsafe_allow_html=True
        )

    # Action callout
    st.info(f"**AST Node: [{step_data['node_name']}]** &bull; {step_data['action']}")
    st.divider()

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("#### Live State Allocators")
        m1, m2 = st.columns(2)
        m1.metric("Temporaries", len(step_data.get("temps", [])))
        m2.metric("Labels", len(step_data.get("labels", [])))

        st.markdown("**Allocated Temporaries:**")
        temps = step_data.get("temps", [])
        if temps:
            st.markdown(" ".join([f"`{t}`" for t in temps]))
        else:
            st.caption("None allocated yet.")

        st.markdown("**Generated Labels:**")
        labels = step_data.get("labels", [])
        if labels:
            st.markdown(" ".join([f"`{l}`" for l in labels]))
        else:
            st.caption("None generated yet.")

        if step_data.get("quadruple"):
            st.markdown("#### Latest Quadruple Emitted")
            q = step_data["quadruple"]
            df_q = pd.DataFrame([{
                "op": q.get("op"),
                "arg1": q.get("arg1") or "-",
                "arg2": q.get("arg2") or "-",
                "result": q.get("result") or "-"
            }])
            df_q.columns = ["Operator", "Arg 1", "Arg 2", "Result"]
            render_dataframe(df_q)

        if step_data.get("triple"):
            st.markdown("#### Latest Triple Emitted")
            t = step_data["triple"]
            df_t = pd.DataFrame([{
                "index": f"({t.get('index')})",
                "op": t.get("op"),
                "arg1": t.get("arg1") or "-",
                "arg2": t.get("arg2") or "-"
            }])
            df_t.columns = ["(i)", "Operator", "Arg 1", "Arg 2"]
            render_dataframe(df_t)

    with col_right:
        vtab1, vtab2, vtab3, vtab4 = st.tabs(["3AC Traversal", "Control Flow Graph", "Quadruples", "Triples"])

        with vtab1:
            st.markdown("#### Intermediate Code (3AC)")
            insts = icg_res.get("instructions", [])
            active_idx = step_data.get("instruction_index")

            code_html = "<pre style='background-color: #1e1e2e; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 13px; line-height: 1.6; max-height: 400px; overflow-y: auto;'>"
            for inst in insts:
                idx = inst.get("index", 0)
                code_text = inst.get("code", "")
                leader = "[LEADER] " if inst.get("is_leader") else "         "
                if active_idx is not None and idx == active_idx:
                    code_html += f"<span style='background-color: rgba(99, 102, 241, 0.4); border-left: 3px solid #6366f1; display: block; color: #fff; padding-left: 6px;'>{idx:2d}: {leader}{code_text}  <- active</span>"
                elif active_idx is not None and idx < active_idx:
                    code_html += f"<span style='color: #cdd6f4; display: block; padding-left: 6px;'>{idx:2d}: {leader}{code_text}</span>"
                else:
                    code_html += f"<span style='color: #585b70; display: block; padding-left: 6px;'>{idx:2d}: {leader}{code_text}</span>"
            code_html += "</pre>"
            st.markdown(code_html, unsafe_allow_html=True)

        with vtab2:
            cfg_data = icg_res.get("cfg", {})
            if cfg_data and cfg_data.get("blocks"):
                st.markdown("#### Control Flow Graph")
                st.caption("Emerald = True branch, Red = False branch, Purple = Goto, Cyan = Fall-through")
                dot_cfg = generate_graphviz_cfg(cfg_data)
                st.graphviz_chart(dot_cfg, use_container_width=True)
            else:
                st.info("No CFG data available.")

        with vtab3:
            quads = icg_res.get("quadruples", [])
            if quads:
                df_quads = pd.DataFrame(quads)[["index", "op", "arg1", "arg2", "result"]]
                df_quads.columns = ["#", "Operator", "Arg 1", "Arg 2", "Result"]
                render_dataframe(df_quads)
            else:
                st.info("No quadruples generated.")

        with vtab4:
            triples = icg_res.get("triples", [])
            if triples:
                df_triples = pd.DataFrame(triples)[["index", "op", "arg1", "arg2"]]
                df_triples.columns = ["(i)", "Operator", "Arg 1", "Arg 2"]
                render_dataframe(df_triples)
            else:
                st.info("No triples generated.")

def render_tutor_ui(res=None):
    st.markdown("### 🤖 ToyLang AI Compiler Tutor")
    st.caption("Ask questions about your code, compiler phases (Lexer, Parser, Semantic, ICG, Assembly), or optimization theory.")
    
    # Header with clear button
    th_col1, th_col2 = st.columns([4, 1])
    with th_col1:
        st.markdown("**Quick Topics:**")
    with th_col2:
        if st.button("Clear Chat", key="btn_clear_tutor", use_container_width=True):
            st.session_state.tutor_history = []
            st.rerun()

    qcol1, qcol2, qcol3, qcol4 = st.columns(4)
    clicked_query = None
    if qcol1.button("Assembly Translation", key="btn_explain_asm", use_container_width=True):
        clicked_query = "Explain how the intermediate code translates into x86-64 NASM assembly instructions, including register usage and glibc calls."
    if qcol2.button("3AC & Quadruples", key="btn_explain_icg", use_container_width=True):
        clicked_query = "Explain the 3-address code quadruples and temporary variables generated for this program."
    if qcol3.button("Scoping & Symbols", key="btn_explain_scope", use_container_width=True):
        clicked_query = "How does ToyLang handle lexical scoping and symbol table lookup for the variables in this program?"
    if qcol4.button("ToyLang CFG Rules", key="btn_check_cfg", use_container_width=True):
        clicked_query = "What formal CFG grammar productions in ToyLang are used to parse this program?"

    if "tutor_history" not in st.session_state:
        st.session_state.tutor_history = []

    with st.form(key="tutor_form", clear_on_submit=True):
        user_input = st.text_input("Ask a question about this code or compiler theory:", placeholder="e.g. Why did the compiler emit 'cqo' before 'idiv'?")
        submit_btn = st.form_submit_button("Ask Tutor", type="primary")

    query_to_run = clicked_query or (user_input if submit_btn and user_input.strip() else None)

    if query_to_run:
        curr_res = res or (st.session_state.get('parse_results') or {})
        compiler_ctx = {
            "source_code": st.session_state.get("code", ""),
            "parse_tree": (curr_res.get("parse") or {}).get("parse_tree") if curr_res else None,
            "parse_error": (curr_res.get("parse") or {}).get("error") if curr_res else None,
            "symbols": (curr_res.get("lex") or {}).get("symbol_table", []) if curr_res else [],
            "ir_code": "\n".join((curr_res.get("icg") or {}).get("three_address_code") or []) if curr_res else "",
            "asm_code": (curr_res.get("assembly") or {}).get("assembly", "") if curr_res else ""
        }
        with st.spinner("Retrieving ToyLang specifications and generating grounded answer..."):
            rag = get_rag_engine()
            tutor_res = rag.ask_tutor(query_to_run, compiler_ctx)
            st.session_state.tutor_history.insert(0, {
                "query": query_to_run,
                "answer": tutor_res["answer"],
                "rules": tutor_res["retrieved_chunks"],
                "model": tutor_res.get("model_used", "Groq")
            })

    if st.session_state.tutor_history:
        for idx, item in enumerate(st.session_state.tutor_history):
            with st.chat_message("user"):
                st.write(item["query"])
            with st.chat_message("assistant"):
                st.markdown(item["answer"])
                if item.get("rules"):
                    with st.expander(f"📚 Retrieved Knowledge Chunks ({item.get('model', 'RAG')})", expanded=False):
                        for r in item["rules"]:
                            st.markdown(f"**{r.get('title')}** `({r.get('document')})` - *Relevance Score: {r.get('score')}*")
                            st.caption(r.get("content"))
    else:
        st.info("Ask any question above or click one of the quick topics to explore compiler concepts grounded in ToyLang specifications!")

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

        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        with col_btn1:
            compile_clicked = st.button("Compile", use_container_width=True, type="primary")
        with col_btn2:
            visualize_clicked = st.button("Pipeline Stepper", use_container_width=True)
        with col_btn3:
            icg_clicked = st.button("Phase 4 Stepper", use_container_width=True)
        with col_btn4:
            reset_clicked = st.button("Reset", use_container_width=True)
            
        if reset_clicked:
            set_sample(st.session_state.selected_sample)
            st.session_state.pop('parse_results', None)
            st.session_state.pop('cached_diagnostic', None)
            st.session_state.pop('cached_sem_diagnostic', None)
            st.rerun()

        if compile_clicked or visualize_clicked or icg_clicked:
            st.session_state.parse_results = compile_source(st.session_state.code)
            st.session_state.pop('cached_diagnostic', None)
            st.session_state.pop('cached_sem_diagnostic', None)
            if visualize_clicked:
                st.session_state.visualizer_step = 0
                visualizer_modal()
            elif icg_clicked:
                st.session_state.icg_step = 0
                st.session_state.icg_slider_val = 0
                icg_stepper_modal()

        # Handle Diagnostics & Errors
        if 'parse_results' in st.session_state:
            res = st.session_state.parse_results
            parse_res = res["parse"]
            
            if not parse_res.get("success", False) and parse_res.get("error"):
                err = parse_res["error"]
                line_no = err.get("line") or len(st.session_state.code.splitlines())
                
                # Fetch AI diagnostics (cached per compilation to prevent rerun loops)
                if "cached_diagnostic" not in st.session_state:
                    with st.spinner("Analyzing error with RAG AI..."):
                        diagnostic = get_ai_diagnostic(
                            code=st.session_state.code,
                            error_msg=err.get("message", "Unknown syntax error"),
                            line=line_no,
                            phase="lexical" if err.get("error_type") == "LexicalError" else "syntax"
                        )
                        st.session_state.cached_diagnostic = diagnostic
                else:
                    diagnostic = st.session_state.cached_diagnostic
                
                st.error(f"**{err.get('error_type', 'Error')} detected at Line {line_no}:** {err.get('message', '')}")
                
                with st.expander("AI Diagnostic Details (RAG Grounded)", expanded=True):
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
                            
                        st.button("Apply AI Auto-Fix", on_click=apply_fix, args=(corrected,), type="primary", key="apply_syntax_fix")

                    rules = diagnostic.get("retrieved_rules", [])
                    if rules:
                        with st.expander("📚 Retrieved ToyLang Specification Rules (RAG)", expanded=False):
                            for r in rules:
                                st.markdown(f"**{r.get('title')}** `({r.get('document')})`")
                                st.caption(r.get("content"))
            elif parse_res.get("success", False):
                semantic_result = res.get("semantic")
                if semantic_result is not None and not semantic_result["success"]:
                    st.error("Semantic analysis failed.")
                    first_err = semantic_result["errors"][0] if semantic_result.get("errors") else {"message": "Semantic error", "line": 1}
                    sem_line_no = first_err.get("line") or 1
                    
                    if "cached_sem_diagnostic" not in st.session_state:
                        with st.spinner("Analyzing semantic error with RAG AI..."):
                            sem_diag = get_ai_diagnostic(
                                code=st.session_state.code,
                                error_msg=first_err.get("message", "Semantic error"),
                                line=sem_line_no,
                                phase="semantic"
                            )
                            st.session_state.cached_sem_diagnostic = sem_diag
                    else:
                        sem_diag = st.session_state.cached_sem_diagnostic
                    
                    for err in semantic_result["errors"]:
                        location = (
                            f" at line {err['line']}"
                            if err.get("line") is not None
                            else ""
                        )
                        st.error(
                            f"{err['code']}{location}: {err['message']}"
                        )

                    with st.expander("AI Semantic Diagnostic Details (RAG Grounded)", expanded=True):
                        st.markdown(f"**Explanation:** {sem_diag.get('explanation')}")
                        st.markdown(f"**Suggested Fix:** {sem_diag.get('suggested_fix')}")
                        
                        sem_corrected = sem_diag.get("corrected_code", st.session_state.code)
                        if sem_corrected and sem_corrected.strip() != st.session_state.code.strip():
                            diff = difflib.unified_diff(
                                st.session_state.code.splitlines(),
                                sem_corrected.splitlines(),
                                fromfile="Current Code",
                                tofile="Corrected Code",
                                lineterm=""
                            )
                            diff_str = "\n".join(diff)
                            if diff_str:
                                st.markdown("**Diff:**")
                                st.code(diff_str, language="diff")
                            st.button("Apply AI Semantic Fix", on_click=apply_fix, args=(sem_corrected,), type="primary", key="apply_sem_fix")

                        sem_rules = sem_diag.get("retrieved_rules", [])
                        if sem_rules:
                            with st.expander("📚 Retrieved ToyLang Semantic Rules (RAG)", expanded=False):
                                for r in sem_rules:
                                    st.markdown(f"**{r.get('title')}** `({r.get('document')})`")
                                    st.caption(r.get("content"))
                else:
                    st.success(
                        "Compilation successful! Parse tree generated."
                    )

    with col2:
        st.subheader("Analysis")
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Parse Tree", "Token Stream", "Symbol Table", "Intermediate Code (ICG)", "Assembly Code (ASM)", "🤖 AI Compiler Tutor"])
        
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

            with tab4:
                icg_res = res.get("icg")
                if icg_res and icg_res.get("success", False):
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("3AC Instructions", len(icg_res.get("instructions", [])))
                    m2.metric("Temporaries", icg_res.get("temp_count", 0))
                    m3.metric("Labels", icg_res.get("label_count", 0))
                    cfg_data = icg_res.get("cfg") or {}
                    blocks = cfg_data.get("blocks", {})
                    m4.metric("Basic Blocks", len(blocks))

                    if st.button("Step Through ICG Traversal", use_container_width=True, type="primary"):
                        st.session_state.icg_step = 0
                        st.session_state.icg_slider_val = 0
                        icg_stepper_modal()

                    icg_sub1, icg_sub2, icg_sub3, icg_sub4 = st.tabs(["3AC Code", "Quadruples", "Triples", "Control Flow Graph"])

                    with icg_sub1:
                        tac_lines = icg_res.get("three_address_code", [])
                        tac_str = "\n".join(f"{i:2d}: {line}" for i, line in enumerate(tac_lines))
                        st.code(tac_str, language="c")

                    with icg_sub2:
                        quads = icg_res.get("quadruples", [])
                        if quads:
                            df_quads = pd.DataFrame(quads)[["index", "op", "arg1", "arg2", "result"]]
                            df_quads.columns = ["#", "Operator", "Arg 1", "Arg 2", "Result"]
                            render_dataframe(df_quads)
                        else:
                            st.info("No quadruples generated.")

                    with icg_sub3:
                        triples = icg_res.get("triples", [])
                        if triples:
                            df_triples = pd.DataFrame(triples)[["index", "op", "arg1", "arg2"]]
                            df_triples.columns = ["(i)", "Operator", "Arg 1", "Arg 2"]
                            render_dataframe(df_triples)
                        else:
                            st.info("No triples generated.")

                    with icg_sub4:
                        edges = cfg_data.get("edges", [])
                        
                        if cfg_data and blocks:
                            st.markdown("##### Control Flow Graph")
                            st.caption("Emerald = True branch, Red = False branch, Purple = Goto, Cyan = Fall-through")
                            dot_cfg = generate_graphviz_cfg(cfg_data)
                            st.graphviz_chart(dot_cfg, use_container_width=True)

                        st.markdown(f"**Decomposed {len(blocks)} Basic Blocks:**")
                        for bid, bdata in blocks.items():
                            leader_idx = bdata.get("leader_index")
                            leader_str = f" [Leader #{leader_idx}]" if leader_idx is not None else ""
                            with st.expander(f"Basic Block {bid}{leader_str} (Predecessors: {bdata.get('predecessors', [])} | Successors: {bdata.get('successors', [])})", expanded=False):
                                for code_line in bdata.get("code_lines", []):
                                    st.code(code_line, language="c")

                        if edges:
                            with st.expander("Directed CFG Edges Table", expanded=False):
                                df_edges = pd.DataFrame(edges)
                                render_dataframe(df_edges)

                elif icg_res and not icg_res.get("success", False):
                    st.error(f"ICG Generation failed: {icg_res.get('error')}")
                else:
                    st.info("Intermediate code will be generated once syntax and semantic analysis succeed.")

            # ---------------------------------------------------------------
            # Tab 5 - Assembly Code Generation (Phase 5)
            # ---------------------------------------------------------------
            with tab5:
                asm_res = res.get("assembly")
                if asm_res is None:
                    st.info(
                        "Assembly code is generated after successful syntax, "
                        "semantic, and intermediate code generation phases. "
                        "Please fix any earlier errors and compile again."
                    )
                elif not asm_res.get("success", False):
                    st.error(f"Assembly generation failed: {asm_res.get('error')}")
                    if asm_res.get("errors"):
                        for warn in asm_res["errors"]:
                            st.warning(warn)
                else:
                    # -- Metrics row --
                    asm_src = asm_res["assembly"]
                    n_lines = len(asm_src.splitlines())
                    n_vars  = asm_src.count("resq")
                    n_jmps  = sum(1 for l in asm_src.splitlines() if l.strip().startswith(("jmp", "je", "jne", "jl", "jle", "jg", "jge")))
                    am1, am2, am3 = st.columns(3)
                    am1.metric("Target",      asm_res.get("target", "x86-64 NASM"))
                    am2.metric("ASM Lines",   n_lines)
                    am3.metric("Variables",   n_vars)

                    # -- Non-fatal warnings --
                    if asm_res.get("errors"):
                        with st.expander("Assembly Warnings", expanded=False):
                            for warn in asm_res["errors"]:
                                st.warning(warn)

                    # -- Code display --
                    st.markdown("#### Generated x86-64 NASM Assembly")
                    st.code(asm_src, language="nasm")

                    # -- Download button --
                    st.download_button(
                        label="⬇️ Download .asm file",
                        data=asm_src.encode("utf-8"),
                        file_name="output.asm",
                        mime="text/plain",
                        use_container_width=True,
                    )

                    # -- Build instructions --
                    with st.expander("How to assemble and run", expanded=False):
                        st.markdown("""
**Requirements:** NASM ≥ 2.14, GCC (or ld) for linking against glibc.

```bash
# 1. Assemble
nasm -f elf64 output.asm -o output.o

# 2. Link (using GCC for automatic glibc linkage)
gcc -no-pie output.o -o output

# 3. Run
./output
```

> **Note:** The generated code uses C `printf` for print statements and
> `exit()` for program termination — standard glibc functions.
> Tested on Linux x86-64.  On Windows, use WSL or an x86-64 Linux VM.
                        """)

            # ---------------------------------------------------------------
            # Tab 6 - AI Compiler Tutor (RAG Grounded)
            # ---------------------------------------------------------------
            with tab6:
                render_tutor_ui(res)
        else:
            with tab1:
                st.info("Click 'Compile' to generate the parse tree.")
            with tab2:
                st.info("Click 'Compile' to generate the token stream.")
            with tab3:
                st.info("Click 'Compile' to generate the symbol table.")
            with tab4:
                st.info("Click 'Compile' to generate intermediate code.")
            with tab5:
                st.info("Click 'Compile' to generate assembly code.")
            with tab6:
                render_tutor_ui(None)

if __name__ == "__main__":
    main()
