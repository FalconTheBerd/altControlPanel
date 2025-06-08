import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import requests
import webbrowser
from concurrent.futures import ThreadPoolExecutor
import socket
import netifaces
from ipaddress import ip_network, ip_interface
import threading

class ControlPanelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Control Panel")
        self.root.state("zoomed")
        self.root.configure(bg="#f0f0f0")

        # Top Frame for IP Controls
        top_frame = tk.Frame(root, bg="#f0f0f0")
        top_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(top_frame, text="Enter IP Address:", font=("Arial", 12), bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.ip_entry = tk.Entry(top_frame, width=25, font=("Arial", 12))
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Scan Network", font=("Arial", 12), command=self.scan_network).pack(side=tk.LEFT, padx=5)

        self.device_list = ttk.Combobox(top_frame, font=("Arial", 12), state="readonly", width=30)
        self.device_list.pack(side=tk.LEFT, padx=10)
        self.device_list.bind("<<ComboboxSelected>>", self.select_device)

        # Split into left and right panels
        main_frame = tk.Frame(root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        left_panel = tk.Frame(main_frame, bg="#f0f0f0")
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        right_panel = tk.Frame(main_frame, bg="#f0f0f0")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Panel - Buttons and Inputs
        tk.Button(left_panel, text="View Screen", font=("Arial", 12), width=25, command=self.view_screen).pack(pady=5)
        tk.Button(left_panel, text="Browse Files", font=("Arial", 12), width=25, command=self.browse_files).pack(pady=5)
        tk.Button(left_panel, text="List Tasks", font=("Arial", 12), width=25, command=self.list_tasks).pack(pady=5)

        # Task kill section
        self.task_entry = tk.Entry(left_panel, font=("Arial", 12), width=22)
        self.task_entry.pack(pady=5)
        self.kill_all_var = tk.BooleanVar()
        tk.Checkbutton(left_panel, text="Kill All by Name", font=("Arial", 12), variable=self.kill_all_var, bg="#f0f0f0").pack(pady=2)
        tk.Button(left_panel, text="Kill Task", font=("Arial", 12), width=25, command=self.kill_task).pack(pady=5)

        # Message display section
        tk.Label(left_panel, text="Display Message on Alt:", font=("Arial", 12), bg="#f0f0f0").pack(anchor="w", pady=(15, 0))
        self.message_input = scrolledtext.ScrolledText(left_panel, width=30, height=4, font=("Arial", 12))
        self.message_input.pack(pady=5)
        tk.Button(left_panel, text="Send Message", font=("Arial", 12), width=25, command=self.display_message).pack(pady=5)

        # Keystroke section
        tk.Label(left_panel, text="Send Keystrokes:", font=("Arial", 12), bg="#f0f0f0").pack(anchor="w", pady=(15, 0))
        self.keystroke_entry = tk.Entry(left_panel, font=("Arial", 12), width=22)
        self.keystroke_entry.pack(pady=5)
        tk.Button(left_panel, text="Send Keystrokes", font=("Arial", 12), width=25, command=self.send_keystrokes).pack(pady=5)

        # Right Panel - Command & Output
        tk.Label(right_panel, text="Run Terminal Command:", font=("Arial", 12), bg="#f0f0f0").pack(anchor="w", pady=(0, 5))
        self.command_input = scrolledtext.ScrolledText(right_panel, width=80, height=6, font=("Arial", 12))
        self.command_input.pack(pady=5)
        tk.Button(right_panel, text="Run Command", font=("Arial", 12), command=self.run_command).pack(pady=5)

        self.output_text = scrolledtext.ScrolledText(right_panel, width=80, height=12, font=("Arial", 12))
        self.output_text.pack(pady=(5, 0))

        # Command Library - Quick command buttons that run immediately
        command_frame = tk.Frame(right_panel, bg="#f0f0f0")
        command_frame.pack(pady=10)

        commands = [
            ("tasklist", "tasklist"),
            ("ipconfig /all", "ipconfig /all"),
            ("shutdown", "shutdown /r /t 0"),
        ]
        for label, cmd in commands:
            tk.Button(
                command_frame,
                text=label,
                font=("Arial", 12),
                command=lambda c=cmd: self.run_command(c)
            ).pack(side=tk.LEFT, padx=5)

        # Status Bar
        status_bar = tk.Frame(root, bg="#f0f0f0")
        status_bar.pack(fill=tk.X, padx=20, pady=10)
        self.status_label = tk.Label(status_bar, text="", font=("Arial", 12), fg="green", bg="#f0f0f0")
        self.status_label.pack(anchor="w")
        self.error_label = tk.Label(status_bar, text="", font=("Arial", 12), fg="red", bg="#f0f0f0")
        self.error_label.pack(anchor="w")

    def get_network_range(self):
        iface = netifaces.gateways()['default'][netifaces.AF_INET][1]
        addr_info = netifaces.ifaddresses(iface)[netifaces.AF_INET][0]
        ip = addr_info['addr']
        netmask = addr_info['netmask']
        network = ip_interface(f"{ip}/{netmask}").network
        return str(network)

    def view_screen(self):
        ip = self.get_ip()
        if ip:
            webbrowser.open(f"http://{ip}:5000/interactive_view")

    def scan_network(self):
        self.status_label.config(text="Scanning network...", fg="blue")
        self.device_list["values"] = []
        scan_thread = threading.Thread(target=self._scan_network_thread)
        scan_thread.daemon = True
        scan_thread.start()

    def _scan_network_thread(self):
        try:
            network_range = self.get_network_range()
            port = 5000
            devices = self._scan_network_for_port(network_range, port)
            if devices:
                device_list = [f"{ip} ({hostname})" for ip, hostname in devices]
                self.root.after(0, self._update_device_list, device_list, "Scan complete. Select a device from the list.", "green")
            else:
                self.root.after(0, self._update_device_list, [], "No devices with port 5000 open were found.", "red")
        except Exception as e:
            self.root.after(0, self.status_label.config, {"text": f"Error during scan: {e}", "fg": "red"})

    def _scan_network_for_port(self, network_range, port):
        open_hosts = []
        # Use more worker threads to check multiple hosts concurrently
        # for quicker scanning of the local network
        with ThreadPoolExecutor(max_workers=100) as executor:
            results = executor.map(lambda ip: self._check_port(ip, port), [str(ip) for ip in ip_network(network_range)])
            for result in results:
                if result:
                    open_hosts.append(result)
        return open_hosts

    def _check_port(self, ip, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # Reduce timeout per host so unreachable machines do not
                # delay the overall scanning process
                sock.settimeout(0.5)
                result = sock.connect_ex((ip, port))
                if result == 0:
                    try:
                        hostname = socket.gethostbyaddr(ip)[0]
                    except socket.herror:
                        hostname = "Unknown Host"
                    return ip, hostname
        except Exception:
            pass
        return None

    def _update_device_list(self, device_list, status_message, status_color):
        self.device_list["values"] = device_list
        self.status_label.config(text=status_message, fg=status_color)

    def select_device(self, event):
        selected = self.device_list.get()
        if selected:
            ip = selected.split(" ")[0]
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, ip)

    def browse_files(self):
        ip = self.get_ip()
        if not ip:
            return
        webbrowser.open(f"http://{ip}:5000/files")

    def list_tasks(self):
        ip = self.get_ip()
        if not ip:
            return
        webbrowser.open(f"http://{ip}:5000/list_tasks")

    def kill_task(self):
        ip = self.get_ip()
        task = self.task_entry.get().strip()
        if not ip or not task:
            return
        try:
            data = {"task": task}
            if self.kill_all_var.get():
                data["kill_all"] = True
            response = requests.post(f"http://{ip}:5000/kill_task", json=data)
            if response.ok:
                self.status_label.config(text=response.json().get("message", "Task killed successfully!"), fg="green")
            else:
                self.error_label.config(text=f"Failed: {response.text}", fg="red")
        except Exception as e:
            self.error_label.config(text=f"Error: {e}", fg="red")

    def run_command(self, command=None):
        ip = self.get_ip()
        if command is None:
            command = self.command_input.get("1.0", tk.END).strip()
        else:
            command = command.strip()
        if not ip or not command:
            return
        try:
            response = requests.post(f"http://{ip}:5000/run_command", json={"command": command})
            if response.ok:
                result = response.json()
                output = result.get("output", "")
                error = result.get("error", "")
                code = result.get("return_code")

                self.output_text.delete(1.0, tk.END)
                if output:
                    self.output_text.insert(tk.END, f"[STDOUT]\n{output}\n")
                if error:
                    self.output_text.insert(tk.END, f"[STDERR]\n{error}\n")

                if code == 0:
                    self.status_label.config(text="Command executed successfully!", fg="green")
                else:
                    self.error_label.config(text=f"Command error (code {code})", fg="red")
            else:
                self.error_label.config(text=f"Failed: {response.text}", fg="red")
        except Exception as e:
            self.error_label.config(text=f"Error: {e}", fg="red")

    def display_message(self):
        ip = self.get_ip()
        message = self.message_input.get("1.0", tk.END).strip()
        if not ip or not message:
            return
        try:
            response = requests.post(f"http://{ip}:5000/display_message", json={"message": message})
            if response.ok:
                self.status_label.config(text="Message sent to Alt successfully!", fg="green")
            else:
                self.error_label.config(text=f"Failed: {response.text}", fg="red")
        except Exception as e:
            self.error_label.config(text=f"Error: {e}", fg="red")

    def send_keystrokes(self):
        ip = self.get_ip()
        keys = self.keystroke_entry.get().strip()
        if not ip or not keys:
            return
        try:
            response = requests.post(f"http://{ip}:5000/keystroke", json={"keys": keys})
            if response.ok:
                self.status_label.config(text="Keystrokes sent successfully!", fg="green")
            else:
                self.error_label.config(text=f"Failed: {response.text}", fg="red")
        except Exception as e:
            self.error_label.config(text=f"Error: {e}", fg="red")

    def get_ip(self):
        ip = self.ip_entry.get().strip()
        if not ip:
            messagebox.showerror("Error", "Please enter Alt's IP address.")
        return ip

if __name__ == "__main__":
    root = tk.Tk()
    app = ControlPanelApp(root)
    root.mainloop()
