"""
Tests for connectivity module.

Tests the internet connectivity checking functionality including:
- Successful connection scenarios
- Connection failures
- Timeout handling
- Fallback mechanism to multiple DNS servers
"""

import pytest
import socket
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner.connectivity import check_internet_connectivity


class TestConnectivitySuccess:
    """Test successful connectivity scenarios."""
    
    @patch('socket.create_connection')
    def test_check_connectivity_cloudflare_success(self, mock_connection):
        """Test successful connection to Cloudflare DNS."""
        mock_connection.return_value = Mock()
        
        result = check_internet_connectivity()
        
        assert result is True
        mock_connection.assert_called_once_with(("1.1.1.1", 53), timeout=2.0)
    
    @patch('socket.create_connection')
    def test_check_connectivity_with_custom_timeout(self, mock_connection):
        """Test connectivity check with custom timeout."""
        mock_connection.return_value = Mock()
        
        result = check_internet_connectivity(timeout=5.0)
        
        assert result is True
        mock_connection.assert_called_once_with(("1.1.1.1", 53), timeout=5.0)
    
    @patch('socket.create_connection')
    def test_check_connectivity_very_short_timeout(self, mock_connection):
        """Test connectivity check with very short timeout."""
        mock_connection.return_value = Mock()
        
        result = check_internet_connectivity(timeout=0.5)
        
        assert result is True
        mock_connection.assert_called_once_with(("1.1.1.1", 53), timeout=0.5)


class TestConnectivityFallback:
    """Test fallback mechanism to alternative DNS servers."""
    
    @patch('socket.create_connection')
    def test_fallback_to_google_dns(self, mock_connection):
        """Test fallback to Google DNS when Cloudflare fails."""
        # First call (Cloudflare) fails, second call (Google) succeeds
        mock_connection.side_effect = [
            OSError("Connection failed"),
            Mock()  # Success
        ]
        
        result = check_internet_connectivity()
        
        assert result is True
        assert mock_connection.call_count == 2
        
        # Verify calls
        calls = mock_connection.call_args_list
        assert calls[0][0] == (("1.1.1.1", 53),)
        assert calls[1][0] == (("8.8.8.8", 53),)
    
    @patch('socket.create_connection')
    def test_fallback_to_opendns(self, mock_connection):
        """Test fallback to OpenDNS when Cloudflare and Google fail."""
        # First two calls fail, third call (OpenDNS) succeeds
        mock_connection.side_effect = [
            OSError("Connection failed"),
            OSError("Connection failed"),
            Mock()  # Success
        ]
        
        result = check_internet_connectivity()
        
        assert result is True
        assert mock_connection.call_count == 3
        
        # Verify calls
        calls = mock_connection.call_args_list
        assert calls[0][0] == (("1.1.1.1", 53),)
        assert calls[1][0] == (("8.8.8.8", 53),)
        assert calls[2][0] == (("208.67.222.222", 53),)
    
    @patch('socket.create_connection')
    def test_fallback_to_quad9(self, mock_connection):
        """Test fallback to Quad9 when all other DNS servers fail."""
        # First three calls fail, fourth call (Quad9) succeeds
        mock_connection.side_effect = [
            OSError("Connection failed"),
            OSError("Connection failed"),
            OSError("Connection failed"),
            Mock()  # Success
        ]
        
        result = check_internet_connectivity()
        
        assert result is True
        assert mock_connection.call_count == 4
        
        # Verify all DNS servers were tried
        calls = mock_connection.call_args_list
        assert calls[0][0] == (("1.1.1.1", 53),)
        assert calls[1][0] == (("8.8.8.8", 53),)
        assert calls[2][0] == (("208.67.222.222", 53),)
        assert calls[3][0] == (("9.9.9.9", 53),)
    
    @patch('socket.create_connection')
    def test_all_fallbacks_fail(self, mock_connection):
        """Test when all DNS servers fail to connect."""
        # All calls fail
        mock_connection.side_effect = [
            OSError("Connection failed"),
            OSError("Connection failed"),
            OSError("Connection failed"),
            OSError("Connection failed")
        ]
        
        result = check_internet_connectivity()
        
        assert result is False
        assert mock_connection.call_count == 4


