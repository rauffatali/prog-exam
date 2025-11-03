#!/usr/bin/env python3
"""
Offline Python Exam Runner CLI

Student-facing application for completing Python programming exams.
Handles task assignment, code submission, testing, and result packaging.
"""

import os
import sys
import argparse
import getpass
import json
import hashlib
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from zipfile import ZipFile, ZIP_DEFLATED
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .models import Bank, Task, ExamConfig
from .grader import Grader
from .config_loader import load_config


class ExamSession:
    """Manages the state of a student's exam session."""
    
    def __init__(
        self,
        name: str,
        surname: str,
        group: str,
        bank: Bank,
        work_dir: Path,
        config: ExamConfig
    ):
        self.name = name
        self.surname = surname
        self.student_name = f"{surname}, {name}"  # For display
        self.group = group
        self.bank = bank
        self.work_dir = work_dir
        self.config = config
        self.grader = Grader(config)
        
        # Assigned tasks (populated by deterministic assignment)
        self.assigned_tasks: Dict[str, Task] = {}  # qN -> Task
        
        # Submission state - dynamic based on config
        self.submissions: Dict[str, Optional[Dict]] = {
            f"q{i+1}": None for i in range(config.total_questions)
        }
        
        # Log file
        self.log_path = work_dir / "session.log"
        self.assignment_path = work_dir / "assignment.json"
        self.results_path = work_dir / "results.txt"
        
        # Track if session is finalized
        self.is_finished = False
    
    def log(self, event: str, details: str = ""):
        """Append an entry to the session log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] - {event}"
        if details:
            log_entry += f" - {details}"
        log_entry += "\n"
        
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def save_assignment(self):
        """Save the task assignment to assignment.json."""
        assignment_data = {
            "name": self.name,
            "surname": self.surname,
            "group": self.group,
            "assigned_tasks": {
                qn: task.id for qn, task in self.assigned_tasks.items()
            }
        }
        
        with open(self.assignment_path, 'w', encoding='utf-8') as f:
            json.dump(assignment_data, f, indent=2)
    
    def load_assignment(self) -> bool:
        """
        Load existing assignment if it exists.
        
        Returns:
            True if assignment was loaded, False otherwise
        """
        if not self.assignment_path.exists():
            return False
        
        try:
            with open(self.assignment_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Verify name and surname match
            if data.get("name") != self.name or data.get("surname") != self.surname:
                return False
            
            # Load assigned tasks
            all_tasks = self.bank.get_all_tasks()
            assigned_task_ids = data.get("assigned_tasks", {})
            
            for qn, task_id in assigned_task_ids.items():
                if task_id in all_tasks:
                    self.assigned_tasks[qn] = all_tasks[task_id]
            
            return len(self.assigned_tasks) == self.config.total_questions
        
        except Exception:
            return False
    
    def get_total_score(self) -> float:
        """Calculate total score from submissions."""
        total = 0.0
        for sub in self.submissions.values():
            if sub is not None:
                total += sub.get("score", 0.0)
        return round(total, 2)
    
    def get_max_score(self) -> float:
        """Get the maximum possible score."""
        return self.config.max_points
    
    def generate_results_file(self):
        """Generate the human-readable results.txt file."""
        lines = []
        lines.append(f"Student: {self.student_name} | Group: {self.group} | Date: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append(f"Assigned: {', '.join(task.id for task in self.assigned_tasks.values())}\n")
        
        # Generate for all questions based on config
        for i in range(self.config.total_questions):
            qn = f"q{i+1}"
            task = self.assigned_tasks.get(qn)
            sub = self.submissions.get(qn)
            
            if task:
                lines.append(f"[{qn}: {task.id}]", )
                
                if sub:
                    timestamp = sub.get("timestamp", "N/A")
                    score = sub.get("score", 0.0)
                    passed = sub.get("passed", 0)
                    total = sub.get("total", 15)
                    sha256 = sub.get("code_sha256", "N/A")
                    max_score = sub.get("max_score", 0.0)
                    
                    lines.append(f"  SUBMITTED @ {timestamp}")
                    lines.append(f"  - Score: {score:.2f} / {max_score:.2f} ({passed}/{total} passed)")
                    
                    # List failed test numbers
                    results = sub.get("results", [])
                    failed_nums = [r["test_num"] for r in results if r["status"] != "passed"]
                    if failed_nums:
                        lines.append(f"  - Failed cases: {', '.join(f'#{n}' for n in failed_nums)}")
                    
                    lines.append(f"  - SHA256({qn}.py): {sha256[:8]}...{sha256[-4:]}")
                else:
                    lines.append(f"  NOT SUBMITTED")
                
                lines.append("")
        
        lines.append(f"TOTAL SCORE: {self.get_total_score():.2f} / {self.get_max_score():.2f}")
        
        with open(self.results_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
    
    def create_submission_zip(self) -> Path:
        """Create the final submission ZIP file in root folder."""
        # Sanitize name and surname for filename
        safe_name = "".join(c if c.isalnum() else '_' for c in self.name.upper())
        safe_surname = "".join(c if c.isalnum() else '_' for c in self.surname.upper())
        
        zip_filename = f"{safe_name}_{safe_surname}_TP_EVAL.zip"
        # Save in root folder (parent of work_dir)
        zip_path = self.work_dir.parent / zip_filename
        
        # Files to include
        files_to_zip = [
            "assignment.json",
            "session.log",
            "results.txt",
            "algorithm.txt"
        ]
        
        # Add qN.py files dynamically based on config
        for i in range(self.config.total_questions):
            code_file = f"q{i+1}.py"
            if (self.work_dir / code_file).exists():
                files_to_zip.append(code_file)
        
        with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zipf:
            for filename in files_to_zip:
                file_path = self.work_dir / filename
                if file_path.exists():
                    zipf.write(file_path, arcname=filename)
        
        return zip_path


class ExamRunner:
    """Main CLI application controller."""
    
    def __init__(self, group: str, bank_path: Path):
        self.group = group
        self.bank_path = bank_path
        self.bank: Optional[Bank] = None
        self.session: Optional[ExamSession] = None
        self.config: Optional[ExamConfig] = None
    
    def derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        """Derive a Fernet key from a password using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP recommendation for 2024
        )
        key_material = kdf.derive(password.encode('utf-8'))
        return base64.urlsafe_b64encode(key_material)
    
    def load_bank(self, key_input: str) -> bool:
        """
        Load and decrypt the question bank.
        
        Args:
            key_input: Encryption key (as string - will be interpreted as password or key)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.bank_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Check if password-based encryption (has SALT prefix)
            is_password_based = encrypted_data.startswith(b'SALT')
            
            if is_password_based:
                # Extract salt and actual encrypted data
                salt = encrypted_data[4:20]  # 4-byte prefix + 16-byte salt
                encrypted_data = encrypted_data[20:]
                
                # Derive key from password
                key = self.derive_key_from_password(key_input, salt)
            else:
                # Key file format - use input as-is (base64 encoded key)
                try:
                    key = key_input.encode('utf-8')
                except:
                    key = key_input

            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(encrypted_data)
            bank_dict = json.loads(decrypted_data)
            
            self.bank = Bank.from_dict(bank_dict)
            return True
        
        except Exception as e:
            print(f"Error: Failed to load or decrypt the question bank.")
            print(f"Details: {e}")
            return False
    
    def authenticate_student(self) -> bool:
        """
        Prompt for student information and create working directory.
        
        Returns:
            True if successful, False otherwise
        """
        print("\n" + "="*60)
        print("STUDENT AUTHENTICATION")
        print("="*60)
        
        try:
            name = input("Enter your first name: ").strip()
            if not name:
                print("Error: First name cannot be empty.")
                return False
            
            surname = input("Enter your surname: ").strip()
            if not surname:
                print("Error: Surname cannot be empty.")
                return False
            
            # Create working directory: name_surname_TP_EVAL (lowercase)
            safe_name = "".join(c if c.isalnum() else '_' for c in name.lower())
            safe_surname = "".join(c if c.isalnum() else '_' for c in surname.lower())
            work_dir_name = f"{safe_name}_{safe_surname}_TP_EVAL"
            work_dir = Path.cwd() / work_dir_name
            
            # Check if directory exists
            if work_dir.exists():
                print(f"\nWorking directory '{work_dir_name}' already exists.")
                resume = input("Do you want to resume your previous session? (y/n): ").strip().lower()
                
                if resume != 'y':
                    print("Please remove the existing directory and try again.")
                    return False
            else:
                work_dir.mkdir(exist_ok=True)
            
            # Create session
            self.session = ExamSession(
                name=name,
                surname=surname,
                group=self.group,
                bank=self.bank,
                work_dir=work_dir,
                config=self.config
            )
            
            # Try to load existing assignment or create new one
            if not self.session.load_assignment():
                self.assign_tasks()
                self.session.save_assignment()
            
            # Log session start
            self.session.log("SESSION_START", f"Student: {surname}, {name}, Group: {self.group}")
            
            # Create algorithm.txt if it doesn't exist
            algo_file = work_dir / "algorithm.txt"
            if not algo_file.exists():
                with open(algo_file, 'w', encoding='utf-8') as f:
                    f.write("# Algorithm Descriptions\n\n")
                    f.write("Please describe your approach for each question below.\n\n")
                    for qn, task in self.session.assigned_tasks.items():
                        f.write(f"## {qn.upper()}: {task.title} ({task.id})\n\n")
                        f.write("Your approach:\n\n\n")
            
            print(f"\n✓ Authenticated as {surname}, {name}")
            print(f"✓ Working directory: {work_dir}")
            print(f"✓ Assigned tasks: {', '.join(task.id for task in self.session.assigned_tasks.values())}")
            
            return True
        
        except (KeyboardInterrupt, EOFError):
            print("\nAuthentication cancelled.")
            return False
        except Exception as e:
            print(f"Error during authentication: {e}")
            return False
    
    def assign_tasks(self):
        """Deterministically assign tasks based on config to the student."""
        # Seed based on name, surname and group
        exam_date = datetime.now().strftime("%Y-%m-%d")
        seed_string = f"{self.session.name.lower()}{self.session.surname.lower()}{self.group}{exam_date}"
        seed_hash = hashlib.sha256(seed_string.encode()).hexdigest()
        seed = int(seed_hash, 16)
        
        # Build list of tasks to assign based on config
        tasks_to_assign = []
        
        # Add easy tasks
        for i in range(self.config.easy_count):
            easy_idx = (seed + i) % len(self.bank.easy)
            tasks_to_assign.append(("easy", self.bank.easy[easy_idx]))
        
        # Add medium tasks
        for i in range(self.config.medium_count):
            medium_idx = (seed // 1000 + i) % len(self.bank.medium)
            tasks_to_assign.append(("medium", self.bank.medium[medium_idx]))
        
        # Add hard tasks
        for i in range(self.config.hard_count):
            hard_idx = (seed // 1000000 + i) % len(self.bank.hard)
            tasks_to_assign.append(("hard", self.bank.hard[hard_idx]))
        
        # Assign to question numbers
        self.session.assigned_tasks = {}
        for i, (difficulty, task) in enumerate(tasks_to_assign):
            qn = f"q{i+1}"
            self.session.assigned_tasks[qn] = task
    
    def run(self):
        """Main application entry point."""
        parser = argparse.ArgumentParser(
            description="Offline Python Exam Runner",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        parser.add_argument(
            "--group",
            required=True,
            choices=['1', '2'],
            help="The exam group (1 or 2)"
        )
        
        args = parser.parse_args()
        
        # Determine the executable/script directory
        if getattr(sys, 'frozen', False):
            # Running as compiled executable - banks/ should be next to .exe
            exe_dir = Path(sys.executable).parent
        else:
            # Running as script - banks/ should be in project root
            exe_dir = Path(__file__).parent.parent
        
        # Set group and bank path (relative to executable location)
        self.group = f"group{args.group}"
        self.bank_path = exe_dir / "banks" / f"bank_group{args.group}.enc"
        
        # Check if bank file exists
        if not self.bank_path.exists():
            print(f"Error: Bank file '{self.bank_path}' not found.")
            print(f"Expected location: {self.bank_path}")
            print(f"Please ensure the 'banks' directory is in the same folder as the executable.")
            return 1
        
        # Get decryption key/password
        print("="*60)
        print("OFFLINE PYTHON EXAM SYSTEM")
        print("="*60)
        
        try:
            key_input = getpass.getpass(f"Enter decryption password for Group {args.group}: ")
            if not key_input:
                print("Error: Password cannot be empty.")
                return 1
            
            # Strip whitespace
            key_input = key_input.strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return 1
        
        # Load bank
        print("\nLoading and decrypting question bank...")
        if not self.load_bank(key_input):
            return 1
        
        print("✓ Bank loaded successfully.")
        
        # Load exam configuration
        try:
            self.config = load_config()
            print(f"✓ Config loaded: {self.config.total_questions} questions ({self.config.easy_count}E, {self.config.medium_count}M, {self.config.hard_count}H) = {self.config.max_points} pts")
        except ValueError as e:
            print(f"Error loading configuration: {e}")
            return 1
        
        # Authenticate student
        if not self.authenticate_student():
            return 1
        
        # Change to working directory
        os.chdir(self.session.work_dir)
        
        # Main command loop
        self.command_loop()
        
        return 0
    
    def command_loop(self):
        """Main interactive command loop."""
        print("\n" + "="*60)
        print("Type 'help' to see available commands.")
        print("="*60 + "\n")
        
        while not self.session.is_finished:
            try:
                cmd_line = input("exam> ").strip()
                if not cmd_line:
                    continue
                
                parts = cmd_line.split()
                command = parts[0].lower()
                
                # Log command
                self.session.log("COMMAND_RUN", f"Command: {cmd_line}")
                
                # Route command
                if command in ['exit', 'quit', 'finish']:
                    self.cmd_finish()
                elif command == 'help':
                    self.cmd_help()
                elif command in [f'q{i+1}' for i in range(self.session.config.total_questions)]:
                    self.cmd_show_question(command)
                elif command == 'test':
                    if len(parts) < 2:
                        print("Usage: test qN (e.g., 'test q1')")
                    else:
                        self.cmd_test(parts[1].lower())
                elif command == 'debug':
                    if len(parts) < 2:
                        print("Usage: debug qN (e.g., 'debug q1')")
                    else:
                        self.cmd_debug(parts[1].lower())
                elif command == 'submit':
                    if len(parts) < 2:
                        print("Usage: submit qN (e.g., 'submit q1')")
                    else:
                        self.cmd_submit(parts[1].lower())
                elif command == 'status':
                    self.cmd_status()
                else:
                    print(f"Unknown command: '{command}'. Type 'help' for a list of commands.")
            
            except (KeyboardInterrupt, EOFError):
                print("\nUse 'finish' to exit and save your work.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                self.session.log("ERROR", str(e))
    
    def cmd_help(self):
        """Display help message."""
        # Generate question list dynamically
        question_list = ", ".join([f"q{i+1}" for i in range(self.session.config.total_questions)])
        
        help_text = f"""
