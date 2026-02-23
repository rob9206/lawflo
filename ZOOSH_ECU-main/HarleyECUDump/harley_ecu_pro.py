#!/usr/bin/env python3
"""
Harley ECU Tool Pro - Premium GUI

Professional interface for Harley-Davidson ECU tuning.
Features: Modern UI, file manager, hex viewer, auto-backup, and more.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import os
import sys
import time
import re
import json
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

# ============================================================
# Configuration
# ============================================================

CONFIG_FILE = "harley_ecu_config.json"
TUNE_OFFSET = 0x1C000
TUNE_SIZE = 0x4000
WRITE_ADDRESS = 0x00004000

# Try importing CAN
CAN_AVAILABLE = False
try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    pass


# ============================================================
# Theme & Styling
# ============================================================

class Theme:
    # Cyberpunk-inspired dark theme
    BG_DARK = '#0a0a0f'
    BG_MID = '#12121a'
    BG_CARD = '#1a1a28'
    BG_INPUT = '#0f0f18'
    
    ACCENT_PRIMARY = '#00d4ff'    # Cyan
    ACCENT_SECONDARY = '#ff3366'  # Pink/Red
    ACCENT_SUCCESS = '#00ff88'    # Green
    ACCENT_WARNING = '#ffaa00'    # Orange
    ACCENT_ERROR = '#ff4444'      # Red
    
    TEXT_PRIMARY = '#ffffff'
    TEXT_SECONDARY = '#a0a0b0'
    TEXT_DIM = '#606070'
    
    BORDER = '#2a2a3a'
    
    FONT_TITLE = ('Segoe UI', 28, 'bold')
    FONT_HEADING = ('Segoe UI', 14, 'bold')
    FONT_NORMAL = ('Segoe UI', 10)
    FONT_SMALL = ('Segoe UI', 9)
    FONT_MONO = ('Consolas', 10)
    FONT_MONO_SMALL = ('Consolas', 9)


# ============================================================
# Custom Widgets
# ============================================================

class GlowButton(tk.Canvas):
    """Modern button with glow effect"""
    
    def __init__(self, parent, text, command, color=Theme.ACCENT_PRIMARY, 
                 width=180, height=40, **kwargs):
        super().__init__(parent, width=width, height=height, 
                        bg=Theme.BG_CARD, highlightthickness=0, **kwargs)
        
        self.text = text
        self.command = command
        self.color = color
        self.width = width
        self.height = height
        self.hover = False
        
        self.draw()
        
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.bind('<Button-1>', self.on_click)
    
    def draw(self):
        self.delete('all')
        
        # Background with rounded corners
        r = 8
        if self.hover:
            fill = self.color
            text_color = Theme.BG_DARK
        else:
            fill = Theme.BG_INPUT
            text_color = self.color
        
        # Draw rounded rectangle
        self.create_polygon(
            r, 0, self.width-r, 0,
            self.width, 0, self.width, r,
            self.width, self.height-r, self.width, self.height,
            self.width-r, self.height, r, self.height,
            0, self.height, 0, self.height-r,
            0, r, 0, 0,
            smooth=True, fill=fill, outline=self.color, width=2
        )
        
        # Text
        self.create_text(self.width//2, self.height//2, text=self.text,
                        fill=text_color, font=Theme.FONT_NORMAL)
    
    def on_enter(self, e):
        self.hover = True
        self.draw()
        self.config(cursor='hand2')
    
    def on_leave(self, e):
        self.hover = False
        self.draw()
    
    def on_click(self, e):
        if self.command:
            self.command()


class StatusIndicator(tk.Canvas):
    """Animated status indicator"""
    
    def __init__(self, parent, size=12, **kwargs):
        super().__init__(parent, width=size, height=size,
                        bg=Theme.BG_CARD, highlightthickness=0, **kwargs)
        self.size = size
        self.status = 'idle'
        self.pulse_state = 0
        self.draw()
    
    def set_status(self, status):
        self.status = status
        self.draw()
        if status == 'active':
            self.pulse()
    
    def draw(self):
        self.delete('all')
        colors = {
            'idle': Theme.TEXT_DIM,
            'active': Theme.ACCENT_PRIMARY,
            'success': Theme.ACCENT_SUCCESS,
            'error': Theme.ACCENT_ERROR,
            'warning': Theme.ACCENT_WARNING
        }
        color = colors.get(self.status, Theme.TEXT_DIM)
        
        pad = 2
        self.create_oval(pad, pad, self.size-pad, self.size-pad,
                        fill=color, outline='')
    
    def pulse(self):
        if self.status != 'active':
            return
        self.pulse_state = (self.pulse_state + 1) % 10
        alpha = 0.5 + 0.5 * abs(5 - self.pulse_state) / 5
        self.after(100, self.pulse)


class HexViewer(tk.Frame):
    """Hex dump viewer widget"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=Theme.BG_INPUT, **kwargs)
        
        # Header
        header = tk.Frame(self, bg=Theme.BG_CARD)
        header.pack(fill=tk.X)
        
        tk.Label(header, text="Offset", bg=Theme.BG_CARD, fg=Theme.TEXT_DIM,
                font=Theme.FONT_MONO_SMALL, width=10).pack(side=tk.LEFT)
        tk.Label(header, text="Hex Data", bg=Theme.BG_CARD, fg=Theme.TEXT_DIM,
                font=Theme.FONT_MONO_SMALL, width=50).pack(side=tk.LEFT)
        tk.Label(header, text="ASCII", bg=Theme.BG_CARD, fg=Theme.TEXT_DIM,
                font=Theme.FONT_MONO_SMALL).pack(side=tk.LEFT)
        
        # Content
        self.text = tk.Text(self, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY,
                           font=Theme.FONT_MONO_SMALL, height=10,
                           insertbackground=Theme.ACCENT_PRIMARY,
                           selectbackground=Theme.ACCENT_PRIMARY,
                           selectforeground=Theme.BG_DARK,
                           bd=0, padx=5, pady=5)
        self.text.pack(fill=tk.BOTH, expand=True)
        
        # Tags
        self.text.tag_configure('offset', foreground=Theme.ACCENT_PRIMARY)
        self.text.tag_configure('changed', foreground=Theme.ACCENT_SECONDARY)
    
    def load_data(self, data: bytes, highlight_offsets: List[int] = None):
        """Load binary data into viewer"""
        self.text.delete(1.0, tk.END)
        
        if highlight_offsets is None:
            highlight_offsets = []
        
        for i in range(0, min(len(data), 512), 16):  # Show first 512 bytes
            # Offset
            line = f"{i:08X}  "
            self.text.insert(tk.END, line, 'offset')
            
            # Hex
            hex_part = ""
            ascii_part = ""
            for j in range(16):
                if i + j < len(data):
                    b = data[i + j]
                    if (i + j) in highlight_offsets:
                        hex_part += f"{b:02X} "
                    else:
                        hex_part += f"{b:02X} "
                    ascii_part += chr(b) if 32 <= b < 127 else '.'
                else:
                    hex_part += "   "
            
            self.text.insert(tk.END, hex_part + " " + ascii_part + "\n")


