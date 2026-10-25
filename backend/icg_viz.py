"""icg_viz.py - Streamlit integration component for Phase 4 ICG Visualizer.

Provides HTML embedding for the interactive Intermediate Code Generator visualizer
directly inside Streamlit tabs and dialogs.
"""

import json
from pathlib import Path


def get_standalone_visualizer_html(initial_code=None, ast_json=None):
    """Generate self-contained HTML for embedding the ICG visualizer inside Streamlit."""
    visualizer_dir = Path(__file__).resolve().parent.parent / "visualizer"
    
    style_path = visualizer_dir / "style.css"
    html_path = visualizer_dir / "index.html"
    ir_structs_path = visualizer_dir / "IRStructures.js"
    parser_path = visualizer_dir / "ToyLangParser.js"
    visitor_path = visualizer_dir / "ICGVisitor.js"
    vis_path = visualizer_dir / "Visualizer.js"

    style_content = style_path.read_text(encoding="utf-8") if style_path.exists() else ""
    ir_structs_content = ir_structs_path.read_text(encoding="utf-8") if ir_structs_path.exists() else ""
    parser_content = parser_path.read_text(encoding="utf-8") if parser_path.exists() else ""
    visitor_content = visitor_path.read_text(encoding="utf-8") if visitor_path.exists() else ""
    vis_content = vis_path.read_text(encoding="utf-8") if vis_path.exists() else ""

    # Replace ES module imports/exports for inline execution inside iframe
    bundled_ir_structs = ir_structs_content.replace("export class ", "class ").replace("export const ", "const ")
    bundled_parser = parser_content.replace("export class ", "class ")
    bundled_visitor = visitor_content.replace(
        'import {\n    TempAllocator,\n    LabelGenerator,\n    Quadruple,\n    Triple,\n    ThreeAddressInstruction,\n    InstructionType,\n    BasicBlock,\n    CFGEdge,\n    ControlFlowGraph\n} from "./IRStructures.js";',
        ''
    ).replace("export class ", "class ")
    
    bundled_vis = vis_content.replace(
        'import { ICGVisitor } from "./ICGVisitor.js";\nimport { ToyLangParser } from "./ToyLangParser.js";',
        ''
    ).replace("export class ", "class ")

    # If custom initial code passed, inject it
    code_init_script = ""
    if initial_code:
        escaped_code = json.dumps(initial_code)
        code_init_script = f"""
        setTimeout(() => {{
            const editor = document.getElementById('source-editor');
            if (editor) {{
                editor.value = {escaped_code};
                if (window.visualizer) {{
                    window.visualizer.compileAndRender();
                }}
            }}
        }}, 150);
        """

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
{style_content}
    </style>
