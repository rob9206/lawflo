#!/usr/bin/env python3
"""
Safe Write Test - Read-Verify Cycle

This script tests the write functionality SAFELY by:
1. Reading current calibration from ECU
2. Writing the SAME data back
3. Reading again and comparing

If read-back matches, the write worked correctly.
Since we're writing the same data, even if something goes wrong,
the ECU should still have its original calibration.

WARNING: This still carries some risk! Only run if you have a backup
and are willing to accept the (small) risk of ECU issues.
"""

import can
import time
import os
import sys
from datetime import datetime

# CAN Configuration
CAN_INTERFACE = 'pcan'
CAN_CHANNEL = 'PCAN_USBBUS1'
CAN_BITRATE = 500000

# UDS IDs
ECU_TX = 0x7E0
ECU_RX = 0x7E8
BROADCAST = 0x7DF

# UDS Services
DIAGNOSTIC_SESSION_CONTROL = 0x10
SECURITY_ACCESS = 0x27
REQUEST_DOWNLOAD = 0x34
REQUEST_UPLOAD = 0x35
TRANSFER_DATA = 0x36
REQUEST_TRANSFER_EXIT = 0x37
TESTER_PRESENT = 0x3E

# Memory regions
AUTH_ADDRESS = 0x00000000
AUTH_LENGTH = 2006

# READ address (where we read calibration FROM)
READ_ADDRESS = 0x7D8000
READ_LENGTH = 0x28000  # 160KB

# WRITE address (where PowerVision writes TO - discovered from capture)
# NOTE: This is DIFFERENT from read address!
WRITE_ADDRESS = 0x00004000
WRITE_LENGTH = 0x4000   # 16KB (from capture analysis)

# Load authentication payload from existing capture
AUTH_PAYLOAD_FILE = "../PowerVision/raw_capture_20251226_200156.txt"


