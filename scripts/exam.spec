# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Offline Python Exam System
# 
# Usage:
#   pyinstaller scripts/exam.spec
#
# This spec file creates a single-file executable that bundles:
# - The entire runner package (exam.py, grader.py, sandbox.py, models.py)
# - The cryptography library and its dependencies
# - A minimal Python interpreter
#
# Note: The encrypted banks/ directory must be distributed separately
# alongside the executable.

import sys
import os
from pathlib import Path

block_cipher = None

# Determine if we're on Windows for executable naming
IS_WINDOWS = sys.platform.startswith('win')
EXE_NAME = 'exam.exe' if IS_WINDOWS else 'exam'

# Path resolution: spec file is in scripts/, project root is parent
SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
PROJECT_ROOT = os.path.dirname(SPEC_DIR)

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'main.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        # Include the entire runner package
        (os.path.join(PROJECT_ROOT, 'runner/__init__.py'), 'runner'),
        (os.path.join(PROJECT_ROOT, 'runner/exam.py'), 'runner'),
        (os.path.join(PROJECT_ROOT, 'runner/models.py'), 'runner'),
        (os.path.join(PROJECT_ROOT, 'runner/grader.py'), 'runner'),
        (os.path.join(PROJECT_ROOT, 'runner/sandbox.py'), 'runner'),
    ],
    hiddenimports=[
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.backends',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Use UPX compression if available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # CLI application, needs console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

