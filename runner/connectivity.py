import socket

def check_internet_connectivity(timeout: float = 2.0) -> bool:
    """
    Check if the system has internet connectivity by attempting to connect
    to a reliable external host.
    
    Args:
        timeout: Connection timeout in seconds
        
    Returns:
        True if internet connection detected, False otherwise
    """
    try:
        # connect to Cloudflare's DNS server
        socket.create_connection(("1.1.1.1", 53), timeout=timeout)
        return True
    except OSError:
        try:
            # Fallback: Google's DNS
            socket.create_connection(("8.8.8.8", 53), timeout=timeout)
            return True
        except OSError:
            try:
                # Fallback: OpenDNS
                socket.create_connection(("208.67.222.222", 53), timeout=timeout)
                return True
            except OSError:
                try:
                    # Fallback: Quad9
                    socket.create_connection(("9.9.9.9", 53), timeout=timeout)
                    return True
                except OSError:
                    return False