class SafeWriteTest:
    def __init__(self):
        self.bus = None
        self.auth_payload = None
        
    def connect(self):
        """Initialize CAN bus"""
        print("[*] Connecting to PCAN...")
        try:
            self.bus = can.interface.Bus(
                interface=CAN_INTERFACE,
                channel=CAN_CHANNEL,
                bitrate=CAN_BITRATE
            )
            print("[+] Connected!")
            return True
        except Exception as e:
            print(f"[-] Connection failed: {e}")
            return False
    
    def disconnect(self):
        if self.bus:
            self.bus.shutdown()
            
    def send_recv(self, data, timeout=2.0):
        """Send UDS request and wait for response"""
        # Build ISO-TP frame(s)
        if len(data) <= 7:
            # Single frame
            frame = bytes([len(data)]) + data + bytes(7 - len(data))
            msg = can.Message(arbitration_id=ECU_TX, data=frame, is_extended_id=False)
            self.bus.send(msg)
        else:
            # Multi-frame - First Frame
            length = len(data)
            ff = bytes([0x10 | ((length >> 8) & 0x0F), length & 0xFF]) + data[:6]
            msg = can.Message(arbitration_id=ECU_TX, data=ff, is_extended_id=False)
            self.bus.send(msg)
            
            # Wait for Flow Control
            fc_msg = self.bus.recv(timeout=1.0)
            if not fc_msg or fc_msg.arbitration_id != ECU_RX:
                return None
            if (fc_msg.data[0] & 0xF0) != 0x30:
                return None
                
            # Send Consecutive Frames
            remaining = data[6:]
            seq = 1
            while remaining:
                chunk = remaining[:7]
                remaining = remaining[7:]
                cf = bytes([0x20 | (seq & 0x0F)]) + chunk
                if len(cf) < 8:
                    cf += bytes(8 - len(cf))
                msg = can.Message(arbitration_id=ECU_TX, data=cf, is_extended_id=False)
                self.bus.send(msg)
                seq = (seq + 1) & 0x0F
                time.sleep(0.001)
        
        # Wait for response
        start = time.time()
        response_data = bytearray()
        expected_length = 0
        
        while time.time() - start < timeout:
            msg = self.bus.recv(timeout=0.1)
            if not msg or msg.arbitration_id != ECU_RX:
                continue
                
            frame_type = msg.data[0] >> 4
            
            if frame_type == 0:  # Single Frame
                length = msg.data[0] & 0x0F
                return bytes(msg.data[1:1+length])
                
            elif frame_type == 1:  # First Frame
                expected_length = ((msg.data[0] & 0x0F) << 8) | msg.data[1]
                response_data.extend(msg.data[2:8])
                # Send Flow Control
                fc = can.Message(arbitration_id=ECU_TX, data=bytes([0x30, 0x00, 0x00, 0, 0, 0, 0, 0]), is_extended_id=False)
                self.bus.send(fc)
                
            elif frame_type == 2:  # Consecutive Frame
                response_data.extend(msg.data[1:8])
                if len(response_data) >= expected_length:
                    return bytes(response_data[:expected_length])
        
        return bytes(response_data) if response_data else None
    
    def drain_bus(self, timeout=0.1):
        """Clear any pending messages"""
        while True:
            msg = self.bus.recv(timeout=timeout)
            if not msg:
                break
    
    def load_auth_payload(self):
        """Load authentication payload from capture file"""
        print("[*] Loading authentication payload...")
        
        if not os.path.exists(AUTH_PAYLOAD_FILE):
            print(f"[-] Auth payload file not found: {AUTH_PAYLOAD_FILE}")
            return False
            
        # Extract payload from capture file
        try:
            import re
            with open(AUTH_PAYLOAD_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Find TransferData messages from 0x7E0
            pattern = r'0x7E0\s+8\s+([0-9A-Fa-f]{16})'
            matches = re.findall(pattern, content)
            
            payload = bytearray()
            collecting = False
            cf_count = 0
            
            for match in matches:
                frame = bytes.fromhex(match)
                pci = frame[0]
                
                # First Frame with TransferData (0x36)
                if (pci & 0xF0) == 0x10:
                    total_len = ((pci & 0x0F) << 8) | frame[1]
                    if frame[2] == 0x36:
                        # Start collecting - skip service byte and block counter
                        payload = bytearray(frame[4:8])  
                        collecting = True
                        cf_count = 0
                        continue
                
                # Consecutive Frames
                if collecting and (pci & 0xF0) == 0x20:
                    payload.extend(frame[1:8])
                    cf_count += 1
                    if len(payload) >= 2006:
                        break
            
            if len(payload) >= 2000:
                self.auth_payload = bytes(payload)
                print(f"[+] Loaded {len(self.auth_payload)} byte auth payload")
                return True
            else:
                print(f"[-] Could not extract payload (got {len(payload)} bytes)")
                return False
                
        except Exception as e:
            print(f"[-] Failed to load auth payload: {e}")
            return False
    
    def authenticate(self):
        """Perform full authentication sequence"""
        print("[*] Starting authentication...")
        
        # TesterPresent
        self.send_recv(bytes([TESTER_PRESENT, 0x00]))
        time.sleep(0.05)
        
        # Extended Session (broadcast)
        msg = can.Message(arbitration_id=BROADCAST, data=bytes([0x02, 0x10, 0x03, 0, 0, 0, 0, 0]), is_extended_id=False)
        self.bus.send(msg)
        time.sleep(0.1)
        self.drain_bus()
        
        # Security Access Level 1
        resp = self.send_recv(bytes([SECURITY_ACCESS, 0x01]))
        if not resp or resp[0] != 0x67:
            print(f"[-] Seed request failed: {resp.hex() if resp else 'No response'}")
            return False
            
        seed = resp[2:4]
        key = bytes([seed[0] ^ 0x9A, seed[1] ^ 0xE8])
        
        resp = self.send_recv(bytes([SECURITY_ACCESS, 0x02]) + key)
        if not resp or resp[0] != 0x67:
            print(f"[-] Key rejected: {resp.hex() if resp else 'No response'}")
            return False
        print("[+] Security unlocked")
        
        # RequestDownload for auth payload
        req = bytes([REQUEST_DOWNLOAD, 0x00, 0x44])
        req += AUTH_ADDRESS.to_bytes(4, 'big')
        req += AUTH_LENGTH.to_bytes(4, 'big')
        
        resp = self.send_recv(req)
        if not resp or resp[0] != 0x74:
            print(f"[-] RequestDownload failed: {resp.hex() if resp else 'No response'}")
            return False
        
        # Send auth payload via TransferData
        block = 1
        sent = 0
        block_size = 256
        
        while sent < len(self.auth_payload):
            chunk = self.auth_payload[sent:sent+block_size]
            data = bytes([TRANSFER_DATA, block]) + chunk
            resp = self.send_recv(data)
            if not resp or resp[0] != 0x76:
                print(f"[-] TransferData failed at block {block}")
                return False
            sent += len(chunk)
            block = (block + 1) & 0xFF
        
        print("[+] Authentication complete!")
        return True
    
    def read_memory(self, address, length, format_byte=0xB0):
        """Read memory from ECU"""
        print(f"[*] Reading memory from 0x{address:X} ({length} bytes)...")
        
        data = bytearray()
        current_addr = address
        read_count = 0
        
        while len(data) < length:
            # Re-authenticate every 32 reads
            if read_count > 0 and read_count % 32 == 0:
                print("\n    [Re-authenticating...]")
                if not self.authenticate():
                    return None
            
            # RequestUpload
            req = bytes([REQUEST_UPLOAD, format_byte, 0x01])
            req += current_addr.to_bytes(4, 'big')
            
            resp = self.send_recv(req, timeout=5.0)
            if not resp or resp[0] != 0x75:
                print(f"\n[-] RequestUpload failed at 0x{current_addr:X}")
                return None
            
            data.extend(resp[1:])
            current_addr += len(resp) - 1
            read_count += 1
            
            progress = len(data) * 100 // length
            print(f"\r    Progress: {progress}% ({len(data)}/{length})", end='', flush=True)
        
        print()
        return bytes(data[:length])
    
    def write_memory(self, address, data):
        """Write data to ECU memory"""
        print(f"[*] Writing {len(data)} bytes to 0x{address:X}...")
        
        # RequestDownload 
        req = bytes([REQUEST_DOWNLOAD, 0x00, 0x44])
        req += address.to_bytes(4, 'big')
        req += len(data).to_bytes(4, 'big')
        
        resp = self.send_recv(req)
        if not resp or resp[0] != 0x74:
            print(f"[-] RequestDownload failed: {resp.hex() if resp else 'No response'}")
            return False
        
        # Send data via TransferData
        block = 1
        sent = 0
        block_size = 256
        
        while sent < len(data):
            chunk = data[sent:sent+block_size]
            td = bytes([TRANSFER_DATA, block]) + chunk
            resp = self.send_recv(td)
            if not resp or resp[0] != 0x76:
                print(f"\n[-] TransferData failed at block {block}")
                return False
            sent += len(chunk)
            block = (block + 1) & 0xFF
            
            progress = sent * 100 // len(data)
            print(f"\r    Progress: {progress}% ({sent}/{len(data)})", end='', flush=True)
        
        print()
        print("[+] Write complete!")
        return True
    
    def run_test(self, mode='analyze'):
        """Run the safe write test"""
        print("=" * 70)
        print("WRITE PROTOCOL ANALYSIS & TEST")
        print("=" * 70)
        print()
        print("IMPORTANT: Read/Write addresses are DIFFERENT!")
        print(f"  READ from:  0x{READ_ADDRESS:08X} (calibration storage)")
        print(f"  WRITE to:   0x{WRITE_ADDRESS:08X} (staging area?)")
        print()
        print("Modes:")
        print("  1. analyze  - Read-only, compare addresses")
        print("  2. test     - Try reading from write address")
        print("  3. verify   - Full write-verify cycle (RISK!)")
        print()
        
        if mode == 'analyze':
            self.analyze_mode()
        elif mode == 'test':
            self.test_mode()
        elif mode == 'verify':
            self.verify_mode()
    
    def analyze_mode(self):
        """Read-only analysis of memory regions"""
        print("=" * 50)
        print("ANALYZE MODE (Read-Only)")
        print("=" * 50)
        
        if not self.connect():
            return
        
        try:
            if not self.load_auth_payload():
                return
                
            if not self.authenticate():
                return
            
            # Read from main calibration address
            print()
            print(f"Reading from calibration (0x{READ_ADDRESS:X})...")
            calib_sample = self.read_memory(READ_ADDRESS, 256, 0xB0)
            if calib_sample:
                print(f"  First 16 bytes: {calib_sample[:16].hex()}")
            
            # Try reading from write address
            print()
            print(f"Attempting to read from write address (0x{WRITE_ADDRESS:X})...")
            if not self.authenticate():
                return
            write_sample = self.read_memory(WRITE_ADDRESS, 256, 0xA0)
            if write_sample:
                print(f"  First 16 bytes: {write_sample[:16].hex()}")
                
                # Compare
                if write_sample == calib_sample:
                    print("\n  [!] Same data at both addresses!")
                else:
                    print("\n  [!] Different data at write vs read address")
            else:
                print("  [-] Could not read from write address")
                
        finally:
            self.disconnect()
    
    def test_mode(self):
        """Test reading from various addresses"""
        print("=" * 50)
        print("TEST MODE - Probing Addresses")
        print("=" * 50)
        
        if not self.connect():
            return
        
        try:
            if not self.load_auth_payload():
                return
                
            if not self.authenticate():
                return
            
            # Try reading small samples from different addresses
            test_addrs = [
                (0x00004000, 0xA0, "Write staging area"),
                (0x00000000, 0xA0, "Auth area"),
                (0x7D8000, 0xB0, "Calibration start"),
                (0x7FFFF0, 0xB0, "Calibration end"),
            ]
            
            for addr, fmt, desc in test_addrs:
                print(f"\n{desc} (0x{addr:08X}):")
                if not self.authenticate():
                    break
                sample = self.read_memory(addr, 16, fmt)
                if sample:
                    print(f"  Data: {sample.hex()}")
                else:
                    print(f"  [-] Read failed")
                    
        finally:
            self.disconnect()
    
    def verify_mode(self):
        """Full write-verify cycle (RISKY!)"""
        print("=" * 50)
        print("VERIFY MODE - Write Test")
        print("=" * 50)
        print()
        print("╔══════════════════════════════════════════════════╗")
        print("║  WARNING: This will WRITE to your ECU!           ║")
        print("║                                                   ║")
        print("║  We will write to 0x4000 (16KB)                  ║")
        print("║  If this fails, your ECU may be damaged!         ║")
        print("╚══════════════════════════════════════════════════╝")
        print()
        
        confirm = input("Type 'YES I UNDERSTAND' to continue: ")
        if confirm != 'YES I UNDERSTAND':
            print("Aborted.")
            return
        
        if not self.connect():
            return
        
        try:
            if not self.load_auth_payload():
                return
                
            # Step 1: Read current data at write address
            print()
            print("STEP 1: Reading current data at write address...")
            if not self.authenticate():
                return
            original = self.read_memory(WRITE_ADDRESS, WRITE_LENGTH, 0xA0)
            if not original:
                print("[-] Cannot read write address - aborting")
                return
            
            # Save backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"write_area_backup_{timestamp}.bin"
            with open(backup_file, 'wb') as f:
                f.write(original)
            print(f"[+] Backup saved: {backup_file}")
            
            # Step 2: Write same data back
            print()
            print("STEP 2: Writing same data back...")
            if not self.authenticate():
                return
            if not self.write_memory(WRITE_ADDRESS, original):
                print("[-] Write failed!")
                return
            
            # Step 3: Read back and verify
            print()
            print("STEP 3: Verify read...")
            if not self.authenticate():
                return
            readback = self.read_memory(WRITE_ADDRESS, WRITE_LENGTH, 0xA0)
            if not readback:
                print("[-] Read-back failed!")
                return
            
            # Compare
            print()
            print("=" * 50)
            print("RESULT")
            print("=" * 50)
            if original == readback:
                print("[+] SUCCESS! Write-verify passed!")
            else:
                print("[-] MISMATCH!")
                diffs = sum(1 for a, b in zip(original, readback) if a != b)
                print(f"    {diffs} bytes differ")
                
        finally:
            self.disconnect()


def main():
    print()
    print("Safe Write Test Tool")
    print("=" * 40)
    print()
    print("Select mode:")
    print("  1. Analyze - Read-only comparison")
    print("  2. Test    - Probe multiple addresses")
    print("  3. Verify  - Write-verify cycle (RISK!)")
    print()
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    modes = {'1': 'analyze', '2': 'test', '3': 'verify'}
    mode = modes.get(choice, 'analyze')
    
    test = SafeWriteTest()
    test.run_test(mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())

