#!/usr/bin/env python3
"""
Test script for ai_detector.py - Run parts incrementally to debug.
"""

import sys
import os
import platform

# Add the workspace root to path (parent of runner/ and tests/)
workspace_root = os.path.dirname(os.path.dirname(__file__))  # Go up from tests/ to workspace root
sys.path.insert(0, workspace_root)

from runner.ai_detector import AIDetector

def test_basic_initialization():
    """Test 1: Basic class initialization."""
    print("=== Test 1: Basic Initialization ===")
    try:
        detector = AIDetector()
        print("✓ AIDetector initialized successfully")
        print(f"✓ System: {platform.system()}")
        print(f"✓ AI processes defined for: {list(detector.ai_processes.keys())}")
        print(f"✓ AI extensions metadata: {len(detector.ai_extension_meta)} extensions")
        return detector
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        return None

def test_process_check(detector):
    """Test 2: Process detection."""
    print("\n=== Test 2: Process Detection ===")
    if not detector:
        return
    
    try:
        system = platform.system().lower()
        ai_processes = detector.ai_processes.get(system, []) + detector.llm_processes.get(system, [])
        if system == "windows":
            processes = detector._check_processes_windows(ai_processes)
        else:
            processes = detector._check_processes_unix(ai_processes)
        
        print(f"✓ Process check completed. Found: {processes}")
        return processes
    except Exception as e:
        print(f"✗ Process check failed: {e}")
        return []

def test_extension_installation(detector):
    """Test 3: Extension installation detection."""
    print("\n=== Test 3: Extension Installation ===")
    if not detector:
        return
    
    try:
        system = platform.system().lower()
        extensions = detector._check_vscode_extensions(system)
        print(f"✓ Extension check completed. Installed AI extensions: {extensions}")
        return extensions
    except Exception as e:
        print(f"✗ Extension check failed: {e}")
        return []

def test_extension_enablement(detector, extensions):
    """Test 4: Extension enablement check."""
    print("\n=== Test 4: Extension Enablement ===")
    if not detector or not extensions:
        print("✗ No extensions to check")
        return
    
    try:
        system = platform.system().lower()
        for ext in extensions:
            enabled, details = detector._check_vscode_extension_enabled(ext, system)
            status = "ENABLED" if enabled else "DISABLED"
            print(f"✓ {ext}: {status} ({details})")
    except Exception as e:
        print(f"✗ Enablement check failed: {e}")

def test_ide_ai_tools(detector):
    """Test 5: Full IDE AI tools check."""
    print("\n=== Test 5: Full IDE AI Tools Check ===")
    if not detector:
        return
    
    try:
        detected, tools = detector.check_ide_ai_tools()
        print(f"✓ IDE check completed. AI detected: {detected}")
        if tools:
            print("Detected tools:")
            for tool in tools:
                print(f"  - {tool}")
        return detected, tools
    except Exception as e:
        print(f"✗ IDE check failed: {e}")
        return False, []

def test_clipboard(detector):
    """Test 6: Clipboard activity check."""
    print("\n=== Test 6: Clipboard Check ===")
    if not detector:
        return
    
    try:
        content = detector._get_clipboard_content()
        if content:
            print(f"✓ Clipboard content retrieved ({len(content)} chars)")
            print(f"Preview: {content[:100]}...")
            
            is_suspicious = detector._is_suspicious_paste(content)
            print(f"Suspicious paste: {is_suspicious}")
        else:
            print("✓ No clipboard content or not accessible")
    except Exception as e:
        print(f"✗ Clipboard check failed: {e}")

def main():
    """Run all tests in sequence."""
    print("AI Detector Test Suite")
    print("=" * 50)
    
    # Run tests step by step
    detector = test_basic_initialization()
    
    if detector:
        test_process_check(detector)
        extensions = test_extension_installation(detector)
        test_extension_enablement(detector, extensions)
        test_ide_ai_tools(detector)
        test_clipboard(detector)
    
    print("\n" + "=" * 50)
    print("Test suite completed.")

if __name__ == "__main__":
    main()