/**
 * Visualizer.js - Interactive UI controller, SVG CFG renderer, and execution stepper.
 * 
 * Separates presentation logic from IR generation:
 * - Tabbed output switching
 * - 3AC syntax highlighting & leader tagging
 * - Formatted Quadruples & Triples tables
 * - Interactive SVG Control Flow Graph with curved directed edges
 * - Step-by-step playback slider & animation controller
 */

import { ICGVisitor } from "./ICGVisitor.js";
import { ToyLangParser } from "./ToyLangParser.js";

export class Visualizer {
    constructor() {
        this.visitor = new ICGVisitor();
        this.currentResult = null;
        this.currentStep = 0;
        this.isPlaying = false;
        this.playTimer = null;
        this.playbackSpeed = 1000; // ms

        // DOM Elements
        this.sourceEditor = document.getElementById("source-editor");
        this.sampleSelect = document.getElementById("sample-select");
        this.btnGenerate = document.getElementById("btn-generate");
        this.btnReset = document.getElementById("btn-reset");

        // Stat Pills
        this.stat3ac = document.getElementById("stat-3ac");
        this.statTemps = document.getElementById("stat-temps");
        this.statLabels = document.getElementById("stat-labels");
        this.statBlocks = document.getElementById("stat-blocks");

        // Stepper Controls
        this.stepSlider = document.getElementById("step-slider");
        this.stepDisplay = document.getElementById("step-display");
        this.stepActionText = document.getElementById("step-action-text");
        this.btnPlay = document.getElementById("btn-play");
        this.btnPrev = document.getElementById("btn-prev");
        this.btnNext = document.getElementById("btn-next");
        this.btnFirst = document.getElementById("btn-first");
        this.btnLast = document.getElementById("btn-last");
        this.speedSelect = document.getElementById("speed-select");

        // Live Registers
        this.tempsContainer = document.getElementById("temps-container");
        this.labelsContainer = document.getElementById("labels-container");

        // Tab Views
        this.view3ac = document.getElementById("view-3ac");
        this.viewQuads = document.getElementById("view-quads");
        this.viewTriples = document.getElementById("view-triples");
        this.viewCfg = document.getElementById("view-cfg");
        this.viewAst = document.getElementById("view-ast");

        this.initEventListeners();
        this.loadSample(this.sampleSelect.value);
    }

