"""
ECU Communication Tool

A comprehensive tool for ECU communication, diagnostics, and tuning.
Supports Harley-Davidson, Indian, Victory and other vehicles with
Delphi ECUs using UDS protocol over CAN bus.

Features:
- Security access using Dynojet Blowfish key
- Memory read/write
- Flash dump and programming
- DTC read/clear
- Multiple CAN interface support

Usage:
    from ECUTool import ECUTool
    
    tool = ECUTool()
    tool.connect("pcan:PCAN_USBBUS1")
    tool.start_session()
    tool.security_access()
    
    # Read VIN
    vin = tool.read_vin()
    
    # Read memory
    data = tool.read_memory(0x10000, 0x1000)
    
    tool.disconnect()
"""

from .ecu_tool import ECUTool, FlashRegion, DTCInfo
from .ecu_protocol import (
    UDSProtocol, SecurityAccess, ISOTP,
    CANID, UDS, NRC, DID, DYNOJET_KEY
)
from .can_interface import (
    CANInterface, CANMessage,
    PythonCANInterface, SerialCANInterface, SimulatedCANInterface,
    create_interface
)

__version__ = "1.0.0"
__author__ = "ECU Tool"

__all__ = [
    'ECUTool',
    'FlashRegion',
    'DTCInfo',
    'UDSProtocol',
    'SecurityAccess',
    'ISOTP',
    'CANID',
    'UDS',
    'NRC',
    'DID',
    'DYNOJET_KEY',
    'CANInterface',
    'CANMessage',
    'PythonCANInterface',
    'SerialCANInterface',
    'SimulatedCANInterface',
    'create_interface',
]

