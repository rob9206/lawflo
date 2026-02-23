#!/usr/bin/env python3
"""
Harley-Davidson ECU Memory Dump Tool

Reads calibration/tune data from Harley-Davidson ECUs (Delphi)
by replaying authentication captured from PowerVision/Power Core.

Usage:
    1. First capture: python harley_ecu_dump.py capture
    2. Then dump:     python harley_ecu_dump.py dump

Requirements:
    - PCAN-USB adapter connected to bike's diagnostic port
    - PowerVision device (for initial auth capture only)
    - Bike ignition ON

Author: Reverse-engineered from PowerVision protocol analysis
"""

import can
import time
import sys
import re
import os
import argparse
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Tuple, List

# ============================================================
# Configuration
# ============================================================

CAN_INTERFACE = 'pcan'
CAN_CHANNEL = 'PCAN_USBBUS1'
CAN_BITRATE = 500000

TX_PHYSICAL = 0x7E0      # Physical addressing to main ECU
TX_FUNCTIONAL = 0x7DF    # Functional broadcast to all ECUs
RX_ECU = 0x7E8           # Main ECU response ID

SEED_XOR_KEY = 0x9AE8    # Security access XOR key

# Memory regions to dump
MEMORY_REGIONS = [
    # (name, start_addr, end_addr, format_byte, block_size)
    ("config_low",   0x000800, 0x001000, 0xA0, 0x100),
    ("config_mid",   0x740000, 0x740400, 0xB0, 0x100),
    ("calibration",  0x7D8000, 0x800000, 0xB0, 0x100),
]

# Re-authenticate every N reads to prevent session timeout
REAUTH_INTERVAL = 32


# ============================================================
# Data Classes
# ============================================================

@dataclass
class ECUInfo:
    """ECU identification data"""
    part_number: str = ""
    serial_number: str = ""
    calibration_id: int = 0
    checksum: int = 0
    raw_dids: dict = None
    
    def __post_init__(self):
        if self.raw_dids is None:
            self.raw_dids = {}


# ============================================================
# ECU Communication Class
# ============================================================

