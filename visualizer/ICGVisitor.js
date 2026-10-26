/**
 * ICGVisitor.js - Recursive SDD Tree Walker & Intermediate Code Generator for ToyLang.
 * 
 * Generates:
 * 1. Linear Three-Address Code (3AC)
 * 2. Quadruples table
 * 3. Triples table (with indexed back-references)
 * 4. Control Flow Graph (CFG) basic blocks & directed edges
 * 5. Execution trace steps for animated stepping visualization
 */

import {
    TempAllocator,
    LabelGenerator,
    Quadruple,
    Triple,
    ThreeAddressInstruction,
    InstructionType,
    BasicBlock,
    CFGEdge,
    ControlFlowGraph
} from "./IRStructures.js";

export class ICGVisitor {
    constructor() {
        this.tempAllocator = new TempAllocator();
        this.labelGenerator = new LabelGenerator();
        this.instructions = [];
        this.quadruples = [];
        this.triples = [];
        this.steps = [];
        this.tempToTripleIdx = new Map();
        this.nodeCounter = 0;
    }

    reset() {
        this.tempAllocator.reset();
        this.labelGenerator.reset();
        this.instructions = [];
        this.quadruples = [];
        this.triples = [];
        this.steps = [];
        this.tempToTripleIdx.clear();
        this.nodeCounter = 0;
    }

    /**
     * Generate IR representations and stepping trace from an AST.
     * @param {Object} ast AST node object or D3-compatible tree { name, children }
     * @returns {Object} Complete IR and visualization artifact
     */
    generate(ast) {
        this.reset();

        if (ast) {
            this._annotateNodeIds(ast);
            this._logStep(ast.name || "Root", "Beginning intermediate code generation traversal.", null, null, null, ast.nodeId);
            this._visit(ast);
        }

        const cfg = this._buildCFG();

        return {
            success: true,
            instructions: this.instructions,
            threeAddressCode: this.instructions.map(inst => inst.formatCode()),
            quadruples: this.quadruples,
            triples: this.triples,
            cfg: cfg,
            steps: this.steps,
            tempCount: this.tempAllocator.counter,
            labelCount: this.labelGenerator.counter
        };
    }

    _annotateNodeIds(node) {
        if (!node) return;
        node.nodeId = `ast_node_${this.nodeCounter++}`;
        if (node.children) {
            for (const child of node.children) {
                this._annotateNodeIds(child);
            }
        }
    }

    _formatTripleArg(arg) {
        if (arg === null || arg === undefined) return null;
        if (this.tempToTripleIdx.has(arg)) {
            return `(${this.tempToTripleIdx.get(arg)})`;
        }
        return String(arg);
    }

    _logStep(nodeName, action, inst = null, quad = null, trip = null, astNodeId = null) {
        this.steps.push({
            step: this.steps.length + 1,
            nodeName: nodeName,
            action: action,
            instruction: inst ? inst.formatCode() : null,
            instructionIndex: inst ? inst.index : null,
            quadruple: quad ? quad.toTuple() : null,
            triple: trip ? trip.toTuple() : null,
            temps: this.tempAllocator.allocated,
            labels: this.labelGenerator.generated,
            currentIrCount: this.instructions.length,
            astNodeId: astNodeId
        });
    }

