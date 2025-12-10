#!/usr/bin/env python3
"""
Teacher Config Helper Tool

Interactive tool to help teachers create and validate exam configuration files.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner.models import ExamConfig


def create_config_interactive():
    """Interactively create a configuration file."""
    print("="*60)
    print("EXAM CONFIGURATION CREATOR")
    print("="*60)
    print("\nThis tool will help you create an exam configuration file.\n")
    
    try:
        # Get total questions
        total_questions = int(input("Total number of questions per student: "))
        if total_questions <= 0:
            print("Error: Total questions must be positive.")
            return None
        
        print(f"\nNow specify how many of each difficulty (must sum to {total_questions}):")
        
        # Get difficulty counts
        easy_count = int(input("  Easy questions: "))
        medium_count = int(input("  Medium questions: "))
        hard_count = int(input("  Hard questions: "))
        
        # Validate sum
        if easy_count + medium_count + hard_count != total_questions:
            print(f"Error: {easy_count} + {medium_count} + {hard_count} = {easy_count + medium_count + hard_count}")
            print(f"       This doesn't equal {total_questions}!")
            return None
        
        print("\nNow specify the point value for each difficulty level:")
        
        # Get weights
        easy_weight = float(input("  Points for each Easy question: "))
        medium_weight = float(input("  Points for each Medium question: "))
        hard_weight = float(input("  Points for each Hard question: "))
        
        # Calculate max points
        calculated_max = (easy_count * easy_weight + 
                         medium_count * medium_weight + 
                         hard_count * hard_weight)
        
        print(f"\nCalculated maximum points: {calculated_max}")
        confirm = input("Is this correct? (y/n): ").strip().lower()
        
        if confirm != 'y':
            max_points = float(input("Enter the correct maximum points: "))
        else:
            max_points = calculated_max

        # Get exam time
        print("\nNow specify exam parameters:")
        exam_time_input = input("  Exam time limit in minutes (default: 180, -1 for unlimited): ").strip()
        if not exam_time_input:
            exam_time_minutes = 180
        else:
            exam_time_minutes = int(exam_time_input)

        if exam_time_minutes < -1:
            print("Error: Exam time must be -1 (unlimited) or positive.")
            return None
        elif exam_time_minutes == -1:
            print("  → Exam time set to unlimited")
        elif exam_time_minutes <= 0:
            print("Error: Exam time must be -1 (unlimited) or positive.")
            return None

        # Get work directory postfix
        work_dir_postfix = input("  Work directory postfix (default: TP_TEST): ").strip() or "TP_TEST"
        if not work_dir_postfix.strip():
            work_dir_postfix = "TP_TEST"

        # Create config
        config_dict = {
            "total_questions": total_questions,
            "easy_count": easy_count,
            "medium_count": medium_count,
            "hard_count": hard_count,
            "easy_weight": easy_weight,
            "medium_weight": medium_weight,
            "hard_weight": hard_weight,
            "max_points": max_points,
            "exam_time_minutes": exam_time_minutes,
            "work_dir_postfix": work_dir_postfix
        }
        
        return config_dict
    
    except ValueError as e:
        print(f"Error: Invalid input - {e}")
        return None
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return None


def validate_config_file(config_path: Path):
    """Validate an existing configuration file."""
    print("="*60)
    print("CONFIG VALIDATOR")
    print("="*60)
    print(f"\nValidating: {config_path}\n")
    
    if not config_path.exists():
        print(f"Error: File '{config_path}' not found.")
        return False
    
    try:
        # Load config
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create ExamConfig object
        config = ExamConfig.from_dict(data)
        
        # Display config
        print("Configuration:")
        print(f"  Total Questions: {config.total_questions}")
        print(f"  Easy:   {config.easy_count} × {config.easy_weight} pts = {config.easy_count * config.easy_weight} pts")
        print(f"  Medium: {config.medium_count} × {config.medium_weight} pts = {config.medium_count * config.medium_weight} pts")
        print(f"  Hard:   {config.hard_count} × {config.hard_weight} pts = {config.hard_count * config.hard_weight} pts")
        print(f"  Maximum Points: {config.max_points}")
        exam_time = getattr(config, 'exam_time_minutes', None)
        if exam_time == -1:
            print("  Exam Time: Unlimited")
        elif exam_time is not None:
            print(f"  Exam Time: {exam_time} minutes")
        else:
            print("  Exam Time: Not set")
        print(f"  Work Directory Postfix: {getattr(config, 'work_dir_postfix', 'Not set')}")
        print()
        
        # Validate
        is_valid, error_message = config.validate()
        
        if is_valid:
            print("✓ Configuration is VALID!")
            return True
        else:
            print(f"✗ Configuration is INVALID!")
            print(f"  Error: {error_message}")
            return False
    
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def show_examples():
    """Display example configurations."""
    print("="*60)
    print("EXAMPLE CONFIGURATIONS")
    print("="*60)
    
    examples = [
        {
            "name": "Standard (Default)",
            "config": {
                "total_questions": 3,
                "easy_count": 1,
                "medium_count": 1,
                "hard_count": 1,
                "easy_weight": 5.0,
                "medium_weight": 5.0,
                "hard_weight": 5.0,
                "max_points": 15.0,
                "exam_time_minutes": 180,
                "work_dir_postfix": "TP_EVAL"
            }
        },
        {
            "name": "Weighted by Difficulty",
            "config": {
                "total_questions": 3,
                "easy_count": 1,
                "medium_count": 1,
                "hard_count": 1,
                "easy_weight": 3.0,
                "medium_weight": 5.0,
                "hard_weight": 7.0,
                "max_points": 15.0,
                "exam_time_minutes": 180,
                "work_dir_postfix": "TP_TEST"
            }
        },
        {
            "name": "5 Questions, 20 Points",
            "config": {
                "total_questions": 5,
                "easy_count": 2,
                "medium_count": 2,
                "hard_count": 1,
                "easy_weight": 3.0,
                "medium_weight": 4.0,
                "hard_weight": 6.0,
                "max_points": 20.0,
                "exam_time_minutes": 180,
                "work_dir_postfix": "TP_EXAM"
            }
        },
        {
            "name": "All Equal Weights",
            "config": {
                "total_questions": 4,
                "easy_count": 1,
                "medium_count": 2,
                "hard_count": 1,
                "easy_weight": 4.0,
                "medium_weight": 4.0,
                "hard_weight": 4.0,
                "max_points": 16.0,
                "exam_time_minutes": 180,
                "work_dir_postfix": "TP_PROG"
            }
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['name']}")
        print(json.dumps(example['config'], indent=2))
    
    print()


def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("EXAM CONFIGURATION HELPER TOOL")
    print("="*60)
    print("\nOptions:")
    print("  1. Create new configuration")
    print("  2. Validate existing configuration")
    print("  3. Show example configurations")
    print("  4. Exit")
    print()
    
    try:
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == '1':
            print()
            config_dict = create_config_interactive()
            
            if config_dict:
                print("\n" + "="*60)
                print("Configuration created successfully!")
                print("="*60)
                print(json.dumps(config_dict, indent=2))
                print()
                
                save = input("Save to config.json? (y/n): ").strip().lower()
                if save == 'y':
                    # Determine save location (project root)
                    save_path = Path.cwd() / "config.json"
                    
                    if save_path.exists():
                        overwrite = input("File exists. Overwrite? (y/n): ").strip().lower()
                        if overwrite != 'y':
                            print("Cancelled.")
                            return 0
                    
                    with open(save_path, 'w', encoding='utf-8') as f:
                        json.dump(config_dict, f, indent=2)
                    
                    print(f"\n✓ Configuration saved to: {save_path}")
                    
                    # Validate the saved file
                    print()
                    validate_config_file(save_path)
        
        elif choice == '2':
            print()
            config_file = input("Enter config file path (default: config.json): ").strip()
            if not config_file:
                config_file = "config.json"
            
            validate_config_file(Path(config_file))
        
        elif choice == '3':
            print()
            show_examples()
        
        elif choice == '4':
            print("Goodbye!")
            return 0
        
        else:
            print("Invalid choice.")
            return 1
    
    except (KeyboardInterrupt, EOFError):
        print("\n\nExiting.")
        return 0
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

