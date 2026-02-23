"""
Authentication Module

Handles ECU security access and proprietary authentication
for Harley-Davidson ECUs.
"""

import os
import re
import hashlib
from typing import Optional, Callable

from .can_interface import CANInterface
from .protocol import UDS, UDSProtocol


class Authenticator:
    """
    ECU Authentication handler.
    
    Implements:
    - Level 1 security access (XOR algorithm)
    - Proprietary 2008-byte authentication payload
    - Session management
    """
    
    # Security algorithm: Key = Seed XOR 0x9AE8
    SECURITY_XOR = 0x9AE8
    
    # Auth payload download parameters
    AUTH_ADDRESS = 0x00000000
    AUTH_LENGTH = 0x07D6  # 2006 bytes
    
    def __init__(self, can: CANInterface):
        self.can = can
        self.auth_payload: Optional[bytes] = None
        self.authenticated = False
        self.log_callback: Optional[Callable] = None
    
    def set_log_callback(self, callback: Callable):
        self.log_callback = callback
    
    def _log(self, message: str, level: str = 'info'):
        if self.log_callback:
            self.log_callback(message, level)
    
    def compute_key(self, seed: bytes) -> bytes:
        """
        Compute security key from seed using XOR algorithm.
        
        Args:
            seed: 2-byte seed from ECU
            
        Returns:
            2-byte key
        """
        if len(seed) < 2:
            return b'\x00\x00'
        
        seed_val = (seed[0] << 8) | seed[1]
        key_val = seed_val ^ self.SECURITY_XOR
        
        return bytes([(key_val >> 8) & 0xFF, key_val & 0xFF])
    
    def load_auth_payload(self, capture_file: str) -> bool:
        """
        Load authentication payload from a capture file.
        
        The auth payload is extracted from the TransferData (0x36)
        sequence in a PowerVision capture.
        
        Args:
            capture_file: Path to capture file
            
        Returns:
            True if payload loaded successfully
        """
        if not os.path.exists(capture_file):
            self._log(f"Capture file not found: {capture_file}", 'error')
            return False
        
        try:
            with open(capture_file, 'r', errors='ignore') as f:
                content = f.read()
            
            # Find all TX frames (0x7E0)
            matches = re.findall(r'0x7E0\s+8\s+([0-9A-Fa-f]{16})', content)
            
            payload = bytearray()
            collecting = False
            
            for match in matches:
                frame = bytes.fromhex(match)
                pci = frame[0]
                
                # First Frame with TransferData (0x36)
                if (pci & 0xF0) == 0x10 and frame[2] == 0x36:
                    payload = bytearray(frame[4:8])
                    collecting = True
                    continue
                
                # Consecutive Frames
                if collecting and (pci & 0xF0) == 0x20:
                    payload.extend(frame[1:8])
                    if len(payload) >= 2006:
                        break
            
            if len(payload) >= 2000:
                self.auth_payload = bytes(payload[:2006])
                checksum = hashlib.md5(self.auth_payload).hexdigest()[:8]
                self._log(
                    f"Auth payload loaded: {len(self.auth_payload)} bytes "
                    f"(MD5: {checksum})",
                    'success'
                )
                return True
            
            self._log("Failed to extract auth payload from capture", 'error')
            return False
            
        except Exception as e:
            self._log(f"Auth payload load error: {e}", 'error')
            return False
    
    def find_capture_file(self, directory: str = '.') -> Optional[str]:
        """
        Find most recent capture file in directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            Path to capture file or None
        """
        try:
            captures = [
                f for f in os.listdir(directory)
                if 'capture' in f.lower() and f.endswith('.txt')
            ]
            
            if not captures:
                return None
            
            # Sort by modification time, newest first
            captures.sort(
                key=lambda f: os.path.getmtime(os.path.join(directory, f)),
                reverse=True
            )
            
            return os.path.join(directory, captures[0])
            
        except Exception:
            return None
    
    def start_session(self, session: int = UDS.DSC_EXTENDED) -> bool:
        """
        Start diagnostic session.
        
        Args:
            session: Session type (default: Extended)
            
        Returns:
            True if session started
        """
        # Send TesterPresent first
        self.can.send_frame(self.can.TX_ID, bytes([0x3E, 0x00]))
        self.can.recv_response(timeout=0.5)
        
        # Broadcast session control
        self.can.send_broadcast(bytes([0x10, session]))
        self.can.drain(timeout=0.1)
        
        return True
    
    def security_access(self, level: int = 1) -> bool:
        """
        Perform security access (Level 1).
        
        Args:
            level: Security level (1, 3, etc.)
            
        Returns:
            True if security unlocked
        """
        # Request seed
        request = UDSProtocol.build_security_seed(level)
        self.can.send_frame(self.can.TX_ID, request)
        
        response = self.can.recv_response()
        if not response or response[0] != 0x67:
            self._log("Security seed request failed", 'error')
            return False
        
        seed = response[2:4]
        key = self.compute_key(seed)
        
        self._log(f"Seed: {seed.hex()}, Key: {key.hex()}", 'info')
        
        # Send key
        request = UDSProtocol.build_security_key(level, key)
        self.can.send_frame(self.can.TX_ID, request)
        
        response = self.can.recv_response()
        if not response or response[0] != 0x67:
            nrc = response[2] if response and len(response) > 2 else 0
            self._log(
                f"Security key rejected: {UDSProtocol.get_nrc_description(nrc)}",
                'error'
            )
            return False
        
        self._log("Security unlocked", 'success')
        return True
    
    def send_auth_payload(self) -> bool:
        """
        Send the proprietary authentication payload.
        
        This enables memory read/write operations.
        
        Returns:
            True if authentication successful
        """
        if not self.auth_payload:
            self._log("No auth payload loaded", 'error')
            return False
        
        # RequestDownload for auth
        request = UDSProtocol.build_request_download(
            self.AUTH_ADDRESS, self.AUTH_LENGTH
        )
        
        if not self.can.send_multiframe(self.can.TX_ID, request):
            self._log("RequestDownload send failed", 'error')
            return False
        
        response = self.can.recv_response()
        if not response or response[0] != 0x74:
            self._log("RequestDownload rejected", 'error')
            return False
        
        # TransferData with auth payload
        transfer = UDSProtocol.build_transfer_data(0x01, self.auth_payload)
        
        if not self.can.send_multiframe(self.can.TX_ID, transfer):
            self._log("TransferData send failed", 'error')
            return False
        
        response = self.can.recv_response(timeout=3.0)
        if not response or response[0] != 0x76:
            self._log("TransferData rejected", 'error')
            return False
        
        self.authenticated = True
        self._log("Authentication complete", 'success')
        return True
    
    def full_authenticate(self, capture_file: str = None) -> bool:
        """
        Perform full authentication sequence.
        
        1. Start extended session
        2. Security access Level 1
        3. Send auth payload
        
        Args:
            capture_file: Path to capture file (auto-detect if None)
            
        Returns:
            True if fully authenticated
        """
        # Find capture file if not specified
        if not capture_file:
            capture_file = self.find_capture_file()
            if not capture_file:
                self._log("No capture file found", 'error')
                return False
            self._log(f"Using capture: {capture_file}", 'info')
        
        # Load auth payload
        if not self.auth_payload:
            if not self.load_auth_payload(capture_file):
                return False
        
        # Start session
        self._log("Starting extended session...", 'info')
        self.start_session(UDS.DSC_EXTENDED)
        
        # Security access
        self._log("Performing security access...", 'info')
        if not self.security_access(level=1):
            return False
        
        # Send auth payload
        self._log("Sending auth payload...", 'info')
        if not self.send_auth_payload():
            return False
        
        return True

