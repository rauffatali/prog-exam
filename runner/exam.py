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
import time
import math
import random
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional
from zipfile import ZipFile, ZIP_DEFLATED
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .models import Bank, Task, ExamConfig
from .grader import Grader
from .config_loader import load_config
from .connectivity import check_internet_connectivity
from .ai_detector import AIDetector, check_ai_tools_at_startup
from .translations import TRANSLATIONS


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
        
        # Track failed attempts
        self.failed_attempts: Dict[str, int] = {}

        # AI detection
        self.ai_detector = None
        self.ai_monitor_active = False

        # Exam timing
        self.exam_start_time: Optional[datetime] = None
        self.exam_end_time: Optional[datetime] = None
        self.timer_state_path = work_dir / "timer_state.json"

        self.language: str = "en"
        self.messages = TRANSLATIONS["en"]
    
    def log(self, event: str, details: str = ""):
        """Append an entry to the session log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] - {event}"
        if details:
            log_entry += f" - {details}"
        log_entry += "\n"
        
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def start_exam_timer(self):
        """Start the exam timer when the exam begins, or resume from saved state."""
        # Try to load existing timer state first
        if self.load_timer_state():
            # Successfully loaded existing timer state - resuming
            if self.exam_end_time is None:
                duration_log = "infinite"
            else:
                remaining_minutes = self.get_remaining_time().total_seconds() / 60
                duration_log = f"{remaining_minutes:.1f} minutes remaining"
            self.log("EXAM_RESUME", f"Exam resumed at {datetime.now().strftime('%H:%M:%S')}, {duration_log}")
            return

        # No existing timer state - starting fresh
        self.exam_start_time = datetime.now()
        if self.config.exam_time_minutes == -1:
            self.exam_end_time = None  # No time limit
            duration_log = "infinite"
        else:
            self.exam_end_time = self.exam_start_time + timedelta(minutes=self.config.exam_time_minutes)
            duration_log = f"{self.config.exam_time_minutes} minutes"

        # Save the timer state
        self.save_timer_state()

        self.log("EXAM_START", f"Exam started at {self.exam_start_time.strftime('%H:%M:%S')}, duration: {duration_log}")
    
    def get_remaining_time(self) -> timedelta:
        """Get the remaining exam time as a timedelta."""
        if self.exam_end_time is None:
            return timedelta.max # Infinite time
        
        remaining = self.exam_end_time - datetime.now()
        return max(remaining, timedelta(0))
        
    def is_time_expired(self) -> bool:
        """Check if exam time has expired."""
        if self.exam_end_time is None:
            return False  # No time limit
        return self.get_remaining_time() <= timedelta(0)
    
    def format_remaining_time(self) -> str:
        """Format remaining time as HH:MM:SS."""
        if self.exam_end_time is None:
            return "infinite"

        remaining = self.get_remaining_time()
        total_seconds = int(remaining.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def save_timer_state(self):
        """Save the current timer state to timer_state.json."""
        if self.exam_start_time is None:
            return

        timer_data = {
            "exam_start_time": self.exam_start_time.isoformat(),
            "exam_end_time": self.exam_end_time.isoformat() if self.exam_end_time else None,
            "exam_time_minutes": self.config.exam_time_minutes
        }

        with open(self.timer_state_path, 'w', encoding='utf-8') as f:
            json.dump(timer_data, f, indent=2)

    def load_timer_state(self) -> bool:
        """
        Load existing timer state if it exists.

        Returns:
            True if timer state was loaded and is valid, False otherwise
        """
        if not self.timer_state_path.exists():
            return False

        try:
            with open(self.timer_state_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Verify that the time configuration matches
            if data.get("exam_time_minutes") != self.config.exam_time_minutes:
                return False

            # Load the times
            self.exam_start_time = datetime.fromisoformat(data["exam_start_time"])
            exam_end_time_str = data.get("exam_end_time")
            if exam_end_time_str:
                self.exam_end_time = datetime.fromisoformat(exam_end_time_str)
            else:
                self.exam_end_time = None

            # Check if time has already expired
            if self.is_time_expired():
                return False

            return True

        except Exception:
            return False
    
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
        
        zip_filename = f"{safe_name}_{safe_surname}_{self.config.work_dir_postfix.upper()}.zip"
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
    
    def __init__(self):
        self.group: Optional[str] = None
        self.bank_path: Optional[Path] = None
        self.bank: Optional[Bank] = None
        self.session: Optional[ExamSession] = None
        self.config: Optional[ExamConfig] = None
        self.time_expired_warning_shown = False

    def _msg(self, key: str, **kwargs) -> str:
        template = self.messages.get(key, key)
        return template.format(**kwargs)
    
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

    def _prompt_language(self) -> str:
        prompt = TRANSLATIONS["en"]["prompt_language"]
        while True:
            choice = input(prompt).strip().lower()
            if choice in ("en", "english", "e", "a", "anglais"):
                return "en"
            if choice in ("fr", "french", "f", "français"):
                return "fr"
            print(TRANSLATIONS["en"]["invalid_language"])
        
    def load_bank(self, key_input: Optional[str]) -> bool:
        """
        Load and decrypt the question bank.
        Also supports loading plain JSON files if the extension is .json.
        
        Args:
            key_input: Encryption key (as string - will be interpreted as password or key).
                       Not used for .json files.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if JSON file and load directly
            if self.bank_path.suffix.lower() == '.json':
                with open(self.bank_path, 'r', encoding='utf-8') as f:
                    bank_dict = json.load(f)
                bank_dict = self._select_language_payload(bank_dict)
                self.bank = Bank.from_dict(bank_dict)
                return True

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
            
            if "config" in bank_dict and "bank" in bank_dict:
                bundle = bank_dict
                normalized_bank = self._select_language_payload(bundle["bank"])
                self.bank = Bank.from_dict(normalized_bank)
                self.config = ExamConfig.from_dict(bundle["config"])
                is_valid, err = self.config.validate()
                if not is_valid:
                    raise ValueError(f"Invalid bundled config: {err}")
            else:
                normalized_bank = self._select_language_payload(bank_dict)
                self.bank = Bank.from_dict(normalized_bank)
            return True
        
        except Exception as e:
            print(f"Error: Failed to load or decrypt the question bank.")
            print(f"Details: {e}")
            return False

    def _resolve_bank_path(self, banks_dir: Path, bank_arg: str, language: str) -> Optional[Path]:
        """
        Resolve the final bank file to load, honoring language-specific suffixes.
        """
        direct_path = banks_dir / bank_arg
        if direct_path.exists():
            return direct_path

        if "{lang}" in bank_arg:
            placeholder = banks_dir / bank_arg.replace("{lang}", language)
            if placeholder.exists():
                return placeholder

        bank_path = Path(bank_arg)
        if bank_path.suffix:
            return None

        candidate_names = [
            f"{bank_arg}-{language}.json",
            f"{bank_arg}-{language}.enc",
            f"{bank_arg}_{language}.json",
            f"{bank_arg}_{language}.enc",
        ]
        for name in candidate_names:
            candidate = banks_dir / name
            if candidate.exists():
                return candidate
        return None
    
    def _select_language_payload(self, bank_dict: dict) -> dict:
        """
        Normalize bank files that may contain multiple language payloads.
        When no language blocks are present, return the dict unchanged.
        """
        if not isinstance(bank_dict, dict):
            return bank_dict

        # Format A: {"languages": {"en": {...}, "fr": {...}}}
        if "languages" in bank_dict:
            lang_data = bank_dict["languages"].get(self.language)
            if not lang_data:
                raise ValueError(f"Language '{self.language}' not found in bank.")
            return lang_data

        # Format B: metadata + language keys at top level (e.g., "en": {...}, "fr": {...})
        known_langs = {"en", "fr", "es", "de"}
        available = known_langs.intersection(bank_dict.keys())
        if available:
            lang_data = bank_dict.get(self.language)
            if not lang_data:
                raise ValueError(f"Language '{self.language}' not found in bank.")
            # Merge shared metadata (group, version, monitoring, etc.) with the language block
            meta_keys = {"group", "version", "network_monitoring", "ai_detection"}
            merged = {k: v for k, v in bank_dict.items() if k in meta_keys}
            merged.update(lang_data)
            return merged

        # Legacy single-language file → return as-is
        return bank_dict
    
    def authenticate_student(self) -> bool:
        """
        Prompt for student information and create working directory.
        
        Returns:
            True if successful, False otherwise
        """
        print("\n" + self._msg("header"))
        print(self._msg("auth_header"))
        print(self._msg("header"))
        
        try:
            name = input(self._msg("ask_name")).strip()
            if not name:
                print(self._msg("name_error"))
                return False
            
            surname = input(self._msg("ask_surname")).strip()
            if not surname:
                print(self._msg("surname_error"))
                return False
            
            # Create working directory: name_surname_TP_EVAL (lowercase)
            safe_name = "".join(c if c.isalnum() else '_' for c in name.lower())
            safe_surname = "".join(c if c.isalnum() else '_' for c in surname.lower())
            work_dir_name = f"{safe_name}_{safe_surname}_{self.config.work_dir_postfix.upper()}"
            work_dir = Path.cwd() / work_dir_name
            
            # Check if directory exists
            if work_dir.exists():
                resume = input(self._msg("resume_prompt")).strip().lower()
                if resume != 'y':
                    print(self._msg("resume_abort"))
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
            self.session.grader.set_message_fn(self._msg)
            
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
                    if self.language == 'fr':
                        f.write("# Descriptions des algorithmes\n\n")
                        f.write("Veuillez décrire votre approche pour chaque question ci-dessous.\n\n")
                    else:
                        f.write("# Algorithm Descriptions\n\n")
                        f.write("Please describe your approach for each question below.\n\n")
                    for qn, task in self.session.assigned_tasks.items():
                        f.write(f"## {qn.upper()}: {task.title} ({task.id})\n\n")
                        f.write("Votre approche:\n\n\n") if self.language == 'fr' else f.write("Your approach:\n\n\n")
            
            print(f"\n{self._msg('auth_success', surname=surname, name=name)}")
            print(f"✓ {self._msg('workdir', path=work_dir)}")
            print(f"✓ {self._msg('assigned', tasks=', '.join(task.id for task in self.session.assigned_tasks.values()))}")

            return True
        
        except (KeyboardInterrupt, EOFError):
            print(self._msg("resume_cancel"))
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
        random.seed(seed)
        
        # Build list of tasks to assign based on config
        tasks_to_assign = []
        
        # Add easy tasks
        shuffled_easy = self.bank.easy.copy()
        random.shuffle(shuffled_easy)
        for i in range(self.config.easy_count):
            tasks_to_assign.append(("easy", shuffled_easy[i]))
        
        # Add medium tasks
        shuffled_medium = self.bank.medium.copy()
        random.shuffle(shuffled_medium)
        for i in range(self.config.medium_count):
            tasks_to_assign.append(("medium", shuffled_medium[i]))
        
        # Add hard tasks
        shuffled_hard = self.bank.hard.copy()
        random.shuffle(shuffled_hard)
        for i in range(self.config.hard_count):
            tasks_to_assign.append(("hard", shuffled_hard[i]))
        
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
            "--bank",
            required=True,
            help="Encrypted bank filename or bundle filename (e.g., bank_group1.enc or bundle.enc)"
        )
        parser.add_argument(
            "--config",
            help="Path to exam configuration file (default: config.json in executable directory)"
        )

        parser.add_argument(
            "--language",
            choices=["prompt", "en", "fr"],
            default="prompt",
            help="Language for the interface and question bank (default: prompt the student)."
        )
        
        args = parser.parse_args()

        self.language = self._prompt_language()
        self.messages = TRANSLATIONS[self.language]
        
        # Determine the executable/script directory
        if getattr(sys, 'frozen', False):
            # Running as compiled executable - banks/ should be next to .exe
            exe_dir = Path(sys.executable).parent
        else:
            # Running as script - banks/ should be in project root
            exe_dir = Path(__file__).parent.parent
        
        # Set bank path (relative to executable location)
        banks_dir = exe_dir / "banks"
        self.bank_path = self._resolve_bank_path(banks_dir, args.bank, self.language)

        if not self.bank_path:
            print(self._msg("language_error", bank=args.bank, lang=self.language))
            print(self._msg("language_bank", banks_path=banks_dir))
            print(self._msg("language_hint", lang=self.language))
            return 1
        
        # Get decryption key/password (moved before connectivity checks to load bank settings)
        print(self._msg("header"))
        print(self._msg("title"))
        print(self._msg("header"))
        
        key_input = None
        if self.bank_path.suffix.lower() != '.json':
            try:
                key_input = getpass.getpass(self._msg("ask_enc_pass", bank=args.bank))
                if not key_input:
                    print(self._msg("enc_error"))
                    return 1
            
                # Strip whitespace
                key_input = key_input.strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n{self._msg('enc_exit')}")
                return 1
        
        # Load bank
        action_en = "Loading JSON" if self.bank_path.suffix.lower() == '.json' else "Loading and decrypting"
        action_fr = "Chargement JSON" if self.bank_path.suffix.lower() == '.json' else "Chargement et décryptage"
        print(f"\n{action_fr} banque de questions...") if self.language == 'fr' else print(f"\n{action_en} question bank...")
        if not self.load_bank(key_input):
            return 1
        
        # Extract group name from the loaded bank
        self.group = self.bank.group
        
        print(self._msg("bank_success"))
        print(self._msg("bank_group", group=self.group))
        print(f"{self._msg('language_confirm')}{'French' if self.language == 'fr' else 'English'}")
        
        # Check network monitoring settings from bank
        if self.bank.network_monitoring.enabled:
            print(self._msg("network_on", interval=self.bank.network_monitoring.check_interval_seconds))
            
            # Check for internet connectivity before starting exam
            print(f"\n{self._msg('network_check')}")
            has_connectivity = check_internet_connectivity()
            if has_connectivity:
                print("\n" + "!"*65)
                print(self._msg("network_detected"))
                print(self._msg("network_instructions_1"))
                print(self._msg("network_instructions_2"))
                print(self._msg("network_instructions_3"))
                print("!"*65)
                return 1
            else:
                print(f"✓ {self._msg('network_ok')}")
        else:
            print(f"✓ {self._msg('network_off')}")
        
        # Check AI detection settings from bank
        if self.bank.ai_detection.enabled:
            print(f"✓ {self._msg('ai_on', interval=self.bank.ai_detection.check_interval_seconds)}")

            # Check for AI tools before starting exam
            print(f"\n{self._msg('ai_check')}")
            ai_detected, ai_tools = check_ai_tools_at_startup()
            if ai_detected:
                tool_list = ", ".join(ai_tools)
                print("\n" + "!"*70)
                print(self._msg('ai_detected'))
                print(self._msg('ai_detected_tools', tools=tool_list))
                print(self._msg('ai_instructions_1'))
                print(self._msg('ai_instructions_2'))
                print(self._msg('ai_instructions_3'))
                print("!"*70)
                return 1
            else:
                print(f"✓ {self._msg('ai_ok')}.")
        else:
            print(f"✓ {self._msg('ai_off')}")
        
        # Load exam configuration
        config_loaded_from_bundle = self.config is not None
        try:
            if config_loaded_from_bundle:
                print(f"✓ {self._msg('config_bundle')}")
            else:
                config_path = Path(args.config) if args.config else None
                self.config = load_config(config_path)
                src = args.config if args.config else "config.json (default)"
                print(f"✓ {self._msg('config_default', src=src)}")
        except ValueError as e:
            print(self._msg("config_error", error=e))
            return 1

        # Authenticate student
        if not self.authenticate_student():
            return 1
        
        os.chdir(self.session.work_dir)

        self.session.start_exam_timer()
        if self.config.exam_time_minutes == -1:
            print(f"✓ {self._msg('timer_infinite')}")
        else:
            print(f"✓ {self._msg('timer_start', minutes=self.config.exam_time_minutes)}")

        # Start network monitoring if enabled
        if self.bank.network_monitoring.enabled:
            self.network_monitor_active = True
            self.network_thread = threading.Thread(
                target=self._monitor_network_background,
                daemon=True
            )
            self.network_thread.start()
        else:
            self.network_monitor_active = False
            self.network_thread = None

        # Start AI monitoring if enabled
        if self.bank.ai_detection.enabled:
            self.ai_detector = AIDetector(session_logger=self.session.log)
            self.ai_detector.process_check_interval = self.bank.ai_detection.check_interval_seconds
            self.ai_detector.start_monitoring()
            self.ai_monitor_active = True
        else:
            self.ai_detector = None
            self.ai_monitor_active = False

        # Start exam timer if enabled if time is not infinite
        if self.config.exam_time_minutes != -1:
            self.exam_timer_active = True
            self.exam_timer_thread = threading.Thread(
                target=self._monitor_exam_timer,
                daemon=True
            )
            self.exam_timer_thread.start()
        else:
            self.exam_timer_active = False
            self.exam_timer_thread = None

        try:
            self.command_loop()
        finally:
            # Stop timer monitoring
            self.exam_timer_active = False
            if self.exam_timer_thread and self.exam_timer_thread.is_alive():
                self.exam_timer_thread.join(timeout=1.0)
            # Stop network monitoring
            if self.network_monitor_active:
                self.network_monitor_active = False
                if self.network_thread and self.network_thread.is_alive():
                    self.network_thread.join(timeout=1.0)           
            # Stop AI monitoring
            if self.ai_monitor_active and self.ai_detector:
                self.ai_detector.stop_monitoring()
                self.ai_monitor_active = False
        
        return 0
    
    def _monitor_exam_timer(self):
        """Background thread to monitor exam time and auto-finish when expired."""
        while self.exam_timer_active and not self.session.is_finished:
            if self.session.is_time_expired():
                
                self.time_expired_warning_shown = True
                self.session.log("EXAM_TIMEOUT", "Exam time finished - auto-stopping")
                break
            
            time.sleep(1)  # Check every second
    
    def _auto_finish_exam(self):
        """Automatically finish the exam when time expires."""
        try:
            # Auto-submit all unsubmitted questions first
            self._auto_submit_all_questions()

            # Generate results file
            self.session.generate_results_file()
            
            # Create submission ZIP
            zip_path = self.session.create_submission_zip()
            
            # Log session finish
            self.session.log("SESSION_FINISH_TIMEOUT", f"Total Score: {self.session.get_total_score():.2f}")
            
            print(self._msg('zip_submission', zip_name=zip_path.name))
            print(self._msg('zip_submission_info'))
            
            self.session.is_finished = True
        except Exception as e:
            print(f"Error during auto-finish: {e}")
            self.session.log("ERROR", f"Auto-finish error: {e}")
    
    def _auto_submit_all_questions(self):
        """Auto-submit all questions that haven't been submitted yet."""
        submitted_count = 0
        
        for i in range(self.session.config.total_questions):
            qn = f"q{i+1}"
            task = self.session.assigned_tasks.get(qn)
            
            # Skip if already submitted or no task assigned
            if not task or self.session.submissions.get(qn) is not None:
                continue
            
            code_file = Path(f"{qn}.py")
            if not code_file.exists():
                if self.language == 'fr':
                    print(f"Avertissement: {qn}.py introuvable, soumission ignorée")
                else:
                    print(f"Warning: {qn}.py not found, skipping submission")
                continue
            
            print(f"Soumission automatique {qn}...") if self.language == 'fr' else print(f"Auto-submitting {qn}...")
            
            # Run final test
            results = self.session.grader.grade_submission(task, str(code_file))
            
            # Read code for SHA256
            with open(code_file, 'rb') as f:
                code_bytes = f.read()
            code_sha256 = hashlib.sha256(code_bytes).hexdigest()
            
            # Get max score for this task
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
            
            # Log auto-submission
            self.session.log(
                "AUTO_SUBMISSION",
                f"Question: {qn}, Score: {results['score']:.2f}, Code SHA256: {code_sha256}"
            )
            
            submitted_count += 1
        
        if submitted_count > 0:
            if self.language == 'fr': print(f"{submitted_count} question(s) soumise(s) automatiquement.")
            else: print(f"Auto-submitted {submitted_count} question(s).")
        else:
            if self.language == 'fr': print("Toutes les questions ont déjà été soumises.")
            else: print("All questions were already submitted.")
    
    def _monitor_network_background(self):
        """Background network monitoring thread."""
        last_check_time = time.time()
        # Use check interval from bank configuration
        check_interval = self.bank.network_monitoring.check_interval_seconds
        check_count = 0
        
        while self.network_monitor_active:
            current_time = time.time()
            if current_time - last_check_time >= check_interval:
                check_count += 1
                has_connectivity = check_internet_connectivity()
                
                # Log every connectivity check (whether connected or not)
                status = "CONNECTED" if has_connectivity else "OFFLINE"
                self.session.log("NETWORK_CHECK", f"Check #{check_count}: Internet status = {status}")
                
                if has_connectivity:
                    self._handle_network_detected()
                    last_check_time = current_time
                else:
                    last_check_time = current_time
            time.sleep(1)  # Avoid busy waiting
    
    def _handle_network_detected(self):
        """Handle when network connectivity is detected during exam."""
        print("\n" + "!"*60)
        print(f"⚠️  {self._msg('network_detected_exam')} ⚠️")
        print(self._msg("network_instructions_exam_1"))
        print(self._msg("network_instructions_2"))
        print(self._msg("network_instructions_exam_3"))
        print("!"*60)
        
        self.session.log("NETWORK_DETECTED", "Internet connection detected during exam - exam paused")
        
        # Wait for network to go offline
        wait_count = 0
        while check_internet_connectivity():
            wait_count += 1
            time.sleep(2)
            print(self._msg("network_still_detected_exam"))
            # Log every 10 seconds of waiting
            if wait_count % 5 == 0:  # Every 10 seconds
                self.session.log("NETWORK_WAITING", f"Still connected after {wait_count * 2} seconds")
        
        print(f"\n✓ {self._msg('network_disconnected_exam')}")
        print(self._msg("network_disconnected_con"))
        self.session.log("NETWORK_DISCONNECTED", "Internet connection removed - exam resumed")
    
    def command_loop(self):
        """Main interactive command loop."""
        print("\n" + self._msg("header"))
        print(self._msg("cmd_help_text"))
        print(self._msg("header") + "\n")

        # Track file modification times for copy-paste detection
        self.file_mod_times = {}
        for i in range(self.session.config.total_questions):
            qn = f"q{i+1}"
            code_file = Path(f"{qn}.py")
            if code_file.exists():
                self.file_mod_times[qn] = code_file.stat().st_mtime
        
        while not self.session.is_finished:
            try:
                # Save timer state periodically
                self.session.save_timer_state()

                # Check if time has expired and show warning
                if self.time_expired_warning_shown and not self.session.is_finished:
                    print("\n" + "!"*60)
                    print(self._msg("cmd_time_finish"))
                    print(self._msg("cmd_time_finish_warning"))
                    print("!"*60)
                    
                    try:
                        response = input("\nHave you saved all your changes? Type 'yes' to continue: ").strip().lower()
                        if response == 'yes':
                            print("\nAuto-submitting all unsubmitted questions...")
                            self._auto_finish_exam()
                        else:
                            print("\nPlease save your changes first, then type 'yes'.")
                            self.time_expired_warning_shown = False
                            continue
                    except (KeyboardInterrupt, EOFError):
                        print("\n\nAuto-submitting all questions and finishing exam...")
                        self._auto_finish_exam()
                    
                    break

                # Check if time has expired before each command
                if self.session.is_time_expired():
                    print(f"\n{self._msg('cmd_time_finish')}")
                    self._auto_finish_exam()
                    break

                cmd_line = input("exam> ").strip()
                if not cmd_line:
                    continue

                parts = cmd_line.split()
                command = parts[0].lower()

                # Check for file modifications (indicates student editing)
                self._check_file_modifications()

                # Log command
                self.session.log("COMMAND_RUN", f"Command: {cmd_line}")
                
                # Route command
                if command in ['exit', 'quit']:
                    self.cmd_exit()
                elif command == 'finish':
                    self.cmd_finish()
                elif command == 'help':
                    self.cmd_help()
                elif command in [f'q{i+1}' for i in range(self.session.config.total_questions)]:
                    self.cmd_show_question(command)
                elif command == 'test':
                    if len(parts) < 2:
                        print(self._msg("cmd_test_usage"))
                    else:
                        self.cmd_test(parts[1].lower())
                elif command == 'debug':
                    if len(parts) < 2:
                        print(self._msg("cmd_debug_usage"))
                    else:
                        self.cmd_debug(parts[1].lower())
                elif command == 'hint':
                    if len(parts) < 2:
                        print(self._msg("cmd_hint_usage"))
                    else:
                        self.cmd_hint(parts[1].lower())
                elif command == 'submit':
                    if len(parts) < 2:
                        print(self._msg("cmd_submit_usage"))
                    else:
                        self.cmd_submit(parts[1].lower())
                elif command == 'status':
                    self.cmd_status()
                elif command == 'time':
                    self.cmd_time()
                else:
                    print(f"Unknown command: '{command}'. Type 'help' for a list of commands.")
            
            except (KeyboardInterrupt, EOFError):
                print("\nUse 'exit' to save progress or 'finish' to complete the exam.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                self.session.log("ERROR", str(e))
    
    def _check_file_modifications(self):
        """Check if code files have been modified (for copy-paste detection)."""
        for i in range(self.session.config.total_questions):
            qn = f"q{i+1}"
            code_file = Path(f"{qn}.py")
            
            if code_file.exists():
                current_mtime = code_file.stat().st_mtime
                last_mtime = self.file_mod_times.get(qn, 0)
                
                if current_mtime != last_mtime:
                    # File was modified
                    size_diff = code_file.stat().st_size
                    if last_mtime > 0:  # Not the first check
                        size_increase = size_diff - (self.file_sizes.get(qn, 0) if hasattr(self, 'file_sizes') else 0)
                        if size_increase > 200:  # Large addition
                            self.session.log("LARGE_CODE_ADDITION", 
                                           f"Question {qn}: +{size_increase} bytes added rapidly")
                    
                    self.file_mod_times[qn] = current_mtime
                    if not hasattr(self, 'file_sizes'):
                        self.file_sizes = {}
                    self.file_sizes[qn] = size_diff

    def cmd_help(self):
        """Display help message."""
        # Generate question list dynamically
        question_list = ", ".join([f"q{i+1}" for i in range(self.session.config.total_questions)])
        print(self._msg("cmd_help", questions=question_list))
    
    def cmd_time(self):
        """Display remaining exam time."""
        remaining_time = self.session.format_remaining_time()
        elapsed_minutes = (datetime.now() - self.session.exam_start_time).total_seconds() / 60
        elapsed_formatted = f"{elapsed_minutes:.1f}"
        
        print()
        print(self._msg("cmd_time_heading", remaining=remaining_time))
        if self.config.exam_time_minutes == -1:
            print(self._msg("cmd_time_elapsed", elapsed=elapsed_formatted))
        else:
            total_minutes = self.config.exam_time_minutes
            print(self._msg("cmd_time_elapsed_total", elapsed=elapsed_formatted, total=total_minutes))
        
        if self.session.exam_end_time is not None:
            remaining_minutes = self.session.get_remaining_time().total_seconds() / 60
            if remaining_minutes <= 30:
                print(self._msg("cmd_time_warning", minutes=30))
        
        print()
    
    def cmd_show_question(self, qn: str):
        """Display the prompt for a question."""
        valid_questions = [f'q{i+1}' for i in range(self.session.config.total_questions)]
        if qn not in valid_questions:
            print(self._msg("cmd_question_invalid", qn=qn, valid_questions=', '.join(valid_questions)))
            return
        
        task = self.session.assigned_tasks.get(qn)
        if not task:
            print(self._msg("cmd_question_not_assigned", qn=qn))
            return
        
        if task in self.bank.easy:
            difficulty = self._msg("difficulty_easy")
        elif task in self.bank.medium:
            difficulty = self._msg("difficulty_medium")
        else:
            difficulty = self._msg("difficulty_hard")
        
        print()
        print(self._msg("cmd_show_heading", number=qn[1:], difficulty=difficulty, title=task.title))
        print(self._msg("cmd_show_id", task_id=task.id))
        print()
        print(self._msg("cmd_show_prompt_label"))
        print(task.prompt)
        print()
        print(self._msg("cmd_show_io_mode", mode=task.io.mode))
        
        if task.visible_sample:
            print()
            print(self._msg("cmd_show_sample_label"))
            if task.visible_sample.input:
                print(self._msg("cmd_show_sample_input"))
                print(task.visible_sample.input)
                print(self._msg("cmd_show_sample_output"))
                print(task.visible_sample.output)
            elif task.visible_sample.args is not None:
                print(self._msg("cmd_show_sample_args"))
                is_sudoku = self._is_sudoku_question(task)
                if is_sudoku and task.visible_sample.args:
                    self._print_sudoku_board(task.visible_sample.args[0])
                else:
                    print(task.visible_sample.args)
                if task.visible_sample.ret is not None:
                    print(self._msg("cmd_show_sample_ret", value=task.visible_sample.ret))
        
        code_file = Path(f"{qn}.py")
        if not code_file.exists():
            if self.language == 'fr':
                self._create_code_file_fr(qn, task)
            else:
                self._create_code_file(qn, task)
            print()
            print(self._msg("cmd_show_question_1", qn=qn))
        else:
            print()
            print(self._msg("cmd_show_question_2", qn=qn))
        
        print()

    def _is_sudoku_question(self, task) -> bool:
        """Check if a task is about Sudoku based on its content."""
        sudoku_keywords = ["sudoku", "9x9 matrix", "9x9 matrix"]
        
        title_lower = task.title.lower()
        prompt_lower = task.prompt.lower()
        
        for keyword in sudoku_keywords:
            if keyword in title_lower or keyword in prompt_lower:
                return True
        
        # Additional check: if args looks like a 9x9 grid
        if task.visible_sample and task.visible_sample.args:
            args = task.visible_sample.args
            if (len(args) == 1 and 
                isinstance(args[0], list) and 
                len(args[0]) == 9 and 
                all(isinstance(row, list) and len(row) == 9 for row in args[0])):
                return True
        
        return False
    
    def _print_sudoku_board(self, board: list[list[str]]) -> None:
        """Print a Sudoku board in a nicely formatted way."""
        print("┌───────┬───────┬───────┐")
        for i in range(9):
            if i % 3 == 0 and i != 0:
                print("├───────┼───────┼───────┤")
            
            row_str = "│"
            for j in range(9):
                if j % 3 == 0 and j != 0:
                    row_str += " │"
                cell = board[i][j] if board[i][j] != "." else " "
                row_str += f" {cell}"
            
            row_str += " │"
            print(row_str)
        
        print("└───────┴───────┴───────┘")
    
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
    
    def _create_code_file_fr(self, qn: str, task: Task):
        """Create a starter code file for a question with prompt and sample in French."""
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
            code_lines.append("# EXEMPLE:")
            if task.visible_sample.input:
                code_lines.append(f"# Entrée: {repr(task.visible_sample.input.rstrip())}")
                code_lines.append(f"# Sortie: {repr(task.visible_sample.output.rstrip())}")
            elif task.visible_sample.args is not None:
                code_lines.append(f"# Arguments: {task.visible_sample.args}")
                code_lines.append(f"# Rendement Attendu: {task.visible_sample.ret}")
            code_lines.append("")
        
        code_lines.append("#" + "="*70)
        code_lines.append("")
        
        # Add mode-specific template
        if task.io.mode == "stdin_stdout":
            code_lines.append("# Lire l'entrée depuis stdin et écrire la sortie vers stdout")
            code_lines.append("# Utilisez input() pour lire et print() pour écrire.")
            code_lines.append("")
            code_lines.append("# Votre code ici")
            code_lines.append("")
        
        elif task.io.mode == "function":
            code_lines.append("# IMPORTANT: Ne modifiez pas le nom de la fonction!")
            code_lines.append("")
            
            # Extract function signature from prompt if available
            signature = self._extract_function_signature(task)
            if signature:
                code_lines.append(signature)
            else:
                # Fallback to basic template
                code_lines.append(f"def {task.io.entrypoint}():")
            
            code_lines.append("    # Votre code ici")
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
        question_list = ', '.join(valid_questions)
        if qn not in valid_questions:
            print(self._msg("cmd_question_invalid", qn=qn, valid_questions=question_list))
            return
        
        task = self.session.assigned_tasks.get(qn)
        if not task:
            print(self._msg("cmd_question_not_assigned", qn=qn))
            return
        
        code_file = Path(f"{qn}.py")
        if not code_file.exists():
            print(self._msg("cmd_question_missing_file", qn=qn))
            return
        
        print()
        print(self._msg("cmd_test_running", count=len(task.tests), qn=qn))
        print()
        
        results = self.session.grader.grade_submission(task, str(code_file))
        if results['passed'] < results['total']:
            self.session.failed_attempts[qn] = self.session.failed_attempts.get(qn, 0) + 1
        
        show_details = os.environ.get('EXAM_DEBUG', '').lower() in ['1', 'true', 'yes']
        formatted_output = self.session.grader.format_test_results(results, show_details=show_details)
        print(formatted_output)
        
        self.session.log("TEST_RESULT", f"Question: {qn}, Passed: {results['passed']}/{results['total']}")
        print()
    def cmd_debug(self, qn: str):
        """Run tests with detailed error output for debugging."""
        valid_questions = [f'q{i+1}' for i in range(self.session.config.total_questions)]
        question_list = ', '.join(valid_questions)
        if qn not in valid_questions:
            print(self._msg("cmd_question_invalid", qn=qn, valid_questions=question_list))
            return
        
        task = self.session.assigned_tasks.get(qn)
        if not task:
            print(self._msg("cmd_question_not_assigned", qn=qn))
            return
        
        code_file = Path(f"{qn}.py")
        if not code_file.exists():
            print(self._msg("cmd_question_missing_file", qn=qn))
            return
        
        print()
        print(self._msg("cmd_debug_running", count=len(task.tests), qn=qn))
        print()
        
        results = self.session.grader.grade_submission(task, str(code_file))
        if results['passed'] < results['total']:
            self.session.failed_attempts[qn] = self.session.failed_attempts.get(qn, 0) + 1
        
        formatted_output = self.session.grader.format_test_results(results, show_details=True)
        print(formatted_output)
        
        self.session.log("DEBUG_TEST", f"Question: {qn}, Passed: {results['passed']}/{results['total']}")
        print()
    def cmd_hint(self, qn: str):
        """Display hints for a question based on progress."""
        valid_questions = [f'q{i+1}' for i in range(self.session.config.total_questions)]
        question_list = ', '.join(valid_questions)
        if qn not in valid_questions:
            print(self._msg("cmd_question_invalid", qn=qn, valid_questions=question_list))
            return

        task = self.session.assigned_tasks.get(qn)
        if not task:
            print(self._msg("cmd_question_not_assigned", qn=qn))
            return

        if not task.hints:
            print()
            print(self._msg("cmd_hint_none", qn=qn))
            print()
            return

        code_file = Path(f"{qn}.py")
        if not code_file.exists():
            print()
            print(self._msg("cmd_hint_need_tests", qn=qn))
            print(self._msg("cmd_hint_need_tests_help"))
            print()
            return

        results = self.session.grader.grade_submission(task, str(code_file))
        passed = results['passed']
        total = results['total']
        pass_rate = passed / total if total > 0 else 0.0

        if pass_rate >= 1.0:
            print()
            print(self._msg("cmd_hint_congrats_title", qn=qn))
            print(self._msg("cmd_hint_congrats_body"))
            print(self._msg("cmd_hint_congrats_body2"))
            print()
            return
        elif pass_rate >= 2 / 3:
            max_hints = len(task.hints)
        elif pass_rate >= 1 / 3:
            max_hints = math.ceil(len(task.hints) / 2)
        else:
            attempts = self.session.failed_attempts.get(qn, 0)
            if attempts < 3:
                print()
                print(self._msg("cmd_hint_attempts_blocked", qn=qn))
                print(self._msg("cmd_hint_attempts_need", attempts=3))
                print(self._msg("cmd_hint_attempts_current", current=attempts))
                print(self._msg("cmd_hint_keep_trying"))
                print()
                return
            max_hints = min(len(task.hints), attempts - 2)

        print()
        print(self._msg("cmd_hint_header", qn=qn, task_id=task.id, title=task.title))
        print(self._msg("cmd_hint_progress", passed=passed, total=total))
        print("=" * 50)

        for i in range(max_hints):
            print(f"{i + 1}. {task.hints[i]}")

        if max_hints < len(task.hints):
            remaining = len(task.hints) - max_hints
            if pass_rate == 0:
                next_attempts = max_hints + 2
                print()
                print(self._msg("cmd_hint_more_attempts", remaining=remaining, next_attempts=next_attempts))
            elif max_hints == math.ceil(len(task.hints) / 2):
                next_tests = math.ceil(2 / 3 * total)
                print()
                print(self._msg("cmd_hint_more_tests", remaining=remaining, next_tests=next_tests, total=total))

        print("=" * 50)
        print(self._msg("cmd_hint_footer_title"))
        print(self._msg("cmd_hint_footer_body"))
        print()

        self.session.log("HINT_REQUEST", f"Question: {qn}, Progress: {passed}/{total}, Hints shown: {max_hints}")
    def cmd_submit(self, qn: str):
        """Submit code for a question."""
        valid_questions = [f'q{i+1}' for i in range(self.session.config.total_questions)]
        question_list = ', '.join(valid_questions)
        if qn not in valid_questions:
            print(self._msg("cmd_question_invalid", qn=qn, valid_questions=question_list))
            return
        
        task = self.session.assigned_tasks.get(qn)
        if not task:
            print(self._msg("cmd_question_not_assigned", qn=qn))
            return
        
        code_file = Path(f"{qn}.py")
        if not code_file.exists():
            print(self._msg("cmd_question_missing_file", qn=qn))
            return
        
        print()
        print(self._msg("cmd_submit_start", qn=qn))
        
        results = self.session.grader.grade_submission(task, str(code_file))
        
        with open(code_file, 'rb') as f:
            code_bytes = f.read()
        code_sha256 = hashlib.sha256(code_bytes).hexdigest()
        max_score = results.get("max_score", 0.0)
        
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
        
        print(self._msg("cmd_submit_result", passed=results['passed'], total=results['total'], score=results['score'], max_score=max_score))
        print(self._msg("cmd_submit_saved"))
        print(self._msg("cmd_submit_reminder"))
        
        self.session.save_timer_state()
        self.session.log("SUBMISSION", f"Question: {qn}, Score: {results['score']:.2f}, Code SHA256: {code_sha256}")
        print()

    def cmd_status(self):
        """Display submission status."""
        print()
        print(self._msg("cmd_status_header", student=self.session.student_name))
        
        for i in range(self.session.config.total_questions):
            qn = f"q{i+1}"
            task = self.session.assigned_tasks.get(qn)
            sub = self.session.submissions.get(qn)
            
            if task:
                status_str = f"- {qn} ({task.id}): "
                if sub:
                    max_score = sub.get('max_score', 0.0)
                    status_str += self._msg("cmd_status_submitted", score=sub['score'], max_score=max_score, passed=sub['passed'], total=sub['total'])
                else:
                    status_str += self._msg("cmd_status_missing")
                print(status_str)
        
        print()
        print(self._msg("cmd_status_total", total_score=self.session.get_total_score(), max_score=self.session.get_max_score()))
        print()

    def cmd_exit(self):
        """Exit the current exam session without finishing."""
        print()
        print(self._msg("cmd_exit_message"))
        print(self._msg("cmd_exit_resume"))
        self.session.log("SESSION_EXIT", "User exited session - progress saved")
        self.session.is_finished = True

    def cmd_finish(self):
        """Finalize the exam and create submission package."""
        submitted_count = sum(1 for sub in self.session.submissions.values() if sub is not None)

        print()
        print(self._msg("cmd_finish_summary", submitted_count=submitted_count, questions=self.session.config.total_questions))

        try:
            confirm = input(self._msg("cmd_finish_confirm")).strip().lower()
            if confirm != 'y':
                print(self._msg("cmd_finish_continue"))
                return
        except (KeyboardInterrupt, EOFError):
            print()
            print(self._msg("cmd_finish_cancel"))
            return

        print()
        print(self._msg("cmd_finish_processing"))

        self.session.generate_results_file()
        zip_path = self.session.create_submission_zip()

        if self.session.timer_state_path.exists():
            self.session.timer_state_path.unlink()

        self.session.log("SESSION_FINISH", f"Total Score: {self.session.get_total_score():.2f}")

        print(self._msg('zip_submission', zip_name=zip_path.name))
        print(self._msg('zip_submission_info'))

        self.session.is_finished = True


def main():
    """Entry point for the exam runner."""
    runner = ExamRunner()
    sys.exit(runner.run())


if __name__ == "__main__":
    main()