    _emit({
        type,
        result = null,
        op = null,
        arg1 = null,
        arg2 = null,
        sourceLine = null,
        comment = null,
        nodeName = "",
        actionDesc = "",
        astNodeId = null
    }) {
        const idx = this.instructions.length;
        const inst = new ThreeAddressInstruction({
            type,
            result,
            op,
            arg1,
            arg2,
            index: idx,
            sourceLine,
            comment,
            astNodeId
        });
        this.instructions.push(inst);

        // Quadruple emission
        let quadOp = op || type.toLowerCase();
        let quad;
        if (type === InstructionType.LABEL) {
            quad = new Quadruple("label", null, null, result, idx);
        } else if (type === InstructionType.GOTO) {
            quad = new Quadruple("goto", null, null, result, idx);
        } else if (type === InstructionType.IF_FALSE_GOTO) {
            quad = new Quadruple("ifFalse", arg1, null, result, idx);
        } else if (type === InstructionType.IF_TRUE_GOTO) {
            quad = new Quadruple("ifTrue", arg1, null, result, idx);
        } else if (type === InstructionType.ASSIGN) {
            quad = new Quadruple("=", arg1, null, result, idx);
        } else if (type === InstructionType.UNARY_OP) {
            quad = new Quadruple(op || "-", arg1, null, result, idx);
        } else if (type === InstructionType.PRINT) {
            quad = new Quadruple("print", arg1, null, null, idx);
        } else if (type === InstructionType.RETURN) {
            quad = new Quadruple("return", arg1, null, null, idx);
        } else {
            quad = new Quadruple(op || "=", arg1, arg2, result, idx);
        }
        this.quadruples.push(quad);

        // Triple emission
        const tripIdx = this.triples.length;
        const tripA1 = this._formatTripleArg(arg1);
        const tripA2 = this._formatTripleArg(arg2);
        let trip;
        if (type === InstructionType.LABEL) {
            trip = new Triple(tripIdx, "label", result, null);
        } else if (type === InstructionType.GOTO) {
            trip = new Triple(tripIdx, "goto", result, null);
        } else if (type === InstructionType.IF_FALSE_GOTO) {
            trip = new Triple(tripIdx, "ifFalse", tripA1, result);
        } else if (type === InstructionType.IF_TRUE_GOTO) {
            trip = new Triple(tripIdx, "ifTrue", tripA1, result);
        } else if (type === InstructionType.ASSIGN) {
            trip = new Triple(tripIdx, "=", result, tripA1);
        } else if (type === InstructionType.PRINT) {
            trip = new Triple(tripIdx, "print", tripA1, null);
        } else if (type === InstructionType.RETURN) {
            trip = new Triple(tripIdx, "return", tripA1, null);
        } else {
            trip = new Triple(tripIdx, op || "=", tripA1, tripA2);
        }
        this.triples.push(trip);

        if (result && result.startsWith(this.tempAllocator.prefix)) {
            this.tempToTripleIdx.set(result, tripIdx);
        }

        this._logStep(
            nodeName || type,
            actionDesc || `Emitted instruction: ${inst.formatCode()}`,
            inst,
            quad,
            trip,
            astNodeId
        );

        return inst;
    }

    _visit(node) {
        if (!node) return null;
        const name = node.name || "";
        const children = node.children || [];

        // 1. Program & StatementList & Block
        if (name === "Program" || name === "StatementList" || name === "Block") {
            for (const child of children) {
                this._visit(child);
            }
            return null;
        }

        // 2. Variable Declaration
        if (name.startsWith("VarDeclaration (")) {
            const varName = this._extractIdentifier(children[0]);
            if (children.length > 1) {
                const exprVal = this._visit(children[1]);
                this._emit({
                    type: InstructionType.ASSIGN,
                    result: varName,
                    arg1: exprVal,
                    nodeName: name,
                    actionDesc: `Initialize '${varName}' with value '${exprVal}'`,
                    astNodeId: node.nodeId
                });
            } else {
                this._logStep(name, `Declared variable '${varName}' (uninitialized).`, null, null, null, node.nodeId);
            }
            return null;
        }

        // 3. Assignment
        if (name === "Assignment") {
            const varName = this._extractIdentifier(children[0]);
            const exprVal = this._visit(children[1]);
            this._emit({
                type: InstructionType.ASSIGN,
                result: varName,
                arg1: exprVal,
                nodeName: "Assignment",
                actionDesc: `Assign '${exprVal}' to '${varName}'`,
                astNodeId: node.nodeId
            });
            return null;
        }

        // 4. If Statement
        if (name === "IfStatement") {
            this._translateIf(node);
            return null;
        }

        // 5. While Statement
        if (name === "WhileStatement") {
            this._translateWhile(node);
            return null;
        }

        // 6. Print Statement
        if (name === "PrintStatement") {
            if (children.length > 0) {
                const val = this._visit(children[0]);
                this._emit({
                    type: InstructionType.PRINT,
                    arg1: val,
                    nodeName: "PrintStatement",
                    actionDesc: `Print output '${val}'`,
                    astNodeId: node.nodeId
                });
            }
            return null;
        }

        // 7. Return Statement
        if (name === "ReturnStatement") {
            const val = children.length > 0 ? this._visit(children[0]) : null;
            this._emit({
                type: InstructionType.RETURN,
                arg1: val,
                nodeName: "ReturnStatement",
                actionDesc: `Return (${val || 'void'})`,
                astNodeId: node.nodeId
            });
            return null;
        }

        // 8. Expression Statement
        if (name === "ExpressionStatement") {
            if (children.length > 0) {
                this._visit(children[0]);
            }
            return null;
        }

        // 9. Binary Operations
        if (name.startsWith("Operator: ")) {
            const op = name.substring("Operator: ".length).trim();
            const leftVal = this._visit(children[0]);
            const rightVal = this._visit(children[1]);
            const temp = this.tempAllocator.newTemp();
            this._emit({
                type: InstructionType.BINARY_OP,
                result: temp,
                op: op,
                arg1: leftVal,
                arg2: rightVal,
                nodeName: name,
                actionDesc: `Evaluated ${leftVal} ${op} ${rightVal} -> allocated ${temp}`,
                astNodeId: node.nodeId
            });
            return temp;
        }

        // 10. Unary Operations
        if (name.startsWith("Unary: ")) {
            const op = name.substring("Unary: ".length).trim();
            const operandVal = this._visit(children[0]);
            const temp = this.tempAllocator.newTemp();
            this._emit({
                type: InstructionType.UNARY_OP,
                result: temp,
                op: op,
                arg1: operandVal,
                nodeName: name,
                actionDesc: `Evaluated unary ${op}${operandVal} -> allocated ${temp}`,
                astNodeId: node.nodeId
            });
            return temp;
        }

        // 11. Identifiers
        if (name.startsWith("Identifier: ")) {
            return name.substring("Identifier: ".length).trim();
        }

        // 12. Literals
        if (name.startsWith("Literal: ")) {
            return name.substring("Literal: ".length).trim();
        }

        // Fallback
        for (const child of children) {
            this._visit(child);
        }
        return null;
    }

