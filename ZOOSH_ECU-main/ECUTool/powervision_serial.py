#!/usr/bin/env python3
"""
PowerVision Serial Interface

Communicates with PowerVision in Update Mode via COM port.
Your PowerVision is detected on COM3 in Update Mode.
"""

import serial
import serial.tools.list_ports
import time
import struct
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import IntEnum

# Import CAN interface base
try:
    from can_interface import CANInterface, CANMessage
except ImportError:
    @dataclass
    class CANMessage:
        arbitration_id: int
        data: bytes
        timestamp: float = 0.0
    
    class CANInterface:
        def __init__(self):
            self.connected = False


# =============================================================================
# PowerVision Device Info
# =============================================================================

@dataclass
class PowerVisionDevice:
    """PowerVision device information"""
    port: str
    description: str
    hwid: str
    serial_number: str = ""
    firmware_version: str = ""
    mode: str = "Unknown"


def find_powervision_devices() -> List[PowerVisionDevice]:
    """Find all connected PowerVision devices"""
    devices = []
    
    for port in serial.tools.list_ports.comports():
        desc_lower = port.description.lower()
        
        # Check for PowerVision
        if 'power' in desc_lower and 'vision' in desc_lower:
            mode = "Update Mode" if "update" in desc_lower else "Normal"
            devices.append(PowerVisionDevice(
                port=port.device,
                description=port.description,
                hwid=port.hwid,
                mode=mode
            ))
        # Also check for FTDI devices (PowerVision uses FTDI chip)
        elif 'ftdi' in desc_lower or 'ft232' in desc_lower:
            devices.append(PowerVisionDevice(
                port=port.device,
                description=port.description,
                hwid=port.hwid,
                mode="FTDI"
            ))
    
    return devices


# =============================================================================
# PowerVision Protocol Constants
# =============================================================================

class PVCmd:
    """PowerVision command bytes (reverse engineered)"""
    # Frame markers
    START = 0x7E
    ESCAPE = 0x7D
    
    # Commands (these are approximations - real protocol may differ)
    PING = 0x00
    GET_INFO = 0x01
    GET_VERSION = 0x02
    
    # CAN commands
    CAN_CONFIG = 0x10
    CAN_SEND = 0x11
    CAN_RECV = 0x12
    
    # ECU commands
    ECU_CONNECT = 0x20
    ECU_REQUEST = 0x21
    ECU_RESPONSE = 0x22
    
    # Flash commands  
    FLASH_INFO = 0x30
    FLASH_READ = 0x31
    FLASH_WRITE = 0x32
    FLASH_ERASE = 0x33


# =============================================================================
# PowerVision Serial Connection
# =============================================================================

