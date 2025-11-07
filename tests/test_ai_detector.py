"""
Tests for AI Detector module.

Tests the AI coding assistant detection functionality including:
- Process detection on different platforms
- Clipboard monitoring
- IDE extension detection
- Background monitoring threads
"""

import pytest
import time
import platform
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner.ai_detector import AIDetector, check_ai_tools_at_startup


class TestAIDetectorInitialization:
    """Test AIDetector class initialization."""
    
    def test_init_without_logger(self):
        """Test initialization without session logger."""
        detector = AIDetector()
        
        assert detector.session_logger is None
        assert not detector.monitoring_active
        assert detector.detection_thread is None
        assert detector.suspicious_paste_count == 0
        assert detector.last_clipboard_content == ""
    
    def test_init_with_logger(self):
        """Test initialization with session logger."""
        mock_logger = Mock()
        detector = AIDetector(session_logger=mock_logger)
        
        assert detector.session_logger == mock_logger
        assert not detector.monitoring_active
    
    def test_ai_processes_configured(self):
        """Test that AI processes are properly configured for all platforms."""
        detector = AIDetector()
        
        assert 'windows' in detector.ai_processes
        assert 'linux' in detector.ai_processes
        assert 'darwin' in detector.ai_processes
        
        # Check that common AI tools are listed
        assert 'copilot' in detector.ai_processes['windows']
        assert 'tabnine' in detector.ai_processes['linux']
        assert 'cursor' in detector.ai_processes['darwin']
    
    def test_ai_websites_configured(self):
        """Test that AI websites are properly configured."""
        detector = AIDetector()
        
        assert 'chat.openai.com' in detector.ai_websites
        assert 'claude.ai' in detector.ai_websites
        assert 'github.com/copilot' in detector.ai_websites


class TestProcessDetectionWindows:
    """Test Windows-specific process detection."""
    
    @patch('platform.system')
    @patch('subprocess.run')
    def test_check_processes_windows_found(self, mock_run, mock_platform):
        """Test detection of AI processes on Windows."""
        mock_platform.return_value = 'Windows'
        
        # Simulate tasklist output with a Copilot process
        mock_run.return_value = Mock(
            returncode=0,
            stdout='"System Idle Process","0","Services","24 K"\n"copilot.exe","1234","Console","50 MB"\n'
        )
        
        detector = AIDetector()
        target_processes = ['copilot', 'tabnine']
        result = detector._check_processes_windows(target_processes)
        
        assert 'copilot.exe' in result
        assert len(result) > 0
    
    @patch('subprocess.run')
    def test_check_processes_windows_not_found(self, mock_run):
        """Test when no AI processes are found on Windows."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='"System Idle Process","0","Services","24 K"\n"notepad.exe","1234","Console","10 MB"\n'
        )
        
        detector = AIDetector()
        target_processes = ['copilot', 'tabnine']
        result = detector._check_processes_windows(target_processes)
        
        assert len(result) == 0
    
    @patch('subprocess.run')
    def test_check_processes_windows_timeout(self, mock_run):
        """Test Windows process check with timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('tasklist', 10)
        
        detector = AIDetector()
        target_processes = ['copilot']
        result = detector._check_processes_windows(target_processes)
        
        # Should return empty list on timeout (or use psutil fallback)
        assert isinstance(result, list)
    
    @patch('subprocess.run')
    def test_check_processes_windows_with_psutil_fallback(self, mock_run):
        """Test psutil fallback when tasklist fails."""
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, 'tasklist')
        
        # Mock psutil inside sys.modules (since it's imported inside the function)
        import sys
        mock_psutil = MagicMock()
        mock_proc = Mock()
        mock_proc.info = {'name': 'copilot.exe'}
        mock_psutil.process_iter.return_value = [mock_proc]
        mock_psutil.NoSuchProcess = Exception
        mock_psutil.AccessDenied = Exception
        
        with patch.dict('sys.modules', {'psutil': mock_psutil}):
            detector = AIDetector()
            target_processes = ['copilot']
            result = detector._check_processes_windows(target_processes)
            
            # Should use psutil fallback
            assert 'copilot.exe' in result


