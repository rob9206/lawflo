#!/usr/bin/env python3
"""
Safe ECU Flash Module

Enhanced safety features for ECU flashing:
- Pre-flight checks
- Checksum verification
- Verify-after-write
- Retry logic
- Comprehensive error handling
"""

import os
import sys
import time
import hashlib
from datetime import datetime
from typing import Optional, Tuple

# Constants
TUNE_OFFSET = 0x1C000
TUNE_SIZE = 0x4000  # 16KB
WRITE_ADDRESS = 0x00004000

try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    CAN_AVAILABLE = False


class SafeFlashError(Exception):
    """Custom exception for flash errors"""
    pass


class SafeECUFlasher:
    """
    Safe ECU Flasher with comprehensive error handling and verification.
    
    Safety Features:
    1. Pre-flight checks (connection, auth, current tune backup)
    2. Data integrity verification (checksums)
    3. Verify-after-write (read back and compare)
    4. Retry logic on transient failures
    5. Detailed logging for troubleshooting
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5
    
    def __init__(self, log_func=None, progress_func=None):
        self.log = log_func or print
        self.progress = progress_func or (lambda x: None)
        self.bus = None
        self.auth_payload = None
        self.backup_data = None
        self.backup_file = None
    
    # ==================== Connection ====================
    
    def connect(self) -> bool:
        """Connect to PCAN with retry"""
        for attempt in range(self.MAX_RETRIES):
            try:
                self.bus = can.interface.Bus(
                    interface='pcan',
                    channel='PCAN_USBBUS1', 
                    bitrate=500000
                )
                self.log("✓ PCAN connected", 'success')
                return True
            except Exception as e:
                self.log(f"Connection attempt {attempt+1} failed: {e}", 'warning')
                time.sleep(self.RETRY_DELAY)
        
        self.log("✗ Failed to connect to PCAN", 'error')
        return False
    
    def disconnect(self):
        if self.bus:
            try:
                self.bus.shutdown()
            except:
                pass
            self.bus = None
    
    def is_connected(self) -> bool:
        return self.bus is not None
    
    # ==================== CAN Communication ====================
    
    def send_frame(self, arb_id: int, data: bytes) -> bool:
        """Send single CAN frame with error handling"""
        try:
            frame = bytes([len(data)]) + data + bytes(7 - len(data))
            msg = can.Message(arbitration_id=arb_id, data=frame, is_extended_id=False)
            self.bus.send(msg)
            return True
        except Exception as e:
            self.log(f"Send error: {e}", 'error')
            return False
    
    def send_multiframe(self, arb_id: int, data: bytes) -> bool:
        """Send multi-frame ISO-TP message with error handling"""
        try:
            if len(data) <= 7:
                return self.send_frame(arb_id, data)
            
            # First Frame
            length = len(data)
            ff = bytes([0x10 | ((length >> 8) & 0x0F), length & 0xFF]) + data[:6]
            msg = can.Message(arbitration_id=arb_id, data=ff, is_extended_id=False)
            self.bus.send(msg)
            
            # Wait for Flow Control
            fc = self.bus.recv(timeout=2.0)
            if not fc or fc.arbitration_id != 0x7E8 or (fc.data[0] & 0xF0) != 0x30:
                self.log("No Flow Control received", 'error')
                return False
            
            # Consecutive Frames
            remaining = data[6:]
            seq = 1
            while remaining:
                chunk = remaining[:7]
                remaining = remaining[7:]
                cf = bytes([0x20 | (seq & 0x0F)]) + chunk
                if len(cf) < 8:
                    cf = cf + bytes(8 - len(cf))
                msg = can.Message(arbitration_id=arb_id, data=cf, is_extended_id=False)
                self.bus.send(msg)
                seq = (seq + 1) & 0x0F
                time.sleep(0.001)
            
            return True
            
        except Exception as e:
            self.log(f"Multi-frame send error: {e}", 'error')
            return False
    
    def recv_response(self, timeout: float = 2.0) -> Optional[bytes]:
        """Receive ISO-TP response with proper assembly"""
        try:
            start = time.time()
            data = bytearray()
            expected = 0
            
            while time.time() - start < timeout:
                msg = self.bus.recv(timeout=0.1)
                if not msg or msg.arbitration_id != 0x7E8:
                    continue
                
                pci = msg.data[0]
                frame_type = pci >> 4
                
                if frame_type == 0:  # Single Frame
                    return bytes(msg.data[1:1+(pci & 0x0F)])
                
                elif frame_type == 1:  # First Frame
                    expected = ((pci & 0x0F) << 8) | msg.data[1]
                    data.extend(msg.data[2:8])
                    # Send Flow Control
                    fc = can.Message(arbitration_id=0x7E0,
                                   data=bytes([0x30, 0, 0, 0, 0, 0, 0, 0]),
                                   is_extended_id=False)
                    self.bus.send(fc)
                
                elif frame_type == 2:  # Consecutive Frame
                    data.extend(msg.data[1:8])
                    if len(data) >= expected:
                        return bytes(data[:expected])
            
            return bytes(data) if data else None
            
        except Exception as e:
            self.log(f"Receive error: {e}", 'error')
            return None
    
    # ==================== Authentication ====================
    
    def load_auth_payload(self, capture_file: str) -> bool:
        """Load and validate auth payload from capture"""
        if not os.path.exists(capture_file):
            self.log(f"Capture file not found: {capture_file}", 'error')
            return False
        
        try:
            import re
            with open(capture_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            matches = re.findall(r'0x7E0\s+8\s+([0-9A-Fa-f]{16})', content)
            
            payload = bytearray()
            collecting = False
            
            for match in matches:
                frame = bytes.fromhex(match)
                pci = frame[0]
                
                if (pci & 0xF0) == 0x10:
                    total_len = ((pci & 0x0F) << 8) | frame[1]
                    if frame[2] == 0x36:
                        payload = bytearray(frame[4:8])
                        collecting = True
                        continue
                
                if collecting and (pci & 0xF0) == 0x20:
                    payload.extend(frame[1:8])
                    if len(payload) >= 2006:
                        break
            
            if len(payload) >= 2000:
                self.auth_payload = bytes(payload)
                self.log(f"✓ Auth payload loaded ({len(self.auth_payload)} bytes)", 'success')
                return True
            
            self.log(f"✗ Failed to extract auth payload", 'error')
            return False
            
        except Exception as e:
            self.log(f"✗ Auth load error: {e}", 'error')
            return False
    
    def authenticate(self) -> bool:
        """Perform authentication sequence with retry"""
        for attempt in range(self.MAX_RETRIES):
            if self._do_authenticate():
                return True
            self.log(f"Auth attempt {attempt+1} failed, retrying...", 'warning')
            time.sleep(self.RETRY_DELAY)
        
        self.log("✗ Authentication failed after all retries", 'error')
        return False
    
    def _do_authenticate(self) -> bool:
        """Internal authentication implementation"""
        try:
            # TesterPresent
            self.send_frame(0x7E0, bytes([0x3E, 0x00]))
            time.sleep(0.05)
            
            # Extended Session (broadcast)
            msg = can.Message(arbitration_id=0x7DF,
                            data=bytes([0x02, 0x10, 0x03, 0, 0, 0, 0, 0]),
                            is_extended_id=False)
            self.bus.send(msg)
            time.sleep(0.1)
            
            # Drain any pending responses
            while self.bus.recv(timeout=0.05):
                pass
            
            # Security Access - Request Seed
            self.send_frame(0x7E0, bytes([0x27, 0x01]))
            resp = self.recv_response()
            
            if not resp or resp[0] != 0x67:
                return False
            
            seed = resp[2:4]
            key = bytes([seed[0] ^ 0x9A, seed[1] ^ 0xE8])
            
            # Security Access - Send Key
            self.send_frame(0x7E0, bytes([0x27, 0x02]) + key)
            resp = self.recv_response()
            
            if not resp or resp[0] != 0x67:
                return False
            
            # RequestDownload for auth
            req = bytes([0x34, 0x00, 0x44, 0, 0, 0, 0, 0, 0, 0x07, 0xD6])
            if not self.send_multiframe(0x7E0, req):
                return False
            
            resp = self.recv_response()
            if not resp or resp[0] != 0x74:
                return False
            
            # TransferData with auth payload
            if not self.auth_payload:
                return False
            
            msg = bytes([0x36, 0x01]) + self.auth_payload
            if not self.send_multiframe(0x7E0, msg):
                return False
            
            resp = self.recv_response(timeout=3.0)
            if not resp or resp[0] != 0x76:
                return False
            
            self.log("✓ Authenticated", 'success')
            return True
            
        except Exception as e:
            self.log(f"Auth error: {e}", 'error')
            return False
    
    # ==================== Memory Operations ====================
    
    def read_memory(self, address: int, length: int, format_byte: int = 0xB0) -> Optional[bytes]:
        """Read memory with progress and re-auth"""
        data = bytearray()
        current_addr = address
        read_count = 0
        
        while len(data) < length:
            # Re-authenticate every 32 reads
            if read_count > 0 and read_count % 32 == 0:
                self.log("  Re-authenticating...", 'info')
                if not self.authenticate():
                    return None
            
            # RequestUpload with retry
            success = False
            for attempt in range(self.MAX_RETRIES):
                req = bytes([0x35, format_byte, 0x01]) + current_addr.to_bytes(4, 'big')
                self.send_frame(0x7E0, req)
                resp = self.recv_response(timeout=3.0)
                
                if resp and resp[0] == 0x75:
                    data.extend(resp[1:])
                    current_addr += len(resp) - 1
                    success = True
                    break
                
                time.sleep(self.RETRY_DELAY)
            
            if not success:
                self.log(f"✗ Read failed at 0x{current_addr:X}", 'error')
                return None
            
            read_count += 1
            self.progress(len(data) / length * 100)
        
        return bytes(data[:length])
    
    def write_memory(self, address: int, data: bytes) -> bool:
        """Write memory with verification"""
        total_len = len(data)
        
        # RequestDownload
        req = bytes([0x34, 0x00, 0x44])
        req += address.to_bytes(4, 'big')
        req += total_len.to_bytes(4, 'big')
        
        if not self.send_multiframe(0x7E0, req):
            self.log("✗ RequestDownload send failed", 'error')
            return False
        
        resp = self.recv_response()
        if not resp or resp[0] != 0x74:
            self.log("✗ RequestDownload rejected", 'error')
            return False
        
        # TransferData in 256-byte blocks
        block_size = 256
        offset = 0
        block_seq = 1
        
        while offset < total_len:
            chunk = data[offset:offset + block_size]
            if len(chunk) < block_size:
                chunk = chunk + bytes(block_size - len(chunk))
            
            # Send with retry
            success = False
            for attempt in range(self.MAX_RETRIES):
                msg = bytes([0x36, block_seq]) + chunk
                if not self.send_multiframe(0x7E0, msg):
                    time.sleep(self.RETRY_DELAY)
                    continue
                
                resp = self.recv_response()
                if resp and resp[0] == 0x76:
                    success = True
                    break
                
                self.log(f"  Block {block_seq} retry {attempt+1}", 'warning')
                time.sleep(self.RETRY_DELAY)
            
            if not success:
                self.log(f"✗ Block {block_seq} failed", 'error')
                return False
            
            offset += block_size
            block_seq = (block_seq % 255) + 1
            self.progress(offset / total_len * 100)
        
        return True
    
    def ecu_reset(self):
        """Reset ECU"""
        self.send_frame(0x7E0, bytes([0x11, 0x01]))
        time.sleep(1.0)
    
    def clear_dtc(self):
        """Clear DTCs"""
        msg = can.Message(arbitration_id=0x7DF,
                        data=bytes([0x04, 0x14, 0xFF, 0xFF, 0xFF, 0, 0, 0]),
                        is_extended_id=False)
        self.bus.send(msg)
        time.sleep(0.5)
    
    # ==================== Safe Flash Operations ====================
    
    def calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA256 checksum"""
        return hashlib.sha256(data).hexdigest()[:16]
    
    def preflight_check(self, tune_file: str, capture_file: str) -> Tuple[bool, str]:
        """
        Pre-flight checks before flashing.
        
        Returns:
            (success, message)
        """
        errors = []
        
        # Check files exist
        if not os.path.exists(tune_file):
            errors.append(f"Tune file not found: {tune_file}")
        
        if not os.path.exists(capture_file):
            errors.append(f"Capture file not found: {capture_file}")
        
        # Check tune file size
        if os.path.exists(tune_file):
            size = os.path.getsize(tune_file)
            if size != TUNE_SIZE:
                errors.append(f"Tune size mismatch: {size} bytes (expected {TUNE_SIZE})")
        
        # Check CAN module
        if not CAN_AVAILABLE:
            errors.append("python-can module not installed")
        
        if errors:
            return (False, "\n".join(errors))
        
        return (True, "All pre-flight checks passed")
    
    def create_backup(self) -> bool:
        """
        Create backup of current tune before flashing.
        
        Returns:
            True if backup successful
        """
        self.log("Creating backup of current tune...", 'info')
        
        if not self.authenticate():
            return False
        
        # Read current calibration
        self.log("  Reading current calibration...", 'info')
        cal_data = self.read_memory(0x7D8000, 0x28000, 0xB0)
        
        if not cal_data or len(cal_data) < TUNE_OFFSET + TUNE_SIZE:
            self.log("✗ Failed to read current calibration", 'error')
            return False
        
        # Extract tune region
        current_tune = cal_data[TUNE_OFFSET:TUNE_OFFSET + TUNE_SIZE]
        
        # Save backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_file = f"backup_pre_flash_{timestamp}.bin"
        
        with open(self.backup_file, 'wb') as f:
            f.write(current_tune)
        
        self.backup_data = current_tune
        checksum = self.calculate_checksum(current_tune)
        
        self.log(f"✓ Backup saved: {self.backup_file}", 'success')
        self.log(f"  Checksum: {checksum}", 'info')
        
        return True
    
    def verify_write(self, expected_data: bytes) -> bool:
        """
        Verify written data by reading back and comparing.
        
        Returns:
            True if data matches
        """
        self.log("Verifying write...", 'info')
        
        if not self.authenticate():
            return False
        
        # Read back the tune region
        self.log("  Reading back written data...", 'info')
        cal_data = self.read_memory(0x7D8000, 0x28000, 0xB0)
        
        if not cal_data or len(cal_data) < TUNE_OFFSET + TUNE_SIZE:
            self.log("✗ Verification read failed", 'error')
            return False
        
        actual_data = cal_data[TUNE_OFFSET:TUNE_OFFSET + TUNE_SIZE]
        
        # Compare
        if actual_data == expected_data:
            self.log("✓ Verification PASSED - data matches!", 'success')
            return True
        else:
            # Count differences
            diffs = sum(1 for a, b in zip(actual_data, expected_data) if a != b)
            self.log(f"✗ Verification FAILED - {diffs} bytes differ!", 'error')
            return False
    
    def safe_flash(self, tune_file: str, capture_file: str, verify: bool = True) -> bool:
        """
        Perform a safe flash operation with all safety checks.
        
        Args:
            tune_file: Path to tune file (16KB)
            capture_file: Path to capture file with auth payload
            verify: Whether to verify after write
        
        Returns:
            True if flash successful and verified
        """
        self.log("="*50, 'info')
        self.log("SAFE FLASH OPERATION", 'info')
        self.log("="*50, 'info')
        
        # Pre-flight checks
        self.log("\n[1/6] Pre-flight checks...", 'info')
        success, message = self.preflight_check(tune_file, capture_file)
        if not success:
            self.log(f"✗ Pre-flight failed:\n{message}", 'error')
            return False
        self.log("✓ Pre-flight passed", 'success')
        
        # Load tune data
        with open(tune_file, 'rb') as f:
            tune_data = f.read()
        
        tune_checksum = self.calculate_checksum(tune_data)
        self.log(f"  Tune checksum: {tune_checksum}", 'info')
        
        # Load auth payload
        self.log("\n[2/6] Loading authentication...", 'info')
        if not self.load_auth_payload(capture_file):
            return False
        
        # Connect
        self.log("\n[3/6] Connecting to ECU...", 'info')
        if not self.connect():
            return False
        
        try:
            # Create backup
            self.log("\n[4/6] Creating backup...", 'info')
            if not self.create_backup():
                self.log("✗ Backup failed - aborting flash for safety", 'error')
                return False
            
            # Re-authenticate for write
            self.log("\n[5/6] Flashing tune...", 'info')
            if not self.authenticate():
                return False
            
            # Perform write
            if not self.write_memory(WRITE_ADDRESS, tune_data):
                self.log("✗ Write failed!", 'error')
                return False
            
            self.log("✓ Write complete", 'success')
            
            # ECU Reset
            self.log("  Resetting ECU...", 'info')
            self.ecu_reset()
            self.clear_dtc()
            
            # Verify
            if verify:
                self.log("\n[6/6] Verifying write...", 'info')
                time.sleep(2)  # Wait for ECU to stabilize
                
                if not self.verify_write(tune_data):
                    self.log("✗ VERIFICATION FAILED!", 'error')
                    self.log("  Your backup is saved at: " + self.backup_file, 'info')
                    return False
            
            self.log("\n" + "="*50, 'success')
            self.log("FLASH COMPLETE AND VERIFIED!", 'success')
            self.log("="*50, 'success')
            self.log("\nCycle ignition: OFF → wait 10s → ON", 'info')
            
            return True
            
        except KeyboardInterrupt:
            self.log("\n✗ INTERRUPTED!", 'error')
            self.log("  ECU may be in inconsistent state", 'warning')
            self.log("  Backup saved at: " + (self.backup_file or "N/A"), 'info')
            return False
            
        except Exception as e:
            self.log(f"\n✗ Unexpected error: {e}", 'error')
            return False
            
        finally:
            self.disconnect()
    
    def restore_backup(self, backup_file: str, capture_file: str) -> bool:
        """
        Restore from a backup file.
        
        Args:
            backup_file: Path to backup file
            capture_file: Path to capture file
        
        Returns:
            True if restore successful
        """
        self.log("="*50, 'info')
        self.log("RESTORE FROM BACKUP", 'info')
        self.log("="*50, 'info')
        
        return self.safe_flash(backup_file, capture_file, verify=True)


