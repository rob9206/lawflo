#!/usr/bin/env python3
"""
CAN Interface Abstraction Layer

Supports multiple CAN interfaces:
- PCAN (Peak Systems)
- SocketCAN (Linux)
- Kvaser
- Vector
- Serial (for some USB-CAN adapters)
- Simulated (for testing)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Callable
from queue import Queue
import threading
import time
import struct

# Try to import python-can
try:
    import can
    HAS_PYTHON_CAN = True
except ImportError:
    HAS_PYTHON_CAN = False

# Try to import serial
try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CANMessage:
    """CAN message container"""
    arbitration_id: int
    data: bytes
    timestamp: float = 0.0
    is_extended: bool = False
    is_remote: bool = False
    is_error: bool = False
    
    def __repr__(self):
        return f"CAN(0x{self.arbitration_id:03X}: {self.data.hex(' ')})"


# =============================================================================
# Base Interface Class
# =============================================================================

class CANInterface(ABC):
    """Abstract base class for CAN interfaces"""
    
    def __init__(self):
        self.connected = False
        self.bitrate = 500000
        self.rx_queue = Queue()
        self.rx_callback: Optional[Callable[[CANMessage], None]] = None
        self._rx_thread: Optional[threading.Thread] = None
        self._running = False
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the CAN interface"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the CAN interface"""
        pass
    
    @abstractmethod
    def send(self, msg: CANMessage) -> bool:
        """Send a CAN message"""
        pass
    
    @abstractmethod
    def _receive_internal(self, timeout: float) -> Optional[CANMessage]:
        """Internal receive method"""
        pass
    
    def receive(self, timeout: float = 1.0) -> Optional[CANMessage]:
        """
        Receive a CAN message
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            CANMessage or None if timeout
        """
        try:
            return self.rx_queue.get(timeout=timeout)
        except:
            return self._receive_internal(timeout)
    
    def receive_filtered(self, arbitration_id: int, timeout: float = 1.0) -> Optional[CANMessage]:
        """
        Receive a message with specific arbitration ID
        """
        start = time.time()
        while time.time() - start < timeout:
            msg = self.receive(timeout=0.1)
            if msg and msg.arbitration_id == arbitration_id:
                return msg
        return None
    
    def start_receiver(self) -> None:
        """Start background receiver thread"""
        if self._rx_thread and self._rx_thread.is_alive():
            return
        
        self._running = True
        self._rx_thread = threading.Thread(target=self._receiver_loop, daemon=True)
        self._rx_thread.start()
    
    def stop_receiver(self) -> None:
        """Stop background receiver thread"""
        self._running = False
        if self._rx_thread:
            self._rx_thread.join(timeout=2.0)
    
    def _receiver_loop(self) -> None:
        """Background receiver loop"""
        while self._running and self.connected:
            msg = self._receive_internal(timeout=0.1)
            if msg:
                self.rx_queue.put(msg)
                if self.rx_callback:
                    self.rx_callback(msg)
    
    def set_filter(self, can_id: int, mask: int = 0x7FF) -> None:
        """Set CAN filter (if supported)"""
        pass
    
    @staticmethod
    def list_interfaces() -> List[str]:
        """List available CAN interfaces"""
        interfaces = []
        
        if HAS_PYTHON_CAN:
            # PCAN interfaces
            for i in range(1, 9):
                interfaces.append(f"pcan:PCAN_USBBUS{i}")
            
            # SocketCAN (Linux)
            interfaces.append("socketcan:can0")
            interfaces.append("socketcan:vcan0")
            
            # Vector
            interfaces.append("vector:0")
            
            # Kvaser
            interfaces.append("kvaser:0")
        
        # Serial interfaces
        if HAS_SERIAL:
            for port in serial.tools.list_ports.comports():
                interfaces.append(f"serial:{port.device}")
        
        # Simulated
        interfaces.append("simulated:test")
        
        return interfaces


# =============================================================================
# Python-CAN Interface (PCAN, SocketCAN, Vector, Kvaser)
# =============================================================================

class PythonCANInterface(CANInterface):
    """
    Interface using python-can library
    Supports: PCAN, SocketCAN, Vector, Kvaser, and more
    """
    
    def __init__(self, interface: str = 'pcan', channel: str = 'PCAN_USBBUS1', 
                 bitrate: int = 500000):
        super().__init__()
        self.interface = interface
        self.channel = channel
        self.bitrate = bitrate
        self.bus: Optional[can.Bus] = None
    
    def connect(self) -> bool:
        if not HAS_PYTHON_CAN:
            print("Error: python-can not installed. Run: pip install python-can")
            return False
        
        try:
            self.bus = can.interface.Bus(
                interface=self.interface,
                channel=self.channel,
                bitrate=self.bitrate
            )
            self.connected = True
            self.start_receiver()
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def disconnect(self) -> None:
        self.stop_receiver()
        if self.bus:
            self.bus.shutdown()
            self.bus = None
        self.connected = False
    
    def send(self, msg: CANMessage) -> bool:
        if not self.bus:
            return False
        
        try:
            can_msg = can.Message(
                arbitration_id=msg.arbitration_id,
                data=msg.data,
                is_extended_id=msg.is_extended
            )
            self.bus.send(can_msg)
            return True
        except Exception as e:
            print(f"Send failed: {e}")
            return False
    
    def _receive_internal(self, timeout: float) -> Optional[CANMessage]:
        if not self.bus:
            return None
        
        try:
            msg = self.bus.recv(timeout=timeout)
            if msg:
                return CANMessage(
                    arbitration_id=msg.arbitration_id,
                    data=bytes(msg.data),
                    timestamp=msg.timestamp or time.time(),
                    is_extended=msg.is_extended_id,
                    is_remote=msg.is_remote_frame,
                    is_error=msg.is_error_frame
                )
        except:
            pass
        return None
    
    def set_filter(self, can_id: int, mask: int = 0x7FF) -> None:
        if self.bus:
            self.bus.set_filters([{"can_id": can_id, "can_mask": mask}])


