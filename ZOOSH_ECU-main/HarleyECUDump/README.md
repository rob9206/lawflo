# Harley-Davidson ECU Dump Tool

A command-line tool for reading calibration/tune data from Harley-Davidson ECUs (Delphi).

## Features

- 🔐 Automatic security access handling (Level 1 XOR algorithm)
- 📡 CAN traffic capture for auth payload extraction
- 💾 Full ECU memory dump (config + calibration data)
- 🔄 Auto re-authentication to prevent session timeouts
- 📊 Progress display and error handling

## Requirements

### Hardware

- **PCAN-USB adapter** (IPEH-002022 or compatible)
- **PowerVision/Power Core device** (for initial auth capture only)
- **Harley-Davidson motorcycle** with Delphi ECU

### Wiring

Connect PCAN to the 6-pin Delphi diagnostic connector:

```
PCAN Pin 7 (CAN-H) ──→ Delphi Pin C (CAN-H)
PCAN Pin 2 (CAN-L) ──→ Delphi Pin A (CAN-L)  
PCAN Pin 3 (GND)   ──→ Delphi Pin B (Ground)
```

### Software

- Python 3.8+
- PCAN drivers installed

## Installation

```bash
# Clone or download this folder
cd HarleyECUDump

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Step 1: Capture Authentication Payload (One-time)

First, you need to capture the authentication payload from PowerVision:

```bash
python harley_ecu_dump.py capture
```

This will:
1. Connect to PCAN
2. Capture CAN traffic for 120 seconds
3. Save to `capture_TIMESTAMP.txt`

**During capture:** Use PowerVision to perform "Read from ECU"

### Step 2: Dump ECU Memory

Once you have a capture file:

```bash
python harley_ecu_dump.py dump
```

This will:
1. Load auth payload from the capture file
2. Authenticate with the ECU
3. Read ECU identification
4. Dump all memory regions
5. Save to `ecu_dump_TIMESTAMP/`

### Command Options

```bash
# Capture with custom settings
python harley_ecu_dump.py capture -o my_capture.txt -t 180

# Dump with specific capture file
python harley_ecu_dump.py dump -c my_capture.txt -o my_dump/

# List available capture files
python harley_ecu_dump.py list
```

## Output Files

After a successful dump, you'll have:

```
ecu_dump_20251226_204022/
├── config_low_000800.bin   # 2KB - VIN, identification
├── config_mid_740000.bin   # 1KB - Configuration  
├── calibration_7D8000.bin  # 160KB - TUNE DATA
└── dump_info.txt           # Dump metadata
```

The `calibration_7D8000.bin` contains the actual tune tables (fuel maps, timing, etc.)

## Memory Map

| Region | Address Range | Size | Contents |
|--------|---------------|------|----------|
| Config Low | 0x000800-0x001000 | 2KB | VIN, Part#, Serial |
| Config Mid | 0x740000-0x740400 | 1KB | Configuration |
| Calibration | 0x7D8000-0x800000 | 160KB | Tune data |

## Technical Details

### Protocol

- **CAN Bitrate:** 500 kbit/s
- **ECU Address:** 0x7E0 (TX) / 0x7E8 (RX)
- **Transport:** ISO-TP (ISO 15765-2)
- **Application:** UDS (ISO 14229)

### Security

- Level 1 algorithm: `Key = Seed XOR 0x9AE8`
- Authentication payload: 2008 bytes (ECU-specific)
- Session timeout: ~30 reads (auto re-auth)

## Troubleshooting

| Error | Solution |
|-------|----------|
| "No capture file found" | Run capture mode first |
| "Could not extract payload" | Capture didn't include PowerVision read |
| "Authentication failed" | Check wiring, try power cycling bike |
| "Read failed" | ECU may be locked, cycle ignition |
| NRC 0x36 "Exceeded attempts" | Wait or cycle ignition to clear lockout |

## Disclaimer

This tool is for educational and research purposes. Use responsibly and in accordance with applicable laws. The author is not responsible for any damage to vehicles or equipment.

## Credits

Reverse-engineered from PowerVision CAN traffic analysis.

