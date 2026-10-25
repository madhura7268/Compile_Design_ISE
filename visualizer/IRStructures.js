/**
 * IRStructures.js - Intermediate Representation data models for ToyLang Visualizer.
 * 
 * Provides:
 * - TempAllocator: Generator for temporaries (t0, t1, t2, ...)
 * - LabelGenerator: Generator for jump labels (L0, L1, L2, ...)
 * - Quadruple: 4-tuple record (op, arg1, arg2, result)
 * - Triple: 3-field indexed record (index, op, arg1, arg2)
 * - ThreeAddressInstruction: 3AC instruction with metadata
 * - BasicBlock: Partition of 3AC instructions
 * - CFGEdge: Directed edge between basic blocks
 * - ControlFlowGraph: Basic blocks + directed edges
 */

export class TempAllocator {
    constructor(prefix = "t") {
        this.prefix = prefix;
        this.counter = 0;
        this.history = [];
    }

    newTemp() {
        const name = `${this.prefix}${this.counter++}`;
        this.history.push(name);
        return name;
    }

    reset() {
        this.counter = 0;
        this.history = [];
    }

    get allocated() {
        return [...this.history];
    }
}

export class LabelGenerator {
    constructor(prefix = "L") {
        this.prefix = prefix;
        this.counter = 0;
        this.history = [];
    }

    newLabel() {
        const name = `${this.prefix}${this.counter++}`;
        this.history.push(name);
        return name;
    }

    reset() {
        this.counter = 0;
        this.history = [];
    }

    get generated() {
        return [...this.history];
    }
}

export class Quadruple {
    constructor(op, arg1 = null, arg2 = null, result = null, index = null) {
        this.op = op;
        this.arg1 = arg1;
        this.arg2 = arg2;
        this.result = result;
        this.index = index;
    }

    toTuple() {
        return [this.op, this.arg1, this.arg2, this.result];
    }

    format() {
        const a1 = this.arg1 !== null ? this.arg1 : "-";
        const a2 = this.arg2 !== null ? this.arg2 : "-";
        const res = this.result !== null ? this.result : "-";
        return `(${this.op}, ${a1}, ${a2}, ${res})`;
    }
}

export class Triple {
    constructor(index, op, arg1, arg2 = null) {
        this.index = index;
        this.op = op;
        this.arg1 = arg1;
        this.arg2 = arg2;
    }

    toTuple() {
        return [this.index, this.op, this.arg1, this.arg2];
    }

    format() {
        const a2 = this.arg2 !== null ? this.arg2 : "-";
        return `(${this.index}) (${this.op}, ${this.arg1}, ${a2})`;
    }
}

export const InstructionType = {
    ASSIGN: "ASSIGN",
    BINARY_OP: "BINARY_OP",
    UNARY_OP: "UNARY_OP",
    LABEL: "LABEL",
    GOTO: "GOTO",
    IF_FALSE_GOTO: "IF_FALSE_GOTO",
    IF_TRUE_GOTO: "IF_TRUE_GOTO",
    IF_CMP_GOTO: "IF_CMP_GOTO",
    PRINT: "PRINT",
    RETURN: "RETURN"
};

export class ThreeAddressInstruction {
    constructor({
        type,
        result = null,
        op = null,
        arg1 = null,
        arg2 = null,
        index = 0,
        isLeader = false,
        sourceLine = null,
        comment = null,
        astNodeId = null
    }) {
        this.type = type;
        this.result = result;
        this.op = op;
        this.arg1 = arg1;
        this.arg2 = arg2;
        this.index = index;
        this.isLeader = isLeader;
        this.sourceLine = sourceLine;
        this.comment = comment;
        this.astNodeId = astNodeId;
    }

    formatCode() {
        switch (this.type) {
            case InstructionType.LABEL:
                return `${this.result}:`;
            case InstructionType.ASSIGN:
                return `${this.result} = ${this.arg1}`;
            case InstructionType.BINARY_OP:
                return `${this.result} = ${this.arg1} ${this.op} ${this.arg2}`;
            case InstructionType.UNARY_OP:
                return `${this.result} = ${this.op} ${this.arg1}`;
            case InstructionType.GOTO:
                return `goto ${this.result}`;
            case InstructionType.IF_FALSE_GOTO:
                return `ifFalse ${this.arg1} goto ${this.result}`;
            case InstructionType.IF_TRUE_GOTO:
                return `ifTrue ${this.arg1} goto ${this.result}`;
            case InstructionType.IF_CMP_GOTO:
                return `if ${this.arg1} ${this.op} ${this.arg2} goto ${this.result}`;
            case InstructionType.PRINT:
                return `print ${this.arg1}`;
            case InstructionType.RETURN:
                return this.arg1 ? `return ${this.arg1}` : "return";
            default:
                return `${this.result} = ${this.arg1} ${this.op} ${this.arg2}`;
        }
    }
}

export class CFGEdge {
    constructor(fromBlock, toBlock, type, condition = null) {
        this.from = fromBlock;
        this.to = toBlock;
        this.type = type; // 'fall-through', 'branch-true', 'branch-false', 'unconditional-jump'
        this.condition = condition;
    }
}

export class BasicBlock {
    constructor(id) {
        this.id = id; // e.g. "B0"
        this.instructions = [];
        this.predecessors = [];
        this.successors = [];
        this.isEntry = false;
        this.isExit = false;
    }

    get leader() {
        return this.instructions.length > 0 ? this.instructions[0] : null;
    }

    get terminator() {
        return this.instructions.length > 0 ? this.instructions[this.instructions.length - 1] : null;
    }
}

export class ControlFlowGraph {
    constructor() {
        this.blocks = new Map();
        this.edges = [];
        this.entryBlockId = null;
        this.exitBlockIds = [];
    }

    addBlock(block) {
        this.blocks.set(block.id, block);
    }

    addEdge(edge) {
        this.edges.push(edge);
    }
}
