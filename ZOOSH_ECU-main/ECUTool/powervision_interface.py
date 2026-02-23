#!/usr/bin/env python3
"""
PowerVision USB Interface

Communicates with Dynojet PowerVision devices via FTDI USB.
Acts as a bridge between the ECU Tool and the PowerVision hardware.

The PowerVision can operate in two modes:
1. Pass-through mode: Acts as a CAN-to-USB bridge
2. Device mode: Direct communication with PowerVision itself
"""

import ctypes
import time
import threading
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import IntEnum
import struct

# Try to load the FTDI library
try:
    import clr
    clr.AddReference(r"C:\Program Files (x86)\Dynojet Power Core\FTD2XX_NET.dll")
    from FTD2XX_NET import FTDI
    HAS_FTDI_NET = True
except:
    HAS_FTDI_NET = False

# Alternative: Use ftd2xx Python package
try:
    import ftd2xx
    HAS_FTD2XX = True
except ImportError:
    HAS_FTD2XX = False


# =============================================================================
# Constants
# =============================================================================

class PVCommand(IntEnum):
    """PowerVision command bytes"""
    # Device info
    GET_VERSION = 0x01
    GET_SERIAL = 0x02
    GET_STATUS = 0x03
    
    # CAN operations
    CAN_INIT = 0x10
    CAN_SEND = 0x11
    CAN_RECV = 0x12
    CAN_FILTER = 0x13
    
    # ECU operations
    ECU_CONNECT = 0x20
    ECU_DISCONNECT = 0x21
    ECU_SEND_UDS = 0x22
    ECU_RECV_UDS = 0x23
    
    # Flash operations
    FLASH_READ = 0x30
    FLASH_WRITE = 0x31
    FLASH_ERASE = 0x32
    
    # Tune operations
    TUNE_READ = 0x40
    TUNE_WRITE = 0x41
    TUNE_LIST = 0x42


@dataclass
class PowerVisionInfo:
    """PowerVision device information"""
    serial: str = ""
    description: str = ""
    firmware_version: str = ""
    hardware_version: str = ""
    device_type: str = ""


# =============================================================================
# FTDI Direct Interface (using ctypes)
# =============================================================================

