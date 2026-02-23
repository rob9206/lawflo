#!/usr/bin/env python3
"""
Capture PowerVision Write Operation

This captures CAN traffic while PowerVision writes a tune to the ECU.
The capture will reveal the write protocol:
- Write address format
- Checksum/validation
- Commit/finalize sequence

Usage:
    1. Connect PCAN (parallel with PowerVision)
    2. Run this script
    3. Use PowerVision to "Write to ECU"
    4. Analyze the output
"""

import can
import time
import sys
import os
from datetime import datetime
from collections import defaultdict

CAN_INTERFACE = 'pcan'
CAN_CHANNEL = 'PCAN_USBBUS1'
CAN_BITRATE = 500000

# Known patterns to identify
PATTERNS = {
    0x34: "RequestDownload (Write setup)",
    0x35: "RequestUpload (Read)",
    0x36: "TransferData",
    0x37: "RequestTransferExit",
    0x27: "SecurityAccess",
    0x10: "DiagnosticSessionControl",
    0x3E: "TesterPresent",
    0x31: "RoutineControl",
    0x22: "ReadDataByIdentifier",
}


def decode_frame(can_id, data):
    """Decode a CAN frame for display"""
    info = ""
    
    if can_id == 0x7E0:
        info = "TX->ECU "
        pci = data[0]
        
        if (pci & 0xF0) == 0x00:  # Single frame
            svc = data[1]
            info += PATTERNS.get(svc, f"Svc 0x{svc:02X}")
            if svc == 0x34:
                if len(data) >= 4:
                    info += f" addr_fmt=0x{data[3]:02X}"
            elif svc == 0x35:
                if len(data) >= 7:
                    addr = int.from_bytes(data[4:8], 'big')
                    info += f" @ 0x{addr:08X}"
        
        elif (pci & 0xF0) == 0x10:  # First frame
            length = ((pci & 0x0F) << 8) | data[1]
            svc = data[2]
            info += f"[FF len={length}] {PATTERNS.get(svc, f'Svc 0x{svc:02X}')}"
            if svc == 0x34:
                info += " *** WRITE SETUP ***"
            elif svc == 0x36:
                info += " *** DATA TRANSFER ***"
        
        elif (pci & 0xF0) == 0x20:  # Consecutive frame
            seq = pci & 0x0F
            info += f"[CF{seq}]"
        
        elif (pci & 0xF0) == 0x30:  # Flow control
            info += "[FC]"
    
    elif can_id == 0x7E8:
        info = "ECU-> "
        pci = data[0]
        
        if (pci & 0xF0) == 0x00:  # Single frame
            svc = data[1]
            if svc == 0x7F:
                nrc = data[3] if len(data) > 3 else 0
                info += f"NRC 0x{nrc:02X}"
            elif svc == 0x74:
                info += "RequestDownload+ *** WRITE ACCEPTED ***"
            elif svc == 0x75:
                info += "RequestUpload+"
            elif svc == 0x76:
                info += "TransferData+"
            elif svc == 0x77:
                info += "TransferExit+"
            else:
                info += f"Response 0x{svc:02X}"
        
        elif (pci & 0xF0) == 0x10:
            length = ((pci & 0x0F) << 8) | data[1]
            info += f"[FF len={length}]"
        
        elif (pci & 0xF0) == 0x20:
            seq = pci & 0x0F
            info += f"[CF{seq}]"
        
        elif (pci & 0xF0) == 0x30:
            info += "[FC]"
    
    elif can_id == 0x7DF:
        info = "Broadcast "
        if len(data) >= 2 and (data[0] & 0xF0) == 0x00:
            svc = data[1]
            info += PATTERNS.get(svc, f"Svc 0x{svc:02X}")
    
    return info