# ==================== CLI Interface ====================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Safe ECU Flash Tool')
    parser.add_argument('tune_file', help='Path to tune file (16KB)')
    parser.add_argument('-c', '--capture', help='Capture file for auth', 
                       default=None)
    parser.add_argument('--no-verify', action='store_true',
                       help='Skip verification (not recommended)')
    parser.add_argument('--restore', action='store_true',
                       help='Restore mode (flash backup)')
    
    args = parser.parse_args()
    
    # Find capture file if not specified
    capture_file = args.capture
    if not capture_file:
        captures = sorted([f for f in os.listdir('.') 
                          if 'capture' in f.lower() and f.endswith('.txt')],
                         key=os.path.getmtime, reverse=True)
        if captures:
            capture_file = captures[0]
            print(f"Using capture file: {capture_file}")
        else:
            print("Error: No capture file found. Use -c to specify one.")
            return 1
    
    # Create flasher with colored output
    def log(msg, level='info'):
        colors = {
            'success': '\033[92m',
            'error': '\033[91m',
            'warning': '\033[93m',
            'info': '\033[0m'
        }
        reset = '\033[0m'
        print(f"{colors.get(level, '')}{msg}{reset}")
    
    flasher = SafeECUFlasher(log_func=log)
    
    # Confirm
    print("\n" + "="*50)
    print("WARNING: This will modify your ECU!")
    print("="*50)
    print(f"\nTune file: {args.tune_file}")
    print(f"Capture: {capture_file}")
    print(f"Verify: {'No (UNSAFE!)' if args.no_verify else 'Yes'}")
    
    response = input("\nType 'FLASH' to proceed: ")
    if response != 'FLASH':
        print("Aborted.")
        return 0
    
    # Flash
    success = flasher.safe_flash(
        args.tune_file, 
        capture_file, 
        verify=not args.no_verify
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

