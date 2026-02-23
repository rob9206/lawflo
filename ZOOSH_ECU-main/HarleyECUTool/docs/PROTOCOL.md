# Harley ECU Communication Protocol

## Overview

This document describes the communication protocol used by Harley-Davidson ECUs, specifically the Delphi units found in models from approximately 2014-2020.

## Physical Layer

- **Bus**: CAN 2.0A
- **Bitrate**: 500 kbit/s
- **Frame Format**: Standard 11-bit identifiers

### CAN Identifiers

| ID | Direction | Description |
|----|-----------|-------------|
| 0x7E0 | Tester → ECU | Physical addressing to ECU |
| 0x7E8 | ECU → Tester | Response from ECU |
| 0x7DF | Tester → All | Functional/broadcast addressing |

## Transport Layer

ISO-TP (ISO 15765-2) for multi-frame messages.

### Frame Types

| Type | PCI Byte | Description |
|------|----------|-------------|
| SF | 0x0N | Single Frame (N = length, 0-7 bytes) |
| FF | 0x1N NN | First Frame (NNN = total length) |
| CF | 0x2N | Consecutive Frame (N = sequence 0-F) |
| FC | 0x30 | Flow Control |

## UDS Services

Standard UDS (ISO 14229) with proprietary extensions.

### Supported Services

| Service | ID | Description |
|---------|-----|-------------|
| DiagnosticSessionControl | 0x10 | Session management |
| ECUReset | 0x11 | Reset ECU |
| ClearDTC | 0x14 | Clear fault codes |
| ReadDataByID | 0x22 | Read data identifiers |
| SecurityAccess | 0x27 | Security unlock |
| RequestDownload | 0x34 | Initiate download |
| RequestUpload | 0x35 | Initiate upload |
| TransferData | 0x36 | Transfer data blocks |
| TesterPresent | 0x3E | Keep session alive |

### Session Types

| Session | ID | Description |
|---------|-----|-------------|
| Default | 0x01 | Standard operation |
| Programming | 0x02 | Flash programming |
| Extended | 0x03 | Extended diagnostics |

## Security Access

### Level 1 (Standard)

Algorithm: `Key = Seed XOR 0x9AE8`

```
Request:  27 01
Response: 67 01 [SEED_H] [SEED_L]

Request:  27 02 [KEY_H] [KEY_L]
Response: 67 02
```

### Example

```
Seed: 0xEE00
Key = 0xEE00 XOR 0x9AE8 = 0x74E8
```

## Authentication Payload

After Level 1 security, memory operations require a proprietary 2008-byte authentication payload.

### Sequence

1. RequestDownload (0x34) for address 0x00000000, length 0x07D6
2. TransferData (0x36) with 2008-byte payload
3. Memory operations now enabled

### RequestDownload Format

```
34 00 44 00 00 00 00 00 00 07 D6
│  │  │  └──────────────┴──────── Length (0x07D6 = 2006)
│  │  │  └──────────────────────── Address (0x00000000)
│  │  └─────────────────────────── ALFID (4-byte addr, 4-byte len)
│  └────────────────────────────── Data format (no compression)
└───────────────────────────────── Service ID
```

## Memory Read (RequestUpload)

### Request Format

```
35 [FMT] 01 [ADDR_H] [ADDR_MH] [ADDR_ML] [ADDR_L]
│   │    │  └──────────────────────────────────── 4-byte address
│   │    └──────────────────────────────────────── Address format
│   └───────────────────────────────────────────── Data format (0xA0/0xB0)
└────────────────────────────────────────────────── Service ID
```

### Response

Returns data starting at specified address. Block size is typically ~1KB per request.

## Memory Write (RequestDownload + TransferData)

### RequestDownload for Write

```
34 00 44 [ADDR_4B] [LEN_4B]
```

### TransferData

```
36 [BLOCK_NUM] [DATA_256B]
```

Block size: 256 bytes
Block counter: 1-255, wraps around

### ECU Reset After Write

```
11 01  (Hard reset)
```

## Memory Map

| Address | Size | Description |
|---------|------|-------------|
| 0x7D8000 | 160KB | Calibration region (read) |
| 0x00004000 | 16KB | Tune region (write) |

### Tune Mapping

The 16KB write region at 0x4000 corresponds to offset 0x1C000 within the 160KB calibration dump (which is read from 0x7D8000).

```
Calibration Read:  0x7D8000 + 0x1C000 = 0x7F4000 (tune start)
Tune Write:        0x00004000
```

## Error Handling

### Negative Response Codes

| NRC | Description |
|-----|-------------|
| 0x10 | General reject |
| 0x11 | Service not supported |
| 0x12 | Sub-function not supported |
| 0x13 | Incorrect message length |
| 0x22 | Conditions not correct |
| 0x31 | Request out of range |
| 0x33 | Security access denied |
| 0x35 | Invalid key |
| 0x36 | Exceeded attempts |
| 0x78 | Response pending |

## Session Timeout

The ECU session times out after approximately 5 seconds of inactivity. During long operations:
- Send TesterPresent (0x3E 0x00) periodically
- Re-authenticate every ~32 read operations

