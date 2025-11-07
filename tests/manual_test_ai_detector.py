"""
Manual Test Script for AI Detector Module

This script tests the ai_detector.py module by calling its functions
and printing the results to the screen.

Run this script with: python tests/manual_test_ai_detector.py
"""

import sys
from pathlib import Path
import time
import platform

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner.ai_detector import AIDetector, check_ai_tools_at_startup


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_test(test_name, passed, details=""):
    """Print test result."""
    status = "PASSED" if passed else "FAILED"
    print(f"\n[{status}] {test_name}")
    if details:
        print(f"  => {details}")


def test_initialization():
    """Test AIDetector initialization."""
    print_header("TEST 1: AIDetector Initialization")
    
    try:
        # Test without logger
        print("  Creating AIDetector without logger...")
        detector1 = AIDetector()
        print(f"  Created: {detector1}")
        print(f"  Session logger: {detector1.session_logger}")
        print(f"  Monitoring active: {detector1.monitoring_active}")
        
        # Test with logger
        print("\n  Creating AIDetector with mock logger...")
        def mock_logger(event, message):
            print(f"    [MOCK LOG] {event}: {message}")
        
        detector2 = AIDetector(session_logger=mock_logger)
        print(f"  Created: {detector2}")
        print(f"  Has logger: {detector2.session_logger is not None}")
        
        passed = (detector1.session_logger is None and 
                 detector2.session_logger is not None and
                 not detector1.monitoring_active)
        
        print_test("Initialization works correctly", passed,
                  "Both with and without logger")
        
        return passed
    except Exception as e:
        print_test("Initialization", False, f"Exception: {str(e)}")
        return False


def test_ai_processes_configuration():
    """Test that AI processes are properly configured."""
    print_header("TEST 2: AI Processes Configuration")
    
    try:
        detector = AIDetector()
        
        print("  Checking AI processes configuration...")
        print(f"  Platforms configured: {list(detector.ai_processes.keys())}")
        
        # Check each platform
        for platform_name, processes in detector.ai_processes.items():
            print(f"\n  {platform_name.upper()}:")
            print(f"    Total processes: {len(processes)}")
            print(f"    Examples: {', '.join(processes[:5])}")
        
        # Verify required platforms
        required_platforms = ['windows', 'linux', 'darwin']
        has_all_platforms = all(p in detector.ai_processes for p in required_platforms)
        
        # Verify common tools are listed
        common_tools = ['copilot', 'tabnine', 'cursor', 'codeium']
        windows_processes = [p.lower() for p in detector.ai_processes.get('windows', [])]
        has_common_tools = all(tool in windows_processes for tool in common_tools)
        
        passed = has_all_platforms and has_common_tools
        
        print_test("AI processes properly configured", passed,
                  f"Has all platforms and common tools")
        
        return passed
    except Exception as e:
        print_test("AI processes configuration", False, f"Exception: {str(e)}")
        return False


def test_ai_websites_configuration():
    """Test that AI websites are configured."""
    print_header("TEST 3: AI Websites Configuration")
    
    try:
        detector = AIDetector()
        
        print("  Checking AI websites configuration...")
        print(f"  Total websites monitored: {len(detector.ai_websites)}")
        print("\n  AI websites:")
        for i, website in enumerate(detector.ai_websites[:10], 1):
            print(f"    {i}. {website}")
        
        if len(detector.ai_websites) > 10:
            print(f"    ... and {len(detector.ai_websites) - 10} more")
        
        # Check for key websites
        key_websites = ['chat.openai.com', 'claude.ai', 'github.com/copilot']
        has_key_sites = all(site in detector.ai_websites for site in key_websites)
        
        passed = has_key_sites and len(detector.ai_websites) > 0
        
        print_test("AI websites properly configured", passed,
                  f"{len(detector.ai_websites)} websites configured")
        
        return passed
    except Exception as e:
        print_test("AI websites configuration", False, f"Exception: {str(e)}")
        return False