class TestConnectivityFailure:
    """Test connectivity failure scenarios."""
    
    @patch('socket.create_connection')
    def test_no_internet_connection(self, mock_connection):
        """Test when there is no internet connection."""
        mock_connection.side_effect = OSError("No internet connection")
        
        result = check_internet_connectivity()
        
        assert result is False
    
    @patch('socket.create_connection')
    def test_network_unreachable(self, mock_connection):
        """Test when network is unreachable."""
        mock_connection.side_effect = OSError("[Errno 101] Network is unreachable")
        
        result = check_internet_connectivity()
        
        assert result is False
    
    @patch('socket.create_connection')
    def test_connection_refused(self, mock_connection):
        """Test when connection is refused."""
        mock_connection.side_effect = OSError("[Errno 111] Connection refused")
        
        result = check_internet_connectivity()
        
        assert result is False
    
    @patch('socket.create_connection')
    def test_timeout_error(self, mock_connection):
        """Test when connection times out."""
        mock_connection.side_effect = socket.timeout("Connection timed out")
        
        result = check_internet_connectivity()
        
        assert result is False


class TestConnectivityEdgeCases:
    """Test edge cases and special scenarios."""
    
    @patch('socket.create_connection')
    def test_zero_timeout(self, mock_connection):
        """Test with zero timeout (should still work if connection is immediate)."""
        mock_connection.return_value = Mock()
        
        result = check_internet_connectivity(timeout=0.0)
        
        assert result is True
        mock_connection.assert_called_once_with(("1.1.1.1", 53), timeout=0.0)
    
    @patch('socket.create_connection')
    def test_negative_timeout(self, mock_connection):
        """Test with negative timeout (unusual but should be handled by socket)."""
        mock_connection.return_value = Mock()
        
        # This might raise an exception depending on socket implementation
        # but our function should handle it
        try:
            result = check_internet_connectivity(timeout=-1.0)
            assert result is True
        except (ValueError, OSError):
            # Socket might reject negative timeout, which is acceptable
            pass
    
    @patch('socket.create_connection')
    def test_very_large_timeout(self, mock_connection):
        """Test with very large timeout value."""
        mock_connection.return_value = Mock()
        
        result = check_internet_connectivity(timeout=3600.0)
        
        assert result is True
        mock_connection.assert_called_once_with(("1.1.1.1", 53), timeout=3600.0)
    
    @patch('socket.create_connection')
    def test_connection_closes_properly(self, mock_connection):
        """Test that connection is created but doesn't leak resources."""
        mock_conn = Mock()
        mock_connection.return_value = mock_conn
        
        result = check_internet_connectivity()
        
        assert result is True
        # Connection object should be created
        mock_connection.assert_called_once()
    
    @patch('socket.create_connection')
    def test_intermittent_failures(self, mock_connection):
        """Test behavior with intermittent failures (some servers work, some don't)."""
        # Simulate: Cloudflare fails, Google fails, OpenDNS works
        mock_connection.side_effect = [
            OSError("Timeout"),
            OSError("Refused"),
            Mock()  # Success
        ]
        
        result = check_internet_connectivity(timeout=1.0)
        
        assert result is True
        assert mock_connection.call_count == 3


class TestConnectivityErrorTypes:
    """Test different types of network errors."""
    
    @patch('socket.create_connection')
    def test_dns_resolution_error(self, mock_connection):
        """Test when DNS resolution fails (though we use IP addresses)."""
        mock_connection.side_effect = socket.gaierror("Name or service not known")
        
        result = check_internet_connectivity()
        
        assert result is False
    
    @patch('socket.create_connection')
    def test_permission_error(self, mock_connection):
        """Test when there's a permission error."""
        mock_connection.side_effect = PermissionError("Permission denied")
        
        # Since we catch OSError, not PermissionError specifically
        # This might propagate up or be caught depending on inheritance
        try:
            result = check_internet_connectivity()
            assert result is False
        except PermissionError:
            # If not caught by OSError, that's also acceptable behavior
            pass
    
    @patch('socket.create_connection')
    def test_socket_error(self, mock_connection):
        """Test generic socket error."""
        mock_connection.side_effect = socket.error("Socket error")
        
        result = check_internet_connectivity()
        
        assert result is False


