"""cfg_viz.py - Native Graphviz renderer for Control Flow Graphs (CFG).

Generates a publication-quality Graphviz Digraph from CFG basic blocks and directed edges
for native rendering via st.graphviz_chart.
"""

import graphviz
from typing import Dict, Any


def generate_graphviz_cfg(cfg_data: Dict[str, Any]) -> graphviz.Digraph:
    """Build a styled Graphviz Digraph from CFG dictionary.
    
    Args:
        cfg_data: Dictionary produced by ControlFlowGraph.to_dict()
        
    Returns:
        graphviz.Digraph configured with dark-theme styling, basic block boxes, and colored branch edges.
    """
    dot = graphviz.Digraph(comment="Control Flow Graph (CFG)")
    dot.attr(rankdir="TB")
    dot.attr(bgcolor="transparent")

    if not cfg_data or "blocks" not in cfg_data:
        dot.node("empty", "No CFG blocks available", shape="box", style="rounded,filled", fillcolor="#1E1B4B", fontcolor="white")
        return dot

    blocks = cfg_data.get("blocks", {})
    edges = cfg_data.get("edges", [])

    # -------------------------------------------------------------
    # Render Basic Block Nodes
    # -------------------------------------------------------------
    for bid, bdata in blocks.items():
        is_entry = bdata.get("is_entry", False)
        is_exit = bdata.get("is_exit", False)
        code_lines = bdata.get("code_lines", [])

        # Build label with block ID header and instructions
        tags = []
        if is_entry:
            tags.append("ENTRY")
        if is_exit:
            tags.append("EXIT")
        tag_str = f" [{', '.join(tags)}]" if tags else ""

        header = f"=== {bid}{tag_str} ==="
        body_lines = []
        for idx, line in enumerate(code_lines):
            leader_mark = "★ " if idx == 0 and bdata.get("leader_index") is not None else "  "
            body_lines.append(f"{leader_mark}{line}")

        body_text = "\n".join(body_lines) if body_lines else "  (empty block)"
        full_label = f"{header}\n\n{body_text}\n"

        # Node styling:
        border_color = "#06B6D4" if is_entry else ("#EF4444" if is_exit else "#4F46E5")
        penwidth = "2.5" if (is_entry or is_exit) else "1.8"

        dot.node(
            bid,
            label=full_label,
            shape="box",
            style="rounded,filled",
            fillcolor="#1E1B4B",
            color=border_color,
            fontcolor="#F8FAFC",
            fontname="Courier, Consolas, monospace",
            fontsize="11",
            penwidth=penwidth,
        )

    # -------------------------------------------------------------
    # Render Directed Edges
    # -------------------------------------------------------------
    for edge in edges:
        from_b = edge.get("from")
        to_b = edge.get("to")
        edge_type = edge.get("type", "fall-through")
        cond = edge.get("condition")

        if not from_b or not to_b:
            continue

        if edge_type == "branch-true":
            color = "#10B981"
            lbl = f"true ({cond})" if cond else "true"
            penwidth = "2.2"
        elif edge_type == "branch-false":
            color = "#EF4444"
            lbl = f"false ({cond})" if cond else "false"
            penwidth = "2.2"
        elif edge_type == "unconditional-jump":
            color = "#A855F7"
            lbl = "goto"
            penwidth = "2.0"
        else:  # fall-through
            color = "#06B6D4"
            lbl = "fall-through"
            penwidth = "1.5"

        dot.edge(
            from_b,
            to_b,
            label=f" {lbl} ",
            color=color,
            fontcolor=color,
            fontsize="10",
            fontname="sans-serif",
            penwidth=penwidth,
            arrowsize="0.85",
        )

    return dot
