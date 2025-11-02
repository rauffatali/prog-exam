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
class Bank:
    """Represents the entire question bank."""
    group: str
    version: str
    easy: List[Task]
    medium: List[Task]
    hard: List[Task]

    @staticmethod
    def from_dict(data: dict) -> 'Bank':
        """Create a Bank object from a dictionary."""
        difficulties = data['difficulties']
        
        return Bank(
            group=data['group'],
            version=data['version'],
            easy=[Task.from_dict(t) for t in difficulties['easy']],
            medium=[Task.from_dict(t) for t in difficulties['medium']],
            hard=[Task.from_dict(t) for t in difficulties['hard']]
        )
    
    def get_all_tasks(self) -> Dict[str, Task]:
        """Return a dictionary mapping task IDs to Task objects."""
        tasks = {}
        for task in self.easy + self.medium + self.hard:
            tasks[task.id] = task
        return tasks


