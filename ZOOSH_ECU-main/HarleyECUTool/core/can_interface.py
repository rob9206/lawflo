"""
CAN Bus Interface Module

Handles low-level CAN communication with PCAN adapter.
Includes ISO-TP message framing and flow control.
"""

import time
from typing import Optional, Callable

try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    CAN_AVAILABLE = False


class CANInterface:
    """
    CAN Bus communication handler for PCAN adapters.
    
    Features:
    - Single and multi-frame ISO-TP messaging
    - Automatic flow control handling
    - Connection retry logic
    - Statistics tracking
    """
    
    # CAN IDs
    TX_ID = 0x7E0       # Tester -> ECU
    RX_ID = 0x7E8       # ECU -> Tester
    BROADCAST_ID = 0x7DF  # Functional addressing
    
    def __init__(self, channel: str = 'PCAN_USBBUS1', bitrate: int = 500000):
        self.channel = channel
        self.bitrate = bitrate
        self.bus = None
        self.stats = {'tx': 0, 'rx': 0, 'errors': 0}
        self.log_callback: Optional[Callable] = None
    
    def set_log_callback(self, callback: Callable):
        """Set callback for logging messages."""
        self.log_callback = callback
    
    def _log(self, message: str, level: str = 'info'):
        if self.log_callback:
            self.log_callback(message, level)
    
    @property
    def is_connected(self) -> bool:
        return self.bus is not None
    
    def connect(self, retries: int = 3, delay: float = 0.5) -> bool:
        """
        Connect to PCAN adapter.
        
        Args:
            retries: Number of connection attempts
            delay: Delay between retries
            
        Returns:
            True if connected successfully
        """
        if not CAN_AVAILABLE:
            self._log("python-can module not installed", 'error')
            return False
        
        for attempt in range(retries):
            try:
                self.bus = can.interface.Bus(
                    interface='pcan',
                    channel=self.channel,
                    bitrate=self.bitrate
                )
                self._log(f"Connected to {self.channel}", 'success')
                return True
            except Exception as e:
                self._log(f"Connection attempt {attempt+1}: {e}", 'warning')
                time.sleep(delay)
        
        self._log("Failed to connect to PCAN", 'error')
        return False
    
    def disconnect(self):
        """Disconnect from PCAN adapter."""
        if self.bus:
            try:
                self.bus.shutdown()
            except Exception:
                pass
            self.bus = None
            self._log("Disconnected", 'info')
    
    def send_frame(self, arb_id: int, data: bytes) -> bool:
        """
        Send a single CAN frame with ISO-TP single-frame format.
        
        Args:
            arb_id: CAN arbitration ID
            data: Payload data (max 7 bytes)
            
        Returns:
            True if sent successfully
        """
        if not self.bus:
            return False
        
        try:
            # ISO-TP single frame: [length | data...]
            frame = bytes([len(data)]) + data
            frame = frame + bytes(8 - len(frame))  # Pad to 8 bytes
            
            msg = can.Message(
                arbitration_id=arb_id,
                data=frame,
                is_extended_id=False
            )
            self.bus.send(msg)
            self.stats['tx'] += 1
            return True
        except Exception as e:
            self.stats['errors'] += 1
            self._log(f"Send error: {e}", 'error')
            return False
    
    def send_multiframe(self, arb_id: int, data: bytes,
                        timeout: float = 2.0) -> bool:
        """
        Send multi-frame ISO-TP message with flow control.
        
        Args:
            arb_id: CAN arbitration ID
            data: Payload data (any length)
            timeout: Timeout for flow control response
            
        Returns:
            True if sent successfully
        """
        if not self.bus:
            return False
        
        # Single frame if <= 7 bytes
        if len(data) <= 7:
            return self.send_frame(arb_id, data)
        
        try:
            length = len(data)
            
            # First Frame: [1x xx | data...]
            # x xxx = 12-bit length
            ff = bytes([
                0x10 | ((length >> 8) & 0x0F),
                length & 0xFF
            ]) + data[:6]
            
            msg = can.Message(
                arbitration_id=arb_id,
                data=ff,
                is_extended_id=False
            )
            self.bus.send(msg)
            self.stats['tx'] += 1
            
            # Wait for Flow Control
            fc = self.bus.recv(timeout=timeout)
            if not fc or (fc.data[0] & 0xF0) != 0x30:
                self._log("No flow control received", 'error')
                self.stats['errors'] += 1
                return False
            self.stats['rx'] += 1
            
            # Extract FC parameters
            # fc.data[1] = block size (0 = no limit)
            # fc.data[2] = separation time (ms)
            sep_time = fc.data[2] / 1000.0 if fc.data[2] < 0x80 else 0.001
            
            # Consecutive Frames: [2x | data...]
            remaining = data[6:]
            seq = 1
            
            while remaining:
                chunk = remaining[:7]
                remaining = remaining[7:]
                
                cf = bytes([0x20 | (seq & 0x0F)]) + chunk
                cf = cf + bytes(8 - len(cf))
                
                msg = can.Message(
                    arbitration_id=arb_id,
                    data=cf,
                    is_extended_id=False
                )
                self.bus.send(msg)
                self.stats['tx'] += 1
                
                seq = (seq + 1) & 0x0F
                time.sleep(sep_time)
            
            return True
            
        except Exception as e:
            self.stats['errors'] += 1
            self._log(f"Multi-frame send error: {e}", 'error')
            return False
    
    def recv_response(self, timeout: float = 2.0,
                      rx_id: int = None) -> Optional[bytes]:
        """
        Receive ISO-TP response with automatic assembly.
        
        Args:
            timeout: Receive timeout in seconds
            rx_id: Expected response CAN ID (default: RX_ID)
            
        Returns:
            Assembled response data or None
        """
        if not self.bus:
            return None
        
        rx_id = rx_id or self.RX_ID
        
        try:
            start = time.time()
            data = bytearray()
            expected = 0
            
            while time.time() - start < timeout:
                msg = self.bus.recv(timeout=0.1)
                if not msg or msg.arbitration_id != rx_id:
                    continue
                
                self.stats['rx'] += 1
                pci = msg.data[0]
                frame_type = pci >> 4
                
                # Single Frame
                if frame_type == 0:
                    length = pci & 0x0F
                    return bytes(msg.data[1:1+length])
                
                # First Frame
                if frame_type == 1:
                    expected = ((pci & 0x0F) << 8) | msg.data[1]
                    data.extend(msg.data[2:8])
                    
                    # Send Flow Control
                    fc = can.Message(
                        arbitration_id=self.TX_ID,
                        data=bytes([0x30, 0x00, 0x00, 0, 0, 0, 0, 0]),
                        is_extended_id=False
                    )
                    self.bus.send(fc)
                    self.stats['tx'] += 1
                
                # Consecutive Frame
                if frame_type == 2:
                    data.extend(msg.data[1:8])
                    if len(data) >= expected:
                        return bytes(data[:expected])
            
            return bytes(data) if data else None
            
        except Exception as e:
            self.stats['errors'] += 1
            self._log(f"Receive error: {e}", 'error')
            return None
    
    def send_broadcast(self, data: bytes) -> bool:
        """Send broadcast message (functional addressing)."""
        if not self.bus:
            return False
        
        try:
            frame = bytes([len(data)]) + data
            frame = frame + bytes(8 - len(frame))
            
            msg = can.Message(
                arbitration_id=self.BROADCAST_ID,
                data=frame,
                is_extended_id=False
            )
            self.bus.send(msg)
            self.stats['tx'] += 1
            return True
        except Exception:
            self.stats['errors'] += 1
            return False
    
    def drain(self, timeout: float = 0.1, max_msgs: int = 100):
        """Drain pending messages from receive buffer."""
        if not self.bus:
            return
        
        count = 0
        while count < max_msgs:
            msg = self.bus.recv(timeout=timeout)
            if not msg:
                break
            count += 1
    
    def test_quality(self, tests: int = 20,
                     threshold: float = 0.95) -> tuple:
        """
        Test CAN bus quality with TesterPresent pings.
        
        Args:
            tests: Number of test pings
            threshold: Required success rate
            
        Returns:
            (passed, success_rate)
        """
        successes = 0
        
        for _ in range(tests):
            self.send_frame(self.TX_ID, bytes([0x3E, 0x00]))
            resp = self.recv_response(timeout=0.5)
            
            if resp and len(resp) > 0 and resp[0] == 0x7E:
                successes += 1
            
            time.sleep(0.05)
        
        rate = successes / tests
        return (rate >= threshold, rate)
    
    def get_stats(self) -> dict:
        """Get communication statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset communication statistics."""
        self.stats = {'tx': 0, 'rx': 0, 'errors': 0}

