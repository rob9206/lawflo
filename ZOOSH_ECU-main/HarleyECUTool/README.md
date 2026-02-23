# Harley ECU Tool

A professional tool for reading and writing Harley-Davidson ECU data.

## Features

- **Capture**: Record PowerVision CAN traffic to extract authentication
- **Dump**: Read ECU calibration and tune data (160KB / 16KB)
- **Flash**: Write tunes with 5-star safety (backup, verify, double-verify)
- **Extract**: Extract 16KB tune from 160KB calibration dump
- **Compare**: Byte-by-byte tune comparison with diff reports

## Requirements

- Windows 10/11
- Python 3.8+
- PCAN-USB adapter (IPEH-002022 or similar)
- PCAN Basic API drivers

## Installation

```bash
# Clone or download
cd HarleyECUTool

# Install dependencies
pip install -r requirements.txt

# Install PCAN drivers from Peak Systems
# https://www.peak-system.com/PCAN-Basic.239.0.html
```

## Usage

### GUI (Recommended)

```bash
python harley_gui.py
# Or double-click: HarleyECUTool.bat
```

### Command Line

```bash
# Capture PowerVision traffic (120 seconds)
python harley_tool.py capture

# Dump ECU memory
python harley_tool.py dump

# Flash tune (with safety checks)
python harley_tool.py flash my_tune.bin

# Extract tune from calibration
python harley_tool.py extract calibration.bin

# Compare two tunes
python harley_tool.py compare tune1.bin tune2.bin
```

## Directory Structure

```
HarleyECUTool/
├── harley_tool.py      # CLI entry point
├── harley_gui.py       # GUI entry point
├── requirements.txt    # Dependencies
│
├── core/               # Core modules
│   ├── can_interface.py   # CAN communication
│   ├── protocol.py        # UDS protocol
│   ├── auth.py            # Authentication
│   └── memory.py          # Memory operations
│
├── tools/              # High-level tools
│   ├── capture.py         # Traffic capture
│   ├── dump.py            # ECU dump
│   ├── flash.py           # ECU flash
│   └── extract.py         # Tune extraction
│
├── docs/               # Documentation
│   ├── PROTOCOL.md        # Protocol details
│   ├── MEMORY_MAP.md      # Memory mapping
│   └── SAFETY.md          # Safety information
│
└── backups/            # Default backup location
```

## Safety Features (5-Star Rating)

| Feature | Description |
|---------|-------------|
| Pre-flight checks | Validates files and connections |
| CAN quality test | 95%+ success rate required |
| Triple backup | Saves to 3 locations |
| Block verification | Each 256-byte block verified |
| Double verify | Reads back twice after write |
| Audit logging | Full operation log saved |

## First Time Setup

1. **Capture Authentication**:
   - Connect PCAN to bike's diagnostic port
   - Connect PowerVision to bike
   - Run `python harley_tool.py capture`
   - Perform a "Read from ECU" in PowerVision
   - Wait for capture to complete

2. **Create Initial Backup**:
   - Run `python harley_tool.py dump`
   - Keep backup files safe!

3. **Flash Tunes**:
   - Use `python harley_tool.py flash tune.bin`
   - Always verify tune file before flashing

## Wiring

PCAN-USB to Harley 6-pin Diagnostic Connector:

```
PCAN Pin 2 (CAN-L)  →  Connector Pin C
PCAN Pin 7 (CAN-H)  →  Connector Pin E
PCAN Pin 3 (GND)    →  Connector Pin A or B
```

## Memory Map

| Region | Address | Size | Description |
|--------|---------|------|-------------|
| Calibration | 0x7D8000 | 160KB | Full calibration (read) |
| Tune | 0x00004000 | 16KB | Writable tune region |
| Tune Offset | 0x1C000 | - | Offset within calibration |

## Troubleshooting

**"No CAN traffic detected"**
- Check wiring (CAN-H/CAN-L may be swapped)
- Verify ignition is ON
- Try 500k/250k bitrates

**"Authentication failed"**
- Capture file may be incomplete
- Re-capture with fresh PowerVision read

**"CAN quality too low"**
- Check connections
- Reduce cable length
- Avoid running engine during operations

## License

For personal/educational use only. Not affiliated with Harley-Davidson or Dynojet.

## Disclaimer

⚠️ **WARNING**: Modifying ECU data can damage your vehicle or void warranty. Use at your own risk. Always maintain backups.