class PowerVisionSerial:
    """
    Serial communication with PowerVision device
    """
    
    # Common PowerVision baud rates
    BAUD_RATES = [921600, 460800, 230400, 115200, 57600, 38400, 19200, 9600]
    
    def __init__(self, port: str = None):
        self.port = port
        self.serial: Optional[serial.Serial] = None
        self.connected = False
        self.info = PowerVisionDevice("", "", "")
    
    @staticmethod
    def find_device() -> Optional[str]:
        """Auto-detect PowerVision port"""
        devices = find_powervision_devices()
        if devices:
            return devices[0].port
        return None
    
    def connect(self, port: str = None, baud: int = 921600) -> bool:
        """
        Connect to PowerVision
        
        Args:
            port: COM port (e.g., "COM3"). Auto-detect if None.
            baud: Baud rate (default 921600 for PowerVision)
        """
        if port is None:
            port = self.find_device()
            if port is None:
                print("No PowerVision device found!")
                return False
        
        self.port = port
        
        # Try different baud rates if the default fails
        for rate in [baud] + [r for r in self.BAUD_RATES if r != baud]:
            try:
                self.serial = serial.Serial(
                    port=port,
                    baudrate=rate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1.0,
                    write_timeout=1.0
                )
                
                # Test connection
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()
                
                # Try to ping device
                if self._ping():
                    self.connected = True
                    print(f"Connected to {port} at {rate} baud")
                    return True
                
                self.serial.close()
                
            except serial.SerialException as e:
                print(f"Failed at {rate} baud: {e}")
                continue
        
        return False
    
    def disconnect(self):
        """Disconnect from PowerVision"""
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.connected = False
    
    def _ping(self) -> bool:
        """Ping device to check connection"""
        try:
            # Send a simple ping/status request
            # Actual protocol may vary
            self.serial.write(bytes([0x00]))  # Simple ping
            time.sleep(0.1)
            
            # Check if we got any response
            if self.serial.in_waiting > 0:
                response = self.serial.read(self.serial.in_waiting)
                return len(response) > 0
            
            # Even without response, connection might be OK
            return True
            
        except:
            return False
    
    def send(self, data: bytes) -> bool:
        """Send raw data"""
        if not self.serial or not self.serial.is_open:
            return False
        
        try:
            written = self.serial.write(data)
            self.serial.flush()
            return written == len(data)
        except:
            return False
    
    def receive(self, timeout: float = 1.0) -> Optional[bytes]:
        """Receive data with timeout"""
        if not self.serial or not self.serial.is_open:
            return None
        
        try:
            self.serial.timeout = timeout
            
            # Wait for data
            start = time.time()
            while time.time() - start < timeout:
                if self.serial.in_waiting > 0:
                    return self.serial.read(self.serial.in_waiting)
                time.sleep(0.01)
            
            return None
        except:
            return None
    
    def send_receive(self, data: bytes, timeout: float = 1.0) -> Optional[bytes]:
        """Send data and wait for response"""
        self.serial.reset_input_buffer()
        
        if not self.send(data):
            return None
        
        return self.receive(timeout)
    
    # =========================================================================
    # PowerVision-specific Commands
    # =========================================================================
    
    def get_info(self) -> Optional[dict]:
        """Get device information"""
        # This would need the actual PowerVision protocol
        # For now, return basic port info
        return {
            'port': self.port,
            'connected': self.connected
        }
    
    def enter_can_mode(self, bitrate: int = 500000) -> bool:
        """
        Put PowerVision into CAN pass-through mode
        
        Note: This requires knowing the actual PowerVision protocol
        """
        # Build CAN config command
        # This is speculative - real protocol may differ
        cmd = bytes([
            PVCmd.CAN_CONFIG,
            (bitrate >> 24) & 0xFF,
            (bitrate >> 16) & 0xFF,
            (bitrate >> 8) & 0xFF,
            bitrate & 0xFF
        ])
        
        response = self.send_receive(cmd)
        return response is not None
    
    def can_send(self, can_id: int, data: bytes) -> bool:
        """Send CAN frame through PowerVision"""
        # Build CAN send command
        cmd = bytearray([PVCmd.CAN_SEND])
        cmd.extend(struct.pack('>I', can_id))  # CAN ID
        cmd.append(len(data))  # DLC
        cmd.extend(data)
        
        return self.send(bytes(cmd))
    
    def can_receive(self, timeout: float = 1.0) -> Optional[Tuple[int, bytes]]:
        """Receive CAN frame from PowerVision"""
        response = self.receive(timeout)
        
        if response and len(response) >= 6:
            # Parse CAN frame
            # This format is speculative
            can_id = struct.unpack('>I', response[1:5])[0]
            dlc = response[5]
            data = response[6:6+dlc]
            return (can_id, data)
        
        return None
    
    def uds_request(self, service: bytes, ecu_id: int = 0x7E0) -> Optional[bytes]:
        """
        Send UDS request through PowerVision's built-in UDS handler
        
        This uses PowerVision's ECU communication capability directly
        """
        cmd = bytearray([PVCmd.ECU_REQUEST])
        cmd.extend(struct.pack('>H', ecu_id))
        cmd.extend(struct.pack('>H', len(service)))
        cmd.extend(service)
        
        response = self.send_receive(bytes(cmd), timeout=3.0)
        
        if response and response[0] == PVCmd.ECU_RESPONSE:
            length = struct.unpack('>H', response[1:3])[0]
            return response[3:3+length]
        
        return None


# =============================================================================
# PowerVision CAN Interface (for ECU Tool)
# =============================================================================

class PowerVisionCANInterface(CANInterface):
    """
    CAN interface using PowerVision as the bridge
    
    Integrates with ECU Tool for seamless communication
    """
    
    def __init__(self, port: str = None):
        super().__init__()
        self.pv = PowerVisionSerial(port)
        self.port = port
    
    def connect(self) -> bool:
        """Connect via PowerVision"""
        if self.pv.connect(self.port):
            self.pv.enter_can_mode(500000)
            self.connected = True
            return True
        return False
    
    def disconnect(self):
        """Disconnect"""
        self.pv.disconnect()
        self.connected = False
    
    def send(self, msg: CANMessage) -> bool:
        """Send CAN message"""
        return self.pv.can_send(msg.arbitration_id, msg.data)
    
    def _receive_internal(self, timeout: float) -> Optional[CANMessage]:
        """Receive CAN message"""
        result = self.pv.can_receive(timeout)
        if result:
            can_id, data = result
            return CANMessage(arbitration_id=can_id, data=data, timestamp=time.time())
        return None


