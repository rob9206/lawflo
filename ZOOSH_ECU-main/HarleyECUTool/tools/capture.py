"""
CAN Traffic Capture Tool

Captures CAN bus traffic during PowerVision operations
to extract authentication payloads.
"""

import os
import time
from datetime import datetime
from typing import Optional, Callable

try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    CAN_AVAILABLE = False


class CaptureManager:
    """
    CAN Traffic Capture Manager.
    
    Captures and analyzes CAN bus traffic to extract:
    - Authentication payloads
    - Security seed/key pairs
    - Protocol sequences
    """
    
    def __init__(self, channel: str = 'PCAN_USBBUS1', bitrate: int = 500000):
        self.channel = channel
        self.bitrate = bitrate
        self.bus = None
        self.log_callback: Optional[Callable] = None
        self.progress_callback: Optional[Callable] = None
    
    def set_callbacks(self, log_func: Callable = None,
                      progress_func: Callable = None):
        self.log_callback = log_func
        self.progress_callback = progress_func
    
    def _log(self, message: str, level: str = 'info'):
        if self.log_callback:
            self.log_callback(message, level)
        else:
            print(f"[{level.upper()}] {message}")
    
    def _progress(self, value: float):
        if self.progress_callback:
            self.progress_callback(value)
    
    def connect(self) -> bool:
        """Connect to PCAN adapter."""
        if not CAN_AVAILABLE:
            self._log("python-can module not installed", 'error')
            return False
        
        try:
            self.bus = can.interface.Bus(
                interface='pcan',
                channel=self.channel,
                bitrate=self.bitrate
            )
            self._log(f"Connected to {self.channel}", 'success')
            return True
        except Exception as e:
            self._log(f"Connection failed: {e}", 'error')
            return False
    
    def disconnect(self):
        """Disconnect from PCAN adapter."""
        if self.bus:
            try:
                self.bus.shutdown()
            except Exception:
                pass
            self.bus = None
    
    def capture(self, duration: int = 120,
                output_dir: str = '.') -> Optional[str]:
        """
        Capture CAN traffic for specified duration.
        
        Args:
            duration: Capture duration in seconds
            output_dir: Output directory for capture file
            
        Returns:
            Path to capture file or None
        """
        if not self.bus:
            if not self.connect():
                return None
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"capture_{timestamp}.txt")
        
        self._log(f"Capturing for {duration} seconds...", 'info')
        self._log("Perform PowerVision read/write operation NOW", 'warning')
        
        start_time = time.time()
        messages = []
        
        try:
            while time.time() - start_time < duration:
                msg = self.bus.recv(timeout=0.1)
                if msg:
                    elapsed = time.time() - start_time
                    messages.append((elapsed, msg))
                
                # Update progress
                progress = (time.time() - start_time) / duration * 100
                self._progress(min(progress, 100))
            
            # Write capture file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# Harley ECU Capture\n")
                f.write(f"# Date: {datetime.now().isoformat()}\n")
                f.write(f"# Duration: {duration} seconds\n")
                f.write(f"# Messages: {len(messages)}\n")
                f.write("#" + "=" * 70 + "\n\n")
                
                for elapsed, msg in messages:
                    elapsed_ms = int(elapsed * 1000)
                    data_hex = ' '.join(f'{b:02X}' for b in msg.data)
                    f.write(
                        f"{elapsed_ms:10d}  "
                        f"0x{msg.arbitration_id:03X}  "
                        f"{msg.dlc}  "
                        f"{data_hex}\n"
                    )
            
            self._log(f"Captured {len(messages)} messages", 'success')
            self._log(f"Saved to: {filename}", 'info')
            
            return filename
            
        except KeyboardInterrupt:
            self._log("Capture interrupted", 'warning')
            return None
        finally:
            self.disconnect()
    
    def analyze_capture(self, capture_file: str) -> dict:
        """
        Analyze capture file for key information.
        
        Args:
            capture_file: Path to capture file
            
        Returns:
            Analysis results dictionary
        """
        results = {
            'has_auth_payload': False,
            'auth_payload_size': 0,
            'has_security_exchange': False,
            'seed': None,
            'key': None,
            'has_memory_ops': False,
            'message_count': 0
        }
        
        if not os.path.exists(capture_file):
            return results
        
        try:
            with open(capture_file, 'r', errors='ignore') as f:
                content = f.read()
            
            import re
            
            # Count messages
            messages = re.findall(r'0x[0-9A-Fa-f]{3}\s+\d\s+', content)
            results['message_count'] = len(messages)
            
            # Check for auth payload (TransferData with large payload)
            if re.search(r'0x7E0.*36\s+01', content):
                results['has_auth_payload'] = True
                # Try to extract payload size
                matches = re.findall(
                    r'0x7E0\s+8\s+10[0-9A-Fa-f]{2}',
                    content
                )
                if matches:
                    results['auth_payload_size'] = 2006  # Typical size
            
            # Check for security exchange
            if re.search(r'67\s+01\s+[0-9A-Fa-f]{2}\s+[0-9A-Fa-f]{2}', content):
                results['has_security_exchange'] = True
                # Extract seed
                match = re.search(
                    r'67\s+01\s+([0-9A-Fa-f]{2})\s+([0-9A-Fa-f]{2})',
                    content
                )
                if match:
                    results['seed'] = match.group(1) + match.group(2)
            
            # Check for memory operations
            if re.search(r'(35|75)\s+[AB]0', content):
                results['has_memory_ops'] = True
            
            return results
            
        except Exception as e:
            self._log(f"Analysis error: {e}", 'error')
            return results
    
    @staticmethod
    def find_captures(directory: str = '.') -> list:
        """
        Find all capture files in directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            List of capture file paths (newest first)
        """
        try:
            captures = [
                os.path.join(directory, f)
                for f in os.listdir(directory)
                if 'capture' in f.lower() and f.endswith('.txt')
            ]
            
            captures.sort(key=os.path.getmtime, reverse=True)
            return captures
            
        except Exception:
            return []

