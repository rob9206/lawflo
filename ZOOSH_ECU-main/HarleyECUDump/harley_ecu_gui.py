#!/usr/bin/env python3
"""
Harley ECU Tool - Optimized GUI

A graphical interface for reading and writing Harley-Davidson ECU tunes.
Direct integration with ECU functions for real-time feedback.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import os
import sys
import time
import re
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Callable

# ============================================================
# Configuration
# ============================================================

TUNE_OFFSET = 0x1C000
TUNE_SIZE = 0x4000  # 16KB
WRITE_ADDRESS = 0x00004000

# ============================================================
# CAN/ECU Module Import
# ============================================================

CAN_AVAILABLE = False
try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    pass


# ============================================================
# Logger that writes to GUI
# ============================================================

class GUILogger:
    """Thread-safe logger that writes to GUI console"""
    
    def __init__(self, console_widget, queue):
        self.console = console_widget
        self.queue = queue
        self.progress_callback = None
    
    def log(self, message: str, level: str = 'info'):
        self.queue.put(('log', message, level))
    
    def progress(self, current: int, total: int, message: str = ""):
        if self.progress_callback:
            pct = (current / total * 100) if total > 0 else 0
            self.queue.put(('progress', pct, message))
    
    def set_progress_callback(self, callback):
        self.progress_callback = callback


# ============================================================
# ECU Operations (integrated, not subprocess)
# ============================================================

class ECUOperations:
    """Direct ECU operations with GUI feedback"""
    
    def __init__(self, logger: GUILogger):
        self.logger = logger
        self.bus = None
        self.auth_payload = None
        
    def connect(self) -> bool:
        """Connect to PCAN adapter"""
        try:
            self.bus = can.interface.Bus(
                interface='pcan',
                channel='PCAN_USBBUS1',
                bitrate=500000
            )
            self.logger.log("PCAN connected", 'success')
            return True
        except Exception as e:
            self.logger.log(f"Connection failed: {e}", 'error')
            return False
    
    def disconnect(self):
        if self.bus:
            self.bus.shutdown()
            self.bus = None
    
    def load_auth_payload(self, capture_file: str) -> bool:
        """Load auth payload from capture file"""
        self.logger.log(f"Loading auth from: {capture_file}")
        
        try:
            with open(capture_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            pattern = r'0x7E0\s+8\s+([0-9A-Fa-f]{16})'
            matches = re.findall(pattern, content)
            
            payload = bytearray()
            collecting = False
            
            for match in matches:
                frame = bytes.fromhex(match)
                pci = frame[0]
                
                if (pci & 0xF0) == 0x10:
                    total_len = ((pci & 0x0F) << 8) | frame[1]
                    if frame[2] == 0x36:
                        payload = bytearray(frame[4:8])
                        collecting = True
                        continue
                
                if collecting and (pci & 0xF0) == 0x20:
                    payload.extend(frame[1:8])
                    if len(payload) >= 2006:
                        break
            
            if len(payload) >= 2000:
                self.auth_payload = bytes(payload)
                self.logger.log(f"Loaded {len(self.auth_payload)} byte auth payload", 'success')
                return True
            else:
                self.logger.log(f"Failed to extract payload (got {len(payload)} bytes)", 'error')
                return False
                
        except Exception as e:
            self.logger.log(f"Error loading auth: {e}", 'error')
            return False
    
    def send_single_frame(self, arb_id: int, data: bytes):
        """Send a single-frame ISO-TP message"""
        frame = bytes([len(data)]) + data
        frame = frame + bytes(8 - len(frame))
        msg = can.Message(arbitration_id=arb_id, data=frame, is_extended_id=False)
        self.bus.send(msg)
    
    def send_multiframe(self, arb_id: int, data: bytes) -> bool:
        """Send multi-frame ISO-TP message"""
        if len(data) <= 7:
            self.send_single_frame(arb_id, data)
            return True
        
        # First Frame
        length = len(data)
        ff = bytes([0x10 | ((length >> 8) & 0x0F), length & 0xFF]) + data[:6]
        msg = can.Message(arbitration_id=arb_id, data=ff, is_extended_id=False)
        self.bus.send(msg)
        
        # Wait for Flow Control
        fc = self.bus.recv(timeout=1.0)
        if not fc or fc.arbitration_id != 0x7E8 or (fc.data[0] & 0xF0) != 0x30:
            return False
        
        # Consecutive Frames
        remaining = data[6:]
        seq = 1
        while remaining:
            chunk = remaining[:7]
            remaining = remaining[7:]
            cf = bytes([0x20 | (seq & 0x0F)]) + chunk
            if len(cf) < 8:
                cf = cf + bytes(8 - len(cf))
            msg = can.Message(arbitration_id=arb_id, data=cf, is_extended_id=False)
            self.bus.send(msg)
            seq = (seq + 1) & 0x0F
            time.sleep(0.001)
        
        return True
    
    def recv_response(self, timeout: float = 2.0) -> Optional[bytes]:
        """Receive ISO-TP response"""
        start = time.time()
        response_data = bytearray()
        expected_length = 0
        
        while time.time() - start < timeout:
            msg = self.bus.recv(timeout=0.1)
            if not msg or msg.arbitration_id != 0x7E8:
                continue
            
            pci = msg.data[0]
            frame_type = pci >> 4
            
            if frame_type == 0:  # Single Frame
                length = pci & 0x0F
                return bytes(msg.data[1:1+length])
            
            elif frame_type == 1:  # First Frame
                expected_length = ((pci & 0x0F) << 8) | msg.data[1]
                response_data.extend(msg.data[2:8])
                # Send Flow Control
                fc = can.Message(arbitration_id=0x7E0, 
                               data=bytes([0x30, 0x00, 0x00, 0, 0, 0, 0, 0]),
                               is_extended_id=False)
                self.bus.send(fc)
            
            elif frame_type == 2:  # Consecutive Frame
                response_data.extend(msg.data[1:8])
                if len(response_data) >= expected_length:
                    return bytes(response_data[:expected_length])
        
        return bytes(response_data) if response_data else None
    
    def authenticate(self) -> bool:
        """Perform full authentication sequence"""
        self.logger.log("Authenticating...")
        
        # TesterPresent
        self.send_single_frame(0x7E0, bytes([0x3E, 0x00]))
        time.sleep(0.05)
        
        # Extended Session (broadcast)
        msg = can.Message(arbitration_id=0x7DF, 
                         data=bytes([0x02, 0x10, 0x03, 0, 0, 0, 0, 0]),
                         is_extended_id=False)
        self.bus.send(msg)
        time.sleep(0.1)
        
        # Drain responses
        while self.bus.recv(timeout=0.05):
            pass
        
        # Security Access
        self.send_single_frame(0x7E0, bytes([0x27, 0x01]))
        resp = self.recv_response()
        
        if not resp or resp[0] != 0x67:
            self.logger.log(f"Seed request failed", 'error')
            return False
        
        seed = resp[2:4]
        key = bytes([seed[0] ^ 0x9A, seed[1] ^ 0xE8])
        self.logger.log(f"  Seed: {seed.hex()}, Key: {key.hex()}")
        
        self.send_single_frame(0x7E0, bytes([0x27, 0x02]) + key)
        resp = self.recv_response()
        
        if not resp or resp[0] != 0x67:
            self.logger.log("Key rejected", 'error')
            return False
        
        self.logger.log("Security unlocked", 'success')
        
        # RequestDownload for auth
        req = bytes([0x34, 0x00, 0x44, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x07, 0xD6])
        if not self.send_multiframe(0x7E0, req):
            self.logger.log("RequestDownload failed", 'error')
            return False
        
        resp = self.recv_response()
        if not resp or resp[0] != 0x74:
            self.logger.log("RequestDownload rejected", 'error')
            return False
        
        # TransferData with auth payload
        if not self.auth_payload:
            self.logger.log("No auth payload!", 'error')
            return False
        
        msg = bytes([0x36, 0x01]) + self.auth_payload
        if not self.send_multiframe(0x7E0, msg):
            self.logger.log("TransferData failed", 'error')
            return False
        
        resp = self.recv_response(timeout=3.0)
        if not resp or resp[0] != 0x76:
            self.logger.log("Auth payload rejected", 'error')
            return False
        
        self.logger.log("Authentication complete", 'success')
        return True
    
    def read_memory(self, address: int, length: int, format_byte: int = 0xB0) -> Optional[bytes]:
        """Read memory from ECU"""
        data = bytearray()
        current_addr = address
        read_count = 0
        
        while len(data) < length:
            # Re-auth every 32 reads
            if read_count > 0 and read_count % 32 == 0:
                self.logger.log("  Refreshing auth...")
                if not self.authenticate():
                    return None
            
            # RequestUpload
            req = bytes([0x35, format_byte, 0x01]) + current_addr.to_bytes(4, 'big')
            self.send_single_frame(0x7E0, req)
            
            resp = self.recv_response(timeout=3.0)
            if not resp or resp[0] != 0x75:
                self.logger.log(f"Read failed at 0x{current_addr:X}", 'error')
                return None
            
            data.extend(resp[1:])
            current_addr += len(resp) - 1
            read_count += 1
            
            self.logger.progress(len(data), length)
        
        return bytes(data[:length])
    
    def write_memory(self, address: int, data: bytes) -> bool:
        """Write data to ECU memory"""
        total_len = len(data)
        self.logger.log(f"Writing {total_len} bytes to 0x{address:08X}")
        
        # RequestDownload
        req = bytes([0x34, 0x00, 0x44])
        req += address.to_bytes(4, 'big')
        req += total_len.to_bytes(4, 'big')
        
        if not self.send_multiframe(0x7E0, req):
            return False
        
        resp = self.recv_response()
        if not resp or resp[0] != 0x74:
            self.logger.log(f"RequestDownload rejected", 'error')
            return False
        
        # TransferData in 256-byte blocks
        block_size = 256
        offset = 0
        block_seq = 1
        
        while offset < total_len:
            chunk = data[offset:offset + block_size]
            if len(chunk) < block_size:
                chunk = chunk + bytes(block_size - len(chunk))
            
            msg = bytes([0x36, block_seq]) + chunk
            if not self.send_multiframe(0x7E0, msg):
                self.logger.log(f"TransferData failed at block {block_seq}", 'error')
                return False
            
            resp = self.recv_response()
            if not resp or resp[0] != 0x76:
                self.logger.log(f"Block {block_seq} rejected", 'error')
                return False
            
            offset += block_size
            block_seq = (block_seq % 255) + 1
            self.logger.progress(offset, total_len)
        
        self.logger.log("Write complete", 'success')
        return True
    
    def ecu_reset(self):
        """Reset ECU"""
        self.logger.log("Resetting ECU...")
        self.send_single_frame(0x7E0, bytes([0x11, 0x01]))
        time.sleep(0.5)
    
    def clear_dtc(self):
        """Clear DTCs"""
        self.logger.log("Clearing DTCs...")
        msg = can.Message(arbitration_id=0x7DF,
                         data=bytes([0x04, 0x14, 0xFF, 0xFF, 0xFF, 0, 0, 0]),
                         is_extended_id=False)
        self.bus.send(msg)
        time.sleep(0.5)


# ============================================================
# GUI Application
# ============================================================

class HarleyECUGui:
    def __init__(self, root):
        self.root = root
        self.root.title("Harley ECU Tool")
        self.root.geometry("950x750")
        self.root.minsize(850, 650)
        
        # Theme
        self.colors = {
            'bg': '#0f0f1a',
            'bg_card': '#1a1a2e',
            'accent': '#e94560',
            'accent2': '#4ecca3',
            'text': '#f0f0f0',
            'text_dim': '#808090',
            'success': '#4ecca3',
            'warning': '#ffc107',
            'error': '#ff4757',
            'button': '#16213e',
            'button_hover': '#1f3460',
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # State
        self.queue = queue.Queue()
        self.is_running = False
        self.capture_file = None
        self.ecu_ops = None
        
        self.setup_ui()
        self.process_queue()
        self.find_capture_file()
    
    def setup_ui(self):
        """Build the user interface"""
        # Main container
        main = tk.Frame(self.root, bg=self.colors['bg'])
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Header
        header = tk.Frame(main, bg=self.colors['bg'])
        header.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(header, text="🏍️ Harley ECU Tool",
                bg=self.colors['bg'], fg=self.colors['accent'],
                font=('Segoe UI', 22, 'bold')).pack(side=tk.LEFT)
        
        self.status_label = tk.Label(header, text="Ready",
                                    bg=self.colors['bg'], fg=self.colors['text_dim'],
                                    font=('Segoe UI', 10))
        self.status_label.pack(side=tk.RIGHT, pady=(8, 0))
        
        # Content
        content = tk.Frame(main, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - buttons
        left = tk.Frame(content, bg=self.colors['bg'], width=280)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        left.pack_propagate(False)
        
        self.create_section(left, "Connection", [
            ("🔌 Check PCAN", self.check_connection, "Test adapter connection"),
            ("📡 Capture Auth", self.capture_auth, "Capture from PowerVision"),
        ])
        
        self.create_section(left, "Read", [
            ("📥 Dump ECU", self.dump_ecu, "Read full calibration"),
            ("📤 Extract Tune", self.extract_tune, "Get 16KB tune region"),
        ])
        
        self.create_section(left, "Write", [
            ("⚡ Flash Tune", self.flash_tune, "Write tune to ECU"),
        ], accent=True)
        
        self.create_section(left, "Tools", [
            ("🔄 Compare", self.compare_files, "Compare two files"),
            ("📂 Open Folder", lambda: os.startfile('.'), "Open output folder"),
        ])
        
        # Capture file indicator
        self.capture_label = tk.Label(left, text="No capture file",
                                     bg=self.colors['bg'], fg=self.colors['text_dim'],
                                     font=('Segoe UI', 9))
        self.capture_label.pack(pady=(20, 0))
        
        # Right panel - console
        right = tk.Frame(content, bg=self.colors['bg'])
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        tk.Label(right, text="Console", bg=self.colors['bg'], 
                fg=self.colors['text'], font=('Segoe UI', 11, 'bold')).pack(anchor=tk.W)
        
        # Console
        console_frame = tk.Frame(right, bg='#0d1117', bd=1, relief=tk.SOLID)
        console_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        self.console = scrolledtext.ScrolledText(
            console_frame, bg='#0d1117', fg='#c9d1d9',
            insertbackground='white', font=('Consolas', 10),
            wrap=tk.WORD, bd=0, highlightthickness=0
        )
        self.console.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Tags
        self.console.tag_configure('time', foreground='#6e7681')
        self.console.tag_configure('success', foreground=self.colors['success'])
        self.console.tag_configure('error', foreground=self.colors['error'])
        self.console.tag_configure('warning', foreground=self.colors['warning'])
        self.console.tag_configure('info', foreground=self.colors['accent'])
        
        # Progress
        progress_frame = tk.Frame(right, bg=self.colors['bg'])
        progress_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.progress_label = tk.Label(progress_frame, text="0%",
                                      bg=self.colors['bg'], fg=self.colors['text_dim'],
                                      font=('Segoe UI', 9), width=6)
        self.progress_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Buttons row
        btn_frame = tk.Frame(right, bg=self.colors['bg'])
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="Clear", command=self.clear_console,
                 bg=self.colors['button'], fg=self.colors['text'],
                 activebackground=self.colors['button_hover'],
                 activeforeground=self.colors['text'],
                 bd=0, padx=15, pady=5).pack(side=tk.RIGHT)
    
    def create_section(self, parent, title, buttons, accent=False):
        """Create a button section"""
        frame = tk.Frame(parent, bg=self.colors['bg_card'], padx=12, pady=12)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(frame, text=title, 
                bg=self.colors['bg_card'],
                fg=self.colors['accent'] if accent else self.colors['text'],
                font=('Segoe UI', 11, 'bold')).pack(anchor=tk.W, pady=(0, 8))
        
        for text, command, tooltip in buttons:
            btn_frame = tk.Frame(frame, bg=self.colors['bg_card'])
            btn_frame.pack(fill=tk.X, pady=2)
            
            btn_color = self.colors['accent'] if accent else self.colors['button']
            
            btn = tk.Button(btn_frame, text=text, command=command,
                           bg=btn_color, fg='white',
                           activebackground=self.colors['button_hover'],
                           activeforeground='white',
                           font=('Segoe UI', 10), bd=0,
                           padx=12, pady=6, cursor='hand2',
                           anchor='w', width=18)
            btn.pack(side=tk.LEFT)
            
            tk.Label(btn_frame, text=tooltip,
                    bg=self.colors['bg_card'], fg=self.colors['text_dim'],
                    font=('Segoe UI', 8)).pack(side=tk.LEFT, padx=(8, 0))
    
    def log(self, message: str, level: str = 'info'):
        """Log message to console"""
        self.queue.put(('log', message, level))
    
    def set_progress(self, value: float, text: str = ""):
        """Update progress bar"""
        self.queue.put(('progress', value, text))
    
    def set_status(self, text: str):
        """Update status label"""
        self.status_label.config(text=text)
    
    def process_queue(self):
        """Process queued UI updates"""
        try:
            while True:
                item = self.queue.get_nowait()
                
                if item[0] == 'log':
                    _, message, level = item
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    self.console.configure(state='normal')
                    self.console.insert(tk.END, f"[{timestamp}] ", 'time')
                    
                    prefix = {'success': '✓ ', 'error': '✗ ', 'warning': '⚠ ', 'info': ''}
                    self.console.insert(tk.END, prefix.get(level, ''), level)
                    self.console.insert(tk.END, f"{message}\n", level if level != 'info' else '')
                    
                    self.console.see(tk.END)
                    self.console.configure(state='disabled')
                
                elif item[0] == 'progress':
                    _, value, _ = item
                    self.progress_var.set(value)
                    self.progress_label.config(text=f"{value:.0f}%")
                
        except queue.Empty:
            pass
        
        self.root.after(50, self.process_queue)
    
    def clear_console(self):
        self.console.configure(state='normal')
        self.console.delete(1.0, tk.END)
        self.console.configure(state='disabled')
        self.progress_var.set(0)
        self.progress_label.config(text="0%")
    
    def find_capture_file(self):
        """Find most recent capture file"""
        captures = sorted([f for f in os.listdir('.') 
                          if f.endswith('.txt') and 
                          ('capture' in f.lower())],
                         key=lambda x: os.path.getmtime(x),
                         reverse=True)
        
        if captures:
            self.capture_file = captures[0]
            self.capture_label.config(text=f"✓ {self.capture_file[:30]}...",
                                     fg=self.colors['success'])
            self.log(f"Found: {self.capture_file}", 'success')
        else:
            self.capture_label.config(text="⚠ No capture file",
                                     fg=self.colors['warning'])
    
    def run_async(self, func):
        """Run function in background thread"""
        if self.is_running:
            self.log("Operation already running!", 'warning')
            return
        
        self.is_running = True
        thread = threading.Thread(target=self._async_wrapper, args=(func,), daemon=True)
        thread.start()
    
    def _async_wrapper(self, func):
        try:
            func()
        except Exception as e:
            self.log(f"Error: {e}", 'error')
        finally:
            self.is_running = False
            self.set_status("Ready")
            self.set_progress(0, "")
    
    # ==================== Operations ====================
    
    def check_connection(self):
        """Check PCAN connection"""
        def do_check():
            self.set_status("Checking...")
            self.log("Checking PCAN connection...")
            
            if not CAN_AVAILABLE:
                self.log("python-can not installed!", 'error')
                self.log("Run: pip install python-can", 'info')
                return
            
            try:
                bus = can.interface.Bus(interface='pcan', channel='PCAN_USBBUS1', bitrate=500000)
                self.log("PCAN connected!", 'success')
                
                self.log("Listening for traffic (3s)...")
                count = 0
                start = time.time()
                while time.time() - start < 3:
                    msg = bus.recv(timeout=0.5)
                    if msg:
                        count += 1
                
                bus.shutdown()
                
                if count > 0:
                    self.log(f"Received {count} messages - ECU active!", 'success')
                else:
                    self.log("No traffic. Check wiring/ignition.", 'warning')
                    
            except Exception as e:
                self.log(f"Connection failed: {e}", 'error')
        
        self.run_async(do_check)
    
    def capture_auth(self):
        """Capture authentication"""
        def do_capture():
            self.set_status("Capturing...")
            self.log("Starting capture mode...")
            self.log("Use PowerVision to read from ECU", 'info')
            
            if not CAN_AVAILABLE:
                self.log("python-can not installed!", 'error')
                return
            
            try:
                bus = can.interface.Bus(interface='pcan', channel='PCAN_USBBUS1', bitrate=500000)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{timestamp}.txt"
                
                self.log(f"Capturing to: {filename}")
                self.log("Waiting for PowerVision activity (60s timeout)...")
                
                messages = []
                start = time.time()
                auth_found = False
                
                while time.time() - start < 60:
                    msg = bus.recv(timeout=0.1)
                    if msg:
                        elapsed = int((time.time() - start) * 1000)
                        data_hex = msg.data.hex()
                        messages.append(f"{elapsed:8d}  0x{msg.arbitration_id:03X}  {msg.dlc}  {data_hex}")
                        
                        # Check for auth payload (TransferData FF with 2008 bytes)
                        if msg.arbitration_id == 0x7E0 and msg.data[0] == 0x17 and msg.data[2] == 0x36:
                            auth_found = True
                            self.log("Auth payload detected!", 'success')
                    
                    if auth_found and len(messages) > 500:
                        break
                    
                    self.set_progress(min(99, (time.time() - start) / 60 * 100))
                
                bus.shutdown()
                
                # Save
                with open(filename, 'w') as f:
                    f.write('\n'.join(messages))
                
                self.log(f"Saved {len(messages)} messages", 'success')
                self.capture_file = filename
                self.capture_label.config(text=f"✓ {filename}", fg=self.colors['success'])
                
            except Exception as e:
                self.log(f"Capture failed: {e}", 'error')
        
        self.run_async(do_capture)
    
    def dump_ecu(self):
        """Dump ECU calibration"""
        if not self.capture_file:
            self.log("No capture file! Run Capture Auth first.", 'error')
            return
        
        def do_dump():
            self.set_status("Dumping ECU...")
            self.log("Starting ECU dump...")
            
            logger = GUILogger(self.console, self.queue)
            ops = ECUOperations(logger)
            
            if not ops.load_auth_payload(self.capture_file):
                return
            
            if not ops.connect():
                return
            
            try:
                if not ops.authenticate():
                    return
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = f"ecu_dump_{timestamp}"
                os.makedirs(output_dir, exist_ok=True)
                
                # Dump calibration
                self.log("Reading calibration (160KB)...")
                data = ops.read_memory(0x7D8000, 0x28000, 0xB0)
                
                if data:
                    filename = os.path.join(output_dir, "calibration_7D8000.bin")
                    with open(filename, 'wb') as f:
                        f.write(data)
                    self.log(f"Saved: {filename}", 'success')
                    self.log(f"Dump complete: {len(data)} bytes", 'success')
                else:
                    self.log("Dump failed!", 'error')
                    
            finally:
                ops.disconnect()
        
        self.run_async(do_dump)
    
    def extract_tune(self):
        """Extract tune from dump"""
        # Find calibration files
        cal_files = []
        for root, dirs, files in os.walk('.'):
            for f in files:
                if f.startswith('calibration_') and f.endswith('.bin'):
                    path = os.path.join(root, f)
                    if os.path.getsize(path) >= TUNE_OFFSET + TUNE_SIZE:
                        cal_files.append(path)
        
        if not cal_files:
            self.log("No calibration dumps found!", 'error')
            return
        
        cal_file = sorted(cal_files, key=os.path.getmtime, reverse=True)[0]
        
        def do_extract():
            self.set_status("Extracting...")
            self.log(f"Extracting from: {cal_file}")
            
            with open(cal_file, 'rb') as f:
                data = f.read()
            
            tune = data[TUNE_OFFSET:TUNE_OFFSET + TUNE_SIZE]
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"tune_{timestamp}.bin"
            
            with open(output, 'wb') as f:
                f.write(tune)
            
            self.log(f"Extracted {len(tune)} bytes", 'success')
            self.log(f"Saved: {output}", 'success')
            self.set_progress(100)
        
        self.run_async(do_extract)
    
    def flash_tune(self):
        """Flash tune to ECU"""
        if not self.capture_file:
            self.log("No capture file!", 'error')
            return
        
        tune_file = filedialog.askopenfilename(
            title="Select Tune File (16KB)",
            filetypes=[("Binary", "*.bin"), ("All", "*.*")]
        )
        
        if not tune_file:
            return
        
        size = os.path.getsize(tune_file)
        if size != TUNE_SIZE:
            if not messagebox.askyesno("Warning",
                f"File is {size} bytes, expected {TUNE_SIZE}.\nContinue?"):
                return
        
        if not messagebox.askyesno("⚠️ FLASH ECU",
            f"This will OVERWRITE your ECU tune!\n\n"
            f"File: {os.path.basename(tune_file)}\n\n"
            f"Make sure you have a backup!\n\nContinue?",
            icon='warning'):
            return
        
        def do_flash():
            self.set_status("FLASHING...")
            self.log("=" * 40, 'warning')
            self.log("FLASHING ECU - DO NOT INTERRUPT!", 'warning')
            self.log("=" * 40, 'warning')
            
            with open(tune_file, 'rb') as f:
                tune_data = f.read()
            
            logger = GUILogger(self.console, self.queue)
            ops = ECUOperations(logger)
            
            if not ops.load_auth_payload(self.capture_file):
                return
            
            if not ops.connect():
                return
            
            try:
                if not ops.authenticate():
                    return
                
                if not ops.write_memory(WRITE_ADDRESS, tune_data):
                    self.log("Flash FAILED!", 'error')
                    return
                
                ops.ecu_reset()
                ops.clear_dtc()
                
                self.log("=" * 40, 'success')
                self.log("FLASH COMPLETE!", 'success')
                self.log("=" * 40, 'success')
                self.log("Turn ignition OFF, wait 10s, then ON", 'info')
                
            finally:
                ops.disconnect()
        
        self.run_async(do_flash)
    
    def compare_files(self):
        """Compare two files"""
        file1 = filedialog.askopenfilename(title="Select First File",
                                          filetypes=[("Binary", "*.bin"), ("All", "*.*")])
        if not file1:
            return
        
        file2 = filedialog.askopenfilename(title="Select Second File",
                                          filetypes=[("Binary", "*.bin"), ("All", "*.*")])
        if not file2:
            return
        
        def do_compare():
            self.log(f"Comparing files...")
            self.log(f"  1: {os.path.basename(file1)}")
            self.log(f"  2: {os.path.basename(file2)}")
            
            with open(file1, 'rb') as f:
                data1 = f.read()
            with open(file2, 'rb') as f:
                data2 = f.read()
            
            if len(data1) != len(data2):
                self.log(f"Different sizes: {len(data1)} vs {len(data2)}", 'warning')
                return
            
            diffs = [(i, data1[i], data2[i]) for i in range(len(data1)) if data1[i] != data2[i]]
            
            if not diffs:
                self.log("Files are IDENTICAL!", 'success')
            else:
                self.log(f"{len(diffs)} bytes differ ({len(diffs)*100/len(data1):.1f}%)", 'warning')
                for i, (off, b1, b2) in enumerate(diffs[:10]):
                    self.log(f"  0x{off:04X}: 0x{b1:02X} → 0x{b2:02X}")
                if len(diffs) > 10:
                    self.log(f"  ...and {len(diffs)-10} more")
        
        self.run_async(do_compare)


def main():
    root = tk.Tk()
    app = HarleyECUGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
