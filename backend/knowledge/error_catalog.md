# ToyLang Common Error Catalog & Canonical Remedies

## Phase 1 & 2: Syntax and Grammar Errors

### Case ERR-SYN-01: Unexpected Token / Missing Semicolon
- **Description**: The parser encounters a token where a statement boundary or delimiter `;` was expected.
- **Example**:
  ```c
  int a = 10
  int b = 20;
  ```
- **Grammar Rule**: `declaration_statement : type ID ASSIGN expression SEMI`
- **Remedy**: Add a semicolon `;` at the end of line 1.

### Case ERR-SYN-02: Missing Expression in Initialized Declaration
- **Description**: An assignment operator `=` is present in a variable declaration, but no expression follows it before the semicolon.
- **Example**:
  ```c
  int b = ;
  ```
- **Grammar Rule**: `declaration_statement : type ID ASSIGN expression SEMI` requires a valid non-empty `expression`.
- **Remedy**: Provide a value or expression after the `=`, or remove the `=` if an uninitialized declaration `int b;` was intended.

### Case ERR-SYN-03: Redundant Semicolons & Disallowed Empty Statements
- **Description**: Consecutive semicolons `;;` or lone semicolons on a line.
- **Example**:
  ```c
  int a = 10;;
  ;;
  ```
- **Grammar Rule**: ToyLang CFG does not support empty statements (`statement : SEMI` does not exist). Every semicolon must be the terminator of a valid declaration, assignment, expression, return, or print statement.
- **Remedy**: Remove the extra semicolon.

### Case ERR-SYN-04: Unclosed Block or Parenthesis
- **Description**: Opening brace `{` or parenthesis `(` is never closed before EOF.
- **Example**:
  ```c
  while (x < 10) {
      x = x + 1;
  ```
- **Grammar Rule**: `block : LBRACE statement_list RBRACE`
- **Remedy**: Add the matching closing brace `}` before the end of input.

---

## Phase 3: Semantic and Type Checking Errors

### Case ERR-SEM-01: Undeclared Variable
- **Description**: An identifier is read or assigned to before it has been declared in the current or an enclosing scope.
- **Example**:
  ```c
  x = 10;
  ```
- **Semantic Rule**: `SEM-SCOPE-02` (Identifier Resolution).
- **Remedy**: Declare the variable with its data type first, e.g. `int x = 10;`.

### Case ERR-SEM-02: Type Incompatibility in Assignment
- **Description**: Attempting to assign a floating point expression to an integer variable.
- **Example**:
  ```c
  int a = 3.14;
  ```
- **Semantic Rule**: `SEM-TYPE-01` (Assignment Compatibility).
- **Remedy**: Change variable type to `float` or convert the expression to an integer.

### Case ERR-SEM-03: Duplicate Declaration
- **Description**: Redeclaring a variable with the same identifier in the exact same scope level.
- **Example**:
  ```c
  int x = 10;
  int x = 20;
  ```
- **Semantic Rule**: `SEM-SCOPE-04` (Duplicate Declaration).
- **Remedy**: Remove the second type specifier to make it an assignment `x = 20;`, or rename the variable.

---

## Phase 4 & 5: Intermediate Code & Assembly Generation Errors

### Case ERR-ICG-01: Control Flow without Block or Statement
- **Description**: An `if` or `while` statement missing its body statement.
- **Example**:
  ```c
  if (x > 0)
  ```
- **Remedy**: Supply a body statement or block `{ ... }`.

### Case ERR-ASM-01: Division by Zero Warning
- **Description**: Immediate zero in division/modulo denominator (`/ 0` or `% 0`).
- **Remedy**: Avoid dividing by a literal zero.
