#!/usr/bin/env python3
"""
Harley-Davidson ECU Flash Tool

Writes tune data to Harley-Davidson ECUs (Delphi).

Based on captured PowerVision write protocol:
1. Authenticate (same as read)
2. RequestDownload to address 0x4000, length = data size
3. TransferData in 256-byte blocks
4. ECUReset to finalize

WARNING: Writing incorrect data can BRICK your ECU!
         Only use with known-good tune files.
         Test thoroughly before using on valuable ECU.
"""

import can
import time
import sys
import os
import struct
from datetime import datetime

# Import from our main tool
from harley_ecu_dump import HarleyECU, TX_PHYSICAL, TX_FUNCTIONAL, RX_ECU

# Write configuration (from capture analysis)
WRITE_ADDRESS = 0x00004000   # Write destination (from capture: 340044000040...)
WRITE_LENGTH = 0x4000        # 16KB - matches capture
BLOCK_SIZE = 256             # Bytes per TransferData block (258 total with header)
MAX_RETRIES = 3


class HarleyFlasher(HarleyECU):
    """ECU Flash handler"""
    
    def request_download_write(self, address: int, length: int) -> tuple:
        """
        Request Download for writing data TO the ECU
        
        Args:
            address: Memory address to write to
            length: Total bytes to write
        
        Returns:
            (success, max_block_size)
        """
        # Build 11-byte message: 34 00 44 [4-byte addr] [4-byte len]
        msg = bytes([
            0x34,                    # RequestDownload
            0x00,                    # dataFormatIdentifier
            0x44,                    # ALFID (4-byte addr, 4-byte len)
        ])
        msg += struct.pack('>I', address)  # 4-byte address big-endian
        msg += struct.pack('>I', length)   # 4-byte length big-endian
        
        self.log(f"RequestDownload: addr=0x{address:08X}, len={length}", "debug")
        
        # Send as multi-frame (11 bytes > 7, needs FF+CF)
        if not self.send_multiframe(TX_PHYSICAL, msg):
            self.log("RequestDownload: No Flow Control", "fail")
            return (False, 0)
        
        # Wait for response
        resp = self.recv_response(timeout=2.0)
        
        if resp and resp[0] == 0x74:  # Positive response
            # Parse: 74 [lenFmt] [maxBlock...]
            len_fmt = (resp[1] >> 4) & 0x0F
            if len_fmt > 0 and len(resp) >= 2 + len_fmt:
                max_block = int.from_bytes(resp[2:2+len_fmt], 'big')
            else:
                max_block = 256
            
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
            }
            self.log(f"RequestDownload NRC 0x{nrc:02X}: {nrc_names.get(nrc, 'Unknown')}", "fail")
        else:
            self.log(f"No response to RequestDownload", "fail")
        
        return (False, 0)
    
    def transfer_data_write(self, block_seq: int, data: bytes) -> bool:
        """
        Send a block of data to ECU
        
        Args:
            block_seq: Block sequence number (1-255)
            data: Data bytes (should be BLOCK_SIZE)
        
        Returns:
            True if ECU accepted
        """
        # Build message: 36 [seq] [data...]
        msg = bytes([0x36, block_seq & 0xFF]) + data
        
        # Send as multi-frame (258 bytes total)
        if not self.send_multiframe(TX_PHYSICAL, msg):
            self.log(f"TransferData block {block_seq}: Send failed", "fail")
            return False
        
        # Wait for response
        resp = self.recv_response(timeout=2.0)
        
        if resp and resp[0] == 0x76:  # Positive response
            return True
        
        elif resp and resp[0] == 0x7F:
            nrc = resp[2] if len(resp) > 2 else 0
            self.log(f"TransferData block {block_seq} NRC 0x{nrc:02X}", "fail")
        else:
            self.log(f"No response to TransferData block {block_seq}", "fail")
        
        return False
    
    def request_transfer_exit(self) -> bool:
        """Finalize the transfer"""
        self.send_single_frame(TX_PHYSICAL, bytes([0x37]))
        resp = self.recv_response(timeout=2.0)
        
        if resp and resp[0] == 0x77:
            self.log("Transfer exit accepted", "ok")
            return True
        elif resp and resp[0] == 0x7F:
            nrc = resp[2] if len(resp) > 2 else 0
            self.log(f"TransferExit NRC 0x{nrc:02X}", "fail")
        return False
    
    def ecu_reset(self, reset_type: int = 0x01) -> bool:
        """
        Reset the ECU to apply changes
        
        Args:
            reset_type: 0x01 = hard reset, 0x02 = key off/on, 0x03 = soft reset
        """
        self.log(f"ECU Reset (type 0x{reset_type:02X})...", "info")
        self.send_single_frame(TX_PHYSICAL, bytes([0x11, reset_type]))
        
        # May not get response if ECU resets immediately
        resp = self.recv_response(timeout=1.0)
        if resp and resp[0] == 0x51:
            self.log("ECU Reset accepted", "ok")
            return True
        
        # No response might still be OK (ECU reset)
        return True
    
    def clear_dtc(self) -> bool:
        """
        Clear Diagnostic Trouble Codes after flash
        
        From capture: 14 FF FF FF (broadcast)
        """
        self.log("Clearing DTCs...", "info")
        # Send as broadcast (0x7DF)
        msg = can.Message(
            arbitration_id=TX_FUNCTIONAL,
            data=bytes([0x04, 0x14, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00]),
            is_extended_id=False
        )
        self.bus.send(msg)
        
        # Wait for response
        resp = self.recv_response(timeout=1.0)
        if resp and resp[0] == 0x54:
            self.log("DTCs cleared", "ok")
            return True
        return False
    
    def flash_data(self, address: int, data: bytes) -> bool:
        """
        Flash data to ECU memory
        
        Args:
            address: Destination address
            data: Data to write
        
        Returns:
            True if successful
        """
        total_len = len(data)
        self.log(f"Flashing {total_len} bytes to 0x{address:08X}", "info")
        
        # Step 1: Request Download
        success, max_block = self.request_download_write(address, total_len)
        if not success:
            return False
        
        # Use 256-byte blocks (matches capture)
        block_size = min(BLOCK_SIZE, max_block - 2)  # -2 for service+seq overhead
        
        # Step 2: Transfer Data
        offset = 0
        block_seq = 1
        retries = 0
        
        while offset < total_len:
            # Get chunk (pad last block if needed)
            chunk = data[offset:offset + block_size]
            if len(chunk) < block_size:
                chunk = chunk + bytes(block_size - len(chunk))
            
            # Send block
            if self.transfer_data_write(block_seq, chunk):
                offset += block_size
                block_seq = (block_seq % 255) + 1  # Wrap 255 -> 1
                retries = 0
                
                # Progress
                pct = min(100, offset * 100 // total_len)
                print(f"\r    Flashing: {pct:3d}% ({offset}/{total_len} bytes)", end='', flush=True)
            else:
                retries += 1
                if retries >= MAX_RETRIES:
                    print()
                    self.log(f"Too many retries at block {block_seq}", "fail")
                    return False
                time.sleep(0.1)
                continue
            
            # Keep-alive every 4KB
            if offset % 4096 == 0 and offset > 0:
                self.tester_present()
        
        print()  # Newline after progress
        
        # Note: PowerVision doesn't send RequestTransferExit (0x37)
        # It goes straight to ECU Reset after last TransferData
        
        self.log(f"Flash complete: {total_len} bytes written", "ok")
        return True
    
    def flash_tune(self, tune_file: str, reset_after: bool = True) -> bool:
        """
        Flash a tune file to the ECU
        
        Args:
            tune_file: Path to tune binary file
            reset_after: Whether to reset ECU after flashing
        
        Returns:
            True if successful
        """
        # Load tune file
        if not os.path.exists(tune_file):
            self.log(f"File not found: {tune_file}", "fail")
            return False
        
        with open(tune_file, 'rb') as f:
            tune_data = f.read()
        
        self.log(f"Tune file: {tune_file} ({len(tune_data)} bytes)", "info")
        
        # Authenticate first
        if not self.authenticate():
            self.log("Authentication failed", "fail")
            return False
        
        # Flash the data
        if not self.flash_data(WRITE_ADDRESS, tune_data):
            return False
        
        # Reset ECU to apply (as seen in capture)
        if reset_after:
            time.sleep(0.5)
            self.ecu_reset()
            time.sleep(1.0)
            self.clear_dtc()
        
        return True


def main():
    print("=" * 70)
    print("Harley ECU Flash Tool")
    print("=" * 70)
    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  WARNING: This tool writes to your ECU's memory!                 ║")
    print("║                                                                  ║")
    print("║  - Incorrect data can PERMANENTLY BRICK your ECU                 ║")
    print("║  - Only use with KNOWN-GOOD tune files                           ║")
    print("║  - Make sure you have a backup of your current tune              ║")
    print("║  - Ensure stable power during flash                              ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()
    
    if len(sys.argv) < 2:
        print("Usage: python ecu_flash.py <tune_file.bin>")
        print()
        print("Example: python ecu_flash.py my_tune.bin")
        print()
        print("The tune file should be a raw binary dump (not .pvt format)")
        return 1
    
    tune_file = sys.argv[1]
    
    if not os.path.exists(tune_file):
        print(f"[-] File not found: {tune_file}")
        return 1
    
    file_size = os.path.getsize(tune_file)
    print(f"[*] Tune file: {tune_file}")
    print(f"[*] File size: {file_size:,} bytes")
    print()
    
    # Sanity check file size
    # Note: Capture showed 16KB (0x4000) being written to address 0x4000
    # Full calibration read is 160KB - only subset is writable
    if file_size < 1000:
        print("[-] File too small - doesn't look like a tune file")
        return 1
    
    expected_size = WRITE_LENGTH  # 16KB from capture
    if file_size != expected_size:
        print(f"[!] WARNING: File size ({file_size}) doesn't match expected ({expected_size})")
        print(f"    Capture showed PowerVision writing exactly {expected_size} bytes")
        confirm = input("    Continue anyway? (y/n): ")
        if confirm.lower() != 'y':
            return 0
    
    if file_size > 200000:
        print("[!] File is very large - this may not be correct")
    
    # Final confirmation
    print("This will OVERWRITE your ECU's tune data!")
    response = input("Type 'FLASH' to proceed: ").strip()
    if response != 'FLASH':
        print("Cancelled.")
        return 0
    
    # Load auth payload
    flasher = HarleyFlasher()
    
    # Find capture file (any capture that contains auth payload)
    captures = sorted([f for f in os.listdir('.') 
                      if (f.startswith('capture_') or f.startswith('raw_capture_') or f.startswith('write_capture_')) 
                      and f.endswith('.txt')])
    if not captures:
        print("[-] No capture file found for auth payload")
        print("    Run: python harley_ecu_dump.py capture")
        return 1
    
    capture_file = captures[-1]
    print(f"[*] Using auth from: {capture_file}")
    
    if not flasher.load_auth_payload(capture_file):
        return 1
    
    if not flasher.connect():
        return 1
    
    try:
        success = flasher.flash_tune(tune_file)
        
        if success:
            print()
            print("=" * 70)
            print("[+] FLASH COMPLETE!")
            print("=" * 70)
            print()
            print("The ECU has been reset. You may need to:")
            print("  1. Turn ignition OFF")
            print("  2. Wait 10 seconds")
            print("  3. Turn ignition ON")
            print()
        else:
            print()
            print("[-] Flash failed!")
            print("    Check connection and try again")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted - ECU may be in inconsistent state!")
        print("    DO NOT turn off ignition - try running flash again")
        return 1
        
    finally:
        flasher.disconnect()


if __name__ == "__main__":
    sys.exit(main())

