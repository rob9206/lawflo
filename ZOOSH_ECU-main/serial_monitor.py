#!/usr/bin/env python3
"""
Simple Serial Port Monitor

Monitors COM port traffic when Power Core isn't using it.
Close Power Core first, then run this.
"""

import serial
import serial.tools.list_ports
import time
import sys

def find_powervision():
    """Find PowerVision COM port"""
    for port in serial.tools.list_ports.comports():
        if 'power' in port.description.lower() and 'vision' in port.description.lower():
            return port.device, port.description
    return None, None

def monitor_port(port, baud=115200):
    """Monitor serial port and display all data"""
    print(f"\nMonitoring {port} at {baud} baud...")
    print("Press Ctrl+C to stop\n")
    print("=" * 60)
    
    try:
        ser = serial.Serial(port, baud, timeout=0.1)
        
        while True:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                timestamp = time.strftime("%H:%M:%S")
                hex_str = ' '.join(f'{b:02X}' for b in data)
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
                
                print(f"[{timestamp}] {len(data)} bytes:")
                print(f"  HEX:   {hex_str}")
                print(f"  ASCII: {ascii_str}")
                print()
            
            time.sleep(0.01)
            
    except serial.SerialException as e:
        print(f"Error: {e}")
        print("\nMake sure Power Core is CLOSED!")
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        if 'ser' in locals():
            ser.close()

def main():
    print("=" * 60)
    print("PowerVision Serial Monitor")
    print("=" * 60)
    
    port, desc = find_powervision()
    
    if not port:
        print("\nPowerVision not found!")
        print("\nAvailable ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device}: {p.description}")
        return
    
    print(f"\nFound: {desc}")
    print(f"Port: {port}")
    
    # Make sure Power Core is closed
    print("\n*** Make sure Power Core is CLOSED! ***")
    input("Press Enter when Power Core is closed...")
    
    # Try different baud rates
    bauds = [115200, 921600, 460800, 230400, 57600, 38400, 19200, 9600]
    
    print(f"\nTrying baud rate: {bauds[0]}")
    monitor_port(port, bauds[0])

if __name__ == "__main__":
    main()

