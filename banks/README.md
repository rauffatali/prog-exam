# Question Bank JSON Schema — Official Specification v1.1

**Target:** Offline Python Exam System  
**Last Updated:** 2025-11-07  
**Applies To:** Group 1 and Group 2 banks (plaintext → encrypted)

---

## 1. Overview

Each question bank is a single JSON file containing:
- **25 total tasks**: 10 Easy, 10 Medium, 5 Hard
- **15 test cases per task** (hidden from students during exam)
- **Metadata**: time limits, memory limits, I/O modes, checkers

**Encryption:** Plaintext JSON is encrypted using **Fernet (AES-128-CBC with HMAC)** before distribution. Only encrypted `.enc` files are deployed to exam machines.

---

## 2. Top-Level Structure

```json
{
  "group": "group1",
  "version": "2025.11.01",
  "network_monitoring": {
    "enabled": false,
    "check_interval_seconds": 15
  },
  "ai_detection": {
    "enabled": true,
    "check_interval_seconds": 60
  },
  "difficulties": {
    "easy": [ /* 20 Task objects */ ],
    "medium": [ /* 20 Task objects */ ],
    "hard": [ /* 20 Task objects */ ]
  }
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `group` | string | ✓ | Group identifier: `"group1"` or `"group2"` |
| `version` | string | ✓ | Bank version (ISO date recommended: `YYYY.MM.DD`) |
| `network_monitoring` | object | ✗ | Network monitoring configuration (see §2.1) |
| `ai_detection` | object | ✗ | AI detection configuration (see §2.2) |
| `difficulties` | object | ✓ | Contains `easy`, `medium`, `hard` arrays |
| `difficulties.easy` | array | ✓ | Array of 20 Easy task objects |
| `difficulties.medium` | array | ✓ | Array of 20 Medium task objects |
| `difficulties.hard` | array | ✓ | Array of 20 Hard task objects |

### 2.1 Network Monitoring Configuration

Controls whether the exam system monitors internet connectivity during the exam.

```json
"network_monitoring": {
  "enabled": true,
  "check_interval_seconds": 15
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable/disable network connectivity monitoring |
| `check_interval_seconds` | integer | `15` | How often to check for internet connection (in seconds) |

**Behavior when enabled:**
- Pre-exam check: Blocks exam start if internet is detected
- During exam: Checks connectivity every `check_interval_seconds`
- If connectivity detected: Pauses exam until student disconnects
- All checks are logged to `session.log`

**Use case:** Enable for high-stakes exams where offline work is mandatory.

### 2.2 AI Detection Configuration

Controls whether the exam system detects and blocks AI coding assistants.

```json
"ai_detection": {
  "enabled": true,
  "check_interval_seconds": 60
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable/disable AI tool detection |
| `check_interval_seconds` | integer | `60` | How often to check for AI tools during exam (in seconds) |

**Behavior when enabled:**
- Pre-exam check: Blocks exam start if AI tools detected (GitHub Copilot, Tabnine, Cursor, Codeium, etc.)
- During exam: Monitors for AI tools every `check_interval_seconds`
- Detects: Running processes, clipboard patterns, suspicious paste activity
- All detections are logged to `session.log`

**Use case:** Enable to prevent use of AI autocomplete tools. Set `enabled: false` for practice exams or collaborative sessions.

---

## 3. Task Object Schema

### 3.1 Core Fields

```json
{
  "id": "E07",
  "title": "Sum of Unique",
  "prompt": "Given a list of integers, return the sum of unique values.\n\nInput format:\n- First line: n (number of integers)\n- Second line: n space-separated integers\n\nOutput format:\n- Single integer: sum of unique values",
  "io": {
    "mode": "stdin_stdout",
    "entrypoint": null
  },
  "tests": [ /* 15 TestCase objects */ ],
  "time_limit_ms": 2000,
  "memory_limit_mb": 256,
  "checker": "exact_match",
  "hints": ["Use collections.Counter", "Consider set operations"],
  "tags": ["lists", "counting", "sets"],
  "visible_sample": {
    "input": "4\n2 2 3 4\n",
    "output": "7\n"
  }
}
```

### 3.2 Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✓ | Unique task identifier: `E01`-`E20`, `M01`-`M20`, `H01`-`H20` |
| `title` | string | ✓ | Short descriptive title (shown to students) |
| `prompt` | string | ✓ | Full problem statement with I/O format details |
| `io` | object | ✓ | I/O mode configuration (see §3.3) |
| `tests` | array | ✓ | Array of exactly 15 test case objects (see §4) |
| `time_limit_ms` | integer | ✓ | Per-test timeout in milliseconds (default: 2000) |
| `memory_limit_mb` | integer | ✓ | Memory limit in MB (default: 256; enforced on Unix only) |
| `checker` | string or null | ✓ | Checker function name or `null` for default (see §5) |
| `hints` | array | ✗ | Internal hints for task authors (never shown to students) |
| `tags` | array | ✗ | Categorization tags for analysis |
| `visible_sample` | object or null | ✗ | One sample I/O pair shown in `qN` command (see §3.4) |

### 3.3 I/O Mode Object

**Mode: `stdin_stdout`** (Standard input/output redirection)

```json
{
  "mode": "stdin_stdout",
  "entrypoint": null
}
```

- Student writes a full program reading from `stdin` and printing to `stdout`.
- Grader feeds `test.input` via subprocess stdin, captures stdout.

**Mode: `function`** (Callable function with arguments)

```json
{
  "mode": "function",
  "entrypoint": "count_primes"
}
```

- Student implements a specific function in `qN.py`.
- Grader imports the module and calls `entrypoint(*test.args)`, compares to `test.ret`.

### 3.4 Visible Sample (Optional)

Displayed to students via `q1`/`q2`/`q3` commands as a worked example.

```json
"visible_sample": {
  "input": "3\n10 10 10\n",
  "output": "0\n"
}
```

- For `stdin_stdout` mode: `input` and `output` strings.
- For `function` mode: Use `args` and `ret` instead.

---

## 4. Test Case Schema

### 4.1 For `stdin_stdout` Mode

```json
{
  "input": "5\n1 1 2 3 3\n",
  "output": "5\n"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `input` | string | ✓ | Full stdin content (include `\n` line endings) |
| `output` | string | ✓ | Expected stdout content (trailing whitespace stripped before comparison) |

**Notes:**
- Always include trailing newlines in `input` and `output` if expected.
- The grader normalizes by calling `rstrip()` on both student and expected output before comparison.

### 4.2 For `function` Mode

```json
{
  "args": [[2, 3, 4, 5, 6]],
  "ret": 3
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `args` | array | ✓ | Positional arguments as a list (e.g., `[[1, 2, 3]]` for one list argument) |
| `ret` | any | ✓ | Expected return value (any JSON-serializable type) |

**Example for multiple arguments:**

```json
{
  "args": [10, 20],
  "ret": 30
}
```

This calls `entrypoint(10, 20)` and expects `30`.

---

## 5. Checker Functions

Checkers validate student output against expected output. Default is `exact_match`.

### 5.1 Built-in Checkers

| Checker Name | Description | Use Case |
|--------------|-------------|----------|
| `exact_match` | Case-sensitive string equality after `rstrip()` | Most tasks |
| `float_isclose` | Floating-point comparison with tolerance (`rel_tol=1e-9`) | Scientific computation |
| `unordered_list_equal` | Order-independent list comparison | Sets, unordered results |

### 5.2 Specifying a Checker

Set the `checker` field to:
- `"exact_match"` (default)
- `"float_isclose"`
- `"unordered_list_equal"`
- `null` → defaults to `"exact_match"`

**Example:**

```json
{
  "id": "M12",
  "title": "Prime Factors",
  "checker": "unordered_list_equal",
  "tests": [
    {"input": "12\n", "output": "2 2 3\n"}
  ]
}
```

---

## 6. Example: Complete Task (stdin_stdout)

```json
{
  "id": "E01",
  "title": "String Reversal",
  "prompt": "Write a program that reads a line of text and prints its reverse.\n\nInput: A single line of text (max 1000 characters)\nOutput: The reversed string",
  "io": {
    "mode": "stdin_stdout",
    "entrypoint": null
  },
  "tests": [
    {"input": "hello\n", "output": "olleh\n"},
    {"input": "world\n", "output": "dlrow\n"},
    {"input": "Python\n", "output": "nohtyP\n"},
    {"input": "a\n", "output": "a\n"},
    {"input": "ab\n", "output": "ba\n"},
    {"input": "12345\n", "output": "54321\n"},
    {"input": "Hello World\n", "output": "dlroW olleH\n"},
    {"input": "racecar\n", "output": "racecar\n"},
    {"input": "step on no pets\n", "output": "step on no pets\n"},
    {"input": "The quick brown fox\n", "output": "xof nworb kciuq ehT\n"},
    {"input": "!@#$%\n", "output": "%$#@!\n"},
    {"input": "  spaces  \n", "output": "  secaps  \n"},
    {"input": "NoSpaces\n", "output": "secapSoN\n"},
    {"input": "123 abc 456\n", "output": "654 cba 321\n"},
    {"input": "Z\n", "output": "Z\n"}
  ],
  "time_limit_ms": 1000,
  "memory_limit_mb": 128,
  "checker": "exact_match",
  "hints": ["Use string slicing", "s[::-1] reverses a string"],
  "tags": ["strings", "basics"],
  "visible_sample": {
    "input": "sample\n",
    "output": "elpmas\n"
  }
}
```

---

## 7. Example: Complete Task (function mode)

```json
{
  "id": "M05",
  "title": "Prime Counter",
  "prompt": "Implement the function count_primes(numbers: list[int]) -> int that counts how many prime numbers are in the given list.\n\nA prime number is a natural number greater than 1 that has no positive divisors other than 1 and itself.\n\nFunction signature:\n  def count_primes(numbers: list[int]) -> int:",
  "io": {
    "mode": "function",
    "entrypoint": "count_primes"
  },
  "tests": [
    {"args": [[2, 3, 4, 5]], "ret": 3},
    {"args": [[7, 8, 9, 10, 11]], "ret": 2},
    {"args": [[1, 2, 3]], "ret": 2},
    {"args": [[10, 20, 30]], "ret": 0},
    {"args": [[13]], "ret": 1},
    {"args": [[1]], "ret": 0},
    {"args": [[2]], "ret": 1},
    {"args": [[-5, -3, 0, 1, 2]], "ret": 1},
    {"args": [[97, 98, 99, 100]], "ret": 1},
    {"args": [[11, 13, 17, 19]], "ret": 4},
    {"args": [list(range(1, 21))], "ret": 8},
    {"args": [[4, 6, 8, 10]], "ret": 0},
    {"args": [[29, 31, 37]], "ret": 3},
    {"args": [[2, 2, 2, 2]], "ret": 4},
    {"args": [[]], "ret": 0}
  ],
  "time_limit_ms": 2000,
  "memory_limit_mb": 256,
  "checker": "exact_match",
  "hints": ["Implement is_prime helper", "Optimize with sqrt(n) upper bound"],
  "tags": ["math", "primes", "lists"],
  "visible_sample": null
}
```

---

## 8. Validation Rules

Use `tools/verify_bank.py` to enforce these rules:

### 8.1 Structural Requirements
- ✓ Exactly 20 tasks per difficulty level (60 total)
- ✓ Each task has exactly 15 test cases
- ✓ All required fields are present
- ✓ `id` values are unique within the bank

### 8.2 Task Constraints
- Task IDs follow naming: `E01`-`E20`, `M01`-`M20`, `H01`-`H20`
- `time_limit_ms` > 0 (typical: 1000-5000)
- `memory_limit_mb` > 0 (typical: 128-512)
- `io.mode` is either `"stdin_stdout"` or `"function"`
- If `io.mode == "function"`, `io.entrypoint` must be a valid Python identifier

### 8.3 Test Case Constraints
- For `stdin_stdout`: each test has `input` and `output` strings
- For `function`: each test has `args` (array) and `ret` (any JSON type)
- All test cases for a task must use the same structure

### 8.4 Checker Constraints
- `checker` must be `null` or a recognized checker name
- Custom checkers must be implemented in `runner/grader.py`

---

## 9. Complete Bank Example (Minimal)

```json
{
  "group": "group1",
  "version": "2025.11.01",
  "network_monitoring": {
    "enabled": false,
    "check_interval_seconds": 15
  },
  "ai_detection": {
    "enabled": true,
    "check_interval_seconds": 60
  },
  "difficulties": {
    "easy": [
      {
        "id": "E01",
        "title": "Hello World",
        "prompt": "Print 'Hello, World!' to stdout.",
        "io": {"mode": "stdin_stdout", "entrypoint": null},
        "tests": [
          {"input": "", "output": "Hello, World!\n"},
          {"input": "", "output": "Hello, World!\n"},
          {"input": "", "output": "Hello, World!\n"},
          {"input": "", "output": "Hello, World!\n"},
          {"input": "", "output": "Hello, World!\n"},
          {"input": "", "output": "Hello, World!\n"},
          {"input": "", "output": "Hello, World!\n"},
          {"input": "", "output": "Hello, World!\n"},
          {"input": "", "output": "Hello, World!\n"},
          {"input": "", "output": "Hello, World!\n"},
          {"input": "", "output": "Hello, World!\n"},
          {"input": "", "output": "Hello, World!\n"},
          {"input": "", "output": "Hello, World!\n"},
          {"input": "", "output": "Hello, World!\n"},
          {"input": "", "output": "Hello, World!\n"}
        ],
        "time_limit_ms": 1000,
        "memory_limit_mb": 128,
        "checker": "exact_match",
        "hints": [],
        "tags": ["basics"],
        "visible_sample": {"input": "", "output": "Hello, World!\n"}
      }
      // ... 19 more easy tasks
    ],
    "medium": [ /* 20 medium tasks */ ],
    "hard": [ /* 20 hard tasks */ ]
  }
}
```

---

## 10. Authoring Workflow

1. **Create plaintext JSON** following this schema
2. **Validate** using `tools/verify_bank.py --bank bank_group1.json`
3. **Generate key** using `tools/keygen.py --out GROUP1.key`
4. **Encrypt** using `tools/build_bank.py --in bank_group1.json --out banks/bank_group1.enc --key-file GROUP1.key`
5. **Verify encrypted** using `tools/verify_bank.py --bank banks/bank_group1.enc --key-file GROUP1.key`
6. **Store key securely** (password manager, not in version control)
7. **Distribute only** the `.enc` file to exam machines

---

## 11. Security Notes

- **Never commit** plaintext banks or keys to public repositories
- **Rotate keys** after each exam session using `tools/rotate_key.py`
- **Keys are entered** by invigilators at runtime (never bundled with binaries)
- **Encrypted banks** use Fernet with authenticated encryption (AES-128-CBC + HMAC-SHA256)
- **Test cases** remain hidden from students; only pass/fail verdicts are shown

---

## 12. File Naming Conventions

| File Type | Naming Pattern | Example |
|-----------|----------------|---------|
| Plaintext bank | `bank_group[N].json` | `bank_group1.json` |
| Encrypted bank | `bank_group[N].enc` | `bank_group1.enc` |
| Encryption key | `GROUP[N].key` | `GROUP1.key` |

---

## 13. Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-01 | Initial schema specification |
| 1.1 | 2025-11-07 | Added optional `network_monitoring` and `ai_detection` configuration objects |

---

**END OF SPECIFICATION**

