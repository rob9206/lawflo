"""
ECU Flash Tool - 5 Star Safety

Safe ECU flashing with comprehensive verification.
"""

import os
import json
from datetime import datetime
from typing import Optional, Callable, List

from ..core import CANInterface, Authenticator, MemoryManager
from ..core.memory import MemoryMap


class ECUFlasher:
    """
    Safe ECU Flasher - 5 Star Safety Rating.
    
    Safety Features:
    1. Pre-flight checks
    2. CAN bus quality verification
    3. Triple redundant backups
    4. Block-by-block write verification
    5. Double read-back verification
    6. Full audit logging
    """
    
    BACKUP_LOCATIONS = [
        '.',
        os.path.expanduser('~'),
        os.path.expanduser('~/Documents')
    ]
    
    def __init__(self, backup_dir: str = 'backups'):
        self.backup_dir = backup_dir
        self.can: Optional[CANInterface] = None
        self.auth: Optional[Authenticator] = None
        self.memory: Optional[MemoryManager] = None
        
        self.backup_files: List[str] = []
        self.original_tune: Optional[bytes] = None
        self.audit_log: List[str] = []
        
        self.log_callback: Optional[Callable] = None
        self.progress_callback: Optional[Callable] = None
    
    def set_callbacks(self, log_func: Callable = None,
                      progress_func: Callable = None):
        self.log_callback = log_func
        self.progress_callback = progress_func
    
    def _log(self, message: str, level: str = 'info'):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.audit_log.append(f"[{timestamp}] [{level}] {message}")
        
        if self.log_callback:
            self.log_callback(message, level)
        else:
            prefix = {
                'success': '✓',
                'error': '✗',
                'warning': '⚠',
                'info': '•'
            }
            print(f"{prefix.get(level, '•')} {message}")
    
    def _progress(self, value: float):
        if self.progress_callback:
            self.progress_callback(value)
    
    def preflight_check(self, tune_file: str,
                        capture_file: str = None) -> tuple:
        """
        Perform pre-flight checks.
        
        Returns:
            (passed, error_message)
        """
        errors = []
        
        # Check tune file
        if not os.path.exists(tune_file):
            errors.append(f"Tune file not found: {tune_file}")
        else:
            size = os.path.getsize(tune_file)
            if size != MemoryMap.TUNE_SIZE:
                errors.append(
                    f"Invalid tune size: {size} "
                    f"(expected {MemoryMap.TUNE_SIZE})"
                )
        
        # Check capture file
        if capture_file:
            if not os.path.exists(capture_file):
                errors.append(f"Capture file not found: {capture_file}")
        
        if errors:
            return (False, '\n'.join(errors))
        
        return (True, "All pre-flight checks passed")
    
    def initialize(self, capture_file: str = None) -> bool:
        """Initialize CAN interface and authentication."""
        self.can = CANInterface()
        self.can.set_log_callback(self.log_callback)
        
        if not self.can.connect():
            return False
        
        # Test CAN quality
        self._log("Testing CAN bus quality...", 'info')
        passed, rate = self.can.test_quality()
        self._log(f"CAN quality: {rate*100:.0f}%", 
                  'success' if passed else 'error')
        
        if not passed:
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
    
    def create_backup(self) -> bool:
        """
        Create triple redundant backups of current tune.
        
        Returns:
            True if at least 2 backups created
        """
        self._log("Creating backups of current tune...", 'info')
        
        # Read current tune
        tune_data = self.memory.read_tune()
        
        if not tune_data:
            self._log("Failed to read current tune for backup", 'error')
            return False
        
        self.original_tune = tune_data
        checksum = MemoryManager.calculate_checksum(tune_data)
        
        self._log(f"Original tune checksum: {checksum[:16]}...", 'info')
        
        # Create backups in multiple locations
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metadata = {
            'timestamp': timestamp,
            'type': 'backup_before_flash',
            'size': len(tune_data),
            'checksum_sha256': checksum
        }
        
        self.backup_files = []
        
        for location in self.BACKUP_LOCATIONS:
            try:
                if not os.path.exists(location):
                    continue
                
                backup_dir = os.path.join(location, 'harley_ecu_backups')
                os.makedirs(backup_dir, exist_ok=True)
                
                filename = f"backup_{timestamp}.bin"
                filepath = os.path.join(backup_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(tune_data)
                
                with open(filepath + '.json', 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                self.backup_files.append(filepath)
                self._log(f"Backup: {filepath}", 'success')
                
            except Exception as e:
                self._log(f"Backup to {location} failed: {e}", 'warning')
        
        success = len(self.backup_files) >= 2
        self._log(
            f"{len(self.backup_files)} backups created",
            'success' if success else 'warning'
        )
        
        return success
    
    def flash(self, tune_file: str, capture_file: str = None,
              verify: bool = True, double_verify: bool = True) -> bool:
        """
        Flash tune to ECU with full safety checks.
        
        Args:
            tune_file: Path to tune file (16KB)
            capture_file: Path to capture file
            verify: Perform verification after write
            double_verify: Perform double verification
            
        Returns:
            True if flash successful and verified
        """
        self._log("=" * 50, 'info')
        self._log("SAFE ECU FLASH - 5 STAR SAFETY", 'info')
        self._log("=" * 50, 'info')
        
        success = False
        
        try:
            # Step 1: Pre-flight
            self._log("\n[1/7] Pre-flight checks...", 'info')
            passed, message = self.preflight_check(tune_file, capture_file)
            if not passed:
                self._log(message, 'error')
                return False
            self._log("Pre-flight: PASSED", 'success')
            
            # Load tune data
            with open(tune_file, 'rb') as f:
                new_tune = f.read()
            
            new_checksum = MemoryManager.calculate_checksum(new_tune)
            self._log(f"New tune checksum: {new_checksum[:16]}...", 'info')
            
            # Step 2: Initialize
            self._log("\n[2/7] Connecting...", 'info')
            if not self.initialize(capture_file):
                return False
            
            # Step 3: Backup
            self._log("\n[3/7] Creating backups...", 'info')
            if not self.create_backup():
                self._log("Backup failed - aborting for safety", 'error')
                return False
            
            # Step 4: Re-authenticate for write
            self._log("\n[4/7] Authenticating for write...", 'info')
            if not self.auth.full_authenticate(capture_file):
                return False
            
            # Step 5: Write
            self._log("\n[5/7] Writing tune...", 'info')
            self._log("*** DO NOT INTERRUPT ***", 'warning')
            
            if not self.memory.write_tune(new_tune):
                self._log("WRITE FAILED!", 'error')
                self._log(f"Backup at: {self.backup_files[0]}", 'info')
                return False
            
            self._log("Write complete", 'success')
            
            # Reset ECU
            self._log("Resetting ECU...", 'info')
            self.memory.ecu_reset()
            self.memory.clear_dtc()
            
            # Step 6: Verify
            if verify:
                self._log("\n[6/7] Verifying write...", 'info')
                
                # Wait for ECU to stabilize
                import time
                time.sleep(2)
                
                if not self.memory.verify_write(new_tune):
                    self._log("VERIFICATION FAILED!", 'error')
                    return False
                
                self._log("Verification: PASSED", 'success')
            
            # Step 7: Double verify
            if double_verify:
                self._log("\n[7/7] Double verification...", 'info')
                
                import time
                time.sleep(1)
                
                if not self.memory.verify_write(new_tune):
                    self._log("DOUBLE VERIFICATION FAILED!", 'error')
                    return False
                
                self._log("Double verification: PASSED", 'success')
            
            success = True
            
            self._log("\n" + "=" * 50, 'success')
            self._log("★★★★★ FLASH COMPLETE ★★★★★", 'success')
            self._log("=" * 50, 'success')
            self._log("\nCycle ignition: OFF → 10 seconds → ON", 'info')
            
            return True
            
        except KeyboardInterrupt:
            self._log("\n*** INTERRUPTED ***", 'error')
            self._log("ECU may be in inconsistent state!", 'warning')
            if self.backup_files:
                self._log(f"Restore from: {self.backup_files[0]}", 'info')
            return False
            
        except Exception as e:
            self._log(f"\n*** ERROR: {e} ***", 'error')
            return False
            
        finally:
            self.cleanup()
            self._save_audit_log()
    
    def _save_audit_log(self):
        """Save audit log to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flash_audit_{timestamp}.log"
            
            with open(filename, 'w') as f:
                f.write("HARLEY ECU FLASH AUDIT LOG\n")
                f.write("=" * 50 + "\n\n")
                f.write('\n'.join(self.audit_log))
            
            self._log(f"Audit log: {filename}", 'info')
            
        except Exception:
            pass

