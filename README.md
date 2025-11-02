# Offline Python Exam System — Operational Playbook

**Version:** 1.0  
**Last Updated:** 2025-11-02  
**Target Audience:** Exam Invigilators and Technical Staff

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Pre-Exam Preparation](#pre-exam-preparation)
3. [Exam Day Startup](#exam-day-startup)
4. [Student Authentication](#student-authentication)
5. [During Exam Monitoring](#during-exam-monitoring)
6. [Post-Exam Collection](#post-exam-collection)
7. [Troubleshooting](#troubleshooting)
8. [Command Reference](#command-reference)
9. [Emergency Procedures](#emergency-procedures)

---

## Quick Start

**For experienced invigilators:**

```powershell
# 1. Navigate to exam directory
Set-Location "C:\exam_system"

# 2. Activate environment
.\.venv\Scripts\Activate.ps1

# 3. Start runner (Group 1)
python main.py --group 1

# 4. Enter decryption key when prompted (provided securely)
# 5. Students authenticate with name, surname
# 6. Collect ZIP files from root after students finish
```

**First time?** Read the full playbook below.

---

## Pre-Exam Preparation

### Timeline: 24-48 Hours Before Exam

#### A. Verify Exam Materials

**Required files on each machine:**

```
exam_system/
├── banks/
│   ├── bank_group1.enc
│   └── bank_group2.enc
├── runner/
│   ├── exam.py
│   ├── grader.py
│   ├── sandbox.py
│   └── models.py
├── requirements.txt
└── .venv/              (virtual environment)
```

**Verification steps:**

1. **Check bank files exist:**
   ```powershell
   Test-Path banks\bank_group1.enc
   Test-Path banks\bank_group2.enc
   ```
   Both should return `True`.

2. **Verify virtual environment:**
   ```powershell
   Test-Path .venv\Scripts\python.exe
   ```

3. **Test runner startup:**
   ```powershell
   .\.venv\Scripts\python.exe runner\exam.py --help
   ```
   Should display help text without errors.

#### B. Obtain Decryption Key

**Key Format:**
- Base64 string (44 characters) OR password
- Example: `EE2GANWkqTJZZ85xQCNdkD8LtqvYk2CY9vHUz0akSfs=`

**Key Management:**
- Provided by exam coordinator 24 hours before exam
- Store in password manager (never on exam machines)
- Use separate keys for Group 1 and Group 2
- Keys are entered at runtime (not saved to disk)

**Key Storage (for invigilator):**
- Write key on paper, store in sealed envelope
- Keep envelope secure until exam start
- Destroy paper after exam completion

#### C. Pre-Flight Checks (Day Before Exam)

Run these tests on **one representative machine:**

1. **Decrypt bank (dry run):**
   ```powershell
   cd tools
   ..\venv\Scripts\python.exe verify_bank.py --bank ..\banks\bank_group1.enc --key-file GROUP1.key
   ```
   
   Expected output:
   ```
   [OK] Bank decrypted successfully
   [OK] Bank validation PASSED
   ```

2. **Full mock run:**
   - Start runner with correct group
   - Authenticate as test student
   - Run `q1`, `test q1`, `submit q1`
   - Run `finish`
   - Verify ZIP file created in root directory

3. **Verify system isolation:**
   - Confirm network disabled (try `ping google.com` → should fail)
   - Confirm USB storage blocked (if policy requires)

#### D. Prepare Room Setup

**Per Machine:**
- [ ] Exam directory deployed to `C:\exam_system`
- [ ] Desktop shortcut created (optional, for convenience)
- [ ] Network adapter disabled
- [ ] Clock synchronized (all machines same time)
- [ ] Power settings: "Never sleep" during exam hours

**Invigilator Station:**
- [ ] Master copy of decryption keys (Group 1 & 2)
- [ ] Seating chart with student names and assigned groups
- [ ] USB drive for collecting ZIP files (post-exam)
- [ ] Printed troubleshooting checklist (this document)

**Backup Materials:**
- [ ] Spare machine with exam system installed
- [ ] Printed copy of student command reference
- [ ] Emergency contact (technical support)

---

## Exam Day Startup

### Timeline: 15 Minutes Before Exam Start

#### Step 1: Arrive Early and Test One Machine

**On invigilator workstation or test machine:**

```powershell
# Navigate to exam directory
Set-Location C:\exam_system

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Start runner (use correct group)
python main.py --group 1
```

**Expected prompt:**
```
============================================================
OFFLINE PYTHON EXAM SYSTEM
============================================================
Enter decryption key for Group 1: 
```

**Enter the key** (text will be hidden). If successful:
```
Loading and decrypting question bank...
✓ Bank loaded successfully.

============================================================
STUDENT AUTHENTICATION
============================================================
```

**Test complete?** Press `Ctrl+C` to exit, then proceed to start all machines.

#### Step 2: Start Runner on All Student Machines

**Method A: Start from Terminal (Recommended)**

On each student machine:

```powershell
cd C:\exam_system
.\.venv\Scripts\Activate.ps1
python main.py --group 1
```

**Method B: Use Desktop Shortcut (if created)**

If you created shortcuts during setup, students can double-click the shortcut.

#### Step 3: Enter Decryption Key

**IMPORTANT:** The key must be entered on **every machine** by the invigilator.

1. Walk to each machine
2. When prompted: `Enter decryption key for Group 1:`
3. Type or paste the key (hidden input)
4. Press Enter

**Key entry tips:**
- Copy key to clipboard on invigilator laptop
- Paste into each machine (Ctrl+V or right-click)
- Do NOT let students see the key
- If paste fails, type carefully (key is case-sensitive)

**Success indicator:**
```
✓ Bank loaded successfully.
```

**Failure indicator:**
```
Error: Failed to load or decrypt the question bank.
Details: [Fernet decryption error]
```

If decryption fails:
1. Verify correct key for the group
2. Re-enter key (may have typo)
3. If persistent, check troubleshooting section

#### Step 4: Verify All Machines Ready

**Walk through room and confirm each machine shows:**
```
============================================================
STUDENT AUTHENTICATION
============================================================
Enter your first name: _
```

**All machines ready?** Announce exam start.

---

## Student Authentication

### What Students Do

**Students will see:**
```
Enter your first name: 
Enter your surname: 
```

**Students enter:**
- First name: `Jane`
- Surname: `Doe`

**System response:**
```
✓ Authenticated as Doe, Jane
✓ Working directory: jane_doe_TP_EVAL
✓ Assigned tasks: E07, M14, H03

============================================================
Type 'help' to see available commands.
============================================================

exam> _
```

### What This Creates

**Directory structure:**
```
exam_system/
└── jane_doe_TP_EVAL/
    ├── assignment.json      (task assignment record)
    ├── session.log          (audit trail)
    ├── algorithm.txt        (created automatically)
    └── (q1.py, q2.py, q3.py created as student works)
```

### Resuming Interrupted Sessions

**If student machine crashes/restarts:**

1. Re-start runner: `python main.py --group 1`
2. Re-enter decryption key (invigilator)
3. Student enters **same name and surname**
4. System prompts: `Do you want to resume your previous session? (y/n):`
5. Student enters: `y`
6. Session resumes with all previous work intact

**Recovery note:** All student work is saved in `jane_doe_TP_EVAL/` directory. As long as this directory exists, work is not lost.

---

## During Exam Monitoring

### Invigilator Responsibilities

#### A. Visual Monitoring

**Watch for:**
- Students stuck at command prompt (may need help with `help` command)
- Error messages displayed (note for troubleshooting)
- Students attempting to open file explorer or browser (policy violation)

**Allowed student activities:**
- Typing commands in exam runner
- Opening `qN.py` files in text editor (VS Code, Notepad++, etc.)
- Editing `algorithm.txt`
- Reading Python cheat sheet (if provided)

**Prohibited activities:**
- Opening web browsers
- Accessing other directories outside `jane_doe_TP_EVAL/`
- Using USB drives
- Communicating with other students

#### B. Common Questions Students Ask

| Question | Answer |
|----------|--------|
| "How do I see my tasks?" | Type `q1`, `q2`, or `q3` |
| "How do I test my code?" | Type `test q1` (or q2, q3) |
| "How do I save my work?" | Type `submit q1` after testing |
| "What editor can I use?" | Any text editor on the machine |
| "Can I submit multiple times?" | Yes, latest submission counts |
| "How do I finish?" | Type `finish` when done with all questions |

**Printed reference card:**
```
STUDENT COMMAND REFERENCE
==========================
q1, q2, q3       View your assigned tasks
test qN          Run tests (e.g., test q1)
submit qN        Save your submission
status           Check your scores
finish           Create final ZIP and exit
help             Show all commands
```

Provide this to students at exam start.

#### C. Checking Student Progress

**Method 1: Ask student to run `status`**

Student types: `status`

Output shows:
```
Status for Doe, Jane:
- q1 (E07): Submitted | Score: 4.00 (12/15)
- q2 (M14): Not submitted
- q3 (H03): Submitted | Score: 2.67 (8/15)

Total Score so far: 6.67 / 15.00
```

**Method 2: Check log files**

On student machine:
```powershell
Get-Content C:\exam_system\jane_doe_TP_EVAL\session.log -Tail 10
```

Shows recent activity:
```
[2025-11-02 10:15:45] - COMMAND_RUN - Command: test q1
[2025-11-02 10:15:47] - TEST_RESULT - Question: q1, Passed: 10/15
[2025-11-02 10:16:10] - SUBMISSION - Question: q1, Score: 3.33
```

#### D. Time Management

**Announcements to make:**
- "30 minutes remaining"
- "15 minutes remaining"
- "5 minutes remaining — start submitting your work"
- "Time is up — type `finish` to create your submission"

**Extension handling:**
If a student needs extra time (accommodations):
- Allow them to continue working
- Collect their ZIP file when they finish
- Note extended time on record sheet

---

## Post-Exam Collection

### Timeline: Immediately After Exam Ends

#### Step 1: Students Finalize Submissions

**Students must type:** `finish`

**System prompts:**
```
You have submissions for 2 out of 3 questions.
Are you sure you want to finish and lock your work? (y/n): 
```

**Student types:** `y`

**System creates ZIP:**
```
Finalizing...
Submission package 'JANE_DOE_TP_EVAL.zip' created successfully.
Your work is now locked. Thank you.
```

**ZIP location:** `C:\exam_system\JANE_DOE_TP_EVAL.zip` (root directory)

#### Step 2: Verify ZIP Files Created

**On each machine, check:**
```powershell
Get-ChildItem C:\exam_system\*.zip
```

**Expected output:**
```
JANE_DOE_TP_EVAL.zip
```

**File size check:**
- Typical size: 5-50 KB
- Empty ZIPs (<1 KB) indicate problem

**If ZIP missing:**
1. Check if student ran `finish` command
2. Look for working directory: `C:\exam_system\jane_doe_TP_EVAL\`
3. If directory exists, manually create ZIP (see Troubleshooting)

#### Step 3: Collect ZIP Files

**Method A: USB Drive (if policy allows)**

On each student machine:
```powershell
Copy-Item C:\exam_system\*.zip -Destination E:\
```
(Replace `E:\` with USB drive letter)

**Method B: Network Share (if available)**

```powershell
Copy-Item C:\exam_system\*.zip -Destination \\server\exam_submissions\
```

**Method C: Manual Collection**

Walk to each machine with USB drive and copy ZIP files.

#### Step 4: Verify Collection

**On collection USB/server:**

1. Count ZIP files: Should equal number of students
2. Check each ZIP opens without errors
3. Verify student names match seating chart

**ZIP contents (verify one sample):**
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

#### Step 5: Secure Storage

**Immediate actions:**
- Copy all ZIPs to grading server
- Create backup copy on separate USB drive
- Store both copies in secure location

**DO NOT:**
- Delete ZIPs from student machines until backup verified
- Leave USB drive unattended
- Email ZIPs unencrypted

---

## Troubleshooting

### Issue: Decryption Key Rejected

**Symptoms:**
```
Error: Failed to load or decrypt the question bank.
```

**Causes & Solutions:**

1. **Wrong key for group**
   - Verify using Group 1 key for `--group 1`
   - Check key file name or password

2. **Typo in key**
   - Re-enter key carefully
   - Copy-paste from source document

3. **Corrupted bank file**
   - Verify file size: `bank_group1.enc` should be ~40-70 KB
   - Re-copy bank file from master source

4. **Password vs Key File Mismatch**
   - If bank encrypted with password, key file won't work
   - Check with exam coordinator which method was used

**Verification command:**
```powershell
python tools\verify_bank.py --bank banks\bank_group1.enc --key-file GROUP1.key
```

### Issue: Student Working Directory Already Exists

**Symptoms:**
```
Working directory 'jane_doe_TP_EVAL' already exists.
Do you want to resume your previous session? (y/n):
```

**Scenarios:**

**A. Student is resuming after crash:**
- Student should type `y`
- Work will be restored

**B. Different student with same name:**
- Student should type `n`
- Invigilator manually renames old directory:
  ```powershell
  Rename-Item jane_doe_TP_EVAL jane_doe_TP_EVAL_OLD
  ```
- Student restarts authentication

**C. Student from previous exam session:**
- Old directory should have been cleaned up
- Invigilator backs up old directory:
  ```powershell
  Move-Item jane_doe_TP_EVAL C:\exam_backups\
  ```

### Issue: Test Command Hangs / Timeout

**Symptoms:**
Student runs `test q1` and system appears frozen.

**Cause:**
Student code has infinite loop.

**Solution:**
1. Wait 2-5 seconds (timeout will trigger)
2. System will display: `Test #3: FAILED (Timeout Error)`
3. Advise student to fix infinite loop in code

**If system completely frozen:**
1. Press `Ctrl+C` to interrupt
2. Restart runner (work is auto-saved)
3. Student resumes session

### Issue: Submission ZIP Not Created

**Symptoms:**
Student ran `finish` but ZIP file not in root directory.

**Manual ZIP creation:**

1. Navigate to student directory:
   ```powershell
   Set-Location C:\exam_system\jane_doe_TP_EVAL
   ```

2. Create ZIP manually:
   ```powershell
   Compress-Archive -Path * -DestinationPath ..\JANE_DOE_TP_EVAL.zip
   ```

3. Verify ZIP created:
   ```powershell
   Test-Path ..\JANE_DOE_TP_EVAL.zip
   ```

### Issue: Python Editor Not Working

**Symptoms:**
Student cannot open/edit `q1.py` file.

**Solutions:**

**A. Use Notepad (always available):**
```powershell
notepad q1.py
```

**B. Use VS Code (if installed):**
```powershell
code q1.py
```

**C. Use Notepad++ (if installed):**
```powershell
notepad++ q1.py
```

**D. Last resort: Edit in terminal:**
- Not recommended, but possible
- Student can view file: `Get-Content q1.py`

### Issue: Student Accidentally Closed Terminal

**Solution:**

1. Re-open PowerShell
2. Navigate: `cd C:\exam_system`
3. Activate: `.\.venv\Scripts\Activate.ps1`
4. Start: `python main.py --group 1`
5. Invigilator re-enters key
6. Student authenticates with same name
7. Session resumes (all work saved)

### Issue: Machine Crash / Power Failure

**Recovery steps:**

1. Reboot machine
2. Verify working directory still exists:
   ```powershell
   Test-Path C:\exam_system\jane_doe_TP_EVAL
   ```

3. If directory exists:
   - Restart runner (see above)
   - Student resumes session
   - All submitted work is intact

4. If directory missing:
   - Check for recent backups
   - Student may need to restart (escalate to coordinator)

### Issue: Student Reports Wrong Task Assignment

**Symptoms:**
"I got a hard question but my friend got an easy one!"

**Explanation:**
- Task assignment is **deterministic** based on name
- Each student gets exactly 1 Easy, 1 Medium, 1 Hard
- Assignment is fair but **appears random**
- Assignment is recorded in `assignment.json`

**Verification:**
```powershell
Get-Content jane_doe_TP_EVAL\assignment.json
```

Shows:
```json
{
  "name": "Jane",
  "surname": "Doe",
  "group": "group1",
  "assigned_tasks": {
    "q1": "E07",
    "q2": "M14",
    "q3": "H03"
  }
}
```

**Response to student:**
"Assignment is correct. Each student gets one task per difficulty level."

---

## Command Reference

### Invigilator Commands

**Environment activation:**
```powershell
# Windows
.\.venv\Scripts\Activate.ps1

# Verify activation
Get-Command python
```

**Start exam runner:**
```powershell
python main.py --group 1  # For Group 1
python main.py --group 2  # For Group 2
```

**Verify bank integrity:**
```powershell
python tools\verify_bank.py --bank banks\bank_group1.enc --key-file GROUP1.key
```

**Check student directory:**
```powershell
Get-ChildItem C:\exam_system\jane_doe_TP_EVAL
```

**View student log:**
```powershell
Get-Content C:\exam_system\jane_doe_TP_EVAL\session.log
```

**Collect all ZIPs:**
```powershell
Get-ChildItem C:\exam_system\*.zip | Copy-Item -Destination E:\
```

### Student Commands

Students type these in the `exam>` prompt:

| Command | Description | Example |
|---------|-------------|---------|
| `help` | Show command list | `help` |
| `q1`, `q2`, `q3` | View task prompt | `q1` |
| `test qN` | Run tests | `test q1` |
| `submit qN` | Submit solution | `submit q2` |
| `status` | Check progress | `status` |
| `finish` | Create final ZIP | `finish` |

**Student workflow example:**
```
exam> q1
[Shows task prompt and creates q1.py]

[Student edits q1.py in editor]

exam> test q1
[Runs 15 tests, shows results]

exam> submit q1
[Saves submission]

exam> status
[Shows score]

exam> finish
[Creates ZIP and exits]
```

---

## Emergency Procedures

### Complete Network Failure During Exam

**Impact:** None. System is fully offline.

**Action:** Continue exam as normal.

### Power Outage

**If UPS available:**
- UPS provides 15-30 minutes backup
- Announce: "Save your work immediately with `submit qN`"
- Students submit all questions
- Collect ZIPs before shutdown

**If no UPS:**
- Machines will shut down immediately
- After power restored:
  - Restart all machines
  - Students resume sessions (work is auto-saved)
  - Extend exam time by outage duration

### Exam Coordinator Unreachable

**If decryption key is lost:**
- Check password manager / sealed envelope
- Check email from coordinator (sent 24h before)
- Try backup key if available

**If still no key:**
- Exam cannot proceed (bank is encrypted)
- Postpone exam and contact technical support

### Student Medical Emergency

**Exam continuity:**
1. Pause student's work: Student should **not** run `finish`
2. Close terminal window (work auto-saved)
3. Attend to emergency
4. When student returns:
   - Restart runner
   - Student resumes session
   - Extend time as appropriate

**Collecting partial work:**
If student cannot return:
```powershell
cd jane_doe_TP_EVAL
Compress-Archive -Path * -DestinationPath ..\JANE_DOE_TP_EVAL_PARTIAL.zip
```

### Fire Alarm / Evacuation

**Before evacuating:**
- Do NOT run `finish` on student machines
- Note time on whiteboard
- Leave machines running (if safe)

**After returning:**
- Students resume at terminals
- Extend exam time by evacuation duration
- Verify no work was lost (check `session.log`)

### Suspected Cheating

**If student is:**
- Accessing prohibited websites → Warning, note in log
- Sharing code with neighbor → Separate students, note in log
- Using external USB → Confiscate, note in log

**Do NOT:**
- Stop student's exam abruptly
- Delete student's work
- Accuse without evidence

**Log the incident:**
```powershell
Add-Content jane_doe_TP_EVAL\INCIDENT.txt "Suspected code sharing at 10:45 AM"
```

**Escalate to exam coordinator** for formal investigation.

---

## Appendix A: File Locations

**System files:**
```
C:\exam_system\
├── banks\
│   ├── bank_group1.enc          ← Encrypted question bank
│   └── bank_group2.enc
├── runner\
│   ├── exam.py                  ← Main application
│   ├── grader.py                ← Test executor
│   └── sandbox.py               ← Secure code runner
├── tools\
│   ├── verify_bank.py           ← Bank validator
│   └── keygen.py                ← Key generator
└── .venv\                       ← Python virtual environment
```

**Student files (per student):**
```
C:\exam_system\jane_doe_TP_EVAL\
├── assignment.json              ← Task assignment record
├── session.log                  ← Full audit trail
├── results.txt                  ← Human-readable results
├── algorithm.txt                ← Student's algorithm descriptions
├── q1.py                        ← Question 1 solution
├── q2.py                        ← Question 2 solution
└── q3.py                        ← Question 3 solution
```

**Output files:**
```
C:\exam_system\
├── JANE_DOE_TP_EVAL.zip         ← Final submission (collect this)
├── JOHN_SMITH_TP_EVAL.zip
└── ...
```

---

## Appendix B: Pre-Exam Checklist

**Print this section and check off during preparation:**

### 48 Hours Before Exam

- [ ] Exam system deployed to all machines
- [ ] Virtual environments created and tested
- [ ] Bank files copied to all machines
- [ ] Decryption keys obtained from coordinator
- [ ] Network disabled on all student machines
- [ ] Power settings configured (no sleep)
- [ ] One full dry run completed successfully

### 24 Hours Before Exam

- [ ] Seating chart finalized
- [ ] Student names and groups confirmed
- [ ] Backup machine prepared
- [ ] USB drive for collection prepared
- [ ] Printed troubleshooting guide (this document)
- [ ] Emergency contact information ready

### 1 Hour Before Exam

- [ ] Room opened and secured
- [ ] All machines powered on
- [ ] One test machine verified working
- [ ] Decryption key accessible
- [ ] Student command reference cards printed
- [ ] Timer/clock visible to all students

### At Exam Start

- [ ] Runner started on all machines
- [ ] Decryption key entered on all machines
- [ ] All machines showing "STUDENT AUTHENTICATION" prompt
- [ ] Students briefed on commands (`help`, `q1`, `test`, `submit`, `finish`)
- [ ] Start time announced and recorded

### At Exam End

- [ ] All students ran `finish` command
- [ ] ZIP files created on all machines
- [ ] ZIP files copied to collection drive
- [ ] Backup copy created
- [ ] Student machines shut down
- [ ] Collection drive secured

---

## Appendix C: Key Rotation (Post-Exam)

**When:** After each exam session, before reusing banks.

**Why:** Security best practice to prevent key leakage.

**How:**

1. Generate new key:
   ```powershell
   python tools\keygen.py --out GROUP1_2026.key
   ```

2. Rotate key:
   ```powershell
   python tools\rotate_key.py `
     --in banks\bank_group1.enc `
     --out banks\bank_group1.enc `
     --old-key-file GROUP1.key `
     --new-key-file GROUP1_2026.key
   ```

3. Verify with new key:
   ```powershell
   python tools\verify_bank.py `
     --bank banks\bank_group1.enc `
     --key-file GROUP1_2026.key
   ```

4. Archive old key securely (for audit trail)

5. Update key distribution to coordinators

---

## Appendix D: Contact Information

**Fill in before exam:**

| Role | Name | Phone | Email |
|------|------|-------|-------|
| Exam Coordinator | ___________ | ___________ | ___________ |
| Technical Support | ___________ | ___________ | ___________ |
| Building Security | ___________ | ___________ | ___________ |
| Medical Emergency | ___________ | ___________ | ___________ |

---

## Appendix E: Student Briefing Script

**Read this to students at exam start:**

> "Welcome to the Python programming exam. You will have [X] hours to complete three programming tasks: one easy, one medium, and one hard.
>
> Your computer is running a special exam system. You'll use commands to view tasks, test your code, and submit your solutions.
>
> To begin, enter your first name and surname when prompted. The system will create a personal workspace for you.
>
> Important commands:
> - Type 'q1', 'q2', or 'q3' to see your tasks
> - Edit your code in the Python files created for you
> - Type 'test q1' to run tests on your solution
> - Type 'submit q1' when you're happy with your solution
> - Type 'finish' when you're done to create your submission file
>
> You can submit each question multiple times. Your latest submission counts.
>
> If you have technical problems, raise your hand. Do not close the terminal window.
>
> You may begin."

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-02 | Initial operational playbook |

---

**END OF OPERATIONAL PLAYBOOK**

For technical implementation details, see:
- `tools/COMMAND_REFERENCE.md` — Tool usage guide
- `tools/README.md` — Bank management tools
- `banks/bank_schema.md` — Question bank format
- `plan-gem.md` — Complete system design


