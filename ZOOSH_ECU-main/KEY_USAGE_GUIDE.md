# Dynojet Blowfish Key - Usage Guide

## The Key
```
R8SJzQ0c2IoKSIVa1YernejU9X5oKQRpPOt2ClU6HiZAk7oEeIHS9orR
```
- **Algorithm**: Blowfish (ECB mode)
- **Length**: 56 bytes (448 bits)

---

## 1. Tune File Decryption (.pvv files)

PowerVision tune files are encrypted with this key.

### What's Inside .pvv Files:
- Fuel injection maps
- Ignition timing tables
- Air-Fuel Ratio (AFR) targets
- Rev limiters
- Speed limiters
- VE (Volumetric Efficiency) tables

### How to Decrypt:
```python
from Crypto.Cipher import Blowfish

KEY = b"R8SJzQ0c2IoKSIVa1YernejU9X5oKQRpPOt2ClU6HiZAk7oEeIHS9orR"

def decrypt_pvv(encrypted_data):
    cipher = Blowfish.new(KEY, Blowfish.MODE_ECB)
    return cipher.decrypt(encrypted_data)
```

### Use Cases:
- Edit tunes without PowerVision software
- Convert tunes between formats
- Analyze competitor tunes
- Backup/archive tunes in readable format

---

## 2. ECU Security Access (Seed/Key)

When connecting to Harley-Davidson ECUs, a challenge-response authentication is required.

### The Process:
```
┌─────────────┐                      ┌─────────────┐
│  PowerVision │                      │    ECU      │
└──────┬──────┘                      └──────┬──────┘
       │                                    │
       │  1. Request Security Access        │
       │ ─────────────────────────────────► │
       │                                    │
       │  2. ECU sends SEED (challenge)     │
       │ ◄───────────────────────────────── │
       │                                    │
       │  3. Compute KEY using Blowfish     │
       │     KEY = Blowfish(SEED)           │
       │                                    │
       │  4. Send KEY (response)            │
       │ ─────────────────────────────────► │
       │                                    │
       │  5. Access Granted!                │
       │ ◄───────────────────────────────── │
       │                                    │
```

### Code Example:
```python
from Crypto.Cipher import Blowfish

KEY = b"R8SJzQ0c2IoKSIVa1YernejU9X5oKQRpPOt2ClU6HiZAk7oEeIHS9orR"

def compute_ecu_response(seed: bytes) -> bytes:
    """
    Given an ECU seed, compute the security response.
    This unlocks the ECU for reading/writing.
    """
    cipher = Blowfish.new(KEY, Blowfish.MODE_ECB)
    
    # Pad seed to 8 bytes (Blowfish block size)
    if len(seed) < 8:
        seed = seed + b'\x00' * (8 - len(seed))
    
    # Decrypt seed to get response
    response = cipher.decrypt(seed[:8])
    return response
```

### Use Cases:
- Build custom ECU flash tools
- Create open-source tuning software
- Develop diagnostic tools
- Research ECU behavior

---

## 3. Definition File Decryption

ECU definition files contain:
- Memory addresses for tables
- Table dimensions and units
- Scaling factors
- Checksums locations

### These files tell the software:
- Where fuel maps are stored in ECU memory
- How to interpret raw bytes as real values
- Which ECU versions are supported

---

## 4. Flash Read/Write Operations

With security access unlocked, you can:

### Read Operations:
- Dump full ECU calibration
- Read diagnostic trouble codes (DTCs)
- Extract current tune
- Read sensor calibrations

### Write Operations:
- Flash custom tunes
- Clear DTCs
- Modify parameters in real-time
- Update ECU firmware

---

## 5. Building Custom Tools

### Example: Simple Tune Editor
```python
#!/usr/bin/env python3
"""
Basic PVV Tune File Reader
"""
from Crypto.Cipher import Blowfish
import xml.etree.ElementTree as ET

KEY = b"R8SJzQ0c2IoKSIVa1YernejU9X5oKQRpPOt2ClU6HiZAk7oEeIHS9orR"

def read_pvv_file(filepath):
    """Read and decrypt a .pvv tune file"""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Check if encrypted (look for XML header)
    if not data.startswith(b'<?xml'):
        cipher = Blowfish.new(KEY, Blowfish.MODE_ECB)
        data = cipher.decrypt(data)
    
    # Parse XML
    root = ET.fromstring(data)
    
    # Extract tables
    tables = {}
    for table in root.findall('.//Table'):
        name = table.get('Name')
        tables[name] = {
            'columns': table.find('Columns').text if table.find('Columns') is not None else None,
            'rows': table.find('Rows').text if table.find('Rows') is not None else None,
            'data': table.find('Data').text if table.find('Data') is not None else None
        }
    
    return tables

# Usage
tables = read_pvv_file("mytune.pvv")
for name, data in tables.items():
    print(f"Table: {name}")
```

