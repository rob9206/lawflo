#!/usr/bin/env python3
"""
Memory Map Analyzer

Compares the 160KB calibration dump with the 16KB write data
to understand the memory mapping between read and write addresses.

Also extracts the actual write data from a capture file for comparison.
"""

import os
import re
import sys
from datetime import datetime


def extract_write_data_from_capture(capture_file):
    """
    Extract the actual tune data sent during a write operation
    from a capture file.
    
    Returns:
        bytes: The tune data that was written (should be ~16KB)
    """
    print(f"[*] Extracting write data from: {capture_file}")
    
    with open(capture_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Find all TX messages to 0x7E0
    pattern = r'0x7E0\s+8\s+([0-9A-Fa-f]{16})'
    matches = re.findall(pattern, content)
    
    # Look for the data write sequence (after 2nd auth, to address 0x4000)
    # Pattern: RequestDownload to 0x4000 followed by TransferData blocks
    
    data_blocks = []
    collecting = False
    current_block = bytearray()
    block_seq = 0
    expected_seq = 1
    
    for i, match in enumerate(matches):
        frame = bytes.fromhex(match)
        pci = frame[0]
        
        # Look for RequestDownload to 0x4000 (FF: 10 0B 34 00 44 00 00 40 00)
        if (pci & 0xF0) == 0x10:  # First Frame
            total_len = ((pci & 0x0F) << 8) | frame[1]
            if total_len == 11 and frame[2] == 0x34:  # RequestDownload
                # Check if address is 0x4000
                # Full message: 34 00 44 00 00 40 00 00 00 40 00
                # We have bytes 2-7 in FF, need to check
                if frame[5] == 0x00 and frame[6] == 0x00 and frame[7] == 0x40:
                    print(f"    Found RequestDownload to 0x4000 at message {i}")
                    collecting = True
                    data_blocks = []
                    expected_seq = 1
                    continue
        
        # Collect TransferData First Frames (len=258 for data blocks)
        if collecting and (pci & 0xF0) == 0x10:
            total_len = ((pci & 0x0F) << 8) | frame[1]
            if total_len == 258 and frame[2] == 0x36:  # TransferData
                block_seq = frame[3]
                if block_seq == expected_seq or (expected_seq > 255 and block_seq == 1):
                    current_block = bytearray(frame[4:8])  # First 4 bytes of data
                    expected_seq = (block_seq % 255) + 1 if block_seq < 64 else block_seq + 1
                continue
        
        # Collect Consecutive Frames
        if collecting and (pci & 0xF0) == 0x20 and len(current_block) > 0:
            cf_seq = pci & 0x0F
            current_block.extend(frame[1:8])
            
            # Check if block complete (256 bytes)
            if len(current_block) >= 256:
                data_blocks.append(bytes(current_block[:256]))
                current_block = bytearray()
                
                if len(data_blocks) % 10 == 0:
                    print(f"    Extracted {len(data_blocks)} blocks...")
    
    if data_blocks:
        all_data = b''.join(data_blocks)
        print(f"    [OK] Extracted {len(all_data)} bytes ({len(data_blocks)} blocks)")
        return all_data
    else:
        print("    [-] No write data found in capture")
        return None


def find_pattern_in_dump(dump_data, pattern, pattern_name="pattern"):
    """
    Find where a pattern appears in the dump data.
    """
    matches = []
    pattern_len = len(pattern)
    
    for i in range(len(dump_data) - pattern_len + 1):
        if dump_data[i:i+pattern_len] == pattern:
            matches.append(i)
    
    return matches


def compare_regions(dump_data, write_data):
    """
    Compare write data against all possible 16KB regions in the dump.
    """
    write_len = len(write_data)
    dump_len = len(dump_data)
    
    print(f"\n[*] Comparing {write_len} byte write data against {dump_len} byte dump")
    print(f"    Checking all possible offsets...")
    
    best_match_offset = -1
    best_match_score = 0
    
    # Check every possible offset
    for offset in range(0, dump_len - write_len + 1, 256):  # Check every 256 bytes
        matches = sum(1 for i in range(write_len) if dump_data[offset + i] == write_data[i])
        score = matches / write_len * 100
        
        if score > best_match_score:
            best_match_score = score
            best_match_offset = offset
        
        if score > 90:
            print(f"    High match at offset 0x{offset:X}: {score:.1f}%")
    
    print(f"\n    Best match: offset 0x{best_match_offset:X} ({best_match_score:.1f}% match)")
    
    return best_match_offset, best_match_score


def analyze_write_data(write_data):
    """
    Analyze the structure of write data.
    """
    print(f"\n[*] Analyzing write data structure ({len(write_data)} bytes)")
    
    # Check for patterns
    print(f"    First 32 bytes: {write_data[:32].hex()}")
    print(f"    Last 32 bytes:  {write_data[-32:].hex()}")
    
    # Count 0xFF bytes (often padding/unused)
    ff_count = write_data.count(0xFF)
    fe_count = write_data.count(0xFE)
    zero_count = write_data.count(0x00)
    
    print(f"    0xFF bytes: {ff_count} ({ff_count*100//len(write_data)}%)")
    print(f"    0xFE bytes: {fe_count} ({fe_count*100//len(write_data)}%)")
    print(f"    0x00 bytes: {zero_count} ({zero_count*100//len(write_data)}%)")
    
    # Find distinct regions
    print("\n    Scanning for region boundaries...")
    last_byte = write_data[0]
    region_start = 0
    regions = []
    
    for i, b in enumerate(write_data):
        if abs(b - last_byte) > 64:  # Significant change
            if i - region_start > 16:  # Minimum region size
                regions.append((region_start, i, write_data[region_start]))
            region_start = i
        last_byte = b
    
    if len(write_data) - region_start > 16:
        regions.append((region_start, len(write_data), write_data[region_start]))
    
    print(f"    Found {len(regions)} distinct regions")
    for start, end, first_byte in regions[:10]:
        print(f"      0x{start:04X}-0x{end:04X}: {end-start} bytes, starts with 0x{first_byte:02X}")


def main():
    print("=" * 70)
    print("Memory Map Analyzer")
    print("=" * 70)
    print()
    
    # Find files
    dump_dir = "../PowerVision"
    dump_file = None
    
    # Look for calibration dump
    for d in os.listdir(dump_dir):
        if d.startswith("ecu_dump_"):
            cal_path = os.path.join(dump_dir, d, "calibration_7D8000.bin")
            if os.path.exists(cal_path):
                dump_file = cal_path
                break
    
    if not dump_file:
        # Check current directory
        for d in os.listdir("."):
            if d.startswith("ecu_dump_"):
                cal_path = os.path.join(d, "calibration_7D8000.bin")
                if os.path.exists(cal_path):
                    dump_file = cal_path
                    break
    
    # Find write capture
    capture_file = None
    for f in sorted(os.listdir("."), reverse=True):
        if f.startswith("write_capture_") and f.endswith(".txt"):
            capture_file = f
            break
    
    print(f"Calibration dump: {dump_file or 'NOT FOUND'}")
    print(f"Write capture:    {capture_file or 'NOT FOUND'}")
    print()
    
    if not dump_file:
        print("[-] No calibration dump found!")
        print("    Run: python harley_ecu_dump.py dump")
        return 1
    
    if not capture_file:
        print("[-] No write capture found!")
        print("    Run: python capture_write.py during a PowerVision write")
        return 1
    
    # Load dump
    with open(dump_file, 'rb') as f:
        dump_data = f.read()
    print(f"[+] Loaded dump: {len(dump_data)} bytes")
    
    # Extract write data from capture
    write_data = extract_write_data_from_capture(capture_file)
    
    if not write_data:
        print("\n[-] Could not extract write data from capture")
        print("    The capture may be incomplete or in wrong format")
        return 1
    
    # Save extracted write data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    write_file = f"extracted_write_{timestamp}.bin"
    with open(write_file, 'wb') as f:
        f.write(write_data)
    print(f"[+] Saved extracted write data: {write_file}")
    
    # Analyze write data
    analyze_write_data(write_data)
    
    # Compare with dump
    offset, score = compare_regions(dump_data, write_data)
    
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()
    
    if score > 80:
        # Calculate actual addresses
        read_base = 0x7D8000
        actual_read_addr = read_base + offset
        
        print(f"[+] FOUND MAPPING!")
        print(f"    Write address: 0x00004000")
        print(f"    Maps to read address: 0x{actual_read_addr:08X}")
        print(f"    Offset in dump: 0x{offset:X} ({offset} bytes)")
        print(f"    Match confidence: {score:.1f}%")
        print()
        print(f"    To extract writable region from a dump:")
        print(f"    dump_data[0x{offset:X}:0x{offset:X}+0x4000]")
        
        # Save mapping info
        with open("memory_map.txt", 'w') as f:
            f.write(f"Memory Map Analysis Results\n")
            f.write(f"===========================\n")
            f.write(f"Date: {datetime.now()}\n")
            f.write(f"Dump file: {dump_file}\n")
            f.write(f"Capture file: {capture_file}\n")
            f.write(f"\n")
            f.write(f"Write address (ECU): 0x00004000\n")
            f.write(f"Read address (ECU):  0x{actual_read_addr:08X}\n")
            f.write(f"Offset in dump:      0x{offset:X}\n")
            f.write(f"Write size:          {len(write_data)} bytes\n")
            f.write(f"Match confidence:    {score:.1f}%\n")
        print(f"\n[+] Saved mapping info: memory_map.txt")
        
    else:
        print(f"[-] No strong match found (best: {score:.1f}%)")
        print("    The write data may not be present in the calibration dump,")
        print("    or uses a different encoding/format.")
        print()
        print("    Possible reasons:")
        print("    1. Write data is to a different memory region")
        print("    2. Data is transformed before writing")
        print("    3. Incomplete capture")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

