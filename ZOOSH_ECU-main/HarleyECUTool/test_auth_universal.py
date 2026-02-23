#!/usr/bin/env python3
"""
Auth Payload Universality Test

Tests if an auth payload captured from one bike works on a different ECU.
This helps determine if the payload is:
- Universal (works on any Harley)
- Model-specific (works on same model year)
- ECU-specific (only works on original bike)
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.can_interface import CANInterface
from core.auth import Authenticator
from core.protocol import UDS

def find_capture():
    """Find most recent capture file."""
    captures = [f for f in os.listdir('.') if 'capture' in f.lower() and f.endswith('.txt')]
    if not captures:
        # Check parent directory
        parent = os.path.join('..', 'HarleyECUDump')
        if os.path.exists(parent):
            captures = [os.path.join(parent, f) for f in os.listdir(parent) 
                       if 'capture' in f.lower() and f.endswith('.txt')]
    
    if captures:
        captures.sort(key=os.path.getmtime, reverse=True)
        return captures[0]
    return None


def test_auth_on_ecu():
    """Test if auth payload works on connected ECU."""
    
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           AUTH PAYLOAD UNIVERSALITY TEST                         ║
╠══════════════════════════════════════════════════════════════════╣
║  This tests if your capture file works on the connected ECU      ║
║                                                                  ║
║  Requirements:                                                   ║
║  - PCAN connected to a Harley ECU                                ║
║  - Ignition ON                                                   ║
║  - Capture file from previous PowerVision session                ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Find capture file
    capture_file = find_capture()
    
    if not capture_file:
        print("[!] No capture file found!")
        print("    Place a capture_*.txt file in this directory")
        return False
    
    print(f"[*] Using capture: {capture_file}")
    
    # Ask user about the ECU
    print("\n" + "=" * 60)
    print("ECU INFORMATION (for documentation)")
    print("=" * 60)
    
    original_info = input("Original bike (capture source) model/year: ").strip() or "Unknown"
    current_info = input("Current bike (connected now) model/year: ").strip() or "Unknown"
    same_bike = input("Is this the SAME bike as capture? (y/n): ").strip().lower()
    
    print(f"\n[*] Testing: {current_info}")
    print(f"[*] Capture from: {original_info}")
    print(f"[*] Same bike: {'Yes' if same_bike == 'y' else 'No'}")
    
    # Connect
    print("\n[1/5] Connecting to PCAN...")
    can = CANInterface()
    
    if not can.connect():
        print("[!] Failed to connect to PCAN")
        return False
    
    print("[OK] Connected")
    
    try:
        # Test CAN quality
        print("\n[2/5] Testing CAN bus...")
        passed, rate = can.test_quality(tests=10, threshold=0.8)
        print(f"[{'OK' if passed else '!!'}] CAN quality: {rate*100:.0f}%")
        
        if not passed:
            print("[!] CAN quality too low - check wiring")
            return False
        
        # Create authenticator
        auth = Authenticator(can)
        
        # Load auth payload
        print("\n[3/5] Loading auth payload...")
        if not auth.load_auth_payload(capture_file):
            print("[!] Failed to load auth payload from capture")
            return False
        
        print(f"[OK] Auth payload loaded ({len(auth.auth_payload)} bytes)")
        
        # Start session
        print("\n[4/5] Starting diagnostic session...")
        auth.start_session(UDS.DSC_EXTENDED)
        print("[OK] Session started")
        
        # Security access
        print("\n[5/5] Testing authentication sequence...")
        
        # Level 1 security
        print("  [a] Level 1 security access...")
        can.send_frame(can.TX_ID, bytes([0x27, 0x01]))
        resp = can.recv_response()
        
        if not resp or resp[0] != 0x67:
            print(f"  [!] Seed request failed: {resp.hex() if resp else 'No response'}")
            return False
        
        seed = resp[2:4]
        key = auth.compute_key(seed)
        print(f"  [OK] Seed: {seed.hex()}, Key: {key.hex()}")
        
        can.send_frame(can.TX_ID, bytes([0x27, 0x02]) + key)
        resp = can.recv_response()
        
        if not resp or resp[0] != 0x67:
            print(f"  [!] Key rejected: {resp.hex() if resp else 'No response'}")
            return False
        
        print("  [OK] Level 1 unlocked!")
        
        # Send auth payload
        print("\n  [b] Sending auth payload (this is the real test)...")
        
        # RequestDownload
        req = bytes([0x34, 0x00, 0x44, 0, 0, 0, 0, 0, 0, 0x07, 0xD6])
        can.send_multiframe(can.TX_ID, req)
        resp = can.recv_response()
        
        if not resp or resp[0] != 0x74:
            nrc = resp[2] if resp and len(resp) > 2 else 0
            print(f"  [!] RequestDownload failed: NRC 0x{nrc:02X}")
            return False
        
        print("  [OK] RequestDownload accepted")
        
        # TransferData with auth
        msg = bytes([0x36, 0x01]) + auth.auth_payload
        can.send_multiframe(can.TX_ID, msg)
        resp = can.recv_response(timeout=3.0)
        
        if not resp or resp[0] != 0x76:
            nrc = resp[2] if resp and len(resp) > 2 else 0
            print(f"  [!] Auth payload REJECTED: NRC 0x{nrc:02X}")
            print("\n" + "=" * 60)
            print("RESULT: ❌ AUTH PAYLOAD NOT UNIVERSAL")
            print("=" * 60)
            print("The auth payload is tied to specific ECU/VIN/license")
            return False
        
        print("  [OK] Auth payload ACCEPTED!")
        
        # Try a quick memory read to confirm
        print("\n  [c] Confirming memory access...")
        can.send_frame(can.TX_ID, bytes([0x35, 0xB0, 0x01, 0x00, 0x7D, 0x80, 0x00]))
        resp = can.recv_response(timeout=2.0)
        
        if resp and resp[0] == 0x75:
            print("  [OK] Memory read works!")
            memory_works = True
        else:
            print("  [?] Memory read unclear")
            memory_works = False
        
        # SUCCESS!
        print("\n" + "=" * 60)
        print("RESULT: ✅ AUTH PAYLOAD WORKS ON THIS ECU!")  
        print("=" * 60)
        
        if same_bike != 'y':
            print("\n🎉 GREAT NEWS! The auth payload appears to be UNIVERSAL!")
            print("   (or at least works across these two bikes)")
            print(f"\n   Tested: {original_info} → {current_info}")
        else:
            print("\n✓ Auth works on original bike (expected)")
            print("  To confirm universality, test on a DIFFERENT bike")
        
        return True
        
    except KeyboardInterrupt:
        print("\n[!] Interrupted")
        return False
        
    except Exception as e:
        print(f"\n[!] Error: {e}")
        return False
        
    finally:
        can.disconnect()
        print("\n[*] Disconnected")


def main():
    result = test_auth_on_ecu()
    
    print("\n" + "=" * 60)
    if result:
        print("TEST PASSED - Auth payload accepted by ECU")
    else:
        print("TEST FAILED - Auth payload not accepted")
    print("=" * 60)
    
    input("\nPress Enter to exit...")
    return 0 if result else 1


if __name__ == '__main__':
    sys.exit(main())

