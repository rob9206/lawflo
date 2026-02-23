# Harley ECU Memory Map

## Overview

The Harley-Davidson Delphi ECU uses different address spaces for reading and writing tune data.

## Memory Regions

### Calibration Region (Read)

| Property | Value |
|----------|-------|
| Address | 0x7D8000 |
| Size | 0x28000 (163,840 bytes / 160KB) |
| Access | RequestUpload (0x35) |
| Format | 0xB0 |

This region contains the complete calibration data including:
- Fuel maps
- Ignition timing
- Rev limiters
- Sensor calibrations
- VE tables

### Tune Region (Write)

| Property | Value |
|----------|-------|
| Address | 0x00004000 |
| Size | 0x4000 (16,384 bytes / 16KB) |
| Access | RequestDownload (0x34) + TransferData (0x36) |
| Block Size | 256 bytes |

This is the writable tune region used for flashing.

## Address Mapping

The 16KB write region maps to a specific offset within the 160KB calibration:

```
┌─────────────────────────────────────────────────────────────────┐
│                    160KB CALIBRATION (0x7D8000)                  │
├─────────────────────────────────────────────────────────────────┤
│  0x00000 - 0x1BFFF  │  First 112KB                             │
├─────────────────────────────────────────────────────────────────┤
│  0x1C000 - 0x1FFFF  │  16KB TUNE REGION ← Maps to 0x4000 write │
├─────────────────────────────────────────────────────────────────┤
│  0x20000 - 0x27FFF  │  Last 32KB                               │
└─────────────────────────────────────────────────────────────────┘
```

### Address Calculation

```
Read address:  0x7D8000 + 0x1C000 = 0x7F4000
Write address: 0x00004000

Tune offset within calibration: 0x1C000 (114,688 bytes)
```

## Practical Usage

### Reading Tune from ECU

1. Read full calibration (160KB from 0x7D8000)
2. Extract bytes at offset 0x1C000, length 0x4000
3. Result: 16KB tune file

### Writing Tune to ECU

1. Prepare 16KB tune file
2. Write to address 0x00004000
3. Block size: 256 bytes
4. 64 blocks total

## File Formats

### Calibration Dump (.bin)

- Size: 163,840 bytes (160KB)
- Format: Raw binary
- Contents: Complete calibration data

### Tune File (.bin)

- Size: 16,384 bytes (16KB)
- Format: Raw binary
- Contents: Writable tune region only

## Extracting Tune from Calibration

```python
# Python example
TUNE_OFFSET = 0x1C000
TUNE_SIZE = 0x4000

with open('calibration.bin', 'rb') as f:
    cal_data = f.read()

tune_data = cal_data[TUNE_OFFSET:TUNE_OFFSET + TUNE_SIZE]

with open('tune.bin', 'wb') as f:
    f.write(tune_data)
```

## Verification

After writing, verify by:

1. Reading calibration again
2. Extracting tune region
3. Comparing with written data

```
Written tune SHA256 == Read back tune SHA256
```

## Notes

- The ECU requires authentication before memory access
- Re-authentication may be needed during long operations
- Block counter wraps from 255 to 1 (not 0)
- ECU reset (0x11 0x01) finalizes write operations

