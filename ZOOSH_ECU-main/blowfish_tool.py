#!/usr/bin/env python3
"""
Dynojet Blowfish Encryption Tool

Usage:
    python blowfish_tool.py --test           # Test the key
    python blowfish_tool.py --encrypt FILE   # Encrypt a file
    python blowfish_tool.py --decrypt FILE   # Decrypt a file
"""

import argparse
import sys
import os

try:
    from Crypto.Cipher import Blowfish
except ImportError:
    print("Error: PyCryptodome not installed.")
    print("Install with: pip install pycryptodome")
    sys.exit(1)

# The extracted Dynojet Blowfish key
DYNOJET_KEY = b"R8SJzQ0c2IoKSIVa1YernejU9X5oKQRpPOt2ClU6HiZAk7oEeIHS9orR"


def pad_data(data: bytes) -> bytes:
    """Pad data to 8-byte boundary for Blowfish"""
    padding_len = 8 - (len(data) % 8)
    if padding_len == 8:
        padding_len = 0
    return data + bytes([padding_len] * padding_len)


def unpad_data(data: bytes) -> bytes:
    """Remove padding from decrypted data"""
    if len(data) == 0:
        return data
    padding_len = data[-1]
    if padding_len > 8:
        return data  # No valid padding
    return data[:-padding_len] if padding_len > 0 else data


def encrypt_data(data: bytes, key: bytes = DYNOJET_KEY) -> bytes:
    """Encrypt data using Blowfish ECB mode"""
    cipher = Blowfish.new(key, Blowfish.MODE_ECB)
    padded = pad_data(data)
    return cipher.encrypt(padded)


def decrypt_data(data: bytes, key: bytes = DYNOJET_KEY) -> bytes:
    """Decrypt data using Blowfish ECB mode"""
    cipher = Blowfish.new(key, Blowfish.MODE_ECB)
    decrypted = cipher.decrypt(data)
    return unpad_data(decrypted)


def test_key():
    """Test the encryption key with a round-trip"""
    print("=" * 60)
    print("DYNOJET BLOWFISH KEY TEST")
    print("=" * 60)
    print()
    print(f"Key (ASCII): {DYNOJET_KEY.decode()}")
    print(f"Key Length:  {len(DYNOJET_KEY)} bytes ({len(DYNOJET_KEY) * 8} bits)")
    print(f"Key (Hex):   {DYNOJET_KEY.hex()}")
    print()
    
    # Test round-trip
    test_data = b"TestData12345678"
    print(f"Test Data:   {test_data}")
    
    encrypted = encrypt_data(test_data)
    print(f"Encrypted:   {encrypted.hex()}")
    
    decrypted = decrypt_data(encrypted)
    print(f"Decrypted:   {decrypted}")
    
    if test_data == decrypted:
        print()
        print("✓ Round-trip test PASSED!")
        return True
    else:
        print()
        print("✗ Round-trip test FAILED!")
        return False


def encrypt_file(input_path: str, output_path: str = None):
    """Encrypt a file"""
    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}")
        return False
    
    if output_path is None:
        output_path = input_path + ".encrypted"
    
    print(f"Encrypting: {input_path}")
    print(f"Output:     {output_path}")
    
    with open(input_path, "rb") as f:
        data = f.read()
    
    encrypted = encrypt_data(data)
    
    with open(output_path, "wb") as f:
        # Write original size header (8 bytes)
        f.write(len(data).to_bytes(8, 'little'))
        f.write(encrypted)
    
    print(f"Done! Original: {len(data)} bytes, Encrypted: {len(encrypted)} bytes")
    return True


def decrypt_file(input_path: str, output_path: str = None):
    """Decrypt a file"""
    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}")
        return False
    
    if output_path is None:
        if input_path.endswith(".encrypted"):
            output_path = input_path[:-10]
        else:
            output_path = input_path + ".decrypted"
    
    print(f"Decrypting: {input_path}")
    print(f"Output:     {output_path}")
    
    with open(input_path, "rb") as f:
        # Read original size header
        size_bytes = f.read(8)
        original_size = int.from_bytes(size_bytes, 'little')
        encrypted = f.read()
    
    decrypted = decrypt_data(encrypted)
    
    # Trim to original size
    decrypted = decrypted[:original_size]
    
    with open(output_path, "wb") as f:
        f.write(decrypted)
    
    print(f"Done! Decrypted: {len(decrypted)} bytes")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Dynojet Blowfish Encryption Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python blowfish_tool.py --test
    python blowfish_tool.py --encrypt data.bin
    python blowfish_tool.py --decrypt data.bin.encrypted
    python blowfish_tool.py --encrypt input.bin --output output.enc
        """
    )
    
    parser.add_argument("--test", action="store_true", help="Test the encryption key")
    parser.add_argument("--encrypt", metavar="FILE", help="Encrypt a file")
    parser.add_argument("--decrypt", metavar="FILE", help="Decrypt a file")
    parser.add_argument("--output", "-o", metavar="FILE", help="Output file path")
    parser.add_argument("--show-key", action="store_true", help="Display the key")
    
    args = parser.parse_args()
    
    if args.show_key:
        print(f"Key: {DYNOJET_KEY.decode()}")
        return
    
    if args.test:
        success = test_key()
        sys.exit(0 if success else 1)
    
    if args.encrypt:
        success = encrypt_file(args.encrypt, args.output)
        sys.exit(0 if success else 1)
    
    if args.decrypt:
        success = decrypt_file(args.decrypt, args.output)
        sys.exit(0 if success else 1)
    
    # No arguments - show help
    parser.print_help()


if __name__ == "__main__":
    main()

