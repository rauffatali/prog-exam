# Test Suite Documentation

This directory contains comprehensive tests for the exam system's AI detection and connectivity modules.

## Test Files

### 1. **pytest Tests** (Automated Unit Tests)

These are automated unit tests that use the pytest framework with mocking to test individual components in isolation.

- **`test_ai_detector.py`** - 33 unit tests for the AI detector module
- **`test_connectivity.py`** - 26 unit tests for the connectivity module

#### Running pytest Tests

```powershell
# Run all pytest tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_ai_detector.py -v
python -m pytest tests/test_connectivity.py -v

# Run with detailed output
python -m pytest tests/ -v --tb=short

# Run and show test coverage
python -m pytest tests/ --cov=runner --cov-report=html
```

### 2. **Manual Tests** (Interactive Function Tests)

These are standalone scripts that directly call functions and print results to the screen. They don't require pytest and are useful for manual verification and demonstration.

- **`manual_test_connectivity.py`** - 6 tests for connectivity functionality
- **`manual_test_ai_detector.py`** - 10 tests for AI detection functionality

#### Running Manual Tests

```powershell
# Run connectivity manual tests
python tests/manual_test_connectivity.py

# Run AI detector manual tests
python tests/manual_test_ai_detector.py
```

## Test Coverage

### AI Detector Tests (`test_ai_detector.py`)

The AI detector test suite covers:

1. **Initialization Tests** (4 tests)
   - Without logger
   - With logger
   - AI processes configuration
   - AI websites configuration

2. **Process Detection Tests** (8 tests)
   - Windows process detection
   - Unix/Linux process detection
   - Timeout handling
   - psutil fallback mechanism

3. **Clipboard Detection Tests** (5 tests)
   - Small content (not suspicious)
   - Large code content (suspicious)
   - Large non-code content
   - New content detection
   - Same content handling

4. **IDE Detection Tests** (4 tests)
   - VS Code extensions detection
   - Copilot settings check
   - Directory not found handling
   - Settings file not found handling

5. **Background Monitoring Tests** (4 tests)
   - Start monitoring
   - Stop monitoring
   - Multiple start calls
   - Monitor loop execution

6. **Browser Detection Tests** (2 tests)
   - Browser detected
   - No browser running

7. **Startup Check Tests** (3 tests)
   - Windows startup check
   - Unix startup check
   - Exception handling

8. **Configuration Tests** (2 tests)
   - Default thresholds
   - Threshold modification

9. **Error Handling Tests** (2 tests)
   - Clipboard exceptions
   - Process check exceptions

### Connectivity Tests (`test_connectivity.py`)

The connectivity test suite covers:

1. **Success Tests** (3 tests)
   - Cloudflare DNS connection
   - Custom timeout values
   - Very short timeout

2. **Fallback Tests** (4 tests)
   - Google DNS fallback
   - OpenDNS fallback
   - Quad9 fallback
   - All fallbacks fail

3. **Failure Tests** (4 tests)
   - No internet connection
   - Network unreachable
   - Connection refused
   - Timeout error

4. **Edge Cases** (6 tests)
   - Zero timeout
   - Negative timeout
   - Very large timeout
   - Connection cleanup
   - Intermittent failures

5. **Error Types** (3 tests)
   - DNS resolution error
   - Permission error
   - Socket error

6. **Multiple Calls** (2 tests)
   - Multiple successful calls
   - Alternating success/failure

7. **DNS Configuration** (2 tests)
   - Valid IP addresses
   - Correct port (53)

8. **Real World Tests** (2 tests, skipped by default)
   - Real connection check
   - Real disconnection

9. **Performance Tests** (1 test)
   - Fast failure with short timeout

## Test Results

### pytest Test Results

```
========================= 57 passed, 2 skipped =========================
```

- **AI Detector**: 33 tests passed
- **Connectivity**: 24 tests passed (2 skipped for real network testing)

### Manual Test Results

Both manual test scripts report:
- **Connectivity**: 6/6 tests passed
- **AI Detector**: 10/10 tests passed

## What the Tests Verify

### Connectivity Module

The tests verify that `connectivity.py`:
- ✅ Returns boolean values (True/False)
- ✅ Accepts custom timeout parameters
- ✅ Falls back to multiple DNS servers (Cloudflare → Google → OpenDNS → Quad9)
- ✅ Handles connection failures gracefully
- ✅ Works with edge cases (zero/negative/large timeouts)
- ✅ Handles various network errors (timeout, refused, unreachable)

### AI Detector Module

The tests verify that `ai_detector.py`:
- ✅ Initializes correctly with/without logger
- ✅ Detects AI coding assistant processes (Copilot, Tabnine, Cursor, etc.)
- ✅ Works cross-platform (Windows, Linux, macOS)
- ✅ Monitors clipboard for suspicious code pastes
- ✅ Distinguishes between code and regular text
- ✅ Detects IDE extensions (VS Code AI tools)
- ✅ Runs background monitoring in separate thread
- ✅ Checks browser processes
- ✅ Has configurable thresholds
- ✅ Handles errors gracefully

## Dependencies

To run the pytest tests, you need:

```
pytest>=8.4.1
pytest-mock>=3.14.1
```

The manual tests only require standard Python libraries (no additional dependencies).

## Notes for Developers

### Running Specific Test Classes

```powershell
# Run specific test class
python -m pytest tests/test_ai_detector.py::TestAIDetectorInitialization -v

# Run specific test method
python -m pytest tests/test_ai_detector.py::TestAIDetectorInitialization::test_init_without_logger -v
```

### Debugging Failed Tests

```powershell
# Run with full traceback
python -m pytest tests/ -v --tb=long

# Run with print statements visible
python -m pytest tests/ -v -s

# Stop at first failure
python -m pytest tests/ -v -x
```

### Adding New Tests

1. For **pytest tests**: Add test methods to the appropriate test class in `test_ai_detector.py` or `test_connectivity.py`
2. For **manual tests**: Add new test functions following the pattern in `manual_test_*.py` files

### Test Organization

Tests are organized by functionality:
- Each test class represents a specific aspect (e.g., `TestClipboardDetection`)
- Test methods should be descriptive (e.g., `test_suspicious_paste_large_code`)
- Use mocking to isolate components and avoid external dependencies

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    python -m pytest tests/ -v --tb=short
```

## Known Issues

1. **Windows Console Encoding**: The manual test scripts use ASCII-safe characters to avoid Unicode encoding issues on Windows.

2. **Real Network Tests**: Two tests in `test_connectivity.py` are skipped by default as they require actual internet connection. Run them manually if needed.

3. **Platform-Specific Tests**: Some AI detection features work differently on Windows vs Unix systems. Tests account for these differences.

## Contact

For questions or issues with the tests, please refer to the main project documentation.

