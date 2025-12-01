# Detailed Technical Analysis (English Version)

## Table of Contents
1. [JSON Tokenizer (Lexical Analyzer)](#1-json-tokenizer-lexical-analyzer)
2. [JSON Parser (Syntactic Analyzer)](#2-json-parser-syntactic-analyzer)
3. [Collection Class (Data Collection Operations)](#3-collection-class-data-collection-operations)
4. [Aggregate Functions Implementation](#4-aggregate-functions-implementation)
5. [Chunk Processing Mechanism](#5-chunk-processing-mechanism)
6. [Partial Aggregation Merging](#6-partial-aggregation-merging)
7. [Practical Application Case](#7-practical-application-case)

---

## 1. JSON Tokenizer (Lexical Analyzer)

### 1.1 Token Class

```python
class Token:
    def __init__(self, t, v, pos):
        self.type, self.value, self.pos = t, v, pos
```

**Purpose**: Represents a lexical unit (Token) in JSON

**Parameter Description**:
- `t` (type): Token type, such as "STR" (string), "NUM" (number), "{" (object start), etc.
- `v` (value): Actual value of the token, such as string content, numeric value, etc.
- `pos` (position): Position of the token in the source text, used for error reporting

**Example**:
- `Token("STR", "hello", 10)` represents a string with value "hello" at position 10
- `Token("{", "{", 0)` represents a left curly brace at position 0

---

### 1.2 Tokenizer Class Initialization

```python
class Tokenizer:
    ws = set(" \t\r\n")  # Whitespace character set
    def __init__(self, text):
        self.text, self.n, self.i = text, len(text), 0
```

**Purpose**: Initialize the lexical analyzer

**Key Variables**:
- `ws`: Class variable defining all whitespace characters (space, tab, carriage return, newline)
- `text`: JSON text string to parse
- `n`: Total length of text
- `i`: Current reading position (index), starting from 0

**Design Philosophy**: Use a single pointer `i` to scan text from left to right, gradually identifying Tokens

---

### 1.3 Basic Methods

#### peek() - Preview Character

```python
def peek(self):
    return self.text[self.i] if self.i < self.n else ''
```

**Purpose**: View the character at the current position without moving the pointer

**Return Value**:
- If there are still characters: return the current character
- If reached the end: return empty string

**Why It's Needed**: Before deciding how to handle a character, we need to "peek" at what the next character is, for example, to determine if a number contains a decimal point

---

#### next() - Read and Move

```python
def next(self):
    ch = self.peek()
    self.i += 1
    return ch
```

**Purpose**: Read the current character and move the pointer forward by one position

**Use Case**: Used when we're certain to consume this character

---

#### skip_ws() - Skip Whitespace

```python
def skip_ws(self):
    while self.i < self.n and self.text[self.i] in self.ws:
        self.i += 1
```

**Purpose**: Skip all consecutive whitespace characters

**Why It's Important**: Whitespace in JSON is insignificant and must be ignored to correctly identify Tokens

**Example**:
- Input: `{   "name"   :   "John"   }`
- After skip_ws, can correctly identify each Token, ignoring spaces

---

### 1.4 Reading Strings (read_str)

```python
def read_str(self, start):
    self.next()  # skip opening quote
    out = []
    while True:
        if self.i >= self.n:
            raise SyntaxError(f"String not closed (from {start})")
        ch = self.next()
        if ch == '"':
            break  # Encountered closing quote
        if ch == '\\':  # Encountered escape character
            if self.i >= self.n:
                raise SyntaxError("Bad escape sequence")
            esc = self.next()  # Read the escaped character
            m = {'"':'"', '\\':'\\', '/':'/', 'b':'\b', 'f':'\f', 'n':'\n', 'r':'\r', 't':'\t'}
            if esc in m:
                out.append(m[esc])
            else:
                raise SyntaxError(f"Unknown escape \\{esc}")
        else:
            out.append(ch)
    return ''.join(out)
```

**Purpose**: Read a complete JSON string value

**Detailed Process**:

1. **Skip Opening Quote**: `self.next()` consumes `"`

2. **Loop to Read Characters**:
   - Check if reached end of file (string not closed error)
   - Read next character

3. **Handle Normal Characters**:
   - If it's closing quote `"`, break the loop
   - If it's a normal character, add to result list

4. **Handle Escape Sequences**:
   - When encountering `\`, read the next character
   - Convert according to escape character mapping table:
     - `\"` → `"` (quote)
     - `\\` → `\` (backslash)
     - `\n` → newline
     - `\t` → tab
     - `\b` → backspace
     - `\f` → form feed
     - `\r` → carriage return
     - `\/` → `/`
   - If it's an unrecognized escape sequence, raise an error

5. **Return Result**: Join the character list into a string

**Example**:
```python
# Input: ""hello\nworld""
# Process:
# 1. Skip first "
# 2. Read h, e, l, l, o
# 3. Encounter \n, convert to newline
# 4. Read w, o, r, l, d
# 5. Encounter ", end
# Result: 'hello\nworld'
```

---

### 1.5 Reading Numbers (read_num)

```python
def read_num(self, start):
    j = self.i  # Record start position
    if self.peek() == '-':  # Negative number
        self.next()
    if self.peek() == '0':  # Starts with 0
        self.next()
    else:  # Other digits
        if not self.peek().isdigit():
            raise SyntaxError(f"Bad number at {start}")
        while self.peek().isdigit():  # Read integer part
            self.next()
    if self.peek() == '.':  # Decimal part
        self.next()
        if not self.peek().isdigit():
            raise SyntaxError("Bad decimal")
        while self.peek().isdigit():  # Read decimal part
            self.next()
    s = self.text[j:self.i]  # Extract number string
    return float(s) if '.' in s else int(s)  # Convert to numeric type
```

**Purpose**: Read a JSON number (integer or floating-point)

**Detailed Process**:

1. **Record Start Position**: `j = self.i` for extracting the entire number string later

2. **Handle Negative Sign**:
   - If current character is `-`, consume it (indicates negative number)

3. **Handle Integer Part**:
   - Case 1: Starts with `0` (e.g., `0`, `0.5`)
     - Directly consume `0`
   - Case 2: Other digits (e.g., `123`, `456.789`)
     - Must have at least one digit
     - Loop to read all consecutive digits

4. **Handle Decimal Part**:
   - If encountering `.`, indicates this is a floating-point number
   - Must ensure at least one digit after `.`
   - Loop to read all decimal places

5. **Type Conversion**:
   - Extract substring from `j` to `i`
   - If contains `.`, convert to `float`
   - Otherwise convert to `int`

**Example**:
```python
# "123" → 123 (int)
# "-456" → -456 (int)
# "0.5" → 0.5 (float)
# "-3.14159" → -3.14159 (float)
# "0123" → 123 (int) - Note: JSON doesn't allow leading zeros, but this will parse
```

**Design Note**: This implementation supports basic JSON number format but simplifies some edge cases (e.g., scientific notation)

---

### 1.6 Reading Keywords (read_kw)

```python
def read_kw(self, start):
    for k, v in [("true", True), ("false", False), ("null", None)]:
        if self.text.startswith(k, self.i):
            self.i += len(k)
            return v
    raise SyntaxError(f"Unknown literal near {start}")
```

**Purpose**: Read JSON keywords (`true`, `false`, `null`)

**Detailed Process**:

1. **Attempt Matching**: Check in sequence if current position starts with `"true"`, `"false"`, `"null"`

2. **Use startswith**: `self.text.startswith(k, self.i)` checks from position `i` if it matches the keyword

3. **Update Pointer**: If matched, move pointer forward by keyword length

4. **Return Value**:
   - `"true"` → Python's `True`
   - `"false"` → Python's `False`
   - `"null"` → Python's `None`

**Example**:
```python
# Input: true
# Matched "true", pointer moves 4 positions
# Return: True

# Input: false
# Matched "false", pointer moves 5 positions
# Return: False

# Input: null
# Matched "null", pointer moves 4 positions
# Return: None
```

**Note**: This method assumes keywords are not part of other characters, e.g., won't mistake the first 4 characters of `"trueValue"` as `true`. In complete JSON syntax, keywords should be followed by separators.

---

### 1.7 Main Method: tokens() Generator

```python
def tokens(self):
    while True:
        self.skip_ws()  # Skip whitespace
        if self.i >= self.n:
            yield Token("EOF", None, self.i)  # End of file
            return
        ch = self.peek()
        pos = self.i
        if ch in '{}[]:,':
            self.next()
            yield Token(ch, ch, pos)  # Punctuation
        elif ch == '"':
            yield Token("STR", self.read_str(pos), pos)  # String
        elif ch in '-0123456789':
            yield Token("NUM", self.read_num(pos), pos)  # Number
        else:
            yield Token("KW", self.read_kw(pos), pos)  # Keyword
```

**Purpose**: Main loop to generate all Tokens

**Detailed Process**:

1. **Infinite Loop**: Continuously generate Tokens until end of file

2. **Skip Whitespace**: Skip whitespace at the start of each loop

3. **Check End of File**:
   - If pointer exceeds range, generate `EOF` Token and exit

4. **Classify Characters**:
   - **Punctuation** (`{}[]:,`):
     - Directly generate corresponding Token type
     - Value is the character itself
   - **String** (`"`):
     - Call `read_str()` to read complete string
     - Generate `STR` type Token
   - **Number** (`-` or `0-9`):
     - Call `read_num()` to read complete number
     - Generate `NUM` type Token
   - **Other**:
     - Should be keywords (true/false/null)
     - Call `read_kw()` to read

5. **Record Position**: Each Token records its position in source text for error reporting

**Example Execution Flow**:
```python
# Input: '{"name": "John", "age": 30}'
# Generated Token sequence:
# Token('{', '{', 0)
# Token('STR', 'name', 1)
# Token(':', ':', 6)
# Token('STR', 'John', 8)
# Token(',', ',', 14)
# Token('STR', 'age', 16)
# Token(':', ':', 21)
# Token('NUM', 30, 23)
# Token('}', '}', 25)
# Token('EOF', None, 26)
```

**Design Advantages**:
- Use generator (`yield`): Memory efficient, generates Tokens on demand
- Unified Token format: Convenient for subsequent parsing
- Complete error handling: All exception cases have error messages

---

## 2. JSON Parser (Syntactic Analyzer)

### 2.1 Stream Class (Token Stream Wrapper)

```python
class Stream:
    def __init__(self, tokenizer):
        self.gen, self.buf = tokenizer.tokens(), []

    def peek(self):
        if not self.buf:
            self.buf.append(next(self.gen))
        return self.buf[0]

    def next(self):
        if self.buf:
            return self.buf.pop(0)
        return next(self.gen)

    def expect(self, t):
        tok = self.next()
        if tok.type != t:
            raise SyntaxError(f"Expect {t} at {tok.pos}, got {tok.type}")
        return tok
```

**Purpose**: Provide buffering and lookahead capability for Tokenizer-generated Token stream

**Why It's Needed**:
- During parsing, we often need to "peek" at the next Token to decide how to parse
- But Tokenizer's generator is one-way; once `next()` is called, the Token is consumed
- Stream implements "lookback" functionality through buffering

**Detailed Method Analysis**:

#### peek() - Preview Next Token

```python
def peek(self):
    if not self.buf:
        self.buf.append(next(self.gen))  # Get a Token from generator into buffer
    return self.buf[0]  # Return first in buffer (without consuming)
```

**Flow**:
1. If buffer is empty, get a Token from generator into buffer
2. Return the first Token in buffer (without consuming it)

**Example**:
```python
stream = Stream(tokenizer)
token1 = stream.peek()  # Read first Token into buffer, return it
token2 = stream.peek()  # Buffer already has it, return the same Token
# token1 and token2 are the same object
```

#### next() - Consume Token

```python
def next(self):
    if self.buf:
        return self.buf.pop(0)  # Get from buffer (FIFO)
    return next(self.gen)  # Buffer empty, get directly from generator
```

**Flow**:
1. If buffer has Tokens, get from buffer (consume)
2. If buffer is empty, get directly from generator

**Example**:
```python
token1 = stream.peek()   # Token A enters buffer, return A
token2 = stream.next()   # Get A from buffer, return A
token3 = stream.next()   # Buffer empty, get next Token B from generator, return B
```

#### expect() - Expect Specific Token Type

```python
def expect(self, t):
    tok = self.next()
    if tok.type != t:
        raise SyntaxError(f"Expect {t} at {tok.pos}, got {tok.type}")
    return tok
```

**Purpose**: Ensure the next Token is of the expected type, otherwise raise an error

**Use Case**: When parsing JSON object, we know there should be `{` at the start:
```python
stream.expect('{')  # Ensure it's left curly brace, otherwise error
```

---

### 2.2 Parser Class - Core Parsing Methods

#### parse() - Entry Method

```python
class Parser:
    def parse(self, text):
        ts = Stream(Tokenizer(text))
        val = self.value(ts)
        if ts.peek().type != "EOF":
            raise SyntaxError("Extra content after JSON")
        return val
```

**Purpose**: Parse complete JSON text

**Flow**:
1. Create Tokenizer, wrap as Stream
2. Call `value()` to parse JSON value (can be object, array, string, number, etc.)
3. Check if there's extra content (should be EOF)
4. Return parsed result

---

#### value() - Parse JSON Value

```python
def value(self, ts):
    t = ts.peek()  # Preview next Token
    if t.type == '{': return self.obj(ts)      # Object
    if t.type == '[': return self.arr(ts)      # Array
    if t.type == 'STR': return ts.next().value # String
    if t.type == 'NUM': return ts.next().value # Number
    if t.type == 'KW':  return ts.next().value # Keyword (true/false/null)
    raise SyntaxError(f"Unexpected token {t.type}")
```

**Purpose**: Dispatch to corresponding parsing method based on Token type

**Design Pattern**: This is the root method of a typical recursive descent parser, deciding parsing path based on the type of the first Token

**JSON Value Types**:
- Object: `{...}`
- Array: `[...]`
- String: `"..."`
- Number: `123`, `3.14`
- Keyword: `true`, `false`, `null`

---

#### obj() - Parse JSON Object

```python
def obj(self, ts):
    ts.expect('{')  # Ensure left curly brace
    o = {}  # Create empty dictionary
    
    if ts.peek().type == '}':  # Empty object
        ts.next()
        return o
    
    while True:
        k = ts.expect("STR").value  # Key must be string
        ts.expect(':')              # Key-value separator
        o[k] = self.value(ts)       # Recursively parse value
        
        t = ts.peek()  # Look at next Token
        if t.type == ',':
            ts.next()  # Consume comma, continue next key-value pair
        elif t.type == '}':
            ts.next(); break  # Consume right curly brace, end
        else:
            raise SyntaxError(f"Unexpected {t.type}")
    return o
```

**Purpose**: Parse JSON object in format `{"key1": value1, "key2": value2}`

**Detailed Flow**:

1. **Expect Left Curly Brace**: `ts.expect('{')` ensures object start

2. **Handle Empty Object**:
   ```json
   {}
   ```
   - If next Token is `}`, directly return empty dictionary

3. **Loop to Parse Key-Value Pairs**:
   ```json
   {"name": "John", "age": 30}
   ```
   - **Read Key**: Must be string type (`ts.expect("STR")`)
   - **Expect Colon**: Must have `:` between key and value
   - **Recursively Parse Value**: `self.value(ts)` can parse any value type (nested objects, arrays, etc.)
   - **Store Key-Value Pair**: `o[k] = ...`

4. **Handle Separator**:
   - If it's `,`: Continue reading next key-value pair
   - If it's `}`: Object ends, break loop
   - Other: Syntax error

**Recursive Feature**:
```json
{
  "user": {
    "name": "John",
    "address": {
      "city": "New York"
    }
  }
}
```
- When parsing outer object, encountering `"user"` value being an object, recursively call `self.value()` → `self.obj()`

**Example Execution**:
```python
# Input: '{"name": "John", "age": 30}'
# Flow:
# 1. expect('{') → consume {
# 2. expect("STR") → key "name"
# 3. expect(':') → consume :
# 4. value() → recursively parse "John", return string
# 5. o["name"] = "John"
# 6. peek() → see ',', consume it
# 7. expect("STR") → key "age"
# 8. expect(':') → consume :
# 9. value() → parse 30, return integer
# 10. o["age"] = 30
# 11. peek() → see '}', consume it, break
# Result: {"name": "John", "age": 30}
```

---

#### arr() - Parse JSON Array

```python
def arr(self, ts):
    ts.expect('[')  # Expect left square bracket
    a = []  # Create empty list
    
    if ts.peek().type == ']':  # Empty array
        ts.next()
        return a
    
    while True:
        a.append(self.value(ts))  # Recursively parse element
        t = ts.peek()
        if t.type == ',':
            ts.next()  # Consume comma, continue next element
        elif t.type == ']':
            ts.next(); break  # Consume right square bracket, end
        else:
            raise SyntaxError(f"Unexpected {t.type}")
    return a
```

**Purpose**: Parse JSON array in format `[value1, value2, value3]`

**Detailed Flow**:

1. **Expect Left Square Bracket**: `ts.expect('[')`

2. **Handle Empty Array**:
   ```json
   []
   ```

3. **Loop to Parse Elements**:
   ```json
   [1, "hello", true, {"key": "value"}]
   ```
   - Each element parsed recursively through `self.value(ts)`
   - Elements can be any JSON value type (including nested arrays and objects)

4. **Handle Separator**:
   - `,`: Continue next element
   - `]`: Array ends

**Example Execution**:
```python
# Input: '[1, "hello", true]'
# Flow:
# 1. expect('[') → consume [
# 2. value() → parse 1, add to array
# 3. peek() → see ',', consume it
# 4. value() → parse "hello", add to array
# 5. peek() → see ',', consume it
# 6. value() → parse true, add to array
# 7. peek() → see ']', consume it, break
# Result: [1, "hello", True]
```

---

### 2.3 Parser Summary

**Design Pattern**: Recursive Descent Parser

**Features**:
- Each syntax structure (object, array) corresponds to a method
- Methods can recursively call other methods (handle nesting)
- Use lookahead (peek) to decide parsing path
- Use expect to verify syntax correctness

**Error Handling**:
- Each method throws `SyntaxError` when syntax is incorrect
- Error messages include position information for debugging

**Parsing Capabilities**:
- ✅ Nested objects: `{"a": {"b": {"c": 1}}}`
- ✅ Nested arrays: `[[1, 2], [3, 4]]`
- ✅ Mixed nesting: `{"items": [{"id": 1}, {"id": 2}]}`
- ✅ All basic types: string, number, boolean, null

---

## 3. Collection Class (Data Collection Operations)

### 3.1 Class Initialization

```python
class Collection:
    def __init__(self, data):
        self.data = data if isinstance(data, list) else [data]
```

**Purpose**: Create a data collection, uniformly handling single object or object list

**Design Philosophy**:
- Unified interface: Whether input is single document or document list, convert to list
- Convenient for subsequent operations: All query operations assume `self.data` is a list

**Example**:
```python
# Single object → convert to list
coll1 = Collection({"name": "John"})
# self.data = [{"name": "John"}]

# List → remain unchanged
coll2 = Collection([{"name": "John"}, {"name": "Jane"}])
# self.data = [{"name": "John"}, {"name": "Jane"}]
```

---

### 3.2 _extract_key() - Key Extraction Helper Method

```python
def _extract_key(self, doc, key):
    """supports dot notation"""
    ks = key.split(".")  # Split key path by dot
    cur = doc  # Current lookup position
    for k in ks:
        if not isinstance(cur, dict) or k not in cur:
            return None  # Path doesn't exist
        cur = cur[k]  # Enter next level
    return cur
```

**Purpose**: Extract field value from document, supports dot notation for nested fields

**Detailed Flow**:

1. **Split Key Path**: `"user.name"` → `["user", "name"]`

2. **Lookup Layer by Layer**:
   - Start from document root
   - Check each layer if it's a dict and contains the key
   - Enter next level

3. **Error Handling**: If path doesn't exist, return `None`

**Example**:
```python
doc = {
    "user": {
        "name": "John",
        "age": 30
    },
    "city": "NYC"
}

# Simple key
_extract_key(doc, "city")  # → "NYC"

# Nested key
_extract_key(doc, "user.name")  # → "John"
_extract_key(doc, "user.age")   # → 30

# Non-existent key
_extract_key(doc, "user.email")  # → None
_extract_key(doc, "invalid.path")  # → None
```

**Complex Nested Example**:
```python
doc = {
    "level1": {
        "level2": {
            "level3": {
                "value": 42
            }
        }
    }
}

_extract_key(doc, "level1.level2.level3.value")  # → 42
```

**Design Advantages**:
- Unified interface: Whether simple or nested fields, use the same method
- Fault-tolerant: Returns `None` when path doesn't exist, doesn't raise exception
- Flexible: Supports arbitrary depth of nesting

---

### 3.3 find() - Query Filter

```python
def find(self, query=None):
    if query is None:  # No query condition
        return self.data  # Return all data
    
    def match(doc, query):  # Inner function: check if document matches query
        for key, value in query.items():
            cur = self._extract_key(doc, key)  # Extract field value
            if cur != value:
                return False  # One field mismatch returns False
        return True  # All fields match
    
    return [doc for doc in self.data if match(doc, query)]
```

**Purpose**: Filter documents based on query conditions, similar to SQL's `WHERE` clause

**Detailed Analysis**:

#### No Query Condition
```python
collection.find()  # Return all documents
collection.find(None)  # Same as above
```

#### With Query Condition
```python
# Query: {"name": "John", "age": 30}
# Matching documents: all documents with name="John" AND age=30
```

**match() Inner Function**:
- Iterate through each key-value pair in query condition
- Extract corresponding field value from document
- If values don't match, document doesn't match
- Only return `True` when all conditions are satisfied

**List Comprehension**:
```python
[doc for doc in self.data if match(doc, query)]
```
- Iterate through all documents
- Only keep matching documents

**Example**:
```python
data = [
    {"name": "John", "age": 30, "city": "NYC"},
    {"name": "Jane", "age": 25, "city": "LA"},
    {"name": "John", "age": 30, "city": "SF"}
]

coll = Collection(data)

# Single condition
coll.find({"name": "John"})
# Result: [{"name": "John", "age": 30, "city": "NYC"},
#          {"name": "John", "age": 30, "city": "SF"}]

# Multiple conditions (AND relationship)
coll.find({"name": "John", "age": 30})
# Result: [{"name": "John", "age": 30, "city": "NYC"},
#          {"name": "John", "age": 30, "city": "SF"}]

# No match
coll.find({"name": "Bob"})
# Result: []

# No query condition
coll.find()
# Result: All three documents
```

**Supports Nested Fields**:
```python
data = [
    {"user": {"name": "John"}, "age": 30},
    {"user": {"name": "Jane"}, "age": 25}
]

coll = Collection(data)
coll.find({"user.name": "John"})  # Use dot notation
# Result: [{"user": {"name": "John"}, "age": 30}]
```

**Limitations**:
- Only supports equality matching (`==`)
- Doesn't support range queries (`>`, `<`)
- Doesn't support OR conditions
- Multiple conditions are AND relationship

---

### 3.4 project() - Field Projection

```python
def project(self, fields):
    """Return documents with only selected fields."""
    result = []
    for doc in self.data:
        projected = {}  # New document, only contains selected fields
        for field in fields:
            # Use _extract_key to handle nested keys
            projected[field] = self._extract_key(doc, field)
        result.append(projected)
    return result
```

**Purpose**: Select fields to display, similar to SQL's `SELECT field1, field2 FROM ...`

**Detailed Flow**:

1. **Iterate Through Each Document**

2. **Create Projected Document**:
   - Only contains fields specified in `fields`
   - Use `_extract_key()` to extract values (supports nested fields)

3. **Add to Result List**

**Example**:
```python
data = [
    {"name": "John", "age": 30, "city": "NYC", "salary": 50000},
    {"name": "Jane", "age": 25, "city": "LA", "salary": 60000}
]

coll = Collection(data)

# Select single field
coll.project(["name"])
# Result: [{"name": "John"}, {"name": "Jane"}]

# Select multiple fields
coll.project(["name", "age"])
# Result: [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]

# Nested fields
data2 = [
    {"user": {"name": "John", "email": "john@example.com"}, "age": 30}
]
coll2 = Collection(data2)
coll2.project(["user.name", "age"])
# Result: [{"user.name": "John", "age": 30}]
```

**Design Features**:
- Field names remain unchanged: If selecting `"user.name"`, result also uses `"user.name"` as key
- Missing fields return `None`: If document doesn't have a field, value is `None`
- Supports nested fields: Select nested fields through dot notation

**Combine with find()**:
```python
# Filter first, then project
filtered = coll.find({"city": "NYC"})
projected = Collection(filtered).project(["name", "age"])
```

---

### 3.5 groupby() - Grouping

```python
def groupby(self, key):
    groups = {}  # Dictionary: group value -> document list
    for doc in self.data:
        group_value = self._extract_key(doc, key)  # Extract grouping key value
        groups.setdefault(group_value, []).append(doc)
    return groups
```

**Purpose**: Group documents by specified field value, similar to SQL's `GROUP BY`

**Detailed Flow**:

1. **Create Group Dictionary**: Key is grouping field value, value is list of all documents in that group

2. **Iterate Through Documents**:
   - Extract grouping field value
   - Add document to corresponding group's list

3. **setdefault Usage**:
   ```python
   groups.setdefault(group_value, []).append(doc)
   ```
   - If `group_value` not in dictionary, create new list `[]`
   - If exists, use existing list
   - Add document to list

**Example**:
```python
data = [
    {"city": "NYC", "name": "John", "age": 30},
    {"city": "NYC", "name": "Jane", "age": 25},
    {"city": "LA", "name": "Bob", "age": 35},
    {"city": "LA", "name": "Alice", "age": 28}
]

coll = Collection(data)
groups = coll.groupby("city")

# Result:
# {
#     "NYC": [
#         {"city": "NYC", "name": "John", "age": 30},
#         {"city": "NYC", "name": "Jane", "age": 25}
#     ],
#     "LA": [
#         {"city": "LA", "name": "Bob", "age": 35},
#         {"city": "LA", "name": "Alice", "age": 28}
#     ]
# }
```

**Nested Field Grouping**:
```python
data = [
    {"user": {"city": "NYC"}, "name": "John"},
    {"user": {"city": "NYC"}, "name": "Jane"},
    {"user": {"city": "LA"}, "name": "Bob"}
]

coll = Collection(data)
groups = coll.groupby("user.city")
# Group by nested field
```

**Null Value Handling**:
```python
data = [
    {"city": "NYC", "name": "John"},
    {"city": None, "name": "Jane"}  # Missing field
]

coll = Collection(data)
groups = coll.groupby("city")
# {
#     "NYC": [{"city": "NYC", "name": "John"}],
#     None: [{"city": None, "name": "Jane"}]
# }
```

---

### 3.6 aggregate() - Aggregation

```python
def aggregate(self, group_key, agg_func):
    """Apply an aggregation function (sum, count, avg, etc.) on each group."""
    grouped = self.groupby(group_key)  # Group first
    result = {}
    for k, docs in grouped.items():
        result[k] = agg_func(docs)  # Apply aggregation function to each group
    return result
```

**Purpose**: Perform aggregation calculations on grouped data, similar to SQL's `GROUP BY ... COUNT/SUM/AVG(...)`

**Detailed Flow**:

1. **Group First**: Call `groupby()` to get grouping dictionary

2. **Apply Aggregation Function to Each Group**:
   - Iterate through each group
   - Call `agg_func(docs)` to aggregate documents in group
   - Store result as `{group value: aggregation result}`

**Aggregation Function**: Accepts document list, returns aggregation value (see Section 4)

**Example**:
```python
data = [
    {"city": "NYC", "sales": 100},
    {"city": "NYC", "sales": 200},
    {"city": "LA", "sales": 150},
    {"city": "LA", "sales": 250}
]

coll = Collection(data)

# Calculate count per group
count_func = lambda docs: len(docs)
result = coll.aggregate("city", count_func)
# Result: {"NYC": 2, "LA": 2}

# Calculate sum of sales per group
sum_func = lambda docs: sum(doc["sales"] for doc in docs)
result = coll.aggregate("city", sum_func)
# Result: {"NYC": 300, "LA": 400}
```

**Combine with Aggregation Function Library** (see Section 4):
```python
from aggregate_functions import agg_count, agg_sum

coll.aggregate("city", agg_count())  # Count
coll.aggregate("city", agg_sum("sales"))  # Sum
```

---

### 3.7 hash_join() - Hash Join

```python
def hash_join(self, other, key_self, key_other, join_type="inner"):
    """
    join_type: inner / left / right / full
    """
    
    # Step 1: Build hash table for right table (other)
    hashmap = {}
    for doc in other.data:
        val = self._extract_key(doc, key_other)  # Extract join key value
        hashmap.setdefault(val, []).append(doc)  # Documents with same key value go into same list
    
    result = []
    matched_right_keys = set()  # Record matched right table documents (for right/full join)
    
    # Step 2: Process each document in left table (self)
    for doc_left in self.data:
        val_left = self._extract_key(doc_left, key_self)
        if val_left in hashmap:  # Found match in hash table
            for doc_right in hashmap[val_left]:  # May have multiple matches (one-to-many)
                matched_right_keys.add(id(doc_right))  # Record matched
                result.append({
                    "left": doc_left,
                    "right": doc_right
                })
        else:  # Left table document has no match
            if join_type in ("left", "full"):
                result.append({
                    "left": doc_left,
                    "right": None  # Right table fields are None
                })
    
    # Step 3: Process unmatched right table documents (right join or full join)
    if join_type in ("right", "full"):
        for doc_right in other.data:
            if id(doc_right) not in matched_right_keys:
                result.append({
                    "left": None,  # Left table fields are None
                    "right": doc_right
                })
    
    return result
```

**Purpose**: Implement hash join algorithm to connect two datasets, similar to SQL's `JOIN`

**Join Types**:
- **inner join**: Only return records that have matches in both tables
- **left join**: Return all left table records, use `None` when right table has no match
- **right join**: Return all right table records, use `None` when left table has no match
- **full join**: Return all records from both tables, use `None` when no match

**Detailed Algorithm Analysis**:

#### Step 1: Build Hash Table (Right Table)

```python
hashmap = {}
for doc in other.data:
    val = self._extract_key(doc, key_other)
    hashmap.setdefault(val, []).append(doc)
```

**Purpose**: Quickly find matching right table documents

**Structure**:
```python
{
    join_key_value1: [doc1, doc2, ...],  # May have multiple docs with same key (one-to-many)
    join_key_value2: [doc3, ...],
    ...
}
```

**Time Complexity**: O(n), n is number of right table documents

#### Step 2: Process Left Table (Inner Join + Left Join Part)

```python
for doc_left in self.data:
    val_left = self._extract_key(doc_left, key_self)
    if val_left in hashmap:  # Found match
        for doc_right in hashmap[val_left]:
            result.append({"left": doc_left, "right": doc_right})
    else:  # No match found
        if join_type in ("left", "full"):
            result.append({"left": doc_left, "right": None})
```

**Flow**:
1. Iterate through each document in left table
2. Extract join key value
3. Look up in hash table
   - **Has match**: Generate all matching pairs (supports one-to-many)
   - **No match**: If left/full join, add left table record with right as `None`

#### Step 3: Process Unmatched Right Table Documents (Right Join + Full Join Part)

```python
if join_type in ("right", "full"):
    for doc_right in other.data:
        if id(doc_right) not in matched_right_keys:
            result.append({"left": None, "right": doc_right})
```

**Purpose**: Add documents from right table that have no matches

**Using `id()`**: Python object's unique identifier to determine if document has been matched

**Example Execution**:

```python
# Left table
left_data = [
    {"id": 1, "name": "John"},
    {"id": 2, "name": "Jane"},
    {"id": 3, "name": "Bob"}
]

# Right table
right_data = [
    {"user_id": 1, "city": "NYC"},
    {"user_id": 1, "city": "SF"},  # One-to-many
    {"user_id": 2, "city": "LA"}
]

left_coll = Collection(left_data)
right_coll = Collection(right_data)

# Inner Join
result = left_coll.hash_join(right_coll, "id", "user_id", "inner")
# Result:
# [
#     {"left": {"id": 1, "name": "John"}, "right": {"user_id": 1, "city": "NYC"}},
#     {"left": {"id": 1, "name": "John"}, "right": {"user_id": 1, "city": "SF"}},  # One-to-many
#     {"left": {"id": 2, "name": "Jane"}, "right": {"user_id": 2, "city": "LA"}}
# ]
# Note: id=3 Bob has no match, not included in result

# Left Join
result = left_coll.hash_join(right_coll, "id", "user_id", "left")
# Result includes id=3 record with right as None

# Right Join
result = left_coll.hash_join(right_coll, "id", "user_id", "right")
# Result includes all right table records, left is None if left table has no match

# Full Join
result = left_coll.hash_join(right_coll, "id", "user_id", "full")
# Result includes all records from both tables
```

**Algorithm Advantages**:
- **Time Complexity**: O(m + n), m and n are sizes of two tables (hash table lookup is O(1))
- **Space Complexity**: O(n), need to store right table hash table
- **Efficient**: Much faster than nested loop O(m × n)

**Limitations**:
- Only supports equality joins (equal matching)
- Doesn't support range joins (`>`, `<`)

---

### 3.8 pipeline() - Operation Pipeline

```python
def pipeline(self, query=None, project_fields=None,
             group_key=None, agg_func=None,
             join_collection=None, join_self_key=None, 
             join_other_key=None, join_type="inner"):
    data = self.data
    
    # Step 1: Filter (if query condition exists)
    if query:
        data = Collection(data).find(query)
    
    # Step 2: Project (if fields specified)
    if project_fields:
        data = Collection(data).project(project_fields)
    
    # Step 3: Aggregate (if grouping key and aggregation function specified)
    if group_key and agg_func:
        data = Collection(data).aggregate(group_key, agg_func)
    
    # Step 4: Join (if join collection specified)
    if join_collection:
        data = Collection(data).hash_join(
            join_collection,
            join_self_key,
            join_other_key,
            join_type
        )
    
    return data
```

**Purpose**: Combine multiple operations into a pipeline, executed in sequence

**Operation Order**:
1. **find** (filter): Reduce data volume
2. **project** (projection): Select fields
3. **aggregate** (aggregation): Group statistics
4. **hash_join** (join): Merge data

**Design Philosophy**:
- Result of each operation becomes input for next operation
- Use `Collection(data)` to wrap intermediate results, maintaining consistent interface

**Example**:
```python
# Query records with city="NYC", select name and age fields, group by age and count
result = coll.pipeline(
    query={"city": "NYC"},
    project_fields=["name", "age"],
    group_key="age",
    agg_func=agg_count()
)
```

**Actual Execution Flow**:
```python
# Original data
data = [
    {"name": "John", "age": 30, "city": "NYC"},
    {"name": "Jane", "age": 25, "city": "NYC"},
    {"name": "Bob", "age": 30, "city": "LA"}
]

# Step 1: find({"city": "NYC"})
filtered = [
    {"name": "John", "age": 30, "city": "NYC"},
    {"name": "Jane", "age": 25, "city": "NYC"}
]

# Step 2: project(["name", "age"])
projected = [
    {"name": "John", "age": 30},
    {"name": "Jane", "age": 25}
]

# Step 3: aggregate("age", agg_count())
result = {
    30: 1,  # 1 person aged 30
    25: 1   # 1 person aged 25
}
```

**Flexibility**:
- All parameters are optional
- Can use only part of operations
- Order is fixed (optimized order)

---

## 4. Aggregate Functions Implementation

### 4.1 agg_count() - Count

```python
def agg_count(field=None):
    return lambda docs: len(docs)
```

**Purpose**: Count number of documents (number of documents in group)

**Design Pattern**: Higher-order function
- `agg_count()` returns a function (lambda)
- This function accepts document list, returns count

**Why This Design**:
- Unified interface: All aggregation functions return `(docs) -> value` function
- Flexible: Although `field` parameter isn't used here, maintains interface consistency

**Usage Example**:
```python
count_func = agg_count()  # Returns function
result = coll.aggregate("city", count_func)  # Apply function to each group

# Equivalent writing
result = coll.aggregate("city", lambda docs: len(docs))
```

**Result Example**:
```python
data = [
    {"city": "NYC", "name": "John"},
    {"city": "NYC", "name": "Jane"},
    {"city": "LA", "name": "Bob"}
]

coll = Collection(data)
result = coll.aggregate("city", agg_count())
# Result: {"NYC": 2, "LA": 1}
```

---

### 4.2 agg_sum() - Sum

```python
def agg_sum(field):
    return lambda docs: sum(
        doc.get(field, 0) for doc in docs
        if isinstance(doc.get(field), (int, float))
    )
```

**Purpose**: Sum specified field

**Detailed Analysis**:

1. **Return Function**: Lambda accepts document list

2. **Generator Expression**:
   ```python
   doc.get(field, 0) for doc in docs
       if isinstance(doc.get(field), (int, float))
   ```
   - Iterate through each document
   - Only process numeric types (int or float)
   - Use `doc.get(field, 0)` to safely get field value, default to 0 if missing

3. **Sum**: `sum(...)` sums generator results

**Example**:
```python
data = [
    {"city": "NYC", "sales": 100},
    {"city": "NYC", "sales": 200},
    {"city": "LA", "sales": 150},
    {"city": "LA", "sales": None}  # Non-numeric, will be skipped
]

coll = Collection(data)
result = coll.aggregate("city", agg_sum("sales"))
# Result: {"NYC": 300, "LA": 150}
```

**Fault Tolerance**:
- Missing fields: Use default value 0
- Non-numeric fields: Checked through `isinstance`, skipped
- Type-safe: Only process numeric types

---

### 4.3 agg_max() - Maximum

```python
def agg_max(field):
    return lambda docs: max(
        doc.get(field) for doc in docs
        if isinstance(doc.get(field), (int, float))
    )
```

**Purpose**: Find maximum value of specified field

**Note**:
- Uses `doc.get(field)` instead of `doc.get(field, 0)`
- Because if all documents are missing this field, `max()` will throw error (empty sequence)
- But here through `if` condition filtering, ensures generator has at least one value

**Example**:
```python
data = [
    {"city": "NYC", "sales": 100},
    {"city": "NYC", "sales": 200},
    {"city": "LA", "sales": 150}
]

coll = Collection(data)
result = coll.aggregate("city", agg_max("sales"))
# Result: {"NYC": 200, "LA": 150}
```

**Edge Cases**:
- If all documents in group are missing this field, generator is empty, `max()` will throw `ValueError`
- May need additional handling in actual use

---

### 4.4 agg_min() - Minimum

```python
def agg_min(field):
    return lambda docs: min(
        doc.get(field) for doc in docs
        if isinstance(doc.get(field), (int, float))
    )
```

**Purpose**: Find minimum value of specified field

**Implementation**: Similar to `agg_max()`, uses `min()` instead of `max()`

---

### 4.5 agg_avg() - Average

```python
def agg_avg(field):
    return lambda docs: (
        sum(doc.get(field, 0) for doc in docs
            if isinstance(doc.get(field), (int, float)))
        / len(docs)
        if docs else None
    )
```

**Purpose**: Calculate average value of specified field

**Detailed Analysis**:

1. **Sum Part**:
   ```python
   sum(doc.get(field, 0) for doc in docs
       if isinstance(doc.get(field), (int, float)))
   ```
   - Only sum numeric fields
   - Missing fields use 0

2. **Divide by Document Count**:
   ```python
   / len(docs)
   ```
   - Use total document count (not count of valid values)
   - This means missing values are treated as 0 in calculation

3. **Empty List Handling**:
   ```python
   if docs else None
   ```
   - If document list is empty, return `None` (avoid division by zero error)

**Example**:
```python
data = [
    {"city": "NYC", "sales": 100},
    {"city": "NYC", "sales": 200},
    {"city": "NYC", "sales": None}  # Missing value
]

coll = Collection(data)
result = coll.aggregate("city", agg_avg("sales"))
# Calculation: (100 + 200 + 0) / 3 = 100.0
# Note: Missing value treated as 0, denominator is total document count 3
```

**Design Choice**:
- Use `len(docs)` as denominator: Includes all documents (missing values counted as 0)
- Alternative design: Only calculate average of valid values, denominator is valid value count
- Current implementation is simpler but may not meet some business requirements

---

## 5. Chunk Processing Mechanism

### 5.1 load_json_chunks() - Chunk Loader

```python
def load_json_chunks(path, chunk_size=5000):
    """
    Generic loader:
        - if JSONL:  one JSON object per line
        - if JSON array: [ {...}, {...} ]
    """
    with open(path, "r", encoding="utf-8") as f:
        first_char = f.read(1)  # Read first character to determine format
        f.seek(0)  # Return to file beginning
        
        if first_char == "[":  # JSON array format
            text = f.read()  # Read entire file
            parser = Parser()
            arr = parser.parse(text)  # Parse as array
            for i in range(0, len(arr), chunk_size):
                yield arr[i:i + chunk_size]  # Slice by chunk size
        else:  # JSONL format (one JSON object per line)
            parser = Parser()
            buffer = []  # Buffer
            for line in f:
                line = line.strip()  # Remove leading/trailing whitespace
                if not line:
                    continue  # Skip empty lines
                buffer.append(parser.parse(line))  # Parse line, add to buffer
                if len(buffer) >= chunk_size:  # Buffer full
                    yield buffer  # Return a chunk
                    buffer = []  # Clear buffer
            if buffer:  # Handle remaining data
                yield buffer
```

**Purpose**: Load large JSON/JSONL files in chunks to avoid memory overflow

**Why It's Needed**:
- Large files (GB level) cannot be loaded into memory at once
- Chunk processing allows processing block by block with controllable memory usage

**Detailed Flow**:

#### Format Detection

```python
first_char = f.read(1)  # Read first character
f.seek(0)  # Reset file pointer
```

**Detection Logic**:
- `[` → JSON array format: `[{...}, {...}, ...]`
- Other → JSONL format: one JSON object per line

---

#### JSON Array Format Processing

```python
if first_char == "[":
    text = f.read()  # Read entire file into memory
    parser = Parser()
    arr = parser.parse(text)  # Parse as Python list
    for i in range(0, len(arr), chunk_size):
        yield arr[i:i + chunk_size]  # Slice to generate chunks
```

**Flow**:
1. Read entire file (assuming file isn't too large)
2. Parse as Python list
3. Slice by `chunk_size`, generator returns each slice

**Limitations**:
- File must be fully loaded into memory first
- Will fail if file is too large (exceeds memory)
- Better suited for medium-sized JSON array files

**Example**:
```python
# File content: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
# chunk_size = 3

# Generated chunks:
# [1, 2, 3]
# [4, 5, 6]
# [7, 8, 9]
# [10]
```

---

#### JSONL Format Processing

```python
else:  # JSONL
    parser = Parser()
    buffer = []
    for line in f:
        line = line.strip()
        if not line:
            continue
        buffer.append(parser.parse(line))
        if len(buffer) >= chunk_size:
            yield buffer
            buffer = []
    if buffer:
        yield buffer
```

**Flow**:

1. **Read Line by Line**: Don't load entire file at once
   - Memory-friendly: only process one line at a time

2. **Parse Each Line**:
   - Each line is an independent JSON object
   - Use custom Parser to parse

3. **Buffer Accumulation**:
   - Add parsed objects to buffer
   - When buffer reaches `chunk_size`, generate a chunk

4. **Handle Remaining**:
   - End of file may have data less than `chunk_size`
   - Needs separate handling

**Advantages**:
- ✅ Memory efficient: doesn't need to load entire file
- ✅ Supports very large files (GB level)
- ✅ Line-by-line processing, memory usage = `chunk_size` × average document size

**Example**:
```python
# File content (JSONL):
# {"id": 1}
# {"id": 2}
# {"id": 3}
# {"id": 4}
# {"id": 5}
# chunk_size = 2

# Generated chunks:
# [{"id": 1}, {"id": 2}]
# [{"id": 3}, {"id": 4}]
# [{"id": 5}]
```

**Generator Advantages**:
- Uses `yield` instead of `return`, generator function
- Generates chunks on demand, doesn't generate all chunks at once
- Smaller memory footprint

---

### 5.2 Application Scenarios of Chunk Processing

**Typical Scenario**: Processing social media data files
- File size: Several GB to tens of GB
- Record count: Millions to tens of millions
- Cannot be loaded into memory at once

**Solution**:
1. Load file in chunks
2. Perform local aggregation on each chunk
3. Merge aggregation results from all chunks

**Example Code Structure**:
```python
# Initialize global aggregation containers
global_results = {}

# Process in chunks
for chunk in load_json_chunks("large_file.jsonl", chunk_size=5000):
    # Process current chunk
    chunk_results = process_chunk(chunk)
    
    # Merge into global results
    global_results = merge(global_results, chunk_results)
```

---

## 6. Partial Aggregation Merging

### 6.1 PartialAgg Class

```python
class PartialAgg:
    """merge of partial aggregation results"""
    
    @staticmethod
    def merge_count(v1, v2):
        return v1 + v2
    
    @staticmethod
    def merge_sum(v1, v2):
        return v1 + v2
    
    @staticmethod
    def merge_max(v1, v2):
        return max(v1, v2)
    
    @staticmethod
    def merge_min(v1, v2):
        return min(v1, v2)
    
    @staticmethod
    def merge_avg(avg1, count1, avg2, count2):
        # weighted average
        total = count1 + count2
        return (avg1 * count1 + avg2 * count2) / total, total
```

**Purpose**: Merge aggregation results from different data chunks

**Why It's Needed**:
- When data is processed in chunks, each chunk produces partial aggregation results
- Need to correctly merge these partial results to get global aggregation result

**Detailed Analysis**:

---

#### merge_count() - Merge Count

```python
@staticmethod
def merge_count(v1, v2):
    return v1 + v2
```

**Logic**: Counts can be directly added

**Example**:
```python
# Chunk 1 count: {"NYC": 5, "LA": 3}
# Chunk 2 count: {"NYC": 4, "LA": 2}
# Merged result: {"NYC": 9, "LA": 5}
```

---

#### merge_sum() - Merge Sum

```python
@staticmethod
def merge_sum(v1, v2):
    return v1 + v2
```

**Logic**: Sums can also be directly added

**Example**:
```python
# Chunk 1 sales sum: {"NYC": 1000, "LA": 800}
# Chunk 2 sales sum: {"NYC": 1200, "LA": 900}
# Merged result: {"NYC": 2200, "LA": 1700}
```

---

#### merge_max() - Merge Maximum

```python
@staticmethod
def merge_max(v1, v2):
    return max(v1, v2)
```

**Logic**: Take maximum of two values

**Example**:
```python
# Chunk 1 max sales: {"NYC": 500, "LA": 400}
# Chunk 2 max sales: {"NYC": 600, "LA": 350}
# Merged result: {"NYC": 600, "LA": 400}
```

---

#### merge_min() - Merge Minimum

```python
@staticmethod
def merge_min(v1, v2):
    return min(v1, v2)
```

**Logic**: Take minimum of two values

---

#### merge_avg() - Merge Average (Most Complex)

```python
@staticmethod
def merge_avg(avg1, count1, avg2, count2):
    # weighted average
    total = count1 + count2
    return (avg1 * count1 + avg2 * count2) / total, total
```

**Problem**: Averages cannot be directly averaged!

**Wrong Example**:
```python
# Chunk 1: average sales 100, 10 records
# Chunk 2: average sales 200, 20 records
# Wrong merge: (100 + 200) / 2 = 150 ❌
# Correct should be: (100*10 + 200*20) / (10+20) = 166.67 ✅
```

**Correct Method**: Weighted Average

1. **Required Information**:
   - `avg1`, `count1`: First chunk's average and record count
   - `avg2`, `count2`: Second chunk's average and record count

2. **Calculation Formula**:
   ```
   Global Average = (Average1 × Count1 + Average2 × Count2) / (Count1 + Count2)
   ```

3. **Mathematical Principle**:
   ```
   Sum1 = Average1 × Count1
   Sum2 = Average2 × Count2
   Global Sum = Sum1 + Sum2
   Global Average = Global Sum / (Count1 + Count2)
   ```

**Return Value**:
- Returns two values: `(merged average, total record count)`
- Total record count needs to be preserved for subsequent merges

**Example**:
```python
# Chunk 1: NYC average sales 100, 5 records
# Chunk 2: NYC average sales 150, 4 records

avg, count = PartialAgg.merge_avg(100, 5, 150, 4)
# avg = (100*5 + 150*4) / (5+4) = 122.22
# count = 9
```

**Multi-Chunk Merging**:
```python
# Initial
avg, count = 100, 5

# Merge chunk 2
avg, count = PartialAgg.merge_avg(avg, count, 150, 4)
# Result: 122.22, 9

# Merge chunk 3
avg, count = PartialAgg.merge_avg(avg, count, 120, 6)
# Result: ((122.22*9) + (120*6)) / (9+6) = 121.33, 15
```

---

### 6.2 Map-Reduce Pattern

**Map-Reduce is a classic pattern in distributed computing**:

1. **Map Phase** (Mapping):
   - Split large dataset into multiple chunks
   - Independently perform local aggregation calculations on each chunk
   - Output partial aggregation results

2. **Reduce Phase** (Reduction):
   - Collect all partial aggregation results
   - Use merge functions to combine results
   - Output final global result

**Application in This Project**:

```python
# Map phase: each chunk independently aggregates
for chunk in load_json_chunks(filepath):
    chunk_results = aggregate(chunk)  # Local aggregation
    partial_results.append(chunk_results)

# Reduce phase: merge all local results
final_results = merge_all(partial_results)  # Global merge
```

**Advantages**:
- Parallelizable: Map operations for each chunk can be executed in parallel
- Memory-friendly: Doesn't need to load entire dataset
- Scalable: Can handle data of arbitrary size

**Current Implementation**:
- Map phase: Process each chunk sequentially (can be changed to parallel)
- Reduce phase: Merge incrementally (incremental merge)

---

## 7. Practical Application Case

### 7.1 calculate_average_engagement_by_location()

```python
def calculate_average_engagement_by_location(filepath, chunk_size=5000):
    """
    Calculates the Average Engagement Rate (AER) grouped by IP location 
    for large datasets using chunked processing and partial aggregation merging.
    This demonstrates the project's scaling requirement.
    AER = (Total Reposts + Total Comments + Total Attitudes) / Total Posts
    """
```

**Purpose**: Calculate Average Engagement Rate (AER) grouped by IP location

**Business Context**:
- Social media data analysis
- Want to know user engagement rates in different regions
- Engagement Rate = (Reposts + Comments + Likes) / Posts

**Data Format Assumption**:
```json
{
    "ip_location": "NYC",
    "reposts_count": 10,
    "comments_count": 5,
    "attitudes_count": 20,
    "text": "..."
}
```

---

### 7.2 Step 1: Initialize Global Aggregation Containers

```python
# 1. initialize four global partial result containers
# Dictionaries to store merged partial aggregation results globally
partial_counts = {}          # Total posts per location
partial_reposts_sums = {}    # Total reposts per location
partial_comments_sums = {}   # Total comments per location
partial_attitudes_sums = {}  # Total likes per location
```

**Why Four Containers Are Needed**:
- Need to track four different metrics separately
- Each metric requires grouped aggregation (by `ip_location`)

**Data Structure**:
```python
{
    "NYC": 100,  # Number of posts/reposts/comments/likes in NYC
    "LA": 50,
    ...
}
```

---

### 7.3 Step 2: Chunk Processing (Map Phase)

```python
# 2. process the file chunk by chunk
for chunk in load_json_chunks(filepath, chunk_size):
    coll = Collection(chunk)  # Convert chunk to Collection object
    
    # local aggregation calculations (Grouped by "ip_location")
    chunk_counts = coll.aggregate("ip_location", agg_count())
    chunk_reposts = coll.aggregate("ip_location", agg_sum("reposts_count"))
    chunk_comments = coll.aggregate("ip_location", agg_sum("comments_count"))
    chunk_attitudes = coll.aggregate("ip_location", agg_sum("attitudes_count"))
```

**Detailed Flow**:

1. **Load Chunk**: `load_json_chunks()` generator returns a list of documents for one chunk

2. **Create Collection**: Wrap chunk data, use query API

3. **Local Aggregation**: Perform four aggregation operations on current chunk
   - `chunk_counts`: Count by location (how many posts per location)
   - `chunk_reposts`: Sum reposts by location
   - `chunk_comments`: Sum comments by location
   - `chunk_attitudes`: Sum likes by location

**Local Result Example**:
```python
# Assuming current chunk has 5000 records, after processing:
chunk_counts = {"NYC": 200, "LA": 150, "SF": 100}
chunk_reposts = {"NYC": 1000, "LA": 750, "SF": 500}
chunk_comments = {"NYC": 500, "LA": 375, "SF": 250}
chunk_attitudes = {"NYC": 2000, "LA": 1500, "SF": 1000}
```

---

### 7.4 Step 3: Merge Local Results (Reduce Phase)

```python
# 3. merge Local Results
    
# Merge Counts (Total Posts)
for loc, count in chunk_counts.items():
    current_count = partial_counts.get(loc, 0)
    # use PartialAgg.merge_count to combine current global total with local chunk total
    partial_counts[loc] = PartialAgg.merge_count(current_count, count)
    
# Merge Reposts Sums
for loc, total in chunk_reposts.items():
    current_total = partial_reposts_sums.get(loc, 0)
    # Use PartialAgg.merge_sum for addition
    partial_reposts_sums[loc] = PartialAgg.merge_sum(current_total, total)
    
# Merge Comments Sums
for loc, total in chunk_comments.items():
    current_total = partial_comments_sums.get(loc, 0)
    partial_comments_sums[loc] = PartialAgg.merge_sum(current_total, total)
    
# Merge Attitudes (Likes) Sums
for loc, total in chunk_attitudes.items():
    current_total = partial_attitudes_sums.get(loc, 0)
    partial_attitudes_sums[loc] = PartialAgg.merge_sum(current_total, total)
```

**Merge Logic**:

For each location and each metric:
1. Get current global value (default to 0 if doesn't exist)
2. Use merge function to combine global value and local value
3. Update global value

**Example Execution**:

```python
# Initial global state (after processing first chunk)
partial_counts = {"NYC": 200, "LA": 150}

# Second chunk results
chunk_counts = {"NYC": 300, "SF": 100}

# Merge process:
# NYC: merge_count(200, 300) = 500
# LA: remains 150 (second chunk has no LA)
# SF: merge_count(0, 100) = 100 (new location)

# Merged global state
partial_counts = {"NYC": 500, "LA": 150, "SF": 100}
```

**Incremental Merging**:
- After processing each chunk, immediately merge into global results
- Don't need to store local results from all chunks
- Small memory footprint

---

### 7.5 Step 4: Calculate Final Average

```python
# 4. Calculate Final Average Engagement Rate (Final Calculation)
final_results = {}
for loc in partial_counts:
    # Get all global sums
    total_interactions = (
        partial_reposts_sums.get(loc, 0) +
        partial_comments_sums.get(loc, 0) +
        partial_attitudes_sums.get(loc, 0)
    )
    total_posts = partial_counts[loc]
    
    # Calculate Average Engagement Rate, prevent division by zero
    avg_engagement_rate = total_interactions / total_posts if total_posts else 0
    
    final_results[loc] = {
        "Total_Posts": total_posts,
        "Avg_Engagement_Rate": avg_engagement_rate
    }

return final_results
```

**Calculation Flow**:

1. **Iterate Through All Locations**: Use `partial_counts.keys()`

2. **Calculate Total Interactions**:
   ```python
   total_interactions = reposts + comments + likes
   ```

3. **Calculate Average Engagement Rate**:
   ```python
   AER = total_interactions / total_posts
   ```

4. **Prevent Division by Zero**: If `total_posts` is 0, return 0

**Result Format**:
```python
{
    "NYC": {
        "Total_Posts": 1000,
        "Avg_Engagement_Rate": 3.5  # Average 3.5 interactions per post
    },
    "LA": {
        "Total_Posts": 500,
        "Avg_Engagement_Rate": 2.8
    }
}
```

**Complete Example**:

Assuming global state after processing all chunks:
```python
partial_counts = {"NYC": 1000, "LA": 500}
partial_reposts_sums = {"NYC": 2000, "LA": 800}
partial_comments_sums = {"NYC": 1000, "LA": 400}
partial_attitudes_sums = {"NYC": 500, "LA": 200}
```

Calculate NYC:
```python
total_interactions = 2000 + 1000 + 500 = 3500
total_posts = 1000
AER = 3500 / 1000 = 3.5
```

Calculate LA:
```python
total_interactions = 800 + 400 + 200 = 1400
total_posts = 500
AER = 1400 / 500 = 2.8
```

Final Result:
```python
{
    "NYC": {"Total_Posts": 1000, "Avg_Engagement_Rate": 3.5},
    "LA": {"Total_Posts": 500, "Avg_Engagement_Rate": 2.8}
}
```

---

### 7.6 Algorithm Summary

**Complete Flow Diagram**:

```
File (Large File)
    ↓
[Chunk Loading] ← chunk_size=5000
    ↓
Chunk 1 → [Local Aggregation] → Partial Result 1
Chunk 2 → [Local Aggregation] → Partial Result 2
Chunk 3 → [Local Aggregation] → Partial Result 3
...   ...                        ...
    ↓
[Merge Partial Results] ← Using PartialAgg
    ↓
Global Aggregation Results
    ↓
[Calculate Average]
    ↓
Final Result (AER grouped by location)
```

**Time Complexity**:
- Map phase: O(n), n is total record count
- Reduce phase: O(m), m is number of unique locations (usually small)
- Total complexity: O(n)

**Space Complexity**:
- Chunk size: O(chunk_size)
- Global aggregation: O(m), m is number of unique locations
- Total space: O(chunk_size + m)

**Scalability**:
- ✅ Supports files of arbitrary size (by adjusting chunk_size)
- ✅ Can parallelize Map phase (multi-threading/multi-processing)
- ✅ Can distribute processing (multiple machines)

---

## Summary

This project implements a complete **database query system**, from bottom layer to application layer:

1. **Bottom Layer Parsing**: Custom JSON parser (Tokenizer + Parser)
2. **Data Operations**: Collection class provides rich query API
3. **Aggregation Functions**: Multiple aggregation function support
4. **Large File Processing**: Chunk loading and partial aggregation merging
5. **Practical Application**: Calculate average engagement rate by location

**Technical Highlights**:
- Recursive descent parser
- Hash join algorithm
- Map-Reduce pattern
- Memory-friendly chunk processing
- Correct aggregation result merging

**Applicable Scenarios**:
- Social media data analysis
- Log data analysis
- Large-scale JSON data querying
- Data warehouse query system prototype