def main():
    print("=" * 70)
    print("Capture PowerVision WRITE Operation")
    print("=" * 70)
    print()
    print("This will capture the write protocol when PowerVision flashes a tune.")
    print()
    print("Instructions:")
    print("  1. Connect PCAN adapter to bike's diagnostic port")
    print("  2. Connect PowerVision device")
    print("  3. Turn bike ignition ON")
    print("  4. Have a tune file ready in PowerVision")
    print("  5. Start this capture")
    print("  6. Use PowerVision to 'Write to ECU' / 'Flash Tune'")
    print("  7. Wait for write to complete, then press Ctrl+C")
    print()
    print("WARNING: Writing wrong data could brick the ECU!")
    print("         Only write a known-good tune file.")
    print()
    
    input("Press ENTER to start capture...")
    
    try:
        bus = can.Bus(interface=CAN_INTERFACE, channel=CAN_CHANNEL, bitrate=CAN_BITRATE)
        print(f"\n[OK] PCAN connected at {CAN_BITRATE} baud")
    except Exception as e:
        print(f"\n[-] Failed to connect: {e}")
        return 1
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"write_capture_{timestamp}.txt"
    
    print(f"\n[*] Capturing to: {output_file}")
    print("[*] Press Ctrl+C when write operation completes\n")
    print("-" * 70)
    
    messages = []
    start_time = time.time()
    
    # Track statistics
    stats = defaultdict(int)
    write_setups = 0
    data_transfers = 0
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# PowerVision WRITE Capture\n")
            f.write(f"# Date: {datetime.now().isoformat()}\n")
            f.write(f"# Looking for write protocol patterns\n\n")
            
            while True:
                msg = bus.recv(timeout=0.1)
                if not msg:
                    continue
                
                elapsed = int((time.time() - start_time) * 1000)
                data = bytes(msg.data[:msg.dlc])
                data_hex = data.hex()
                
                # Decode
                info = decode_frame(msg.arbitration_id, data)
                
                # Track important events
                if msg.arbitration_id == 0x7E0:
                    stats['tx'] += 1
                    if len(data) >= 3:
                        pci = data[0]
                        if (pci & 0xF0) == 0x10:  # First frame
                            svc = data[2]
                            if svc == 0x34:
                                write_setups += 1
                                print(f"\n{'='*70}")
                                print(f"*** WRITE SETUP #{write_setups} DETECTED ***")
                                print(f"{'='*70}")
                            elif svc == 0x36:
                                data_transfers += 1
                
                elif msg.arbitration_id == 0x7E8:
                    stats['rx'] += 1
                    if len(data) >= 2 and (data[0] & 0xF0) == 0x00:
                        if data[1] == 0x74:
                            print(f"\n*** ECU ACCEPTED WRITE REQUEST ***")
                        elif data[1] == 0x77:
                            print(f"\n*** TRANSFER EXIT - WRITE COMPLETE? ***")
                
                # Only log diagnostic traffic
                if msg.arbitration_id in [0x7E0, 0x7E8, 0x7DF]:
                    line = f"{elapsed:10d}  0x{msg.arbitration_id:03X}  {msg.dlc}  {data_hex:<16}  {info}"
                    f.write(line + "\n")
                    
                    # Print important frames
                    if "***" in info or "NRC" in info:
                        print(line)
                    elif elapsed % 5000 < 100:  # Progress every 5 seconds
                        print(f"\r[{elapsed/1000:.1f}s] TX:{stats['tx']} RX:{stats['rx']} Writes:{write_setups} Transfers:{data_transfers}", end='', flush=True)
    
    except KeyboardInterrupt:
        print(f"\n\n[!] Capture stopped")
    
    finally:
        bus.shutdown()
    
    # Summary
    print(f"\n{'='*70}")
    print("Capture Summary")
    print(f"{'='*70}")
    print(f"Duration: {(time.time() - start_time):.1f} seconds")
    print(f"TX messages: {stats['tx']}")
    print(f"RX messages: {stats['rx']}")
    print(f"Write setups (0x34): {write_setups}")
    print(f"Data transfers (0x36 FF): {data_transfers}")
    print(f"\nSaved to: {output_file}")
    
    if write_setups > 1:
        print(f"\n[OK] Captured {write_setups} write sequences!")
        print("     Analyze the capture to understand write protocol.")
    else:
        print(f"\n[!] Only {write_setups} write setup detected.")
        print("    Make sure PowerVision actually wrote to ECU.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