</head>
<body>
    <div class="app-container" style="padding: 10px; max-width: 100%;">
        <!-- Header -->
        <header class="app-header">
            <div class="brand-wrapper">
                <div class="brand-icon">⚡</div>
                <div>
                    <h1 class="brand-title">Intermediate Code Generator (ICG)</h1>
                    <p class="brand-subtitle">Educational Compiler Pipeline &bull; Phase 4 &bull; 3AC &bull; Quadruples &bull; Triples &bull; CFG</p>
                </div>
            </div>
            <div class="header-badges">
                <span class="phase-badge">Phase 4 Interactive</span>
            </div>
        </header>

        <!-- Toolbar & Statistics -->
        <section class="toolbar-section">
            <div class="sample-controls">
                <label for="sample-select">Load Test Case:</label>
                <select id="sample-select" class="select-input">
                    <option value="arithmetic">1. Arithmetic & Expression (a + b * 2)</option>
                    <option value="if_else">2. If-Else Branching (if / else)</option>
                    <option value="while_loop">3. While Loop (sum accumulation)</option>
                    <option value="nested_logic">4. Nested Control Flow (while + if/else)</option>
                    <option value="multi_expr">5. Multi-operator Expression</option>
                </select>
                <button id="btn-generate" class="btn btn-primary">Generate IR &amp; CFG</button>
                <button id="btn-reset" class="btn btn-secondary">Reset</button>
            </div>

            <div class="stats-grid">
                <div class="stat-pill">
                    <span class="stat-label">3AC Code:</span>
                    <span id="stat-3ac" class="stat-val">0 lines</span>
                </div>
                <div class="stat-pill">
                    <span class="stat-label">Temporaries:</span>
                    <span id="stat-temps" class="stat-val">0</span>
                </div>
                <div class="stat-pill">
                    <span class="stat-label">Labels:</span>
                    <span id="stat-labels" class="stat-val">0</span>
                </div>
                <div class="stat-pill">
                    <span class="stat-label">Basic Blocks:</span>
                    <span id="stat-blocks" class="stat-val">0</span>
                </div>
            </div>
        </section>

        <!-- Main Layout -->
        <main class="main-layout" style="grid-template-columns: 380px 1fr;">
            <!-- Left Column: Source Editor & Stepper -->
            <div class="left-column">
                <div class="card editor-card">
                    <div class="card-header">
                        <h2 class="card-title">📝 ToyLang Source Editor</h2>
                    </div>
                    <div class="editor-container">
                        <textarea id="source-editor" class="code-textarea" spellcheck="false" placeholder="Write ToyLang statements here..."></textarea>
                    </div>
                </div>

                <div class="card stepper-card">
                    <div class="card-header">
                        <h2 class="card-title">⏱️ Execution Stepper</h2>
                        <span id="step-display" class="stat-val">Step 0 / 0</span>
                    </div>

                    <div class="stepper-panel">
                        <div class="stepper-transport">
                            <div class="transport-buttons">
                                <button id="btn-first" class="btn-icon" title="First step">&vert;&lt;</button>
                                <button id="btn-prev" class="btn-icon" title="Previous step">&lt;</button>
                                <button id="btn-play" class="btn btn-play" title="Play / Pause">▶ Play</button>
                                <button id="btn-next" class="btn-icon" title="Next step">&gt;</button>
                                <button id="btn-last" class="btn-icon" title="Last step">&gt;&vert;</button>
                            </div>
                            <div class="speed-control">
                                <span>Speed:</span>
                                <select id="speed-select" class="select-input">
                                    <option value="0.5">0.5x</option>
                                    <option value="1" selected>1.0x</option>
                                    <option value="2">2.0x</option>
                                </select>
                            </div>
                        </div>

                        <div class="slider-wrapper">
                            <input type="range" id="step-slider" class="step-slider" min="0" max="0" value="0">
                        </div>

                        <div id="step-action-text" class="step-explanation-box">
                            Click 'Generate IR' or step through to begin execution.
                        </div>

                        <div class="registers-section">
                            <div class="reg-box">
                                <span class="reg-label">Temp Allocator (t0, t1...)</span>
                                <div id="temps-container" class="chips-container">
                                    <span class="empty-state">None</span>
                                </div>
                            </div>
                            <div class="reg-box">
                                <span class="reg-label">Label Generator (L0, L1...)</span>
                                <div id="labels-container" class="chips-container">
                                    <span class="empty-state">None</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Right Column: Tabbed Output Views -->
            <div class="right-column card">
                <nav class="tabs-header">
                    <button class="tab-btn active" data-tab="3ac">⚡ Three-Address Code (3AC)</button>
                    <button class="tab-btn" data-tab="quads">📋 Quadruples Table</button>
                    <button class="tab-btn" data-tab="triples">🔢 Triples Table</button>
                    <button class="tab-btn" data-tab="cfg">🕸️ Control Flow Graph (CFG)</button>
                    <button class="tab-btn" data-tab="ast">🌳 AST Tree View</button>
                </nav>

                <div class="tab-content-area">
                    <div id="tab-3ac" class="tab-pane active">
                        <div id="view-3ac"></div>
                    </div>
                    <div id="tab-quads" class="tab-pane">
                        <div id="view-quads"></div>
                    </div>
                    <div id="tab-triples" class="tab-pane">
                        <div id="view-triples"></div>
                    </div>
                    <div id="tab-cfg" class="tab-pane">
                        <div id="view-cfg"></div>
                    </div>
                    <div id="tab-ast" class="tab-pane">
                        <div id="view-ast"></div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
{bundled_ir_structs}
{bundled_parser}
{bundled_visitor}
{bundled_vis}
{code_init_script}
    </script>
</body>
</html>"""
    return full_html
