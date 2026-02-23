# ECU Communication Tool

A comprehensive ECU communication, diagnostics, and tuning tool for Harley-Davidson and similar vehicles.

## Features

- 🔐 **Security Access** - Automatic unlock using extracted Blowfish key
- 💾 **Memory Read/Write** - Direct ECU memory access
- ⚡ **Flash Operations** - Dump and program ECU calibration
- 🔍 **Diagnostics** - Read and clear DTCs
- 📟 **Multiple Interfaces** - PCAN, SocketCAN, USB-CAN, Simulated

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Launch GUI

Double-click `ECUTool.bat` or run:

```bash
python ecu_gui.py
```

### 3. Connect and Unlock

1. Select your CAN interface
2. Click "Connect"
3. Click "Start Session"
4. Click "🔓 Unlock" for security access
5. You now have full ECU access!

## Supported Hardware

### CAN Interfaces

| Interface | Type | Notes |
|-----------|------|-------|
| PCAN | USB | Peak Systems USB adapters |
| SocketCAN | Linux | Built-in Linux CAN support |
| Kvaser | USB | Kvaser USB adapters |
| Vector | USB | Vector CANcase/CANboard |
| Serial | USB-Serial | Canable, USBtin (SLCAN) |
| Simulated | Virtual | For testing without hardware |

### Vehicles

| Manufacturer | Years | ECU Type |
|--------------|-------|----------|
| Harley-Davidson | 2007+ | Delphi |
| Indian | 2014+ | Delphi |
| Victory | 2008-2017 | Delphi |

## Command Line Usage

```bash
# List interfaces
python ecu_tool.py --list

# Read ECU info
python ecu_tool.py -i pcan:PCAN_USBBUS1 info

# Read memory
python ecu_tool.py -i pcan:PCAN_USBBUS1 read -a 0x10000 -n 256

# Dump flash
python ecu_tool.py -i pcan:PCAN_USBBUS1 dump -o flash.bin

# Read DTCs
python ecu_tool.py -i pcan:PCAN_USBBUS1 dtc

# Clear DTCs
python ecu_tool.py -i pcan:PCAN_USBBUS1 dtc --clear
```

## Python API

```python
from ecu_tool import ECUTool

# Create tool and connect
tool = ECUTool()
tool.connect("pcan:PCAN_USBBUS1")  # or "simulated:test"

# Start session and unlock
tool.start_session()
tool.security_access()

# Read ECU info
info = tool.read_ecu_info()
print(f"VIN: {info.vin}")
print(f"Software: {info.software_version}")

# Read memory
data = tool.read_memory(0x10000, 0x1000)
with open("dump.bin", "wb") as f:
    f.write(data)

# Read calibration
cal_data = tool.read_calibration()

# Read/clear DTCs
dtcs = tool.read_dtc()
for dtc in dtcs:
    print(f"{dtc.code}: {dtc.description}")

tool.clear_dtc()

# Disconnect
tool.disconnect()
```

## The Blowfish Key

This tool uses the extracted Dynojet Blowfish key:

```
R8SJzQ0c2IoKSIVa1YernejU9X5oKQRpPOt2ClU6HiZAk7oEeIHS9orR
```

The key is used for:
- ECU seed/key security access
- Tune file decryption
- Definition file decryption

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   ecu_gui.py                    │
│               (Graphical Interface)             │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│                   ecu_tool.py                   │
│              (High-level ECU API)               │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│                 ecu_protocol.py                 │
│     (UDS Protocol, Security, ISO-TP)            │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│                can_interface.py                 │
│        (CAN Bus Abstraction Layer)              │
├─────────────┬───────────┬───────────┬───────────┤
│    PCAN     │ SocketCAN │  Serial   │ Simulated │
└─────────────┴───────────┴───────────┴───────────┘
```

## Files

| File | Description |
|------|-------------|
| `ecu_gui.py` | Graphical user interface |
| `ecu_tool.py` | High-level ECU operations |
| `ecu_protocol.py` | UDS protocol implementation |
| `can_interface.py` | CAN bus abstraction |
| `ECUTool.bat` | Windows launcher |
| `requirements.txt` | Python dependencies |

## ⚠️ Warnings

- **Backup First** - Always dump your current calibration before flashing
- **Stable Power** - Ensure stable 12V power during flash operations
- **Correct Files** - Only flash files meant for your specific ECU
- **Warranty** - ECU modifications may void your warranty
- **Emissions** - Tampering may violate EPA regulations
- **Safety** - Incorrect tunes can damage engines

## Testing (Without Hardware)

Use the simulated interface for testing:

```bash
python ecu_tool.py -i simulated:test info
```

The simulator emulates basic ECU responses for development and testing.

## Troubleshooting

### "No response from ECU"
- Check CAN wiring
- Verify correct CAN ID (0x7E0/0x7E8)
- Ensure ECU is powered
- Try different bitrate (500k is common)

### "Security access denied"
- Make sure extended session is active
- Wait if "time delay not expired"
- Check security level (try level 1 or 3)

### "Interface not found"
- Install correct drivers for your interface
- Check USB connection
- Run `python ecu_tool.py --list` to see available interfaces

## License

For educational and personal use only.