class FTDIDevice:
    """
    Direct FTDI device interface using ctypes
    Works without .NET or Python packages
    """
    
    # FTDI status codes
    FT_OK = 0
    FT_INVALID_HANDLE = 1
    FT_DEVICE_NOT_FOUND = 2
    FT_DEVICE_NOT_OPENED = 3
    FT_IO_ERROR = 4
    FT_INSUFFICIENT_RESOURCES = 5
    
    def __init__(self):
        self.handle = None
        self.dll = None
        self._load_dll()
    
    def _load_dll(self):
        """Load FTDI DLL"""
        dll_paths = [
            r"C:\Windows\System32\ftd2xx.dll",
            r"C:\Windows\SysWOW64\ftd2xx.dll",
            "ftd2xx.dll"
        ]
        
        for path in dll_paths:
            try:
                self.dll = ctypes.WinDLL(path)
                return
            except:
                continue
        
        # Try loading from Power Core directory
        try:
            # ftd2xx64.dll or ftd2xx.dll might be bundled
            import os
            pc_path = r"C:\Program Files (x86)\Dynojet Power Core"
            for f in os.listdir(pc_path):
                if f.lower().startswith('ftd2xx') and f.endswith('.dll'):
                    self.dll = ctypes.WinDLL(os.path.join(pc_path, f))
                    return
        except:
            pass
    
    def list_devices(self) -> List[dict]:
        """List all FTDI devices"""
        if not self.dll:
            return []
        
        devices = []
        num_devices = ctypes.c_ulong()
        
        # Get number of devices
        status = self.dll.FT_CreateDeviceInfoList(ctypes.byref(num_devices))
        if status != self.FT_OK or num_devices.value == 0:
            return devices
        
        # Get device info for each
        for i in range(num_devices.value):
            flags = ctypes.c_ulong()
            dev_type = ctypes.c_ulong()
            dev_id = ctypes.c_ulong()
            loc_id = ctypes.c_ulong()
            serial = ctypes.create_string_buffer(64)
            desc = ctypes.create_string_buffer(64)
            handle = ctypes.c_void_p()
            
            status = self.dll.FT_GetDeviceInfoDetail(
                i,
                ctypes.byref(flags),
                ctypes.byref(dev_type),
                ctypes.byref(dev_id),
                ctypes.byref(loc_id),
                serial,
                desc,
                ctypes.byref(handle)
            )
            
            if status == self.FT_OK:
                devices.append({
                    'index': i,
                    'serial': serial.value.decode('utf-8', errors='ignore'),
                    'description': desc.value.decode('utf-8', errors='ignore'),
                    'type': dev_type.value,
                    'id': dev_id.value
                })
        
        return devices
    
    def open(self, index: int = 0) -> bool:
        """Open device by index"""
        if not self.dll:
            return False
        
        handle = ctypes.c_void_p()
        status = self.dll.FT_Open(index, ctypes.byref(handle))
        
        if status == self.FT_OK:
            self.handle = handle
            return True
        return False
    
    def open_by_serial(self, serial: str) -> bool:
        """Open device by serial number"""
        if not self.dll:
            return False
        
        handle = ctypes.c_void_p()
        status = self.dll.FT_OpenEx(
            serial.encode(),
            1,  # FT_OPEN_BY_SERIAL_NUMBER
            ctypes.byref(handle)
        )
        
        if status == self.FT_OK:
            self.handle = handle
            return True
        return False
    
    def close(self):
        """Close device"""
        if self.dll and self.handle:
            self.dll.FT_Close(self.handle)
            self.handle = None
    
    def set_baud_rate(self, baud: int) -> bool:
        """Set baud rate"""
        if not self.handle:
            return False
        return self.dll.FT_SetBaudRate(self.handle, baud) == self.FT_OK
    
    def set_timeouts(self, read_ms: int, write_ms: int) -> bool:
        """Set read/write timeouts"""
        if not self.handle:
            return False
        return self.dll.FT_SetTimeouts(self.handle, read_ms, write_ms) == self.FT_OK
    
    def write(self, data: bytes) -> int:
        """Write data to device"""
        if not self.handle:
            return 0
        
        written = ctypes.c_ulong()
        status = self.dll.FT_Write(
            self.handle,
            data,
            len(data),
            ctypes.byref(written)
        )
        
        return written.value if status == self.FT_OK else 0
    
    def read(self, num_bytes: int) -> bytes:
        """Read data from device"""
        if not self.handle:
            return b''
        
        buffer = ctypes.create_string_buffer(num_bytes)
        read_count = ctypes.c_ulong()
        
        status = self.dll.FT_Read(
            self.handle,
            buffer,
            num_bytes,
            ctypes.byref(read_count)
        )
        
        if status == self.FT_OK:
            return buffer.raw[:read_count.value]
        return b''
    
    def get_queue_status(self) -> int:
        """Get number of bytes in receive queue"""
        if not self.handle:
            return 0
        
        rx_bytes = ctypes.c_ulong()
        status = self.dll.FT_GetQueueStatus(self.handle, ctypes.byref(rx_bytes))
        
        return rx_bytes.value if status == self.FT_OK else 0
    
    def purge(self, rx: bool = True, tx: bool = True):
        """Purge receive and/or transmit buffers"""
        if not self.handle:
            return
        
        mask = 0
        if rx:
            mask |= 1  # FT_PURGE_RX
        if tx:
            mask |= 2  # FT_PURGE_TX
        
        self.dll.FT_Purge(self.handle, mask)


# =============================================================================
# PowerVision Interface
# =============================================================================

