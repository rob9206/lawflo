#!/usr/bin/env python3
"""
ECU Communication Tool

High-level interface for ECU communication, flash reading/writing,
and diagnostics for Harley-Davidson and similar vehicles.
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple, Callable
import time
import struct

from ecu_protocol import (
    UDSProtocol, UDSResponse, SecurityAccess, ISOTP, ECUInfo,
    CANID, UDS, NRC, DID, DYNOJET_KEY
)
from can_interface import CANInterface, CANMessage, create_interface


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class FlashRegion:
    """Flash memory region"""
    name: str
    start_address: int
    size: int
    description: str = ""


@dataclass  
class DTCInfo:
    """Diagnostic Trouble Code"""
    code: str
    status: int
    description: str = ""


# =============================================================================
# ECU Tool Class
# =============================================================================

class ECUTool:
    """
    High-level ECU communication tool
    
    Usage:
        tool = ECUTool()
        tool.connect("pcan:PCAN_USBBUS1")
        tool.start_session()
        tool.security_access()
        data = tool.read_memory(0x00000, 0x1000)
        tool.disconnect()
    """
    
    # Common flash regions for Harley Delphi ECUs
    FLASH_REGIONS = [
        FlashRegion("Bootloader", 0x00000, 0x4000, "Boot code (protected)"),
        FlashRegion("Calibration", 0x10000, 0x10000, "Tune/calibration data"),
        FlashRegion("Program", 0x20000, 0x60000, "Main program"),
    ]
    
    def __init__(self, request_id: int = CANID.ECU_REQUEST, 
                 response_id: int = CANID.ECU_RESPONSE):
        self.can: Optional[CANInterface] = None
        self.protocol = UDSProtocol()
        self.isotp = ISOTP()
        
        self.request_id = request_id
        self.response_id = response_id
        
        self.connected = False
        self.session_active = False
        self.security_unlocked = False
        
        # Callbacks
        self.on_progress: Optional[Callable[[int, int, str], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None
        
        # Timing
        self.timeout = 2.0
        self.p2_timeout = 0.05  # Inter-frame delay
    
    def log(self, message: str) -> None:
        """Log a message"""
        if self.on_log:
            self.on_log(message)
        else:
            print(message)
    
    def progress(self, current: int, total: int, message: str = "") -> None:
        """Report progress"""
        if self.on_progress:
            self.on_progress(current, total, message)
    
    # =========================================================================
    # Connection
    # =========================================================================
    
    def connect(self, interface: str = "simulated:test") -> bool:
        """
        Connect to CAN interface
        
        Args:
            interface: Interface string (e.g., "pcan:PCAN_USBBUS1", "simulated:test")
        """
        try:
            self.can = create_interface(interface)
            if self.can.connect():
                self.connected = True
                self.log(f"Connected to {interface}")
                return True
            else:
                self.log(f"Failed to connect to {interface}")
                return False
        except Exception as e:
            self.log(f"Connection error: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from CAN interface"""
        if self.can:
            self.can.disconnect()
        self.connected = False
        self.session_active = False
        self.security_unlocked = False
        self.log("Disconnected")
    
    # =========================================================================
    # Low-Level Communication
    # =========================================================================
    
    def send_raw(self, data: bytes) -> bool:
        """Send raw CAN data (handles ISO-TP framing)"""
        if not self.can or not self.connected:
            return False
        
        frames = self.isotp.encode(data)
        
        for i, frame in enumerate(frames):
            msg = CANMessage(arbitration_id=self.request_id, data=frame)
            if not self.can.send(msg):
                return False
            
            # Wait for flow control after first frame of multi-frame
            if i == 0 and len(frames) > 1:
                fc = self.can.receive_filtered(self.response_id, timeout=1.0)
                if not fc or (fc.data[0] & 0xF0) != 0x30:
                    self.log("No flow control received")
                    return False
            
            time.sleep(self.p2_timeout)
        
        return True
    
    def receive_raw(self, timeout: float = None) -> Optional[bytes]:
        """Receive raw data (handles ISO-TP reassembly)"""
        if not self.can or not self.connected:
            return None
        
        timeout = timeout or self.timeout
        frames = []
        expected_frames = 1
        
        start = time.time()
        while time.time() - start < timeout:
            msg = self.can.receive_filtered(self.response_id, timeout=0.5)
            
            if not msg:
                continue
            
            frame_type = msg.data[0] & 0xF0
            
            if frame_type == 0x00:  # Single frame
                length = msg.data[0] & 0x0F
                return bytes(msg.data[1:1+length])
            
            elif frame_type == 0x10:  # First frame
                total_length = ((msg.data[0] & 0x0F) << 8) | msg.data[1]
                frames.append(bytes(msg.data))
                expected_frames = 1 + (total_length - 6 + 6) // 7
                
                # Send flow control
                fc = CANMessage(
                    arbitration_id=self.request_id,
                    data=bytes([0x30, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                )
                self.can.send(fc)
            
            elif frame_type == 0x20:  # Consecutive frame
                frames.append(bytes(msg.data))
                
                if len(frames) >= expected_frames:
                    return self.isotp.decode(frames)
        
        return None
    
    def send_uds(self, request: bytes) -> UDSResponse:
        """Send UDS request and get response"""
        if not self.send_raw(request):
            return UDSResponse(False, request[0], b'', 0xFF, "Send failed")
        
        response = self.receive_raw()
        if not response:
            return UDSResponse(False, request[0], b'', 0xFF, "No response")
        
        return self.protocol.parse_response(response)
    
    # =========================================================================
    # Session Control
    # =========================================================================
        def start_session(self, session_type: int = UDS.DSC_EXTENDED_SESSION) -> bool:
        """
        Start diagnostic session.

        Some ECUs are picky about the initial session. If the preferred session
        doesn't respond, we fall back through common session types.

        Args:
            session_type: Preferred session type (default: extended)
        """
        # Try preferred first, then common fallbacks.
        candidates = []
        for st in [session_type, UDS.DSC_DEFAULT_SESSION, UDS.DSC_EXTENDED_SESSION, UDS.DSC_PROGRAMMING_SESSION]:
            if st not in candidates:
                candidates.append(st)

        last_error = None
        for st in candidates:
            self.log(f"Starting session 0x{st:02X}...")
            request = self.protocol.build_diagnostic_session_control(st)
            response = self.send_uds(request)

            if response.success:
                self.session_active = True
                self.log("Session started successfully")
                return True

            last_error = response.error_message
            # Small delay before trying next candidate
            time.sleep(0.1)

        self.log(f"Session start failed: {last_error}")
        return False
    def tester_present(self) -> bool:
        """Send Tester Present to keep session alive"""
        request = self.protocol.build_tester_present(response_required=False)
        self.send_raw(request)
        return True
    
    # =========================================================================
    # Security Access
    # =========================================================================
    
    def security_access(self, level: int = 1) -> bool:
        """
        Perform security access using Blowfish key
        
        Args:
            level: Security level (1 = standard, 3 = extended)
        """
        self.log(f"Requesting security access level {level}...")
        
        # Step 1: Request seed
        request = self.protocol.build_security_access_request_seed(level)
        response = self.send_uds(request)
        
        if not response.success:
            self.log(f"Seed request failed: {response.error_message}")
            return False
        
        seed = response.data[1:]  # Skip sub-function byte
        self.log(f"Received seed: {seed.hex()}")
        
        # Step 2: Compute key
        key = self.protocol.compute_security_key(seed)
        self.log(f"Computed key: {key.hex()}")
        
        # Step 3: Send key
        request = self.protocol.build_security_access_send_key(key, level + 1)
        response = self.send_uds(request)
        
        if response.success:
            self.security_unlocked = True
            self.log("Security access granted!")
            return True
        else:
            self.log(f"Security access denied: {response.error_message}")
            return False
    
    # =========================================================================
    # Data Reading
    # =========================================================================
    
    def read_data_by_id(self, did: int) -> Tuple[bool, bytes]:
        """
        Read data by identifier
        
        Args:
            did: Data Identifier (e.g., 0xF190 for VIN)
            
        Returns:
            (success, data)
        """
        request = self.protocol.build_read_data_by_id(did)
        response = self.send_uds(request)
        
        if response.success:
            _, data = self.protocol.parse_read_data_response(response)
            return True, data
        
        return False, b''
    
    def read_vin(self) -> Optional[str]:
        """Read Vehicle Identification Number"""
        success, data = self.read_data_by_id(DID.VIN)
        if success and data:
            return data.decode('ascii', errors='ignore').strip('\x00')
        return None
    
    def read_ecu_info(self) -> ECUInfo:
        """Read all ECU information"""
        info = ECUInfo()
        
        success, data = self.read_data_by_id(DID.VIN)
        if success:
            info.vin = data.decode('ascii', errors='ignore').strip('\x00')
        
        success, data = self.read_data_by_id(DID.ECU_SERIAL)
        if success:
            info.serial = data.decode('ascii', errors='ignore').strip('\x00')
        
        success, data = self.read_data_by_id(DID.ECU_HARDWARE_VERSION)
        if success:
            info.hardware_version = data.decode('ascii', errors='ignore').strip('\x00')
        
        success, data = self.read_data_by_id(DID.ECU_SOFTWARE_VERSION)
        if success:
            info.software_version = data.decode('ascii', errors='ignore').strip('\x00')
        
        success, data = self.read_data_by_id(DID.CALIBRATION_ID)
        if success:
            info.calibration_id = data.decode('ascii', errors='ignore').strip('\x00')
        
        return info
    
    # =========================================================================
    # Memory Operations
    # =========================================================================
    
    def read_memory(self, address: int, length: int, 
                    chunk_size: int = 256, addr_bytes: int = 4, len_bytes: int = 2) -> Optional[bytes]:
        """
        Read ECU memory
        
        Args:
            address: Start address
            length: Number of bytes to read
            chunk_size: Bytes per request (max ~256 for CAN)
            
        Returns:
            Memory contents or None on error
        """
        if not self.security_unlocked:
            self.log("Security access required for memory read")
            return None
        
        self.log(f"Reading memory: 0x{address:08X} - 0x{address+length:08X}")
        
        data = bytearray()
        offset = 0
        
        while offset < length:
            chunk_len = min(chunk_size, length - offset)
            current_addr = address + offset
            
            request = self.protocol.build_read_memory_by_address(current_addr, chunk_len, addr_bytes=addr_bytes, len_bytes=len_bytes)
            response = self.send_uds(request)
            
            if response.success:
                data.extend(response.data)
                offset += chunk_len
                self.progress(offset, length, f"Reading 0x{current_addr:08X}")
            else:
                self.log(f"Read failed at 0x{current_addr:08X}: {response.error_message}")
                return None
            
            # Keep session alive
            if offset % 4096 == 0:
                self.tester_present()
        
        self.log(f"Read complete: {len(data)} bytes")
        return bytes(data)
    
    def read_memory_upload(self, address: int, length: int) -> Optional[bytes]:
        """Read ECU memory using RequestUpload/TransferData instead of 0x23."""
        if not self.security_unlocked:
            self.log("Security access required for upload read")
            return None

        self.log(f"RequestUpload read: 0x{address:08X} - 0x{address+length:08X} ({length} bytes)")

        # Step 1: RequestUpload
        request = self.protocol.build_request_upload(address, length)
        response = self.send_uds(request)
        if not response.success:
            self.log(f"RequestUpload failed: {response.error_message}")
            return None

        # Try to parse max block size from positive response
        max_block = 256
        if len(response.data) >= 2:
            format_byte = response.data[0]
            len_bytes = (format_byte >> 4) & 0x0F
            if len_bytes > 0 and len(response.data) >= 1 + len_bytes:
                try:
                    max_block = int.from_bytes(response.data[1:1+len_bytes], 'big')
                except Exception:
                    max_block = 256

        # Step 2: TransferData requests (no payload) and collect 0x76 responses
        data = bytearray()
        block_counter = 1

        self.log(f"Uploading data (max block: {max_block})...")

        while len(data) < length:
            # For upload, request next block by sending only the block counter
            request = self.protocol.build_transfer_data(block_counter)
            response = self.send_uds(request)

            if not response.success:
                self.log(f"Upload failed at block {block_counter}: {response.error_message}")
                return None

            # response.data begins with block counter then data
            if not response.data:
                self.log(f"Upload returned empty block at {block_counter}")
                break

            resp_block = response.data[0]
            chunk = response.data[1:]

            if resp_block != block_counter:
                self.log(f"Warning: block counter mismatch (sent {block_counter}, got {resp_block})")

            if chunk:
                data.extend(chunk)
                self.progress(min(len(data), length), length, f"Upload block {block_counter}")
            else:
                # No chunk data, stop
                break

            block_counter = (block_counter + 1) & 0xFF

            # Keep session alive
            if len(data) % 4096 == 0:
                self.tester_present()

        # Step 3: RequestTransferExit
        request = self.protocol.build_request_transfer_exit()
        _ = self.send_uds(request)

        if not data:
            return None

        self.log(f"Upload complete: {len(data[:length])} bytes")
        return bytes(data[:length])
    def write_memory(self, address: int, data: bytes,
                     chunk_size: int = 128) -> bool:
        """
        Write ECU memory
        
        Args:
            address: Start address
            data: Data to write
            chunk_size: Bytes per request
        """
        if not self.security_unlocked:
            self.log("Security access required for memory write")
            return False
        
        self.log(f"Writing memory: 0x{address:08X}, {len(data)} bytes")
        
        offset = 0
        while offset < len(data):
            chunk = data[offset:offset + chunk_size]
            current_addr = address + offset
            
            request = self.protocol.build_write_memory_by_address(current_addr, chunk)
            response = self.send_uds(request)
            
            if response.success:
                offset += len(chunk)
                self.progress(offset, len(data), f"Writing 0x{current_addr:08X}")
            else:
                self.log(f"Write failed at 0x{current_addr:08X}: {response.error_message}")
                return False
            
            if offset % 4096 == 0:
                self.tester_present()
        
        self.log(f"Write complete: {len(data)} bytes")
        return True
    
    # =========================================================================
    # Flash Operations
    # =========================================================================
    
    def read_flash_region(self, region: FlashRegion) -> Optional[bytes]:
        """Read a flash memory region"""
        self.log(f"Reading flash region: {region.name}")
        return self.read_memory(region.start_address, region.size)
    
    def read_calibration(self) -> Optional[bytes]:
        """Read calibration/tune data"""
        for region in self.FLASH_REGIONS:
            if region.name == "Calibration":
                return self.read_flash_region(region)
        return None
    
    def dump_flash(self, filename: str) -> bool:
        """
        Dump entire readable flash to file
        
        Args:
            filename: Output filename
        """
        self.log(f"Dumping flash to {filename}")
        
        all_data = bytearray()
        
        for region in self.FLASH_REGIONS:
            if "protected" in region.description.lower():
                self.log(f"Skipping protected region: {region.name}")
                continue
            
            data = self.read_flash_region(region)
            if data:
                all_data.extend(data)
            else:
                self.log(f"Failed to read region: {region.name}")
        
        if all_data:
            with open(filename, 'wb') as f:
                f.write(all_data)
            self.log(f"Flash dump saved: {len(all_data)} bytes")
            return True
        
        return False
    
    def flash_calibration(self, data: bytes) -> bool:
        """
        Flash new calibration data to ECU
        
        WARNING: This can brick your ECU if done incorrectly!
        """
        self.log("WARNING: Flashing calibration data!")
        
        # Find calibration region
        cal_region = None
        for region in self.FLASH_REGIONS:
            if region.name == "Calibration":
                cal_region = region
                break
        
        if not cal_region:
            self.log("Calibration region not found")
            return False
        
        if len(data) > cal_region.size:
            self.log(f"Data too large: {len(data)} > {cal_region.size}")
            return False
        
        # Request download
        self.log("Requesting download...")
        request = self.protocol.build_request_download(
            cal_region.start_address, len(data)
        )
        response = self.send_uds(request)
        
        if not response.success:
            self.log(f"Download request failed: {response.error_message}")
            return False
        
        # Get max block size from response
        max_block = 256  # Default
        if len(response.data) >= 2:
            format_byte = response.data[0]
            len_bytes = (format_byte >> 4) & 0x0F
            if len_bytes > 0 and len(response.data) >= 1 + len_bytes:
                max_block = int.from_bytes(response.data[1:1+len_bytes], 'big')
        
        # Transfer data
        self.log(f"Transferring data (block size: {max_block})...")
        block_counter = 1
        offset = 0
        
        while offset < len(data):
            chunk = data[offset:offset + max_block - 2]  # -2 for service ID and counter
            
            request = self.protocol.build_transfer_data(block_counter, chunk)
            response = self.send_uds(request)
            
            if not response.success:
                self.log(f"Transfer failed at block {block_counter}: {response.error_message}")
                return False
            
            offset += len(chunk)
            block_counter = (block_counter + 1) & 0xFF
            self.progress(offset, len(data), "Flashing...")
        
        # Request transfer exit
        self.log("Finishing transfer...")
        request = self.protocol.build_request_transfer_exit()
        response = self.send_uds(request)
        
        if response.success:
            self.log("Flash complete!")
            return True
        else:
            self.log(f"Transfer exit failed: {response.error_message}")
            return False
    
    # =========================================================================
    # Diagnostics
    # =========================================================================
    
    def read_dtc(self) -> List[DTCInfo]:
        """Read Diagnostic Trouble Codes"""
        self.log("Reading DTCs...")
        
        request = self.protocol.build_read_dtc(sub_function=0x01)
        response = self.send_uds(request)
        
        dtcs = []
        
        if response.success and len(response.data) >= 3:
            # Parse DTC response
            # Format varies by ECU, this is a common format
            data = response.data[2:]  # Skip sub-function and status
            
            i = 0
            while i + 3 <= len(data):
                dtc_high = data[i]
                dtc_mid = data[i+1]
                dtc_low = data[i+2]
                status = data[i+3] if i + 3 < len(data) else 0
                
                # Format as standard DTC code (e.g., P0123)
                code_type = ['P', 'C', 'B', 'U'][(dtc_high >> 6) & 0x03]
                code_num = ((dtc_high & 0x3F) << 8) | dtc_mid
                
                dtc = DTCInfo(
                    code=f"{code_type}{code_num:04d}",
                    status=status
                )
                dtcs.append(dtc)
                
                i += 4
        
        self.log(f"Found {len(dtcs)} DTCs")
        return dtcs
    
    def clear_dtc(self) -> bool:
        """Clear all Diagnostic Trouble Codes"""
        self.log("Clearing DTCs...")
        
        request = self.protocol.build_clear_dtc()
        response = self.send_uds(request)
        
        if response.success:
            self.log("DTCs cleared")
            return True
        else:
            self.log(f"Clear DTC failed: {response.error_message}")
            return False
    
    def reset_ecu(self, hard: bool = False) -> bool:
        """
        Reset ECU
        
        Args:
            hard: True for hard reset, False for soft reset
        """
        reset_type = UDS.ECU_RESET_HARD if hard else UDS.ECU_RESET_SOFT
        self.log(f"Resetting ECU ({'hard' if hard else 'soft'})...")
        
        request = self.protocol.build_ecu_reset(reset_type)
        response = self.send_uds(request)
        
        if response.success:
            self.log("ECU reset initiated")
            self.session_active = False
            self.security_unlocked = False
            return True
        else:
            self.log(f"Reset failed: {response.error_message}")
            return False


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ECU Communication Tool")
    parser.add_argument('--interface', '-i', default='simulated:test',
                        help='CAN interface (e.g., pcan:PCAN_USBBUS1, simulated:test)')
    parser.add_argument('--list', '-l', action='store_true',
                        help='List available interfaces')
    
    subparsers = parser.add_subparsers(dest='command')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Read ECU info')
    
    # Read command
    read_parser = subparsers.add_parser('read', help='Read memory')
    read_parser.add_argument('--address', '-a', type=lambda x: int(x, 0), required=True)
    read_parser.add_argument('--length', '-n', type=lambda x: int(x, 0), required=True)
    read_parser.add_argument('--output', '-o', help='Output file')
    
    # Dump command
    dump_parser = subparsers.add_parser('dump', help='Dump flash')
    dump_parser.add_argument('--output', '-o', default='flash_dump.bin')
    
    # DTC command
    dtc_parser = subparsers.add_parser('dtc', help='Read/clear DTCs')
    dtc_parser.add_argument('--clear', '-c', action='store_true')
    
    args = parser.parse_args()
    
    if args.list:
        print("Available interfaces:")
        from can_interface import CANInterface
        for iface in CANInterface.list_interfaces():
            print(f"  {iface}")
        return
    
    # Create tool
    tool = ECUTool()
    
    if not tool.connect(args.interface):
        print("Failed to connect")
        return
    
    try:
        if not tool.start_session():
            print("Failed to start session")
            return
        
        if args.command == 'info':
            # Read without security access
            info = tool.read_ecu_info()
            print(f"VIN: {info.vin}")
            print(f"Serial: {info.serial}")
            print(f"Hardware: {info.hardware_version}")
            print(f"Software: {info.software_version}")
            print(f"Calibration: {info.calibration_id}")
        
        elif args.command in ['read', 'dump']:
            if not tool.security_access():
                print("Security access failed")
                return
            
            if args.command == 'read':
                data = tool.read_memory(args.address, args.length)
                if data:
                    if args.output:
                        with open(args.output, 'wb') as f:
                            f.write(data)
                        print(f"Saved to {args.output}")
                    else:
                        # Hex dump
                        for i in range(0, len(data), 16):
                            hex_str = ' '.join(f'{b:02X}' for b in data[i:i+16])
                            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
                            print(f"{args.address+i:08X}: {hex_str:<48} {ascii_str}")
            
            elif args.command == 'dump':
                tool.dump_flash(args.output)
        
        elif args.command == 'dtc':
            if args.clear:
                tool.clear_dtc()
            else:
                dtcs = tool.read_dtc()
                for dtc in dtcs:
                    print(f"{dtc.code}: Status=0x{dtc.status:02X}")
    
    finally:
        tool.disconnect()


if __name__ == "__main__":
    main()