class FileCard(tk.Frame):
    """Card displaying a tune/dump file"""
    
    def __init__(self, parent, filepath: str, on_select=None, **kwargs):
        super().__init__(parent, bg=Theme.BG_CARD, padx=10, pady=8, **kwargs)
        
        self.filepath = filepath
        self.on_select = on_select
        self.selected = False
        
        filename = os.path.basename(filepath)
        size = os.path.getsize(filepath)
        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        
        # Icon based on type
        if 'calibration' in filename:
            icon = "📦"
            color = Theme.ACCENT_PRIMARY
        elif 'tune' in filename:
            icon = "🎵"
            color = Theme.ACCENT_SUCCESS
        else:
            icon = "📄"
            color = Theme.TEXT_SECONDARY
        
        # Layout
        top = tk.Frame(self, bg=Theme.BG_CARD)
        top.pack(fill=tk.X)
        
        tk.Label(top, text=icon, bg=Theme.BG_CARD, fg=color,
                font=('Segoe UI', 14)).pack(side=tk.LEFT)
        
        tk.Label(top, text=filename, bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY,
                font=Theme.FONT_NORMAL).pack(side=tk.LEFT, padx=(5, 0))
        
        info = f"{size:,} bytes • {mtime.strftime('%m/%d %H:%M')}"
        tk.Label(self, text=info, bg=Theme.BG_CARD, fg=Theme.TEXT_DIM,
                font=Theme.FONT_SMALL).pack(anchor=tk.W, pady=(2, 0))
        
        # Bindings
        self.bind('<Enter>', lambda e: self.config(bg=Theme.BG_INPUT))
        self.bind('<Leave>', lambda e: self.config(bg=Theme.BG_CARD))
        self.bind('<Button-1>', self._on_click)
        
        for child in self.winfo_children():
            child.bind('<Button-1>', self._on_click)
            for subchild in child.winfo_children():
                subchild.bind('<Button-1>', self._on_click)
    
    def _on_click(self, e):
        if self.on_select:
            self.on_select(self.filepath)


