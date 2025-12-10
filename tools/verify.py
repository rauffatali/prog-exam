#!/usr/bin/env python3
"""
verify.py - Validate banks, configs, or bundles (.json or .enc)

Examples:
  # Plaintext bank
  python tools/verify.py --bank bank_group1.json

  # Encrypted bank (key file)
  python tools/verify.py --bank banks/bank_group1.enc --key-file GROUP1.key

  # Encrypted bank (password)
  python tools/verify.py --bank banks/bank_group1.enc --password

  # Config file
  python tools/verify.py --config config.json

  # Bundle (encrypted config+bank)
  python tools/verify.py --bundle banks/group1_bundle.enc --password
"""

import argparse
import getpass
import json
import sys
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

# Import shared helpers and models
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.utils import derive_key_from_password
from runner.models import ExamConfig

def _decrypt_if_needed(path: Path, key_file: str | None, use_password: bool):
    is_enc = path.suffix.lower() == ".enc"
    data = path.read_bytes()
    if not is_enc:
        return data

    is_password_based = data.startswith(b"SALT")
    if is_password_based:
        if not use_password:
            raise ValueError("This file was encrypted with a password. Use --password.")
        salt = data[4:20]
        encrypted = data[20:]
        password = getpass.getpass("Enter decryption password: ")
        key = derive_key_from_password(password, salt)
    else:
        if not key_file:
            raise ValueError("This file was encrypted with a key file. Use --key-file.")
        key = Path(key_file).read_bytes()
        encrypted = data

    try:
        return Fernet(key).decrypt(encrypted)
    except InvalidToken as e:
        raise ValueError("Decryption failed: invalid key/password or corrupted file") from e

def _verify_config(config_bytes: bytes) -> bool:
    try:
        cfg_dict = json.loads(config_bytes)
        cfg = ExamConfig.from_dict(cfg_dict)
        is_valid, err = cfg.validate()
        if not is_valid:
            print(f"[ERROR] Config invalid: {err}")
            return False
        print("[OK] Config validation passed")
        print(f"  Questions: {cfg.total_questions} ({cfg.easy_count}E/{cfg.medium_count}M/{cfg.hard_count}H)")
        print(f"  Max points: {cfg.max_points}")
        print(f"  Time limit: {'unlimited' if cfg.exam_time_minutes == -1 else cfg.exam_time_minutes} minutes")
        print(f"  Work dir postfix: {cfg.work_dir_postfix}")
        return True
    except Exception as e:
        print(f"[ERROR] Config validation failed: {e}")
        return False

