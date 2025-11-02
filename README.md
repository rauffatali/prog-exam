# Offline Python Exam System — Teacher Guide

**Version:** 1.0  
**Last Updated:** 2025-11-02  
**Target Audience:** Exam Teachers and Technical Staff

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Before Exam Day (Preparation)](#before-exam-day-preparation)
3. [Day of Exam (Installation & Setup)](#day-of-exam-installation--setup)
4. [Exam Start (Per Student)](#exam-start-per-student)
5. [During Exam](#during-exam)
6. [After Exam (Collection)](#after-exam-collection)
7. [Troubleshooting](#troubleshooting)
8. [Student Commands Reference](#student-commands-reference)

---

## System Overview

**What students will do:**
- Type commands to view tasks (`q1`, `q2`, `q3`)
- Edit Python files in their preferred editor
- Test their code (`test q1`)
- Submit solutions (`submit q1`)
- Finish exam (`finish`) → creates ZIP file

**What you need:**
- Encrypted question banks (`bank_group1.enc`, `bank_group2.enc`)
- Decryption key (provided by coordinator)
- Python 3.10+ with virtual environment
- Exam runner application

---

## Before Exam Day (Preparation)

### Task 1: Obtain Exam Materials

**Get from exam coordinator:**
- [ ] Encrypted question bank file (`bank_group1.enc` or `bank_group2.enc`)
- [ ] Decryption key (Base64 string like `EE2GANWkqT...` OR password)
- [ ] Exam system files (full `exam_system/` directory)

**Key security:**
- Store key in password manager OR sealed envelope
- **Never save key on student machines**
- Use separate keys for Group 1 and Group 2

### Task 2: Test the System (One Machine)

**On your personal machine or test computer:**

1. Copy exam system directory
2. Verify files exist:
   ```powershell
   Test-Path exam_system\banks\bank_group1.enc
   Test-Path exam_system\requirements.txt
   Test-Path exam_system\main.py
   ```

3. Test decryption (optional, if you have key):
   ```powershell
   cd exam_system
   python tools\verify_bank.py --bank banks\bank_group1.enc --key-file GROUP1.key
   ```
   Expected: `[OK] Bank validation PASSED`

### Task 3: Prepare Room

- [ ] Disable network on all student machines (Windows: Network Adapter Settings)
- [ ] Set power settings to "Never sleep"
- [ ] Synchronize clocks on all machines
- [ ] Prepare USB drive for collecting ZIP files
- [ ] Print student command reference cards (see end of document)

### Task 4: Prepare Materials

- [ ] Seating chart with student names
- [ ] This guide (printed or accessible)
- [ ] USB drive for ZIP collection
- [ ] Backup machine (if available)

---

## Building Executable (Optional - Before Exam)

**Alternative to virtual environment:** Build a single-file executable that students can run directly.

### Option A: Build on Windows

**On your development machine (requires internet):**

```powershell
cd exam_system
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
cd exam_system
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
exam_system/
├── exam.exe         ← Built executable (Windows)
└── banks/
    ├── bank_group1.enc
    └── bank_group2.enc
```

**Run executable:**
```powershell
.\exam.exe --group 1
```
No Python installation or virtual environment needed on student machines!

**Note:** Executable is ~15-25 MB. If size is a concern, use virtual environment method below.

---

## Day of Exam (Installation & Setup)

**Choose ONE method:**

### Method A: Using Executable (Simpler)

**If you built `exam.exe`:**

1. **Copy to each machine:**
   ```powershell
   # Copy executable and banks
   Copy-Item -Recurse E:\exam_system -Destination C:\
   ```

2. **Verify files:**
   ```powershell
   cd C:\exam_system
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
   Copy-Item -Recurse E:\exam_system -Destination C:\
   ```

2. **Navigate to exam directory:**
   ```powershell
   Set-Location C:\exam_system
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
cd C:\exam_system
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
   cd C:\exam_system
   .\exam.exe --group 1
   ```
   
   **If using virtual environment:**
   ```powershell
   cd C:\exam_system
   .\.venv\Scripts\Activate.ps1
   python main.py --group 1
   ```
   
   (Use `--group 2` for Group 2)

2. **Enter decryption key:**
   - System prompts: `Enter decryption key for Group 1:`
   - Type or paste the key (hidden input)
   - Press Enter
   
   **Success:**
   ```
   ✓ Bank loaded successfully.
   
   STUDENT AUTHENTICATION
   Enter your first name: _
   ```

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

### If Student Machine Needs Restart

**If using executable:**
```powershell
.\exam.exe --group 1
```

**If using virtual environment:**
```powershell
.\.venv\Scripts\Activate.ps1
python main.py --group 1
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
1. Type `q1`, `q2`, or `q3` to view tasks
2. Edit Python files (`q1.py`, `q2.py`, `q3.py`) in any text editor
3. Test code: `test q1`
4. Submit solution: `submit q1`
5. Check progress: `status`
6. Finish exam: `finish` (creates ZIP file)

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
| "How do I see my tasks?" | Type `q1`, `q2`, or `q3` |
| "How do I test my code?" | Type `test q1` |
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

---

## After Exam (Collection)

### Step 1: Students Finish

**Tell students to type:** `finish`

```
exam> finish
```

System creates ZIP file: `JANE_DOE_TP_EVAL.zip` in `C:\exam_system\`

### Step 2: Verify ZIP Files

**On each machine:**
```powershell
Get-ChildItem C:\exam_system\*.zip
```

Should see one ZIP file per student (typical size: 5-50 KB).

**If ZIP missing:**
- Check if student ran `finish`
- Look for directory `jane_doe_TP_EVAL\`
- Manually create ZIP (see Troubleshooting)

### Step 3: Collect ZIP Files

**Copy to USB drive:**
```powershell
Copy-Item C:\exam_system\*.zip -Destination E:\
```
(Replace `E:\` with your USB drive letter)

**Or collect manually:**
Walk to each machine and copy ZIPs to USB.

### Step 4: Verify Collection

**Check:**
- [ ] Number of ZIPs = number of students
- [ ] Each ZIP opens without error
- [ ] Student names match seating chart

**Create backup:**
Copy all ZIPs to second USB drive or server.

**ZIP contents (expected):**
```
JANE_DOE_TP_EVAL.zip
├── assignment.json
├── session.log
├── results.txt
├── algorithm.txt
├── q1.py
├── q2.py
└── q3.py
```

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
   cd C:\exam_system
   .\exam.exe --group 1
   ```
   
   **If using virtual environment:**
   ```powershell
   cd C:\exam_system
   .\.venv\Scripts\Activate.ps1
   python main.py --group 1
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
  q1, q2, q3         Show your assigned tasks

TESTING CODE:
  test q1            Run all tests for question 1
  test q2            Run all tests for question 2
  test q3            Run all tests for question 3

SUBMITTING:
  submit q1          Submit your solution for q1
  submit q2          Submit your solution for q2
  submit q3          Submit your solution for q3

CHECKING PROGRESS:
  status             Show your current scores

FINISHING:
  finish             Create final ZIP and exit

HELP:
  help               Show command list

═══════════════════════════════════════════════════
WORKFLOW:
1. Type 'q1' to see your first task
2. Edit the file 'q1.py' in any text editor
3. Type 'test q1' to check your solution
4. Type 'submit q1' to save your work
5. Repeat for q2 and q3
6. Type 'finish' when done
═══════════════════════════════════════════════════

IMPORTANT:
- You can submit multiple times (latest counts)
- Use any text editor (VS Code, Notepad, etc.)
- Do NOT close the terminal window
- Raise your hand if you need help
═══════════════════════════════════════════════════
```

---

## Quick Reference for Teachers

### Build Executable (Before Exam - Optional)
```powershell
# Windows
cd exam_system
.\scripts\build_windows.ps1

# Linux/macOS
./scripts/build_unix.sh
```
Output: `exam.exe` (Windows) or `exam` (Unix)

### Installation (Day of Exam)

**Method A: Executable (simpler)**
```powershell
# Just copy files
Copy-Item -Recurse E:\exam_system -Destination C:\
# Test: .\exam.exe --help
```

**Method B: Virtual Environment**
```powershell
cd C:\exam_system
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Start Exam (Per Machine)

**Executable:**
```powershell
cd C:\exam_system
.\exam.exe --group 1
# Enter decryption key
```

**Virtual Environment:**
```powershell
cd C:\exam_system
.\.venv\Scripts\Activate.ps1
python main.py --group 1
# Enter decryption key
```

### Collect Results
```powershell
Get-ChildItem C:\exam_system\*.zip | Copy-Item -Destination E:\
```

### Restart After Crash
**Executable:** `.\exam.exe --group 1`  
**Virtual Env:** `.\.venv\Scripts\Activate.ps1` then `python main.py --group 1`  
Then: Enter key → Student enters same name → resumes

---

**For full technical documentation, see:**
- `tools/README.md` — Bank management
- `banks/bank_schema.md` — Question bank format
- `plan-gem.md` — System design