class TestProcessDetectionUnix:
    """Test Unix-specific process detection."""
    
    @patch('subprocess.run')
    def test_check_processes_unix_found(self, mock_run):
        """Test detection of AI processes on Unix."""
        # Simulate ps aux output
        mock_run.return_value = Mock(
            returncode=0,
            stdout='USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND\nuser 1234 0.0 0.1 12345 6789 ? S 10:00 0:00 /usr/bin/cursor --no-sandbox\n'
        )
        
        detector = AIDetector()
        target_processes = ['cursor', 'tabnine']
        result = detector._check_processes_unix(target_processes)
        
        assert 'cursor' in result
    
    @patch('subprocess.run')
    def test_check_processes_unix_not_found(self, mock_run):
        """Test when no AI processes are found on Unix."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND\nuser 1234 0.0 0.1 12345 6789 ? S 10:00 0:00 /usr/bin/vim\n'
        )
        
        detector = AIDetector()
        target_processes = ['cursor', 'tabnine']
        result = detector._check_processes_unix(target_processes)
        
        assert len(result) == 0
    
    @patch('subprocess.run')
    def test_check_processes_unix_timeout(self, mock_run):
        """Test Unix process check with timeout."""
        import subprocess
        import sys
        mock_run.side_effect = subprocess.TimeoutExpired('ps', 10)
        
        # Mock psutil for the fallback
        mock_psutil = MagicMock()
        mock_psutil.process_iter.return_value = []
        mock_psutil.NoSuchProcess = Exception
        mock_psutil.AccessDenied = Exception
        
        with patch.dict('sys.modules', {'psutil': mock_psutil}):
            detector = AIDetector()
            target_processes = ['cursor']
            result = detector._check_processes_unix(target_processes)
            
            assert isinstance(result, list)


class TestClipboardDetection:
    """Test clipboard monitoring functionality."""
    
    def test_is_suspicious_paste_small_content(self):
        """Test that small content is not flagged as suspicious."""
        detector = AIDetector()
        
        small_content = "hello world"
        assert not detector._is_suspicious_paste(small_content)
    
    def test_is_suspicious_paste_large_code(self):
        """Test that large code-like content is flagged as suspicious."""
        detector = AIDetector()
        
        # Large content with code indicators
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
        assert detector._is_suspicious_paste(large_code)
    
    def test_is_suspicious_paste_large_non_code(self):
        """Test that large non-code content is not flagged."""
        detector = AIDetector()
        
        # Large content without code indicators
        large_text = "Lorem ipsum dolor sit amet. " * 20
        assert not detector._is_suspicious_paste(large_text)
    
    @patch.object(AIDetector, '_get_clipboard_content')
    def test_check_clipboard_activity_new_content(self, mock_clipboard):
        """Test clipboard check with new content."""
        mock_logger = Mock()
        detector = AIDetector(session_logger=mock_logger)
        
        # Simulate suspicious paste - large code with multiple indicators
        suspicious_code = """
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        if num > 0:
            total += num
        else:
            print("Negative number found")
    return total

class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, x):
        self.result += x
        return self.result
"""
        mock_clipboard.return_value = suspicious_code
        
        detector._check_clipboard_activity()
        
        assert detector.suspicious_paste_count == 1
        mock_logger.assert_called()
    
    @patch.object(AIDetector, '_get_clipboard_content')
    def test_check_clipboard_activity_same_content(self, mock_clipboard):
        """Test that same clipboard content doesn't trigger multiple alerts."""
        detector = AIDetector()
        
        content = "def test():\n    pass\n" * 20
        mock_clipboard.return_value = content
        detector.last_clipboard_content = content
        
        initial_count = detector.suspicious_paste_count
        detector._check_clipboard_activity()
        
        # Should not increment count for same content
        assert detector.suspicious_paste_count == initial_count