# =============================================================================
# Serial CAN Interface (for USB-CAN adapters with serial protocol)
# =============================================================================

class SerialCANInterface(CANInterface):
    """
    Serial CAN interface for USB-CAN adapters
    Supports: Canable, USBtin, SLCAN compatible devices
    """
    
    def __init__(self, port: str, baudrate: int = 115200, bitrate: int = 500000):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.bitrate = bitrate
        self.serial: Optional[serial.Serial] = None
    
    def connect(self) -> bool:
        if not HAS_SERIAL:
            print("Error: pyserial not installed. Run: pip install pyserial")
            return False
        
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1
            )
            
            # Initialize SLCAN mode
            self._send_command('C')  # Close any existing connection
            time.sleep(0.1)
            
            # Set bitrate
            speed_codes = {
                10000: 'S0',
                20000: 'S1',
                50000: 'S2',
                100000: 'S3',
                125000: 'S4',
                250000: 'S5',
                500000: 'S6',
                800000: 'S7',
                1000000: 'S8',
            }
            
            if self.bitrate in speed_codes:
                self._send_command(speed_codes[self.bitrate])
            
            self._send_command('O')  # Open CAN channel
            
            self.connected = True
            self.start_receiver()
            return True
            
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def _send_command(self, cmd: str) -> None:
        if self.serial:
            self.serial.write(f"{cmd}\r".encode())
            self.serial.flush()
    
    def disconnect(self) -> None:
        self.stop_receiver()
        if self.serial:
            self._send_command('C')  # Close CAN channel
            self.serial.close()
            self.serial = None
        self.connected = False
    
    def send(self, msg: CANMessage) -> bool:
        if not self.serial:
            return False
        
        try:
            # SLCAN format: tiiildd...
            # t = transmit, iii = ID (3 hex), l = length, dd = data bytes
            cmd = f"t{msg.arbitration_id:03X}{len(msg.data)}"
            cmd += msg.data.hex().upper()
            self._send_command(cmd)
            return True
        except Exception as e:
            print(f"Send failed: {e}")
            return False
    
    def _receive_internal(self, timeout: float) -> Optional[CANMessage]:
        if not self.serial:
            return None
        
        try:
            start = time.time()
            line = b''
            
            while time.time() - start < timeout:
                if self.serial.in_waiting:
                    char = self.serial.read(1)
                    if char == b'\r':
                        break
                    line += char
            
            if line and line[0:1] == b't':
                # Parse SLCAN frame
                line = line.decode()
                can_id = int(line[1:4], 16)
                length = int(line[4], 16)
                data = bytes.fromhex(line[5:5+length*2])
                
                return CANMessage(
                    arbitration_id=can_id,
                    data=data,
                    timestamp=time.time()
                )
        except:
            pass
        
        return None


# =============================================================================
# Simulated CAN Interface (for testing)
# =============================================================================

