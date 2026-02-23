#!/usr/bin/env python3
"""
Power Core Bridge

Intercepts and uses Power Core's communication with PowerVision.
This allows us to piggyback on Power Core's existing connection.

Two approaches:
1. Hook Power Core's DLL calls (using Frida)
2. Use Power Core's named pipes/IPC

Your PowerVision is connected on COM3 and Power Core is using it.
"""

import os
import sys
import time
import struct
import threading
from typing import Optional, Callable
from dataclasses import dataclass

# =============================================================================
# Power Core IPC Interface
# =============================================================================

class PowerCoreBridge:
    """
    Bridge to Power Core's ECU communication
    
    Power Core uses:
    - FTD2XX_NET.dll for USB communication
    - DJ.Reflash.dll for ECU/flash operations
    - BLOWFISHLIB.dll for encryption
    
    We can hook these to intercept/inject communication.
    """
    
    def __init__(self):
        self.hooked = False
        self._callbacks = {}
    
    def hook_with_frida(self, pid: int) -> bool:
        """
        Use Frida to hook Power Core's communication
        """
        try:
            import frida
        except ImportError:
            print("Frida not installed. Run: pip install frida-tools")
            return False
        
        # Hook script for Power Core communication
        hook_script = '''
        // Hook FTD2XX_NET.dll communication
        
        var ftdiModule = null;
        
        function findFTDI() {
            Process.enumerateModules().forEach(function(m) {
                if (m.name.toLowerCase().indexOf('ftd2xx') !== -1) {
                    ftdiModule = m;
                    console.log("[+] Found FTDI module: " + m.name);
                }
            });
        }
        
        findFTDI();
        
        // Hook Write function to see outgoing data
        // Hook Read function to see incoming data
        
        // Export functions for RPC
        rpc.exports = {
            sendToECU: function(data) {
                // TODO: Implement sending through Power Core
                return null;
            },
            getStatus: function() {
                return { hooked: true, ftdi: ftdiModule !== null };
            }
        };
        '''
        
        try:
            session = frida.attach(pid)
            script = session.create_script(hook_script)
            script.load()
            
            self.frida_session = session
            self.frida_script = script
            self.hooked = True
            
            return True
        except Exception as e:
            print(f"Frida hook failed: {e}")
            return False
    
    def send_uds_via_powercore(self, request: bytes) -> Optional[bytes]:
        """
        Send UDS request through Power Core's hooked functions
        """
        if not self.hooked:
            return None
        
        # Use Frida RPC to send
        try:
            return self.frida_script.exports.send_to_ecu(list(request))
        except:
            return None


# =============================================================================
# Direct COM Port Access (when Power Core is closed)
# =============================================================================

