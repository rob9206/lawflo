"""
UDS Protocol Module

Implements UDS (Unified Diagnostic Services) protocol
for Harley-Davidson ECU communication.
"""

from typing import Optional, Dict
from dataclasses import dataclass


# UDS Service IDs
class UDS:
    # Diagnostic Session Control
    DIAGNOSTIC_SESSION_CONTROL = 0x10
    DSC_DEFAULT = 0x01
    DSC_PROGRAMMING = 0x02
    DSC_EXTENDED = 0x03
    
    # ECU Reset
    ECU_RESET = 0x11
    RESET_HARD = 0x01
    RESET_KEY_OFF_ON = 0x02
    RESET_SOFT = 0x03
    
    # Security Access
    SECURITY_ACCESS = 0x27
    SA_REQUEST_SEED = 0x01
    SA_SEND_KEY = 0x02
    
    # Communication Control
    COMMUNICATION_CONTROL = 0x28
    
    # Tester Present
    TESTER_PRESENT = 0x3E
    
    # Control DTC Setting
    CONTROL_DTC_SETTING = 0x85
    
    # Read Data By ID
    READ_DATA_BY_ID = 0x22
    
    # Write Data By ID
    WRITE_DATA_BY_ID = 0x2E
    
    # Clear DTC
    CLEAR_DTC = 0x14
    
    # Read Memory By Address
    READ_MEMORY_BY_ADDRESS = 0x23
    
    # Request Download
    REQUEST_DOWNLOAD = 0x34
    
    # Request Upload
    REQUEST_UPLOAD = 0x35
    
    # Transfer Data
    TRANSFER_DATA = 0x36
    
    # Request Transfer Exit
    REQUEST_TRANSFER_EXIT = 0x37
    
    # Negative Response
    NEGATIVE_RESPONSE = 0x7F


# Negative Response Codes
NRC_CODES = {
    0x10: "General Reject",
    0x11: "Service Not Supported",
    0x12: "Sub-function Not Supported",
    0x13: "Incorrect Message Length/Format",
    0x14: "Response Too Long",
    0x21: "Busy Repeat Request",
    0x22: "Conditions Not Correct",
    0x24: "Request Sequence Error",
    0x25: "No Response From Subnet",
    0x26: "Failure Prevents Execution",
    0x31: "Request Out Of Range",
    0x33: "Security Access Denied",
    0x35: "Invalid Key",
    0x36: "Exceeded Number Of Attempts",
    0x37: "Required Time Delay Not Expired",
    0x70: "Upload Download Not Accepted",
    0x71: "Transfer Data Suspended",
    0x72: "General Programming Failure",
    0x73: "Wrong Block Sequence Counter",
    0x78: "Request Correctly Received - Response Pending",
    0x7E: "Sub-function Not Supported In Active Session",
    0x7F: "Service Not Supported In Active Session",
}


@dataclass
class UDSResponse:
    """Parsed UDS response."""
    success: bool
    service: int
    data: bytes
    nrc: Optional[int] = None
    
    @property
    def error_message(self) -> str:
        if self.nrc:
            return NRC_CODES.get(self.nrc, f"Unknown NRC 0x{self.nrc:02X}")
        return ""


class UDSProtocol:
    """
    UDS Protocol handler for Harley-Davidson ECUs.
    
    Provides message building and parsing for standard UDS services
    plus Harley-specific extensions.
    """
    
    @staticmethod
    def parse_response(data: bytes) -> UDSResponse:
        """
        Parse raw UDS response.
        
        Args:
            data: Raw response bytes
            
        Returns:
            Parsed UDSResponse object
        """
        if not data:
            return UDSResponse(
                success=False,
                service=0,
                data=b'',
                nrc=None
            )
        
        service = data[0]
        
        # Negative response
        if service == UDS.NEGATIVE_RESPONSE:
            nrc = data[2] if len(data) > 2 else 0
            return UDSResponse(
                success=False,
                service=data[1] if len(data) > 1 else 0,
                data=data,
                nrc=nrc
            )
        
        # Positive response (service + 0x40)
        return UDSResponse(
            success=True,
            service=service - 0x40,
            data=data[1:] if len(data) > 1 else b''
        )
    
    @staticmethod
    def build_session_control(session: int) -> bytes:
        """Build DiagnosticSessionControl request."""
        return bytes([UDS.DIAGNOSTIC_SESSION_CONTROL, session])
    
    @staticmethod
    def build_tester_present(response_required: bool = False) -> bytes:
        """Build TesterPresent request."""
        sub = 0x00 if response_required else 0x80
        return bytes([UDS.TESTER_PRESENT, sub])
    
    @staticmethod
    def build_security_seed(level: int = 1) -> bytes:
        """Build SecurityAccess request seed."""
        return bytes([UDS.SECURITY_ACCESS, level])
    
    @staticmethod
    def build_security_key(level: int, key: bytes) -> bytes:
        """Build SecurityAccess send key."""
        return bytes([UDS.SECURITY_ACCESS, level + 1]) + key
    
    @staticmethod
    def build_ecu_reset(reset_type: int = 0x01) -> bytes:
        """Build ECUReset request."""
        return bytes([UDS.ECU_RESET, reset_type])
    
    @staticmethod
    def build_clear_dtc() -> bytes:
        """Build ClearDTC request (all groups)."""
        return bytes([UDS.CLEAR_DTC, 0xFF, 0xFF, 0xFF])
    
    @staticmethod
    def build_read_did(did: int) -> bytes:
        """Build ReadDataByIdentifier request."""
        return bytes([UDS.READ_DATA_BY_ID, (did >> 8) & 0xFF, did & 0xFF])
    
    @staticmethod
    def build_request_download(address: int, length: int,
                               compression: int = 0,
                               encryption: int = 0) -> bytes:
        """
        Build RequestDownload request.
        
        Args:
            address: Memory address (4 bytes)
            length: Data length (4 bytes)
            compression: Compression method
            encryption: Encryption method
            
        Returns:
            UDS request bytes
        """
        data_format = (compression << 4) | encryption
        addr_len_format = 0x44  # 4 bytes address, 4 bytes length
        
        msg = bytes([UDS.REQUEST_DOWNLOAD, data_format, addr_len_format])
        msg += address.to_bytes(4, 'big')
        msg += length.to_bytes(4, 'big')
        return msg
    
    @staticmethod
    def build_request_upload(address: int, data_format: int = 0xB0) -> bytes:
        """
        Build RequestUpload request (Harley-specific format).
        
        Args:
            address: Memory address (4 bytes)
            data_format: Data format byte (0xA0 or 0xB0)
            
        Returns:
            UDS request bytes
        """
        msg = bytes([UDS.REQUEST_UPLOAD, data_format, 0x01])
        msg += address.to_bytes(4, 'big')
        return msg
    
    @staticmethod
    def build_transfer_data(block_num: int, data: bytes = b'') -> bytes:
        """
        Build TransferData request.
        
        Args:
            block_num: Block sequence counter (1-255)
            data: Data to transfer (for download)
            
        Returns:
            UDS request bytes
        """
        return bytes([UDS.TRANSFER_DATA, block_num]) + data
    
    @staticmethod
    def build_transfer_exit() -> bytes:
        """Build RequestTransferExit request."""
        return bytes([UDS.REQUEST_TRANSFER_EXIT])
    
    @staticmethod
    def get_nrc_description(nrc: int) -> str:
        """Get human-readable NRC description."""
        return NRC_CODES.get(nrc, f"Unknown NRC 0x{nrc:02X}")