def test_suspicious_paste_detection():
    """Test clipboard paste detection logic."""
    print_header("TEST 4: Suspicious Paste Detection")
    
    try:
        detector = AIDetector()
        
        # Test 1: Small content (not suspicious)
        print("  Test 1: Small content")
        small_content = "hello world"
        result1 = detector._is_suspicious_paste(small_content)
        print(f"    Content: '{small_content}'")
        print(f"    Is suspicious: {result1}")
        print(f"    Expected: False")
        test1_passed = result1 == False
        
        # Test 2: Large code (suspicious)
        print("\n  Test 2: Large code content")
        large_code = """
def calculate_fibonacci(n):
    if n <= 1:
        return n
    else:
        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class MyClass:
    def __init__(self):
        self.value = 0
    
    def increment(self):
        self.value += 1
        return self.value

for i in range(10):
    print(calculate_fibonacci(i))
"""
        result2 = detector._is_suspicious_paste(large_code)
        print(f"    Content length: {len(large_code)} characters")
        print(f"    Is suspicious: {result2}")
        print(f"    Expected: True")
        test2_passed = result2 == True
        
        # Test 3: Large non-code (not suspicious)
        print("\n  Test 3: Large non-code content")
        large_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 30
        result3 = detector._is_suspicious_paste(large_text)
        print(f"    Content length: {len(large_text)} characters")
        print(f"    Is suspicious: {result3}")
        print(f"    Expected: False")
        test3_passed = result3 == False
        
        passed = test1_passed and test2_passed and test3_passed
        
        print_test("Suspicious paste detection works", passed,
                  "Correctly identifies code vs non-code")
        
        return passed
    except Exception as e:
        print_test("Suspicious paste detection", False, f"Exception: {str(e)}")
        return False


def test_process_detection():
    """Test process detection functionality."""
    print_header("TEST 5: Process Detection")
    
    try:
        detector = AIDetector()
        system = platform.system().lower()
        
        print(f"  Current system: {system}")
        print(f"  Running process detection for current platform...")
        
        if system == "windows":
            target_processes = detector.ai_processes.get('windows', [])[:5]
            print(f"  Testing with processes: {target_processes}")
            detected = detector._check_processes_windows(target_processes)
        else:
            target_processes = detector.ai_processes.get(system, [])[:5]
            print(f"  Testing with processes: {target_processes}")
            detected = detector._check_processes_unix(target_processes)
        
        print(f"\n  Detected AI processes: {detected if detected else 'None'}")
        print(f"  Result type: {type(detected)}")
        print(f"  Result is list: {isinstance(detected, list)}")
        
        # Test passes if returns a list (even if empty)
        passed = isinstance(detected, list)
        
        if detected:
            print("\n  ** WARNING: AI coding assistants detected on your system!")
            print(f"  Detected tools: {', '.join(detected)}")
        else:
            print("\n  [OK] No AI coding assistants detected")
        
        print_test("Process detection works", passed,
                  "Returns list of processes")
        
        return passed
    except Exception as e:
        print_test("Process detection", False, f"Exception: {str(e)}")
        return False


def test_background_monitoring():
    """Test background monitoring thread."""
    print_header("TEST 6: Background Monitoring Thread")
    
    try:
        def test_logger(event, message):
            print(f"    [LOG] {event}: {message}")
        
        detector = AIDetector(session_logger=test_logger)
        
        print("  Starting background monitoring...")
        detector.start_monitoring()
        
        print(f"  Monitoring active: {detector.monitoring_active}")
        print(f"  Thread alive: {detector.detection_thread.is_alive()}")
        
        # Let it run for a bit
        print("  Waiting 2 seconds...")
        time.sleep(2)
        
        print("  Stopping background monitoring...")
        detector.stop_monitoring()
        
        print(f"  Monitoring active: {detector.monitoring_active}")
        
        passed = not detector.monitoring_active
        
        print_test("Background monitoring works", passed,
                  "Can start and stop monitoring thread")
        
        return passed
    except Exception as e:
        print_test("Background monitoring", False, f"Exception: {str(e)}")
        return False


def test_ide_detection():
    """Test IDE AI tool detection."""
    print_header("TEST 7: IDE AI Tool Detection")
    
    try:
        detector = AIDetector()
        
        print("  Checking for VS Code extensions...")
        extensions = detector._check_vscode_extensions()
        
        print(f"  Extensions found: {len(extensions)}")
        if extensions:
            print("  Detected extensions:")
            for ext in extensions:
                print(f"    - {ext}")
        else:
            print("  No AI extensions detected in VS Code")
        
        # Check Copilot settings
        print("\n  Checking GitHub Copilot settings...")
        enabled, details = detector._check_vscode_copilot_enabled()
        print(f"  Copilot enabled: {enabled}")
        print(f"  Details: {details}")
        
        # Check IDE AI tools (comprehensive check)
        print("\n  Running comprehensive IDE check...")
        ide_detected, tools = detector.check_ide_ai_tools()
        print(f"  AI tools detected: {ide_detected}")
        if tools:
            print("  Detected tools:")
            for tool in tools:
                print(f"    - {tool}")
        
        # Test passes if functions run without error
        passed = isinstance(extensions, list) and isinstance(enabled, bool)
        
        print_test("IDE detection works", passed,
                  "Successfully scanned for IDE AI tools")
        
        return passed
    except Exception as e:
        print_test("IDE detection", False, f"Exception: {str(e)}")
        return False


