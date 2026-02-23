"""
ECU Memory Dump Tool

Dumps ECU memory (calibration and tune data).
"""

import os
import json
from datetime import datetime
from typing import Optional, Callable

from ..core import CANInterface, Authenticator, MemoryManager


class ECUDumper:
    """
    ECU Memory Dumper.
    
    Features:
    - Full calibration dump (160KB)
    - Tune extraction (16KB)
    - Automatic backup with metadata
    - Progress reporting
    """
    
    def __init__(self, output_dir: str = 'backups'):
        self.output_dir = output_dir
        self.can: Optional[CANInterface] = None
        self.auth: Optional[Authenticator] = None
        self.memory: Optional[MemoryManager] = None
        
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
    
    def initialize(self, capture_file: str = None) -> bool:
        """
        Initialize CAN interface and authentication.
        
        Args:
            capture_file: Path to capture file for auth
            
        Returns:
            True if initialized successfully
        """
        # Create CAN interface
        self.can = CANInterface()
        self.can.set_log_callback(self.log_callback)
        
        if not self.can.connect():
            return False
        
        # Test CAN quality
        passed, rate = self.can.test_quality()
        if not passed:
            self._log(f"CAN quality too low: {rate*100:.0f}%", 'error')
            self.can.disconnect()
            return False
        
        # Create authenticator
        self.auth = Authenticator(self.can)
        self.auth.set_log_callback(self.log_callback)
        
        # Authenticate
        if not self.auth.full_authenticate(capture_file):
            self.can.disconnect()
            return False
        
        # Create memory manager
        self.memory = MemoryManager(self.can, self.auth)
        self.memory.set_callbacks(self.log_callback, self.progress_callback)
        
        return True
    
    def cleanup(self):
        """Clean up resources."""
        if self.can:
            self.can.disconnect()
    
    def dump_calibration(self, name_prefix: str = 'calibration') -> Optional[str]:
        """
        Dump full calibration region.
        
        Args:
            name_prefix: Prefix for output filename
            
        Returns:
            Path to dump file or None
        """
        if not self.memory:
            self._log("Not initialized", 'error')
            return None
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Read calibration
        self._log("Reading calibration data...", 'info')
        data = self.memory.read_calibration()
        
        if not data:
            self._log("Calibration read failed", 'error')
            return None
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(
            self.output_dir,
            f"{name_prefix}_{timestamp}.bin"
        )
        
        # Save data
        with open(filename, 'wb') as f:
            f.write(data)
        
        # Save metadata
        checksum = MemoryManager.calculate_checksum(data)
        metadata = {
            'timestamp': timestamp,
            'type': 'calibration',
            'address': f"0x{0x7D8000:X}",
            'size': len(data),
            'checksum_sha256': checksum
        }
        
        meta_file = filename + '.json'
        with open(meta_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self._log(f"Calibration saved: {filename}", 'success')
        self._log(f"Checksum: {checksum[:16]}...", 'info')
        
        return filename
    
    def dump_tune(self, name_prefix: str = 'tune') -> Optional[str]:
        """
        Dump tune region (extracted from calibration).
        
        Args:
            name_prefix: Prefix for output filename
            
        Returns:
            Path to dump file or None
        """
        if not self.memory:
            self._log("Not initialized", 'error')
            return None
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Read tune
        self._log("Reading tune data...", 'info')
        data = self.memory.read_tune()
        
        if not data:
            self._log("Tune read failed", 'error')
            return None
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(
            self.output_dir,
            f"{name_prefix}_{timestamp}.bin"
        )
        
        # Save data
        with open(filename, 'wb') as f:
            f.write(data)
        
        # Save metadata
        checksum = MemoryManager.calculate_checksum(data)
        metadata = {
            'timestamp': timestamp,
            'type': 'tune',
            'size': len(data),
            'checksum_sha256': checksum
        }
        
        meta_file = filename + '.json'
        with open(meta_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self._log(f"Tune saved: {filename}", 'success')
        self._log(f"Checksum: {checksum[:16]}...", 'info')
        
        return filename
    
    def full_dump(self) -> dict:
        """
        Perform full dump (calibration + tune extraction).
        
        Returns:
            Dictionary with file paths
        """
        results = {
            'calibration': None,
            'tune': None,
            'success': False
        }
        
        # Dump calibration
        cal_file = self.dump_calibration()
        if cal_file:
            results['calibration'] = cal_file
            
            # Extract tune
            with open(cal_file, 'rb') as f:
                cal_data = f.read()
            
            tune_data = MemoryManager.extract_tune(cal_data)
            if tune_data:
                # Save extracted tune
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                tune_file = os.path.join(
                    self.output_dir,
                    f"tune_extracted_{timestamp}.bin"
                )
                
                with open(tune_file, 'wb') as f:
                    f.write(tune_data)
                
                results['tune'] = tune_file
                self._log(f"Tune extracted: {tune_file}", 'success')
        
        results['success'] = results['calibration'] is not None
        return results

