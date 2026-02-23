"""
Memory Operations Module

Handles ECU memory read and write operations
for Harley-Davidson ECUs.
"""

import time
import hashlib
from typing import Optional, Callable

from .can_interface import CANInterface
from .protocol import UDS, UDSProtocol
from .auth import Authenticator


# Memory Map Constants
class MemoryMap:
    """Harley ECU Memory Map."""
    
    # Calibration region (read)
    CAL_ADDRESS = 0x7D8000
    CAL_SIZE = 0x28000  # 160KB
    
    # Tune region (write)
    TUNE_ADDRESS = 0x00004000
    TUNE_SIZE = 0x4000  # 16KB
    
    # Tune offset within calibration dump
    TUNE_OFFSET = 0x1C000
    
    # Read format bytes
    READ_FORMAT_A0 = 0xA0
    READ_FORMAT_B0 = 0xB0
    
    # Block sizes
    READ_BLOCK_SIZE = 1024
    WRITE_BLOCK_SIZE = 256


class MemoryManager:
    """
    ECU Memory Manager.
    
    Provides high-level memory read/write operations with:
    - Automatic re-authentication
    - Progress callbacks
    - Retry logic
    - Checksum calculation
    """
    
    MAX_RETRIES = 5
    RETRY_DELAY = 0.3
    REAUTH_INTERVAL = 32  # Re-auth every N reads
    
    def __init__(self, can: CANInterface, auth: Authenticator):
        self.can = can
        self.auth = auth
        self.log_callback: Optional[Callable] = None
        self.progress_callback: Optional[Callable] = None
    
    def set_callbacks(self, log_func: Callable = None,
                      progress_func: Callable = None):
        self.log_callback = log_func
        self.progress_callback = progress_func
    
    def _log(self, message: str, level: str = 'info'):
        if self.log_callback:
            self.log_callback(message, level)
    
    def _progress(self, value: float):
        if self.progress_callback:
            self.progress_callback(value)
    
    @staticmethod
    def calculate_checksum(data: bytes) -> str:
        """Calculate SHA256 checksum of data."""
        return hashlib.sha256(data).hexdigest()
    
    def read_block(self, address: int,
                   format_byte: int = MemoryMap.READ_FORMAT_B0) -> Optional[bytes]:
        """
        Read a single block of memory using RequestUpload.
        
        Args:
            address: Memory address
            format_byte: Data format (0xA0 or 0xB0)
            
        Returns:
            Block data or None
        """
        request = UDSProtocol.build_request_upload(address, format_byte)
        
        for attempt in range(self.MAX_RETRIES):
            self.can.send_frame(self.can.TX_ID, request)
            response = self.can.recv_response(timeout=3.0)
            
            if response and response[0] == 0x75:
                return response[1:]
            
            time.sleep(self.RETRY_DELAY)
        
        return None
    
    def read_memory(self, address: int, length: int,
                    format_byte: int = MemoryMap.READ_FORMAT_B0) -> Optional[bytes]:
        """
        Read memory region with automatic re-authentication.
        
        Args:
            address: Start address
            length: Number of bytes to read
            format_byte: Data format byte
            
        Returns:
            Memory data or None
        """
        data = bytearray()
        current_addr = address
        read_count = 0
        
        while len(data) < length:
            # Re-authenticate periodically
            if read_count > 0 and read_count % self.REAUTH_INTERVAL == 0:
                self._log("Re-authenticating...", 'info')
                if not self.auth.full_authenticate():
                    self._log("Re-authentication failed", 'error')
                    return None
            
            # Read block
            block = self.read_block(current_addr, format_byte)
            
            if not block:
                self._log(f"Read failed at 0x{current_addr:X}", 'error')
                return None
            
            data.extend(block)
            current_addr += len(block)
            read_count += 1
            
            self._progress(len(data) / length * 100)
        
        return bytes(data[:length])
    
    def read_calibration(self) -> Optional[bytes]:
        """
        Read full calibration region (160KB).
        
        Returns:
            Calibration data or None
        """
        self._log(f"Reading calibration: 0x{MemoryMap.CAL_ADDRESS:X} "
                  f"({MemoryMap.CAL_SIZE} bytes)", 'info')
        
        return self.read_memory(
            MemoryMap.CAL_ADDRESS,
            MemoryMap.CAL_SIZE,
            MemoryMap.READ_FORMAT_B0
        )
    
    def read_tune(self) -> Optional[bytes]:
        """
        Read tune region from calibration and extract 16KB tune.
        
        Returns:
            Tune data (16KB) or None
        """
        cal_data = self.read_calibration()
        
        if not cal_data:
            return None
        
        return self.extract_tune(cal_data)
    
    @staticmethod
    def extract_tune(calibration: bytes) -> Optional[bytes]:
        """
        Extract 16KB tune from calibration data.
        
        Args:
            calibration: Full calibration data (160KB)
            
        Returns:
            Tune data (16KB) or None
        """
        if len(calibration) < MemoryMap.TUNE_OFFSET + MemoryMap.TUNE_SIZE:
            return None
        
        return calibration[
            MemoryMap.TUNE_OFFSET:
            MemoryMap.TUNE_OFFSET + MemoryMap.TUNE_SIZE
        ]
    
    def write_block(self, block_num: int, data: bytes) -> bool:
        """
        Write a single block of data using TransferData.
        
        Args:
            block_num: Block sequence number
            data: Block data (256 bytes)
            
        Returns:
            True if successful
        """
        request = UDSProtocol.build_transfer_data(block_num, data)
        
        for attempt in range(self.MAX_RETRIES):
            if not self.can.send_multiframe(self.can.TX_ID, request):
                time.sleep(self.RETRY_DELAY)
                continue
            
            response = self.can.recv_response()
            if response and response[0] == 0x76:
                return True
            
            self._log(f"Block {block_num} retry {attempt+1}", 'warning')
            time.sleep(self.RETRY_DELAY)
        
        return False
    
    def write_tune(self, tune_data: bytes) -> bool:
        """
        Write tune data to ECU.
        
        Args:
            tune_data: Tune data (must be 16KB)
            
        Returns:
            True if successful
        """
        if len(tune_data) != MemoryMap.TUNE_SIZE:
            self._log(
                f"Invalid tune size: {len(tune_data)} "
                f"(expected {MemoryMap.TUNE_SIZE})",
                'error'
            )
            return False
        
        # RequestDownload
        request = UDSProtocol.build_request_download(
            MemoryMap.TUNE_ADDRESS,
            MemoryMap.TUNE_SIZE
        )
        
        if not self.can.send_multiframe(self.can.TX_ID, request):
            self._log("RequestDownload send failed", 'error')
            return False
        
        response = self.can.recv_response()
        if not response or response[0] != 0x74:
            self._log("RequestDownload rejected", 'error')
            return False
        
        self._log("Download accepted, writing blocks...", 'info')
        
        # Write blocks
        offset = 0
        block_num = 1
        
        while offset < len(tune_data):
            chunk = tune_data[offset:offset + MemoryMap.WRITE_BLOCK_SIZE]
            
            # Pad if needed
            if len(chunk) < MemoryMap.WRITE_BLOCK_SIZE:
                chunk = chunk + bytes(MemoryMap.WRITE_BLOCK_SIZE - len(chunk))
            
            if not self.write_block(block_num, chunk):
                self._log(f"Block {block_num} write failed", 'error')
                return False
            
            offset += MemoryMap.WRITE_BLOCK_SIZE
            block_num = (block_num % 255) + 1
            
            self._progress(offset / len(tune_data) * 100)
        
        self._log("All blocks written successfully", 'success')
        return True
    
    def ecu_reset(self, reset_type: int = UDS.RESET_HARD):
        """
        Reset ECU.
        
        Args:
            reset_type: Reset type (default: hard reset)
        """
        request = UDSProtocol.build_ecu_reset(reset_type)
        self.can.send_frame(self.can.TX_ID, request)
        time.sleep(1.0)
    
    def clear_dtc(self):
        """Clear all DTCs."""
        request = UDSProtocol.build_clear_dtc()
        self.can.send_broadcast(request)
        time.sleep(0.5)
    
    def verify_write(self, expected_data: bytes) -> bool:
        """
        Verify written data by reading back.
        
        Args:
            expected_data: Expected tune data
            
        Returns:
            True if data matches
        """
        self._log("Verifying write...", 'info')
        
        # Re-authenticate
        if not self.auth.full_authenticate():
            self._log("Verification auth failed", 'error')
            return False
        
        # Read back
        actual_data = self.read_tune()
        
        if not actual_data:
            self._log("Verification read failed", 'error')
            return False
        
        if actual_data == expected_data:
            self._log("Verification PASSED", 'success')
            return True
        
        # Count differences
        diff_count = sum(1 for a, b in zip(actual_data, expected_data) if a != b)
        self._log(f"Verification FAILED: {diff_count} bytes differ", 'error')
        return False