class PowerVisionInterface:
    """
    High-level PowerVision interface
    
    Provides methods to:
    - Connect to PowerVision device
    - Send/receive CAN messages through PowerVision
    - Communicate with ECU via PowerVision
    """
    
    # PowerVision USB parameters
    BAUD_RATE = 921600
    READ_TIMEOUT = 1000
    WRITE_TIMEOUT = 1000
    
    def __init__(self):
        self.device = FTDIDevice()
        self.connected = False
        self.info = PowerVisionInfo()
        self._rx_thread: Optional[threading.Thread] = None
        self._running = False
        self._rx_callback = None
    
    @staticmethod
    def list_devices() -> List[PowerVisionInfo]:
        """List all connected PowerVision devices"""
        devices = []
        ftdi = FTDIDevice()
        
        for dev in ftdi.list_devices():
            # Filter for PowerVision devices
            desc = dev['description'].upper()
            if 'POWERVISION' in desc or 'PV3' in desc or 'DYNOJET' in desc or 'FT232' in desc:
                info = PowerVisionInfo(
                    serial=dev['serial'],
                    description=dev['description'],
                    device_type=f"Type {dev['type']}"
                )
                devices.append(info)
        
        # Also check for generic FTDI devices that might be PowerVision
        if not devices:
            for dev in ftdi.list_devices():
                info = PowerVisionInfo(
                    serial=dev['serial'],
                    description=dev['description'],
                    device_type=f"FTDI Type {dev['type']}"
                )
                devices.append(info)
        
        return devices
    
    def connect(self, serial: str = None, index: int = 0) -> bool:
        """
        Connect to PowerVision device
        
        Args:
            serial: Device serial number (optional)
            index: Device index if serial not specified
        """
        if serial:
            success = self.device.open_by_serial(serial)
        else:
            success = self.device.open(index)
        
        if not success:
            return False
        
        # Configure device
        self.device.set_baud_rate(self.BAUD_RATE)
        self.device.set_timeouts(self.READ_TIMEOUT, self.WRITE_TIMEOUT)
        self.device.purge()
        
        self.connected = True
        
        # Try to get device info
        self._get_device_info()
        
        return True
    
    def disconnect(self):
        """Disconnect from PowerVision"""
        self._running = False
        if self._rx_thread:
            self._rx_thread.join(timeout=2.0)
        
        self.device.close()
        self.connected = False
    
    def _get_device_info(self):
        """Query device for info"""
        # This would send PowerVision-specific commands
        # For now, we'll use the FTDI info
        pass
    
    def send_raw(self, data: bytes) -> bool:
        """Send raw data to PowerVision"""
        if not self.connected:
            return False
        
        written = self.device.write(data)
        return written == len(data)
    
    def receive_raw(self, timeout: float = 1.0) -> Optional[bytes]:
        """Receive raw data from PowerVision"""
        if not self.connected:
            return None
        
        start = time.time()
        data = bytearray()
        
        while time.time() - start < timeout:
            available = self.device.get_queue_status()
            if available > 0:
                chunk = self.device.read(available)
                data.extend(chunk)
                
                # Check if we have a complete message
                if self._is_complete_message(data):
                    return bytes(data)
            else:
                time.sleep(0.01)
        
        return bytes(data) if data else None
    
    def _is_complete_message(self, data: bytes) -> bool:
        """Check if received data is a complete message"""
        # This depends on the PowerVision protocol
        # For now, assume any data is complete
        return len(data) > 0
    
    # =========================================================================
    # CAN Pass-through Mode
    # =========================================================================
    
    def can_init(self, bitrate: int = 500000) -> bool:
        """Initialize CAN interface through PowerVision"""
        # Send CAN init command to PowerVision
        # This is protocol-specific
        cmd = bytes([PVCommand.CAN_INIT, 
                    (bitrate >> 24) & 0xFF,
                    (bitrate >> 16) & 0xFF,
                    (bitrate >> 8) & 0xFF,
                    bitrate & 0xFF])
        
        return self.send_raw(cmd)
    
    def can_send(self, can_id: int, data: bytes) -> bool:
        """Send CAN message through PowerVision"""
        # Build CAN frame command
        cmd = bytearray([PVCommand.CAN_SEND])
        cmd.extend(struct.pack('>I', can_id))  # CAN ID (big endian)
        cmd.append(len(data))  # DLC
        cmd.extend(data)
        
        return self.send_raw(bytes(cmd))
    
    def can_receive(self, timeout: float = 1.0) -> Optional[Tuple[int, bytes]]:
        """Receive CAN message through PowerVision"""
        response = self.receive_raw(timeout)
        
        if response and len(response) >= 6:
            if response[0] == PVCommand.CAN_RECV:
                can_id = struct.unpack('>I', response[1:5])[0]
                dlc = response[5]
                data = response[6:6+dlc]
                return (can_id, bytes(data))
        
        return None
    
    # =========================================================================
    # UDS Communication
    # =========================================================================
    
    def uds_request(self, request: bytes, ecu_id: int = 0x7E0) -> Optional[bytes]:
        """
        Send UDS request and get response
        
        This sends through PowerVision which handles the ISO-TP framing
        """
        # Build UDS request command
        cmd = bytearray([PVCommand.ECU_SEND_UDS])
        cmd.extend(struct.pack('>H', ecu_id))  # ECU CAN ID
        cmd.extend(struct.pack('>H', len(request)))  # Request length
        cmd.extend(request)
        
        if not self.send_raw(bytes(cmd)):
            return None
        
        # Wait for response
        response = self.receive_raw(timeout=2.0)
        
        if response and len(response) > 4:
            if response[0] == PVCommand.ECU_RECV_UDS:
                resp_len = struct.unpack('>H', response[1:3])[0]
                return response[3:3+resp_len]
        
        return None