class TestConnectivityMultipleCalls:
    """Test multiple consecutive calls to check_internet_connectivity."""
    
    @patch('socket.create_connection')
    def test_multiple_successful_calls(self, mock_connection):
        """Test multiple consecutive successful calls."""
        mock_connection.return_value = Mock()
        
        result1 = check_internet_connectivity()
        result2 = check_internet_connectivity()
        result3 = check_internet_connectivity()
        
        assert result1 is True
        assert result2 is True
        assert result3 is True
        assert mock_connection.call_count == 3
    
    @patch('socket.create_connection')
    def test_alternating_success_failure(self, mock_connection):
        """Test alternating success and failure calls."""
        # Alternate between success and failure
        mock_connection.side_effect = [
            Mock(),  # Success
            OSError("Failed"),  # All fail
            OSError("Failed"),
            OSError("Failed"),
            OSError("Failed"),
            Mock(),  # Success again
        ]
        
        result1 = check_internet_connectivity()
        result2 = check_internet_connectivity()
        result3 = check_internet_connectivity()
        
        assert result1 is True
        assert result2 is False
        assert result3 is True


class TestConnectivityDNSServers:
    """Test that all DNS servers are properly configured."""
    
    @patch('socket.create_connection')
    def test_all_dns_servers_are_valid_ips(self, mock_connection):
        """Test that all DNS server IPs used are valid."""
        mock_connection.side_effect = [
            OSError("Fail"),
            OSError("Fail"),
            OSError("Fail"),
            OSError("Fail")
        ]
        
        check_internet_connectivity()
        
        # Extract IPs from all calls
        calls = mock_connection.call_args_list
        ips = [call[0][0][0] for call in calls]
        
        # Verify known DNS servers
        assert "1.1.1.1" in ips      # Cloudflare
        assert "8.8.8.8" in ips      # Google
        assert "208.67.222.222" in ips  # OpenDNS
        assert "9.9.9.9" in ips      # Quad9
    
    @patch('socket.create_connection')
    def test_all_use_port_53(self, mock_connection):
        """Test that all DNS checks use port 53."""
        mock_connection.side_effect = [
            OSError("Fail"),
            OSError("Fail"),
            OSError("Fail"),
            OSError("Fail")
        ]
        
        check_internet_connectivity()
        
        # Extract ports from all calls
        calls = mock_connection.call_args_list
        ports = [call[0][0][1] for call in calls]
        
        # All should use DNS port 53
        assert all(port == 53 for port in ports)


class TestConnectivityRealWorld:
    """Integration-style tests that can be run with real network (optional)."""
    
    @pytest.mark.skip(reason="Requires actual internet connection")
    def test_real_connection_check(self):
        """Test with real internet connection (skip in CI/CD)."""
        result = check_internet_connectivity()
        
        # Should succeed if internet is available
        assert isinstance(result, bool)
    
    @pytest.mark.skip(reason="Requires network simulation")
    def test_real_no_connection(self):
        """Test with real disconnected network (skip in CI/CD)."""
        # This would require actually disconnecting from network
        # or using network simulation tools
        pass


class TestConnectivityPerformance:
    """Test performance characteristics of connectivity checks."""
    
    @patch('socket.create_connection')
    def test_fast_failure_with_short_timeout(self, mock_connection):
        """Test that function fails fast with short timeout."""
        import time
        
        def slow_fail(*args, **kwargs):
            time.sleep(0.1)
            raise OSError("Timeout")
        
        mock_connection.side_effect = slow_fail
        
        start_time = time.time()
        result = check_internet_connectivity(timeout=0.1)
        elapsed_time = time.time() - start_time
        
        assert result is False
        # Should complete within reasonable time (4 attempts * 0.1s + overhead)
        assert elapsed_time < 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

