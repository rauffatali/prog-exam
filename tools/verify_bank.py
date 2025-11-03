#!/usr/bin/env python3
"""
verify_bank.py - Validate question bank schema and decrypt for inspection.

Usage with key file:
    python tools/verify_bank.py --bank banks/bank_group1.enc --key-file GROUP1.key

Usage with password:
    python tools/verify_bank.py --bank banks/bank_group1.enc --password

Usage with plaintext:
    python tools/verify_bank.py --bank bank_group1.json
"""

import argparse
import getpass
import json
import sys
from cryptography.fernet import Fernet, InvalidToken

from utils import derive_key_from_password


def verify_bank(bank_file: str, key_file: str = None, use_password: bool = False, verbose: bool = False) -> bool:
    """
    Verify a question bank (encrypted or plaintext).
    Returns True if valid, False otherwise.
    """
    try:
        # Determine if encrypted or plaintext
        is_encrypted = bank_file.endswith('.enc')
        
        if is_encrypted:
            if not key_file and not use_password:
                print("[ERROR] Encrypted bank requires --key-file or --password", file=sys.stderr)
                return False
            
            # Read encrypted data
            with open(bank_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Check if password-based (has SALT prefix)
            is_password_based = encrypted_data.startswith(b'SALT')
            
            if is_password_based:
                # Extract salt and actual encrypted data
                salt = encrypted_data[4:20]  # 4-byte prefix + 16-byte salt
                encrypted_data = encrypted_data[20:]
                
                if not use_password:
                    print("[ERROR] This bank was encrypted with a password. Use --password flag.", file=sys.stderr)
                    return False
                
                password = getpass.getpass("Enter decryption password: ")
                key = derive_key_from_password(password, salt)
                print(f"[OK] Using password-based decryption")
            else:
                # Key file based
                if not key_file:
                    print("[ERROR] This bank was encrypted with a key file. Use --key-file.", file=sys.stderr)
                    return False
                
                with open(key_file, 'rb') as f:
                    key = f.read()
                print(f"[OK] Using key file decryption")
            
            fernet = Fernet(key)
            
            try:
                plaintext = fernet.decrypt(encrypted_data)
                print(f"[OK] Bank decrypted successfully")
            except InvalidToken:
                print(f"[ERROR] Decryption failed: Invalid key/password or corrupted file", file=sys.stderr)
                return False
        else:
            # Read plaintext
            with open(bank_file, 'rb') as f:
                plaintext = f.read()
        
        # Parse JSON
        try:
            bank_data = json.loads(plaintext)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON: {e}", file=sys.stderr)
            return False
        
        # Schema validation
        print(f"\n[SCHEMA] Bank Schema Validation")
        print(f"{'='*60}")
        
        errors = []
        warnings = []
        
        # Top-level structure
        required_top = ['group', 'version', 'difficulties']
        for field in required_top:
            if field not in bank_data:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            for err in errors:
                print(f"[ERROR] {err}")
            return False
        
        print(f"[OK] Group: {bank_data['group']}")
        print(f"[OK] Version: {bank_data['version']}")
        
        # Difficulties structure
        difficulties = bank_data.get('difficulties', {})
        required_difficulties = ['easy', 'medium', 'hard']
        
        for diff in required_difficulties:
            if diff not in difficulties:
                errors.append(f"Missing difficulty level: {diff}")
        
        if errors:
            for err in errors:
                print(f"[ERROR] {err}")
            return False
        
        # Validate each difficulty level
        total_tasks = 0
        total_tests = 0
        
        for difficulty in required_difficulties:
            tasks = difficulties[difficulty]
            print(f"\n[TASKS] {difficulty.upper()} ({len(tasks)} tasks)")
            
            if not isinstance(tasks, list):
                errors.append(f"{difficulty}: must be a list")
                continue
            
            for idx, task in enumerate(tasks):
                task_num = idx + 1
                total_tasks += 1
                
                # Required task fields
                required_task_fields = ['id', 'title', 'prompt', 'io', 'tests', 'time_limit_ms', 'memory_limit_mb']
                missing = [f for f in required_task_fields if f not in task]
                
                if missing:
                    errors.append(f"{difficulty}[{task_num}]: Missing fields: {', '.join(missing)}")
                    continue
                
                # Validate IO structure
                io = task.get('io', {})
                if 'mode' not in io:
                    errors.append(f"{difficulty}[{task_num}] ({task.get('id', '?')}): Missing io.mode")
                elif io['mode'] not in ['stdin_stdout', 'function']:
                    errors.append(f"{difficulty}[{task_num}] ({task.get('id', '?')}): Invalid io.mode: {io['mode']}")
                
                if io.get('mode') == 'function' and 'entrypoint' not in io:
                    errors.append(f"{difficulty}[{task_num}] ({task.get('id', '?')}): Function mode requires io.entrypoint")
                
                # Validate tests
                tests = task.get('tests', [])
                if not isinstance(tests, list):
                    errors.append(f"{difficulty}[{task_num}] ({task.get('id', '?')}): tests must be a list")
                elif len(tests) == 0:
                    errors.append(f"{difficulty}[{task_num}] ({task.get('id', '?')}): No test cases defined")
                else:
                    total_tests += len(tests)
                    
                    # Validate test structure
                    for test_idx, test in enumerate(tests):
                        if io.get('mode') == 'stdin_stdout':
                            if 'input' not in test or 'output' not in test:
                                errors.append(f"{difficulty}[{task_num}] ({task.get('id', '?')}) test {test_idx+1}: Missing input/output")
                        elif io.get('mode') == 'function':
                            if 'args' not in test or 'ret' not in test:
                                errors.append(f"{difficulty}[{task_num}] ({task.get('id', '?')}) test {test_idx+1}: Missing args/ret")
                    
                    if len(tests) != 15:
                        warnings.append(f"{difficulty}[{task_num}] ({task.get('id', '?')}): Expected 15 tests, found {len(tests)}")
                
                # Validate limits
                if task.get('time_limit_ms', 0) <= 0:
                    warnings.append(f"{difficulty}[{task_num}] ({task.get('id', '?')}): time_limit_ms should be > 0")
                
                if task.get('memory_limit_mb', 0) <= 0:
                    warnings.append(f"{difficulty}[{task_num}] ({task.get('id', '?')}): memory_limit_mb should be > 0")
                
                if verbose:
                    print(f"  [OK] {task.get('id', '?')}: {task.get('title', '?')} ({len(tests)} tests)")
        
        # Summary
        print(f"\n{'='*60}")
        print(f"[SUMMARY]")
        print(f"  Total tasks: {total_tasks}")
        print(f"  Total test cases: {total_tests}")
        
        if warnings:
            print(f"\n[WARNING] ({len(warnings)}):")
            for warn in warnings[:10]:  # Limit output
                print(f"  - {warn}")
            if len(warnings) > 10:
                print(f"  ... and {len(warnings) - 10} more")
        
        if errors:
            print(f"\n[ERROR] ({len(errors)}):")
            for err in errors[:20]:  # Limit output
                print(f"  - {err}")
            if len(errors) > 20:
                print(f"  ... and {len(errors) - 20} more")
            return False
        
        print(f"\n[OK] Bank validation PASSED")
        return True
        
    except FileNotFoundError as e:
        print(f"[ERROR] File not found: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Validate question bank schema and content.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify encrypted bank
  python tools/verify_bank.py --bank banks/bank_group1.enc --key-file GROUP1.key
  
  # Verify plaintext bank (during authoring)
  python tools/verify_bank.py --bank bank_group1.json
  
  # Verbose output
  python tools/verify_bank.py --bank bank_group1.json --verbose
        """
    )
    parser.add_argument(
        "--bank",
        required=True,
        help="Path to bank file (.enc or .json)"
    )
    parser.add_argument(
        "--key-file",
        help="Encryption key file (for key-file encrypted banks)"
    )
    parser.add_argument(
        "--password",
        action="store_true",
        help="Use password to decrypt (for password-encrypted banks)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed task information"
    )
    
    args = parser.parse_args()
    
    success = verify_bank(args.bank, args.key_file, args.password, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