# =============================================================================
# PowerVision CAN Interface (for ECU Tool integration)
# =============================================================================

# Import base class
import sys
sys.path.insert(0, str(__file__).rsplit('\\', 1)[0])

try:
    from can_interface import CANInterface, CANMessage
except ImportError:
    # Define minimal classes if import fails
    class CANInterface:
        pass
    
    @dataclass
    class CANMessage:
        arbitration_id: int
        data: bytes
        timestamp: float = 0.0


class PowerVisionCANInterface(CANInterface):
    """
    CAN interface implementation using PowerVision as the bridge
    
    This allows the ECU Tool to communicate with ECUs through
    the PowerVision device.
    """
    
    def __init__(self, serial: str = None):
        super().__init__()
        self.pv = PowerVisionInterface()
        self.serial = serial
    
    def connect(self) -> bool:
        """Connect to PowerVision and initialize CAN"""
        devices = PowerVisionInterface.list_devices()
        
        if not devices:
            print("No PowerVision devices found")
            return False
        
        # Connect to first device or specified serial
        if self.serial:
            success = self.pv.connect(serial=self.serial)
        else:
            success = self.pv.connect(index=0)
        
        if not success:
            print("Failed to connect to PowerVision")
            return False
        
        # Initialize CAN
        if not self.pv.can_init(500000):
            print("Failed to initialize CAN")
            self.pv.disconnect()
            return False
        
        self.connected = True
        self.start_receiver()
        return True
    
    def disconnect(self):
        """Disconnect from PowerVision"""
        self.stop_receiver()
        self.pv.disconnect()
        self.connected = False
    
    def send(self, msg: CANMessage) -> bool:
        """Send CAN message through PowerVision"""
        return self.pv.can_send(msg.arbitration_id, msg.data)
    
    def _receive_internal(self, timeout: float) -> Optional[CANMessage]:
        """Receive CAN message from PowerVision"""
        result = self.pv.can_receive(timeout)
        
        if result:
            can_id, data = result
            return CANMessage(
                arbitration_id=can_id,
                data=data,
                timestamp=time.time()
            )
        
        return None


# =============================================================================
# Factory function update
# =============================================================================

def create_powervision_interface(serial: str = None) -> PowerVisionCANInterface:
    """Create PowerVision CAN interface"""
    return PowerVisionCANInterface(serial)


# =============================================================================
# Test / Demo
# =============================================================================

def main():
    """Demo / test function"""
    print("=" * 60)
    print("PowerVision Interface Test")
    print("=" * 60)
    
    # List devices
    print("\nSearching for PowerVision devices...")
    devices = PowerVisionInterface.list_devices()
    
    if not devices:
        print("No PowerVision devices found!")
        print("\nMake sure:")
        print("  1. PowerVision is connected via USB")
        print("  2. FTDI drivers are installed")
        print("  3. Device is powered on")
        
        # List all FTDI devices anyway
        print("\nAll FTDI devices found:")
        ftdi = FTDIDevice()
        for dev in ftdi.list_devices():
            print(f"  Serial: {dev['serial']}")
            print(f"  Description: {dev['description']}")
            print(f"  Type: {dev['type']}")
            print()
        return
    
    print(f"\nFound {len(devices)} device(s):")
    for i, dev in enumerate(devices):
        print(f"\n  [{i}] {dev.description}")
        print(f"      Serial: {dev.serial}")
        print(f"      Type: {dev.device_type}")
    
    # Try to connect
    print("\nConnecting to first device...")
    pv = PowerVisionInterface()
    
    if pv.connect(index=0):
        print("Connected!")
        print(f"  Serial: {pv.info.serial}")
        print(f"  Description: {pv.info.description}")
        
        # Test sending
        print("\nInitializing CAN bus...")
        pv.can_init(500000)
        
        print("Sending test message...")
        pv.can_send(0x7DF, bytes([0x01, 0x00]))  # OBD2 broadcast
        
        print("Waiting for response...")
        result = pv.can_receive(timeout=2.0)
        if result:
            can_id, data = result
            print(f"  Received: ID=0x{can_id:03X} Data={data.hex()}")
        else:
            print("  No response")
        
        pv.disconnect()
        print("\nDisconnected")
    else:
        print("Failed to connect!")


if __name__ == "__main__":
    main()