class TestIDEDetection:
    """Test IDE AI tool detection."""
    
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('platform.system')
    def test_check_vscode_extensions_found(self, mock_platform, mock_listdir, mock_exists):
        """Test detection of VS Code AI extensions."""
        mock_platform.return_value = 'Linux'
        mock_exists.return_value = True
        mock_listdir.return_value = [
            'github.copilot-1.0.0',
            'tabnine.tabnine-vscode-3.5.0',
            'ms-python.python-2023.1.0'
        ]
        
        detector = AIDetector()
        extensions = detector._check_vscode_extensions()
        
        assert 'github.copilot' in extensions
        assert 'tabnine.tabnine-vscode' in extensions
    
    @patch('os.path.exists')
    def test_check_vscode_extensions_dir_not_exists(self, mock_exists):
        """Test when VS Code extensions directory doesn't exist."""
        mock_exists.return_value = False
        
        detector = AIDetector()
        extensions = detector._check_vscode_extensions()
        
        assert len(extensions) == 0
    
    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    def test_check_vscode_copilot_enabled(self, mock_open, mock_exists):
        """Test checking if Copilot is enabled in VS Code."""
        mock_exists.return_value = True
        
        # Mock settings.json with Copilot enabled
        settings = {
            "github.copilot.enable": True,
            "editor.fontSize": 14
        }
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(settings)
        
        with patch('json.load', return_value=settings):
            detector = AIDetector()
            enabled, details = detector._check_vscode_copilot_enabled()
        
        assert enabled
        assert "Enabled" in details
    
    @patch('os.path.exists')
    def test_check_vscode_copilot_settings_not_found(self, mock_exists):
        """Test when VS Code settings file doesn't exist."""
        mock_exists.return_value = False
        
        detector = AIDetector()
        enabled, details = detector._check_vscode_copilot_enabled()
        
        assert not enabled
        assert "not found" in details


class TestBackgroundMonitoring:
    """Test background monitoring thread functionality."""
    
    def test_start_monitoring(self):
        """Test starting background monitoring."""
        mock_logger = Mock()
        detector = AIDetector(session_logger=mock_logger)
        
        detector.start_monitoring()
        
        assert detector.monitoring_active
        assert detector.detection_thread is not None
        assert detector.detection_thread.is_alive()
        
        # Clean up
        detector.stop_monitoring()
    
    def test_stop_monitoring(self):
        """Test stopping background monitoring."""
        mock_logger = Mock()
        detector = AIDetector(session_logger=mock_logger)
        
        detector.start_monitoring()
        time.sleep(0.1)  # Let thread start
        detector.stop_monitoring()
        
        assert not detector.monitoring_active
        mock_logger.assert_any_call("AI_MONITORING_STOPPED", 
                                    "AI detection monitoring deactivated")
    
    def test_start_monitoring_twice(self):
        """Test that starting monitoring twice doesn't create duplicate threads."""
        detector = AIDetector()
        
        detector.start_monitoring()
        thread1 = detector.detection_thread
        
        detector.start_monitoring()  # Second call
        thread2 = detector.detection_thread
        
        assert thread1 is thread2
        
        # Clean up
        detector.stop_monitoring()
    
    @patch.object(AIDetector, '_check_ai_processes')
    @patch.object(AIDetector, '_check_clipboard_activity')
    def test_monitor_background_calls_checks(self, mock_clipboard, mock_processes):
        """Test that background monitor calls check methods."""
        detector = AIDetector()
        detector.process_check_interval = 0.1
        detector.clipboard_check_interval = 0.1
        
        detector.start_monitoring()
        time.sleep(0.3)  # Let it run a bit
        detector.stop_monitoring()
        
        # Should have been called at least once
        assert mock_processes.call_count >= 1 or mock_clipboard.call_count >= 1


