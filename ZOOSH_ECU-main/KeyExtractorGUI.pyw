#!/usr/bin/env python3
"""
Dynojet Power Core - Key Extractor GUI
A graphical interface for extracting Blowfish encryption keys
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import subprocess
import threading
import os
import sys
import json
import re
from pathlib import Path

# Try to import Blowfish for encryption/decryption
try:
    from Crypto.Cipher import Blowfish
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class DynojetKeyExtractor:
    def __init__(self, root):
        self.root = root
        self.root.title("Dynojet Key Extractor")
        self.root.geometry("700x600")
        self.root.minsize(600, 500)
        
        # Set dark theme colors
        self.colors = {
            'bg': '#1a1a2e',
            'fg': '#eaeaea',
            'accent': '#e94560',
            'accent2': '#0f3460',
            'success': '#00d26a',
            'warning': '#ffb830',
            'card': '#16213e',
            'border': '#0f3460'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # Variables
        self.frida_process = None
        self.is_extracting = False
        self.captured_key = tk.StringVar(value="No key captured yet")
        self.status_var = tk.StringVar(value="Ready")
        self.power_core_status = tk.StringVar(value="Checking...")
        
        # Find paths
        self.script_dir = Path(__file__).parent
        self.frida_script = self.script_dir / "extract_key.js"
        self.frida_path = self.find_frida()
        
        # Known key (from previous extraction)
        self.known_key = "R8SJzQ0c2IoKSIVa1YernejU9X5oKQRpPOt2ClU6HiZAk7oEeIHS9orR"
        
        self.setup_styles()
        self.create_widgets()
        self.check_power_core_status()
        
    def find_frida(self):
        """Find Frida executable"""
        paths = [
            Path(os.environ.get('APPDATA', '')) / 'Python' / 'Python311' / 'Scripts' / 'frida.exe',
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Python' / 'Python311' / 'Scripts' / 'frida.exe',
            Path('C:/Program Files/Python311/Scripts/frida.exe'),
            Path('C:/Python311/Scripts/frida.exe'),
        ]
        for p in paths:
            if p.exists():
                return p
        return None
        
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure styles
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('Card.TFrame', background=self.colors['card'])
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['fg'], font=('Segoe UI', 10))
        style.configure('Card.TLabel', background=self.colors['card'], foreground=self.colors['fg'])
        style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'), foreground=self.colors['accent'])
        style.configure('Subtitle.TLabel', font=('Segoe UI', 11), foreground=self.colors['fg'])
        style.configure('Status.TLabel', font=('Consolas', 9))
        style.configure('Key.TLabel', font=('Consolas', 11, 'bold'), foreground=self.colors['success'])
        
        # Button styles
        style.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'))
        style.map('Accent.TButton',
            background=[('active', self.colors['accent']), ('!active', self.colors['accent2'])],
            foreground=[('active', 'white'), ('!active', 'white')])
            
    def create_widgets(self):
        """Create all GUI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(header_frame, text="🔐 Dynojet Key Extractor", style='Title.TLabel')
        title_label.pack(side=tk.LEFT)
        
        # Status indicator
        self.status_indicator = tk.Canvas(header_frame, width=12, height=12, bg=self.colors['bg'], highlightthickness=0)
        self.status_indicator.pack(side=tk.RIGHT, padx=5)
        self.status_circle = self.status_indicator.create_oval(2, 2, 10, 10, fill='gray')
        
        status_label = ttk.Label(header_frame, textvariable=self.power_core_status, style='Status.TLabel')
        status_label.pack(side=tk.RIGHT)
        
        # Card 1: Extraction
        extract_card = self.create_card(main_frame, "Key Extraction")
        extract_card.pack(fill=tk.X, pady=(0, 15))
        
        extract_inner = ttk.Frame(extract_card, style='Card.TFrame')
        extract_inner.pack(fill=tk.X, padx=15, pady=10)
        
        # Buttons row
        btn_frame = ttk.Frame(extract_inner, style='Card.TFrame')
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.extract_btn = tk.Button(btn_frame, text="▶ Start Extraction", command=self.toggle_extraction,
                                      bg=self.colors['accent'], fg='white', font=('Segoe UI', 11, 'bold'),
                                      relief=tk.FLAT, padx=20, pady=8, cursor='hand2')
        self.extract_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        refresh_btn = tk.Button(btn_frame, text="🔄 Refresh", command=self.check_power_core_status,
                                bg=self.colors['accent2'], fg='white', font=('Segoe UI', 10),
                                relief=tk.FLAT, padx=15, pady=8, cursor='hand2')
        refresh_btn.pack(side=tk.LEFT)
        
        start_pc_btn = tk.Button(btn_frame, text="🚀 Start Power Core", command=self.start_power_core,
                                 bg=self.colors['accent2'], fg='white', font=('Segoe UI', 10),
                                 relief=tk.FLAT, padx=15, pady=8, cursor='hand2')
        start_pc_btn.pack(side=tk.RIGHT)
        
        # Instructions
        instr_label = ttk.Label(extract_inner, text="After starting extraction, open a tune file in Power Core",
                                style='Card.TLabel')
        instr_label.pack(anchor=tk.W)
        
        # Card 2: Captured Key
        key_card = self.create_card(main_frame, "Captured Key")
        key_card.pack(fill=tk.X, pady=(0, 15))
        
        key_inner = ttk.Frame(key_card, style='Card.TFrame')
        key_inner.pack(fill=tk.X, padx=15, pady=10)
        
        # Key display
        self.key_entry = tk.Entry(key_inner, textvariable=self.captured_key, font=('Consolas', 11),
                                  bg=self.colors['bg'], fg=self.colors['success'], insertbackground='white',
                                  relief=tk.FLAT, state='readonly')
        self.key_entry.pack(fill=tk.X, pady=(0, 10), ipady=8)
        
        key_btn_frame = ttk.Frame(key_inner, style='Card.TFrame')
        key_btn_frame.pack(fill=tk.X)
        
        copy_btn = tk.Button(key_btn_frame, text="📋 Copy Key", command=self.copy_key,
                             bg=self.colors['accent2'], fg='white', font=('Segoe UI', 10),
                             relief=tk.FLAT, padx=15, pady=5, cursor='hand2')
        copy_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        use_known_btn = tk.Button(key_btn_frame, text="Use Known Key", command=self.use_known_key,
                                  bg=self.colors['accent2'], fg='white', font=('Segoe UI', 10),
                                  relief=tk.FLAT, padx=15, pady=5, cursor='hand2')
        use_known_btn.pack(side=tk.LEFT)
        
        # Card 3: Output Log
        log_card = self.create_card(main_frame, "Output Log")
        log_card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        log_inner = ttk.Frame(log_card, style='Card.TFrame')
        log_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_inner, height=10, font=('Consolas', 9),
                                                   bg=self.colors['bg'], fg=self.colors['fg'],
                                                   insertbackground='white', relief=tk.FLAT)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log("Ready. Click 'Start Extraction' to begin.")
        
        # Card 4: Tools (if crypto available)
        if HAS_CRYPTO:
            tools_card = self.create_card(main_frame, "Encryption Tools")
            tools_card.pack(fill=tk.X)
            
            tools_inner = ttk.Frame(tools_card, style='Card.TFrame')
            tools_inner.pack(fill=tk.X, padx=15, pady=10)
            
            encrypt_btn = tk.Button(tools_inner, text="🔒 Encrypt File", command=self.encrypt_file,
                                    bg=self.colors['accent2'], fg='white', font=('Segoe UI', 10),
                                    relief=tk.FLAT, padx=15, pady=5, cursor='hand2')
            encrypt_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            decrypt_btn = tk.Button(tools_inner, text="🔓 Decrypt File", command=self.decrypt_file,
                                    bg=self.colors['accent2'], fg='white', font=('Segoe UI', 10),
                                    relief=tk.FLAT, padx=15, pady=5, cursor='hand2')
            decrypt_btn.pack(side=tk.LEFT)
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(status_frame, textvariable=self.status_var, style='Status.TLabel').pack(side=tk.LEFT)
        
    def create_card(self, parent, title):
        """Create a card-style frame"""
        card = tk.Frame(parent, bg=self.colors['card'], relief=tk.FLAT)
        
        # Title bar
        title_bar = tk.Frame(card, bg=self.colors['border'])
        title_bar.pack(fill=tk.X)
        
        title_label = tk.Label(title_bar, text=title, bg=self.colors['border'], fg=self.colors['fg'],
                               font=('Segoe UI', 10, 'bold'), anchor=tk.W, padx=15, pady=8)
        title_label.pack(fill=tk.X)
        
        return card
        
    def log(self, message):
        """Add message to log"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        
    def check_power_core_status(self):
        """Check if Power Core is running"""
        try:
            result = subprocess.run(
                ['powershell', '-Command', 
                 'Get-Process | Where-Object { $_.ProcessName -match "Power.?Core" } | Select-Object -First 1 Id'],
                capture_output=True, text=True, timeout=5
            )
            
            # Parse PID from output
            output = result.stdout.strip()
            pid_match = re.search(r'\d+', output)
            
            if pid_match:
                self.power_core_pid = int(pid_match.group())
                self.power_core_status.set(f"Power Core Running (PID: {self.power_core_pid})")
                self.status_indicator.itemconfig(self.status_circle, fill=self.colors['success'])
                return True
            else:
                self.power_core_pid = None
                self.power_core_status.set("Power Core Not Running")
                self.status_indicator.itemconfig(self.status_circle, fill=self.colors['warning'])
                return False
        except Exception as e:
            self.power_core_status.set("Error checking status")
            self.status_indicator.itemconfig(self.status_circle, fill='red')
            return False
            
    def start_power_core(self):
        """Start Power Core application"""
        pc_path = Path("C:/Program Files (x86)/Dynojet Power Core/Power Core.exe")
        if pc_path.exists():
            subprocess.Popen([str(pc_path)])
            self.log("Starting Power Core...")
            self.root.after(3000, self.check_power_core_status)
        else:
            messagebox.showerror("Error", f"Power Core not found at:\n{pc_path}")
            
    def toggle_extraction(self):
        """Start or stop extraction"""
        if self.is_extracting:
            self.stop_extraction()
        else:
            self.start_extraction()
            
    def start_extraction(self):
        """Start the Frida extraction process"""
        if not self.frida_path:
            messagebox.showerror("Error", "Frida not found!\nInstall with: pip install frida-tools")
            return
            
        if not self.frida_script.exists():
            messagebox.showerror("Error", f"Hook script not found:\n{self.frida_script}")
            return
            
        if not self.check_power_core_status():
            if messagebox.askyesno("Power Core Not Running", 
                                   "Power Core is not running. Start it now?"):
                self.start_power_core()
                self.root.after(4000, self.start_extraction)
            return
            
        self.is_extracting = True
        self.extract_btn.config(text="⏹ Stop Extraction", bg=self.colors['warning'])
        self.status_var.set("Extracting... Trigger encryption in Power Core")
        self.log(f"\n{'='*50}")
        self.log("Starting extraction...")
        self.log(f"Attaching to PID: {self.power_core_pid}")
        
        # Start Frida in background thread
        thread = threading.Thread(target=self.run_frida, daemon=True)
        thread.start()
        
    def run_frida(self):
        """Run Frida process"""
        try:
            cmd = [str(self.frida_path), '-p', str(self.power_core_pid), '-l', str(self.frida_script)]
            
            self.frida_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Read output line by line
            for line in self.frida_process.stdout:
                line = line.strip()
                if line:
                    self.root.after(0, self.process_frida_output, line)
                    
        except Exception as e:
            self.root.after(0, self.log, f"Error: {e}")
        finally:
            self.root.after(0, self.extraction_stopped)
            
    def process_frida_output(self, line):
        """Process a line of Frida output"""
        self.log(line)
        
        # Look for captured key
        if "KEY (ASCII):" in line or "KEY BYTES:" in line:
            self.status_var.set("Key detected! Capturing...")
            
        # Try to extract the key from the output
        # Look for the pattern of the key (56 alphanumeric chars)
        key_match = re.search(r'[A-Za-z0-9]{50,60}', line)
        if key_match and len(key_match.group()) >= 50:
            potential_key = key_match.group()
            if potential_key != self.captured_key.get():
                self.captured_key.set(potential_key)
                self.status_var.set("✓ Key captured!")
                self.log(f"\n🔐 KEY CAPTURED: {potential_key[:40]}...")
                
    def stop_extraction(self):
        """Stop the extraction process"""
        if self.frida_process:
            self.frida_process.terminate()
            self.frida_process = None
        self.extraction_stopped()
        
    def extraction_stopped(self):
        """Called when extraction stops"""
        self.is_extracting = False
        self.extract_btn.config(text="▶ Start Extraction", bg=self.colors['accent'])
        self.status_var.set("Extraction stopped")
        self.log("Extraction stopped.")
        
    def copy_key(self):
        """Copy key to clipboard"""
        key = self.captured_key.get()
        if key and key != "No key captured yet":
            self.root.clipboard_clear()
            self.root.clipboard_append(key)
            self.status_var.set("Key copied to clipboard!")
            self.log("Key copied to clipboard")
        else:
            messagebox.showinfo("No Key", "No key to copy")
            
    def use_known_key(self):
        """Use the previously extracted known key"""
        self.captured_key.set(self.known_key)
        self.status_var.set("Using known key")
        self.log(f"Loaded known key: {self.known_key[:40]}...")
        
    def get_current_key(self):
        """Get the current key as bytes"""
        key = self.captured_key.get()
        if key and key != "No key captured yet":
            return key.encode()
        return None
        
    def encrypt_file(self):
        """Encrypt a file using the captured key"""
        key = self.get_current_key()
        if not key:
            messagebox.showwarning("No Key", "Please capture or load a key first")
            return
            
        filepath = filedialog.askopenfilename(title="Select file to encrypt")
        if not filepath:
            return
            
        try:
            cipher = Blowfish.new(key, Blowfish.MODE_ECB)
            
            with open(filepath, 'rb') as f:
                data = f.read()
                
            # Pad data
            padding_len = 8 - (len(data) % 8)
            padded = data + bytes([padding_len] * padding_len)
            
            encrypted = cipher.encrypt(padded)
            
            output_path = filepath + ".encrypted"
            with open(output_path, 'wb') as f:
                f.write(len(data).to_bytes(8, 'little'))
                f.write(encrypted)
                
            self.log(f"Encrypted: {filepath}")
            self.log(f"Output: {output_path}")
            messagebox.showinfo("Success", f"File encrypted!\n{output_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Encryption failed:\n{e}")
            
    def decrypt_file(self):
        """Decrypt a file using the captured key"""
        key = self.get_current_key()
        if not key:
            messagebox.showwarning("No Key", "Please capture or load a key first")
            return
            
        filepath = filedialog.askopenfilename(title="Select file to decrypt")
        if not filepath:
            return
            
        try:
            cipher = Blowfish.new(key, Blowfish.MODE_ECB)
            
            with open(filepath, 'rb') as f:
                original_size = int.from_bytes(f.read(8), 'little')
                encrypted = f.read()
                
            decrypted = cipher.decrypt(encrypted)[:original_size]
            
            if filepath.endswith('.encrypted'):
                output_path = filepath[:-10]
            else:
                output_path = filepath + ".decrypted"
                
            with open(output_path, 'wb') as f:
                f.write(decrypted)
                
            self.log(f"Decrypted: {filepath}")
            self.log(f"Output: {output_path}")
            messagebox.showinfo("Success", f"File decrypted!\n{output_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Decryption failed:\n{e}")


def main():
    root = tk.Tk()
    
    # Set window icon (if available)
    try:
        root.iconbitmap(default='')
    except:
        pass
        
    app = DynojetKeyExtractor(root)
    root.mainloop()


if __name__ == "__main__":
    main()

