"""
Secure sandbox for executing student code with resource limits.

Provides cross-platform isolation using subprocess with interpreter flags.
Unix: Uses resource module for CPU time and memory limits.
Windows: Uses timeout parameter (wall-clock time only).
"""

import sys
import json
import subprocess
import platform
import tempfile
import shutil
from pathlib import Path
from typing import Tuple


def get_python_executable():
    """Get the appropriate Python executable path."""
    if getattr(sys, 'frozen', False):
        python_path = shutil.which('python')
        if not python_path:
            python_path = shutil.which('python3')
        
        if python_path:
            return python_path, ['-I', '-B']
        else:
            raise RuntimeError("Python executable not found. Please ensure Python is installed on the exam machines.")
    else:
        return sys.executable, ['-I', '-B']

PYTHON_EXE, ISOLATION_FLAGS = get_python_executable()


def run_code_stdin_stdout(
    code_path: str,
    input_str: str,
    timeout_sec: float,
    memory_limit_mb: int
) -> Tuple[str, str, str]:
    """
    Run a Python script in sandbox mode with stdin/stdout redirection.
    
    Args:
        code_path: Path to the student's Python file
        input_str: Input to feed via stdin
        timeout_sec: Timeout in seconds
        memory_limit_mb: Memory limit in MB (Unix only)
    
    Returns:
        Tuple of (status, stdout, stderr)
        status: "success", "timeout", "runtime_error", "memory_error"
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_code_path = Path(temp_dir) / Path(code_path).name
        shutil.copy(code_path, temp_code_path)
        
        command = [PYTHON_EXE, *ISOLATION_FLAGS, str(temp_code_path)]
        
        try:
            if platform.system() != "Windows":
                # Unix-like systems: use preexec_fn with resource limits
                def set_limits():
                    try:
                        import resource
                        # Set CPU time limit
                        try:
                            resource.setrlimit(resource.RLIMIT_CPU, (int(timeout_sec) + 1, int(timeout_sec) + 1))
                        except (ValueError, OSError):
                            pass
                        
                        # Set memory limit (bytes)
                        try:
                            memory_bytes = memory_limit_mb * 1024 * 1024
                            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
                        except (ValueError, OSError):
                            pass
                    except ImportError:
                        pass
                
                proc = subprocess.run(
                    command,
                    input=input_str.encode('utf-8'),
                    capture_output=True,
                    timeout=timeout_sec * 2,  # Fallback wall-clock timeout
                    check=False,
                    cwd=temp_dir,
                    preexec_fn=set_limits
                )
            else:
                # Windows: rely on timeout parameter only
                proc = subprocess.run(
                    command,
                    input=input_str.encode('utf-8'),
                    capture_output=True,
                    timeout=timeout_sec,
                    check=False,
                    cwd=temp_dir
                )
            
            stdout = proc.stdout.decode('utf-8', errors='replace')
            stderr = proc.stderr.decode('utf-8', errors='replace')
            
            if 'MemoryError' in stderr or 'memory' in stderr.lower():
                return "memory_error", stdout, stderr
            
            if proc.returncode == 0:
                return "success", stdout, stderr
            else:
                return "runtime_error", stdout, stderr
        
        except subprocess.TimeoutExpired:
            return "timeout", "", "Process exceeded time limit"
        except MemoryError:
            return "memory_error", "", "Memory limit exceeded"
        except Exception as e:
            return "runtime_error", "", f"Execution error: {str(e)}"


def run_code_function(
    code_path: str,
    function_name: str,
    args: list,
    timeout_sec: float,
    memory_limit_mb: int
) -> Tuple[str, any, str]:
    """
    Run a Python function from a file in sandbox mode.
    
    Args:
        code_path: Path to the student's Python file
        function_name: Name of the function to call
        args: List of arguments to pass to the function
        timeout_sec: Timeout in seconds
        memory_limit_mb: Memory limit in MB (Unix only)
    
    Returns:
        Tuple of (status, return_value, error_message)
        status: "success", "timeout", "runtime_error", "memory_error", "import_error"
    """
    student_module_name = Path(code_path).stem

    wrapper_code = f"""
import sys
import json
import os

# Add current directory to sys.path to enable imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import student module
try:
    import {student_module_name} as student_module
except Exception as e:
    print(json.dumps({{"error": "import_error", "message": str(e)}}))
    sys.exit(1)

# Get the function
try:
    func = getattr(student_module, '{function_name}')
except AttributeError:
    print(json.dumps({{"error": "function_not_found", "message": "Function '{function_name}' not found"}}))
    sys.exit(1)

# Load arguments
args = json.loads(sys.stdin.read())

# Call the function
try:
    result = func(*args)
    print(json.dumps({{"result": result}}))
except Exception as e:
    print(json.dumps({{"error": "runtime_error", "message": str(e)}}))
    sys.exit(1)
"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_code_path = Path(temp_dir) / Path(code_path).name
        shutil.copy(code_path, temp_code_path)
        
        wrapper_path = Path(temp_dir) / "__wrapper__.py"
        with open(wrapper_path, 'w', encoding='utf-8') as f:
            f.write(wrapper_code)
        
        input_json = json.dumps(args)
        
        command = [PYTHON_EXE, *ISOLATION_FLAGS, str(wrapper_path)]
        
        try:
            if platform.system() != "Windows":
                def set_limits():
                    try:
                        import resource
                        try:
                            resource.setrlimit(resource.RLIMIT_CPU, (int(timeout_sec) + 1, int(timeout_sec) + 1))
                        except (ValueError, OSError):
                            pass

                        try:
                            memory_bytes = memory_limit_mb * 1024 * 1024
                            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
                        except (ValueError, OSError):
                            pass 
                    except ImportError:
                        pass
                
                proc = subprocess.run(
                    command,
                    input=input_json.encode('utf-8'),
                    capture_output=True,
                    timeout=timeout_sec * 2,
                    check=False,
                    cwd=temp_dir,
                    preexec_fn=set_limits
                )
            else:
                proc = subprocess.run(
                    command,
                    input=input_json.encode('utf-8'),
                    capture_output=True,
                    timeout=timeout_sec,
                    check=False,
                    cwd=temp_dir
                )
            
            stdout = proc.stdout.decode('utf-8', errors='replace')
            stderr = proc.stderr.decode('utf-8', errors='replace')

            try:
                result_data = json.loads(stdout)
                
                if "error" in result_data:
                    error_type = result_data["error"]
                    error_msg = result_data.get("message", "Unknown error")
                    
                    if error_type == "import_error":
                        return "import_error", None, error_msg
                    elif error_type == "function_not_found":
                        return "runtime_error", None, error_msg
                    else:
                        return "runtime_error", None, error_msg
                
                if "result" in result_data:
                    return "success", result_data["result"], ""
                
                return "runtime_error", None, "Invalid response format"
            
            except json.JSONDecodeError:
                if 'MemoryError' in stderr or 'memory' in stderr.lower():
                    return "memory_error", None, "Memory limit exceeded"
                return "runtime_error", None, f"Failed to parse output: {stdout[:200]}"
        
        except subprocess.TimeoutExpired:
            return "timeout", None, "Process exceeded time limit"
        except MemoryError:
            return "memory_error", None, "Memory limit exceeded"
        except Exception as e:
            return "runtime_error", None, f"Execution error: {str(e)}"