class HarleyECU:
    """Harley-Davidson ECU communication handler"""
    
    def __init__(self):
        self.bus: Optional[can.Bus] = None
        self.auth_payload: Optional[bytes] = None
        self.ecu_info = ECUInfo()
        self.verbose = False
    
    def log(self, msg: str, level: str = "info"):
        """Print log message"""
        if level == "debug" and not self.verbose:
            return
        prefix = {"info": "[*]", "ok": "[+]", "fail": "[-]", "debug": "[D]"}
        print(f"{prefix.get(level, '[*]')} {msg}")
    
    def connect(self) -> bool:
        """Connect to PCAN adapter"""
        try:
            self.bus = can.Bus(
                interface=CAN_INTERFACE,
                channel=CAN_CHANNEL,
                bitrate=CAN_BITRATE
            )
            self.log("Connected to PCAN adapter", "ok")
            return True
        except Exception as e:
            self.log(f"Failed to connect: {e}", "fail")
            return False
    
    def disconnect(self):
        """Disconnect from PCAN"""
        if self.bus:
            self.bus.shutdown()
            self.bus = None
    
    # ----------------------------------------------------------
    # ISO-TP Communication
    # ----------------------------------------------------------
    
    def send_frame(self, tx_id: int, data: bytes):
        """Send a single CAN frame"""
        msg = can.Message(
            arbitration_id=tx_id,
            data=data.ljust(8, b'\x00'),
            is_extended_id=False
        )
        self.bus.send(msg)
    
    def send_single_frame(self, tx_id: int, payload: bytes):
        """Send ISO-TP single frame"""
        if len(payload) > 7:
            raise ValueError("Payload too long for single frame")
        frame = bytes([len(payload)]) + payload
        self.send_frame(tx_id, frame)
    
    def send_multiframe(self, tx_id: int, payload: bytes, timeout: float = 2.0) -> bool:
        """Send ISO-TP multi-frame message"""
        total_len = len(payload)
        
        # First Frame
        ff = bytes([(0x10 | (total_len >> 8)), total_len & 0xFF]) + payload[:6]
        self.send_frame(tx_id, ff)
        
        # Wait for Flow Control
        start = time.time()
        fc_stmin = 1
        while time.time() - start < timeout:
            msg = self.bus.recv(timeout=0.1)
            if msg and msg.arbitration_id == RX_ECU:
                if (msg.data[0] & 0xF0) == 0x30:
                    fc_stmin = msg.data[2] if msg.data[2] > 0 else 1
                    break
        else:
            return False
        
        # Send Consecutive Frames
        remaining = payload[6:]
        seq = 1
        while remaining:
            cf_data = remaining[:7]
            remaining = remaining[7:]
            cf = bytes([0x20 | (seq & 0x0F)]) + cf_data
            self.send_frame(tx_id, cf.ljust(8, b'\x00'))
            seq += 1
            time.sleep(fc_stmin / 1000.0)
        
        return True
    
    def recv_response(self, timeout: float = 2.0) -> Optional[bytes]:
        """Receive single-frame response"""
        start = time.time()
        while time.time() - start < timeout:
            msg = self.bus.recv(timeout=0.1)
            if msg and msg.arbitration_id == RX_ECU:
                pci = msg.data[0] & 0xF0
                if pci == 0x00:  # Single frame
                    length = msg.data[0] & 0x0F
                    return bytes(msg.data[1:1+length])
        return None
    
    def recv_multiframe(self, timeout: float = 5.0) -> Optional[bytes]:
        """Receive multi-frame response with Flow Control"""
        start = time.time()
        
        while time.time() - start < timeout:
            msg = self.bus.recv(timeout=0.2)
            if not msg or msg.arbitration_id != RX_ECU:
                continue
            
            pci = msg.data[0] & 0xF0
            
            if pci == 0x00:  # Single frame
                length = msg.data[0] & 0x0F
                return bytes(msg.data[1:1+length])
            
            elif pci == 0x10:  # First frame
                total_len = ((msg.data[0] & 0x0F) << 8) | msg.data[1]
                data = bytearray(msg.data[2:8])
                
                # Send Flow Control
                fc = bytes([0x30, 0x00, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00])
                self.send_frame(TX_PHYSICAL, fc)
                
                # Receive consecutive frames
                cf_timeout = time.time() + 5.0
                while len(data) < total_len and time.time() < cf_timeout:
                    cf_msg = self.bus.recv(timeout=0.5)
                    if cf_msg and cf_msg.arbitration_id == RX_ECU:
                        if (cf_msg.data[0] & 0xF0) == 0x20:
                            data.extend(cf_msg.data[1:8])
                
                return bytes(data[:total_len])
        
        return None
    
    def drain_bus(self, timeout: float = 0.3):
        """Drain pending messages from bus"""
        end = time.time() + timeout
        while time.time() < end:
            self.bus.recv(timeout=0.05)
    
    # ----------------------------------------------------------
    # UDS Services
    # ----------------------------------------------------------
    
    def tester_present(self):
        """Send TesterPresent to keep session alive"""
        self.send_single_frame(TX_PHYSICAL, bytes([0x3E, 0x00, 0x01]))
        time.sleep(0.01)
    
    def read_did(self, did: int) -> Optional[bytes]:
        """Read Data By Identifier"""
        req = bytes([0x22, (did >> 8) & 0xFF, did & 0xFF])
        self.send_single_frame(TX_PHYSICAL, req)
        resp = self.recv_multiframe(timeout=1.0)
        if resp and resp[0] == 0x62:
            return resp[3:]  # Skip service + DID
        return None
    
    def authenticate(self, quiet: bool = False) -> bool:
        """Perform full authentication sequence"""
        def log(msg):
            if not quiet:
                print(f"    {msg}")
        
        if not quiet:
            print("\n[AUTH] Performing authentication sequence...")
        
        # TesterPresent
        log("TesterPresent...")
        self.tester_present()
        time.sleep(0.1)
        
        # Extended Session via broadcast
        log("Extended Session (broadcast)...")
        self.send_single_frame(TX_FUNCTIONAL, bytes([0x10, 0x03]))
        time.sleep(0.3)
        self.drain_bus()
        
        # Security Access Level 1
        log("Security Access...")
        self.send_single_frame(TX_PHYSICAL, bytes([0x27, 0x01]))
        resp = self.recv_response()
        
        if not resp or resp[0] != 0x67:
            log(f"[FAIL] Seed request failed: {resp.hex() if resp else 'No response'}")
            return False
        
        seed = resp[2:4]
        log(f"  Seed: {seed.hex()}")
        
        if seed != b'\x00\x00':
            key = (int.from_bytes(seed, 'big') ^ SEED_XOR_KEY).to_bytes(2, 'big')
            log(f"  Key:  {key.hex()}")
            
            self.send_single_frame(TX_PHYSICAL, bytes([0x27, 0x02]) + key)
            resp = self.recv_response()
            
            if not resp or resp[0] != 0x67:
                log(f"[FAIL] Key rejected")
                return False
        
        log("[OK] Security unlocked!")
        
        # RequestDownload
        log("RequestDownload...")
        rd_msg = bytes([0x34, 0x00, 0x44, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x07, 0xD6])
        if not self.send_multiframe(TX_PHYSICAL, rd_msg):
            log("[FAIL] No Flow Control")
            return False
        
        resp = self.recv_response()
        if not resp or resp[0] != 0x74:
            log(f"[FAIL] RequestDownload failed")
            return False
        log("[OK] RequestDownload accepted")
        
        # TransferData with auth payload
        if not self.auth_payload:
            log("[FAIL] No auth payload loaded!")
            return False
        
        log(f"TransferData ({len(self.auth_payload)} bytes)...")
        if not self.send_multiframe(TX_PHYSICAL, self.auth_payload):
            log("[FAIL] TransferData send failed")
            return False
        
        resp = self.recv_response(timeout=5.0)
        if not resp or resp[0] != 0x76:
            log(f"[FAIL] TransferData failed: {resp.hex() if resp else 'No response'}")
            return False
        
        log("[OK] Authentication complete!")
        return True
    
    def request_upload(self, address: int, fmt: int) -> Optional[bytes]:
        """Request memory upload from ECU"""
        req = bytes([0x35, fmt, 0x01]) + address.to_bytes(4, 'big')
        self.send_single_frame(TX_PHYSICAL, req)
        
        resp = self.recv_multiframe(timeout=3.0)
        if resp and len(resp) > 7 and resp[0] == 0x75:
            return resp[7:]  # Skip header
        elif resp and resp[0] == 0x7F:
            nrc = resp[2] if len(resp) > 2 else 0
            self.log(f"NRC 0x{nrc:02X} at 0x{address:06X}", "debug")
        return None
    
    # ----------------------------------------------------------
    # High-Level Operations
    # ----------------------------------------------------------
    
    def read_ecu_info(self) -> ECUInfo:
        """Read ECU identification DIDs"""
        print("\n[INFO] Reading ECU information...")
        
        dids = {
            0xF1EA: "Part Number",
            0xF1ED: "Serial Number",
            0xF1F5: "Calibration ID",
            0xF1F2: "Checksum",
            0xF1EF: "ECU Info",
        }
        
        for did, name in dids.items():
            data = self.read_did(did)
            if data:
                self.ecu_info.raw_dids[did] = data
                
                # Parse specific DIDs
                if did == 0xF1EA:
                    self.ecu_info.part_number = data.rstrip(b'\x00').decode('ascii', errors='replace')
                elif did == 0xF1ED:
                    self.ecu_info.serial_number = data.rstrip(b'\x00').decode('ascii', errors='replace')
                elif did == 0xF1F5 and len(data) >= 2:
                    self.ecu_info.calibration_id = int.from_bytes(data[:2], 'big')
                elif did == 0xF1F2 and len(data) >= 4:
                    self.ecu_info.checksum = int.from_bytes(data[:4], 'big')
                
                print(f"    {name}: {data.hex()}")
            time.sleep(0.01)
        
        return self.ecu_info
    
    def dump_region(self, name: str, start: int, end: int, fmt: int, 
                    block_size: int) -> bytes:
        """Dump a memory region"""
        all_data = bytearray()
        current = start
        total = end - start
        read_count = 0
        fail_count = 0
        
        print(f"\n  [{name}] 0x{start:06X}-0x{end:06X} ({total:,} bytes)")
        
        while current < end:
            data = self.request_upload(current, fmt)
            
            if data and len(data) > 0:
                chunk = data[:block_size] if len(data) >= block_size else \
                        data + b'\xFF' * (block_size - len(data))
                all_data.extend(chunk)
                fail_count = 0
                read_count += 1
            else:
                fail_count += 1
                if fail_count >= 3:
                    print(f"\n    Re-authenticating...")
                    if self.authenticate(quiet=True):
                        fail_count = 0
                        continue
                    else:
                        all_data.extend(b'\xFF' * block_size)
                else:
                    time.sleep(0.1)
                    continue
            
            current += block_size
            
            # Progress
            pct = (current - start) * 100 // total
            print(f"\r    Progress: {pct:3d}% ({len(all_data):,} bytes)", end='', flush=True)
            
            # Preventive re-auth
            if read_count % REAUTH_INTERVAL == 0 and read_count > 0:
                print(f"\n    Refreshing auth...", end='')
                self.authenticate(quiet=True)
        
        print(f"\n    Complete: {len(all_data):,} bytes")
        return bytes(all_data)
    
    def dump_all(self, output_dir: str) -> bool:
        """Dump all memory regions"""
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n[DUMP] Dumping memory to: {output_dir}")
        
        for name, start, end, fmt, bs in MEMORY_REGIONS:
            data = self.dump_region(name, start, end, fmt, bs)
            
            filename = os.path.join(output_dir, f"{name}_{start:06X}.bin")
            with open(filename, 'wb') as f:
                f.write(data)
            print(f"    Saved: {filename}")
        
        # Write info file
        info_file = os.path.join(output_dir, "dump_info.txt")
        with open(info_file, 'w') as f:
            f.write(f"Harley ECU Dump\n")
            f.write(f"===============\n\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"Part Number: {self.ecu_info.part_number}\n")
            f.write(f"Serial Number: {self.ecu_info.serial_number}\n")
            f.write(f"Calibration ID: 0x{self.ecu_info.calibration_id:04X}\n")
            f.write(f"Checksum: 0x{self.ecu_info.checksum:08X}\n")
            f.write(f"\nFiles:\n")
            for name, start, end, _, _ in MEMORY_REGIONS:
                f.write(f"  {name}_{start:06X}.bin: {end-start:,} bytes\n")
        
        print(f"\n[OK] Dump complete!")
        return True
    
    # ----------------------------------------------------------
    # Auth Payload Handling
    # ----------------------------------------------------------
    
    def load_auth_payload(self, capture_file: str) -> bool:
        """Extract auth payload from capture file"""
        print(f"\n[AUTH] Loading auth payload from: {capture_file}")
        
        if not os.path.exists(capture_file):
            self.log(f"File not found: {capture_file}", "fail")
            return False
        
        with open(capture_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        payload = bytearray()
        in_transfer = False
        expected_len = 0
        
        for line in lines:
            if "0x7E0" not in line or "TX" not in line:
                continue
            
            match = re.search(r'0x7E0\s+\d+\s+([0-9a-fA-F]{16})', line)
            if not match:
                continue
            
            frame = bytes.fromhex(match.group(1))
            pci = frame[0]
            
            # First Frame with TransferData (0x36)
            if (pci & 0xF0) == 0x10:
                total_len = ((pci & 0x0F) << 8) | frame[1]
                if frame[2] == 0x36:
                    in_transfer = True
                    expected_len = total_len
                    payload = bytearray(frame[2:8])
            
            # Consecutive Frames
            elif (pci & 0xF0) == 0x20 and in_transfer:
                payload.extend(frame[1:8])
                if len(payload) >= expected_len:
                    payload = payload[:expected_len]
                    break
        
        if len(payload) >= 2000:
            self.auth_payload = bytes(payload)
            print(f"    [OK] Loaded {len(payload)} bytes")
            return True
        else:
            self.log(f"Could not extract payload (got {len(payload)} bytes)", "fail")
            return False
    
    def save_auth_payload(self, filename: str):
        """Save auth payload to file"""
        if self.auth_payload:
            with open(filename, 'wb') as f:
                f.write(self.auth_payload)
            print(f"    Saved: {filename}")


# ============================================================
# Capture Mode
# ============================================================

def run_capture(output_file: str, duration: int, yes: bool = False):
    """Capture CAN traffic for auth payload extraction"""
    print("=" * 60)
    print("Harley ECU - Capture Mode")
    print("=" * 60)
    print(f"\nThis captures CAN traffic to extract the auth payload.")
    print(f"Output: {output_file}")
    print(f"Duration: {duration} seconds")
    print(f"\nInstructions:")
    print("  1. Connect PCAN adapter to bike's diagnostic port")
    print("  2. Connect PowerVision device")
    print("  3. Turn bike ignition ON")
    print("  4. Start this capture")
    print("  5. Use PowerVision to 'Read from ECU'")
    print("  6. Wait for capture to complete")
    
    if not yes:
        input("\nPress ENTER to start capture...")
    
    try:
        bus = can.Bus(interface=CAN_INTERFACE, channel=CAN_CHANNEL, bitrate=CAN_BITRATE)
        print(f"\n[OK] PCAN connected")
    except Exception as e:
        print(f"\n[-] Failed to connect: {e}")
        return False
    
    print(f"\n[*] Capturing for {duration} seconds...")
    print("    (Use PowerVision to read from ECU now)")
    
    messages = []
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            msg = bus.recv(timeout=0.1)
            if msg:
                elapsed = int((time.time() - start_time) * 1000)
                messages.append((elapsed, msg))
            
            # Progress every 10 seconds
            elapsed_sec = int(time.time() - start_time)
            if elapsed_sec > 0 and elapsed_sec % 10 == 0:
                print(f"\r    {elapsed_sec}s - {len(messages)} messages", end='', flush=True)
    
    except KeyboardInterrupt:
        print("\n\n[!] Capture interrupted")
    
    finally:
        bus.shutdown()
    
    print(f"\n\n[*] Captured {len(messages)} messages")
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Harley ECU CAN Capture\n")
        f.write(f"# Date: {datetime.now().isoformat()}\n")
        f.write(f"# Messages: {len(messages)}\n\n")
        
        for elapsed, msg in messages:
            data_hex = msg.data.hex()
            
            # Identify message type
            info = ""
            if msg.arbitration_id == 0x7E0:
                info = "TX->ECU"
                if len(msg.data) >= 2:
                    svc = msg.data[1] if (msg.data[0] & 0xF0) == 0x00 else msg.data[2]
                    if svc == 0x35:
                        info += " ReqUpload"
                    elif svc == 0x36:
                        info += " TransferData"
            elif msg.arbitration_id == 0x7E8:
                info = "ECU->"
            elif msg.arbitration_id == 0x7DF:
                info = "Broadcast"
            
            f.write(f"{elapsed:10d}  0x{msg.arbitration_id:03X}  {msg.dlc}  {data_hex:<16}  {info}\n")
    
    print(f"[OK] Saved to: {output_file}")
    return True


# ============================================================
# Dump Mode
# ============================================================

def run_dump(capture_file: str, output_dir: str, yes: bool = False):
    """Dump ECU memory using captured auth payload"""
    print("=" * 60)
    print("Harley ECU - Dump Mode")
    print("=" * 60)
    
    ecu = HarleyECU()
    
    # Load auth payload
    if not ecu.load_auth_payload(capture_file):
        print("\n[-] Cannot proceed without auth payload")
        print("    Run capture mode first: python harley_ecu_dump.py capture")
        return False
    
    # Connect
    if not ecu.connect():
        return False
    
    try:
        # Authenticate
        if not ecu.authenticate():
            print("\n[-] Authentication failed")
            return False
        
        # Read ECU info
        ecu.read_ecu_info()
        
        # Quick test
        print("\n[TEST] Testing memory read...")
        data = ecu.request_upload(0x000800, 0xA0)
        if data:
            print(f"    [OK] Got {len(data)} bytes")
            print(f"    First 16: {data[:16].hex()}")
        else:
            print("    [-] Read failed")
            return False
        
        # Confirm dump
        if output_dir is None:
            output_dir = f"ecu_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if not yes:
            response = input(f"\nProceed with full dump to '{output_dir}'? [y/N]: ").strip().lower()
            if response != 'y':
                print("Cancelled.")
                return False
        
        # Dump
        return ecu.dump_all(output_dir)
    
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted")
        return False
    
    finally:
        ecu.disconnect()


# ============================================================
# Main Entry Point
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Harley-Davidson ECU Memory Dump Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Capture auth payload:
    python harley_ecu_dump.py capture
    python harley_ecu_dump.py capture -o my_capture.txt -t 120

  Dump ECU memory:
    python harley_ecu_dump.py dump
    python harley_ecu_dump.py dump -c my_capture.txt -o my_dump/

  List available capture files:
    python harley_ecu_dump.py list
"""
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Capture command
    cap_parser = subparsers.add_parser('capture', help='Capture CAN traffic for auth payload')
    cap_parser.add_argument('-o', '--output', default=None,
                           help='Output capture file (default: capture_TIMESTAMP.txt)')
    cap_parser.add_argument('-t', '--time', type=int, default=120,
                           help='Capture duration in seconds (default: 120)')
    cap_parser.add_argument('-y', '--yes', action='store_true',
                           help='Skip start prompt')
    
    # Dump command
    dump_parser = subparsers.add_parser('dump', help='Dump ECU memory')
    dump_parser.add_argument('-c', '--capture', default=None,
                            help='Capture file with auth payload (default: latest capture_*.txt)')
    dump_parser.add_argument('-o', '--output', default=None,
                            help='Output directory (default: ecu_dump_TIMESTAMP/)')
    dump_parser.add_argument('-y', '--yes', action='store_true',
                            help='Skip confirmation prompt')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available capture files')
    
    args = parser.parse_args()
    
    if args.command == 'capture':
        output = args.output or f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        return 0 if run_capture(output, args.time, args.yes) else 1
    
    elif args.command == 'dump':
        # Find capture file
        capture_file = args.capture
        if not capture_file:
            # Look for most recent capture file
            captures = sorted([f for f in os.listdir('.') if f.startswith('capture_') and f.endswith('.txt')])
            if captures:
                capture_file = captures[-1]
                print(f"[*] Using capture file: {capture_file}")
            else:
                # Also check for raw_capture files
                captures = sorted([f for f in os.listdir('.') if f.startswith('raw_capture_') and f.endswith('.txt')])
                if captures:
                    capture_file = captures[-1]
                    print(f"[*] Using capture file: {capture_file}")
                else:
                    print("[-] No capture file found. Run capture mode first.")
                    return 1
        
        return 0 if run_dump(capture_file, args.output, args.yes) else 1
    
    elif args.command == 'list':
        print("\nAvailable capture files:")
        for f in sorted(os.listdir('.')):
            if (f.startswith('capture_') or f.startswith('raw_capture_')) and f.endswith('.txt'):
                size = os.path.getsize(f)
                print(f"  {f} ({size:,} bytes)")
        return 0
    
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())

