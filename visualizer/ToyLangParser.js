/**
 * ToyLangParser.js - Client-side Lexer & AST Parser for ToyLang.
 * 
 * Generates an AST structure identical to the backend parser (tree_builder.py Node):
 * {
 *   name: "Operator: +",
 *   children: [...],
 *   line: 1
 * }
 */

export class ToyLangParser {
    constructor(source) {
        this.source = source || "";
        this.tokens = [];
        this.pos = 0;
    }

    tokenize() {
        const tokens = [];
        let line = 1;
        let col = 1;
        let i = 0;
        const src = this.source;
        const n = src.length;

        const isWhitespace = c => /\s/.test(c);
        const isDigit = c => /[0-9]/.test(c);
        const isAlpha = c => /[a-zA-Z_]/.test(c);
        const isAlphaNum = c => /[a-zA-Z0-9_]/.test(c);

        while (i < n) {
            const ch = src[i];

            if (ch === '\n') {
                line++;
                col = 1;
                i++;
                continue;
            }
            if (isWhitespace(ch)) {
                col++;
                i++;
                continue;
            }

            // Single line comment //
            if (ch === '/' && i + 1 < n && src[i + 1] === '/') {
                while (i < n && src[i] !== '\n') i++;
                continue;
            }

            // Multi-char operators
            if (ch === '=' && i + 1 < n && src[i + 1] === '=') {
                tokens.push({ type: "EQ", value: "==", line, col });
                i += 2; col += 2; continue;
            }
            if (ch === '!' && i + 1 < n && src[i + 1] === '=') {
                tokens.push({ type: "NE", value: "!=", line, col });
                i += 2; col += 2; continue;
            }
            if (ch === '<' && i + 1 < n && src[i + 1] === '=') {
                tokens.push({ type: "LE", value: "<=", line, col });
                i += 2; col += 2; continue;
            }
            if (ch === '>' && i + 1 < n && src[i + 1] === '=') {
                tokens.push({ type: "GE", value: ">=", line, col });
                i += 2; col += 2; continue;
            }

            // Single char tokens
            const singleChars = {
                '+': "PLUS", '-': "MINUS", '*': "TIMES", '/': "DIVIDE", '%': "MOD",
                '<': "LT", '>': "GT", '=': "ASSIGN", ';': "SEMI",
                '(': "LPAREN", ')': "RPAREN", '{': "LBRACE", '}': "RBRACE",
                ',': "COMMA"
            };

            if (singleChars[ch]) {
                tokens.push({ type: singleChars[ch], value: ch, line, col });
                i++; col++; continue;
            }

            // Numbers (int or float)
            if (isDigit(ch)) {
                let numStr = "";
                while (i < n && (isDigit(src[i]) || src[i] === '.')) {
                    numStr += src[i];
                    i++; col++;
                }
                tokens.push({
                    type: numStr.includes('.') ? "FLOAT_NUM" : "INT_NUM",
                    value: numStr,
                    line,
                    col
                });
                continue;
            }

            // Identifiers / Keywords
            if (isAlpha(ch)) {
                let idStr = "";
                while (i < n && isAlphaNum(src[i])) {
                    idStr += src[i];
                    i++; col++;
                }
                const keywords = {
                    "int": "INT",
                    "float": "FLOAT",
                    "bool": "BOOL",
                    "if": "IF",
                    "else": "ELSE",
                    "while": "WHILE",
                    "return": "RETURN",
                    "print": "PRINT"
                };
                tokens.push({
                    type: keywords[idStr] || "ID",
                    value: idStr,
                    line,
                    col
                });
                continue;
            }

            // Unknown character
            i++; col++;
        }

        tokens.push({ type: "EOF", value: "", line, col });
        this.tokens = tokens;
        this.pos = 0;
        return tokens;
    }

    peek() {
        return this.tokens[this.pos] || { type: "EOF", value: "" };
    }

    consume(expectedType = null) {
        const tok = this.peek();
        if (expectedType && tok.type !== expectedType) {
            throw new Error(`Syntax Error at line ${tok.line}: Expected ${expectedType}, found ${tok.type} ('${tok.value}')`);
        }
        this.pos++;
        return tok;
    }

    match(...types) {
        const tok = this.peek();
        return types.includes(tok.type);
    }

    parse() {
        this.tokenize();
        const statements = [];
        while (!this.match("EOF")) {
            statements.push(this.statement());
        }
        return {
            name: "Program",
            children: [
                {
                    name: "StatementList",
                    children: statements
                }
            ],
            line: 1
        };
    }

    statement() {
        const tok = this.peek();
        if (this.match("INT", "FLOAT", "BOOL")) {
            return this.declaration();
        }
        if (this.match("ID")) {
            return this.assignmentOrExpr();
        }
        if (this.match("IF")) {
            return this.ifStatement();
        }
        if (this.match("WHILE")) {
            return this.whileStatement();
        }
        if (this.match("LBRACE")) {
            return this.block();
        }
        if (this.match("PRINT")) {
            return this.printStatement();
        }
        if (this.match("RETURN")) {
            return this.returnStatement();
        }

        throw new Error(`Unexpected token '${tok.value}' at line ${tok.line}`);
    }

