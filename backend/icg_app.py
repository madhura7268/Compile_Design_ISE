"""icg_app.py - Dedicated Native Streamlit Visualizer for Phase 4 (Intermediate Code Generation).

Provides a pure, native Streamlit visualizer for:
1. Three-Address Code (3AC) generation with leader identification
2. Quadruples table (op, arg1, arg2, result)
3. Triples table ((i), op, arg1, arg2)
4. Control Flow Graph (CFG) basic blocks and colored directed branch edges
5. Interactive SDD tree-walking step-by-step execution debugger
"""

import streamlit as st
import pandas as pd
import graphviz
from typing import Dict, Any, List

# Local imports
from app.semantic.pipeline import compile_source
from cfg_viz import generate_graphviz_cfg
from tree_viz import generate_graphviz_tree


def render_dataframe(df: pd.DataFrame) -> None:
    """Render DataFrame using native streamlit or clean HTML fallback."""
    try:
        st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception:
        st.table(df)


# -----------------------------------------------------------------------------
# Curated Educational Test Programs
# -----------------------------------------------------------------------------
SAMPLES = {
    "1. Arithmetic & Expressions": """int a = 10;
int b = 20;
int c = a + b * 2;
""",
    "2. If-Else Branching": """int a = 5;
if (a > 10) {
    a = a + 1;
} else {
    a = a - 1;
}
""",
    "3. While Loop (Iteration)": """int count = 0;
while (count < 5) {
    count = count + 1;
}
""",
    "4. Nested Control Flow (While + If-Else)": """int count = 0;
while (count < 5) {
    if (count == 2) {
        count = count + 2;
    } else {
        count = count + 1;
    }
}
""",
    "5. Complex Expressions & Operator Precedence": """int a = 2;
int b = 3;
int c = 4;
int d = a + b * c - (a + b);
"""
}


