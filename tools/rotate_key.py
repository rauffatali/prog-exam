#!/usr/bin/env python3
"""
rotate_key.py - Re-encrypt a question bank with a new key or password.

Usage with key files:
    python tools/rotate_key.py --in banks/bank_group1.enc --out banks/bank_group1.enc --old-key-file GROUP1.key --new-key-file GROUP1_NEW.key

Usage changing from key to password:
    python tools/rotate_key.py --in banks/bank_group1.enc --out banks/bank_group1.enc --old-key-file GROUP1.key --new-password

Usage changing from password to password:
    python tools/rotate_key.py --in banks/bank_group1.enc --out banks/bank_group1.enc --old-password --new-password
"""

import argparse
import getpass
import hashlib
import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

from utils import derive_key_from_password


def rotate_key(in_file: str, out_file: str, old_key_file: str = None, new_key_file: str = None,
               old_password: bool = False, new_password: bool = False) -> None:
    """Re-encrypt a bank with a new key or password."""
    try:
        # Read encrypted bank
        with open(in_file, 'rb') as f:
            encrypted_data = f.read()
        
        old_hash = hashlib.sha256(encrypted_data).hexdigest()
        print(f"[INPUT] {in_file}")
        print(f"  SHA256: {old_hash}")
        
        # === DECRYPT WITH OLD KEY/PASSWORD ===
        
        # Check if password-based (has SALT prefix)
        is_old_password_based = encrypted_data.startswith(b'SALT')
        
        if is_old_password_based:
            # Extract salt and actual encrypted data
            salt = encrypted_data[4:20]
            encrypted_data_only = encrypted_data[20:]
            
            if not old_password:
                print(f"[ERROR] Bank was encrypted with password. Use --old-password.", file=sys.stderr)
                sys.exit(1)
            
            password = getpass.getpass("Enter current password: ")
            old_key = derive_key_from_password(password, salt)
            print(f"[OK] Using old password")
        else:
            # Key file based
            if not old_key_file:
                print(f"[ERROR] Bank was encrypted with key file. Use --old-key-file.", file=sys.stderr)
                sys.exit(1)
            
            with open(old_key_file, 'rb') as f:
                old_key = f.read()
            encrypted_data_only = encrypted_data
            print(f"[OK] Using old key file")
        
        old_fernet = Fernet(old_key)
        
        # Decrypt
        try:
            plaintext = old_fernet.decrypt(encrypted_data_only)
            print(f"[OK] Decrypted successfully")
        except InvalidToken:
            print(f"[ERROR] Failed to decrypt: Invalid old key/password or corrupted file", file=sys.stderr)
            sys.exit(1)
        
        # === ENCRYPT WITH NEW KEY/PASSWORD ===
        
        new_salt = None
        
        if new_password:
            password = getpass.getpass("Enter new password: ")
            password_confirm = getpass.getpass("Confirm new password: ")
            
            if password != password_confirm:
                print("[ERROR] Passwords do not match", file=sys.stderr)
                sys.exit(1)
            
            if len(password) < 8:
                print("[ERROR] Password must be at least 8 characters", file=sys.stderr)
                sys.exit(1)
            
            new_salt = os.urandom(16)
            new_key = derive_key_from_password(password, new_salt)
            print(f"[OK] Using new password")
        else:
            if not new_key_file:
                print(f"[ERROR] Must specify --new-key-file or --new-password", file=sys.stderr)
                sys.exit(1)
            
            with open(new_key_file, 'rb') as f:
                new_key = f.read()
            print(f"[OK] Using new key file")
        
        new_fernet = Fernet(new_key)
        new_encrypted_data = new_fernet.encrypt(plaintext)
        
        # Prepend salt if password-based
        if new_salt:
            final_data = b'SALT' + new_salt + new_encrypted_data
        else:
            final_data = new_encrypted_data
        
        new_hash = hashlib.sha256(final_data).hexdigest()
        
        # Write re-encrypted bank
        Path(out_file).parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, 'wb') as f:
            f.write(final_data)
        
        print(f"\n[OK] Success: Bank re-encrypted")
        print(f"  Output: {out_file}")
        print(f"  Method: {'Password-based' if new_salt else 'Key file'}")
        print(f"  SHA256: {new_hash}")
        print(f"\n[!] IMPORTANT:")
        if old_key_file:
            print(f"  - Archive old key: {old_key_file}")
        if new_key_file:
            print(f"  - Distribute new key: {new_key_file}")
        else:
            print(f"  - Remember your password - it cannot be recovered!")
        print(f"  - Update key/password storage/documentation")
        
    except FileNotFoundError as e:
        print(f"[ERROR] File not found: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error rotating key: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Re-encrypt a question bank with a new key.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Rotate key in-place
  python tools/rotate_key.py \\
    --in banks/bank_group1.enc \\
    --out banks/bank_group1.enc \\
    --old-key-file GROUP1.key \\
    --new-key-file GROUP1_NEW.key
  
  # Create new encrypted copy
  python tools/rotate_key.py \\
    --in banks/bank_group1.enc \\
    --out banks/bank_group1_v2.enc \\
    --old-key-file GROUP1.key \\
    --new-key-file GROUP1_V2.key

Security Notes:
  - Always generate a new key with keygen.py first
  - Archive old keys securely before rotating
  - Test decryption with new key before distributing
        """
    )
    parser.add_argument(
        "--in",
        dest="in_file",
        required=True,
        help="Input encrypted bank file"
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output encrypted bank file (can be same as input)"
    )
    parser.add_argument(
        "--old-key-file",
        help="File containing the current encryption key"
    )
    parser.add_argument(
        "--new-key-file",
        help="File containing the new encryption key"
    )
    parser.add_argument(
        "--old-password",
        action="store_true",
        help="Current bank is encrypted with password"
    )
    parser.add_argument(
        "--new-password",
        action="store_true",
        help="Re-encrypt with password instead of key file"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.old_key_file and not args.old_password:
        print("[ERROR] Must specify either --old-key-file or --old-password", file=sys.stderr)
        sys.exit(1)
    
    if args.old_key_file and args.old_password:
        print("[ERROR] Cannot use both --old-key-file and --old-password", file=sys.stderr)
        sys.exit(1)
    
    if not args.new_key_file and not args.new_password:
        print("[ERROR] Must specify either --new-key-file or --new-password", file=sys.stderr)
        sys.exit(1)
    
    if args.new_key_file and args.new_password:
        print("[ERROR] Cannot use both --new-key-file and --new-password", file=sys.stderr)
        sys.exit(1)
    
    rotate_key(args.in_file, args.out, args.old_key_file, args.new_key_file,
               args.old_password, args.new_password)


if __name__ == "__main__":
    main()

