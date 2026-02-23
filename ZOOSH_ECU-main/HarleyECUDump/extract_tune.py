#!/usr/bin/env python3
"""
Extract Tune from Calibration Dump

Extracts the 16KB writable tune region from a full 160KB calibration dump.
This extracted file can then be written back using ecu_flash.py.

Memory mapping (discovered via capture analysis):
  - Write address: 0x00004000
  - Read address:  0x7F4000
  - Offset in dump: 0x1C000 (114688 bytes from start)
  - Size: 16KB (16384 bytes)
"""

import os
import sys
from datetime import datetime

# Memory mapping constants
DUMP_START = 0x7D8000
TUNE_OFFSET = 0x1C000  # Offset within the 160KB dump
TUNE_SIZE = 0x4000     # 16KB
TUNE_READ_ADDR = 0x7F4000  # Actual ECU address
TUNE_WRITE_ADDR = 0x00004000  # Where to write


def extract_tune(dump_file: str, output_file: str = None) -> bytes:
    """
    Extract the 16KB tune data from a calibration dump.
    
    Args:
        dump_file: Path to calibration_*.bin file
        output_file: Optional output path (auto-generated if not provided)
    
    Returns:
        The extracted tune data (16KB)
    """
    if not os.path.exists(dump_file):
        print(f"[-] File not found: {dump_file}")
        return None
    
    with open(dump_file, 'rb') as f:
        dump_data = f.read()
    
    print(f"[*] Loaded dump: {len(dump_data)} bytes")
    
    if len(dump_data) < TUNE_OFFSET + TUNE_SIZE:
        print(f"[-] Dump too small! Expected at least {TUNE_OFFSET + TUNE_SIZE} bytes")
        return None
    
    # Extract tune region
    tune_data = dump_data[TUNE_OFFSET:TUNE_OFFSET + TUNE_SIZE]
    print(f"[+] Extracted {len(tune_data)} bytes from offset 0x{TUNE_OFFSET:X}")
    
    # Generate output filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.basename(dump_file).replace("calibration_", "tune_").replace(".bin", "")
        output_file = f"{base_name}_{timestamp}.bin"
    
    # Save
    with open(output_file, 'wb') as f:
        f.write(tune_data)
    print(f"[+] Saved tune: {output_file}")
    
    # Show info
    print()
    print("Tune Data Info:")
    print(f"  First 16 bytes: {tune_data[:16].hex()}")
    print(f"  Last 16 bytes:  {tune_data[-16:].hex()}")
    
    return tune_data


def compare_tunes(tune1_file: str, tune2_file: str):
    """
    Compare two tune files byte-by-byte.
    """
    with open(tune1_file, 'rb') as f:
        tune1 = f.read()
    with open(tune2_file, 'rb') as f:
        tune2 = f.read()
    
    print(f"\n[*] Comparing tunes:")
    print(f"    File 1: {tune1_file} ({len(tune1)} bytes)")
    print(f"    File 2: {tune2_file} ({len(tune2)} bytes)")
    
    if len(tune1) != len(tune2):
        print(f"[-] Different sizes!")
        return
    
    diffs = []
    for i in range(len(tune1)):
        if tune1[i] != tune2[i]:
            diffs.append((i, tune1[i], tune2[i]))
    
    if not diffs:
        print("[+] Files are IDENTICAL!")
    else:
        print(f"[-] {len(diffs)} bytes differ ({len(diffs)*100/len(tune1):.1f}%)")
        print("\n    First 20 differences:")
        for i, (offset, b1, b2) in enumerate(diffs[:20]):
            print(f"      0x{offset:04X}: 0x{b1:02X} -> 0x{b2:02X}")
        
        if len(diffs) > 20:
            print(f"      ... and {len(diffs) - 20} more")


def main():
    print("=" * 60)
    print("Tune Extractor")
    print("=" * 60)
    print()
    print(f"Extracts the 16KB writable tune region from a calibration dump.")
    print(f"Offset: 0x{TUNE_OFFSET:X}, Size: {TUNE_SIZE} bytes")
    print()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Extract: python extract_tune.py <calibration_dump.bin>")
        print("  Compare: python extract_tune.py <tune1.bin> <tune2.bin>")
        print()
        
        # Try to find dumps automatically
        print("Looking for calibration dumps...")
        dumps = []
        for root, dirs, files in os.walk("."):
            for f in files:
                if f.startswith("calibration_") and f.endswith(".bin"):
                    path = os.path.join(root, f)
                    size = os.path.getsize(path)
                    if size >= TUNE_OFFSET + TUNE_SIZE:
                        dumps.append((path, size))
        
        if dumps:
            print(f"Found {len(dumps)} valid dump(s):")
            for path, size in dumps:
                print(f"  {path} ({size} bytes)")
            print()
            print("Run: python extract_tune.py <dump_file>")
        else:
            print("No calibration dumps found!")
            print("Run: python harley_ecu_dump.py dump")
        
        return 1
    
    if len(sys.argv) == 2:
        # Extract mode - auto output name
        extract_tune(sys.argv[1])
    elif len(sys.argv) == 3:
        # Check if second arg is output file or compare mode
        if sys.argv[2].endswith('.bin') and not os.path.exists(sys.argv[2]):
            # Extract mode with output filename
            extract_tune(sys.argv[1], sys.argv[2])
        elif os.path.exists(sys.argv[1]) and os.path.exists(sys.argv[2]):
            # Compare mode
            compare_tunes(sys.argv[1], sys.argv[2])
        else:
            # Assume extract mode with output filename
            extract_tune(sys.argv[1], sys.argv[2])
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