def main():
    st.set_page_config(
        page_title="Phase 4: Intermediate Code Generation (ICG)",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # -------------------------------------------------------------------------
    # Styling
    # -------------------------------------------------------------------------
    st.markdown("""
    <style>
    .stTextArea textarea {
        font-family: 'Fira Code', 'Consolas', 'Courier New', monospace !important;
        background-color: #1e1e2e !important;
        color: #cdd6f4 !important;
        font-size: 14px !important;
        border-radius: 8px !important;
        border: 1px solid #45475a !important;
    }
    .metric-card {
        background: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # Session State Initialization
    # -------------------------------------------------------------------------
    if "icg_sample_name" not in st.session_state:
        st.session_state.icg_sample_name = "1. Arithmetic & Expressions"
    if "icg_code" not in st.session_state:
        st.session_state.icg_code = SAMPLES[st.session_state.icg_sample_name]
    if "icg_step_idx" not in st.session_state:
        st.session_state.icg_step_idx = 0

    # -------------------------------------------------------------------------
    # Sidebar
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.title("⚡ Phase 4: ICG")
        st.caption("Intermediate Code Generation & CFG Visualizer")
        st.markdown("---")

        st.subheader("📁 Test Cases")
        selected_sample = st.selectbox(
            "Choose Sample Program:",
            list(SAMPLES.keys()),
            index=list(SAMPLES.keys()).index(st.session_state.icg_sample_name)
        )

        if selected_sample != st.session_state.icg_sample_name:
            st.session_state.icg_sample_name = selected_sample
            st.session_state.icg_code = SAMPLES[selected_sample]
            st.session_state.icg_step_idx = 0
            st.rerun()

        st.markdown("---")
        st.subheader("💡 Compiler Concepts")
        st.markdown("""
        - **3AC:** Max 3 addresses per op (`t0 = b * c`)
        - **Quadruples:** `(op, arg1, arg2, result)`
        - **Triples:** `(op, arg1, arg2)` referenced by index `(i)`
        - **CFG Leaders:**
          1. First instruction
          2. Target of any conditional/unconditional jump
          3. Instruction immediately following a jump
        """)

        st.markdown("---")
        st.caption("ToyLang Educational Compiler &bull; Phase 4")

    # -------------------------------------------------------------------------
    # Header Banner
    # -------------------------------------------------------------------------
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.title("Intermediate Code Generator (ICG)")
        st.markdown("Interactive Syntax-Directed Translation, Three-Address Code, Quadruples, Triples, and Control Flow Graphs.")
    with col_head2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Reset Editor", use_container_width=True):
            st.session_state.icg_code = SAMPLES[st.session_state.icg_sample_name]
            st.session_state.icg_step_idx = 0
            st.rerun()

    # -------------------------------------------------------------------------
    # Source Code Input
    # -------------------------------------------------------------------------
    st.subheader("Source Code (ToyLang)")
    code_input = st.text_area(
        "Source Code Editor",
        value=st.session_state.icg_code,
        height=160,
        label_visibility="collapsed"
    )
    if code_input != st.session_state.icg_code:
        st.session_state.icg_code = code_input

    # -------------------------------------------------------------------------
    # Compile Source Code through Pipeline
    # -------------------------------------------------------------------------
    results = compile_source(st.session_state.icg_code)
    parse_res = results.get("parse", {})
    semantic_res = results.get("semantic")
    icg_res = results.get("icg")

    # Syntax / Semantic error handling
    if not parse_res.get("success", False):
        err = parse_res.get("error", {})
        st.error(f"❌ Syntax Error at Line {err.get('line', '?')}: {err.get('message', 'Syntax error')}")
        return

    if semantic_res is not None and not semantic_res.get("success", True):
        st.error("❌ Semantic Analysis Failed:")
        for err in semantic_res.get("errors", []):
            st.error(f"&bull; {err.get('code')}: {err.get('message')}")
        return

    if not icg_res or not icg_res.get("success", False):
        err_msg = icg_res.get("error") if icg_res else "Intermediate code generation failed."
        st.error(f"❌ ICG Error: {err_msg}")
        return

    # -------------------------------------------------------------------------
    # Summary Metrics Row
    # -------------------------------------------------------------------------
    instructions = icg_res.get("instructions", [])
    quadruples = icg_res.get("quadruples", [])
    triples = icg_res.get("triples", [])
    cfg_data = icg_res.get("cfg", {})
    blocks = cfg_data.get("blocks", {})
    steps = icg_res.get("steps", [])

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("3AC Instructions", len(instructions))
    m2.metric("Temporaries Allocated", icg_res.get("temp_count", 0))
    m3.metric("Labels Generated", icg_res.get("label_count", 0))
    m4.metric("Basic Blocks", len(blocks))
    m5.metric("Traversal Steps", len(steps))

    st.markdown("---")

    # -------------------------------------------------------------------------
    # Interactive SDD Execution Stepper
    # -------------------------------------------------------------------------
    st.subheader("🔍 Step-by-Step SDD Traversal Stepper")

    total_steps = len(steps)
    if total_steps > 0:
        if st.session_state.icg_step_idx >= total_steps:
            st.session_state.icg_step_idx = total_steps - 1

        curr_step_idx = st.session_state.icg_step_idx
        current_step = steps[curr_step_idx]

        # Step controls
        col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4 = st.columns([1, 1, 3, 1])
        with col_ctrl1:
            if st.button("⏮ Previous", disabled=(curr_step_idx <= 0), use_container_width=True, key="step_prev"):
                st.session_state.icg_step_idx -= 1
                st.rerun()

        with col_ctrl2:
            if st.button("Next ⏭", disabled=(curr_step_idx >= total_steps - 1), use_container_width=True, key="step_next"):
                st.session_state.icg_step_idx += 1
                st.rerun()

        with col_ctrl3:
            slider_val = st.slider(
                "Step Scrubber",
                min_value=0,
                max_value=total_steps - 1,
                value=curr_step_idx,
                label_visibility="collapsed",
                key="step_slider"
            )
            if slider_val != curr_step_idx:
                st.session_state.icg_step_idx = slider_val
                st.rerun()

        with col_ctrl4:
            st.markdown(f"<div style='text-align:right; font-weight:700; padding-top:8px;'>Step {curr_step_idx + 1} / {total_steps}</div>", unsafe_allow_html=True)

        # Step Callout Card
        node_name = current_step.get("node_name", "AST Node")
        action_text = current_step.get("action", "")
        st.info(f"📍 **AST Node: [{node_name}]** &mdash; {action_text}")

        # Live State Badges
        col_s1, col_s2, col_s3 = st.columns([1, 1, 2])
        with col_s1:
            st.markdown("**Live Temporaries:**")
            t_list = current_step.get("temps", [])
            if t_list:
                st.markdown(" ".join([f"`{t}`" for t in t_list]))
            else:
                st.caption("None allocated yet.")

        with col_s2:
            st.markdown("**Live Labels:**")
            l_list = current_step.get("labels", [])
            if l_list:
                st.markdown(" ".join([f"`{l}`" for l in l_list]))
            else:
                st.caption("None generated yet.")

        with col_s3:
            if current_step.get("quadruple"):
                q = current_step["quadruple"]
                st.markdown(f"**Latest Emitted Quadruple:** `({q.get('op')}, {q.get('arg1') or '-'}, {q.get('arg2') or '-'}, {q.get('result') or '-'})`")
            elif current_step.get("triple"):
                t = current_step["triple"]
                st.markdown(f"**Latest Emitted Triple:** `({t.get('op')}, {t.get('arg1') or '-'}, {t.get('arg2') or '-'})`")
            else:
                st.caption("No new IR record emitted at this step.")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # Comprehensive IR & CFG Representations Tabs
    # -------------------------------------------------------------------------
    tab_cfg, tab_3ac, tab_quads, tab_triples, tab_blocks, tab_ast = st.tabs([
        "🕸️ Control Flow Graph (CFG)",
        "⚡ Three-Address Code (3AC)",
        "📋 Quadruples Table",
        "🔢 Triples Table",
        "🧱 Basic Blocks Breakdown",
        "🌳 Abstract Syntax Tree (AST)"
    ])

    # -------------------------------------------------------------------------
    # Tab 1: Control Flow Graph
    # -------------------------------------------------------------------------
    with tab_cfg:
        st.markdown("#### Control Flow Graph (CFG)")
        st.caption("Basic blocks with leaders and colored branch edges: Emerald = True branch, Red = False branch, Purple = Goto, Cyan = Fall-through.")
        
        if cfg_data and blocks:
            dot_cfg = generate_graphviz_cfg(cfg_data)
            st.graphviz_chart(dot_cfg, use_container_width=True)
        else:
            st.info("No CFG blocks available.")

    # -------------------------------------------------------------------------
    # Tab 2: Three-Address Code (3AC)
    # -------------------------------------------------------------------------
    with tab_3ac:
        st.markdown("#### Linear Three-Address Code (3AC)")
        active_inst_idx = current_step.get("instruction_index") if total_steps > 0 else None

        col_3ac_code, col_3ac_info = st.columns([3, 1])

        with col_3ac_code:
            code_html = "<pre style='background-color: #1e1e2e; padding: 14px; border-radius: 8px; font-family: monospace; font-size: 14px; line-height: 1.7; overflow-x: auto;'>"
            for inst in instructions:
                idx = inst.get("index", 0)
                code_text = inst.get("code", "")
                is_leader = inst.get("is_leader", False)
                leader_tag = "<span style='color:#f59e0b; font-weight:bold;'>[LEADER]</span> " if is_leader else "         "

                safe_code = code_text.replace("<", "&lt;").replace(">", "&gt;")

                if active_inst_idx is not None and idx == active_inst_idx:
                    code_html += f"<span style='background-color: rgba(99, 102, 241, 0.45); border-left: 4px solid #6366f1; display: block; color: #ffffff; padding-left: 8px;'>{idx:2d}: {leader_tag}{safe_code}  ⬅ ACTIVE</span>"
                elif active_inst_idx is not None and idx < active_inst_idx:
                    code_html += f"<span style='color: #cdd6f4; display: block; padding-left: 8px;'>{idx:2d}: {leader_tag}{safe_code}</span>"
                else:
                    code_html += f"<span style='color: #6c7086; display: block; padding-left: 8px;'>{idx:2d}: {leader_tag}{safe_code}</span>"
            code_html += "</pre>"
            st.markdown(code_html, unsafe_allow_html=True)

        with col_3ac_info:
            st.markdown("##### 📌 Legend")
            st.markdown("""
            - `[LEADER]`: Start of a basic block.
            - `t0, t1...`: Compiler-generated temporary registers.
            - `L0, L1...`: Flow control branch target labels.
            - `if False x goto L`: Conditional test branch.
            - `goto L`: Unconditional jump.
            """)
            raw_tac = "\n".join(f"{i:2d}: {inst.get('code')}" for i, inst in enumerate(instructions))
            st.download_button(
                "📥 Download 3AC (.txt)",
                data=raw_tac,
                file_name="intermediate_code_3ac.txt",
                mime="text/plain",
                use_container_width=True
            )

    # -------------------------------------------------------------------------
    # Tab 3: Quadruples Table
    # -------------------------------------------------------------------------
    with tab_quads:
        st.markdown("#### Quadruples Table")
        st.caption("Standard 4-tuple representation: (operator, argument 1, argument 2, result).")
        if quadruples:
            df_quads = pd.DataFrame([
                {
                    "#": q.get("index"),
                    "Operator": q.get("op"),
                    "Arg 1": q.get("arg1") if q.get("arg1") is not None else "-",
                    "Arg 2": q.get("arg2") if q.get("arg2") is not None else "-",
                    "Result": q.get("result") if q.get("result") is not None else "-"
                }
                for q in quadruples
            ])
            render_dataframe(df_quads)
        else:
            st.info("No quadruples generated.")

    # -------------------------------------------------------------------------
    # Tab 4: Triples Table
    # -------------------------------------------------------------------------
    with tab_triples:
        st.markdown("#### Triples Table")
        st.caption("Memory-efficient 3-tuple representation: references intermediate values using tuple index (i).")
        if triples:
            df_triples = pd.DataFrame([
                {
                    "(i)": f"({t.get('index')})",
                    "Operator": t.get("op"),
                    "Arg 1": t.get("arg1") if t.get("arg1") is not None else "-",
                    "Arg 2": t.get("arg2") if t.get("arg2") is not None else "-"
                }
                for t in triples
            ])
            render_dataframe(df_triples)
        else:
            st.info("No triples generated.")

    # -------------------------------------------------------------------------
    # Tab 5: Basic Blocks Breakdown
    # -------------------------------------------------------------------------
    with tab_blocks:
        st.markdown(f"#### Decomposed Basic Blocks ({len(blocks)} Blocks Total)")
        st.caption("Each basic block has a single entry point (leader) and a single exit point.")

        for bid, bdata in blocks.items():
            is_entry = bdata.get("is_entry", False)
            is_exit = bdata.get("is_exit", False)
            leader_idx = bdata.get("leader_index")
            preds = bdata.get("predecessors", [])
            succs = bdata.get("successors", [])

            tags = []
            if is_entry:
                tags.append("ENTRY")
            if is_exit:
                tags.append("EXIT")
            tag_text = f" [{', '.join(tags)}]" if tags else ""

            title = f"Basic Block {bid}{tag_text} &bull; Leader #{leader_idx} &bull; Preds: {preds} &bull; Succs: {succs}"
            with st.expander(title, expanded=True):
                code_lines = bdata.get("code_lines", [])
                if code_lines:
                    for cl in code_lines:
                        st.code(cl, language="c")
                else:
                    st.caption("(Empty Block)")

    # -------------------------------------------------------------------------
    # Tab 6: Abstract Syntax Tree (AST)
    # -------------------------------------------------------------------------
    with tab_ast:
        st.markdown("#### Abstract Syntax Tree (Input to ICG)")
        st.caption("The syntax tree parsed during Phase 2 that drives the recursive SDD traversal.")
        ast_dict = parse_res.get("parse_tree")
        if ast_dict:
            dot_ast = generate_graphviz_tree(ast_dict)
            st.graphviz_chart(dot_ast, use_container_width=True)
        else:
            st.info("No AST available.")


if __name__ == "__main__":
    main()
