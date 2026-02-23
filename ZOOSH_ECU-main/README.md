# Dynojet Power Core - Blowfish Key Extractor

Automated tool to extract Blowfish encryption keys from Dynojet Power Core software.

## Prerequisites

1. **Python 3.x** installed
2. **Frida** installed: `pip install frida-tools`
3. **Dynojet Power Core** installed

## Quick Start

### Method 1: Double-click (Easiest)
1. Start Power Core
2. Double-click `run_extractor.bat`
3. In Power Core, open a tune file or connect to a device
4. The key will be displayed in the console

### Method 2: PowerShell
```powershell
cd C:\Users\dawso\Downloads\DynojetKeyExtractor
.\run_extractor.ps1
```

### Method 3: Manual Frida
```powershell
# Find Power Core PID
Get-Process | Where-Object { $_.ProcessName -match "Power" }

# Run Frida with the PID
frida -p <PID> -l extract_key.js
```

## Output

When a key is captured, you'll see:

```
╔══════════════════════════════════════════════════════════════╗
║                    🔐 KEY CAPTURED!                          ║
╠══════════════════════════════════════════════════════════════╣
║ Operation:  DECRYPT                                          ║
║ Data Size:  68096 bytes                                      ║
║ Key Length: 56 bytes (448 bits)                              ║
╠══════════════════════════════════════════════════════════════╣
║ KEY (ASCII):                                                 ║
║ R8SJzQ0c2IoKSIVa1YernejU9X5oKQRpPOt2ClU6HiZAk7oEeIHS9orR    ║
╠══════════════════════════════════════════════════════════════╣
║ KEY (HEX):                                                   ║
║ 52 38 53 4a 7a 51 30 63 32 49 6f 4b 53 49 56 61              ║
║ 31 59 65 72 6e 65 6a 55 39 58 35 6f 4b 51 52 70              ║
║ 50 4f 74 32 43 6c 55 36 48 69 5a 41 6b 37 6f 45              ║
║ 65 49 48 53 39 6f 72 52                                      ║
╚══════════════════════════════════════════════════════════════╝
```

## Files

| File | Description |
|------|-------------|
| `run_extractor.bat` | Windows batch launcher (double-click) |
| `run_extractor.ps1` | PowerShell automation script |
| `extract_key.js` | Frida hook script |
| `README.md` | This file |

## Technical Details

- **Target**: BLOWFISHLIB.dll (native DLL)
- **Functions Hooked**: `Encrypt()`, `Decrypt()`
- **Method**: Runtime function interception via Frida
- **Key Size**: Up to 56 bytes (448 bits, Blowfish maximum)

## Troubleshooting

### "Frida not found"
Install Frida: `pip install frida-tools`

### "Power Core not running"
Start Power Core before running the extractor, or use:
```powershell
.\run_extractor.ps1 -StartPowerCore
```

### "Failed to attach"
- Make sure Power Core is running
- Try running PowerShell as Administrator
- Check if antivirus is blocking Frida

## Legal Notice

This tool is for educational and research purposes only. Extracting encryption keys may violate software licenses and applicable laws. Use responsibly.

