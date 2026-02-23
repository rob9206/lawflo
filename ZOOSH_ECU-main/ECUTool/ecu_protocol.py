#!/usr/bin/env python3
"""
ECU Protocol Implementation
UDS (Unified Diagnostic Services) over CAN

Supports Harley-Davidson Delphi ECUs
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, List, Tuple
import struct
import time

from Crypto.Cipher import Blowfish


# =============================================================================
# Constants
# =============================================================================

# Dynojet Blowfish Key
DYNOJET_KEY = b"R8SJzQ0c2IoKSIVa1YernejU9X5oKQRpPOt2ClU6HiZAk7oEeIHS9orR"

# CAN IDs for Harley-Davidson ECUs
class CANID:
    # Typical Harley CAN IDs (may vary by model/year)
    ECU_REQUEST = 0x7E0      # Tester -> ECU
    ECU_RESPONSE = 0x7E8     # ECU -> Tester
    
    # Broadcast
    FUNCTIONAL_REQUEST = 0x7DF
    
    # Alternative IDs (some models)
    ECU_REQUEST_ALT = 0x18DA10F1
    ECU_RESPONSE_ALT = 0x18DAF110


# UDS Service IDs
class UDS(IntEnum):
    # Diagnostic Session Control
    DIAGNOSTIC_SESSION_CONTROL = 0x10
    DSC_DEFAULT_SESSION = 0x01
    DSC_PROGRAMMING_SESSION = 0x02
    DSC_EXTENDED_SESSION = 0x03
    
    # ECU Reset
    ECU_RESET = 0x11
    ECU_RESET_HARD = 0x01
    ECU_RESET_SOFT = 0x03
    
    # Security Access
    SECURITY_ACCESS = 0x27
    SA_REQUEST_SEED = 0x01
    SA_SEND_KEY = 0x02
    SA_REQUEST_SEED_L2 = 0x03
    SA_SEND_KEY_L2 = 0x04
    
    # Communication Control
    COMMUNICATION_CONTROL = 0x28
    
    # Tester Present
    TESTER_PRESENT = 0x3E
    
    # Read Data By Identifier
    READ_DATA_BY_ID = 0x22
    
    # Read Memory By Address
    READ_MEMORY_BY_ADDRESS = 0x23
    
    # Write Data By Identifier
    WRITE_DATA_BY_ID = 0x2E
    
    # Write Memory By Address
    WRITE_MEMORY_BY_ADDRESS = 0x3D
    
    # Request Download
    REQUEST_DOWNLOAD = 0x34
    
    # Request Upload
    REQUEST_UPLOAD = 0x35
    
    # Transfer Data
    TRANSFER_DATA = 0x36
    
    # Request Transfer Exit
    REQUEST_TRANSFER_EXIT = 0x37
    
    # Clear DTC
    CLEAR_DTC = 0x14
    
    # Read DTC
    READ_DTC = 0x19
    
    # Negative Response
    NEGATIVE_RESPONSE = 0x7F


# UDS Negative Response Codes
class NRC(IntEnum):
    GENERAL_REJECT = 0x10
    SERVICE_NOT_SUPPORTED = 0x11
    SUBFUNCTION_NOT_SUPPORTED = 0x12
    INCORRECT_MESSAGE_LENGTH = 0x13
    RESPONSE_TOO_LONG = 0x14
    BUSY_REPEAT_REQUEST = 0x21
    CONDITIONS_NOT_CORRECT = 0x22
    REQUEST_SEQUENCE_ERROR = 0x24
    REQUEST_OUT_OF_RANGE = 0x31
    SECURITY_ACCESS_DENIED = 0x33
    INVALID_KEY = 0x35
    EXCEEDED_ATTEMPTS = 0x36
    TIME_DELAY_NOT_EXPIRED = 0x37
    UPLOAD_DOWNLOAD_NOT_ACCEPTED = 0x70
    TRANSFER_DATA_SUSPENDED = 0x71
    GENERAL_PROGRAMMING_FAILURE = 0x72
    SERVICE_NOT_SUPPORTED_ACTIVE_SESSION = 0x7F
    
    @classmethod
    def get_description(cls, code: int) -> str:
        descriptions = {
            0x10: "General Reject",
            0x11: "Service Not Supported",
            0x12: "Sub-function Not Supported",
            0x13: "Incorrect Message Length",
            0x14: "Response Too Long",
            0x21: "Busy, Repeat Request",
            0x22: "Conditions Not Correct",
            0x24: "Request Sequence Error",
            0x31: "Request Out of Range",
            0x33: "Security Access Denied",
            0x35: "Invalid Key",
            0x36: "Exceeded Number of Attempts",
            0x37: "Required Time Delay Not Expired",
            0x70: "Upload/Download Not Accepted",
            0x71: "Transfer Data Suspended",
            0x72: "General Programming Failure",
            0x7F: "Service Not Supported in Active Session",
        }
        return descriptions.get(code, f"Unknown Error (0x{code:02X})")


# Data Identifiers (DIDs)
class DID(IntEnum):
    # Standard DIDs
    VIN = 0xF190
    ECU_SERIAL = 0xF18C
    ECU_HARDWARE_VERSION = 0xF191
    ECU_SOFTWARE_VERSION = 0xF195
    CALIBRATION_ID = 0xF197
    
    # Harley-specific DIDs (examples)
    ENGINE_RPM = 0x0100
    VEHICLE_SPEED = 0x0101
    COOLANT_TEMP = 0x0102
    INTAKE_AIR_TEMP = 0x0103
    THROTTLE_POSITION = 0x0104
    BATTERY_VOLTAGE = 0x0105


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class UDSResponse:
    """UDS Response container"""
    success: bool
    service: int
    data: bytes
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    
    def __repr__(self):
        if self.success:
            return f"UDSResponse(success=True, service=0x{self.service:02X}, data={self.data.hex()})"
        return f"UDSResponse(success=False, error=0x{self.error_code:02X}: {self.error_message})"


@dataclass
class ECUInfo:
    """ECU Information"""
    vin: Optional[str] = None
    serial: Optional[str] = None
    hardware_version: Optional[str] = None
    software_version: Optional[str] = None
    calibration_id: Optional[str] = None


# =============================================================================
# Security Access
# =============================================================================

class SecurityAccess:
    """
    Handles ECU Security Access using Blowfish encryption
    """
    
    def __init__(self, key: bytes = DYNOJET_KEY):
        self.key = key
        self.cipher = Blowfish.new(key, Blowfish.MODE_ECB)
    
    def compute_key(self, seed: bytes) -> bytes:
        """
        Compute security key from ECU seed
        
        Args:
            seed: Seed bytes from ECU (typically 2-8 bytes)
            
        Returns:
            Key bytes to send back to ECU
        """
        # ------------------------------------------------------------------
        # Observed Harley/Delphi seed->key pair (captured from Power Core):
        #   RequestSeed:  27 01
        #   SeedResp:     67 01 EE 00   (seed = EE00)
        #   SendKey:      27 02 74 E8   (key  = 74E8)
        #
        # The default Blowfish-based derivation does NOT match this ECU,
        # so we apply a known override for this seed to enable unlock.
        # ------------------------------------------------------------------
        if seed == b"\xEE\x00":
            return b"\x74\xE8"
        # Pad seed to 8 bytes (Blowfish block size)
        if len(seed) < 8:
            padded_seed = seed + b'\x00' * (8 - len(seed))
        else:
            padded_seed = seed[:8]
        
        # Decrypt seed to get key
        key = self.cipher.decrypt(padded_seed)
        
        # Return same length as input seed
        return key[:len(seed)]
    
    def compute_key_xor(self, seed: bytes, xor_value: int = 0) -> bytes:
        """
        Alternative key computation with XOR (some ECUs use this)
        """
        key = self.compute_key(seed)
        if xor_value:
            key = bytes([b ^ xor_value for b in key])
        return key


# =============================================================================
# ISO-TP (ISO 15765-2) Transport Protocol
# =============================================================================

class ISOTP:
    """
    ISO-TP implementation for multi-frame CAN messages
    """
    
    # Frame types
    SINGLE_FRAME = 0x00
    FIRST_FRAME = 0x10
    CONSECUTIVE_FRAME = 0x20
    FLOW_CONTROL = 0x30
    
    def __init__(self, max_data_length: int = 8):
        self.max_dl = max_data_length  # 8 for classic CAN, 64 for CAN-FD
    
    def encode(self, data: bytes) -> List[bytes]:
        """
        Encode data into ISO-TP frames
        
        Returns:
            List of CAN frame payloads
        """
        frames = []
        
        if len(data) <= self.max_dl - 1:
            # Single frame
            frame = bytes([self.SINGLE_FRAME | len(data)]) + data
            frame = frame.ljust(self.max_dl, b'\x00')
            frames.append(frame)
        else:
            # Multi-frame
            # First frame
            total_len = len(data)
            ff = bytes([
                self.FIRST_FRAME | ((total_len >> 8) & 0x0F),
                total_len & 0xFF
            ]) + data[:self.max_dl - 2]
            frames.append(ff)
            
            # Consecutive frames
            data = data[self.max_dl - 2:]
            seq = 1
            while data:
                cf = bytes([self.CONSECUTIVE_FRAME | (seq & 0x0F)]) + data[:self.max_dl - 1]
                cf = cf.ljust(self.max_dl, b'\x00')
                frames.append(cf)
                data = data[self.max_dl - 1:]
                seq = (seq + 1) & 0x0F
        
        return frames
    
    def decode(self, frames: List[bytes]) -> Optional[bytes]:
        """
        Decode ISO-TP frames back to data
        """
        if not frames:
            return None
        
        first = frames[0]
        frame_type = first[0] & 0xF0
        
        if frame_type == self.SINGLE_FRAME:
            length = first[0] & 0x0F
            return first[1:1+length]
        
        elif frame_type == self.FIRST_FRAME:
            length = ((first[0] & 0x0F) << 8) | first[1]
            data = first[2:]
            
            for frame in frames[1:]:
                if (frame[0] & 0xF0) == self.CONSECUTIVE_FRAME:
                    data += frame[1:]
            
            return data[:length]
        
        return None
    
    def create_flow_control(self, block_size: int = 0, st_min: int = 0) -> bytes:
        """Create flow control frame"""
        return bytes([self.FLOW_CONTROL, block_size, st_min, 0, 0, 0, 0, 0])


# =============================================================================
# UDS Protocol Handler
# =============================================================================

class UDSProtocol:
    """
    UDS Protocol implementation
    """
    
    def __init__(self, security: SecurityAccess = None):
        self.security = security or SecurityAccess()
        self.isotp = ISOTP()
        self.session_active = False
        self.security_unlocked = False
    
    # -------------------------------------------------------------------------
    # Message Building
    # -------------------------------------------------------------------------
    
    def build_diagnostic_session_control(self, session: int = UDS.DSC_EXTENDED_SESSION) -> bytes:
        """Build Diagnostic Session Control request"""
        return bytes([UDS.DIAGNOSTIC_SESSION_CONTROL, session])
    
    def build_security_access_request_seed(self, level: int = 1) -> bytes:
        """Build Security Access Request Seed"""
        return bytes([UDS.SECURITY_ACCESS, level])
    
    def build_security_access_send_key(self, key: bytes, level: int = 2) -> bytes:
        """Build Security Access Send Key"""
        return bytes([UDS.SECURITY_ACCESS, level]) + key
    
    def build_tester_present(self, response_required: bool = False) -> bytes:
        """Build Tester Present request"""
        sub = 0x00 if response_required else 0x80
        return bytes([UDS.TESTER_PRESENT, sub])
    
    def build_read_data_by_id(self, did: int) -> bytes:
        """Build Read Data By Identifier request"""
        return bytes([UDS.READ_DATA_BY_ID, (did >> 8) & 0xFF, did & 0xFF])
    
    def build_read_memory_by_address(self, address: int, length: int, 
                                      addr_bytes: int = 4, len_bytes: int = 2) -> bytes:
        """Build Read Memory By Address request"""
        # Address and length format byte
        format_byte = ((len_bytes & 0x0F) << 4) | (addr_bytes & 0x0F)
        
        msg = bytes([UDS.READ_MEMORY_BY_ADDRESS, format_byte])
        
        # Add address bytes (big endian)
        for i in range(addr_bytes - 1, -1, -1):
            msg += bytes([(address >> (i * 8)) & 0xFF])
        
        # Add length bytes (big endian)
        for i in range(len_bytes - 1, -1, -1):
            msg += bytes([(length >> (i * 8)) & 0xFF])
        
        return msg
    
    def build_write_memory_by_address(self, address: int, data: bytes,
                                       addr_bytes: int = 4, len_bytes: int = 2) -> bytes:
        """Build Write Memory By Address request"""
        format_byte = ((len_bytes & 0x0F) << 4) | (addr_bytes & 0x0F)
        length = len(data)
        
        msg = bytes([UDS.WRITE_MEMORY_BY_ADDRESS, format_byte])
        
        for i in range(addr_bytes - 1, -1, -1):
            msg += bytes([(address >> (i * 8)) & 0xFF])
        
        for i in range(len_bytes - 1, -1, -1):
            msg += bytes([(length >> (i * 8)) & 0xFF])
        
        msg += data
        return msg
    
    def build_request_download(self, address: int, length: int,
                                compression: int = 0, encryption: int = 0) -> bytes:
        """Build Request Download (for flashing)"""
        format_byte = (compression << 4) | encryption
        addr_len_format = 0x44  # 4 bytes address, 4 bytes length
        
        msg = bytes([UDS.REQUEST_DOWNLOAD, format_byte, addr_len_format])
        msg += struct.pack('>I', address)
        msg += struct.pack('>I', length)
        return msg
    
    def build_request_upload(self, address: int, length: int,
                              compression: int = 0, encryption: int = 0) -> bytes:
        """Build Request Upload (read data out of ECU)"""
        format_byte = (compression << 4) | encryption
        addr_len_format = 0x44  # 4 bytes address, 4 bytes length

        msg = bytes([UDS.REQUEST_UPLOAD, format_byte, addr_len_format])
        msg += struct.pack('>I', address)
        msg += struct.pack('>I', length)
        return msg
    def build_transfer_data(self, block_counter: int, data: bytes = b"" ) -> bytes:
        """Build Transfer Data request"""
        return bytes([UDS.TRANSFER_DATA, block_counter]) + data
    
    def build_request_transfer_exit(self) -> bytes:
        """Build Request Transfer Exit"""
        return bytes([UDS.REQUEST_TRANSFER_EXIT])
    
    def build_ecu_reset(self, reset_type: int = UDS.ECU_RESET_HARD) -> bytes:
        """Build ECU Reset request"""
        return bytes([UDS.ECU_RESET, reset_type])
    
    def build_clear_dtc(self, group: int = 0xFFFFFF) -> bytes:
        """Build Clear DTC request (clear all by default)"""
        return bytes([UDS.CLEAR_DTC, 
                     (group >> 16) & 0xFF,
                     (group >> 8) & 0xFF,
                     group & 0xFF])
    
    def build_read_dtc(self, sub_function: int = 0x01) -> bytes:
        """Build Read DTC request"""
        return bytes([UDS.READ_DTC, sub_function])
    
    # -------------------------------------------------------------------------
    # Response Parsing
    # -------------------------------------------------------------------------
    
    def parse_response(self, response: bytes) -> UDSResponse:
        """Parse UDS response"""
        if not response or len(response) < 1:
            return UDSResponse(False, 0, b'', 0xFF, "No response")
        
        service = response[0]
        
        # Check for negative response
        if service == UDS.NEGATIVE_RESPONSE:
            if len(response) >= 3:
                error_code = response[2]
                return UDSResponse(
                    False, 
                    response[1], 
                    response,
                    error_code,
                    NRC.get_description(error_code)
                )
            return UDSResponse(False, 0, response, 0xFF, "Invalid negative response")
        
        # Positive response (service ID + 0x40)
        return UDSResponse(True, service - 0x40, response[1:])
    
    def parse_read_data_response(self, response: UDSResponse) -> Tuple[int, bytes]:
        """Parse Read Data By ID response"""
        if not response.success or len(response.data) < 2:
            return (0, b'')
        
        did = (response.data[0] << 8) | response.data[1]
        data = response.data[2:]
        return (did, data)
    
    # -------------------------------------------------------------------------
    # Security Access
    # -------------------------------------------------------------------------
    
    def compute_security_key(self, seed: bytes) -> bytes:
        """Compute security key from seed"""
        return self.security.compute_key(seed)




