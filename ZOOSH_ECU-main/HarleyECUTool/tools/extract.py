"""
Tune Extraction Tool

Extracts and compares tune data from calibration dumps.
"""

import os
import json
import hashlib
from typing import Optional, Tuple

from ..core.memory import MemoryMap


class TuneExtractor:
    """
    Tune Extraction and Comparison Tool.
    
    Features:
    - Extract 16KB tune from 160KB calibration
    - Compare tunes byte-by-byte
    - Generate diff reports
    """
    
    @staticmethod
    def extract_from_calibration(cal_file: str,
                                 output_file: str = None) -> Optional[bytes]:
        """
        Extract tune region from calibration dump.
        
        Args:
            cal_file: Path to calibration file (160KB)
            output_file: Optional output path for extracted tune
            
        Returns:
            Extracted tune data or None
        """
        if not os.path.exists(cal_file):
            print(f"File not found: {cal_file}")
            return None
        
        with open(cal_file, 'rb') as f:
            cal_data = f.read()
        
        # Validate size
        expected_size = MemoryMap.CAL_SIZE
        if len(cal_data) < MemoryMap.TUNE_OFFSET + MemoryMap.TUNE_SIZE:
            print(f"File too small: {len(cal_data)} bytes")
            return None
        
        # Extract tune region
        tune_data = cal_data[
            MemoryMap.TUNE_OFFSET:
            MemoryMap.TUNE_OFFSET + MemoryMap.TUNE_SIZE
        ]
        
        # Save if output specified
        if output_file:
            with open(output_file, 'wb') as f:
                f.write(tune_data)
            
            checksum = hashlib.sha256(tune_data).hexdigest()
            
            # Save metadata
            metadata = {
                'source': cal_file,
                'offset': f"0x{MemoryMap.TUNE_OFFSET:X}",
                'size': len(tune_data),
                'checksum_sha256': checksum
            }
            
            with open(output_file + '.json', 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"Extracted tune saved: {output_file}")
            print(f"Checksum: {checksum[:16]}...")
        
        return tune_data
    
    @staticmethod
    def compare_tunes(tune1_file: str, tune2_file: str) -> Tuple[bool, dict]:
        """
        Compare two tune files byte-by-byte.
        
        Args:
            tune1_file: Path to first tune file
            tune2_file: Path to second tune file
            
        Returns:
            (match, details_dict)
        """
        result = {
            'match': False,
            'tune1_size': 0,
            'tune2_size': 0,
            'differences': 0,
            'diff_offsets': []
        }
        
        if not os.path.exists(tune1_file):
            result['error'] = f"File not found: {tune1_file}"
            return (False, result)
        
        if not os.path.exists(tune2_file):
            result['error'] = f"File not found: {tune2_file}"
            return (False, result)
        
        with open(tune1_file, 'rb') as f:
            tune1 = f.read()
        
        with open(tune2_file, 'rb') as f:
            tune2 = f.read()
        
        result['tune1_size'] = len(tune1)
        result['tune2_size'] = len(tune2)
        result['tune1_checksum'] = hashlib.sha256(tune1).hexdigest()
        result['tune2_checksum'] = hashlib.sha256(tune2).hexdigest()
        
        if len(tune1) != len(tune2):
            result['error'] = "Size mismatch"
            return (False, result)
        
        # Compare bytes
        diffs = []
        for i, (a, b) in enumerate(zip(tune1, tune2)):
            if a != b:
                diffs.append({
                    'offset': i,
                    'tune1': f"0x{a:02X}",
                    'tune2': f"0x{b:02X}"
                })
        
        result['differences'] = len(diffs)
        result['diff_offsets'] = diffs[:100]  # Limit to first 100
        result['match'] = len(diffs) == 0
        
        return (result['match'], result)
    
    @staticmethod
    def generate_diff_report(tune1_file: str, tune2_file: str,
                            output_file: str = None) -> str:
        """
        Generate human-readable diff report.
        
        Args:
            tune1_file: Path to first tune file
            tune2_file: Path to second tune file
            output_file: Optional output path for report
            
        Returns:
            Report text
        """
        match, details = TuneExtractor.compare_tunes(tune1_file, tune2_file)
        
        lines = [
            "=" * 60,
            "TUNE COMPARISON REPORT",
            "=" * 60,
            "",
            f"Tune 1: {tune1_file}",
            f"  Size: {details['tune1_size']} bytes",
            f"  SHA256: {details.get('tune1_checksum', 'N/A')[:16]}...",
            "",
            f"Tune 2: {tune2_file}",
            f"  Size: {details['tune2_size']} bytes",
            f"  SHA256: {details.get('tune2_checksum', 'N/A')[:16]}...",
            "",
            "-" * 60,
            ""
        ]
        
        if match:
            lines.append("RESULT: ✓ TUNES ARE IDENTICAL")
        else:
            lines.append(f"RESULT: ✗ {details['differences']} DIFFERENCES FOUND")
            
            if 'error' in details:
                lines.append(f"Error: {details['error']}")
            
            if details['diff_offsets']:
                lines.append("")
                lines.append("First differences:")
                lines.append("-" * 40)
                
                for diff in details['diff_offsets'][:20]:
                    lines.append(
                        f"  0x{diff['offset']:04X}: "
                        f"{diff['tune1']} -> {diff['tune2']}"
                    )
                
                if details['differences'] > 20:
                    lines.append(f"  ... and {details['differences'] - 20} more")
        
        lines.append("")
        lines.append("=" * 60)
        
        report = '\n'.join(lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            print(f"Report saved: {output_file}")
        
        return report
    
    @staticmethod
    def validate_tune(tune_file: str) -> Tuple[bool, str]:
        """
        Validate tune file format and size.
        
        Args:
            tune_file: Path to tune file
            
        Returns:
            (valid, message)
        """
        if not os.path.exists(tune_file):
            return (False, f"File not found: {tune_file}")
        
        size = os.path.getsize(tune_file)
        
        if size == MemoryMap.TUNE_SIZE:
            return (True, f"Valid tune file ({size} bytes)")
        
        if size == MemoryMap.CAL_SIZE:
            return (False, f"This is a calibration file ({size} bytes). "
                          f"Extract tune first.")
        
        return (False, f"Invalid size: {size} bytes "
                      f"(expected {MemoryMap.TUNE_SIZE})")

