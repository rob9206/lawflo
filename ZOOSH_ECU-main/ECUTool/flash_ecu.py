#!/usr/bin/env python3
"""
ECU Flash Tool

Flash calibration data to Harley-Davidson ECUs.
Requires: PCAN-USB or compatible CAN adapter

WARNING: Flashing can brick your ECU! Always have a backup!

Usage:
    python flash_ecu.py --read backup.bin      # Read current calibration
    python flash_ecu.py --write new_tune.bin   # Flash new calibration
    python flash_ecu.py --verify backup.bin    # Verify against file
"""

import argparse
import sys
import time
import os
from typing import Optional, Callable
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from ecu_tool import ECUTool, FlashRegion
from ecu_protocol import DYNOJET_KEY

# =============================================================================
# Constants
# =============================================================================

# Harley-Davidson ECU Flash Regions (Delphi ECU)
HARLEY_FLASH_REGIONS = [
    FlashRegion("Boot", 0x00000000, 0x4000, "Bootloader (DO NOT TOUCH)"),
    FlashRegion("Cal1", 0x00010000, 0x10000, "Calibration Area 1"),
    FlashRegion("Cal2", 0x00020000, 0x10000, "Calibration Area 2"),
    FlashRegion("Main", 0x00040000, 0x40000, "Main Program"),
]

# Safe region for flashing (calibration only)
SAFE_FLASH_START = 0x00010000
SAFE_FLASH_SIZE = 0x20000  # 128KB calibration area


# =============================================================================
# Flash Tool Class
# =============================================================================

