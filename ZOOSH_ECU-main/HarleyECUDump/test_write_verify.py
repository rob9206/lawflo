#!/usr/bin/env python3
"""
Test Write/Verify

This does a SAFE read-only test to verify our understanding
of the write protocol WITHOUT actually modifying ECU data.

It analyzes what addresses PowerVision writes to vs reads from.
"""

import os
import sys

def analyze_captures():
    """Analyze read vs write captures to understand memory mapping"""
    
    print("=" * 70)
    print("Analyzing Read vs Write Captures")
    print("=" * 70)
    print()
    
    # Find capture files
    read_capture = None
    write_capture = None
    
    for f in os.listdir('.'):
        if f.startswith('raw_capture_') and f.endswith('.txt'):
            read_capture = f
        elif f.startswith('write_capture_') and f.endswith('.txt'):
            write_capture = f
    
    if not read_capture:
        # Check parent directory
        parent = '../PowerVision'
        if os.path.exists(parent):
            for f in os.listdir(parent):
                if f.startswith('raw_capture_') and f.endswith('.txt'):
                    read_capture = os.path.join(parent, f)
                    break
    
    print(f"Read capture:  {read_capture or 'NOT FOUND'}")
    print(f"Write capture: {write_capture or 'NOT FOUND'}")
    print()
    
    if not write_capture:
        print("[-] No write capture found")
        print("    Need write_capture_*.txt to analyze write addresses")
        return
    
    # Analyze write capture
    print("Analyzing write capture...")
    print()
    
    with open(write_capture, 'r') as f:
        lines = f.readlines()
    
    # Find RequestDownload messages
    request_downloads = []
    for line in lines:
        if '0x7E0' in line and '34' in line:
            # Look for FF with RequestDownload
            if '100b3400440000' in line.lower():
                # Extract the address bytes
                import re
                match = re.search(r'100b340044([0-9a-f]{6})', line.lower())
                if match:
                    addr_partial = match.group(1)
                    request_downloads.append(('FF', addr_partial, line.strip()))
    
    # Find TransferData first frames
    transfer_data = []
    for line in lines:
        if '0x7E0' in line and 'TransferData' in line:
            import re
            # Look for FF with length
            match = re.search(r'([0-9a-f]{2})023601', line.lower())
            if match:
                transfer_data.append(line.strip())
    
    print("RequestDownload messages found:")
    for rd in request_downloads:
        print(f"  {rd}")
    
    print()
    print(f"TransferData first frames: {len(transfer_data)}")
    if transfer_data:
        print(f"  First: {transfer_data[0][:80]}...")
        print(f"  Last:  {transfer_data[-1][:80]}...")
    
    print()
    print("=" * 70)
    print("Memory Mapping Analysis")
    print("=" * 70)
    print()
    print("READ operation (from raw_capture):")
    print("  - Auth write to:     0x00000000 (2006 bytes)")
    print("  - RequestUpload from: 0x7D8000-0x800000 (calibration)")
    print()
    print("WRITE operation (from write_capture):")
    print("  - Auth write to:     0x00000000 (2006 bytes)")
    print("  - Data write to:     0x00004000 (seen in capture)")
    print()
    print("QUESTION: Why different addresses?")
    print()
    print("Possibilities:")
    print("  1. 0x4000 is a staging/buffer area")
    print("  2. Address 0x4000 maps to 0x7D8000 internally")
    print("  3. Different memory banks")
    print()
    print("RECOMMENDATION:")
    print("  Before flashing, capture a COMPLETE write operation")
    print("  including any final commit/copy commands.")


def main():
    analyze_captures()
    
    print()
    print("=" * 70)
    print("Safe Test Options")
    print("=" * 70)
    print()
    print("Option 1: Re-capture a full PowerVision write")
    print("  - Use PowerVision to write a tune")
    print("  - Capture the ENTIRE operation including finish")
    print("  - Analyze for any additional steps")
    print()
    print("Option 2: Read-back test")  
    print("  - Read current calibration (already done)")
    print("  - Write same data back")
    print("  - Read again and compare")
    print("  - If identical, write works correctly")
    print()
    print("Option 3: PowerVision file analysis")
    print("  - If you have .pvt files, we can analyze the format")
    print("  - Compare with raw dump to understand structure")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

