# ToyLang Formal Grammar & Syntax Specification

## Lexical Tokens and Operators
- **Data Types**: `int`, `float`, `bool`
- **Arithmetic Operators**: `+` (PLUS), `-` (MINUS), `*` (TIMES), `/` (DIVIDE), `%` (MOD)
- **Relational Operators**: `==` (EQ), `!=` (NE), `<` (LT), `<=` (LE), `>` (GT), `>=` (GE)
- **Assignment Operator**: `=` (ASSIGN)
- **Delimiters**: `;` (SEMI), `,` (COMMA), `(` (LPAREN), `)` (RPAREN), `{` (LBRACE), `}` (RBRACE)
- **Keywords**: `if`, `else`, `while`, `print`, `return`, `int`, `float`, `bool`
- **Comments**: Single-line `// comment` and multi-line `/* comment */`

## Context-Free Grammar (CFG) Productions

### Section 1: Program and Statement Lists
```ebnf
program : statement_list
statement_list : statement_list statement
               | statement
               | empty
```
A program is a sequence of zero or more statements executed sequentially.

### Section 2: Statement Types
```ebnf
statement : declaration_statement
          | assignment_statement
          | expression_statement
          | if_statement
          | while_statement
          | return_statement
          | print_statement
          | block
```
ToyLang strictly requires every statement to be one of the above 8 types.

### Section 3: Variable Declarations
```ebnf
declaration_statement : type ID SEMI
                      | type ID ASSIGN expression SEMI
```
- **Uninitialized declaration**: `int x;` allocates variable `x` with default zero value.
- **Initialized declaration**: `int x = 10;` declares variable `x` and evaluates `expression`.
- **Constraint**: If an assignment operator `=` is present, an expression MUST precede the semicolon. Expressions cannot be empty (e.g. `int b = ;` is invalid syntax).

### Section 4: Assignment and Expressions
```ebnf
assignment_statement : ID ASSIGN expression SEMI
expression_statement : expression SEMI
```
- Assignments update previously declared variables.
- Expressions evaluate arithmetic, relational, or literal operations.
- All expression statements must end with a single semicolon `;`.

### Section 5: Control Flow (If-Else & While)
```ebnf
if_statement : IF LPAREN expression RPAREN statement
             | IF LPAREN expression RPAREN statement ELSE statement

while_statement : WHILE LPAREN expression RPAREN statement
```
- Condition expressions must be enclosed in parentheses `( condition )`.
- Statements can be a single statement or a block `{ ... }`.
- Dangling `else` associates with the nearest preceding `if`.

### Section 6: Blocks & Scoping
```ebnf
block : LBRACE statement_list RBRACE
```
- Blocks group statements and create an inner lexical scope.

### Section 7: Function Return and Print
```ebnf
return_statement : RETURN expression SEMI
                 | RETURN SEMI

print_statement : PRINT LPAREN expression RPAREN SEMI
```
- `print(expr);` evaluates the expression and outputs to standard output.
- `return expr;` exits the program returning the evaluation result.

### Section 8: Operator Precedence & Associativity
1. Grouping: `( ... )`
2. Unary minus: `-` (right-associative)
3. Multiplicative: `*`, `/`, `%` (left-associative)
4. Additive: `+`, `-` (left-associative)
5. Relational: `<`, `<=`, `>`, `>=` (left-associative)
6. Equality: `==`, `!=` (left-associative)

### Section 9: Disallowed Constructs
- **No Empty Statements**: Lone semicolons `;` or double semicolons `;;` are NOT valid statements in ToyLang and will produce an unexpected token error.
- **No For Loops**: ToyLang uses `while` loops exclusively.
- **No Global Main Wrapper**: Code executes top-level directly without needing `int main()`.