# ============================================================
# ECU Operations
# ============================================================

class ECUOperations:
    """ECU communication handler"""
    
    def __init__(self, log_callback, progress_callback):
        self.log = log_callback
        self.progress = progress_callback
        self.bus = None
        self.auth_payload = None
        self.ecu_info = {}
    
    def connect(self) -> bool:
        try:
            self.bus = can.interface.Bus(
                interface='pcan', channel='PCAN_USBBUS1', bitrate=500000
            )
            self.log("PCAN connected", 'success')
            return True
        except Exception as e:
            self.log(f"Connection failed: {e}", 'error')
            return False
    
    def disconnect(self):
        if self.bus:
            self.bus.shutdown()
            self.bus = None
    
    def load_auth(self, capture_file: str) -> bool:
        try:
            with open(capture_file, 'r', errors='ignore') as f:
                content = f.read()
            
            matches = re.findall(r'0x7E0\s+8\s+([0-9A-Fa-f]{16})', content)
            
            payload = bytearray()
            collecting = False
            
            for match in matches:
                frame = bytes.fromhex(match)
                pci = frame[0]
                
                if (pci & 0xF0) == 0x10 and frame[2] == 0x36:
                    payload = bytearray(frame[4:8])
                    collecting = True
                    continue
                
                if collecting and (pci & 0xF0) == 0x20:
                    payload.extend(frame[1:8])
                    if len(payload) >= 2006:
                        break
            
            if len(payload) >= 2000:
                self.auth_payload = bytes(payload)
                self.log(f"Auth loaded ({len(self.auth_payload)} bytes)", 'success')
                return True
            
            self.log("Failed to extract auth", 'error')
            return False
            
        except Exception as e:
            self.log(f"Auth load error: {e}", 'error')
            return False
    
    def send_frame(self, arb_id: int, data: bytes):
        frame = bytes([len(data)]) + data + bytes(7 - len(data))
        self.bus.send(can.Message(arbitration_id=arb_id, data=frame, is_extended_id=False))
    
    def send_multi(self, arb_id: int, data: bytes) -> bool:
        if len(data) <= 7:
            self.send_frame(arb_id, data)
            return True
        
        length = len(data)
        ff = bytes([0x10 | ((length >> 8) & 0x0F), length & 0xFF]) + data[:6]
        self.bus.send(can.Message(arbitration_id=arb_id, data=ff, is_extended_id=False))
        
        fc = self.bus.recv(timeout=1.0)
        if not fc or (fc.data[0] & 0xF0) != 0x30:
            return False
        
        remaining = data[6:]
        seq = 1
        while remaining:
            chunk = remaining[:7]
            remaining = remaining[7:]
            cf = bytes([0x20 | (seq & 0x0F)]) + chunk + bytes(7 - len(chunk))
            self.bus.send(can.Message(arbitration_id=arb_id, data=cf, is_extended_id=False))
            seq = (seq + 1) & 0x0F
            time.sleep(0.001)
        
        return True
    
    def recv(self, timeout: float = 2.0) -> Optional[bytes]:
        start = time.time()
        data = bytearray()
        expected = 0
        
        while time.time() - start < timeout:
            msg = self.bus.recv(timeout=0.1)
            if not msg or msg.arbitration_id != 0x7E8:
                continue
            
            pci = msg.data[0]
            
            if (pci >> 4) == 0:
                return bytes(msg.data[1:1+(pci & 0x0F)])
            
            if (pci >> 4) == 1:
                expected = ((pci & 0x0F) << 8) | msg.data[1]
                data.extend(msg.data[2:8])
                self.bus.send(can.Message(arbitration_id=0x7E0,
                    data=bytes([0x30, 0, 0, 0, 0, 0, 0, 0]), is_extended_id=False))
            
            if (pci >> 4) == 2:
                data.extend(msg.data[1:8])
                if len(data) >= expected:
                    return bytes(data[:expected])
        
        return bytes(data) if data else None
    
    def authenticate(self) -> bool:
        self.log("Authenticating...")
        
        # TesterPresent
        self.send_frame(0x7E0, bytes([0x3E, 0x00]))
        time.sleep(0.05)
        
        # Extended Session
        self.bus.send(can.Message(arbitration_id=0x7DF,
            data=bytes([0x02, 0x10, 0x03, 0, 0, 0, 0, 0]), is_extended_id=False))
        time.sleep(0.1)
        while self.bus.recv(timeout=0.05): pass
        
        # Security
        self.send_frame(0x7E0, bytes([0x27, 0x01]))
        resp = self.recv()
        if not resp or resp[0] != 0x67:
            self.log("Seed failed", 'error')
            return False
        
        seed = resp[2:4]
        key = bytes([seed[0] ^ 0x9A, seed[1] ^ 0xE8])
        
        self.send_frame(0x7E0, bytes([0x27, 0x02]) + key)
        resp = self.recv()
        if not resp or resp[0] != 0x67:
            self.log("Key rejected", 'error')
            return False
        
        self.log("Security unlocked", 'success')
        
        # Auth download
        req = bytes([0x34, 0x00, 0x44, 0, 0, 0, 0, 0, 0, 0x07, 0xD6])
        self.send_multi(0x7E0, req)
        resp = self.recv()
        if not resp or resp[0] != 0x74:
            self.log("Download request failed", 'error')
            return False
        
        # Auth payload
        msg = bytes([0x36, 0x01]) + self.auth_payload
        self.send_multi(0x7E0, msg)
        resp = self.recv(timeout=3.0)
        if not resp or resp[0] != 0x76:
            self.log("Auth rejected", 'error')
            return False
        
        self.log("Authenticated!", 'success')
        return True
    
    def read_memory(self, addr: int, length: int, fmt: int = 0xB0) -> Optional[bytes]:
        data = bytearray()
        current = addr
        count = 0
        
        while len(data) < length:
            if count > 0 and count % 32 == 0:
                self.log("  Re-authenticating...")
                if not self.authenticate():
                    return None
            
            req = bytes([0x35, fmt, 0x01]) + current.to_bytes(4, 'big')
            self.send_frame(0x7E0, req)
            resp = self.recv(timeout=3.0)
            
            if not resp or resp[0] != 0x75:
                self.log(f"Read failed at 0x{current:X}", 'error')
                return None
            
            data.extend(resp[1:])
            current += len(resp) - 1
            count += 1
            self.progress(len(data) / length * 100)
        
        return bytes(data[:length])
    
    def write_memory(self, addr: int, data: bytes) -> bool:
        self.log(f"Writing {len(data)} bytes...")
        
        req = bytes([0x34, 0x00, 0x44]) + addr.to_bytes(4, 'big') + len(data).to_bytes(4, 'big')
        self.send_multi(0x7E0, req)
        resp = self.recv()
        if not resp or resp[0] != 0x74:
            self.log("Download rejected", 'error')
            return False
        
        offset = 0
        seq = 1
        while offset < len(data):
            chunk = data[offset:offset + 256]
            if len(chunk) < 256:
                chunk += bytes(256 - len(chunk))
            
            msg = bytes([0x36, seq]) + chunk
            self.send_multi(0x7E0, msg)
            resp = self.recv()
            if not resp or resp[0] != 0x76:
                self.log(f"Block {seq} rejected", 'error')
                return False
            
            offset += 256
            seq = (seq % 255) + 1
            self.progress(offset / len(data) * 100)
        
        self.log("Write complete", 'success')
        return True
    
    def reset(self):
        self.send_frame(0x7E0, bytes([0x11, 0x01]))
        time.sleep(0.5)
    
    def clear_dtc(self):
        self.bus.send(can.Message(arbitration_id=0x7DF,
            data=bytes([0x04, 0x14, 0xFF, 0xFF, 0xFF, 0, 0, 0]), is_extended_id=False))