    _translateIf(node) {
        const children = node.children || [];
        let condNode = null;
        let thenNode = null;
        let elseNode = null;

        for (const child of children) {
            const cname = child.name || "";
            if (cname === "Condition") condNode = child;
            else if (cname === "Then") thenNode = child;
            else if (cname === "Else") elseNode = child;
            else if (cname === "Block") thenNode = child;
        }

        const condVal = condNode && condNode.children && condNode.children.length > 0
            ? this._visit(condNode.children[0])
            : null;

        if (elseNode) {
            const labelElse = this.labelGenerator.newLabel();
            const labelAfter = this.labelGenerator.newLabel();

            this._emit({
                type: InstructionType.IF_FALSE_GOTO,
                arg1: condVal,
                result: labelElse,
                nodeName: "IfStatement",
                actionDesc: `Condition test: if !(${condVal}) goto ${labelElse}`,
                astNodeId: node.nodeId
            });

            this._visit(thenNode);

            this._emit({
                type: InstructionType.GOTO,
                result: labelAfter,
                nodeName: "IfStatement",
                actionDesc: `Skip else block: goto ${labelAfter}`,
                astNodeId: node.nodeId
            });

            this._emit({
                type: InstructionType.LABEL,
                result: labelElse,
                nodeName: "Else",
                actionDesc: `Else branch entry: ${labelElse}:`,
                astNodeId: elseNode.nodeId
            });

            this._visit(elseNode);

            this._emit({
                type: InstructionType.LABEL,
                result: labelAfter,
                nodeName: "IfStatement",
                actionDesc: `If continuation label: ${labelAfter}:`,
                astNodeId: node.nodeId
            });
        } else {
            const labelAfter = this.labelGenerator.newLabel();

            this._emit({
                type: InstructionType.IF_FALSE_GOTO,
                arg1: condVal,
                result: labelAfter,
                nodeName: "IfStatement",
                actionDesc: `Condition test: if !(${condVal}) goto ${labelAfter}`,
                astNodeId: node.nodeId
            });

            this._visit(thenNode);

            this._emit({
                type: InstructionType.LABEL,
                result: labelAfter,
                nodeName: "IfStatement",
                actionDesc: `If exit label: ${labelAfter}:`,
                astNodeId: node.nodeId
            });
        }
    }

    _translateWhile(node) {
        const children = node.children || [];
        let condNode = null;
        let bodyNode = null;

        for (const child of children) {
            const cname = child.name || "";
            if (cname === "Condition") condNode = child;
            else if (cname === "Block") bodyNode = child;
        }

        const labelStart = this.labelGenerator.newLabel();
        const labelExit = this.labelGenerator.newLabel();

        this._emit({
            type: InstructionType.LABEL,
            result: labelStart,
            nodeName: "WhileStatement",
            actionDesc: `Loop header label: ${labelStart}:`,
            astNodeId: node.nodeId
        });

        const condVal = condNode && condNode.children && condNode.children.length > 0
            ? this._visit(condNode.children[0])
            : null;

        this._emit({
            type: InstructionType.IF_FALSE_GOTO,
            arg1: condVal,
            result: labelExit,
            nodeName: "WhileStatement",
            actionDesc: `Loop guard: if !(${condVal}) goto ${labelExit}`,
            astNodeId: node.nodeId
        });

        if (bodyNode) {
            this._visit(bodyNode);
        }

        this._emit({
            type: InstructionType.GOTO,
            result: labelStart,
            nodeName: "WhileStatement",
            actionDesc: `Loop loop-back: goto ${labelStart}`,
            astNodeId: node.nodeId
        });

        this._emit({
            type: InstructionType.LABEL,
            result: labelExit,
            nodeName: "WhileStatement",
            actionDesc: `Loop exit label: ${labelExit}:`,
            astNodeId: node.nodeId
        });
    }

    _extractIdentifier(node) {
        if (!node) return "";
        const name = node.name || "";
        if (name.startsWith("Identifier: ")) {
            return name.substring("Identifier: ".length).trim();
        }
        return name;
    }

