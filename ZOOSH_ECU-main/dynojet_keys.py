#!/usr/bin/env python3
"""
Dynojet Power Core - Encryption Keys

Captured via runtime analysis of Power Core + PowerVision + Harley ECU
December 2024
"""

from Crypto.Cipher import Blowfish

# =============================================================================
# CAPTURED KEYS
# =============================================================================

# Key 1: Definition/Metadata files (~16 KB data)
KEY_DEFINITIONS = b"hI8I2TlMgp3OteXkMO0C39sPdl6VNCq4DmSIxYZcUcBOgKT8eKe4zv0I"

# Key 2: ECU Calibration/Tune data (~68-168 KB data)
KEY_CALIBRATION = b"R8SJzQ0c2IoKSIVa1YernejU9X5oKQRpPOt2ClU6HiZAk7oEeIHS9orR"

# Alias for backwards compatibility
DYNOJET_KEY = KEY_CALIBRATION


# =============================================================================
# ENCRYPTION/DECRYPTION FUNCTIONS
# =============================================================================

def pad(data: bytes, block_size: int = 8) -> bytes:
    """Pad data to block boundary"""
    padding_len = block_size - (len(data) % block_size)
    if padding_len == block_size:
        padding_len = 0
    return data + bytes([padding_len] * padding_len)


def unpad(data: bytes) -> bytes:
    """Remove padding"""
    if not data:
        return data
    padding_len = data[-1]
    if padding_len > 8 or padding_len == 0:
        return data
    return data[:-padding_len]


def decrypt_definitions(data: bytes) -> bytes:
    """Decrypt definition/metadata files"""
    cipher = Blowfish.new(KEY_DEFINITIONS, Blowfish.MODE_ECB)
    return cipher.decrypt(data)


def encrypt_definitions(data: bytes) -> bytes:
    """Encrypt definition/metadata files"""
    cipher = Blowfish.new(KEY_DEFINITIONS, Blowfish.MODE_ECB)
    return cipher.encrypt(pad(data))


def decrypt_calibration(data: bytes) -> bytes:
    """Decrypt ECU calibration/tune data"""
    cipher = Blowfish.new(KEY_CALIBRATION, Blowfish.MODE_ECB)
    return cipher.decrypt(data)


def encrypt_calibration(data: bytes) -> bytes:
    """Encrypt ECU calibration/tune data"""
    cipher = Blowfish.new(KEY_CALIBRATION, Blowfish.MODE_ECB)
    return cipher.encrypt(pad(data))


def compute_ecu_response(seed: bytes) -> bytes:
    """
    Compute ECU security access response from seed
    Used for UDS SecurityAccess (0x27) service
    """
    cipher = Blowfish.new(KEY_CALIBRATION, Blowfish.MODE_ECB)
    
    # Pad seed to 8 bytes
    if len(seed) < 8:
        seed = seed + b'\x00' * (8 - len(seed))
    
    return cipher.decrypt(seed[:8])


def try_decrypt(data: bytes) -> tuple:
    """
    Try to decrypt with both keys, return (key_name, decrypted_data)
    """
    # Try calibration key first (more common)
    try:
        cipher = Blowfish.new(KEY_CALIBRATION, Blowfish.MODE_ECB)
        decrypted = cipher.decrypt(data[:8])
        # Check if it looks like valid data (has printable chars or valid structure)
        if any(32 <= b <= 126 for b in decrypted):
            return ("CALIBRATION", cipher.decrypt(data))
    except:
        pass
    
    # Try definitions key
    try:
        cipher = Blowfish.new(KEY_DEFINITIONS, Blowfish.MODE_ECB)
        decrypted = cipher.decrypt(data[:8])
        if any(32 <= b <= 126 for b in decrypted):
            return ("DEFINITIONS", cipher.decrypt(data))
    except:
        pass
    
    return (None, None)


# =============================================================================
# MAIN / TEST
# =============================================================================

def main():
    print("=" * 60)
    print("DYNOJET POWER CORE - ENCRYPTION KEYS")
    print("=" * 60)
    
    print("\nKey 1 (Definitions):")
    print(f"  ASCII: {KEY_DEFINITIONS.decode()}")
    print(f"  Length: {len(KEY_DEFINITIONS)} bytes ({len(KEY_DEFINITIONS)*8} bits)")
    
    print("\nKey 2 (Calibration):")
    print(f"  ASCII: {KEY_CALIBRATION.decode()}")
    print(f"  Length: {len(KEY_CALIBRATION)} bytes ({len(KEY_CALIBRATION)*8} bits)")
    
    # Test round-trip
    print("\n" + "-" * 60)
    print("Testing encryption round-trip...")
    
    test_data = b"TestData12345678"
    
    # Test calibration key
    encrypted = encrypt_calibration(test_data)
    decrypted = decrypt_calibration(encrypted)
    decrypted = unpad(decrypted)
    
    print(f"\nCalibration Key Test:")
    print(f"  Original:  {test_data}")
    print(f"  Encrypted: {encrypted.hex()[:32]}...")
    print(f"  Decrypted: {decrypted}")
    print(f"  Match: {'✓ PASS' if test_data == decrypted else '✗ FAIL'}")
    
    # Test definitions key
    encrypted = encrypt_definitions(test_data)
    decrypted = decrypt_definitions(encrypted)
    decrypted = unpad(decrypted)
    
    print(f"\nDefinitions Key Test:")
    print(f"  Original:  {test_data}")
    print(f"  Encrypted: {encrypted.hex()[:32]}...")
    print(f"  Decrypted: {decrypted}")
    print(f"  Match: {'✓ PASS' if test_data == decrypted else '✗ FAIL'}")
    
    # Test ECU response
    print("\n" + "-" * 60)
    print("ECU Security Access Test:")
    test_seed = bytes([0x12, 0x34, 0x56, 0x78])
    response = compute_ecu_response(test_seed)
    print(f"  Seed:     {test_seed.hex()}")
    print(f"  Response: {response.hex()}")


if __name__ == "__main__":
    main()

