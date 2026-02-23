#!/usr/bin/env python3
"""
ECU Tool - Graphical User Interface

A modern GUI for ECU communication and tuning.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import time
import os
from pathlib import Path

# Import ECU modules
try:
    from ecu_tool import ECUTool, FlashRegion, DTCInfo
    from can_interface import CANInterface
    HAS_ECU = True
except ImportError as e:
    print(f"Import error: {e}")
    HAS_ECU = False


class ECUToolGUI:
    """Main GUI Application"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🔧 ECU Communication Tool")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Colors
        self.colors = {
            'bg': '#0d1117',
            'card': '#161b22',
            'border': '#30363d',
            'text': '#c9d1d9',
            'accent': '#58a6ff',
            'success': '#3fb950',
            'warning': '#d29922',
            'danger': '#f85149',
            'muted': '#8b949e'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # ECU Tool instance
        self.ecu: ECUTool = None
        
        # Variables
        self.interface_var = tk.StringVar(value="simulated:test")
        self.connected_var = tk.StringVar(value="⚪ Disconnected")
        self.session_var = tk.StringVar(value="No Session")
        self.security_var = tk.StringVar(value="🔒 Locked")
        
        self.setup_styles()
        self.create_widgets()
        self.refresh_interfaces()
    
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('Card.TFrame', background=self.colors['card'])
        style.configure('TLabel', background=self.colors['bg'], 
                       foreground=self.colors['text'], font=('Segoe UI', 10))
        style.configure('Card.TLabel', background=self.colors['card'])
        style.configure('Title.TLabel', font=('Segoe UI', 14, 'bold'),
                       foreground=self.colors['accent'])
        style.configure('TNotebook', background=self.colors['bg'])
        style.configure('TNotebook.Tab', padding=[12, 8], font=('Segoe UI', 10))
    
    def create_widgets(self):
        """Create all widgets"""
        # Main container
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Top bar - Connection
        self.create_connection_bar(main)
        
        # Notebook for tabs
        notebook = ttk.Notebook(main)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Tabs
        self.create_info_tab(notebook)
        self.create_memory_tab(notebook)
        self.create_flash_tab(notebook)
        self.create_dtc_tab(notebook)
        self.create_terminal_tab(notebook)
    
    def create_connection_bar(self, parent):
        """Create connection controls bar"""
        bar = tk.Frame(parent, bg=self.colors['card'], padx=15, pady=12)
        bar.pack(fill=tk.X)
        
        # Interface selection
        tk.Label(bar, text="Interface:", bg=self.colors['card'], 
                fg=self.colors['text'], font=('Segoe UI', 10)).pack(side=tk.LEFT)
        
        self.interface_combo = ttk.Combobox(bar, textvariable=self.interface_var,
                                            width=30, state='readonly')
        self.interface_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        # Refresh button
        refresh_btn = tk.Button(bar, text="🔄", command=self.refresh_interfaces,
                               bg=self.colors['border'], fg=self.colors['text'],
                               relief=tk.FLAT, padx=8, font=('Segoe UI', 10))
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Connect button
        self.connect_btn = tk.Button(bar, text="Connect", command=self.toggle_connection,
                                     bg=self.colors['accent'], fg='white',
                                     relief=tk.FLAT, padx=20, font=('Segoe UI', 10, 'bold'))
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        # Status indicators
        tk.Label(bar, textvariable=self.connected_var, bg=self.colors['card'],
                fg=self.colors['text'], font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=10)
        
        tk.Label(bar, textvariable=self.session_var, bg=self.colors['card'],
                fg=self.colors['muted'], font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=10)
        
        tk.Label(bar, textvariable=self.security_var, bg=self.colors['card'],
                fg=self.colors['warning'], font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=10)
        
        # Quick actions
        tk.Button(bar, text="Start Session", command=self.start_session,
                 bg=self.colors['border'], fg=self.colors['text'],
                 relief=tk.FLAT, padx=10).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(bar, text="🔓 Unlock", command=self.security_access,
                 bg=self.colors['border'], fg=self.colors['text'],
                 relief=tk.FLAT, padx=10).pack(side=tk.RIGHT, padx=5)
    
    def create_info_tab(self, notebook):
        """Create ECU Info tab"""
        frame = ttk.Frame(notebook, padding=15)
        notebook.add(frame, text="📋 ECU Info")
        
        # Info card
        card = tk.Frame(frame, bg=self.colors['card'], padx=20, pady=15)
        card.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(card, text="ECU Information", bg=self.colors['card'],
                fg=self.colors['accent'], font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W)
        
        info_frame = tk.Frame(card, bg=self.colors['card'])
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.info_labels = {}
        fields = ['VIN', 'Serial', 'Hardware', 'Software', 'Calibration']
        
        for i, field in enumerate(fields):
            row = tk.Frame(info_frame, bg=self.colors['card'])
            row.pack(fill=tk.X, pady=3)
            
            tk.Label(row, text=f"{field}:", width=15, anchor=tk.W,
                    bg=self.colors['card'], fg=self.colors['muted'],
                    font=('Segoe UI', 10)).pack(side=tk.LEFT)
            
            val_label = tk.Label(row, text="---", anchor=tk.W,
                                bg=self.colors['card'], fg=self.colors['text'],
                                font=('Consolas', 10))
            val_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.info_labels[field.lower()] = val_label
        
        # Refresh button
        tk.Button(card, text="Read ECU Info", command=self.read_ecu_info,
                 bg=self.colors['accent'], fg='white', relief=tk.FLAT,
                 padx=15, pady=5, font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(15, 0))
    
    def create_memory_tab(self, notebook):
        """Create Memory Read/Write tab"""
        frame = ttk.Frame(notebook, padding=15)
        notebook.add(frame, text="💾 Memory")
        
        # Read section
        read_card = tk.Frame(frame, bg=self.colors['card'], padx=20, pady=15)
        read_card.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(read_card, text="Read Memory", bg=self.colors['card'],
                fg=self.colors['accent'], font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W)
        
        input_frame = tk.Frame(read_card, bg=self.colors['card'])
        input_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Label(input_frame, text="Address (hex):", bg=self.colors['card'],
                fg=self.colors['text']).pack(side=tk.LEFT)
        self.read_addr = tk.Entry(input_frame, width=12, font=('Consolas', 10))
        self.read_addr.insert(0, "0x10000")
        self.read_addr.pack(side=tk.LEFT, padx=(5, 15))
        
        tk.Label(input_frame, text="Length:", bg=self.colors['card'],
                fg=self.colors['text']).pack(side=tk.LEFT)
        self.read_len = tk.Entry(input_frame, width=10, font=('Consolas', 10))
        self.read_len.insert(0, "256")
        self.read_len.pack(side=tk.LEFT, padx=(5, 15))
        
        tk.Button(input_frame, text="Read", command=self.read_memory,
                 bg=self.colors['success'], fg='white', relief=tk.FLAT,
                 padx=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(input_frame, text="Save to File", command=self.save_memory,
                 bg=self.colors['border'], fg=self.colors['text'],
                 relief=tk.FLAT, padx=10).pack(side=tk.LEFT)
        
        # Hex viewer
        hex_frame = tk.Frame(frame, bg=self.colors['card'], padx=15, pady=15)
        hex_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(hex_frame, text="Memory View", bg=self.colors['card'],
                fg=self.colors['accent'], font=('Segoe UI', 11, 'bold')).pack(anchor=tk.W)
        
        self.hex_text = scrolledtext.ScrolledText(hex_frame, font=('Consolas', 10),
                                                   bg=self.colors['bg'], 
                                                   fg=self.colors['text'],
                                                   insertbackground='white',
                                                   height=15)
        self.hex_text.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Store read data
        self.last_read_data = None
        self.last_read_addr = 0
    
    def create_flash_tab(self, notebook):
        """Create Flash tab"""
        frame = ttk.Frame(notebook, padding=15)
        notebook.add(frame, text="⚡ Flash")
        
        # Flash regions
        regions_card = tk.Frame(frame, bg=self.colors['card'], padx=20, pady=15)
        regions_card.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(regions_card, text="Flash Regions", bg=self.colors['card'],
                fg=self.colors['accent'], font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W)
        
        # Treeview for regions
        columns = ('name', 'address', 'size', 'description')
        self.regions_tree = ttk.Treeview(regions_card, columns=columns, 
                                          show='headings', height=4)
        
        self.regions_tree.heading('name', text='Name')
        self.regions_tree.heading('address', text='Address')
        self.regions_tree.heading('size', text='Size')
        self.regions_tree.heading('description', text='Description')
        
        self.regions_tree.column('name', width=120)
        self.regions_tree.column('address', width=100)
        self.regions_tree.column('size', width=100)
        self.regions_tree.column('description', width=200)
        
        self.regions_tree.pack(fill=tk.X, pady=(10, 0))
        
        # Add default regions
        from ecu_tool import ECUTool
        for region in ECUTool.FLASH_REGIONS:
            self.regions_tree.insert('', tk.END, values=(
                region.name,
                f"0x{region.start_address:08X}",
                f"{region.size // 1024} KB",
                region.description
            ))
        
        # Flash actions
        actions_card = tk.Frame(frame, bg=self.colors['card'], padx=20, pady=15)
        actions_card.pack(fill=tk.X)
        
        tk.Label(actions_card, text="Flash Operations", bg=self.colors['card'],
                fg=self.colors['accent'], font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W)
        
        btn_frame = tk.Frame(actions_card, bg=self.colors['card'])
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(btn_frame, text="📥 Read Calibration", command=self.read_calibration,
                 bg=self.colors['success'], fg='white', relief=tk.FLAT,
                 padx=15, pady=8, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="💾 Dump Full Flash", command=self.dump_flash,
                 bg=self.colors['accent'], fg='white', relief=tk.FLAT,
                 padx=15, pady=8, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="📤 Flash Calibration", command=self.flash_calibration,
                 bg=self.colors['danger'], fg='white', relief=tk.FLAT,
                 padx=15, pady=8, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=5)
        
        # Progress
        self.flash_progress = ttk.Progressbar(actions_card, mode='determinate')
        self.flash_progress.pack(fill=tk.X, pady=(15, 0))
        
        self.flash_status = tk.Label(actions_card, text="Ready",
                                     bg=self.colors['card'], fg=self.colors['muted'])
        self.flash_status.pack(anchor=tk.W, pady=(5, 0))
    
    def create_dtc_tab(self, notebook):
        """Create DTC (Diagnostic Trouble Codes) tab"""
        frame = ttk.Frame(notebook, padding=15)
        notebook.add(frame, text="🔍 Diagnostics")
        
        # DTC card
        dtc_card = tk.Frame(frame, bg=self.colors['card'], padx=20, pady=15)
        dtc_card.pack(fill=tk.BOTH, expand=True)
        
        header = tk.Frame(dtc_card, bg=self.colors['card'])
        header.pack(fill=tk.X)
        
        tk.Label(header, text="Diagnostic Trouble Codes", bg=self.colors['card'],
                fg=self.colors['accent'], font=('Segoe UI', 12, 'bold')).pack(side=tk.LEFT)
        
        tk.Button(header, text="Read DTCs", command=self.read_dtcs,
                 bg=self.colors['accent'], fg='white', relief=tk.FLAT,
                 padx=15).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(header, text="Clear DTCs", command=self.clear_dtcs,
                 bg=self.colors['danger'], fg='white', relief=tk.FLAT,
                 padx=15).pack(side=tk.RIGHT, padx=5)
        
        # DTC list
        columns = ('code', 'status', 'description')
        self.dtc_tree = ttk.Treeview(dtc_card, columns=columns, show='headings', height=10)
        
        self.dtc_tree.heading('code', text='Code')
        self.dtc_tree.heading('status', text='Status')
        self.dtc_tree.heading('description', text='Description')
        
        self.dtc_tree.column('code', width=100)
        self.dtc_tree.column('status', width=100)
        self.dtc_tree.column('description', width=300)
        
        self.dtc_tree.pack(fill=tk.BOTH, expand=True, pady=(15, 0))
        
        # ECU Reset
        reset_frame = tk.Frame(dtc_card, bg=self.colors['card'])
        reset_frame.pack(fill=tk.X, pady=(15, 0))
        
        tk.Button(reset_frame, text="🔄 Soft Reset ECU", command=lambda: self.reset_ecu(False),
                 bg=self.colors['warning'], fg='black', relief=tk.FLAT,
                 padx=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(reset_frame, text="⚠️ Hard Reset ECU", command=lambda: self.reset_ecu(True),
                 bg=self.colors['danger'], fg='white', relief=tk.FLAT,
                 padx=15).pack(side=tk.LEFT, padx=5)
    
    def create_terminal_tab(self, notebook):
        """Create Terminal/Log tab"""
        frame = ttk.Frame(notebook, padding=15)
        notebook.add(frame, text="📟 Terminal")
        
        # Log output
        self.log_text = scrolledtext.ScrolledText(frame, font=('Consolas', 10),
                                                   bg=self.colors['bg'],
                                                   fg=self.colors['text'],
                                                   insertbackground='white')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Command input
        cmd_frame = tk.Frame(frame, bg=self.colors['bg'])
        cmd_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Label(cmd_frame, text=">", bg=self.colors['bg'], 
                fg=self.colors['accent'], font=('Consolas', 12, 'bold')).pack(side=tk.LEFT)
        
        self.cmd_entry = tk.Entry(cmd_frame, font=('Consolas', 10),
                                  bg=self.colors['card'], fg=self.colors['text'],
                                  insertbackground='white')
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.cmd_entry.bind('<Return>', self.send_command)
        
        tk.Button(cmd_frame, text="Send", command=self.send_command,
                 bg=self.colors['accent'], fg='white', relief=tk.FLAT,
                 padx=15).pack(side=tk.RIGHT)
    
    # =========================================================================
    # Actions
    # =========================================================================
    
    def log(self, message: str):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def refresh_interfaces(self):
        """Refresh available CAN interfaces"""
        interfaces = CANInterface.list_interfaces() if HAS_ECU else ["simulated:test"]
        self.interface_combo['values'] = interfaces
        if interfaces:
            self.interface_var.set(interfaces[0])
    
    def toggle_connection(self):
        """Connect or disconnect"""
        if self.ecu and self.ecu.connected:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        """Connect to ECU"""
        interface = self.interface_var.get()
        self.log(f"Connecting to {interface}...")
        
        self.ecu = ECUTool()
        self.ecu.on_log = self.log
        self.ecu.on_progress = self.update_progress
        
        if self.ecu.connect(interface):
            self.connected_var.set("🟢 Connected")
            self.connect_btn.config(text="Disconnect", bg=self.colors['danger'])
            self.log("Connected successfully")
        else:
            self.log("Connection failed")
            self.ecu = None
    
    def disconnect(self):
        """Disconnect from ECU"""
        if self.ecu:
            self.ecu.disconnect()
            self.ecu = None
        
        self.connected_var.set("⚪ Disconnected")
        self.session_var.set("No Session")
        self.security_var.set("🔒 Locked")
        self.connect_btn.config(text="Connect", bg=self.colors['accent'])
        self.log("Disconnected")
    
    def start_session(self):
        """Start diagnostic session"""
        if not self.ecu or not self.ecu.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        def task():
            if self.ecu.start_session():
                self.session_var.set("Session Active")
        
        threading.Thread(target=task, daemon=True).start()
    
    def security_access(self):
        """Perform security access"""
        if not self.ecu or not self.ecu.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        def task():
            if self.ecu.security_access():
                self.security_var.set("🔓 Unlocked")
                self.root.after(0, lambda: self.security_var.set("🔓 Unlocked"))
        
        threading.Thread(target=task, daemon=True).start()
    
    def read_ecu_info(self):
        """Read ECU information"""
        if not self.ecu or not self.ecu.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        def task():
            info = self.ecu.read_ecu_info()
            
            self.root.after(0, lambda: self.info_labels['vin'].config(
                text=info.vin or "N/A"))
            self.root.after(0, lambda: self.info_labels['serial'].config(
                text=info.serial or "N/A"))
            self.root.after(0, lambda: self.info_labels['hardware'].config(
                text=info.hardware_version or "N/A"))
            self.root.after(0, lambda: self.info_labels['software'].config(
                text=info.software_version or "N/A"))
            self.root.after(0, lambda: self.info_labels['calibration'].config(
                text=info.calibration_id or "N/A"))
        
        threading.Thread(target=task, daemon=True).start()
    
    def read_memory(self):
        """Read memory and display"""
        if not self.ecu or not self.ecu.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        try:
            address = int(self.read_addr.get(), 0)
            length = int(self.read_len.get(), 0)
        except ValueError:
            messagebox.showerror("Invalid Input", "Invalid address or length")
            return
        
        def task():
            data = self.ecu.read_memory(address, length)
            if data:
                self.last_read_data = data
                self.last_read_addr = address
                self.root.after(0, lambda: self.display_hex(data, address))
        
        threading.Thread(target=task, daemon=True).start()
    
    def display_hex(self, data: bytes, address: int):
        """Display data in hex view"""
        self.hex_text.delete('1.0', tk.END)
        
        for i in range(0, len(data), 16):
            addr = address + i
            hex_bytes = ' '.join(f'{b:02X}' for b in data[i:i+16])
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
            
            line = f"{addr:08X}:  {hex_bytes:<48}  {ascii_str}\n"
            self.hex_text.insert(tk.END, line)
    
    def save_memory(self):
        """Save last read memory to file"""
        if not self.last_read_data:
            messagebox.showwarning("No Data", "No memory data to save")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".bin",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'wb') as f:
                f.write(self.last_read_data)
            self.log(f"Saved to {filename}")
    
    def read_calibration(self):
        """Read calibration data"""
        if not self.ecu or not self.ecu.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".bin",
            initialfile="calibration.bin",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        def task():
            data = self.ecu.read_calibration()
            if data:
                with open(filename, 'wb') as f:
                    f.write(data)
                self.log(f"Calibration saved to {filename}")
        
        threading.Thread(target=task, daemon=True).start()
    
    def dump_flash(self):
        """Dump full flash"""
        if not self.ecu or not self.ecu.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".bin",
            initialfile="flash_dump.bin",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        
        if filename:
            threading.Thread(target=lambda: self.ecu.dump_flash(filename), 
                           daemon=True).start()
    
    def flash_calibration(self):
        """Flash calibration file"""
        if not self.ecu or not self.ecu.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        result = messagebox.askokcancel(
            "⚠️ Warning",
            "Flashing can BRICK your ECU if something goes wrong!\n\n"
            "Make sure you have:\n"
            "• A backup of your current calibration\n"
            "• Stable power supply\n"
            "• Correct calibration file\n\n"
            "Continue?"
        )
        
        if not result:
            return
        
        filename = filedialog.askopenfilename(
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        with open(filename, 'rb') as f:
            data = f.read()
        
        threading.Thread(target=lambda: self.ecu.flash_calibration(data),
                        daemon=True).start()
    
    def read_dtcs(self):
        """Read diagnostic trouble codes"""
        if not self.ecu or not self.ecu.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        def task():
            dtcs = self.ecu.read_dtc()
            
            self.root.after(0, lambda: self.dtc_tree.delete(*self.dtc_tree.get_children()))
            
            for dtc in dtcs:
                self.root.after(0, lambda d=dtc: self.dtc_tree.insert('', tk.END, values=(
                    d.code,
                    f"0x{d.status:02X}",
                    d.description or "Unknown"
                )))
        
        threading.Thread(target=task, daemon=True).start()
    
    def clear_dtcs(self):
        """Clear diagnostic trouble codes"""
        if not self.ecu or not self.ecu.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        if messagebox.askyesno("Clear DTCs", "Clear all diagnostic trouble codes?"):
            threading.Thread(target=self.ecu.clear_dtc, daemon=True).start()
    
    def reset_ecu(self, hard: bool):
        """Reset ECU"""
        if not self.ecu or not self.ecu.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        msg = "Perform HARD reset?" if hard else "Perform soft reset?"
        if messagebox.askyesno("Reset ECU", msg):
            threading.Thread(target=lambda: self.ecu.reset_ecu(hard), daemon=True).start()
    
    def send_command(self, event=None):
        """Send raw command"""
        cmd = self.cmd_entry.get().strip()
        if not cmd:
            return
        
        self.log(f"> {cmd}")
        self.cmd_entry.delete(0, tk.END)
        
        # Parse and send command
        # TODO: Implement command parser
    
    def update_progress(self, current: int, total: int, message: str):
        """Update progress bar"""
        percent = (current / total * 100) if total > 0 else 0
        self.flash_progress['value'] = percent
        self.flash_status.config(text=f"{message} ({current}/{total})")
        self.root.update_idletasks()


# =============================================================================
# Main
# =============================================================================

def main():
    root = tk.Tk()
    app = ECUToolGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