def test_startup_check():
    """Test startup AI tools check."""
    print_header("TEST 8: Startup AI Tools Check")
    
    try:
        print("  Running startup check for AI tools...")
        detected, tools = check_ai_tools_at_startup()
        
        print(f"  AI tools detected: {detected}")
        print(f"  Result type: {type(detected)} (should be bool)")
        print(f"  Tools list type: {type(tools)} (should be list)")
        
        if detected:
            print(f"\n  ** Detected tools: {', '.join(tools)}")
        else:
            print("\n  [OK] No AI tools detected at startup")
        
        passed = isinstance(detected, bool) and isinstance(tools, list)
        
        print_test("Startup check works", passed,
                  "Returns boolean and list")
        
        return passed
    except Exception as e:
        print_test("Startup check", False, f"Exception: {str(e)}")
        return False


def test_configuration_values():
    """Test configuration values and thresholds."""
    print_header("TEST 9: Configuration Values")
    
    try:
        detector = AIDetector()
        
        print("  Checking configuration values...")
        print(f"  Large paste threshold: {detector.large_paste_threshold} chars")
        print(f"  Max suspicious pastes: {detector.max_suspicious_pastes}")
        print(f"  Clipboard check interval: {detector.clipboard_check_interval} seconds")
        print(f"  Process check interval: {detector.process_check_interval} seconds")
        
        # Verify reasonable values
        thresholds_valid = (
            detector.large_paste_threshold == 100 and
            detector.max_suspicious_pastes == 3 and
            detector.clipboard_check_interval == 30 and
            detector.process_check_interval == 60
        )
        
        # Test modification
        print("\n  Testing threshold modification...")
        detector.large_paste_threshold = 200
        print(f"  Modified large paste threshold: {detector.large_paste_threshold}")
        modification_works = detector.large_paste_threshold == 200
        
        passed = thresholds_valid and modification_works
        
        print_test("Configuration values are correct", passed,
                  "All thresholds have expected defaults")
        
        return passed
    except Exception as e:
        print_test("Configuration values", False, f"Exception: {str(e)}")
        return False


def test_browser_detection():
    """Test browser AI activity detection."""
    print_header("TEST 10: Browser Detection")
    
    try:
        detector = AIDetector()
        
        print("  Checking for browser processes...")
        browser_active = detector.check_browser_ai_activity()
        
        print(f"  Browser detected: {browser_active}")
        print(f"  Result type: {type(browser_active)} (should be bool)")
        
        if browser_active:
            print("  [INFO] Browser process detected (may be accessing AI sites)")
        else:
            print("  [OK] No browser activity detected")
        
        passed = isinstance(browser_active, bool)
        
        print_test("Browser detection works", passed,
                  "Returns boolean value")
        
        return passed
    except Exception as e:
        print_test("Browser detection", False, f"Exception: {str(e)}")
        return False


def run_all_tests():
    """Run all tests and print summary."""
    print("\n" + "#" * 70)
    print("  MANUAL TEST SUITE FOR AI DETECTOR MODULE")
    print("#" * 70)
    print(f"  System: {platform.system()} {platform.release()}")
    print(f"  Python: {sys.version.split()[0]}")
    print("#" * 70)
    
    tests = [
        ("Initialization", test_initialization),
        ("AI Processes Config", test_ai_processes_configuration),
        ("AI Websites Config", test_ai_websites_configuration),
        ("Suspicious Paste Detection", test_suspicious_paste_detection),
        ("Process Detection", test_process_detection),
        ("Background Monitoring", test_background_monitoring),
        ("IDE Detection", test_ide_detection),
        ("Startup Check", test_startup_check),
        ("Configuration Values", test_configuration_values),
        ("Browser Detection", test_browser_detection),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[CRASH] Test '{test_name}' crashed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}  {test_name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  *** ALL TESTS PASSED! ***")
    else:
        print(f"\n  WARNING: {total - passed} test(s) failed")
    
    print("\n" + "=" * 70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

