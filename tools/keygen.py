#!/usr/bin/env python3
"""
keygen.py - Generate Fernet encryption keys for question banks.

Usage:
    python tools/keygen.py --out GROUP1.key
    python tools/keygen.py --out GROUP2.key
    
Note: You can also use passwords directly with build_bank.py --password
      instead of generating key files.
"""

import argparse
import sys
from cryptography.fernet import Fernet


def generate_key(output_file: str) -> None:
    """Generate a new Fernet key and save it to file."""
    try:
        key = Fernet.generate_key()
        
        with open(output_file, 'wb') as f:
            f.write(key)
        
        print(f"[OK] Success: Encryption key generated")
        print(f"  Output: {output_file}")
        print(f"  Key (base64): {key.decode('utf-8')}")
        print(f"\n[!] SECURITY: Store this key securely. Never commit to version control.")
        print(f"\n[i] Alternative: You can use --password flag in build_bank.py")
        print(f"    to encrypt with a password instead of a key file.")
        
    except Exception as e:
        print(f"[ERROR] Error generating key: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a new Fernet encryption key for question banks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/keygen.py --out GROUP1.key
  python tools/keygen.py --out GROUP2.key

Security Notes:
  - Store keys in a secure password manager
  - Never distribute keys with encrypted banks
  - Rotate keys after each exam session
        """
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output file path for the key (e.g., GROUP1.key)"
    )
    
    args = parser.parse_args()
    generate_key(args.out)


if __name__ == "__main__":
    main()