    block() {
        this.consume("LBRACE");
        const stmts = [];
        while (!this.match("RBRACE", "EOF")) {
            stmts.push(this.statement());
        }
        this.consume("RBRACE");
        return {
            name: "Block",
            children: [
                {
                    name: "StatementList",
                    children: stmts
                }
            ]
        };
    }

    declaration() {
        const typeTok = this.consume(); // INT / FLOAT / BOOL
        const idTok = this.consume("ID");
        const identNode = { name: `Identifier: ${idTok.value}`, line: idTok.line };

        let initExpr = null;
        if (this.match("ASSIGN")) {
            this.consume("ASSIGN");
            initExpr = this.expression();
        }
        this.consume("SEMI");

        const children = [identNode];
        if (initExpr) children.push(initExpr);

        return {
            name: `VarDeclaration (${typeTok.value})`,
            children,
            line: typeTok.line
        };
    }

    assignmentOrExpr() {
        // Lookahead to see if next token is ASSIGN
        if (this.tokens[this.pos + 1] && this.tokens[this.pos + 1].type === "ASSIGN") {
            const idTok = this.consume("ID");
            this.consume("ASSIGN");
            const expr = this.expression();
            this.consume("SEMI");
            return {
                name: "Assignment",
                children: [
                    { name: `Identifier: ${idTok.value}`, line: idTok.line },
                    expr
                ],
                line: idTok.line
            };
        } else {
            const expr = this.expression();
            this.consume("SEMI");
            return {
                name: "ExpressionStatement",
                children: [expr],
                line: expr.line || 1
            };
        }
    }

    ifStatement() {
        const ifTok = this.consume("IF");
        this.consume("LPAREN");
        const condExpr = this.expression();
        this.consume("RPAREN");
        const thenBlock = this.block();

        if (this.match("ELSE")) {
            this.consume("ELSE");
            const elseBlock = this.block();
            return {
                name: "IfStatement",
                children: [
                    { name: "Condition", children: [condExpr], line: ifTok.line },
                    { name: "Then", children: [thenBlock] },
                    { name: "Else", children: [elseBlock] }
                ],
                line: ifTok.line
            };
        }

        return {
            name: "IfStatement",
            children: [
                { name: "Condition", children: [condExpr], line: ifTok.line },
                thenBlock
            ],
            line: ifTok.line
        };
    }

    whileStatement() {
        const whileTok = this.consume("WHILE");
        this.consume("LPAREN");
        const condExpr = this.expression();
        this.consume("RPAREN");
        const bodyBlock = this.block();

        return {
            name: "WhileStatement",
            children: [
                { name: "Condition", children: [condExpr], line: whileTok.line },
                bodyBlock
            ],
            line: whileTok.line
        };
    }

    printStatement() {
        const pTok = this.consume("PRINT");
        this.consume("LPAREN");
        const expr = this.expression();
        this.consume("RPAREN");
        this.consume("SEMI");
        return {
            name: "PrintStatement",
            children: [expr],
            line: pTok.line
        };
    }

    returnStatement() {
        const rTok = this.consume("RETURN");
        let expr = null;
        if (!this.match("SEMI")) {
            expr = this.expression();
        }
        this.consume("SEMI");
        return {
            name: "ReturnStatement",
            children: expr ? [expr] : [],
            line: rTok.line
        };
    }

    expression() {
        return this.equality();
    }

    equality() {
        let left = this.relational();
        while (this.match("EQ", "NE")) {
            const opTok = this.consume();
            const right = this.relational();
            left = {
                name: `Operator: ${opTok.value}`,
                children: [left, right],
                line: opTok.line
            };
        }
        return left;
    }

    relational() {
        let left = this.additive();
        while (this.match("LT", "LE", "GT", "GE")) {
            const opTok = this.consume();
            const right = this.additive();
            left = {
                name: `Operator: ${opTok.value}`,
                children: [left, right],
                line: opTok.line
            };
        }
        return left;
    }

    additive() {
        let left = this.multiplicative();
        while (this.match("PLUS", "MINUS")) {
            const opTok = this.consume();
            const right = this.multiplicative();
            left = {
                name: `Operator: ${opTok.value}`,
                children: [left, right],
                line: opTok.line
            };
        }
        return left;
    }

    multiplicative() {
        let left = this.unary();
        while (this.match("TIMES", "DIVIDE", "MOD")) {
            const opTok = this.consume();
            const right = this.unary();
            left = {
                name: `Operator: ${opTok.value}`,
                children: [left, right],
                line: opTok.line
            };
        }
        return left;
    }

    unary() {
        if (this.match("MINUS")) {
            const opTok = this.consume();
            const operand = this.unary();
            return {
                name: "Unary: -",
                children: [operand],
                line: opTok.line
            };
        }
        return this.primary();
    }

    primary() {
        const tok = this.peek();

        if (this.match("INT_NUM", "FLOAT_NUM")) {
            this.consume();
            return { name: `Literal: ${tok.value}`, line: tok.line };
        }

        if (this.match("ID")) {
            this.consume();
            return { name: `Identifier: ${tok.value}`, line: tok.line };
        }

        if (this.match("LPAREN")) {
            this.consume("LPAREN");
            const expr = this.expression();
            this.consume("RPAREN");
            return expr;
        }

        throw new Error(`Syntax Error: Expected expression, got '${tok.value}' at line ${tok.line}`);
    }
}