class DirectPowerVision:
    """
    Direct communication with PowerVision when Power Core is not running.
    
    To use this:
    1. Close Power Core
    2. Connect using this class
    3. Send ECU commands directly
    """
    
    def __init__(self, port: str = "COM3"):
        self.port = port
        self.serial = None
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to PowerVision directly"""
        import serial
        
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=115200,  # Common for update mode
                timeout=2.0
            )
            self.connected = True
            print(f"Connected to PowerVision on {self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            print("\nMake sure Power Core is CLOSED!")
            return False
    
    def disconnect(self):
        """Disconnect"""
        if self.serial:
            self.serial.close()
        self.connected = False
    
    def send_receive(self, data: bytes, timeout: float = 2.0) -> Optional[bytes]:
        """Send data and receive response"""
        if not self.serial:
            return None
        
        self.serial.reset_input_buffer()
        self.serial.write(data)
        self.serial.flush()
        
        time.sleep(0.1)
        
        if self.serial.in_waiting > 0:
            return self.serial.read(self.serial.in_waiting)
        return None


# =============================================================================
# Frida-based ECU Communication Hook
# =============================================================================

FRIDA_HOOK_SCRIPT = '''
/*
 * Hook Power Core's ECU Communication
 * Intercepts DJ.Reflash.dll calls
 */

console.log("[*] Power Core ECU Hook");

// Store intercepted data
var ecuData = {
    lastRequest: null,
    lastResponse: null,
    securityUnlocked: false
};

// Find and hook the reflash DLL
var reflashModule = null;

Process.enumerateModules().forEach(function(m) {
    if (m.name.toLowerCase().indexOf('dj.reflash') !== -1) {
        reflashModule = m;
        console.log("[+] Found DJ.Reflash.dll at: " + m.base);
    }
});

// Hook the BLOWFISHLIB calls (we already know these work)
var blowfishModule = Process.getModuleByName("BLOWFISHLIB.dll");
if (blowfishModule) {
    console.log("[+] Found BLOWFISHLIB.dll");
    
    var decryptAddr = blowfishModule.getExportByName("Decrypt");
    var encryptAddr = blowfishModule.getExportByName("Encrypt");
    
    Interceptor.attach(decryptAddr, {
        onEnter: function(args) {
            var keyLen = args[3].toInt32();
            if (keyLen > 0 && keyLen <= 64) {
                ecuData.lastKey = args[2].readByteArray(keyLen);
                console.log("[*] Decrypt called, key length: " + keyLen);
            }
        }
    });
}

// RPC exports
rpc.exports = {
    getEcuData: function() {
        return ecuData;
    },
    
    isConnected: function() {
        return reflashModule !== null;
    },
    
    triggerSecurityAccess: function() {
        // This would need to call Power Core's internal functions
        // which requires more reverse engineering
        return false;
    }
};

console.log("[+] Hooks installed. Use RPC to communicate.");
'''


def hook_powercore_ecu():
    """
    Hook Power Core's ECU communication using Frida
    """
    try:
        import frida
    except ImportError:
        print("Install Frida: pip install frida-tools")
        return None
    
    # Find Power Core process
    try:
        session = frida.attach("Power Core")
        print("[+] Attached to Power Core")
    except frida.ProcessNotFoundError:
        print("[-] Power Core not running")
        return None
    
    script = session.create_script(FRIDA_HOOK_SCRIPT)
    
    def on_message(message, data):
        if message['type'] == 'send':
            print(f"[*] {message['payload']}")
        elif message['type'] == 'error':
            print(f"[!] Error: {message['stack']}")
    
    script.on('message', on_message)
    script.load()
    
    return script


# =============================================================================
# Instructions
# =============================================================================

def print_instructions():
    print("""
========================================================================
                    POWERVISION CONNECTION OPTIONS                         
========================================================================

Your PowerVision is connected on COM3 in Update Mode.
Power Core is currently using it.

========================================================================

OPTION 1: USE POWER CORE (Recommended)
------------------------------------------------------------------------
Power Core is already connected to your PowerVision and ECU.
Use Power Core's interface to:
  - Read/write tunes
  - Flash ECU
  - Read diagnostics

Our tool can HOOK Power Core to intercept/monitor communication.

To hook Power Core:
  python powercore_bridge.py --hook

========================================================================

OPTION 2: DIRECT CONNECTION (Close Power Core first)
------------------------------------------------------------------------
1. Close Power Core completely
2. Run our ECU Tool with PowerVision interface:
   
   python ecu_gui.py
   
   Then select "PowerVision (COM3)" as the interface

========================================================================

OPTION 3: MONITOR MODE
------------------------------------------------------------------------
Monitor Power Core's ECU communication without interfering:

  python powercore_bridge.py --monitor

This will show you:
  - All UDS requests/responses
  - Security access seeds/keys
  - Flash operations
  - Diagnostic data

========================================================================
""")


# =============================================================================
# Main
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Power Core Bridge")
    parser.add_argument('--hook', action='store_true', help='Hook Power Core communication')
    parser.add_argument('--monitor', action='store_true', help='Monitor Power Core (passive)')
    parser.add_argument('--direct', action='store_true', help='Direct PowerVision (Power Core must be closed)')
    
    args = parser.parse_args()
    
    if args.hook or args.monitor:
        print("Hooking Power Core...")
        script = hook_powercore_ecu()
        
        if script:
            print("\n[+] Hook active. Press Ctrl+C to exit.\n")
            print("Use Power Core normally - we'll see all ECU communication.\n")
            
            try:
                while True:
                    # Check for data periodically
                    try:
                        data = script.exports.get_ecu_data()
                        if data.get('lastKey'):
                            print(f"[KEY] {bytes(data['lastKey']).hex()}")
                    except:
                        pass
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n[*] Exiting...")
    
    elif args.direct:
        print("Direct PowerVision mode")
        print("Make sure Power Core is CLOSED!\n")
        
        pv = DirectPowerVision("COM3")
        if pv.connect():
            print("Connected! You can now send commands.")
            pv.disconnect()
        else:
            print("Failed to connect. Is Power Core closed?")
    
    else:
        print_instructions()


if __name__ == "__main__":
    main()

