#!/usr/bin/env python3
"""
Harley ECU Tool - Graphical User Interface

Professional GUI for ECU operations with:
- Real-time console output
- Progress tracking
- File management
- Safety confirmations
"""

import os
import sys
import threading
import queue
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.capture import CaptureManager
from tools.dump import ECUDumper  
from tools.flash import ECUFlasher
from tools.extract import TuneExtractor
from core.memory import MemoryMap


class HarleyECUGUI:
    """Main GUI Application."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Harley ECU Tool")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Message queue for thread-safe logging
        self.log_queue = queue.Queue()
        
        # Current operation
        self.current_operation = None
        self.operation_thread = None
        
        # Setup UI
        self._setup_styles()
        self._create_widgets()
        self._start_log_consumer()
    
    def _setup_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()
        
        # Configure colors
        style.configure('TFrame', background='#1e1e1e')
        style.configure('TLabel', background='#1e1e1e', foreground='#ffffff')
        style.configure('TButton', padding=10)
        style.configure('Header.TLabel', font=('Segoe UI', 24, 'bold'),
                       foreground='#ff6b00')
        style.configure('Status.TLabel', font=('Segoe UI', 10),
                       foreground='#888888')
        
        # Progress bar
        style.configure('Custom.Horizontal.TProgressbar',
                       background='#ff6b00', troughcolor='#333333')
    
    def _create_widgets(self):
        """Create all UI widgets."""
        # Main container
        main = ttk.Frame(self.root, padding=20)
        main.pack(fill='both', expand=True)
        
        # Header
        header = ttk.Frame(main)
        header.pack(fill='x', pady=(0, 20))
        
        ttk.Label(header, text="⚡ HARLEY ECU TOOL",
                 style='Header.TLabel').pack(side='left')
        
        self.status_label = ttk.Label(header, text="Ready",
                                     style='Status.TLabel')
        self.status_label.pack(side='right')
        
        # Button panel
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill='x', pady=10)
        
        buttons = [
            ("📷 Capture", self._on_capture, "Capture PowerVision traffic"),
            ("📥 Dump", self._on_dump, "Dump ECU memory"),
            ("⚡ Flash", self._on_flash, "Flash tune to ECU"),
            ("📦 Extract", self._on_extract, "Extract tune from calibration"),
            ("🔍 Compare", self._on_compare, "Compare two tune files"),
        ]
        
        for text, command, tooltip in buttons:
            btn = ttk.Button(btn_frame, text=text, command=command, width=15)
            btn.pack(side='left', padx=5)
            self._create_tooltip(btn, tooltip)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            main,
            variable=self.progress_var,
            maximum=100,
            style='Custom.Horizontal.TProgressbar'
        )
        self.progress.pack(fill='x', pady=10)
        
        # Console output
        console_frame = ttk.LabelFrame(main, text="Console", padding=10)
        console_frame.pack(fill='both', expand=True, pady=10)
        
        self.console = scrolledtext.ScrolledText(
            console_frame,
            wrap='word',
            font=('Consolas', 10),
            bg='#0d0d0d',
            fg='#ffffff',
            insertbackground='#ffffff'
        )
        self.console.pack(fill='both', expand=True)
        
        # Configure tags for colored output
        self.console.tag_configure('success', foreground='#00ff00')
        self.console.tag_configure('error', foreground='#ff4444')
        self.console.tag_configure('warning', foreground='#ffaa00')
        self.console.tag_configure('info', foreground='#ffffff')
        self.console.tag_configure('header', foreground='#ff6b00',
                                   font=('Consolas', 10, 'bold'))
        
        # File info panel
        info_frame = ttk.LabelFrame(main, text="Files", padding=10)
        info_frame.pack(fill='x', pady=10)
        
        # Capture file
        ttk.Label(info_frame, text="Capture:").grid(row=0, column=0, sticky='w')
        self.capture_var = tk.StringVar(value="(auto-detect)")
        ttk.Entry(info_frame, textvariable=self.capture_var,
                 width=60).grid(row=0, column=1, padx=5)
        ttk.Button(info_frame, text="Browse",
                  command=self._browse_capture).grid(row=0, column=2)
        
        # Tune file
        ttk.Label(info_frame, text="Tune:").grid(row=1, column=0, sticky='w',
                                                 pady=5)
        self.tune_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.tune_var,
                 width=60).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(info_frame, text="Browse",
                  command=self._browse_tune).grid(row=1, column=2, pady=5)
        
        # Status bar
        status_bar = ttk.Frame(main)
        status_bar.pack(fill='x')
        
        self.status_text = ttk.Label(status_bar, text="")
        self.status_text.pack(side='left')
        
        # Initial log
        self._log_header()
    
    def _create_tooltip(self, widget, text):
        """Create tooltip for widget."""
        def show(event):
            x, y = widget.winfo_rootx() + 20, widget.winfo_rooty() + 30
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            label = ttk.Label(self.tooltip, text=text, padding=5)
            label.pack()
        
        def hide(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
        
        widget.bind('<Enter>', show)
        widget.bind('<Leave>', hide)
    
    def _log_header(self):
        """Log application header."""
        self.console.insert('end', "=" * 60 + "\n", 'header')
        self.console.insert('end', "  HARLEY ECU TOOL v1.0\n", 'header')
        self.console.insert('end', "  Capture • Dump • Flash • Extract\n", 'header')
        self.console.insert('end', "=" * 60 + "\n\n", 'header')
    
    def _start_log_consumer(self):
        """Start log message consumer."""
        def consume():
            try:
                while True:
                    msg, level = self.log_queue.get_nowait()
                    self._log_message(msg, level)
            except queue.Empty:
                pass
            self.root.after(100, consume)
        
        self.root.after(100, consume)
    
    def _log_message(self, message: str, level: str = 'info'):
        """Log message to console."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            'success': '✓',
            'error': '✗',
            'warning': '⚠',
            'info': '•'
        }.get(level, '•')
        
        self.console.insert('end', f"[{timestamp}] {prefix} {message}\n", level)
        self.console.see('end')
    
    def log(self, message: str, level: str = 'info'):
        """Thread-safe logging."""
        self.log_queue.put((message, level))
    
    def progress_update(self, value: float):
        """Update progress bar."""
        self.progress_var.set(value)
        self.root.update_idletasks()
    
    def set_status(self, text: str):
        """Update status label."""
        self.status_label.config(text=text)
    
    def _browse_capture(self):
        """Browse for capture file."""
        filename = filedialog.askopenfilename(
            title="Select Capture File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.capture_var.set(filename)
    
    def _browse_tune(self):
        """Browse for tune file."""
        filename = filedialog.askopenfilename(
            title="Select Tune File",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if filename:
            self.tune_var.set(filename)
    
    def _run_operation(self, operation, *args):
        """Run operation in background thread."""
        if self.operation_thread and self.operation_thread.is_alive():
            messagebox.showwarning("Busy", "Operation already in progress")
            return
        
        self.progress_var.set(0)
        self.operation_thread = threading.Thread(
            target=operation,
            args=args,
            daemon=True
        )
        self.operation_thread.start()
    
    def _on_capture(self):
        """Handle capture button."""
        self.set_status("Capturing...")
        self.log("Starting capture...", 'info')
        self.log("Perform PowerVision operation NOW!", 'warning')
        
        def capture():
            manager = CaptureManager()
            manager.set_callbacks(self.log, self.progress_update)
            
            filename = manager.capture(duration=120)
            
            if filename:
                self.capture_var.set(filename)
                self.log(f"Capture saved: {filename}", 'success')
                
                # Analyze
                results = manager.analyze_capture(filename)
                self.log(f"Messages: {results['message_count']}", 'info')
                self.log(f"Auth payload: {'✓' if results['has_auth_payload'] else '✗'}", 
                        'success' if results['has_auth_payload'] else 'warning')
            
            self.set_status("Ready")
        
        self._run_operation(capture)
    
    def _on_dump(self):
        """Handle dump button."""
        self.set_status("Dumping...")
        self.log("Starting ECU dump...", 'info')
        
        capture = self.capture_var.get()
        if capture == "(auto-detect)":
            capture = None
        
        def dump():
            dumper = ECUDumper(output_dir='backups')
            dumper.set_callbacks(self.log, self.progress_update)
            
            try:
                if not dumper.initialize(capture):
                    self.set_status("Failed")
                    return
                
                results = dumper.full_dump()
                
                if results['success']:
                    self.log("Dump complete!", 'success')
                    if results['tune']:
                        self.tune_var.set(results['tune'])
                
            finally:
                dumper.cleanup()
                self.set_status("Ready")
        
        self._run_operation(dump)
    
    def _on_flash(self):
        """Handle flash button."""
        tune_file = self.tune_var.get()
        
        if not tune_file or not os.path.exists(tune_file):
            messagebox.showerror("Error", "Please select a valid tune file")
            return
        
        # Validate
        valid, message = TuneExtractor.validate_tune(tune_file)
        if not valid:
            messagebox.showerror("Error", message)
            return
        
        # Confirm
        result = messagebox.askquestion(
            "⚠ CONFIRM FLASH",
            f"This will write to your ECU!\n\n"
            f"File: {tune_file}\n"
            f"Size: {MemoryMap.TUNE_SIZE} bytes\n\n"
            f"A backup will be created automatically.\n\n"
            f"Do you want to proceed?",
            icon='warning'
        )
        
        if result != 'yes':
            return
        
        # Double confirm
        confirm = messagebox.askquestion(
            "FINAL CONFIRMATION",
            "Are you ABSOLUTELY SURE?\n\n"
            "Type YES to proceed.",
            icon='warning'
        )
        
        if confirm != 'yes':
            return
        
        self.set_status("Flashing...")
        self.log("Starting ECU flash...", 'warning')
        
        capture = self.capture_var.get()
        if capture == "(auto-detect)":
            capture = None
        
        def flash():
            flasher = ECUFlasher(backup_dir='backups')
            flasher.set_callbacks(self.log, self.progress_update)
            
            success = flasher.flash(
                tune_file=tune_file,
                capture_file=capture,
                verify=True,
                double_verify=True
            )
            
            if success:
                self.log("★★★★★ FLASH COMPLETE! ★★★★★", 'success')
                messagebox.showinfo("Success", 
                    "Flash complete!\n\n"
                    "Cycle ignition: OFF → 10 seconds → ON"
                )
            else:
                messagebox.showerror("Failed", "Flash failed. Check console.")
            
            self.set_status("Ready")
        
        self._run_operation(flash)
    
    def _on_extract(self):
        """Handle extract button."""
        cal_file = filedialog.askopenfilename(
            title="Select Calibration File (160KB)",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        
        if not cal_file:
            return
        
        output = cal_file.replace('.bin', '_tune.bin')
        
        self.log(f"Extracting tune from: {cal_file}", 'info')
        
        tune = TuneExtractor.extract_from_calibration(cal_file, output)
        
        if tune:
            self.tune_var.set(output)
            self.log(f"Tune extracted: {output}", 'success')
        else:
            self.log("Extraction failed", 'error')
    
    def _on_compare(self):
        """Handle compare button."""
        tune1 = filedialog.askopenfilename(
            title="Select First Tune File",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if not tune1:
            return
        
        tune2 = filedialog.askopenfilename(
            title="Select Second Tune File",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if not tune2:
            return
        
        report = TuneExtractor.generate_diff_report(tune1, tune2)
        
        # Show in console
        self.console.insert('end', "\n" + report + "\n", 'info')
        self.console.see('end')
    
    def run(self):
        """Start the application."""
        self.root.mainloop()


def main():
    """Main entry point."""
    app = HarleyECUGUI()
    app.run()


if __name__ == '__main__':
    main()