class SimulatedCANInterface(CANInterface):
    """
    Simulated CAN interface for testing without hardware
    Emulates a basic ECU
    """
    
    def __init__(self):
        super().__init__()
        self.tx_queue = Queue()
        self.rx_queue = Queue()  # Initialize rx_queue
        self.ecu_request_id = 0x7E0
        self.ecu_response_id = 0x7E8
        
        # Simulated ECU state
        self.session = 0x01
        self.security_level = 0
        self.seed = bytes([0x12, 0x34, 0x56, 0x78])
        
        # Pre-import for simulator thread
        self._security = None
    
    def connect(self) -> bool:
        self.connected = True
        self._running = True
        self._rx_thread = threading.Thread(target=self._simulator_loop, daemon=True)
        self._rx_thread.start()
        time.sleep(0.2)  # Let simulator thread start
        return True
    
    def disconnect(self) -> None:
        self._running = False
        self.connected = False
    
    def send(self, msg: CANMessage) -> bool:
        if not self.connected:
            return False
        self.tx_queue.put(msg)
        return True
    
    def _receive_internal(self, timeout: float) -> Optional[CANMessage]:
        try:
            return self.rx_queue.get(timeout=timeout)
        except:
            return None
    
    def _simulator_loop(self) -> None:
        """Simulate ECU responses"""
        while self._running:
            try:
                msg = self.tx_queue.get(timeout=0.1)
                
                if msg.arbitration_id == self.ecu_request_id:
                    # Decode ISO-TP frame to get UDS data
                    frame_type = msg.data[0] & 0xF0
                    
                    if frame_type == 0x00:  # Single frame
                        length = msg.data[0] & 0x0F
                        uds_data = bytes(msg.data[1:1+length])
                    else:
                        # For now, just use the data as-is for other frame types
                        uds_data = bytes(msg.data[1:])
                    
                    response = self._process_request(uds_data)
                    if response:
                        # Encode response as ISO-TP single frame
                        resp_len = len(response)
                        if resp_len <= 7:
                            isotp_frame = bytes([resp_len]) + response
                            isotp_frame = isotp_frame.ljust(8, b'\x00')
                        else:
                            # For longer responses, just truncate for now
                            isotp_frame = bytes([7]) + response[:7]
                        
                        resp_msg = CANMessage(
                            arbitration_id=self.ecu_response_id,
                            data=isotp_frame,
                            timestamp=time.time()
                        )
                        self.rx_queue.put(resp_msg)
            except Exception:
                continue
    
    def _process_request(self, data: bytes) -> Optional[bytes]:
        """Process UDS request and generate response"""
        # UDS Service IDs
        DIAGNOSTIC_SESSION_CONTROL = 0x10
        SECURITY_ACCESS = 0x27
        TESTER_PRESENT = 0x3E
        READ_DATA_BY_ID = 0x22
        READ_MEMORY_BY_ADDRESS = 0x23
        
        if not data:
            return None
        
        service = data[0]
        
        # Diagnostic Session Control
        if service == DIAGNOSTIC_SESSION_CONTROL:
            self.session = data[1] if len(data) > 1 else 0x01
            return bytes([service + 0x40, self.session, 0x00, 0x32, 0x01, 0xF4])
        
        # Security Access
        elif service == SECURITY_ACCESS:
            sub = data[1] if len(data) > 1 else 0x01
            
            if sub == 0x01:  # Request seed
                return bytes([service + 0x40, sub]) + self.seed
            
            elif sub == 0x02:  # Send key
                received_key = data[2:6]
                # Accept any key in simulation
                self.security_level = 1
                return bytes([service + 0x40, sub])
        
        # Tester Present
        elif service == TESTER_PRESENT:
            if len(data) > 1 and not (data[1] & 0x80):  # Response required
                return bytes([service + 0x40, 0x00])
            return None
        
        # Read Data By ID
        elif service == READ_DATA_BY_ID:
            did = (data[1] << 8) | data[2] if len(data) >= 3 else 0
            
            # Simulated data
            if did == 0xF190:  # VIN
                return bytes([service + 0x40, data[1], data[2]]) + b'1HD1TEST12345678'
            elif did == 0xF18C:  # Serial
                return bytes([service + 0x40, data[1], data[2]]) + b'SIM123456'
            elif did == 0xF191:  # Hardware
                return bytes([service + 0x40, data[1], data[2]]) + b'HW_V2.0'
            elif did == 0xF195:  # Software version
                return bytes([service + 0x40, data[1], data[2]]) + b'SW_V3.5'
            elif did == 0xF197:  # Calibration
                return bytes([service + 0x40, data[1], data[2]]) + b'CAL_2024'
            else:
                return bytes([0x7F, service, 0x31])  # Request out of range
        
        # Read Memory By Address
        elif service == READ_MEMORY_BY_ADDRESS:
            if self.security_level < 1:
                return bytes([0x7F, service, 0x33])  # Security access denied
            
            # Return simulated data
            return bytes([service + 0x40]) + bytes([0xDE, 0xAD, 0xBE, 0xEF] * 4)
        
        # Default: Service not supported
        return bytes([0x7F, service, 0x11])


# =============================================================================
# Factory Function
# =============================================================================

def create_interface(interface_string: str) -> CANInterface:
    """
    Create CAN interface from string specification
    
    Format: "type:channel" or "type:channel:bitrate"
    
    Examples:
        - "pcan:PCAN_USBBUS1"
        - "socketcan:can0"
        - "serial:COM3"
        - "simulated:test"
    """
    parts = interface_string.split(':')
    interface_type = parts[0].lower()
    
    if interface_type == 'simulated':
        return SimulatedCANInterface()
    
    elif interface_type == 'serial':
        port = parts[1] if len(parts) > 1 else 'COM3'
        return SerialCANInterface(port=port)
    
    elif interface_type in ['pcan', 'socketcan', 'vector', 'kvaser', 'ixxat', 'ni']:
        channel = parts[1] if len(parts) > 1 else 'PCAN_USBBUS1'
        bitrate = int(parts[2]) if len(parts) > 2 else 500000
        return PythonCANInterface(interface=interface_type, channel=channel, bitrate=bitrate)
    
    else:
        raise ValueError(f"Unknown interface type: {interface_type}")