class TestBrowserDetection:
    """Test browser and AI website detection."""
    
    @patch('subprocess.run')
    @patch('platform.system')
    def test_check_browser_ai_activity_windows(self, mock_platform, mock_run):
        """Test browser detection on Windows."""
        mock_platform.return_value = 'Windows'
        mock_run.return_value = Mock(
            returncode=0,
            stdout='"chrome.exe","1234","Console","100 MB"\n'
        )
        
        detector = AIDetector()
        result = detector.check_browser_ai_activity()
        
        assert result is True
    
    @patch('subprocess.run')
    @patch('platform.system')
    def test_check_browser_ai_activity_no_browser(self, mock_platform, mock_run):
        """Test when no browser is running."""
        mock_platform.return_value = 'Windows'
        mock_run.return_value = Mock(
            returncode=1,
            stdout=''
        )
        
        detector = AIDetector()
        result = detector.check_browser_ai_activity()
        
        assert result is False


class TestStartupCheck:
    """Test startup AI tool check function."""
    
    @patch('platform.system')
    @patch.object(AIDetector, '_check_processes_windows')
    def test_check_ai_tools_at_startup_windows(self, mock_check, mock_platform):
        """Test startup check on Windows."""
        mock_platform.return_value = 'Windows'
        mock_check.return_value = ['copilot.exe', 'tabnine.exe']
        
        detected, tools = check_ai_tools_at_startup()
        
        assert detected is True
        assert len(tools) == 2
        assert 'copilot.exe' in tools
    
    @patch('platform.system')
    @patch.object(AIDetector, '_check_processes_unix')
    def test_check_ai_tools_at_startup_unix(self, mock_check, mock_platform):
        """Test startup check on Unix."""
        mock_platform.return_value = 'Linux'
        mock_check.return_value = []
        
        detected, tools = check_ai_tools_at_startup()
        
        assert detected is False
        assert len(tools) == 0
    
    @patch('platform.system')
    @patch.object(AIDetector, '_check_processes_windows')
    def test_check_ai_tools_at_startup_exception(self, mock_check, mock_platform):
        """Test startup check handles exceptions gracefully."""
        mock_platform.return_value = 'Windows'
        mock_check.side_effect = Exception("Test error")
        
        detected, tools = check_ai_tools_at_startup()
        
        assert detected is False
        assert len(tools) == 0


class TestConfigurationValues:
    """Test configuration and threshold values."""
    
    def test_default_thresholds(self):
        """Test that default threshold values are reasonable."""
        detector = AIDetector()
        
        assert detector.large_paste_threshold == 100
        assert detector.max_suspicious_pastes == 3
        assert detector.clipboard_check_interval == 30
        assert detector.process_check_interval == 60
    
    def test_threshold_modification(self):
        """Test that thresholds can be modified."""
        detector = AIDetector()
        
        detector.large_paste_threshold = 200
        detector.max_suspicious_pastes = 5
        
        assert detector.large_paste_threshold == 200
        assert detector.max_suspicious_pastes == 5


class TestErrorHandling:
    """Test error handling in various scenarios."""
    
    @patch.object(AIDetector, '_get_clipboard_content')
    def test_clipboard_check_handles_exceptions(self, mock_clipboard):
        """Test that clipboard check handles exceptions gracefully."""
        mock_clipboard.side_effect = Exception("Clipboard error")
        
        detector = AIDetector()
        
        # Should not raise exception
        try:
            detector._check_clipboard_activity()
        except Exception:
            pytest.fail("_check_clipboard_activity raised an exception")
    
    @patch('subprocess.run')
    def test_process_check_handles_exceptions(self, mock_run):
        """Test that process check handles known exceptions gracefully."""
        import subprocess
        import sys
        
        # Test with CalledProcessError which is handled
        mock_run.side_effect = subprocess.CalledProcessError(1, 'tasklist')
        
        # Mock psutil to not be available (ImportError)
        with patch.dict('sys.modules', {'psutil': None}):
            detector = AIDetector()
            
            # Should not raise exception and return empty list
            try:
                result = detector._check_processes_windows(['copilot'])
                assert isinstance(result, list)
                assert len(result) == 0
            except Exception as e:
                pytest.fail(f"_check_processes_windows raised an exception: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