### Example: ECU Communication
```python
#!/usr/bin/env python3
"""
ECU Security Access Example (pseudo-code)
Requires: python-can, appropriate CAN interface
"""
from Crypto.Cipher import Blowfish
# import can  # Uncomment if you have python-can installed

KEY = b"R8SJzQ0c2IoKSIVa1YernejU9X5oKQRpPOt2ClU6HiZAk7oEeIHS9orR"

class ECUConnection:
    def __init__(self, interface='pcan', channel='PCAN_USBBUS1'):
        # self.bus = can.interface.Bus(interface=interface, channel=channel)
        self.cipher = Blowfish.new(KEY, Blowfish.MODE_ECB)
    
    def request_security_access(self):
        """
        UDS Security Access (Service 0x27)
        """
        # Step 1: Request seed (0x27 0x01)
        # self.send([0x27, 0x01])
        # seed = self.receive()
        
        # Step 2: Compute response
        # response = self.cipher.decrypt(seed)
        
        # Step 3: Send response (0x27 0x02 + key)
        # self.send([0x27, 0x02] + list(response))
        
        # Step 4: Check for positive response (0x67 0x02)
        pass
    
    def read_memory(self, address, length):
        """Read ECU memory after security access"""
        # UDS Read Memory By Address (0x23)
        pass
    
    def write_memory(self, address, data):
        """Write ECU memory after security access"""
        # UDS Write Memory By Address (0x3D)
        pass
```

---

## 6. Supported ECU Types

Based on Power Core's definition files, this key likely works with:

| Manufacturer | ECU Type | Years |
|--------------|----------|-------|
| Harley-Davidson | Delphi | 2007-2011 |
| Harley-Davidson | Delphi (newer) | 2012-2016 |
| Harley-Davidson | Delphi (CAN) | 2017+ |
| Indian | Various | 2014+ |
| Victory | Various | 2008-2017 |

---

## 7. Integration Examples

### With TunerPro
- Export decrypted calibration data
- Create XDF definition files
- Edit tunes in TunerPro RT

### With ECU Flash
- Use key for security bypass
- Custom flash utilities

### With CAN Analysis Tools
- Decode encrypted CAN messages
- Build protocol analyzers

---

## 8. Python Package Example

```python
#!/usr/bin/env python3
"""
dynojet_crypto.py - Reusable encryption module
"""
from Crypto.Cipher import Blowfish
from typing import Union

class DynojetCrypto:
    KEY = b"R8SJzQ0c2IoKSIVa1YernejU9X5oKQRpPOt2ClU6HiZAk7oEeIHS9orR"
    BLOCK_SIZE = 8
    
    def __init__(self, key: bytes = None):
        self.key = key or self.KEY
        self.cipher = Blowfish.new(self.key, Blowfish.MODE_ECB)
    
    def pad(self, data: bytes) -> bytes:
        """PKCS7 padding"""
        padding_len = self.BLOCK_SIZE - (len(data) % self.BLOCK_SIZE)
        return data + bytes([padding_len] * padding_len)
    
    def unpad(self, data: bytes) -> bytes:
        """Remove PKCS7 padding"""
        padding_len = data[-1]
        if padding_len > self.BLOCK_SIZE:
            return data
        return data[:-padding_len]
    
    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data"""
        return self.cipher.encrypt(self.pad(data))
    
    def decrypt(self, data: bytes) -> bytes:
        """Decrypt data"""
        return self.unpad(self.cipher.decrypt(data))
    
    def compute_seed_response(self, seed: bytes) -> bytes:
        """Compute ECU security response from seed"""
        if len(seed) < 8:
            seed = seed.ljust(8, b'\x00')
        return self.cipher.decrypt(seed[:8])


# Usage
if __name__ == "__main__":
    crypto = DynojetCrypto()
    
    # Test encryption
    plaintext = b"Hello ECU!"
    encrypted = crypto.encrypt(plaintext)
    decrypted = crypto.decrypt(encrypted)
    
    print(f"Original:  {plaintext}")
    print(f"Encrypted: {encrypted.hex()}")
    print(f"Decrypted: {decrypted}")
    
    # Test seed response
    seed = bytes([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0])
    response = crypto.compute_seed_response(seed)
    print(f"\nSeed:     {seed.hex()}")
    print(f"Response: {response.hex()}")
```

---

## Security & Legal Notes

### ⚠️ Important Considerations:

1. **Warranty**: Modifying ECU may void manufacturer warranty
2. **Emissions**: Tampering with emissions controls may violate EPA regulations
3. **Licensing**: Using this key may violate Dynojet's software license
4. **Safety**: Incorrect tunes can damage engines or cause unsafe operation
5. **Insurance**: Modifications may affect insurance coverage

### ✅ Legitimate Uses:
- Personal vehicle tuning (off-road/race use)
- Security research
- Educational purposes
- Interoperability with your own devices
- Right to repair advocacy

---

## Quick Reference

```python
# The Key
KEY = b"R8SJzQ0c2IoKSIVa1YernejU9X5oKQRpPOt2ClU6HiZAk7oEeIHS9orR"

# Quick Encrypt
from Crypto.Cipher import Blowfish
cipher = Blowfish.new(KEY, Blowfish.MODE_ECB)
encrypted = cipher.encrypt(data_padded_to_8_bytes)

# Quick Decrypt
decrypted = cipher.decrypt(encrypted_data)

# ECU Seed Response
response = cipher.decrypt(seed_padded_to_8_bytes)
```

