# PCAN Wiring Guide

## Harley-Davidson 6-Pin Diagnostic Connector

### Connector Location

The diagnostic connector is typically located:
- Under the seat
- Near the battery
- Behind a side cover

### Connector Pinout

```
    ┌─────────────┐
    │  F   E   D  │
    │  ●   ●   ○  │
    │             │
    │  ●   ●   ○  │
    │  C   B   A  │
    └─────────────┘
    (Looking at connector face)
```

| Pin | Function | Wire Color (typical) |
|-----|----------|----------------------|
| A | Ground | Black |
| B | Ground | Black |
| C | CAN-L | Green/White |
| D | Not used | - |
| E | CAN-H | Blue/White |
| F | 12V (key-on) | Red |

**Note**: Your connector may only have wires on A, B, C, E (D and F empty).

## PCAN-USB Adapter

### DB9 Pinout

```
    ┌─────────────────────┐
    │  1   2   3   4   5  │
    │  ○   ●   ●   ○   ○  │
    │                     │
    │    ●   ●   ○   ○    │
    │    6   7   8   9    │
    └─────────────────────┘
    (Looking at connector face)
```

| Pin | Function |
|-----|----------|
| 2 | CAN-L |
| 3 | GND |
| 7 | CAN-H |

**Other pins are not used for basic operation.**

## Wiring Connections

```
PCAN-USB DB9          Harley 6-Pin
─────────────          ────────────
Pin 2 (CAN-L)  ──────→  Pin C (CAN-L)
Pin 7 (CAN-H)  ──────→  Pin E (CAN-H)
Pin 3 (GND)    ──────→  Pin A or B (GND)
```

### Visual Diagram

```
┌─────────────────┐                 ┌─────────────────┐
│   PCAN-USB DB9  │                 │  Harley 6-Pin   │
│                 │                 │                 │
│  Pin 2 (CAN-L) ●├────────────────┼─● Pin C (CAN-L) │
│                 │                 │                 │
│  Pin 7 (CAN-H) ●├────────────────┼─● Pin E (CAN-H) │
│                 │                 │                 │
│  Pin 3 (GND)   ●├────────────────┼─● Pin A (GND)   │
│                 │                 │                 │
└─────────────────┘                 └─────────────────┘
```

## Verification

### Step 1: Physical Check

1. Verify wire colors match expected pins
2. Check for secure connections
3. No exposed wire touching metal

### Step 2: Continuity Test

With multimeter in continuity mode:
- PCAN Pin 2 should beep to Harley Pin C
- PCAN Pin 7 should beep to Harley Pin E
- PCAN Pin 3 should beep to Harley Pin A/B

### Step 3: Software Check

```bash
# With bike ignition ON
python harley_tool.py capture -d 5
```

You should see messages from CAN IDs like:
- 0x546, 0x547, 0x548 (VIN broadcast)
- 0x5xx (periodic vehicle data)

## Troubleshooting

### No CAN Traffic

| Check | Solution |
|-------|----------|
| Ignition off | Turn ignition ON |
| Wires swapped | Swap CAN-H and CAN-L |
| No ground | Verify ground connection |
| Wrong bitrate | Try 500k, 250k, 125k |

### Bus Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Bus Off" | Short circuit | Check wiring |
| "Bus Heavy" | Wrong bitrate | Use 500 kbit/s |
| Intermittent | Loose connection | Secure wires |

### PCAN-View Settings

If using PCAN-View for testing:
- Bitrate: 500 kbit/s
- Mode: Listen Only (initially)
- No hardware termination (usually)

## Cable Recommendations

### Best Practice

- Use twisted pair wire for CAN-H/CAN-L
- Keep cable length under 2 meters
- Use shielded cable if possible
- Secure connections (no loose wires)

### DIY Cable

Materials:
- DB9 male connector
- 6-pin Delphi female connector (or equivalent)
- 3 wires (~18-22 AWG)
- Heat shrink tubing

## Safety Notes

⚠️ **Electrical Safety**:
- Disconnect battery before wiring
- Don't short pins together
- Verify connections before powering on
- Don't leave cable connected when riding

⚠️ **CAN Bus Integrity**:
- Don't add termination resistors (ECU has them)
- Don't connect multiple devices simultaneously
- Disconnect PowerVision when using PCAN