    /**
     * Partition linear 3AC instructions into Basic Blocks and build Control Flow Graph.
     */
    _buildCFG() {
        const cfg = new ControlFlowGraph();
        const instructions = this.instructions;
        const n = instructions.length;
        if (n === 0) return cfg;

        const labelToIndex = new Map();
        for (let i = 0; i < n; i++) {
            if (instructions[i].type === InstructionType.LABEL && instructions[i].result) {
                labelToIndex.set(instructions[i].result, i);
            }
        }

        const leaderIndices = new Set([0]);

        for (let i = 0; i < n; i++) {
            const inst = instructions[i];
            if (
                inst.type === InstructionType.GOTO ||
                inst.type === InstructionType.IF_FALSE_GOTO ||
                inst.type === InstructionType.IF_TRUE_GOTO
            ) {
                if (labelToIndex.has(inst.result)) {
                    leaderIndices.add(labelToIndex.get(inst.result));
                }
                if (i + 1 < n) {
                    leaderIndices.add(i + 1);
                }
            } else if (inst.type === InstructionType.RETURN) {
                if (i + 1 < n) {
                    leaderIndices.add(i + 1);
                }
            } else if (inst.type === InstructionType.LABEL) {
                leaderIndices.add(i);
            }
        }

        const sortedLeaders = Array.from(leaderIndices).sort((a, b) => a - b);
        for (const idx of sortedLeaders) {
            instructions[idx].isLeader = true;
        }

        const labelToBlock = new Map();

        for (let bIdx = 0; bIdx < sortedLeaders.length; bIdx++) {
            const startIdx = sortedLeaders[bIdx];
            const endIdx = bIdx + 1 < sortedLeaders.length ? sortedLeaders[bIdx + 1] : n;
            const blockId = `B${bIdx}`;
            const block = new BasicBlock(blockId);
            block.isEntry = (bIdx === 0);
            block.instructions = instructions.slice(startIdx, endIdx);

            for (let i = startIdx; i < endIdx; i++) {
                if (instructions[i].type === InstructionType.LABEL && instructions[i].result) {
                    labelToBlock.set(instructions[i].result, blockId);
                }
            }

            cfg.addBlock(block);
        }

        cfg.entryBlockId = "B0";

        for (let bIdx = 0; bIdx < sortedLeaders.length; bIdx++) {
            const blockId = `B${bIdx}`;
            const block = cfg.blocks.get(blockId);
            if (!block || block.instructions.length === 0) continue;

            const terminator = block.terminator;
            const nextBlockId = bIdx + 1 < sortedLeaders.length ? `B${bIdx + 1}` : null;

            if (terminator.type === InstructionType.GOTO) {
                const targetBlockId = labelToBlock.get(terminator.result);
                if (targetBlockId) {
                    this._addCFGEdge(cfg, blockId, targetBlockId, "unconditional-jump");
                }
            } else if (terminator.type === InstructionType.IF_FALSE_GOTO) {
                const targetBlockId = labelToBlock.get(terminator.result);
                if (targetBlockId) {
                    this._addCFGEdge(cfg, blockId, targetBlockId, "branch-false", `!(${terminator.arg1})`);
                }
                if (nextBlockId) {
                    this._addCFGEdge(cfg, blockId, nextBlockId, "branch-true", String(terminator.arg1));
                }
            } else if (terminator.type === InstructionType.IF_TRUE_GOTO) {
                const targetBlockId = labelToBlock.get(terminator.result);
                if (targetBlockId) {
                    this._addCFGEdge(cfg, blockId, targetBlockId, "branch-true", String(terminator.arg1));
                }
                if (nextBlockId) {
                    this._addCFGEdge(cfg, blockId, nextBlockId, "branch-false", `!(${terminator.arg1})`);
                }
            } else if (terminator.type === InstructionType.RETURN) {
                // Exit block
            } else {
                if (nextBlockId) {
                    this._addCFGEdge(cfg, blockId, nextBlockId, "fall-through");
                }
            }
        }

        // Identify exit blocks
        for (const [id, block] of cfg.blocks.entries()) {
            if (block.successors.length === 0) {
                block.isExit = true;
                cfg.exitBlockIds.push(id);
            }
        }

        return cfg;
    }

    _addCFGEdge(cfg, fromId, toId, type, condition = null) {
        cfg.addEdge(new CFGEdge(fromId, toId, type, condition));
        const fromBlock = cfg.blocks.get(fromId);
        const toBlock = cfg.blocks.get(toId);
        if (fromBlock && !fromBlock.successors.includes(toId)) {
            fromBlock.successors.push(toId);
        }
        if (toBlock && !toBlock.predecessors.includes(fromId)) {
            toBlock.predecessors.push(fromId);
        }
    }
}
