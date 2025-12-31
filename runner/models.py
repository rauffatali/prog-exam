"""
Data models for the Question Bank schema.

Provides type-safe structures for Task, TestCase, and Bank objects.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class IOConfig:
    """I/O mode configuration for a task."""
    mode: str  # "stdin_stdout" or "function"
    entrypoint: Optional[str]  # Function name for function mode, null for stdin_stdout


@dataclass
class TestCase:
    """Represents a single test case for a task."""
    # For stdin_stdout mode
    input: Optional[str] = None
    output: Optional[str] = None
    
    # For function mode
    args: Optional[List[Any]] = None
    ret: Optional[Any] = None


@dataclass
class VisibleSample:
    """Optional sample input/output shown to students."""
    input: Optional[str] = None
    output: Optional[str] = None
    args: Optional[List[Any]] = None
    ret: Optional[Any] = None


@dataclass
class Task:
    """Represents a programming task/question."""
    id: str
    title: str
    prompt: str
    io: IOConfig
    tests: List[TestCase]
    time_limit_ms: int
    memory_limit_mb: int
    checker: str
    hints: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    visible_sample: Optional[VisibleSample] = None

    @staticmethod
    def from_dict(data: dict) -> 'Task':
        """Create a Task object from a dictionary."""
        io_config = IOConfig(
            mode=data['io']['mode'],
            entrypoint=data['io'].get('entrypoint')
        )
        
        tests = []
        for test_data in data['tests']:
            if 'input' in test_data:
                tests.append(TestCase(
                    input=test_data['input'],
                    output=test_data['output']
                ))
            else:
                tests.append(TestCase(
                    args=test_data['args'],
                    ret=test_data['ret']
                ))
        
        visible_sample = None
        if data.get('visible_sample'):
            vs_data = data['visible_sample']
            visible_sample = VisibleSample(
                input=vs_data.get('input'),
                output=vs_data.get('output'),
                args=vs_data.get('args'),
                ret=vs_data.get('ret')
            )
        
        return Task(
            id=data['id'],
            title=data['title'],
            prompt=data['prompt'],
            io=io_config,
            tests=tests,
            time_limit_ms=data['time_limit_ms'],
            memory_limit_mb=data['memory_limit_mb'],
            checker=data.get('checker') or 'exact_match',
            hints=data.get('hints'),
            tags=data.get('tags'),
            visible_sample=visible_sample
        )


@dataclass
class NetworkMonitoringConfig:
    """Network monitoring settings from the bank."""
    enabled: bool
    check_interval_seconds: int
    
    @staticmethod
    def from_dict(data: dict) -> 'NetworkMonitoringConfig':
        """Create NetworkMonitoringConfig from dictionary."""
        return NetworkMonitoringConfig(
            enabled=data.get('enabled', False),
            check_interval_seconds=data.get('check_interval_seconds', 15)
        )
    
    @staticmethod
    def default() -> 'NetworkMonitoringConfig':
        """Return default config (monitoring disabled)."""
        return NetworkMonitoringConfig(enabled=False, check_interval_seconds=15)


@dataclass
class AIDetectionConfig:
    """AI detection settings from the bank."""
    enabled: bool
    check_interval_seconds: int
    
    @staticmethod
    def from_dict(data: dict) -> 'AIDetectionConfig':
        """Create AIDetectionConfig from dictionary."""
        return AIDetectionConfig(
            enabled=data.get('enabled', True),
            check_interval_seconds=data.get('check_interval_seconds', 60),
        )
    
    @staticmethod
    def default() -> 'AIDetectionConfig':
        """Return default config (detection enabled)."""
        return AIDetectionConfig(enabled=True, check_interval_seconds=60)


@dataclass
class Bank:
    """Represents the entire question bank."""
    group: str
    version: str
    easy: List[Task]
    medium: List[Task]
    hard: List[Task]
    network_monitoring: NetworkMonitoringConfig
    ai_detection: AIDetectionConfig

    @staticmethod
    def from_dict(data: dict) -> 'Bank':
        """Create a Bank object from a dictionary."""
        difficulties = data['difficulties']
        
        network_config = NetworkMonitoringConfig.default()
        if 'network_monitoring' in data:
            network_config = NetworkMonitoringConfig.from_dict(data['network_monitoring'])
        
        ai_config = AIDetectionConfig.default()
        if 'ai_detection' in data:
            ai_config = AIDetectionConfig.from_dict(data['ai_detection'])
        
        return Bank(
            group=data['group'],
            version=data['version'],
            easy=[Task.from_dict(t) for t in difficulties['easy']],
            medium=[Task.from_dict(t) for t in difficulties['medium']],
            hard=[Task.from_dict(t) for t in difficulties['hard']],
            network_monitoring=network_config,
            ai_detection=ai_config
        )
    
    def get_all_tasks(self) -> Dict[str, Task]:
        """Return a dictionary mapping task IDs to Task objects."""
        tasks = {}
        for task in self.easy + self.medium + self.hard:
            tasks[task.id] = task
        return tasks


@dataclass
class ExamConfig:
    """
    Configuration for exam parameters set by teacher.
    
    Attributes:
        total_questions: Total number of questions per student
        easy_count: Number of easy questions
        medium_count: Number of medium questions
        hard_count: Number of hard questions
        easy_weight: Point value for each easy question
        medium_weight: Point value for each medium question
        hard_weight: Point value for each hard question
        max_points: Maximum total points for the exam
    """
    total_questions: int
    easy_count: int
    medium_count: int
    hard_count: int
    easy_weight: float
    medium_weight: float
    hard_weight: float
    max_points: float
    exam_time_minutes: int
    work_dir_postfix: str
    
    @staticmethod
    def from_dict(data: dict) -> 'ExamConfig':
        """Create ExamConfig from dictionary."""
        return ExamConfig(
            total_questions=data.get('total_questions', 3),
            easy_count=data.get('easy_count', 1),
            medium_count=data.get('medium_count', 1),
            hard_count=data.get('hard_count', 1),
            easy_weight=float(data.get('easy_weight', 5.0)),
            medium_weight=float(data.get('medium_weight', 5.0)),
            hard_weight=float(data.get('hard_weight', 5.0)),
            max_points=float(data.get('max_points', 15.0)),
            exam_time_minutes=data.get('exam_time_minutes', 120),
            work_dir_postfix=data.get('work_dir_postfix', 'TP_EVAL')
        )
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate configuration consistency.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.easy_count + self.medium_count + self.hard_count != self.total_questions:
            return False, f"Question counts don't match: {self.easy_count} + {self.medium_count} + {self.hard_count} != {self.total_questions}"
        
        calculated_max = (self.easy_count * self.easy_weight + 
                         self.medium_count * self.medium_weight + 
                         self.hard_count * self.hard_weight)
        
        if abs(calculated_max - self.max_points) > 0.01:
            return False, f"Max points ({self.max_points}) doesn't match calculated sum ({calculated_max})"

        if any(x < 0 for x in [self.total_questions, self.easy_count, self.medium_count, 
                                self.hard_count, self.easy_weight, self.medium_weight, 
                                self.hard_weight, self.max_points]):
            return False, "All values must be non-negative"
        
        if self.exam_time_minutes != -1 and (self.exam_time_minutes < 1 or self.exam_time_minutes > 480):
            return False, "Exam time must be between 1 and 480 minutes (8 hours)"
        
        return True, ""
    
    def get_difficulty_weight(self, difficulty: str) -> float:
        """Get the point value for a difficulty level."""
        if difficulty.lower() == 'easy':
            return self.easy_weight
        elif difficulty.lower() == 'medium':
            return self.medium_weight
        elif difficulty.lower() == 'hard':
            return self.hard_weight
        return 0.0
    
    @staticmethod
    def default() -> 'ExamConfig':
        """Return default configuration (backward compatible with current system)."""
        return ExamConfig(
            total_questions=3,
            easy_count=1,
            medium_count=1,
            hard_count=1,
            easy_weight=5.0,
            medium_weight=5.0,
            hard_weight=5.0,
            max_points=15.0,
            exam_time_minutes=120,
            work_dir_postfix='TP_EVAL'
        )


