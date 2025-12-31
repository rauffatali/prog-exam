"""
Configuration loader for teacher-defined exam parameters.

Handles loading and validating exam configuration files.
"""

import json
import sys
from pathlib import Path
from typing import Optional

from .models import ExamConfig


def load_config(config_path: Optional[Path] = None) -> ExamConfig:
    """
    Load exam configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file. If None, looks for
                    'config.json' next to the executable/script.
    
    Returns:
        ExamConfig object with validated configuration
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    if config_path is None:
        if getattr(sys, 'frozen', False):
            exe_dir = Path(sys.executable).parent
        else:
            exe_dir = Path(__file__).parent.parent
        
        config_path = exe_dir / "config.json"
    
    if not config_path.exists():
        print(f"Warning: Config file '{config_path}' not found. Using default configuration.")
        return ExamConfig.default()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")
    except Exception as e:
        raise ValueError(f"Error reading config file: {e}")

    config = ExamConfig.from_dict(data)
    
    is_valid, error_message = config.validate()
    if not is_valid:
        raise ValueError(f"Invalid configuration: {error_message}")
    
    return config


def create_sample_config(output_path: Path):
    """
    Create a sample configuration file for teachers.
    
    Args:
        output_path: Path where to save the sample config
    """
    sample_config = {
        "total_questions": 3,
        "easy_count": 1,
        "medium_count": 1,
        "hard_count": 1,
        "easy_weight": 5.0,
        "medium_weight": 5.0,
        "hard_weight": 5.0,
        "max_points": 15.0,
        "exam_time_minutes": 180,
        "work_dir_postfix": "TP_EVAL",
        "_comment": "This is a sample exam configuration. Adjust values as needed.",
        "_instructions": {
            "total_questions": "Total number of questions per student",
            "easy_count": "Number of easy difficulty questions",
            "medium_count": "Number of medium difficulty questions",
            "hard_count": "Number of hard difficulty questions",
            "easy_weight": "Points awarded for each easy question",
            "medium_weight": "Points awarded for each medium question",
            "hard_weight": "Points awarded for each hard question",
            "max_points": "Maximum total points (should equal sum of all weights)",
            "exam_time_minutes": "Total time allowed for the exam in minutes",
            "work_dir_postfix": "Postfix for the student's working directoriy (e.g., name_surname_POSTFIX)"
        },
        "_examples": [
            {
                "description": "Standard exam: 3 questions, equal weights",
                "total_questions": 3,
                "easy_count": 1,
                "medium_count": 1,
                "hard_count": 1,
                "easy_weight": 5.0,
                "medium_weight": 5.0,
                "hard_weight": 5.0,
                "max_points": 15.0,
                "exam_time_minutes": 120,
                "work_dir_postfix": "TP_EVAL"
            },
            {
                "description": "Weighted exam: harder questions worth more",
                "total_questions": 3,
                "easy_count": 1,
                "medium_count": 1,
                "hard_count": 1,
                "easy_weight": 3.0,
                "medium_weight": 5.0,
                "hard_weight": 7.0,
                "max_points": 15.0,
                "exam_time_minutes": 90,
                "work_dir_postfix": "TP_EXAM"
            },
            {
                "description": "5-question exam with 20 total points",
                "total_questions": 5,
                "easy_count": 2,
                "medium_count": 2,
                "hard_count": 1,
                "easy_weight": 3.0,
                "medium_weight": 4.0,
                "hard_weight": 6.0,
                "max_points": 20.0,
                "exam_time_minutes": 150,
                "work_dir_postfix": "TP_TEST"
            }
        ]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, indent=2)
    
    print(f"Sample configuration created at: {output_path}")