Available commands:
  {question_list}       Show your assigned prompts.
  test qN          Run hidden tests for question N (e.g., 'test q1').
  debug qN         Run tests with detailed error messages and output comparison.
  submit qN        Submit your code for question N.
  status           Show your current submission status and scores.
  finish           Finalize and package your submission.
  help             Show this help message.
"""
        print(help_text)
    
    def cmd_show_question(self, qn: str):
        """Display the prompt for a question."""
        task = self.session.assigned_tasks.get(qn)
        if not task:
            print(f"Error: {qn} is not a valid question.")
            return
        
        # Determine difficulty label
        difficulty = "Easy" if task in self.bank.easy else ("Medium" if task in self.bank.medium else "Hard")
        
        print(f"\nQuestion {qn[-1]} ({difficulty}): {task.title}")
        print(f"ID: {task.id}\n")
        print("Prompt:")
        print(task.prompt)
        print(f"\nI/O Mode: {task.io.mode}")
        
        # Show visible sample if available
        if task.visible_sample:
            print("\nSample:")
            if task.visible_sample.input:
                print(f"Input:\n{task.visible_sample.input}")
                print(f"Output:\n{task.visible_sample.output}")
            elif task.visible_sample.args is not None:
                print(f"Arguments: {task.visible_sample.args}")
                print(f"Expected Return: {task.visible_sample.ret}")
        
        # Create code file if it doesn't exist
        code_file = Path(f"{qn}.py")
        if not code_file.exists():
            self._create_code_file(qn, task)
            print(f"\nA file '{qn}.py' has been created for you.")
        else:
            print(f"\nEdit your solution in '{qn}.py'.")
        
        print()
    
    def _create_code_file(self, qn: str, task: Task):
        """Create a starter code file for a question with prompt and sample."""
        code_lines = []
        
        # Add header with question info
        code_lines.append(f"# {task.title} ({task.id})")
        code_lines.append("#" + "="*70)
        code_lines.append("")
        
        # Add prompt as comments
        code_lines.append("# PROMPT:")
        for line in task.prompt.split('\n'):
            code_lines.append(f"# {line}")
        code_lines.append("")
        
        # Add sample if available
        if task.visible_sample:
            code_lines.append("# SAMPLE:")
            if task.visible_sample.input:
                code_lines.append(f"# Input: {repr(task.visible_sample.input.rstrip())}")
                code_lines.append(f"# Output: {repr(task.visible_sample.output.rstrip())}")
            elif task.visible_sample.args is not None:
                code_lines.append(f"# Arguments: {task.visible_sample.args}")
                code_lines.append(f"# Expected Return: {task.visible_sample.ret}")
            code_lines.append("")
        
        code_lines.append("#" + "="*70)
        code_lines.append("")
        
        # Add mode-specific template
        if task.io.mode == "stdin_stdout":
            code_lines.append("# Read input from stdin and write output to stdout")
            code_lines.append("# Use input() to read and print() to write")
            code_lines.append("")
            code_lines.append("# Your code here")
            code_lines.append("")
        
        elif task.io.mode == "function":
            code_lines.append("# IMPORTANT: Do not change the function name!")
            code_lines.append("")
            
            # Extract function signature from prompt if available
            signature = self._extract_function_signature(task)
            if signature:
                code_lines.append(signature)
            else:
                # Fallback to basic template
                code_lines.append(f"def {task.io.entrypoint}():")
            
            code_lines.append("    # Your code here")
            code_lines.append("    pass")
            code_lines.append("")
        
        with open(f"{qn}.py", 'w', encoding='utf-8') as f:
            f.write("\n".join(code_lines))
    
    def _extract_function_signature(self, task: Task) -> Optional[str]:
        """
        Extract function signature from task prompt.
        
        Looks for lines like:
          def function_name(args) -> return_type:
        """
        lines = task.prompt.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('def ') and task.io.entrypoint in stripped:
                # Found the signature
                return stripped
        return None
    
    def cmd_test(self, qn: str):
        """Run tests for a question."""
        valid_questions = [f'q{i+1}' for i in range(self.session.config.total_questions)]
        if qn not in valid_questions:
            print(f"Error: '{qn}' is not a valid question (use {', '.join(valid_questions)}).")
            return
        
        task = self.session.assigned_tasks.get(qn)
        if not task:
            print(f"Error: {qn} is not assigned.")
            return
        
        code_file = Path(f"{qn}.py")
        if not code_file.exists():
            print(f"Error: File '{qn}.py' not found. Use '{qn}' command first to see the prompt.")
            return
        
        print(f"\nRunning {len(task.tests)} hidden tests for {qn}...\n")
        
        # Run grader
        results = self.session.grader.grade_submission(task, str(code_file))
        
        # Check if debug mode is enabled via environment variable
        show_details = os.environ.get('EXAM_DEBUG', '').lower() in ['1', 'true', 'yes']
        
        # Format and display results
        formatted_output = self.session.grader.format_test_results(results, show_details=show_details)
        print(formatted_output)
        
        # Log test results
        self.session.log("TEST_RESULT", f"Question: {qn}, Passed: {results['passed']}/{results['total']}")
        
        print()
    
    def cmd_debug(self, qn: str):
        """Run tests with detailed error output for debugging."""
        valid_questions = [f'q{i+1}' for i in range(self.session.config.total_questions)]
        if qn not in valid_questions:
            print(f"Error: '{qn}' is not a valid question (use {', '.join(valid_questions)}).")
            return
        
        task = self.session.assigned_tasks.get(qn)
        if not task:
            print(f"Error: {qn} is not assigned.")
            return
        
        code_file = Path(f"{qn}.py")
        if not code_file.exists():
            print(f"Error: File '{qn}.py' not found. Use '{qn}' command first to see the prompt.")
            return
        
        print(f"\nRunning {len(task.tests)} hidden tests for {qn} (DEBUG MODE)...\n")
        
        # Run grader
        results = self.session.grader.grade_submission(task, str(code_file))
        
        # Format and display results with details
        formatted_output = self.session.grader.format_test_results(results, show_details=True)
        print(formatted_output)
        
        # Log debug test results
        self.session.log("DEBUG_TEST", f"Question: {qn}, Passed: {results['passed']}/{results['total']}")
        
        print()
    
    def cmd_submit(self, qn: str):
        """Submit code for a question."""
        valid_questions = [f'q{i+1}' for i in range(self.session.config.total_questions)]
        if qn not in valid_questions:
            print(f"Error: '{qn}' is not a valid question (use {', '.join(valid_questions)}).")
            return
        
        task = self.session.assigned_tasks.get(qn)
        if not task:
            print(f"Error: {qn} is not assigned.")
            return
        
        code_file = Path(f"{qn}.py")
        if not code_file.exists():
            print(f"Error: File '{qn}.py' not found. Use '{qn}' command first to see the prompt.")
            return
        
        print(f"\nSubmitting {qn}...")
        
        # Run final test
        results = self.session.grader.grade_submission(task, str(code_file))
        
        # Read code for SHA256
        with open(code_file, 'rb') as f:
            code_bytes = f.read()
        code_sha256 = hashlib.sha256(code_bytes).hexdigest()
        
        # Get max score for this task based on difficulty
        max_score = results.get("max_score", 0.0)
        
        # Store submission
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.session.submissions[qn] = {
            "task_id": task.id,
            "score": results["score"],
            "passed": results["passed"],
            "total": results["total"],
            "max_score": max_score,
            "results": results["results"],
            "code_sha256": code_sha256,
            "timestamp": timestamp
        }
        
        print(f"Final test run: {results['passed']}/{results['total']} passed. Score: {results['score']:.2f} / {max_score:.2f}.")
        print("This result has been saved. You can submit again to overwrite.")
        print("Please ensure your approach is described in 'algorithm.txt'.")
        
        # Log submission
        self.session.log(
            "SUBMISSION",
            f"Question: {qn}, Score: {results['score']:.2f}, Code SHA256: {code_sha256}"
        )
        
        print()
    
    def cmd_status(self):
        """Display submission status."""
        print(f"\nStatus for {self.session.student_name}:")
        
        for i in range(self.session.config.total_questions):
            qn = f"q{i+1}"
            task = self.session.assigned_tasks.get(qn)
            sub = self.session.submissions.get(qn)
            
            if task:
                status_str = f"- {qn} ({task.id}): "
                if sub:
                    max_score = sub.get('max_score', 0.0)
                    status_str += f"Submitted | Score: {sub['score']:.2f} / {max_score:.2f} ({sub['passed']}/{sub['total']})"
                else:
                    status_str += "Not submitted"
                print(status_str)
        
        print(f"\nTotal Score so far: {self.session.get_total_score():.2f} / {self.session.get_max_score():.2f}")
        print()
    
    def cmd_finish(self):
        """Finalize the exam and create submission package."""
        submitted_count = sum(1 for sub in self.session.submissions.values() if sub is not None)
        
        print(f"\nYou have submissions for {submitted_count} out of {self.session.config.total_questions} questions.")
        
        try:
            confirm = input("Are you sure you want to finish and lock your work? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Cancelled. You can continue working.")
                return
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return
        
        print("\nFinalizing...")
        
        # Generate results file
        self.session.generate_results_file()
        
        # Create submission ZIP
        zip_path = self.session.create_submission_zip()
        
        # Log session finish
        self.session.log("SESSION_FINISH", f"Total Score: {self.session.get_total_score():.2f}")
        
        print(f"Submission package '{zip_path.name}' created successfully.")
        print("Your work is now locked. Thank you.")
        
        self.session.is_finished = True


def main():
    """Entry point for the exam runner."""
    runner = ExamRunner(group="", bank_path=Path(""))
    sys.exit(runner.run())


if __name__ == "__main__":
    main()

