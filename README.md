# Offline Python Exam System — Teacher Guide

**Version:** 0.1.2  
**Last Updated:** 2025-11-03  
**Target Audience:** Exam Teachers and Technical Staff

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Before Exam Day (Preparation)](#before-exam-day-preparation)
3. [Exam Configuration (Optional)](#exam-configuration-optional)
4. [Day of Exam (Installation & Setup)](#day-of-exam-installation--setup)
5. [Exam Start (Per Student)](#exam-start-per-student)
6. [During Exam](#during-exam)
7. [After Exam (Collection)](#after-exam-collection)
8. [Troubleshooting](#troubleshooting)
9. [Student Commands Reference](#student-commands-reference)

---

## System Overview

**What students will do:**
- Type commands to view tasks (`q1`, `q2`, `q3`, ...)
- Edit Python files in their preferred editor
- Test their code (`test q1`)
- Debug their code (`debug q1`)
- Submit solutions (`submit q1`)
- Finish exam (`finish`) → creates ZIP file

**What you need:**
- Encrypted question banks (`bank_group1.enc`, `bank_group2.enc`)
- Decryption key (provided by coordinator)
- Python 3.10+ with virtual environment
- Exam runner application
- **(Optional)** Exam configuration file (`config.json`)

---

## Before Exam Day (Preparation)

### Task 1: Obtain Exam Materials

**Get from exam coordinator:**
- [ ] Encrypted question bank file (`bank_group1.enc` or `bank_group2.enc`)
- [ ] Decryption key (Base64 string like `EE2GANWkqT...` OR password)
- [ ] Exam system files (full `prog-exam/` directory)
- [ ] **(Optional)** Exam configuration file (`config.json`)

**Key security:**
- Store key in password manager OR sealed envelope
- **Never save key on student machines**
- Use separate keys for each group

**Configuration (Optional):**
- If provided, `config.json` customizes exam parameters
- Controls number of questions, difficulty distribution, point weights
- See [Exam Configuration](#exam-configuration-optional) section below

### Task 2: Test the System (One Machine)

**On your personal machine or test computer:**

1. Copy exam system directory
2. Verify files exist:
   ```powershell
   Test-Path prog-exam\banks\bank_group1.enc
   Test-Path prog-exam\requirements.txt
   Test-Path prog-exam\main.py
   ```

3. Test decryption (optional, if you have key):
   ```powershell
   cd prog-exam
   # Option A: Using key file
   python tools\verify_bank.py --bank banks\bank_group1.enc --key-file GROUP1.key

   # Option B: Using password directly
   python tools\verify_bank.py --bank banks\bank_group1.enc --password
   ```
   Expected: `[OK] Bank validation PASSED`

4. Test the full exam system:
   ```powershell
   cd prog-exam

   # Option A: Test with encrypted bank (requires key)
   python main.py --bank bank_group1.enc
   # Enter the decryption key when prompted
   # Expected: System starts and prompts for student authentication

   # Option B: Direct test with bank_test.json (no key needed)
   python main.py --bank bank_test.json
   ```
   This tests the complete exam workflow using either encrypted or unencrypted question banks.

---

## Exam Configuration

Teachers can customize exam parameters using a configuration file.

### What Can Be Configured

- **Number of questions** per student (default: 3)
- **Distribution of difficulty** (how many easy, medium, hard)
- **Point weights** for each difficulty level (default: 5 points each)
- **Maximum total points** for the exam (default: 15)
- **Exam time limit** in minutes (default: 180, -1 for unlimited time)
- **Working directory postfix** for student folders (default: "TP_TEST")

### Creating a Configuration

**Option 1: Use Interactive Tool (Recommended)**

```powershell
cd prog-exam
python tools\config_helper.py
```

Select option 1 (Create new configuration) and follow the prompts:
```
Total number of questions per student: 3

Now specify how many of each difficulty (must sum to 3):
  Easy questions: 1
  Medium questions: 1
  Hard questions: 1

Now specify the point value for each difficulty level:
  Points for each Easy question: 5
  Points for each Medium question: 5
  Points for each Hard question: 5

Calculated maximum points: 15.0
Is this correct? (y/n): y

Save to config.json? (y/n): y
```

**Option 2: Edit Manually**

Edit `config.json`:
```json
{
  "total_questions": 3,
  "easy_count": 1,
  "medium_count": 1,
  "hard_count": 1,
  "easy_weight": 5.0,
  "medium_weight": 5.0,
  "hard_weight": 5.0,
  "max_points": 15.0,
  "exam_time_minutes": 180,
  "work_dir_postfix": "TP_TEST"
}
```

**Validation Rules:**
1. Question counts must sum to total: `easy_count + medium_count + hard_count = total_questions`
2. Weights must sum to max points: `(easy_count × easy_weight) + (medium_count × medium_weight) + (hard_count × hard_weight) = max_points`

### Validating Configuration

Before deploying, validate your configuration:
```powershell
python tools\config_helper.py
# Choose option 2 (Validate existing configuration)
```

### Common Examples

**Standard (Default):**
```json
{
  "total_questions": 3,
  "easy_count": 1, "medium_count": 1, "hard_count": 1,
  "easy_weight": 5.0, "medium_weight": 5.0, "hard_weight": 5.0,
  "max_points": 15.0,
  "exam_time_minutes": 180,
  "work_dir_postfix": "TP_EVAL"
}
```

**Weighted by Difficulty:**
```json
{
  "total_questions": 3,
  "easy_count": 1, "medium_count": 1, "hard_count": 1,
  "easy_weight": 3.0, "medium_weight": 5.0, "hard_weight": 7.0,
  "max_points": 15.0,
  "exam_time_minutes": 180,
  "work_dir_postfix": "TP_TEST"
}
```

**5 Questions, 20 Points:**
```json
{
  "total_questions": 5,
  "easy_count": 2, "medium_count": 2, "hard_count": 1,
  "easy_weight": 3.0, "medium_weight": 4.0, "hard_weight": 6.0,
  "max_points": 20.0,
  "exam_time_minutes": 180,
  "work_dir_postfix": "TP_EXAM"
}
```

### Deploying with Configuration

1. Create or obtain `config.json`
2. Place it in the same directory as the exam executable (or `main.py`)
3. Deploy both together to student machines

**If no configuration file is provided:** System uses default values (3 questions, 15 points, equal weights).

**For more details:** See `tools/README.md`

---

## Building Executable (Before Exam)

**Alternative to virtual environment:** Build a single-file executable that students can run directly.

### Option A: Build on Windows

**On your development machine (requires internet):**

```powershell
cd prog-exam
.\scripts\build_windows.ps1
```

**Output:** `exam.exe` in root directory

**With options:**
```powershell
# Clean previous builds
.\scripts\build_windows.ps1 -Clean

# Offline build (requires vendor/ directory with wheels)
.\scripts\build_windows.ps1 -Offline
```

### Option B: Build on Linux/macOS

**On your development machine:**

```bash
cd prog-exam
chmod +x scripts/build_unix.sh
./scripts/build_unix.sh
```

**Output:** `exam` executable in root directory

**With options:**
```bash
# Clean previous builds
./scripts/build_unix.sh --clean

# Offline build
./scripts/build_unix.sh --offline
```

### Deploying Executable

**Distribute to exam machines:**
```
prog-exam/
├── exam.exe            ← Built executable (Windows)
├── config.json         ← (Optional) Configuration file
└── banks/
    ├── bank_group1.enc
    └── bank_group2.enc
```

**Run executable:**
```powershell
.\exam.exe --bank bank_group1.enc
```
No Python installation or virtual environment needed on student machines!

**With custom configuration:**
Place `config.json` in the same directory as `exam.exe`. The system will automatically load it on startup.

**Note:** Executable is ~15-25 MB. If size is a concern, use virtual environment method below.

---

## Day of Exam (Installation & Setup)

**Choose ONE method:**

### Method A: Using Executable (Simpler)

**If you built `exam.exe`:**

1. **Copy to each machine:**
   ```powershell
   # Copy executable and banks
   Copy-Item -Recurse E:\prog-exam -Destination C:\
   ```

2. **Verify files:**
   ```powershell
   cd C:\prog-exam
   Test-Path exam.exe
   Test-Path banks\bank_group1.enc
   ```

3. **Test run (on ONE machine):**
   ```powershell
   .\exam.exe --help
   ```

**Done! Skip to "Exam Start" section.**

### Method B: Using Virtual Environment

**If you did NOT build executable:**

**On each student machine, before students arrive:**

1. **Copy exam system directory:**
   ```powershell
   # Copy from USB/network to each machine
   Copy-Item -Recurse E:\prog-exam -Destination C:\
   ```

2. **Navigate to exam directory:**
   ```powershell
   Set-Location C:\prog-exam
   ```

3. **Check Python is installed:**
   ```powershell
   python --version
   ```
   Should show Python 3.10 or higher.

4. **Create virtual environment:**
   ```powershell
   python -m venv .venv
   ```

5. **Activate virtual environment:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

6. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
   This installs `cryptography` and other required packages.

**Verification (run on ONE machine):**
```powershell
python main.py --help
```
Should show help text without errors.

### Verify Installation on All Machines

**Quick check on each machine:**
```powershell
cd C:\prog-exam
# If using executable:
Test-Path exam.exe
# If using virtual environment:
Test-Path .venv\Scripts\python.exe
Test-Path main.py
# Both methods:
Test-Path banks\bank_group1.enc
```
All should return `True`.

---

## Exam Start (Per Student)

### What You Do (Once Per Machine)

**Walk to each student machine:**

1. **Start the exam runner:**

   **If using executable:**
   ```powershell
   cd C:\prog-exam
   .\exam.exe --bank bank_group1.enc
   ```
   
   **If using virtual environment:**
   ```powershell
   cd C:\prog-exam
   .\.venv\Scripts\Activate.ps1
   python main.py --bank bank_group1.enc
   ```

2. **Enter decryption key:**
   - System prompts: `Enter decryption key for Group 1:`
   - Type or paste the key (hidden input)
   - Press Enter
   
   **Success:**
   ```
   ✓ Bank loaded successfully.
   ✓ Config loaded: 3 questions (1E, 1M, 1H) = 15.0 pts
   
   STUDENT AUTHENTICATION
   Enter your first name: _
   ```
   
   **Note:** The config line shows exam parameters. If using custom configuration, verify the values are correct. If no config file is found, system uses defaults.

3. **Leave machine ready for student**

**Key entry tips:**
- Copy key to clipboard on your laptop
- Paste with Ctrl+V at each machine
- Key is case-sensitive
- **Do NOT let students see the key**

### What Students Do (At Their Machine)

**Students enter their information:**
```
Enter your first name: Jane
Enter your surname: Doe
```

**System creates their workspace:**
```
✓ Authenticated as Doe, Jane
✓ Working directory: jane_doe_TP_EVAL
✓ Assigned tasks: E07, M14, H03

exam> _
```

Students can now type commands.

**Note:** Number of assigned tasks matches configured `total_questions`. Default is 3 (q1, q2, q3), but can be more if using custom configuration.

### If Student Machine Needs Restart

**If using executable:**
```powershell
.\exam.exe --bank bank_group1.enc
```

**If using virtual environment:**
```powershell
.\.venv\Scripts\Activate.ps1
python main.py --bank bank_group1.enc
```

Then:
1. Enter decryption key (you)
2. Student enters **same name and surname**
3. System prompts: `Do you want to resume your previous session? (y/n):`
4. Student types: `y`
5. Work is restored

---

## During Exam

### Student Workflow

**Students work independently:**
1. Type `q1`, `q2`, `q3`, etc. to view tasks (number depends on configuration)
2. Edit Python files (`q1.py`, `q2.py`, `q3.py`, etc.) in any text editor
3. Test code: `test q1`
4. Debug code: `debug q1`
5. Submit solution: `submit q1`
6. Check progress: `status`
7. Finish exam: `finish` (creates ZIP file)

**Note:** Default is 3 questions. If using custom configuration, students may have more questions (e.g., q1 through q5).

**Files created per student:**
```
jane_doe_TP_EVAL/
├── assignment.json      ← Task assignment
├── session.log          ← Activity log
├── algorithm.txt        ← Algorithm descriptions
├── q1.py, q2.py, q3.py  ← Student code
└── results.txt          ← Test results
```

### Monitoring Students

**Watch for:**
- Students stuck (tell them to type `help`)
- Error messages on screen
- Policy violations (browser, USB drive, etc.)

**Common questions:**

| Question | Answer |
|----------|--------|
| "How do I see my tasks?" | Type `q1`, `q2`, `q3`, etc. (or type `help` to see list) |
| "How many questions?" | Type `status` to see all questions |
| "How do I test my code?" | Type `test q1` |
| "Why are tests failing?" | Type `debug q1` to see detailed errors |
| "How do I save?" | Type `submit q1` |
| "What editor?" | Any text editor (VS Code, Notepad, etc.) |
| "Can I resubmit?" | Yes, latest counts |
| "How do I finish?" | Type `finish` |

### Checking Progress

**Ask student to run:**
```
exam> status
```

**Or check log file:**
```powershell
Get-Content jane_doe_TP_EVAL\session.log -Tail 10
```

### Debugging Test Failures

#### Using Debug Mode

Debug mode helps diagnose why tests fail, especially useful for cross-platform issues.

**When to use:**
- Code works on one machine but fails on another
- Need to see actual error messages
- Want to understand why tests are failing

**How to use:**

**Method 1: Debug Command**
```
exam> debug q1
```

Shows:
- Error messages (stderr) for runtime errors
- Student's actual output vs expected output
- Function arguments (for function-mode tests)
- Full error details

**Example output:**
```
Test # 1:  PASSED (3 ms)
Test # 2:  FAILED (Wrong Answer)
         Args: ['hello']
         Your output: 6
         Expected: 5
Test # 3:  FAILED (Runtime Error)
         Error: NameError: name 'result' is not defined
```

**Method 2: Environment Variable**

Set `EXAM_DEBUG=1` to enable detailed output for all `test` commands:

```powershell
# Windows
$env:EXAM_DEBUG = "1"
.\exam.exe --bank bank_group1.enc

# Linux/macOS
export EXAM_DEBUG=1
python main.py --bank bank_group1.enc
```

**Important Notes:**
- Debug mode reveals test outputs - use only for practice/troubleshooting
- For actual exams, use regular `test` command (keeps tests hidden)
- Debug mode helps identify:
  - Import errors from isolation flags
  - Line ending differences (Windows vs Unix)
  - Type mismatches
  - Logic errors in student code

---

## After Exam (Collection)

### Step 1: Students Finish

**Tell students to type:** `finish`

```
exam> finish
```

System creates ZIP file: `JANE_DOE_TP_EVAL.zip` in `C:\prog-exam\`

### Step 2: Verify ZIP Files

**On each machine:**
```powershell
Get-ChildItem C:\prog-exam\*.zip
```

Should see one ZIP file per student (typical size: 5-50 KB).

**If ZIP missing:**
- Check if student ran `finish`
- Look for directory `jane_doe_TP_EVAL\`
- Manually create ZIP (see Troubleshooting)

**ZIP contents (expected):**
```
JANE_DOE_TP_EVAL.zip
├── assignment.json
├── session.log
├── results.txt
├── algorithm.txt
├── q1.py
├── q2.py
├── q3.py
└── ... (additional qN.py files if using custom configuration)
```

**Note:** Number of `.py` files depends on exam configuration (default: 3).

---

## Troubleshooting

### Problem: Key Rejected

**Error:**
```
Error: Failed to load or decrypt the question bank.
```

**Fix:**
1. Verify correct key for group (Group 1 key for `--group 1`)
2. Re-enter key (check for typos)
3. Verify bank file size (~40-70 KB):
   ```powershell
   (Get-Item banks\bank_group1.enc).Length
   ```

### Problem: Directory Already Exists

**Message:**
```
Working directory 'jane_doe_TP_EVAL' already exists.
Do you want to resume your previous session? (y/n):
```

**Solutions:**
- **Same student resuming:** Student types `y`
- **Different student, same name:** Rename old directory:
  ```powershell
  Rename-Item jane_doe_TP_EVAL jane_doe_TP_EVAL_OLD
  ```

### Problem: Test Hangs (Infinite Loop)

**Symptom:** `test q1` appears frozen.

**Fix:** Wait 2-5 seconds for timeout. System will show `FAILED (Timeout Error)`.

**If frozen:** Press `Ctrl+C`, restart runner, student resumes.

### Problem: Tests Fail on One Machine But Pass on Another

**Symptom:** Same code passes tests on development machine but fails on exam machine.

**Diagnosis:**
1. Use debug mode to see actual errors:
   ```
   exam> debug q1
   ```

2. Common causes:
   - **Import errors**: Code imports packages not available with isolation flags
   - **Path issues**: Code uses absolute paths or wrong separators
   - **Encoding**: Different character encoding between systems
   - **Python version**: Different behavior between Python versions

**Solutions:**
- Check error messages in debug output
- Ensure code uses only standard library
- Use `Path` from `pathlib` for file paths
- Test with isolation flags: `python -I -B -S -E -s your_code.py`

### Problem: ZIP Not Created

**Manual creation:**
```powershell
cd jane_doe_TP_EVAL
Compress-Archive -Path * -DestinationPath ..\JANE_DOE_TP_EVAL.zip
```

### Problem: Terminal Closed

**Fix:**
1. Re-open PowerShell
2. Run:
   
   **If using executable:**
   ```powershell
   cd C:\prog-exam
   .\exam.exe --bank bank_group1.enc
   ```
   
   **If using virtual environment:**
   ```powershell
   cd C:\prog-exam
   .\.venv\Scripts\Activate.ps1
   python main.py --bank bank_group1.enc
   ```
3. Enter key
4. Student enters same name → resumes

### Problem: Machine Crash

**Recovery:**
1. Reboot
2. Check directory exists:
   ```powershell
   Test-Path jane_doe_TP_EVAL
   ```
3. If yes: restart runner, student resumes
4. If no: escalate to coordinator

---

## Student Commands Reference

**Print and distribute to students:**

```
═══════════════════════════════════════════════════
  PYTHON EXAM SYSTEM - STUDENT COMMANDS
═══════════════════════════════════════════════════

VIEWING TASKS:
  q1, q2, q3, ...    Show your assigned tasks
                     (Type 'help' to see how many questions)

TESTING CODE:
  test q1            Run all tests for question 1
  test q2            Run all tests for question 2
  test q3            Run all tests for question 3

SUBMITTING:
  submit q1          Submit your solution for q1
  submit q2          Submit your solution for q2
  submit q3          Submit your solution for q3

CHECKING PROGRESS:
  status             Show your current scores and all questions

FINISHING:
  finish             Create final ZIP and exit

HELP:
  help               Show command list with available questions

DEBUGGING (Optional):
  debug q1           Show detailed errors and output comparison
                     (Use if you need to see why tests fail)

═══════════════════════════════════════════════════
WORKFLOW:
1. Type 'help' to see how many questions you have
2. Type 'q1' to see your first task
3. Edit the file 'q1.py' in any text editor
4. Type 'test q1' to check your solution
5. If tests fail, type 'debug q1' to see details
6. Type 'submit q1' to save your work
7. Repeat for all questions (q2, q3, etc.)
8. Type 'finish' when done
═══════════════════════════════════════════════════

IMPORTANT:
- You can submit multiple times (latest counts)
- Use any text editor (VS Code, Notepad, etc.)
- Do NOT close the terminal window
- Use 'debug' command to see detailed test errors
- Type 'status' to see all your questions and scores
- Raise your hand if you need help
═══════════════════════════════════════════════════
```

---

## Quick Reference for Teachers

### Create Exam Configuration (Optional)
```powershell
cd prog-exam
python tools\config_helper.py
# Choose option 1, follow prompts
```
Output: `config.json` (place next to executable)

**Or validate existing config:**
```powershell
python tools\config_helper.py
# Choose option 2
```

### Build Executable (Before Exam - Optional)
```powershell
# Windows
cd prog-exam
.\scripts\build_windows.ps1

# Linux/macOS
./scripts/build_unix.sh
```
Output: `exam.exe` (Windows) or `exam` (Unix)

### Installation (Day of Exam)

**Method A: Executable (simpler)**
```powershell
# Just copy files
Copy-Item -Recurse E:\prog-exam -Destination C:\
# Test: .\exam.exe --help
```

**Method B: Virtual Environment**
```powershell
cd C:\prog-exam
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Start Exam (Per Machine)

**Executable:**
```powershell
cd C:\prog-exam
.\exam.exe --bank bank_group1.enc
# Enter decryption key
```

**Virtual Environment:**
```powershell
cd C:\prog-exam
.\.venv\Scripts\Activate.ps1
python main.py --bank bank_group1.enc
# Enter decryption key
```

### Restart After Crash
**Executable:** `.\exam.exe --bank bank_group1.enc`  
**Virtual Env:** `.\.venv\Scripts\Activate.ps1` then `python main.py --bank bank_group1.enc`  
Then: Enter key → Student enters same name → resumes

---

**For full technical documentation, see:**
- `tools/README.md` — Bank management & config helper tool
- `banks/README.md` — Question bank format
- `runner/grader.py` — Grading implementation with debug support


