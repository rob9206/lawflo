#!/usr/bin/env python3
"""
Harley ECU Tool - Command Line Interface

A comprehensive tool for Harley-Davidson ECU operations:
- Capture PowerVision traffic
- Dump ECU memory
- Flash tunes safely
- Extract and compare tunes
"""

import os
import sys
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.capture import CaptureManager
from tools.dump import ECUDumper
from tools.flash import ECUFlasher
from tools.extract import TuneExtractor


def print_banner():
    """Print application banner."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                    HARLEY ECU TOOL v1.0                          ║
║                                                                  ║
║  Capture • Dump • Flash • Extract                                ║
╚══════════════════════════════════════════════════════════════════╝
    """)


def cmd_capture(args):
    """Handle capture command."""
    print_banner()
    print("[CAPTURE] Recording CAN traffic...")
    print("")
    
    manager = CaptureManager()
    
    capture_file = manager.capture(
        duration=args.duration,
        output_dir=args.output
    )
    
    if capture_file:
        print("")
        print("[ANALYSIS] Checking capture...")
        results = manager.analyze_capture(capture_file)
        
        print(f"  Messages: {results['message_count']}")
        print(f"  Auth payload: {'✓' if results['has_auth_payload'] else '✗'}")
        print(f"  Security exchange: {'✓' if results['has_security_exchange'] else '✗'}")
        print(f"  Memory operations: {'✓' if results['has_memory_ops'] else '✗'}")
        
        return 0
    
    return 1


def cmd_dump(args):
    """Handle dump command."""
    print_banner()
    print("[DUMP] Reading ECU memory...")
    print("")
    
    dumper = ECUDumper(output_dir=args.output)
    
    try:
        if not dumper.initialize(args.capture):
            return 1
        
        if args.tune_only:
            result = dumper.dump_tune()
        else:
            results = dumper.full_dump()
            result = results.get('calibration')
        
        return 0 if result else 1
        
    finally:
        dumper.cleanup()


def cmd_flash(args):
    """Handle flash command."""
    print_banner()
    
    # Validate tune file
    valid, message = TuneExtractor.validate_tune(args.tune_file)
    if not valid:
        print(f"[ERROR] {message}")
        return 1
    
    print("[FLASH] Safe ECU Flash - 5 Star Safety")
    print("")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  WARNING: This will modify your ECU!                       ║")
    print("║                                                            ║")
    print("║  • Ensure stable power supply                              ║")
    print("║  • Do not interrupt the process                            ║")
    print("║  • A backup will be created automatically                  ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("")
    print(f"Tune file: {args.tune_file}")
    print(f"Capture: {args.capture or 'auto-detect'}")
    print("")
    
    if not args.yes:
        response = input("Type 'FLASH' to proceed: ")
        if response != 'FLASH':
            print("Aborted.")
            return 0
    
    flasher = ECUFlasher(backup_dir=args.backup_dir)
    
    success = flasher.flash(
        tune_file=args.tune_file,
        capture_file=args.capture,
        verify=not args.no_verify,
        double_verify=not args.no_verify
    )
    
    return 0 if success else 1


def cmd_extract(args):
    """Handle extract command."""
    print_banner()
    print("[EXTRACT] Extracting tune from calibration...")
    print("")
    
    output = args.output or args.calibration_file.replace('.bin', '_tune.bin')
    
    tune = TuneExtractor.extract_from_calibration(
        args.calibration_file,
        output
    )
    
    return 0 if tune else 1


def cmd_compare(args):
    """Handle compare command."""
    print_banner()
    
    report = TuneExtractor.generate_diff_report(
        args.tune1,
        args.tune2,
        args.output
    )
    
    print(report)
    return 0


def cmd_info(args):
    """Handle info command."""
    print_banner()
    
    valid, message = TuneExtractor.validate_tune(args.file)
    print(f"File: {args.file}")
    print(f"Status: {message}")
    
    if os.path.exists(args.file):
        import hashlib
        with open(args.file, 'rb') as f:
            data = f.read()
        checksum = hashlib.sha256(data).hexdigest()
        print(f"Size: {len(data)} bytes")
        print(f"SHA256: {checksum}")
    
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Harley ECU Tool - Read and Write ECU Data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s capture                    # Capture PowerVision traffic
  %(prog)s dump                       # Dump ECU calibration
  %(prog)s flash my_tune.bin          # Flash tune to ECU
  %(prog)s extract calibration.bin    # Extract tune from calibration
  %(prog)s compare tune1.bin tune2.bin # Compare two tunes
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Capture command
    cap_parser = subparsers.add_parser('capture', help='Capture CAN traffic')
    cap_parser.add_argument('-d', '--duration', type=int, default=120,
                           help='Capture duration in seconds (default: 120)')
    cap_parser.add_argument('-o', '--output', default='.',
                           help='Output directory')
    
    # Dump command
    dump_parser = subparsers.add_parser('dump', help='Dump ECU memory')
    dump_parser.add_argument('-c', '--capture', help='Capture file for auth')
    dump_parser.add_argument('-o', '--output', default='backups',
                            help='Output directory')
    dump_parser.add_argument('--tune-only', action='store_true',
                            help='Dump only tune region')
    
    # Flash command
    flash_parser = subparsers.add_parser('flash', help='Flash tune to ECU')
    flash_parser.add_argument('tune_file', help='Tune file to flash (16KB)')
    flash_parser.add_argument('-c', '--capture', help='Capture file for auth')
    flash_parser.add_argument('-b', '--backup-dir', default='backups',
                             help='Backup directory')
    flash_parser.add_argument('--no-verify', action='store_true',
                             help='Skip verification (not recommended)')
    flash_parser.add_argument('-y', '--yes', action='store_true',
                             help='Skip confirmation prompt')
    
    # Extract command
    ext_parser = subparsers.add_parser('extract', 
                                       help='Extract tune from calibration')
    ext_parser.add_argument('calibration_file', 
                           help='Calibration file (160KB)')
    ext_parser.add_argument('-o', '--output', help='Output tune file')
    
    # Compare command
    cmp_parser = subparsers.add_parser('compare', help='Compare two tunes')
    cmp_parser.add_argument('tune1', help='First tune file')
    cmp_parser.add_argument('tune2', help='Second tune file')
    cmp_parser.add_argument('-o', '--output', help='Output report file')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show file information')
    info_parser.add_argument('file', help='File to inspect')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Dispatch to command handler
    handlers = {
        'capture': cmd_capture,
        'dump': cmd_dump,
        'flash': cmd_flash,
        'extract': cmd_extract,
        'compare': cmd_compare,
        'info': cmd_info
    }
    
    handler = handlers.get(args.command)
    if handler:
        try:
            return handler(args)
        except KeyboardInterrupt:
            print("\nInterrupted.")
            return 1
        except Exception as e:
            print(f"\nError: {e}")
            return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