def _verify_bank(bank_bytes: bytes, verbose: bool) -> bool:
    try:
        bank_data = json.loads(bank_bytes)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON: {e}")
        return False

    # Existing schema checks (kept from verify_bank.py)
    errors, warnings = [], []
    required_top = ["group", "version", "difficulties"]
    for field in required_top:
        if field not in bank_data:
            errors.append(f"Missing required field: {field}")

    if errors:
        for err in errors:
            print(f"[ERROR] {err}")
        return False

    difficulties = bank_data.get("difficulties", {})
    required_difficulties = ["easy", "medium", "hard"]
    for diff in required_difficulties:
        if diff not in difficulties:
            errors.append(f"Missing difficulty level: {diff}")

    total_tasks = 0
    total_tests = 0
    for difficulty in required_difficulties:
        tasks = difficulties.get(difficulty, [])
        print(f"\n[TASKS] {difficulty.upper()} ({len(tasks)} tasks)")
        if not isinstance(tasks, list):
            errors.append(f"{difficulty}: must be a list")
            continue
        for idx, task in enumerate(tasks, 1):
            total_tasks += 1
            required_task_fields = ["id", "title", "prompt", "io", "tests", "time_limit_ms", "memory_limit_mb"]
            missing = [f for f in required_task_fields if f not in task]
            if missing:
                errors.append(f"{difficulty}[{idx}]: Missing fields: {', '.join(missing)}")
                continue
            io = task.get("io", {})
            if "mode" not in io:
                errors.append(f"{difficulty}[{idx}] ({task.get('id', '?')}): Missing io.mode")
            elif io["mode"] not in ["stdin_stdout", "function"]:
                errors.append(f"{difficulty}[{idx}] ({task.get('id', '?')}): Invalid io.mode: {io['mode']}")
            if io.get("mode") == "function" and "entrypoint" not in io:
                errors.append(f"{difficulty}[{idx}] ({task.get('id', '?')}): Function mode requires io.entrypoint")

            tests = task.get("tests", [])
            if not isinstance(tests, list):
                errors.append(f"{difficulty}[{idx}] ({task.get('id', '?')}): tests must be a list")
            elif len(tests) == 0:
                errors.append(f"{difficulty}[{idx}] ({task.get('id', '?')}): No test cases defined")
            else:
                total_tests += len(tests)
                if len(tests) != 15:
                    warnings.append(f"{difficulty}[{idx}] ({task.get('id', '?')}): Expected 15 tests, found {len(tests)}")

            if task.get("time_limit_ms", 0) <= 0:
                warnings.append(f"{difficulty}[{idx}] ({task.get('id', '?')}): time_limit_ms should be > 0")
            if task.get("memory_limit_mb", 0) <= 0:
                warnings.append(f"{difficulty}[{idx}] ({task.get('id', '?')}): memory_limit_mb should be > 0")
            if verbose:
                print(f"  [OK] {task.get('id', '?')}: {task.get('title', '?')} ({len(tests)} tests)")

    print(f"\n{'='*60}")
    print(f"[SUMMARY]")
    print(f"  Total tasks: {total_tasks}")
    print(f"  Total test cases: {total_tests}")

    if warnings:
        print(f"\n[WARNING] ({len(warnings)}):")
        for warn in warnings[:10]:
            print(f"  - {warn}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more")

    if errors:
        print(f"\n[ERROR] ({len(errors)}):")
        for err in errors[:20]:
            print(f"  - {err}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
        return False

    print(f"\n[OK] Bank validation PASSED")
    return True

def _verify_bundle(bundle_bytes: bytes, verbose: bool) -> bool:
    try:
        bundle = json.loads(bundle_bytes)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in bundle: {e}")
        return False

    if not isinstance(bundle, dict) or "config" not in bundle or "bank" not in bundle:
        print("[ERROR] Bundle must contain 'config' and 'bank' keys")
        return False

    print("\n[Bundle] Validating config...")
    ok_cfg = _verify_config(json.dumps(bundle["config"]).encode())
    print("\n[Bundle] Validating bank...")
    ok_bank = _verify_bank(json.dumps(bundle["bank"]).encode(), verbose)
    return ok_cfg and ok_bank

def main():
    parser = argparse.ArgumentParser(description="Verify bank, config, or bundle (.json or .enc).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--bank", help="Path to bank file (.json or .enc)")
    group.add_argument("--config", help="Path to config file (.json)")
    group.add_argument("--bundle", help="Path to bundle file (.json or .enc)")
    parser.add_argument("--key-file", help="Encryption key file (for key-file encrypted .enc files)")
    parser.add_argument("--password", action="store_true", help="Use password to decrypt (for password-encrypted .enc files)")
    parser.add_argument("--verbose", action="store_true", help="Show detailed task info (banks only)")
    args = parser.parse_args()

    target = args.bank or args.config or args.bundle
    path = Path(target)

    try:
        if args.bank:
            plaintext = _decrypt_if_needed(path, args.key_file, args.password)
            ok = _verify_bank(plaintext, args.verbose)
        elif args.config:
            plaintext = _decrypt_if_needed(path, args.key_file, args.password) if path.suffix == ".enc" else path.read_bytes()
            ok = _verify_config(plaintext)
        else:  # bundle
            plaintext = _decrypt_if_needed(path, args.key_file, args.password)
            ok = _verify_bundle(plaintext, args.verbose)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()