class ECUFlashTool:
    """
    ECU Flash Tool for Harley-Davidson ECUs
    
    Supports reading and writing calibration data.
    Uses the captured Blowfish key for security access.
    """
    
    def __init__(self, interface: str = "pcan:PCAN_USBBUS1"):
        self.ecu = ECUTool()
        self.interface = interface
        self.connected = False
        self.unlocked = False
        
        # Callbacks
        self.on_progress: Optional[Callable[[int, int, str], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None
    
    def log(self, message: str):
        """Log a message"""
        if self.on_log:
            self.on_log(message)
        else:
            print(f"[*] {message}")
    
    def progress(self, current: int, total: int, message: str = ""):
        """Report progress"""
        if self.on_progress:
            self.on_progress(current, total, message)
        else:
            pct = (current / total * 100) if total > 0 else 0
            print(f"    {message} {pct:.1f}% ({current}/{total})")
    
    def connect(self) -> bool:
        """Connect to ECU via CAN adapter"""
        self.log(f"Connecting to {self.interface}...")
        
        if not self.ecu.connect(self.interface):
            self.log("Failed to connect to CAN interface")
            self.log("Make sure PCAN-USB is connected and drivers installed")
            return False
        
        self.connected = True
        self.log("CAN interface connected")
        return True
    
    def disconnect(self):
        """Disconnect from ECU"""
        self.ecu.disconnect()
        self.connected = False
        self.unlocked = False
        self.log("Disconnected")
    
    def unlock(self) -> bool:
        """Start session and unlock ECU"""
        if not self.connected:
            self.log("Not connected!")
            return False
        
        # Start extended diagnostic session
        self.log("Starting diagnostic session...")
        if not self.ecu.start_session():
            self.log("Failed to start session")
            return False
        
        # Security access with our captured key
        self.log("Performing security access...")
        if not self.ecu.security_access():
            self.log("Security access failed")
            return False
        
        self.unlocked = True
        self.log("ECU unlocked successfully!")
        return True
    
    def read_calibration(self, output_file: str) -> bool:
        """
        Read calibration data from ECU
        
        Args:
            output_file: Path to save calibration data
        """
        if not self.unlocked:
            self.log("ECU not unlocked! Run unlock() first")
            return False
        
        self.log(f"Reading calibration from ECU...")
        self.log(f"Address: 0x{SAFE_FLASH_START:08X}")
        self.log(f"Size: {SAFE_FLASH_SIZE // 1024} KB")
        
        data = self.ecu.read_memory(SAFE_FLASH_START, SAFE_FLASH_SIZE)
        
        if data:
            with open(output_file, 'wb') as f:
                f.write(data)
            self.log(f"Calibration saved to: {output_file}")
            self.log(f"Size: {len(data)} bytes")
            return True
        else:
            self.log("Failed to read calibration!")
            return False
    
    def verify_calibration(self, input_file: str) -> bool:
        """
        Verify ECU calibration against file
        
        Args:
            input_file: Path to calibration file to verify against
        """
        if not self.unlocked:
            self.log("ECU not unlocked!")
            return False
        
        self.log(f"Reading file: {input_file}")
        with open(input_file, 'rb') as f:
            file_data = f.read()
        
        self.log(f"Reading ECU calibration...")
        ecu_data = self.ecu.read_memory(SAFE_FLASH_START, len(file_data))
        
        if not ecu_data:
            self.log("Failed to read ECU!")
            return False
        
        if file_data == ecu_data:
            self.log("VERIFICATION PASSED - Data matches!")
            return True
        else:
            # Find differences
            diffs = 0
            for i in range(min(len(file_data), len(ecu_data))):
                if file_data[i] != ecu_data[i]:
                    diffs += 1
            
            self.log(f"VERIFICATION FAILED - {diffs} bytes differ!")
            return False
    
    def write_calibration(self, input_file: str, verify: bool = True) -> bool:
        """
        Write calibration data to ECU
        
        ⚠️ WARNING: This can brick your ECU!
        
        Args:
            input_file: Path to calibration file to flash
            verify: Verify after writing (recommended)
        """
        if not self.unlocked:
            self.log("ECU not unlocked!")
            return False
        
        # Read file
        self.log(f"Reading file: {input_file}")
        with open(input_file, 'rb') as f:
            data = f.read()
        
        # Validate size
        if len(data) > SAFE_FLASH_SIZE:
            self.log(f"ERROR: File too large! Max {SAFE_FLASH_SIZE} bytes")
            return False
        
        if len(data) < 1024:
            self.log(f"ERROR: File too small! Minimum 1KB")
            return False
        
        # Confirm
        self.log("")
        self.log("=" * 50)
        self.log("⚠️  WARNING: ABOUT TO FLASH ECU!")
        self.log("=" * 50)
        self.log(f"File: {input_file}")
        self.log(f"Size: {len(data)} bytes")
        self.log(f"Address: 0x{SAFE_FLASH_START:08X}")
        self.log("")
        self.log("DO NOT disconnect power or USB during flash!")
        self.log("=" * 50)
        
        # Flash
        self.log("")
        self.log("Flashing calibration...")
        
        success = self.ecu.flash_calibration(data)
        
        if success:
            self.log("Flash complete!")
            
            if verify:
                self.log("")
                self.log("Verifying...")
                if self.verify_calibration(input_file):
                    self.log("Flash and verify successful!")
                    return True
                else:
                    self.log("VERIFY FAILED! ECU may be corrupted!")
                    return False
            
            return True
        else:
            self.log("FLASH FAILED!")
            return False
    
    def get_ecu_info(self) -> dict:
        """Get ECU information"""
        info = self.ecu.read_ecu_info()
        return {
            'vin': info.vin,
            'serial': info.serial,
            'hardware': info.hardware_version,
            'software': info.software_version,
            'calibration': info.calibration_id
        }


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ECU Flash Tool for Harley-Davidson",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Read current calibration to backup file
    python flash_ecu.py --interface pcan:PCAN_USBBUS1 --read backup.bin
    
    # Write new calibration
    python flash_ecu.py --interface pcan:PCAN_USBBUS1 --write new_tune.bin
    
    # Verify ECU matches file
    python flash_ecu.py --interface pcan:PCAN_USBBUS1 --verify backup.bin
    
    # Get ECU info only
    python flash_ecu.py --interface pcan:PCAN_USBBUS1 --info

Supported interfaces:
    pcan:PCAN_USBBUS1    - PCAN-USB adapter
    socketcan:can0       - SocketCAN (Linux)
    simulated:test       - Simulator (for testing)
        """
    )
    
    parser.add_argument('--interface', '-i', default='pcan:PCAN_USBBUS1',
                        help='CAN interface (default: pcan:PCAN_USBBUS1)')
    parser.add_argument('--read', '-r', metavar='FILE',
                        help='Read calibration from ECU to file')
    parser.add_argument('--write', '-w', metavar='FILE',
                        help='Write calibration from file to ECU')
    parser.add_argument('--verify', '-v', metavar='FILE',
                        help='Verify ECU calibration against file')
    parser.add_argument('--info', action='store_true',
                        help='Show ECU information only')
    parser.add_argument('--no-verify', action='store_true',
                        help='Skip verification after write')
    
    args = parser.parse_args()
    
    if not any([args.read, args.write, args.verify, args.info]):
        parser.print_help()
        return 1
    
    # Create flash tool
    tool = ECUFlashTool(args.interface)
    
    try:
        # Connect
        if not tool.connect():
            return 1
        
        # Unlock ECU
        if not tool.unlock():
            return 1
        
        # Perform operation
        if args.info:
            info = tool.get_ecu_info()
            print("\n=== ECU Information ===")
            for key, value in info.items():
                print(f"  {key}: {value or 'N/A'}")
            print()
        
        elif args.read:
            if not tool.read_calibration(args.read):
                return 1
        
        elif args.verify:
            if not tool.verify_calibration(args.verify):
                return 1
        
        elif args.write:
            # Extra confirmation for write
            print("\n" + "!" * 50)
            print("!!! WARNING: YOU ARE ABOUT TO FLASH THE ECU !!!")
            print("!" * 50)
            print(f"\nFile: {args.write}")
            print("\nThis can PERMANENTLY DAMAGE your ECU!")
            print("Make sure you have a backup!")
            print("")
            
            confirm = input("Type 'FLASH' to continue: ")
            if confirm != 'FLASH':
                print("Aborted.")
                return 1
            
            if not tool.write_calibration(args.write, verify=not args.no_verify):
                return 1
        
        return 0
    
    finally:
        tool.disconnect()


if __name__ == "__main__":
    sys.exit(main())

