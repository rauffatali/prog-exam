"""
Grader module for running test cases and validating student submissions.

Provides the Grader class which orchestrates test execution using the sandbox
and applies various checker functions to validate outputs.
"""

import math
import time
from pathlib import Path
from typing import Dict, List, Tuple, Callable, Any

from .models import Task, ExamConfig
from .sandbox import run_code_stdin_stdout, run_code_function


class Grader:
    """Handles test case execution and output validation."""
    
    def __init__(self, config: ExamConfig):
        """Initialize grader with available checker functions and exam config."""
        self.config = config
        self.checkers: Dict[str, Callable] = {
            "exact_match": self._exact_match,
            "float_isclose": self._float_isclose,
            "unordered_list_equal": self._unordered_list_equal,
        }
    
    # ===== CHECKER FUNCTIONS =====
    
    def _exact_match(self, student_output: Any, expected_output: Any) -> bool:
        """
        Default checker: exact string equality after stripping trailing whitespace.
        
        Args:
            student_output: Output from student code
            expected_output: Expected output from test case
        
        Returns:
            True if outputs match exactly (after rstrip)
        """
        student_str = str(student_output).rstrip()
        expected_str = str(expected_output).rstrip()
        return student_str == expected_str
    
    def _float_isclose(self, student_output: Any, expected_output: Any) -> bool:
        """
        Checker for floating-point numbers with tolerance.
        
        Uses math.isclose with rel_tol=1e-6 (relative tolerance) and abs_tol=1e-8.
        This allows for reasonable floating-point precision differences.
        
        Args:
            student_output: Output from student code
            expected_output: Expected output from test case
        
        Returns:
            True if floats are close within tolerance
        """
        try:
            student_float = float(student_output)
            expected_float = float(expected_output)
            return math.isclose(student_float, expected_float, rel_tol=1e-6, abs_tol=1e-8)
        except (ValueError, TypeError):
            return False
    
    def _unordered_list_equal(self, student_output: Any, expected_output: Any) -> bool:
        """
        Checker for lists where order does not matter.
        
        Assumes outputs are whitespace-separated values. Sorts both lists
        and compares them for equality.
        
        Args:
            student_output: Output from student code
            expected_output: Expected output from test case
        
        Returns:
            True if sorted lists are equal
        """
        try:
            student_list = sorted(str(student_output).strip().split())
            expected_list = sorted(str(expected_output).strip().split())
            return student_list == expected_list
        except Exception:
            return False
    
    # ===== TEST EXECUTION =====
    
    def get_task_difficulty(self, task: Task, bank) -> str:
        """Determine the difficulty level of a task."""
        if task in bank.easy:
            return "easy"
        elif task in bank.medium:
            return "medium"
        elif task in bank.hard:
            return "hard"
        return "unknown"
    
    def grade_submission(
        self,
        task: Task,
        code_path: str
    ) -> Dict[str, Any]:
        """
        Run all test cases for a task and return results.
        
        Args:
            task: Task object containing test cases and configuration
            code_path: Path to the student's Python file
        
        Returns:
            Dictionary containing:
            - passed: Number of passed test cases
            - total: Total number of test cases
            - score: Calculated score based on task difficulty weight
            - max_score: Maximum possible score for this task
            - results: List of individual test results
        """
        if not Path(code_path).exists():
            return {
                "passed": 0,
                "total": len(task.tests),
                "score": 0.0,
                "max_score": 0.0,
                "results": [{"status": "file_not_found", "message": f"File '{code_path}' not found"}]
            }
        
        results = []
        passed_count = 0
        timeout_sec = task.time_limit_ms / 1000.0
        memory_limit_mb = task.memory_limit_mb
        
        # Get checker function
        checker_name = task.checker or "exact_match"
        checker_func = self.checkers.get(checker_name, self._exact_match)
        
        # Determine I/O mode
        if task.io.mode == "stdin_stdout":
            passed_count, results = self._grade_stdin_stdout(
                task, code_path, timeout_sec, memory_limit_mb, checker_func
            )
        elif task.io.mode == "function":
            passed_count, results = self._grade_function(
                task, code_path, timeout_sec, memory_limit_mb, checker_func
            )
        else:
            results = [{"status": "error", "message": f"Unknown I/O mode: {task.io.mode}"}]
        
        # Determine difficulty from task ID prefix
        difficulty = "medium"  # default
        if task.id.startswith("E"):
            difficulty = "easy"
        elif task.id.startswith("M"):
            difficulty = "medium"
        elif task.id.startswith("H"):
            difficulty = "hard"
        
        # Get max score for this task based on difficulty and config
        max_score = self.config.get_difficulty_weight(difficulty)
        
        # Calculate score: max_score * (passed / total)
        total_tests = len(task.tests)
        score = round(max_score * (passed_count / total_tests), 2) if total_tests > 0 else 0.0
        
        return {
            "passed": passed_count,
            "total": total_tests,
            "score": score,
            "max_score": max_score,
            "results": results
        }
    
    def _grade_stdin_stdout(
        self,
        task: Task,
        code_path: str,
        timeout_sec: float,
        memory_limit_mb: int,
        checker_func: Callable
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Grade a stdin/stdout mode task.
        
        Returns:
            Tuple of (passed_count, results_list)
        """
        results = []
        passed_count = 0
        
        for i, test_case in enumerate(task.tests, start=1):
            start_time = time.time()
            
            status, stdout, stderr = run_code_stdin_stdout(
                code_path,
                test_case.input or "",
                timeout_sec,
                memory_limit_mb
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Determine pass/fail
            is_correct = False
            result_status = status
            
            if status == "success":
                is_correct = checker_func(stdout, test_case.output)
                result_status = "passed" if is_correct else "failed"
                if is_correct:
                    passed_count += 1
            elif status == "timeout":
                result_status = "timeout"
            elif status == "memory_error":
                result_status = "memory_error"
            else:
                result_status = "runtime_error"
            
            # Store diagnostic info for debugging
            result_dict = {
                "test_num": i,
                "status": result_status,
                "elapsed_ms": elapsed_ms,
                "stderr": stderr if status != "success" else None
            }
            
            # Add student output and expected for failed tests (for debugging)
            if result_status == "failed":
                result_dict["student_output"] = stdout
                result_dict["expected_output"] = test_case.output
            
            results.append(result_dict)
        
        return passed_count, results
    
    def _grade_function(
        self,
        task: Task,
        code_path: str,
        timeout_sec: float,
        memory_limit_mb: int,
        checker_func: Callable
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Grade a function mode task.
        
        Returns:
            Tuple of (passed_count, results_list)
        """
        results = []
        passed_count = 0
        
        for i, test_case in enumerate(task.tests, start=1):
            start_time = time.time()
            
            status, return_value, error_msg = run_code_function(
                code_path,
                task.io.entrypoint,
                test_case.args or [],
                timeout_sec,
                memory_limit_mb
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Determine pass/fail
            is_correct = False
            result_status = status
            
            if status == "success":
                is_correct = checker_func(return_value, test_case.ret)
                result_status = "passed" if is_correct else "failed"
                if is_correct:
                    passed_count += 1
            elif status == "timeout":
                result_status = "timeout"
            elif status == "memory_error":
                result_status = "memory_error"
            elif status == "import_error":
                result_status = "import_error"
            else:
                result_status = "runtime_error"
            
            # Store diagnostic info for debugging
            result_dict = {
                "test_num": i,
                "status": result_status,
                "elapsed_ms": elapsed_ms,
                "error": error_msg if status != "success" else None
            }
            
            # Add student output and expected for failed tests (for debugging)
            if result_status == "failed":
                result_dict["student_output"] = return_value
                result_dict["expected_output"] = test_case.ret
                result_dict["function_args"] = test_case.args
            
            results.append(result_dict)
        
        return passed_count, results
    
    # ===== UTILITY METHODS =====
    
    def format_test_results(self, results: Dict[str, Any], show_details: bool = False) -> str:
        """
        Format test results for display to student.
        
        Args:
            results: Results dictionary from grade_submission
            show_details: If True, show error messages and output comparison for failed tests
        
        Returns:
            Formatted string for terminal display
        """
        lines = []
        lines.append(f"Running {results['total']} hidden tests...\n")
        
        for result in results['results']:
            test_num = result['test_num']
            status = result['status']
            elapsed_ms = result.get('elapsed_ms', 0)
            
            if status == "passed":
                lines.append(f"Test #{test_num:2d}:  PASSED ({elapsed_ms} ms)")
            elif status == "failed":
                lines.append(f"Test #{test_num:2d}:  FAILED (Wrong Answer)")
            elif status == "timeout":
                lines.append(f"Test #{test_num:2d}:  FAILED (Timeout)")
            elif status == "runtime_error":
                lines.append(f"Test #{test_num:2d}:  FAILED (Runtime Error)")
            elif status == "memory_error":
                lines.append(f"Test #{test_num:2d}:  FAILED (Memory Limit Exceeded)")
            elif status == "import_error":
                lines.append(f"Test #{test_num:2d}:  FAILED (Import Error)")
            else:
                lines.append(f"Test #{test_num:2d}:  FAILED ({status})")
            
            # Show error details for debugging (always show for runtime errors)
            if status != "passed" and show_details:
                stderr = result.get('stderr')
                error = result.get('error')
                
                if stderr and stderr.strip():
                    lines.append(f"         Error: {stderr.strip()[:200]}")
                if error and error.strip():
                    lines.append(f"         Details: {error.strip()[:200]}")
                
                # Show output comparison for failed tests
                if status == "failed":
                    student_out = result.get('student_output')
                    expected_out = result.get('expected_output')
                    func_args = result.get('function_args')
                    
                    if func_args is not None:
                        lines.append(f"         Args: {func_args}")
                    if student_out is not None:
                        lines.append(f"         Your output: {repr(student_out)[:100]}")
                    if expected_out is not None:
                        lines.append(f"         Expected: {repr(expected_out)[:100]}")
        
        lines.append(f"\nResult: {results['passed']} / {results['total']} tests passed.")
        lines.append("This is not your final score. Use 'submit qN' to record your result.")
        
        return "\n".join(lines)

