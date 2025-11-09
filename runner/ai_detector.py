"""
AI Autocomplete Detection Module

Monitors for AI coding assistants and suspicious activity during exams.
Provides cross-platform detection of AI tools and usage patterns.
"""

import os
import json
import time
import platform
import subprocess
import threading
from typing import List, Optional, Tuple


class AIDetector:
    """Detects AI coding assistants and suspicious activity during exams."""
    
    def __init__(self, session_logger=None):
        self.session_logger = session_logger
        self.monitoring_active = False
        self.detection_thread = None
        
        # Known AI coding assistants (process names)
        self.ai_processes = {
            'windows': [
                'github.copilot',
                'copilot',
                'tabnine',
                'kite',
                'intellicode',
                'codex',
                # 'cursor',
                'windsor',
                'continue',
                'codium',
                'codewhisperer',
                'aws-toolkit',
                'genie',
                'blackbox',
                'askcodi',
                'mutableai',
                'replit-ghostwriter',
                'refact',
                'codegeex',
                'codeium'
            ],
            'linux': [
                'copilot',
                'tabnine',
                'kite',
                'cursor',
                'codium',
                'codewhisperer',
                'genie',
                'blackbox',
                'askcodi',
                'mutableai',
                'refact',
                'codegeex',
                'codeium'
            ],
            'darwin': [  # macOS
                'copilot',
                'tabnine',
                'kite',
                'cursor',
                'codium',
                'codewhisperer',
                'genie',
                'blackbox',
                'askcodi',
                'mutableai',
                'refact',
                'codegeex',
                'codeium'
            ]
        }
        

        # Detection state
        self.last_clipboard_content = ""
        self.clipboard_check_interval = 30  # seconds
        self.process_check_interval = 60    # seconds
        self.last_process_check = 0
        self.last_clipboard_check = 0
        
        # Detection thresholds
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
                
                # Check for AI processes periodically
                if current_time - self.last_process_check >= self.process_check_interval:
                    self._check_ai_processes()
                    self.last_process_check = current_time
                
                # Check clipboard for suspicious activity
                if current_time - self.last_clipboard_check >= self.clipboard_check_interval:
                    self._check_clipboard_activity() # check for suspicious large code pastes
                    self.last_clipboard_check = current_time
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                if self.session_logger:
                    self.session_logger("AI_MONITORING_ERROR", f"Monitoring error: {str(e)}")
                time.sleep(10)  # Wait longer on errors
    
    def _check_ai_processes(self):
        """Check for running AI coding assistant processes."""
        system = platform.system().lower()
        if system not in self.ai_processes:
            return
        
        target_processes = self.ai_processes[system]
        running_ai_processes = []
        
        try:
            if system == "windows":
                running_ai_processes = self._check_processes_windows(target_processes)
            else:
                running_ai_processes = self._check_processes_unix(target_processes)
            
            # Also check IDE-integrated tools
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
            # Use tasklist command to get running processes
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
                        # Parse CSV format: "process.exe","PID","Session","Mem Usage"
                        parts = line.split('","')
                        if len(parts) >= 1:
                            process_name = parts[0].strip('"').lower()
                            # Check if any target AI process matches
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
        
        return list(set(running_processes))  # Remove duplicates
    
    def _check_processes_unix(self, target_processes: List[str]) -> List[str]:
        """Check for AI processes on Unix-like systems using ps."""
        running_processes = []
        try:
            # Use ps command to get process list
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 11:  # Standard ps aux format
                        command_line = ' '.join(parts[10:]).lower()
                        for ai_proc in target_processes:
                            if ai_proc.lower() in command_line:
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
                            if (ai_proc.lower() in proc_name or 
                                ai_proc.lower() in cmdline):
                                running_processes.append(proc_name)
                                break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except ImportError:
                pass
        
        return list(set(running_processes))  # Remove duplicates
    
    def _check_clipboard_activity(self):
        """Check clipboard for suspicious large code pastes."""
        try:
            clipboard_content = self._get_clipboard_content()
            if clipboard_content and clipboard_content != self.last_clipboard_content:
                
                # Check for large code-like content
                if self._is_suspicious_paste(clipboard_content):
                    self.suspicious_paste_count += 1
                    
                    if self.session_logger:
                        content_preview = clipboard_content[:200] + "..." if len(clipboard_content) > 200 else clipboard_content
                        self.session_logger("SUSPICIOUS_PASTE", 
                                          f"Large code paste detected ({len(clipboard_content)} chars). "
                                          f"Count: {self.suspicious_paste_count}. Preview: {content_preview}")
                    
                    # Alert if too many suspicious pastes
                    if self.suspicious_paste_count >= self.max_suspicious_pastes:
                        self._handle_excessive_suspicious_activity()
                
                self.last_clipboard_content = clipboard_content
                
        except Exception as e:
            # Silently handle clipboard errors (common on some systems)
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
                # Try xclip first (X11)
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
                
                # Try wl-clipboard (Wayland)
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
        
        # Check for code-like patterns
        code_indicators = [
            'def ', 'class ', 'import ', 'from ', 'if ', 'for ', 'while ',
            'try:', 'except:', 'with ', 'return ', 'print(', 'len(',
            'def\n', 'class\n', 'import\n', 'from\n', 'if\n', 'for\n', 'while\n',
            'try:\n', 'except:\n', 'with\n', 'return\n', 'print(\n', 'len(\n',
            '():', '[]', '{}', '==', '!=', '>=', '<=', '+=', '-=', '*=', '/=',
            'and ', 'or ', 'not ', 'True', 'False', 'None'
        ]
        
        # Count code indicators
        code_matches = sum(1 for indicator in code_indicators if indicator in content)
        
        # Consider it suspicious if it has multiple code indicators
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
        
        # Wait for processes to be closed
        self._wait_for_ai_processes_closed(processes)
    
    def _wait_for_ai_processes_closed(self, target_processes: List[str]):
        """Wait for detected AI processes to be closed."""
        print("Monitoring for AI process termination...")
        
        wait_count = 0
        while self.monitoring_active:
            wait_count += 1
            time.sleep(5)
            
            # Recheck processes
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
        
        # Reset counter but keep monitoring
        self.suspicious_paste_count = 0
    
    def _check_vscode_extensions(self) -> List[str]:
        """Check for AI extensions installed in VS Code."""
        system = platform.system().lower()
        detected_extensions = set()
        
        # VS Code extensions directory
        if system == "windows":
            vscode_ext_dir = os.path.expandvars(r"%USERPROFILE%\.vscode\extensions")
        else:
            vscode_ext_dir = os.path.expanduser("~/.vscode/extensions")
        
        # AI extensions to look for
        ai_extensions = [
            'github.copilot',
            'tabnine.tabnine-vscode',
            'visualstudioexptteam.vscodeintellicode',
            'codeium.codeium',
            'amazonwebservices.aws-toolkit-vscode',
            'blackboxapp.blackbox',
            'askcodi.askcodi',
            'mutable-ai.mutable-ai',
            'refact.refact',
            'aminer.codegeex',
            'continue.continue'
        ]
        
        if os.path.exists(vscode_ext_dir):
            try:
                for item in os.listdir(vscode_ext_dir):
                    for ai_ext in ai_extensions:
                        if item.startswith(ai_ext):
                            detected_extensions.add(ai_ext)
                            break
            except (PermissionError, OSError):
                pass
        
        return detected_extensions
    
    def _check_vscode_copilot_enabled(self) -> Tuple[bool, str]:
        """Check if GitHub Copilot is enabled in VS Code settings."""
        system = platform.system().lower()
        
        # VS Code settings path
        if system == "windows":
            settings_path = os.path.expandvars(r"%APPDATA%\Code\User\settings.json")
        elif system == "darwin":  # macOS
            settings_path = os.path.expanduser("~/Library/Application Support/Code/User/settings.json")
        else:  # Linux
            settings_path = os.path.expanduser("~/.config/Code/User/settings.json")
        
        if not os.path.exists(settings_path):
            return False, "VS Code settings not found"
        
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # Check Copilot enable setting
            copilot_enabled = settings.get("github.copilot.enable", {})
            
            # Can be boolean or dict with language-specific settings
            if isinstance(copilot_enabled, dict):
                # Check if enabled for any language
                if any(copilot_enabled.values()):
                    enabled_langs = [k for k, v in copilot_enabled.items() if v]
                    return True, f"Enabled for: {', '.join(enabled_langs)}"
                return False, "Disabled for all languages"
            elif copilot_enabled:
                return True, "Enabled globally"
            else:
                return False, "Disabled"
                
        except (json.JSONDecodeError, IOError, PermissionError):
            return False, "Could not read settings"
    
    def check_ide_ai_tools(self) -> Tuple[bool, List[str]]:
        """
        Comprehensive check for IDE-integrated AI tools.
        
        Returns:
            Tuple of (ai_detected, list_of_detected_tools)
        """
        detected = []
        
        # Check VS Code extensions
        vscode_extensions = self._check_vscode_extensions()
        if vscode_extensions:
            for ext in vscode_extensions:    
                if ext == 'github.copilot':
                    enabled, details = self._check_vscode_copilot_enabled()
                    if enabled:
                        detected.append(f"VS Code: {ext} ({details})")
                    continue
                
                detected.append(f"VS Code: {ext}")
        
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
        if system == "windows":
            detected = detector._check_processes_windows(detector.ai_processes.get(system, []))
        else:
            detected = detector._check_processes_unix(detector.ai_processes.get(system, []))
        
        ide_detected, ide_tools = detector.check_ide_ai_tools()
        if ide_detected:
            detected.extend(ide_tools)
        
        return len(detected) > 0, detected
        
    except Exception:
        return False, []
