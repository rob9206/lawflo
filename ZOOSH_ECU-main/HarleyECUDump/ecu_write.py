#!/usr/bin/env python3
"""
Harley-Davidson ECU Write Tool (EXPERIMENTAL)

Writes calibration/tune data to Harley-Davidson ECUs.

WARNING: This is EXPERIMENTAL. Writing incorrect data can brick your ECU!
         Only use with known-good tune files after full testing.

Status: INCOMPLETE - Needs write capture analysis to determine:
        - Exact write address format
        - Checksum calculation
        - Commit/finalize sequence
"""

import can
import time
import sys
import os
import struct
from datetime import datetime

# Import from our read tool
from harley_ecu_dump import (
    HarleyECU, 
    TX_PHYSICAL, TX_FUNCTIONAL, RX_ECU,
    SEED_XOR_KEY, MEMORY_REGIONS
)


class HarleyECUWriter(HarleyECU):
    """Extended ECU handler with write capability"""
    
    def __init__(self):
        super().__init__()
        self.verbose = True
    
    def request_download(self, address: int, length: int, 
                         data_fmt: int = 0x00, addr_fmt: int = 0x44) -> tuple:
        """
        Request Download - prepare ECU to receive data
        
        Args:
            address: Memory address to write to
            length: Number of bytes to write
            data_fmt: Data format (0x00 = no compression/encryption)
            addr_fmt: Address/length format (0x44 = 4-byte addr, 4-byte len)
        
        Returns:
            (success, max_block_size)
        """
        # Build request: 34 [dataFmt] [addrFmt] [addr...] [len...]
        req = bytes([0x34, data_fmt, addr_fmt])
        
        if addr_fmt == 0x44:
            req += struct.pack('>I', address)  # 4-byte address
            req += struct.pack('>I', length)   # 4-byte length
        elif addr_fmt == 0x24:
            req += struct.pack('>H', address)  # 2-byte address
            req += struct.pack('>I', length)   # 4-byte length
        else:
            self.log(f"Unsupported addr_fmt: 0x{addr_fmt:02X}", "fail")
            return (False, 0)
        
        self.log(f"RequestDownload @ 0x{address:08X}, {length} bytes", "debug")
        
        # Send (may be multi-frame)
        if len(req) > 7:
            if not self.send_multiframe(TX_PHYSICAL, req):
                return (False, 0)
        else:
            self.send_single_frame(TX_PHYSICAL, req)
        
        # Get response
        resp = self.recv_response(timeout=2.0)
        
        if resp and resp[0] == 0x74:  # Positive response
            # Parse max block length from response
            len_fmt = (resp[1] >> 4) & 0x0F
            if len_fmt > 0 and len(resp) >= 2 + len_fmt:
                max_block = int.from_bytes(resp[2:2+len_fmt], 'big')
            else:
                max_block = 256  # Default
            
            self.log(f"Download accepted, max block: {max_block}", "ok")
            return (True, max_block)
        
        elif resp and resp[0] == 0x7F:
            nrc = resp[2] if len(resp) > 2 else 0
            nrc_names = {
                0x13: "Incorrect message length",
                0x22: "Conditions not correct",
                0x31: "Request out of range",
                0x33: "Security access denied",
                0x70: "Upload/download not accepted",
                0x71: "Transfer data suspended",
            }
            self.log(f"RequestDownload NRC 0x{nrc:02X}: {nrc_names.get(nrc, 'Unknown')}", "fail")
        else:
            self.log(f"No response to RequestDownload", "fail")
        
        return (False, 0)
    
    def transfer_data(self, block_seq: int, data: bytes) -> bool:
        """
        Transfer Data - send a block of data to ECU
        
        Args:
            block_seq: Block sequence number (1-255, wraps)
            data: Data bytes to transfer
        
        Returns:
            True if ECU accepted the block
        """
        # Build request: 36 [blockSeq] [data...]
        req = bytes([0x36, block_seq & 0xFF]) + data
        
        self.log(f"TransferData block {block_seq}, {len(data)} bytes", "debug")
        
        # Send (almost always multi-frame)
        if len(req) > 7:
            if not self.send_multiframe(TX_PHYSICAL, req):
                return False
        else:
            self.send_single_frame(TX_PHYSICAL, req)
        
        # Get response
        resp = self.recv_response(timeout=5.0)
        
        if resp and resp[0] == 0x76:  # Positive response
            return True
        
        elif resp and resp[0] == 0x7F:
            nrc = resp[2] if len(resp) > 2 else 0
            self.log(f"TransferData NRC 0x{nrc:02X}", "fail")
        else:
            self.log(f"No response to TransferData", "fail")
        
        return False
    
    def request_transfer_exit(self) -> bool:
        """
        Request Transfer Exit - finalize the transfer
        
        Returns:
            True if ECU accepted
        """
        self.send_single_frame(TX_PHYSICAL, bytes([0x37]))
        resp = self.recv_response(timeout=2.0)
        
        if resp and resp[0] == 0x77:
            self.log("Transfer exit accepted", "ok")
            return True
        
        elif resp and resp[0] == 0x7F:
            nrc = resp[2] if len(resp) > 2 else 0
            self.log(f"TransferExit NRC 0x{nrc:02X}", "fail")
        
        return False
    
    def write_memory(self, address: int, data: bytes, 
                     data_fmt: int = 0x00, block_size: int = 256) -> bool:
        """
        Write data to ECU memory
        
        Args:
            address: Starting memory address
            data: Data to write
            data_fmt: Data format identifier
            block_size: Maximum bytes per transfer block
        
        Returns:
            True if write completed successfully
        """
        self.log(f"Writing {len(data)} bytes to 0x{address:08X}", "info")
        
        # Step 1: Request Download
        success, max_block = self.request_download(address, len(data), data_fmt)
        if not success:
            return False
        
        # Use smaller of our block_size and ECU's max
        actual_block = min(block_size, max_block - 2)  # -2 for service + seq
        
        # Step 2: Transfer Data in blocks
        offset = 0
        block_seq = 1
        
        while offset < len(data):
            chunk = data[offset:offset + actual_block]
            
            if not self.transfer_data(block_seq, chunk):
                self.log(f"Transfer failed at block {block_seq}", "fail")
                return False
            
            offset += len(chunk)
            block_seq = (block_seq % 255) + 1
            
            # Progress
            pct = offset * 100 // len(data)
            print(f"\r    Writing: {pct}% ({offset}/{len(data)} bytes)", end='', flush=True)
            
            # Keep-alive every 4KB
            if offset % 4096 == 0:
                self.tester_present()
        
        print()  # Newline after progress
        
        # Step 3: Request Transfer Exit
        if not self.request_transfer_exit():
            self.log("Transfer exit failed", "fail")
            return False
        
        self.log(f"Write complete: {len(data)} bytes", "ok")
        return True
    
    def write_calibration(self, cal_file: str) -> bool:
        """
        Write a calibration file to the ECU
        
        Args:
            cal_file: Path to calibration binary file
        
        Returns:
            True if write completed successfully
        """
        if not os.path.exists(cal_file):
            self.log(f"File not found: {cal_file}", "fail")
            return False
        
        with open(cal_file, 'rb') as f:
            cal_data = f.read()
        
        self.log(f"Calibration file: {len(cal_data)} bytes", "info")
        
        # Verify file size matches expected calibration region
        expected_size = 0x800000 - 0x7D8000  # 163840 bytes
        if len(cal_data) != expected_size:
            self.log(f"Warning: File size {len(cal_data)} != expected {expected_size}", "fail")
            response = input("Continue anyway? [y/N]: ").strip().lower()
            if response != 'y':
                return False
        
        # TODO: Verify checksum before writing
        
        # Write to calibration region
        return self.write_memory(0x7D8000, cal_data, data_fmt=0xB0)


def main():
    print("=" * 70)
    print("Harley ECU Write Tool (EXPERIMENTAL)")
    print("=" * 70)
    print()
    print("!!! WARNING !!!")
    print("This tool is EXPERIMENTAL and INCOMPLETE.")
    print("Writing incorrect data can PERMANENTLY BRICK your ECU!")
    print()
    print("Status: Needs write capture analysis to complete.")
    print("        Run 'python capture_write.py' first to capture")
    print("        the PowerVision write protocol.")
    print()
    
    # Check for write capture
    write_captures = [f for f in os.listdir('.') if f.startswith('write_capture_')]
    if not write_captures:
        print("[-] No write captures found.")
        print("    Run: python capture_write.py")
        print("    While PowerVision writes a tune to ECU.")
        return 1
    
    print(f"[*] Found write captures: {write_captures}")
    print()
    print("Next steps:")
    print("  1. Analyze write_capture_*.txt to understand protocol")
    print("  2. Identify checksum algorithm")
    print("  3. Test with known-good tune file")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

