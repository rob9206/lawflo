# ECU Flash Safety Guide

## ⚠️ IMPORTANT WARNING

Flashing an ECU can permanently damage your motorcycle's engine control system. Incorrect data or interrupted operations can result in:

- **Bricked ECU** (requiring dealer replacement)
- **Engine damage** (wrong fuel/timing maps)
- **Voided warranty**
- **Failed emissions compliance**

**Proceed only if you fully understand the risks.**

## Safety Rating System

### ★★★★★ 5-Star Safety Features

This tool implements the highest level of safety for ECU flashing:

| Feature | Description | Risk Mitigation |
|---------|-------------|-----------------|
| Pre-flight checks | Validates files, connections, ECU state | Catches errors before starting |
| CAN quality test | 95%+ success rate required | Ensures reliable communication |
| Triple backup | Saves to 3 locations | Redundancy against data loss |
| Block verification | Each 256-byte block verified | Catches write errors immediately |
| Double read-back | Reads entire tune twice after write | Confirms complete success |
| Audit logging | Full operation log saved | Troubleshooting and evidence |

## Before Flashing

### Checklist

- [ ] Battery fully charged (>12.4V)
- [ ] Stable power connection (battery tender recommended)
- [ ] Engine OFF, ignition ON
- [ ] No other devices on CAN bus
- [ ] PCAN connected and verified
- [ ] Capture file with valid auth payload
- [ ] Tune file verified (correct size, known-good source)
- [ ] Recent backup of current tune

### Environment

- Work in a dry, temperature-controlled environment
- Avoid flashing during storms (power fluctuation risk)
- Keep USB cables short and secure
- Don't run other demanding software during flash

## During Flashing

### Critical Period

**DO NOT INTERRUPT** the flash process once it begins:

1. Don't touch the computer
2. Don't disconnect any cables
3. Don't turn off ignition
4. Don't disturb the motorcycle

The critical period is during "Writing blocks..." - this is when the ECU's memory is being modified.

### Expected Duration

| Operation | Time |
|-----------|------|
| Authentication | ~5 seconds |
| Backup creation | ~3 minutes |
| Flash write | ~30 seconds |
| Verification | ~3 minutes |
| **Total** | **~7 minutes** |

## After Flashing

### Immediate Steps

1. Wait for "FLASH COMPLETE" confirmation
2. Verify checksum matches
3. Turn ignition OFF
4. Wait 10 seconds
5. Turn ignition ON
6. Check for warning lights

### First Ride

- Monitor engine behavior
- Listen for unusual sounds
- Check for engine codes
- Take a short test ride first
- Have recovery plan if issues arise

## Recovery Procedures

### If Flash Fails

1. **Don't panic** - the tool creates backups
2. Note the error message
3. Check audit log for details
4. Try re-flashing with original backup
5. If ECU unresponsive, try ignition cycle

### If ECU Won't Boot

1. Try key cycle: OFF → wait 30s → ON
2. Disconnect battery for 5 minutes
3. Reconnect and try ignition
4. If still dead, may need dealer recovery

### Backup Locations

Backups are saved to multiple locations:
- `./backups/` (tool directory)
- `~/harley_ecu_backups/` (home directory)
- `~/Documents/harley_ecu_backups/`

## Common Failure Modes

| Symptom | Cause | Solution |
|---------|-------|----------|
| "CAN quality too low" | Bad connection | Check wiring |
| "Authentication failed" | Invalid capture | Re-capture auth |
| Write stops mid-block | Power/connection issue | Re-flash with backup |
| Verification fails | Data corruption | Re-flash with known-good file |
| ECU won't respond | Session timeout | Ignition cycle, retry |

## Best Practices

### Do:
- Always create backups before flashing
- Use known-good tune files
- Verify tune file size (16,384 bytes)
- Keep capture files organized
- Maintain stable power
- Flash in controlled environment

### Don't:
- Flash with low battery
- Use unverified tune files
- Interrupt the flash process
- Flash during storms
- Ignore error messages
- Skip verification steps

## Technical Support

If you encounter issues:

1. Check the audit log file
2. Note exact error messages
3. Document the sequence of events
4. Have backup files available
5. Capture file may need refresh

## Legal Disclaimer

This tool is provided for educational and personal use only. By using this tool, you acknowledge:

- ECU modification may void manufacturer warranty
- Emissions compliance may be affected
- You assume all risks associated with ECU modification
- The authors are not responsible for any damage

**Use at your own risk.**