# ============================================================
# Main Application
# ============================================================

class HarleyECUPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Harley ECU Tool Pro")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        self.root.configure(bg=Theme.BG_DARK)
        
        self.queue = queue.Queue()
        self.is_running = False
        self.capture_file = None
        self.selected_file = None
        
        self.build_ui()
        self.process_queue()
        self.scan_files()
        self.load_config()
    
    def build_ui(self):
        """Build the main interface"""
        # Top bar
        topbar = tk.Frame(self.root, bg=Theme.BG_MID, height=60)
        topbar.pack(fill=tk.X)
        topbar.pack_propagate(False)
        
        # Logo/Title
        title_frame = tk.Frame(topbar, bg=Theme.BG_MID)
        title_frame.pack(side=tk.LEFT, padx=20, pady=10)
        
        tk.Label(title_frame, text="🏍️", bg=Theme.BG_MID, 
                font=('Segoe UI', 24)).pack(side=tk.LEFT)
        tk.Label(title_frame, text="Harley ECU Tool", bg=Theme.BG_MID,
                fg=Theme.ACCENT_PRIMARY, font=Theme.FONT_TITLE).pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(title_frame, text="PRO", bg=Theme.BG_MID,
                fg=Theme.ACCENT_SECONDARY, font=('Segoe UI', 12, 'bold')).pack(side=tk.LEFT, padx=(5, 0), pady=(15, 0))
        
        # Status
        status_frame = tk.Frame(topbar, bg=Theme.BG_MID)
        status_frame.pack(side=tk.RIGHT, padx=20)
        
        self.status_indicator = StatusIndicator(status_frame)
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 8))
        
        self.status_label = tk.Label(status_frame, text="Ready",
                                    bg=Theme.BG_MID, fg=Theme.TEXT_SECONDARY,
                                    font=Theme.FONT_NORMAL)
        self.status_label.pack(side=tk.LEFT)
        
        # Main content
        content = tk.Frame(self.root, bg=Theme.BG_DARK)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Left panel - File Manager
        left = tk.Frame(content, bg=Theme.BG_CARD, width=300)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        left.pack_propagate(False)
        
        self.build_file_panel(left)
        
        # Center panel - Actions & Console
        center = tk.Frame(content, bg=Theme.BG_DARK)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        self.build_action_panel(center)
        self.build_console_panel(center)
        
        # Right panel - Info & Hex View
        right = tk.Frame(content, bg=Theme.BG_CARD, width=350)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)
        
        self.build_info_panel(right)
    
    def build_file_panel(self, parent):
        """Build file manager panel"""
        # Header
        header = tk.Frame(parent, bg=Theme.BG_CARD)
        header.pack(fill=tk.X, padx=15, pady=15)
        
        tk.Label(header, text="📁 Files", bg=Theme.BG_CARD,
                fg=Theme.TEXT_PRIMARY, font=Theme.FONT_HEADING).pack(side=tk.LEFT)
        
        tk.Button(header, text="🔄", command=self.scan_files,
                 bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY,
                 activebackground=Theme.BG_MID, bd=0,
                 font=Theme.FONT_NORMAL).pack(side=tk.RIGHT)
        
        # Scrollable file list
        canvas = tk.Canvas(parent, bg=Theme.BG_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        self.file_frame = tk.Frame(canvas, bg=Theme.BG_CARD)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        canvas.create_window((0, 0), window=self.file_frame, anchor=tk.NW)
        self.file_frame.bind('<Configure>', 
                            lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
    
    def build_action_panel(self, parent):
        """Build action buttons panel"""
        panel = tk.Frame(parent, bg=Theme.BG_CARD)
        panel.pack(fill=tk.X, pady=(0, 15))
        
        inner = tk.Frame(panel, bg=Theme.BG_CARD, padx=20, pady=15)
        inner.pack(fill=tk.X)
        
        tk.Label(inner, text="⚡ Actions", bg=Theme.BG_CARD,
                fg=Theme.TEXT_PRIMARY, font=Theme.FONT_HEADING).pack(anchor=tk.W, pady=(0, 15))
        
        btn_frame = tk.Frame(inner, bg=Theme.BG_CARD)
        btn_frame.pack(fill=tk.X)
        
        buttons = [
            ("🔌 Connect", self.check_connection, Theme.ACCENT_PRIMARY),
            ("📡 Capture", self.capture_auth, Theme.ACCENT_PRIMARY),
            ("📥 Dump ECU", self.dump_ecu, Theme.ACCENT_PRIMARY),
            ("📤 Extract", self.extract_tune, Theme.ACCENT_SUCCESS),
            ("⚡ Flash", self.flash_tune, Theme.ACCENT_SECONDARY),
        ]
        
        for text, cmd, color in buttons:
            btn = GlowButton(btn_frame, text, cmd, color, width=130, height=36)
            btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Progress bar
        progress_frame = tk.Frame(inner, bg=Theme.BG_CARD)
        progress_frame.pack(fill=tk.X, pady=(15, 0))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, side=tk.LEFT, expand=True)
        
        self.progress_label = tk.Label(progress_frame, text="0%",
                                      bg=Theme.BG_CARD, fg=Theme.TEXT_DIM,
                                      font=Theme.FONT_SMALL, width=5)
        self.progress_label.pack(side=tk.RIGHT, padx=(10, 0))
    
    def build_console_panel(self, parent):
        """Build console output panel"""
        panel = tk.Frame(parent, bg=Theme.BG_CARD)
        panel.pack(fill=tk.BOTH, expand=True)
        
        inner = tk.Frame(panel, bg=Theme.BG_CARD, padx=15, pady=15)
        inner.pack(fill=tk.BOTH, expand=True)
        
        header = tk.Frame(inner, bg=Theme.BG_CARD)
        header.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(header, text="📋 Console", bg=Theme.BG_CARD,
                fg=Theme.TEXT_PRIMARY, font=Theme.FONT_HEADING).pack(side=tk.LEFT)
        
        tk.Button(header, text="Clear", command=self.clear_console,
                 bg=Theme.BG_INPUT, fg=Theme.TEXT_SECONDARY,
                 activebackground=Theme.BG_MID, bd=0,
                 font=Theme.FONT_SMALL, padx=10).pack(side=tk.RIGHT)
        
        # Console text
        self.console = tk.Text(inner, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY,
                              font=Theme.FONT_MONO, wrap=tk.WORD,
                              insertbackground=Theme.ACCENT_PRIMARY,
                              bd=0, padx=10, pady=10)
        self.console.pack(fill=tk.BOTH, expand=True)
        
        # Tags
        self.console.tag_configure('time', foreground=Theme.TEXT_DIM)
        self.console.tag_configure('success', foreground=Theme.ACCENT_SUCCESS)
        self.console.tag_configure('error', foreground=Theme.ACCENT_ERROR)
        self.console.tag_configure('warning', foreground=Theme.ACCENT_WARNING)
        self.console.tag_configure('info', foreground=Theme.ACCENT_PRIMARY)
    
    def build_info_panel(self, parent):
        """Build info and hex viewer panel"""
        inner = tk.Frame(parent, bg=Theme.BG_CARD, padx=15, pady=15)
        inner.pack(fill=tk.BOTH, expand=True)
        
        # Selected file info
        tk.Label(inner, text="📄 Selected File", bg=Theme.BG_CARD,
                fg=Theme.TEXT_PRIMARY, font=Theme.FONT_HEADING).pack(anchor=tk.W)
        
        self.file_info_label = tk.Label(inner, text="No file selected",
                                       bg=Theme.BG_CARD, fg=Theme.TEXT_DIM,
                                       font=Theme.FONT_NORMAL, wraplength=300)
        self.file_info_label.pack(anchor=tk.W, pady=(5, 15))
        
        # Hex viewer
        tk.Label(inner, text="🔢 Hex Preview", bg=Theme.BG_CARD,
                fg=Theme.TEXT_PRIMARY, font=Theme.FONT_HEADING).pack(anchor=tk.W)
        
        self.hex_viewer = HexViewer(inner)
        self.hex_viewer.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Capture file indicator
        tk.Label(inner, text="🔑 Auth Capture", bg=Theme.BG_CARD,
                fg=Theme.TEXT_PRIMARY, font=Theme.FONT_HEADING).pack(anchor=tk.W, pady=(20, 5))
        
        self.capture_label = tk.Label(inner, text="None",
                                     bg=Theme.BG_CARD, fg=Theme.TEXT_DIM,
                                     font=Theme.FONT_SMALL)
        self.capture_label.pack(anchor=tk.W)
    
    # ==================== Helpers ====================
    
    def log(self, message: str, level: str = 'info'):
        self.queue.put(('log', message, level))
    
    def set_progress(self, value: float):
        self.queue.put(('progress', value))
    
    def set_status(self, text: str, status: str = 'idle'):
        self.status_label.config(text=text)
        self.status_indicator.set_status(status)
    
    def process_queue(self):
        try:
            while True:
                item = self.queue.get_nowait()
                
                if item[0] == 'log':
                    _, msg, level = item
                    ts = datetime.now().strftime("%H:%M:%S")
                    
                    self.console.configure(state='normal')
                    self.console.insert(tk.END, f"[{ts}] ", 'time')
                    
                    icons = {'success': '✓ ', 'error': '✗ ', 'warning': '⚠ '}
                    self.console.insert(tk.END, icons.get(level, ''), level)
                    self.console.insert(tk.END, f"{msg}\n", level if level != 'info' else '')
                    
                    self.console.see(tk.END)
                    self.console.configure(state='disabled')
                
                elif item[0] == 'progress':
                    _, value = item
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
    
    def scan_files(self):
        """Scan for tune/dump files"""
        for widget in self.file_frame.winfo_children():
            widget.destroy()
        
        files = []
        for root, dirs, filenames in os.walk('.'):
            if '.git' in root:
                continue
            for f in filenames:
                if f.endswith('.bin'):
                    path = os.path.join(root, f)
                    files.append(path)
        
        # Also find capture files
        for f in os.listdir('.'):
            if f.endswith('.txt') and 'capture' in f.lower():
                if not self.capture_file:
                    self.capture_file = f
        
        if self.capture_file:
            self.capture_label.config(text=f"✓ {self.capture_file[:25]}...",
                                     fg=Theme.ACCENT_SUCCESS)
        
        # Sort by modification time
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        for path in files[:20]:  # Show max 20
            card = FileCard(self.file_frame, path, on_select=self.select_file)
            card.pack(fill=tk.X, pady=2)
        
        self.log(f"Found {len(files)} files")
    
    def select_file(self, filepath: str):
        """Handle file selection"""
        self.selected_file = filepath
        
        filename = os.path.basename(filepath)
        size = os.path.getsize(filepath)
        
        self.file_info_label.config(text=f"{filename}\n{size:,} bytes")
        
        # Load preview
        with open(filepath, 'rb') as f:
            data = f.read(512)
        self.hex_viewer.load_data(data)
        
        self.log(f"Selected: {filename}")
    
    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.capture_file = config.get('capture_file')
        except:
            pass
    
    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({'capture_file': self.capture_file}, f)
        except:
            pass
    
    def run_async(self, func):
        if self.is_running:
            self.log("Operation in progress!", 'warning')
            return
        
        self.is_running = True
        self.set_status("Working...", 'active')
        thread = threading.Thread(target=self._async_wrapper, args=(func,), daemon=True)
        thread.start()
    
    def _async_wrapper(self, func):
        try:
            func()
        except Exception as e:
            self.log(f"Error: {e}", 'error')
        finally:
            self.is_running = False
            self.set_status("Ready", 'idle')
            self.set_progress(0)
    
    # ==================== Operations ====================
    
    def check_connection(self):
        def do_check():
            self.log("Checking PCAN...")
            
            if not CAN_AVAILABLE:
                self.log("python-can not installed!", 'error')
                return
            
            try:
                bus = can.interface.Bus(interface='pcan', channel='PCAN_USBBUS1', bitrate=500000)
                self.log("PCAN connected!", 'success')
                
                self.log("Listening (3s)...")
                count = 0
                start = time.time()
                while time.time() - start < 3:
                    if bus.recv(timeout=0.5):
                        count += 1
                
                bus.shutdown()
                
                if count:
                    self.log(f"ECU active ({count} msgs)", 'success')
                    self.set_status("Connected", 'success')
                else:
                    self.log("No traffic detected", 'warning')
                    
            except Exception as e:
                self.log(f"Failed: {e}", 'error')
        
        self.run_async(do_check)
    
    def capture_auth(self):
        def do_capture():
            self.log("Starting capture...")
            self.log("Use PowerVision to read ECU", 'info')
            
            if not CAN_AVAILABLE:
                self.log("python-can missing!", 'error')
                return
            
            try:
                bus = can.interface.Bus(interface='pcan', channel='PCAN_USBBUS1', bitrate=500000)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{timestamp}.txt"
                
                messages = []
                start = time.time()
                auth_found = False
                
                while time.time() - start < 90:
                    msg = bus.recv(timeout=0.1)
                    if msg:
                        elapsed = int((time.time() - start) * 1000)
                        messages.append(f"{elapsed:8d}  0x{msg.arbitration_id:03X}  {msg.dlc}  {msg.data.hex()}")
                        
                        if msg.arbitration_id == 0x7E0 and msg.data[0] == 0x17 and len(msg.data) > 2 and msg.data[2] == 0x36:
                            auth_found = True
                            self.log("Auth detected!", 'success')
                    
                    if auth_found and len(messages) > 500:
                        break
                    
                    self.set_progress(min(99, (time.time() - start) / 90 * 100))
                
                bus.shutdown()
                
                with open(filename, 'w') as f:
                    f.write('\n'.join(messages))
                
                self.capture_file = filename
                self.capture_label.config(text=f"✓ {filename}", fg=Theme.ACCENT_SUCCESS)
                self.save_config()
                self.log(f"Saved: {filename}", 'success')
                
            except Exception as e:
                self.log(f"Capture failed: {e}", 'error')
        
        self.run_async(do_capture)
    
    def dump_ecu(self):
        if not self.capture_file:
            self.log("No capture file!", 'error')
            return
        
        def do_dump():
            self.log("Starting dump...")
            
            ops = ECUOperations(self.log, self.set_progress)
            
            if not ops.load_auth(self.capture_file):
                return
            
            if not ops.connect():
                return
            
            try:
                if not ops.authenticate():
                    return
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                outdir = f"ecu_dump_{timestamp}"
                os.makedirs(outdir, exist_ok=True)
                
                self.log("Reading calibration...")
                data = ops.read_memory(0x7D8000, 0x28000, 0xB0)
                
                if data:
                    path = os.path.join(outdir, "calibration_7D8000.bin")
                    with open(path, 'wb') as f:
                        f.write(data)
                    self.log(f"Saved: {path}", 'success')
                    self.scan_files()
                
            finally:
                ops.disconnect()
        
        self.run_async(do_dump)
    
    def extract_tune(self):
        if not self.selected_file:
            # Find most recent calibration
            cals = [f for f in os.listdir('.') if 'calibration' in f and f.endswith('.bin')]
            if not cals:
                for root, dirs, files in os.walk('.'):
                    for f in files:
                        if 'calibration' in f and f.endswith('.bin'):
                            cals.append(os.path.join(root, f))
            
            if not cals:
                self.log("No calibration file found!", 'error')
                return
            
            self.selected_file = sorted(cals, key=os.path.getmtime, reverse=True)[0]
        
        def do_extract():
            self.log(f"Extracting from: {self.selected_file}")
            
            with open(self.selected_file, 'rb') as f:
                data = f.read()
            
            if len(data) < TUNE_OFFSET + TUNE_SIZE:
                self.log("File too small!", 'error')
                return
            
            tune = data[TUNE_OFFSET:TUNE_OFFSET + TUNE_SIZE]
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"tune_{timestamp}.bin"
            
            with open(output, 'wb') as f:
                f.write(tune)
            
            self.log(f"Saved: {output} ({len(tune)} bytes)", 'success')
            self.scan_files()
            self.set_progress(100)
        
        self.run_async(do_extract)
    
    def flash_tune(self):
        if not self.capture_file:
            self.log("No capture file!", 'error')
            return
        
        # File selection
        tune_file = self.selected_file
        if not tune_file or os.path.getsize(tune_file) != TUNE_SIZE:
            tune_file = filedialog.askopenfilename(
                title="Select 16KB Tune File",
                filetypes=[("Tune", "*.bin")]
            )
        
        if not tune_file:
            return
        
        size = os.path.getsize(tune_file)
        if size != TUNE_SIZE:
            if not messagebox.askyesno("Size Mismatch",
                f"File is {size} bytes, expected {TUNE_SIZE}.\nContinue?"):
                return
        
        # Confirm
        if not messagebox.askyesno("⚠️ FLASH ECU",
            f"This will OVERWRITE your ECU!\n\n"
            f"File: {os.path.basename(tune_file)}\n\n"
            f"Continue?", icon='warning'):
            return
        
        def do_flash():
            self.log("="*40, 'warning')
            self.log("FLASHING - DO NOT INTERRUPT!", 'warning')
            self.log("="*40, 'warning')
            
            # Auto-backup
            self.log("Creating backup first...")
            
            ops = ECUOperations(self.log, self.set_progress)
            
            if not ops.load_auth(self.capture_file):
                return
            
            if not ops.connect():
                return
            
            try:
                if not ops.authenticate():
                    return
                
                # Backup current tune
                self.log("Reading current tune for backup...")
                backup_data = ops.read_memory(0x7D8000, 0x28000, 0xB0)
                if backup_data:
                    backup_tune = backup_data[TUNE_OFFSET:TUNE_OFFSET + TUNE_SIZE]
                    backup_file = f"backup_before_flash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bin"
                    with open(backup_file, 'wb') as f:
                        f.write(backup_tune)
                    self.log(f"Backup saved: {backup_file}", 'success')
                
                # Re-auth for write
                if not ops.authenticate():
                    return
                
                # Write
                with open(tune_file, 'rb') as f:
                    tune_data = f.read()
                
                if not ops.write_memory(WRITE_ADDRESS, tune_data):
                    self.log("FLASH FAILED!", 'error')
                    return
                
                ops.reset()
                time.sleep(1)
                ops.clear_dtc()
                
                self.log("="*40, 'success')
                self.log("FLASH COMPLETE!", 'success')
                self.log("="*40, 'success')
                self.log("Cycle ignition: OFF → 10s → ON", 'info')
                
                self.scan_files()
                
            finally:
                ops.disconnect()
        
        self.run_async(do_flash)


def main():
    root = tk.Tk()
    app = HarleyECUPro(root)
    root.mainloop()


if __name__ == "__main__":
    main()

