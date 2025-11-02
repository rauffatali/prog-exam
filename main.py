#!/usr/bin/env python3
"""
Entry point wrapper for PyInstaller packaging.

This wrapper avoids relative import issues by using absolute imports.
When PyInstaller creates the executable, this will be the main entry point.
"""

import sys
import os

# Ensure the runner package can be imported
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    bundle_dir = sys._MEIPASS
else:
    # Running as script
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

# Add bundle directory to path
sys.path.insert(0, bundle_dir)

# Import and run the exam module
if __name__ == "__main__":
    from runner.exam import main
    sys.exit(main())

