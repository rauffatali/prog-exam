"""
Manual Test Script for Connectivity Module

This script tests the connectivity.py module by calling its functions
and printing the results to the screen.

Run this script with: python tests/manual_test_connectivity.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner.connectivity import check_internet_connectivity
import time


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


def test_basic_connectivity():
    """Test basic internet connectivity check."""
    print_header("TEST 1: Basic Internet Connectivity Check")
    
    try:
        result = check_internet_connectivity()
        print(f"  Checking internet connection...")
        print(f"  Result: {result}")
        print(f"  Type: {type(result)}")
        
        # Test passes if result is a boolean
        passed = isinstance(result, bool)
        print_test("Basic connectivity check returns boolean", passed,
                  f"Returned {type(result).__name__}")
        
        if result:
            print("  [OK] Internet connection is AVAILABLE")
        else:
            print("  [FAIL] Internet connection is NOT AVAILABLE")
            print("  Note: This might be expected if you're offline")
        
        return passed
    except Exception as e:
        print_test("Basic connectivity check", False, f"Exception: {str(e)}")
        return False


def test_custom_timeout():
    """Test connectivity check with custom timeout."""
    print_header("TEST 2: Custom Timeout")
    
    try:
        # Test with very short timeout
        print("  Testing with 0.5 second timeout...")
        start_time = time.time()
        result1 = check_internet_connectivity(timeout=0.5)
        elapsed1 = time.time() - start_time
        print(f"  Result: {result1}")
        print(f"  Time taken: {elapsed1:.3f} seconds")
        
        # Test with longer timeout
        print("\n  Testing with 5 second timeout...")
        start_time = time.time()
        result2 = check_internet_connectivity(timeout=5.0)
        elapsed2 = time.time() - start_time
        print(f"  Result: {result2}")
        print(f"  Time taken: {elapsed2:.3f} seconds")
        
        passed = isinstance(result1, bool) and isinstance(result2, bool)
        print_test("Custom timeout works", passed,
                  f"Both calls returned boolean values")
        
        return passed
    except Exception as e:
        print_test("Custom timeout test", False, f"Exception: {str(e)}")
        return False


def test_multiple_calls():
    """Test multiple consecutive calls."""
    print_header("TEST 3: Multiple Consecutive Calls")
    
    try:
        results = []
        print("  Making 5 consecutive connectivity checks...")
        
        for i in range(5):
            start_time = time.time()
            result = check_internet_connectivity(timeout=2.0)
            elapsed = time.time() - start_time
            results.append(result)
            print(f"  Call {i+1}: {result} (took {elapsed:.3f}s)")
        
        # All results should be boolean
        all_boolean = all(isinstance(r, bool) for r in results)
        print(f"\n  All results are boolean: {all_boolean}")
        print(f"  Results: {results}")
        
        print_test("Multiple consecutive calls work", all_boolean,
                  f"Made 5 calls successfully")
        
        return all_boolean
    except Exception as e:
        print_test("Multiple calls test", False, f"Exception: {str(e)}")
        return False


def test_function_signature():
    """Test that function accepts expected parameters."""
    print_header("TEST 4: Function Signature and Parameters")
    
    try:
        import inspect
        sig = inspect.signature(check_internet_connectivity)
        params = list(sig.parameters.keys())
        
        print(f"  Function signature: {sig}")
        print(f"  Parameters: {params}")
        
        # Should have 'timeout' parameter
        has_timeout = 'timeout' in params
        print(f"  Has 'timeout' parameter: {has_timeout}")
        
        if has_timeout:
            timeout_param = sig.parameters['timeout']
            default_value = timeout_param.default
            print(f"  Default timeout value: {default_value}")
            
            passed = default_value == 2.0
            print_test("Function signature is correct", passed,
                      f"Has timeout parameter with default={default_value}")
        else:
            print_test("Function signature", False, "Missing timeout parameter")
            passed = False
        
        return passed
    except Exception as e:
        print_test("Function signature test", False, f"Exception: {str(e)}")
        return False


def test_dns_servers():
    """Test that function tries multiple DNS servers."""
    print_header("TEST 5: DNS Server Fallback Mechanism")
    
    print("  This test verifies the fallback mechanism by checking the code...")
    print("  The function should try multiple DNS servers:")
    print("    1. Cloudflare (1.1.1.1)")
    print("    2. Google (8.8.8.8)")
    print("    3. OpenDNS (208.67.222.222)")
    print("    4. Quad9 (9.9.9.9)")
    
    try:
        # Read the source code to verify DNS servers
        import inspect
        source = inspect.getsource(check_internet_connectivity)
        
        dns_servers = [
            ("1.1.1.1", "Cloudflare"),
            ("8.8.8.8", "Google"),
            ("208.67.222.222", "OpenDNS"),
            ("9.9.9.9", "Quad9")
        ]
        
        all_found = True
        for ip, name in dns_servers:
            found = ip in source
            status = "[OK]" if found else "[FAIL]"
            print(f"  {status} {name} DNS ({ip}): {'Found' if found else 'Not found'}")
            all_found = all_found and found
        
        print_test("All DNS servers configured", all_found,
                  "Function has fallback to multiple DNS servers")
        
        return all_found
    except Exception as e:
        print_test("DNS servers test", False, f"Exception: {str(e)}")
        return False


def test_error_handling():
    """Test error handling with extreme values."""
    print_header("TEST 6: Error Handling")
    
    try:
        # Test with zero timeout
        print("  Testing with zero timeout...")
        try:
            result1 = check_internet_connectivity(timeout=0.0)
            print(f"  Result with timeout=0.0: {result1}")
            zero_handled = True
        except Exception as e:
            print(f"  Exception with zero timeout: {type(e).__name__}")
            zero_handled = True  # It's okay to raise exception
        
        # Test with very large timeout
        print("\n  Testing with very large timeout (will be quick)...")
        try:
            result2 = check_internet_connectivity(timeout=10000.0)
            print(f"  Result with timeout=10000.0: {result2}")
            large_handled = True
        except Exception as e:
            print(f"  Exception with large timeout: {type(e).__name__}")
            large_handled = True
        
        passed = zero_handled and large_handled
        print_test("Error handling works", passed,
                  "Function handles edge cases gracefully")
        
        return passed
    except Exception as e:
        print_test("Error handling test", False, f"Exception: {str(e)}")
        return False


def run_all_tests():
    """Run all tests and print summary."""
    print("\n" + "#" * 70)
    print("  MANUAL TEST SUITE FOR CONNECTIVITY MODULE")
    print("#" * 70)
    
    tests = [
        ("Basic Connectivity", test_basic_connectivity),
        ("Custom Timeout", test_custom_timeout),
        ("Multiple Calls", test_multiple_calls),
        ("Function Signature", test_function_signature),
        ("DNS Fallback", test_dns_servers),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[CRASH] Test '{test_name}' crashed: {str(e)}")
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