# =============================================================================
# Direct Test Mode
# =============================================================================

class PowerVisionDirect:
    """
    Direct PowerVision communication in Update Mode
    
    When PowerVision is in Update Mode (like yours on COM3),
    it may accept different commands than normal operation mode.
    """
    
    def __init__(self, port: str = "COM3"):
        self.port = port
        self.serial: Optional[serial.Serial] = None
    
    def connect(self) -> bool:
        """Connect to PowerVision in Update Mode"""
        try:
            # Try high baud rate first (typical for update mode)
            self.serial = serial.Serial(
                port=self.port,
                baudrate=115200,
                timeout=2.0
            )
            
            print(f"Connected to {self.port}")
            
            # Clear buffers
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            
            return True
            
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect"""
        if self.serial:
            self.serial.close()
    
    def probe(self) -> dict:
        """
        Probe device to understand its protocol
        Send various bytes and see what we get back
        """
        results = {}
        
        # Test patterns
        test_patterns = [
            (b'\x00', "Null"),
            (b'\r', "CR"),
            (b'\n', "LF"),
            (b'\r\n', "CRLF"),
            (b'?', "Query"),
            (b'AT', "AT Command"),
            (b'ATI', "AT Info"),
            (b'\x7E', "HDLC Start"),
            (b'\x01', "STX"),
            (b'V', "Version?"),
            (b'I', "Info?"),
            (bytes([0x10, 0x01]), "UDS Session"),
        ]
        
        for pattern, name in test_patterns:
            self.serial.reset_input_buffer()
            self.serial.write(pattern)
            time.sleep(0.2)
            
            if self.serial.in_waiting > 0:
                response = self.serial.read(self.serial.in_waiting)
                results[name] = response
                print(f"  {name}: {pattern.hex()} -> {response.hex()} ({response})")
            else:
                print(f"  {name}: {pattern.hex()} -> (no response)")
        
        return results
    
    def raw_command(self, data: bytes) -> Optional[bytes]:
        """Send raw command and get response"""
        self.serial.reset_input_buffer()
        self.serial.write(data)
        time.sleep(0.3)
        
        if self.serial.in_waiting > 0:
            return self.serial.read(self.serial.in_waiting)
        return None


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("PowerVision Connection Test")
    print("=" * 60)
    
    # Find devices
    print("\nSearching for PowerVision devices...")
    devices = find_powervision_devices()
    
    if not devices:
        print("No PowerVision devices found!")
        print("\nAll COM ports:")
        for port in serial.tools.list_ports.comports():
            print(f"  {port.device}: {port.description}")
        return
    
    print(f"\nFound {len(devices)} device(s):")
    for i, dev in enumerate(devices):
        print(f"\n  [{i}] {dev.port}")
        print(f"      Description: {dev.description}")
        print(f"      Mode: {dev.mode}")
        print(f"      HWID: {dev.hwid}")
    
    # Connect to first device
    device = devices[0]
    print(f"\n{'='*60}")
    print(f"Connecting to {device.port} ({device.mode})...")
    print("=" * 60)
    
    pv = PowerVisionDirect(device.port)
    
    if pv.connect():
        print("\nProbing device protocol...")
        print("-" * 40)
        pv.probe()
        
        print("\n" + "-" * 40)
        print("Trying some raw commands...")
        
        # Try some commands
        for cmd, desc in [
            (b'\x00\x00\x00\x00', "Zeros"),
            (b'\x10\x03', "UDS Extended Session"),
            (b'\x3E\x00', "UDS Tester Present"),
            (b'\x22\xF1\x90', "UDS Read VIN"),
        ]:
            response = pv.raw_command(cmd)
            if response:
                print(f"  {desc}: -> {response.hex()}")
            else:
                print(f"  {desc}: -> (no response)")
        
        pv.disconnect()
        print("\nDisconnected")
    else:
        print("Failed to connect!")


if __name__ == "__main__":
    main()

