"""
Harley ECU Tool - Core Module

Low-level communication and protocol handling.
"""

from .can_interface import CANInterface
from .protocol import UDSProtocol
from .auth import Authenticator
from .memory import MemoryManager

__all__ = ['CANInterface', 'UDSProtocol', 'Authenticator', 'MemoryManager']

