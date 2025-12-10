#!/usr/bin/env python3
"""
build_bundle.py - Encrypt config + bank together.
Usage (key file):
  python tools/build_bundle.py --config config.json --bank banks/group1.json --out banks/group1_bundle.enc --key-file GROUP1.key
Usage (password):
  python tools/build_bundle.py --config config.json --bank banks/group1.json --out banks/group1_bundle.enc --password
"""
import argparse, getpass, hashlib, json, os, sys
from pathlib import Path
from cryptography.fernet import Fernet
from utils import derive_key_from_password

def build_bundle(config_file, bank_file, out_file, key_file=None, use_password=False):
    salt = None
    if use_password:
        pw1 = getpass.getpass("Enter encryption password: ")
        pw2 = getpass.getpass("Confirm password: ")
        if pw1 != pw2:
            print("[ERROR] Passwords do not match", file=sys.stderr); sys.exit(1)
        if len(pw1) < 8:
            print("[ERROR] Password must be at least 8 characters", file=sys.stderr); sys.exit(1)
        salt = os.urandom(16)
        key = derive_key_from_password(pw1, salt)
        print("[OK] Using password-based encryption")
    elif key_file:
        with open(key_file, "rb") as f:
            key = f.read()
        print("[OK] Using key file encryption")
    else:
        print("[ERROR] Must specify either --key-file or --password", file=sys.stderr); sys.exit(1)

    with open(config_file, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    with open(bank_file, "r", encoding="utf-8") as f:
        bank_data = json.load(f)

    bundle = {"config": config_data, "bank": bank_data}
    plaintext = json.dumps(bundle, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    token = Fernet(key).encrypt(plaintext)
    final_data = b"SALT" + salt + token if salt else token

    sha256 = hashlib.sha256(final_data).hexdigest()
    Path(out_file).parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "wb") as f:
        f.write(final_data)

    print(f"[OK] Bundle encrypted -> {out_file}")
    print(f"  Bytes in/out: {len(plaintext)} -> {len(final_data)}")
    print(f"  SHA256: {sha256}")

def main():
    p = argparse.ArgumentParser(description="Encrypt config + bank together.")
    p.add_argument("--config", required=True, help="Path to config JSON")
    p.add_argument("--bank", required=True, help="Path to bank JSON")
    p.add_argument("--out", required=True, help="Output encrypted bundle (.enc)")
    p.add_argument("--key-file", help="Encryption key file (mutually exclusive with --password)")
    p.add_argument("--password", action="store_true", help="Use password-based encryption")
    args = p.parse_args()

    if args.password and args.key_file:
        print("[ERROR] Cannot use both --password and --key-file", file=sys.stderr); sys.exit(1)
    if not args.password and not args.key_file:
        print("[ERROR] Must specify either --password or --key-file", file=sys.stderr); sys.exit(1)

    build_bundle(args.config, args.bank, args.out, args.key_file, args.password)

if __name__ == "__main__":
    main()