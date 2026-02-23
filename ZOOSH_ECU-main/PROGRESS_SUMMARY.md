# Dynojet PowerVision Reverse Engineering - Progress Summary

## What We Accomplished ✅

### 1. Blowfish Key Extraction
- Successfully extracted **two Blowfish keys** from Power Core
- Keys used for tune file encryption/decryption
- Created automated extraction toolkit with GUI

### 2. PowerVision Protocol Analysis
- Decoded frame format: `F0 [cmd] [params 12b] [00 00 00 seq 00 00 00] [payload] [checksum] F0`
- Identified commands: INIT(0x01), REGISTER(0x07), SUBSCRIBE(0x05), SOAP(0x0B), POLL(0x06), etc.
- Checksum algorithm: XOR all bytes with initial value 0xFE

### 3. Working Communication
- **INIT command works** - returns PowerVision serial number (ANNI2000AA135349)
- Successfully communicate at 115200 baud via COM4

### 4. Built Tools
- `ECUTool/` - UDS protocol implementation for direct ECU communication
- `DynojetKeyExtractor/` - Key extraction toolkit with GUI
- `PowerVision/` - Multiple protocol test scripts

## Current Blocker ❌

**SOAP commands don't get responses** despite:
- Matching exact Power Core frame structure
- Trying all handle values (1, 2, 4, 0x6d, etc.)
- Bike connected with ignition ON
- Full Power Core command sequence

**Likely cause:** Power Core has authentication/session establishment that we can't replicate.

## Next Steps (When Resuming)

### Option 1: Test WinPV (Ready to go)
WinPV is installed. Run Frida capture:
```powershell
C:\Users\dawso\AppData\Roaming\Python\Python311\Scripts\frida.exe -p [PID] -l C:\Users\dawso\Downloads\capture_winpv.js
```

### Option 2: PCAN-USB Adapter (~$270)
Bypass PowerVision, talk directly to ECU via CAN bus.
- We have UDS protocol code ready
- Just need hardware

### Option 3: Deeper Power Core Analysis
Hook .NET methods in DJ.Reflash.dll to find session initialization.

## Key Files

| File | Purpose |
|------|---------|
| `CAPTURED_KEYS.txt` | Extracted Blowfish keys |
| `dynojet_keys.py` | Python module with keys |
| `PowerVision/pv_step.py` | Step-by-step protocol test |
| `PowerVision/pv_exact2.py` | Exact Power Core sequence |
| `capture_winpv.js` | Frida script for WinPV |
| `ECUTool/` | Direct ECU communication tool |

## Hardware Setup
- PowerVision: COM4 (115200 8N1)
- Bike: 2017 Dyna Low Rider S
- 6-pin Delphi diagnostic connector

---
*Last updated: December 2024*

