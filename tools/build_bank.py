#!/usr/bin/env python3
"""
build_bank.py - Encrypt plaintext JSON question banks.

Usage with key file:
    python tools/build_bank.py --in bank_group1.json --out banks/bank_group1.enc --key-file GROUP1.key

Usage with password:
    python tools/build_bank.py --in bank_group1.json --out banks/bank_group1.enc --password
"""

import argparse
import getpass
import hashlib
import json
import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derive a Fernet key from a password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,  # OWASP recommendation for 2024
    )
    # Derive key and encode as Fernet key (base64url)
    key_material = kdf.derive(password.encode())
    return base64.urlsafe_b64encode(key_material)


def build_bank(in_file: str, out_file: str, key_file: str = None, use_password: bool = False) -> None:
    """Encrypt a plaintext JSON question bank."""
    try:
        salt = None
        
        # Get encryption key (either from file or password)
        if use_password:
            password = getpass.getpass("Enter encryption password: ")
            password_confirm = getpass.getpass("Confirm password: ")
            
            if password != password_confirm:
                print("[ERROR] Passwords do not match", file=sys.stderr)
                sys.exit(1)
            
            if len(password) < 8:
                print("[ERROR] Password must be at least 8 characters", file=sys.stderr)
                sys.exit(1)
            
            # Generate random salt for password-based encryption
            salt = os.urandom(16)
            key = derive_key_from_password(password, salt)
            print("[OK] Using password-based encryption")
            
        elif key_file:
            with open(key_file, 'rb') as f:
                key = f.read()
            print("[OK] Using key file encryption")
        else:
            print("[ERROR] Must specify either --key-file or --password", file=sys.stderr)
            sys.exit(1)
        
        fernet = Fernet(key)
        
        # Read and validate plaintext JSON
        with open(in_file, 'rb') as f:
            plaintext = f.read()
        
        # Verify JSON is valid before encrypting
        try:
            bank_data = json.loads(plaintext)
            print(f"[OK] Input JSON validated")
            print(f"  Group: {bank_data.get('group', 'unknown')}")
            print(f"  Version: {bank_data.get('version', 'unknown')}")
            
            difficulties = bank_data.get('difficulties', {})
            easy_count = len(difficulties.get('easy', []))
            medium_count = len(difficulties.get('medium', []))
            hard_count = len(difficulties.get('hard', []))
            print(f"  Tasks: {easy_count} easy, {medium_count} medium, {hard_count} hard")
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in input file: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Encrypt
        encrypted_data = fernet.encrypt(plaintext)
        
        # For password-based encryption, prepend salt to encrypted data
        if salt:
            final_data = b'SALT' + salt + encrypted_data
        else:
            final_data = encrypted_data
        
        # Compute checksum
        sha256_hash = hashlib.sha256(final_data).hexdigest()
        
        # Write encrypted bank
        Path(out_file).parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, 'wb') as f:
            f.write(final_data)
        
        print(f"\n[OK] Success: Bank encrypted")
        print(f"  Input: {in_file} ({len(plaintext)} bytes)")
        print(f"  Output: {out_file} ({len(final_data)} bytes)")
        print(f"  Method: {'Password-based' if salt else 'Key file'}")
        print(f"  SHA256: {sha256_hash}")
        
    except FileNotFoundError as e:
        print(f"[ERROR] File not found: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error encrypting bank: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Encrypt a plaintext JSON question bank.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/build_bank.py --in bank_group1.json --out banks/bank_group1.enc --key-file GROUP1.key
  python tools/build_bank.py --in bank_group2.json --out banks/bank_group2.enc --key-file GROUP2.key

Notes:
  - Input file must be valid JSON
  - Output directory will be created if it doesn't exist
  - Produces SHA256 checksum for verification
        """
    )
    parser.add_argument(
        "--in",
        dest="in_file",
        required=True,
        help="Input plaintext JSON file"
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output encrypted bank file (.enc)"
    )
    parser.add_argument(
        "--key-file",
        help="File containing the encryption key (mutually exclusive with --password)"
    )
    parser.add_argument(
        "--password",
        action="store_true",
        help="Use password-based encryption instead of key file"
    )
    
    args = parser.parse_args()
    
    # Validate that exactly one method is specified
    if args.password and args.key_file:
        print("[ERROR] Cannot use both --password and --key-file", file=sys.stderr)
        sys.exit(1)
    
    if not args.password and not args.key_file:
        print("[ERROR] Must specify either --password or --key-file", file=sys.stderr)
        sys.exit(1)
    
    build_bank(args.in_file, args.out, args.key_file, args.password)


if __name__ == "__main__":
    main()

