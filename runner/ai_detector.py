"""
AI Autocomplete Detection Module

Monitors for AI coding assistants and suspicious activity during exams.
Provides cross-platform detection of AI tools and usage patterns.
"""

import os
import re
import json
import time
import platform
import subprocess
import threading
from typing import List, Optional, Tuple

from .ai_tools_config import AI_PROCESSES, LLM_PROCESSES, AI_EXTENSION_META


class AIDetector:
    """Detects AI coding assistants and suspicious activity during exams."""
    
    def __init__(self, session_logger=None):
        self.session_logger = session_logger
        self.monitoring_active = False
        self.detection_thread = None
        
        # known AI coding assistants
        self.ai_processes = AI_PROCESSES

        # known LLM platforms and AI tools
        self.llm_processes = LLM_PROCESSES

        # AI extension metadata
        self.ai_extension_meta = AI_EXTENSION_META

        self.last_clipboard_content = ""
        self.clipboard_check_interval = 30  # seconds
        self.process_check_interval = 60    # seconds
        self.last_process_check = 0
        self.last_clipboard_check = 0
        
        # detection thresholds
        self.large_paste_threshold = 100  # characters
        self.suspicious_paste_count = 0
        self.max_suspicious_pastes = 3
    
    def start_monitoring(self):
        """Start background AI detection monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.detection_thread = threading.Thread(
            target=self._monitor_background,
            daemon=True
        )
        self.detection_thread.start()
        
        if self.session_logger:
            self.session_logger("AI_MONITORING_STARTED", "AI detection monitoring activated")
    
    def stop_monitoring(self):
        """Stop background AI detection monitoring."""
        self.monitoring_active = False
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=2.0)
        
        if self.session_logger:
            self.session_logger("AI_MONITORING_STOPPED", "AI detection monitoring deactivated")
    
    def _monitor_background(self):
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                current_time = time.time()
                
                # AI processes check periodically
                if current_time - self.last_process_check >= self.process_check_interval:
                    self._check_ai_processes()
                    self.last_process_check = current_time
                
                # suspicious activity check
                if current_time - self.last_clipboard_check >= self.clipboard_check_interval:
                    self._check_clipboard_activity() # suspicious large code pastes
                    self.last_clipboard_check = current_time
                
                time.sleep(5)
                
            except Exception as e:
                if self.session_logger:
                    self.session_logger("AI_MONITORING_ERROR", f"Monitoring error: {str(e)}")
                time.sleep(10)
    
    def _check_ai_processes(self):
        """Check for running AI coding assistant processes."""
        system = platform.system().lower()
        if system not in self.ai_processes:
            return
        
        target_processes = self.ai_processes[system] + self.llm_processes[system]
        running_ai_processes = []
        
        try:
            if system == "windows":
                running_ai_processes = self._check_processes_windows(target_processes)
            else:
                running_ai_processes = self._check_processes_unix(target_processes)
            
            # IDE-integrated tools check
            ide_detected, ide_tools = self.check_ide_ai_tools()
            if ide_detected:
                running_ai_processes.extend(ide_tools)
            
            if running_ai_processes:
                self._handle_ai_processes_detected(running_ai_processes)
                
        except Exception as e:
            if self.session_logger:
                self.session_logger("AI_PROCESS_CHECK_ERROR", f"Process check failed: {str(e)}")
    
    def _check_processes_windows(self, target_processes: List[str]) -> List[str]:
        """Check for AI processes on Windows using tasklist."""
        running_processes = []
        try:
            result = subprocess.run(
                ['tasklist', '/FO', 'CSV', '/NH'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        # CSV format: "process.exe","PID","Session","Mem Usage"
                        parts = line.split('","')
                        if len(parts) >= 1:
                            process_name = parts[0].strip('"').lower()
                            for ai_proc in target_processes:
                                if ai_proc.lower() in process_name:
                                    running_processes.append(process_name)
                                    break
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            # Fallback: try psutil if available
            try:
                import psutil
                for proc in psutil.process_iter(['name']):
                    try:
                        proc_name = proc.info['name'].lower()
                        for ai_proc in target_processes:
                            if ai_proc.lower() in proc_name:
                                running_processes.append(proc_name)
                                break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except ImportError:
                pass
        
        return list(set(running_processes))
    
    def _check_processes_unix(self, target_processes: List[str]) -> List[str]:
        """Check for AI processes on Unix-like systems using ps."""
        running_processes = []
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 11:  # Standard ps aux format
                        command_line = ' '.join(parts[10:]).lower()
                        for ai_proc in target_processes:
                            pattern = r'\b' + re.escape(ai_proc.lower()) + r'\b'
                            if re.search(pattern, command_line):
                                running_processes.append(ai_proc)
                                break
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            # Fallback: try psutil if available
            try:
                import psutil
                for proc in psutil.process_iter(['name', 'cmdline']):
                    try:
                        proc_name = proc.info['name'].lower()
                        cmdline = ' '.join(proc.info.get('cmdline', [])).lower()
                        
                        for ai_proc in target_processes:
                            pattern = r'\b' + re.escape(ai_proc.lower()) + r'\b'
                            if (re.search(pattern, proc_name) or 
                                re.search(pattern, cmdline)):
                                running_processes.append(proc_name)
                                break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except ImportError:
                pass
        
        return list(set(running_processes))
    
    def _check_clipboard_activity(self):
        """Check clipboard for suspicious large code pastes."""
        try:
            clipboard_content = self._get_clipboard_content()
            if clipboard_content and clipboard_content != self.last_clipboard_content:
                
                # large code-like content check
                if self._is_suspicious_paste(clipboard_content):
                    self.suspicious_paste_count += 1
                    
                    if self.session_logger:
                        content_preview = clipboard_content[:200] + "..." if len(clipboard_content) > 200 else clipboard_content
                        self.session_logger("SUSPICIOUS_PASTE", 
                                          f"Large code paste detected ({len(clipboard_content)} chars). "
                                          f"Count: {self.suspicious_paste_count}. Preview: {content_preview}")
                    
                    if self.suspicious_paste_count >= self.max_suspicious_pastes:
                        self._handle_excessive_suspicious_activity()
                
                self.last_clipboard_content = clipboard_content
                
        except Exception as e:
            pass
    
    def _get_clipboard_content(self) -> Optional[str]:
        """Get current clipboard content cross-platform."""
        system = platform.system().lower()
        
        try:
            if system == "windows":
                # Windows clipboard access
                import win32clipboard
                import win32con
                
                win32clipboard.OpenClipboard()
                try:
                    if win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
                        data = win32clipboard.GetClipboardData(win32con.CF_TEXT)
                        return data.decode('utf-8', errors='ignore')
                finally:
                    win32clipboard.CloseClipboard()
                    
            elif system == "darwin":  # macOS
                result = subprocess.run(
                    ['pbpaste'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return result.stdout
                    
            else:  # Linux and others
                try:
                    result = subprocess.run(
                        ['xclip', '-o', '-selection', 'clipboard'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        return result.stdout
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
                
                try:
                    result = subprocess.run(
                        ['wl-paste'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        return result.stdout
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
                        
        except Exception:
            pass
        
        return None
    
    def _is_suspicious_paste(self, content: str) -> bool:
        """Determine if clipboard content looks like suspicious code paste."""
        if len(content) < self.large_paste_threshold:
            return False
        
        # code-like patterns
        code_indicators = [
            'def ', 'class ', 'import ', 'from ', 'if ', 'for ', 'while ',
            'try:', 'except:', 'with ', 'return ', 'print(', 'len(',
            'def\n', 'class\n', 'import\n', 'from\n', 'if\n', 'for\n', 'while\n',
            'try:\n', 'except:\n', 'with\n', 'return\n', 'print(\n', 'len(\n',
            '():', '[]', '{}', '==', '!=', '>=', '<=', '+=', '-=', '*=', '/=',
            'and ', 'or ', 'not ', 'True', 'False', 'None'
        ]
        code_matches = sum(1 for indicator in code_indicators if indicator in content)
        return code_matches >= 3
    
    def _handle_ai_processes_detected(self, processes: List[str]):
        """Handle detection of AI coding assistant processes."""
        process_list = ", ".join(processes)
        
        print("\n" + "!"*70)
        print("⚠️  AI CODING ASSISTANT DETECTED! ⚠️")
        print(f"Detected processes: {process_list}")
        print("Please close all AI coding assistants before continuing.")
        print("Common AI tools: GitHub Copilot, Tabnine, Cursor, Codeium, etc.")
        print("!"*70)
        
        if self.session_logger:
            self.session_logger("AI_PROCESS_DETECTED", f"AI processes found: {process_list}")

        self._wait_for_ai_processes_closed(processes)
    
    def _wait_for_ai_processes_closed(self, target_processes: List[str]):
        """Wait for detected AI processes to be closed."""
        print("Monitoring for AI process termination...")
        
        wait_count = 0
        while self.monitoring_active:
            wait_count += 1
            time.sleep(5)
            
            try:
                if platform.system().lower() == "windows":
                    running = self._check_processes_windows(target_processes)
                else:
                    running = self._check_processes_unix(target_processes)
                
                if not running:
                    print("\n✓ AI processes closed. Exam resuming...")
                    print("Press Enter to continue...")
                    if self.session_logger:
                        self.session_logger("AI_PROCESSES_CLOSED", "Detected AI processes have been terminated")
                    break
                    
                if wait_count % 6 == 0:  # Every 30 seconds
                    still_running = ", ".join(running)
                    print(f"Still detecting AI processes: {still_running}")
                    if self.session_logger:
                        self.session_logger("AI_PROCESSES_STILL_RUNNING", 
                                          f"AI processes still active after {wait_count * 5} seconds: {still_running}")
                        
            except Exception as e:
                if self.session_logger:
                    self.session_logger("AI_PROCESS_RECHECK_ERROR", f"Process recheck failed: {str(e)}")
    
    def _handle_excessive_suspicious_activity(self):
        """Handle detection of excessive suspicious clipboard activity."""
        print("\n" + "!"*70)
        print("⚠️  EXCESSIVE SUSPICIOUS ACTIVITY DETECTED! ⚠️")
        print("Multiple large code pastes detected from clipboard.")
        print("Please write your own code. External assistance is not permitted.")
        print("!"*70)
        
        if self.session_logger:
            self.session_logger("EXCESSIVE_SUSPICIOUS_ACTIVITY", 
                              f"Too many suspicious pastes ({self.suspicious_paste_count}) detected")
        
        # reset counter
        self.suspicious_paste_count = 0
    
    def _get_vscode_extensions_via_cli(self, system: str) -> List[str]:
        """Get installed VS Code extensions using CLI."""
        try:
            if system == "windows":
                cmd = ['code.cmd', '--list-extensions']
            else:
                cmd = ['code', '--list-extensions']

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.split('\n') if line.strip()]
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        return []
    
    def _get_vscode_extensions_dir(self, system: str) -> str:
        """Get VS Code extensions directory cross-platform."""
        if system == "windows":
            return os.path.expandvars(r"%USERPROFILE%\.vscode\extensions")
        else:  # Linux
            return os.path.expanduser("~/.vscode/extensions")
    
    def _check_vscode_extensions(self, system: str) -> List[str]:
        """Check for AI extensions installed in VS Code."""
        detected_extensions = set()

        # VS Code CLI
        cli_extensions = self._get_vscode_extensions_via_cli(system)
        if cli_extensions:
            for ext in cli_extensions:
                for ai_ext in self.ai_extension_meta.keys():
                    if ext.startswith(ai_ext):
                        detected_extensions.add(ext)
                        break
            return list(detected_extensions)
        
        # Fallback: Check folders
        ext_dir = self._get_vscode_extensions_dir(system)
        if os.path.exists(ext_dir):
            try:
                for item in os.listdir(ext_dir):
                    for ai_ext in self.ai_extension_meta.keys():
                        if item.startswith(ai_ext):
                            # Optional: Validate with package.json to avoid old leftovers
                            package_path = os.path.join(ext_dir, item, 'package.json')
                            if os.path.exists(package_path):
                                detected_extensions.add(item)
                            break
            except (PermissionError, OSError):
                pass
        
        return list(detected_extensions)
    
    def _check_vscode_global_disabled(self, system: str) -> set:
        """Check globally disabled extensions from VS Code's state database."""
        disabled = set()
        
        # VS Code's global state database
        if system == "windows":
            db_path = os.path.expandvars(r"%APPDATA%\Code\User\globalStorage\state.vscdb")
        elif system == "darwin":
            db_path = os.path.expanduser("~/Library/Application Support/Code/User/globalStorage/state.vscdb")
        else:  # Linux
            db_path = os.path.expanduser("~/.config/Code/User/globalStorage/state.vscdb")
        
        if not os.path.exists(db_path):
            return disabled
        
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            # query for disabled extensions
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'extensionsIdentifiers/disabled'")
            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                if isinstance(data, list):
                    for ext_obj in data:
                        if isinstance(ext_obj, dict) and 'id' in ext_obj:
                            disabled.add(ext_obj['id'])
                elif isinstance(data, dict):
                    disabled.update(data.get('extensions', {}).keys())
            conn.close()
        except (ImportError, sqlite3.Error, json.JSONDecodeError):
            pass
    
        return disabled
    
    def _check_vscode_extension_enabled(self, extension: str, system: str) -> Tuple[bool, str]:
        """Check if an AI extension is enabled, considering defaults and global state."""
        if extension not in self.ai_extension_meta:
            return False, "Unknown extension"
        
        meta = self.ai_extension_meta[extension]
        global_disabled = self._check_vscode_global_disabled(system)
        
        if extension in global_disabled:
            return False, "Disabled globally"
        
        settings = self._load_vscode_settings(system)

        if meta['settings_keys']:
            disabled_reasons = []
            enabled_details = []
            for key, disable_val in zip(meta['settings_keys'], meta['disable_values']):
                setting_val = settings.get(key)
                if setting_val is None:
                    enabled_details.append(f"{key}: default enabled")
                    continue
                if isinstance(setting_val, dict):
                    # Language-specific: enabled if any is True
                    if any(setting_val.values()):
                        enabled_langs = [k for k, v in setting_val.items() if v]
                        enabled_details.append(f"{key}: enabled for {', '.join(enabled_langs)}")
                    else:
                        disabled_reasons.append(f"{key}: disabled for all languages")
                elif setting_val == disable_val:
                    disabled_reasons.append(f"{key}: explicitly disabled")
                else:
                    enabled_details.append(f"{key}: explicitly enabled")

            if enabled_details:
                return True, f"{'; '.join(enabled_details)}"
            
            details = "; ".join(disabled_reasons) if disabled_reasons else "All settings disabled"
            return False, details

        # No explicit settings: use default
        return meta['default_enabled'], "Default state"

    def _load_vscode_settings(self, system: str) -> dict:
        """Load VS Code user settings.json."""
        if system == "windows":
            settings_path = os.path.expandvars(r"%APPDATA%\Code\User\settings.json")
        elif system == "darwin":
            settings_path = os.path.expanduser("~/Library/Application Support/Code/User/settings.json")
        else:  # Linux
            settings_path = os.path.expanduser("~/.config/Code/User/settings.json")
        
        if not os.path.exists(settings_path):
            return {}
        
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def check_ide_ai_tools(self) -> Tuple[bool, List[str]]:
        """
        Comprehensive check for IDE-integrated AI tools.
        
        Returns:
            Tuple of (ai_detected, list_of_detected_tools)
        """
        system = platform.system().lower()
        detected = []
        
        vscode_extensions = self._check_vscode_extensions(system)
        if vscode_extensions:
            for ext in vscode_extensions:
                enabled, details = self._check_vscode_extension_enabled(ext, system)
                if enabled:
                    detected.append(f"VS Code: {ext} ({details})")
        
        # TODO: Add checks for other IDEs (PyCharm, IntelliJ, etc.)
        
        return len(detected) > 0, detected


def check_ai_tools_at_startup() -> Tuple[bool, List[str]]:
    """
    Perform initial AI tool check at exam startup.
    
    Returns:
        Tuple of (ai_tools_detected, list_of_detected_tools)
    """
    detector = AIDetector()
    
    try:
        system = platform.system().lower()
        ai_procs = detector.ai_processes.get(system, []) + detector.llm_processes.get(system, [])
        detected = detector._check_processes_windows(ai_procs) if system == "windows" else detector._check_processes_unix(ai_procs)
        
        ide_detected, ide_tools = detector.check_ide_ai_tools()
        if ide_detected:
            detected.extend(ide_tools)
        
        return len(detected) > 0, detected
        
    except Exception:
        return False, []
