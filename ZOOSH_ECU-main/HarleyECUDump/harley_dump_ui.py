import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import sys

# Default path - relative to this script
DEFAULT_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "harley_ecu_dump.py")

class HarleyDumpApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Harley ECU Dump Tool UI")
        self.root.geometry("700x550")

        self.script_path = tk.StringVar(value=DEFAULT_SCRIPT_PATH)
        
        self.create_widgets()

    def create_widgets(self):
        # Configuration Frame
        config_frame = ttk.LabelFrame(self.root, text="Configuration", padding="10")
        config_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(config_frame, text="Script Path:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(config_frame, textvariable=self.script_path, width=60).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(config_frame, text="Browse", command=self.browse_script).grid(row=0, column=2, pady=2)

        # Actions Frame
        action_frame = ttk.LabelFrame(self.root, text="Actions", padding="10")
        action_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(action_frame, text="1. Start Capture", command=self.run_capture).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(action_frame, text="2. Dump Memory", command=self.run_dump).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(action_frame, text="List Captures", command=self.run_list).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(action_frame, text="Requires PCAN adapter connected").grid(row=1, column=0, columnspan=3, pady=5)

        # Output Frame
        output_frame = ttk.LabelFrame(self.root, text="Log Output", padding="10")
        output_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.output_text = tk.Text(output_frame, height=15, width=80, state='disabled')
        self.output_text.pack(fill="both", expand=True, side="left")
        
        scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.output_text.config(yscrollcommand=scrollbar.set)

        # Style text tags
        self.output_text.tag_config("error", foreground="red")
        self.output_text.tag_config("info", foreground="blue")

    def browse_script(self):
        filename = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
        if filename:
            self.script_path.set(filename)

    def log(self, message, tag=None):
        self.output_text.config(state='normal')
        self.output_text.insert("end", message + "\n", tag)
        self.output_text.see("end")
        self.output_text.config(state='disabled')

    def run_command(self, args):
        script = self.script_path.get()
        if not os.path.exists(script):
            messagebox.showerror("Error", f"Script file not found at:\n{script}")
            return

        cmd = [sys.executable, script] + args
        self.log(f"Running: {' '.join(cmd)}", "info")
        
        def task():
            try:
                # Set cwd to the script directory so it finds requirements/etc
                cwd = os.path.dirname(script)
                
                # Start process
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    cwd=cwd,
                    bufsize=1,
                    universal_newlines=True
                )

                # Read stdout/stderr line by line
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        self.root.after(0, self.log, output.strip())
                
                # Capture remaining error output
                stderr = process.communicate()[1]
                if stderr:
                     self.root.after(0, self.log, stderr.strip(), "error")

                self.root.after(0, self.log, f"Process finished with exit code {process.returncode}", "info")
                
            except Exception as e:
                self.root.after(0, self.log, f"Exception: {str(e)}", "error")

        threading.Thread(target=task, daemon=True).start()

    def run_capture(self):
        self.run_command(["capture", "-y"])

    def run_dump(self):
        self.run_command(["dump", "-y"])
        
    def run_list(self):
        self.run_command(["list"])

if __name__ == "__main__":
    root = tk.Tk()
    app = HarleyDumpApp(root)
    root.mainloop()