    initEventListeners() {
        this.btnGenerate.addEventListener("click", () => this.compileAndRender());
        this.btnReset.addEventListener("click", () => {
            this.loadSample(this.sampleSelect.value);
        });

        this.sampleSelect.addEventListener("change", (e) => {
            this.loadSample(e.target.value);
        });

        // Tabs
        const tabBtns = document.querySelectorAll(".tab-btn");
        tabBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                tabBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                const target = btn.dataset.tab;
                document.querySelectorAll(".tab-pane").forEach(pane => {
                    pane.classList.remove("active");
                });
                const targetPane = document.getElementById(`tab-${target}`);
                if (targetPane) targetPane.classList.add("active");
            });
        });

        // Stepper
        this.stepSlider.addEventListener("input", (e) => {
            this.pause();
            this.goToStep(parseInt(e.target.value, 10));
        });

        this.btnPlay.addEventListener("click", () => {
            if (this.isPlaying) this.pause();
            else this.play();
        });

        this.btnPrev.addEventListener("click", () => {
            this.pause();
            if (this.currentStep > 0) this.goToStep(this.currentStep - 1);
        });

        this.btnNext.addEventListener("click", () => {
            this.pause();
            if (this.currentResult && this.currentStep < this.currentResult.steps.length - 1) {
                this.goToStep(this.currentStep + 1);
            }
        });

        this.btnFirst.addEventListener("click", () => {
            this.pause();
            this.goToStep(0);
        });

        this.btnLast.addEventListener("click", () => {
            this.pause();
            if (this.currentResult) {
                this.goToStep(this.currentResult.steps.length - 1);
            }
        });

        this.speedSelect.addEventListener("change", (e) => {
            const mult = parseFloat(e.target.value);
            this.playbackSpeed = 1000 / mult;
            if (this.isPlaying) {
                this.pause();
                this.play();
            }
        });
    }

    loadSample(sampleKey) {
        const samples = {
            "arithmetic": `int a = 10;\nint b = 20;\nint c = a + b * 2;`,
            "if_else": `int a = 5;\nint b = 10;\nint x = 0;\nif (a < b) {\n    x = 1;\n} else {\n    x = 2;\n}`,
            "while_loop": `int i = 0;\nint sum = 0;\nwhile (i < 10) {\n    sum = sum + i;\n    i = i + 1;\n}`,
            "nested_logic": `int count = 0;\nwhile (count < 5) {\n    if (count == 2) {\n        count = count + 2;\n    } else {\n        count = count + 1;\n    }\n}`,
            "multi_expr": `int a = 8;\nint b = 4;\nint c = 2;\nint res = (a + b) * (c - 1) / 2;`
        };

        if (samples[sampleKey]) {
            this.sourceEditor.value = samples[sampleKey];
            this.compileAndRender();
        }
    }

    compileAndRender() {
        this.pause();
        const source = this.sourceEditor.value.trim();
        if (!source) return;

        try {
            const parser = new ToyLangParser(source);
            const ast = parser.parse();
            this.currentResult = this.visitor.generate(ast);
            this.currentStep = 0;

            // Update stats
            this.stat3ac.textContent = `${this.currentResult.instructions.length} lines`;
            this.statTemps.textContent = `${this.currentResult.tempCount} allocated`;
            this.statLabels.textContent = `${this.currentResult.labelCount} generated`;
            this.statBlocks.textContent = `${this.currentResult.cfg.blocks.size} blocks`;

            // Setup Stepper Slider
            const maxStep = Math.max(0, this.currentResult.steps.length - 1);
            this.stepSlider.min = 0;
            this.stepSlider.max = maxStep;
            this.stepSlider.value = 0;

            // Render all views
            this.render3ACView();
            this.renderQuadruplesTable();
            this.renderTriplesTable();
            this.renderCFGDiagram();
            this.renderASTView(ast);

            this.goToStep(0);
        } catch (err) {
            console.error("Compilation error:", err);
            alert("Compilation error: " + err.message);
        }
    }

    goToStep(stepIndex) {
        if (!this.currentResult || !this.currentResult.steps || this.currentResult.steps.length === 0) return;
        this.currentStep = Math.max(0, Math.min(stepIndex, this.currentResult.steps.length - 1));
        this.stepSlider.value = this.currentStep;
        this.stepDisplay.textContent = `Step ${this.currentStep + 1} / ${this.currentResult.steps.length}`;

        const step = this.currentResult.steps[this.currentStep];
        this.stepActionText.innerHTML = `<strong>[${step.nodeName}]</strong> ${step.action}`;

        // Update live registers
        this.updateRegisters(step.temps, step.labels);

        // Highlight synchronized IR lines & rows
        this.highlightActiveStep(step);
    }

    play() {
        if (!this.currentResult) return;
        this.isPlaying = true;
        this.btnPlay.innerHTML = "⏸ Pause";
        this.btnPlay.classList.add("playing");

        this.playTimer = setInterval(() => {
            if (this.currentStep < this.currentResult.steps.length - 1) {
                this.goToStep(this.currentStep + 1);
            } else {
                this.pause();
            }
        }, this.playbackSpeed);
    }

    pause() {
        this.isPlaying = false;
        if (this.playTimer) {
            clearInterval(this.playTimer);
            this.playTimer = null;
        }
        this.btnPlay.innerHTML = "▶ Play";
        this.btnPlay.classList.remove("playing");
    }

    updateRegisters(temps, labels) {
        this.tempsContainer.innerHTML = "";
        if (temps.length === 0) {
            this.tempsContainer.innerHTML = `<span class="empty-state">None</span>`;
        } else {
            temps.forEach((t, i) => {
                const chip = document.createElement("span");
                chip.className = `reg-chip temp-chip ${i === temps.length - 1 ? 'just-allocated' : ''}`;
                chip.textContent = t;
                this.tempsContainer.appendChild(chip);
            });
        }

        this.labelsContainer.innerHTML = "";
        if (labels.length === 0) {
            this.labelsContainer.innerHTML = `<span class="empty-state">None</span>`;
        } else {
            labels.forEach((l, i) => {
                const chip = document.createElement("span");
                chip.className = `reg-chip label-chip ${i === labels.length - 1 ? 'just-allocated' : ''}`;
                chip.textContent = l;
                this.labelsContainer.appendChild(chip);
            });
        }
    }

    highlightActiveStep(step) {
        // Highlight active 3AC line
        const irLines = document.querySelectorAll(".tac-line");
        irLines.forEach(line => line.classList.remove("active-ir-line"));
        if (step.instructionIndex !== null && step.instructionIndex !== undefined) {
            const activeLine = document.querySelector(`.tac-line[data-idx="${step.instructionIndex}"]`);
            if (activeLine) {
                activeLine.classList.add("active-ir-line");
                activeLine.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
        }

        // Highlight Quadruple row
        const quadRows = document.querySelectorAll(".quad-row");
        quadRows.forEach(row => row.classList.remove("active-row"));
        if (step.instructionIndex !== null && step.instructionIndex !== undefined) {
            const activeQuad = document.querySelector(`.quad-row[data-idx="${step.instructionIndex}"]`);
            if (activeQuad) {
                activeQuad.classList.add("active-row");
                activeQuad.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
        }

        // Highlight Triple row
        const tripRows = document.querySelectorAll(".triple-row");
        tripRows.forEach(row => row.classList.remove("active-row"));
        if (step.triple && step.triple[0] !== undefined) {
            const activeTrip = document.querySelector(`.triple-row[data-idx="${step.triple[0]}"]`);
            if (activeTrip) {
                activeTrip.classList.add("active-row");
                activeTrip.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
        }

        // Highlight AST node
        const treeNodes = document.querySelectorAll(".tree-node-item");
        treeNodes.forEach(node => node.classList.remove("active-ast-node"));
        if (step.astNodeId) {
            const activeAst = document.getElementById(step.astNodeId);
            if (activeAst) {
                activeAst.classList.add("active-ast-node");
                activeAst.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
        }
    }

    render3ACView() {
        const instructions = this.currentResult.instructions;
        if (!instructions || instructions.length === 0) {
            this.view3ac.innerHTML = `<div class="empty-state">No intermediate code generated.</div>`;
            return;
        }

        let html = `<div class="tac-container">`;
        instructions.forEach(inst => {
            const leaderBadge = inst.isLeader
                ? `<span class="leader-badge" title="Basic Block Leader">[LEADER]</span>`
                : `<span class="leader-placeholder"></span>`;
            
            const formattedCode = this.syntaxHighlight3AC(inst.formatCode());
            const comment = inst.comment ? `<span class="code-comment"># ${inst.comment}</span>` : "";

            html += `
            <div class="tac-line" data-idx="${inst.index}">
                <span class="line-num">${String(inst.index).padStart(2, ' ')}</span>
                ${leaderBadge}
                <span class="code-body">${formattedCode}</span>
                ${comment}
            </div>`;
        });
        html += `</div>`;
        this.view3ac.innerHTML = html;
    }

    syntaxHighlight3AC(code) {
        // Escape HTML entities first
        const safe = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        // Tokenize using a single combined regex so replacement spans aren't re-matched
        return safe.replace(/\b(goto|ifFalse|ifTrue|if|print|return)\b|\b(t\d+)\b|\b(L\d+):?|\b(\d+(?:\.\d+)?)\b|(&lt;=|&gt;=|==|!=|&lt;|&gt;|\+|-|\*|\/|%|=)/g, (match, kw, temp, label, num, op) => {
            if (kw) return `<span class="kw">${kw}</span>`;
            if (temp) return `<span class="temp">${temp}</span>`;
            if (label) return `<span class="label">${label}</span>`;
            if (num) return `<span class="num">${num}</span>`;
            if (op) return `<span class="op">${op}</span>`;
            return match;
        });
    }

    renderQuadruplesTable() {
        const quads = this.currentResult.quadruples;
        if (!quads || quads.length === 0) {
            this.viewQuads.innerHTML = `<div class="empty-state">No quadruples available.</div>`;
            return;
        }

        let html = `
        <div class="table-responsive">
            <table class="ir-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Operator (op)</th>
                        <th>Argument 1 (arg1)</th>
                        <th>Argument 2 (arg2)</th>
                        <th>Result (result)</th>
                    </tr>
                </thead>
                <tbody>
        `;

        quads.forEach(q => {
            const opBadge = `<span class="badge op-badge">${q.op}</span>`;
            const a1 = q.arg1 !== null ? `<span class="val-badge">${q.arg1}</span>` : `<span class="dash">-</span>`;
            const a2 = q.arg2 !== null ? `<span class="val-badge">${q.arg2}</span>` : `<span class="dash">-</span>`;
            const res = q.result !== null ? `<span class="badge res-badge">${q.result}</span>` : `<span class="dash">-</span>`;

            html += `
                <tr class="quad-row" data-idx="${q.index}">
                    <td class="idx-cell">${q.index}</td>
                    <td>${opBadge}</td>
                    <td>${a1}</td>
                    <td>${a2}</td>
                    <td>${res}</td>
                </tr>
            `;
        });

        html += `</tbody></table></div>`;
        this.viewQuads.innerHTML = html;
    }

    renderTriplesTable() {
        const triples = this.currentResult.triples;
        if (!triples || triples.length === 0) {
            this.viewTriples.innerHTML = `<div class="empty-state">No triples available.</div>`;
            return;
        }

        let html = `
        <div class="table-responsive">
            <table class="ir-table">
                <thead>
                    <tr>
                        <th>(i)</th>
                        <th>Operator</th>
                        <th>Argument 1</th>
                        <th>Argument 2</th>
                    </tr>
                </thead>
                <tbody>
        `;

        triples.forEach(t => {
            const opBadge = `<span class="badge op-badge">${t.op}</span>`;
            const formatTripleVal = (v) => {
                if (v === null || v === undefined) return `<span class="dash">-</span>`;
                if (/^\(\d+\)$/.test(v)) {
                    return `<span class="triple-ref" title="Back-reference to triple ${v}">${v}</span>`;
                }
                return `<span class="val-badge">${v}</span>`;
            };

            html += `
                <tr class="triple-row" data-idx="${t.index}">
                    <td class="idx-cell"><strong>(${t.index})</strong></td>
                    <td>${opBadge}</td>
                    <td>${formatTripleVal(t.arg1)}</td>
                    <td>${formatTripleVal(t.arg2)}</td>
                </tr>
            `;
        });

        html += `</tbody></table></div>`;
        this.viewTriples.innerHTML = html;
    }

    /**
     * SVG Control Flow Graph Renderer with basic block cards & curved directed arrows.
     */
    renderCFGDiagram() {
        const cfg = this.currentResult.cfg;
        if (!cfg || cfg.blocks.size === 0) {
            this.viewCfg.innerHTML = `<div class="empty-state">No CFG generated.</div>`;
            return;
        }

        const blocksArray = Array.from(cfg.blocks.values());
        const blockPositions = new Map();

        const cardWidth = 240;
        const baseCardHeight = 85;
        const gapY = 80;
        const centerX = 240;
        const leftX = 70;
        const rightX = 410;

        // Check for 2-way branch targets
        const branchLeft = new Set();
        const branchRight = new Set();
        blocksArray.forEach(b => {
            if (b.successors.length === 2) {
                // If the second successor jumps forward to another block
                branchLeft.add(b.successors[0]);
                branchRight.add(b.successors[1]);
            }
        });

        let currentY = 30;
        for (let i = 0; i < blocksArray.length; i++) {
            const b = blocksArray[i];
            const height = Math.max(baseCardHeight, 50 + b.instructions.length * 20);

            let posX = centerX;
            if (branchLeft.has(b.id) && !branchRight.has(b.id)) {
                posX = leftX;
            } else if (branchRight.has(b.id) && !branchLeft.has(b.id)) {
                posX = rightX;
            }

            // If this block is placed on the right and previous was on left at same level:
            if (posX === rightX && i > 0 && blockPositions.has(blocksArray[i - 1].id) && branchLeft.has(blocksArray[i - 1].id)) {
                const prevPos = blockPositions.get(blocksArray[i - 1].id);
                blockPositions.set(b.id, {
                    x: posX,
                    y: prevPos.y,
                    width: cardWidth,
                    height: height
                });
                currentY = Math.max(currentY, prevPos.y + Math.max(height, prevPos.height) + gapY);
                continue;
            }

            blockPositions.set(b.id, {
                x: posX,
                y: currentY,
                width: cardWidth,
                height: height
            });

            currentY += height + gapY;
        }

        const totalWidth = 740;
        const totalHeight = Math.max(currentY + 40, 500);

        let svgHtml = `
        <div class="cfg-viewport">
            <svg class="cfg-svg" width="100%" height="${totalHeight}" viewBox="0 0 ${totalWidth} ${totalHeight}">
                <defs>
                    <!-- Markers for edge types -->
                    <marker id="arrow-fall-through" markerWidth="10" markerHeight="10" refX="7" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#06b6d4" />
                    </marker>
                    <marker id="arrow-branch-true" markerWidth="10" markerHeight="10" refX="7" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#10b981" />
                    </marker>
                    <marker id="arrow-branch-false" markerWidth="10" markerHeight="10" refX="7" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#ef4444" />
                    </marker>
                    <marker id="arrow-unconditional-jump" markerWidth="10" markerHeight="10" refX="7" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#a855f7" />
                    </marker>
                </defs>
        `;

        // Render Directed Edges
        cfg.edges.forEach(edge => {
            const src = blockPositions.get(edge.from);
            const dst = blockPositions.get(edge.to);
            if (!src || !dst) return;

            let strokeColor = "#06b6d4";
            let marker = "arrow-fall-through";

            if (edge.type === "branch-true") {
                strokeColor = "#10b981";
                marker = "arrow-branch-true";
            } else if (edge.type === "branch-false") {
                strokeColor = "#ef4444";
                marker = "arrow-branch-false";
            } else if (edge.type === "unconditional-jump") {
                strokeColor = "#a855f7";
                marker = "arrow-unconditional-jump";
            }

            // Route edge: if dst.y <= src.y, it's a loop back edge! Route around the left side
            let pathD = "";
            let labelX = 0;
            let labelY = 0;

            if (dst.y <= src.y) {
                // Loop back-edge: route on the left
                const x1 = src.x;
                const y1 = src.y + src.height / 2;
                const x2 = dst.x;
                const y2 = dst.y + dst.height / 2;
                const loopX = Math.min(x1, x2) - 100;

                pathD = `M ${x1} ${y1} C ${loopX} ${y1}, ${loopX} ${y2}, ${x2} ${y2}`;
                labelX = loopX + 15;
                labelY = (y1 + y2) / 2;
            } else {
                // Forward edge: smooth bezier from bottom of src to top of dst
                const x1 = src.x + src.width / 2;
                const y1 = src.y + src.height;
                const x2 = dst.x + dst.width / 2;
                const y2 = dst.y;

                if (edge.type === "branch-false") {
                    // Route right side
                    const cX = Math.max(x1, x2) + 70;
                    pathD = `M ${src.x + src.width} ${src.y + src.height - 15} C ${cX} ${src.y + src.height}, ${cX} ${dst.y}, ${dst.x + dst.width} ${dst.y + 20}`;
                    labelX = cX + 5;
                    labelY = (src.y + dst.y) / 2;
                } else {
                    const midY = (y1 + y2) / 2;
                    pathD = `M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}`;
                    labelX = (x1 + x2) / 2 + 10;
                    labelY = midY - 5;
                }
            }

            svgHtml += `
                <g class="cfg-edge-group">
                    <path d="${pathD}" fill="none" stroke="${strokeColor}" stroke-width="2.5" marker-end="url(#${marker})" stroke-dasharray="${edge.type.includes('branch') ? 'none' : 'none'}" />
                    <text x="${labelX}" y="${labelY}" fill="${strokeColor}" font-size="11" font-weight="600" class="edge-label">${edge.type}${edge.condition ? ' (' + edge.condition + ')' : ''}</text>
                </g>
            `;
        });

        // Render Basic Block Cards
        blocksArray.forEach(b => {
            const pos = blockPositions.get(b.id);
            const entryBadge = b.isEntry ? `<span class="badge entry-badge">ENTRY</span>` : "";
            const exitBadge = b.isExit ? `<span class="badge exit-badge">EXIT</span>` : "";

            let instructionsHtml = "";
            b.instructions.forEach(inst => {
                const isLeader = inst.isLeader ? `<span class="mini-leader">★</span>` : "";
                instructionsHtml += `<div class="block-code-line">${isLeader} ${inst.formatCode()}</div>`;
            });

            svgHtml += `
                <foreignObject x="${pos.x}" y="${pos.y}" width="${pos.width}" height="${pos.height}">
                    <div xmlns="http://www.w3.org/1999/xhtml" class="cfg-block-card ${b.isEntry ? 'is-entry' : ''} ${b.isExit ? 'is-exit' : ''}" id="cfg-${b.id}">
                        <div class="block-header">
                            <span class="block-id">${b.id}</span>
                            <div class="block-badges">${entryBadge} ${exitBadge}</div>
                        </div>
                        <div class="block-body">
                            ${instructionsHtml}
                        </div>
                    </div>
                </foreignObject>
            `;
        });

        svgHtml += `</svg></div>`;
        this.viewCfg.innerHTML = svgHtml;
    }

    renderASTView(ast) {
        if (!ast) {
            this.viewAst.innerHTML = `<div class="empty-state">No AST available.</div>`;
            return;
        }

        const buildTreeHtml = (node) => {
            if (!node) return "";
            const hasChildren = node.children && node.children.length > 0;
            const badgeClass = node.name.startsWith("Operator") ? "tree-op" :
                               node.name.startsWith("Identifier") ? "tree-id" :
                               node.name.startsWith("Literal") ? "tree-lit" : "tree-stmt";

            let html = `
            <li class="tree-node-item" id="${node.nodeId || ''}">
                <div class="tree-node-content">
                    <span class="tree-badge ${badgeClass}">${node.name}</span>
                </div>
            `;

            if (hasChildren) {
                html += `<ul>`;
                for (const child of node.children) {
                    html += buildTreeHtml(child);
                }
                html += `</ul>`;
            }

            html += `</li>`;
            return html;
        };

        this.viewAst.innerHTML = `<div class="ast-tree-container"><ul class="tree-root">${buildTreeHtml(ast)}</ul></div>`;
    }
}

// Bootstrap once DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    window.visualizer = new Visualizer();
});
