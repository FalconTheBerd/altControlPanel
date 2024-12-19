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
        self.root.configure(padx=40, pady=40, bg="#f0f0f0")

        # IP Entry and Network Scan
        ip_frame = tk.Frame(root, bg="#f0f0f0")
        ip_frame.pack(pady=20)
        tk.Label(ip_frame, text="Enter IP Address:", font=("Arial", 14), bg="#f0f0f0").pack(side=tk.LEFT, padx=10)
        self.ip_entry = tk.Entry(ip_frame, width=30, font=("Arial", 14))
        self.ip_entry.pack(side=tk.LEFT, padx=10)
        tk.Button(ip_frame, text="Scan Network", font=("Arial", 14), command=self.scan_network).pack(side=tk.LEFT, padx=10)

        self.device_list = ttk.Combobox(root, font=("Arial", 14), state="readonly", width=50)
        self.device_list.pack(pady=10)
        self.device_list.bind("<<ComboboxSelected>>", self.select_device)

        # Controls Section
        controls_frame = tk.Frame(root, bg="#f0f0f0")
        controls_frame.pack(pady=20)
        tk.Button(controls_frame, text="Request Screenshot", font=("Arial", 14), command=self.request_screenshot).grid(row=0, column=0, padx=20, pady=10)
        tk.Button(controls_frame, text="Browse Files", font=("Arial", 14), command=self.browse_files).grid(row=0, column=1, padx=20, pady=10)
        tk.Button(controls_frame, text="List Tasks", font=("Arial", 14), command=self.list_tasks).grid(row=1, column=0, padx=20, pady=10)

        # Task Controls
        task_controls_frame = tk.Frame(controls_frame, bg="#f0f0f0")
        task_controls_frame.grid(row=2, column=0, columnspan=2, pady=10)
        self.task_entry = tk.Entry(task_controls_frame, width=20, font=("Arial", 14))
        self.task_entry.pack(side=tk.LEFT, padx=10)
        self.kill_all_var = tk.BooleanVar()
        tk.Checkbutton(task_controls_frame, text="Kill All by Name", font=("Arial", 14), variable=self.kill_all_var, bg="#f0f0f0").pack(side=tk.LEFT, padx=10)
        tk.Button(task_controls_frame, text="Kill Task", font=("Arial", 14), command=self.kill_task).pack(side=tk.LEFT, padx=10)

        # Terminal Command Section
        command_frame = tk.Frame(root, bg="#f0f0f0")
        command_frame.pack(pady=20)
        tk.Label(command_frame, text="Run Terminal Command:", font=("Arial", 14), bg="#f0f0f0").pack(anchor="w", pady=10)
        self.command_input = scrolledtext.ScrolledText(command_frame, width=80, height=6, font=("Arial", 14))
        self.command_input.pack(pady=10)
        tk.Button(command_frame, text="Run Command", font=("Arial", 14), command=self.run_command).pack(pady=10)

        # Status and Output Section
        status_frame = tk.Frame(root, bg="#f0f0f0")
        status_frame.pack(pady=20)
        self.status_label = tk.Label(status_frame, text="", font=("Arial", 14), fg="green", bg="#f0f0f0")
        self.status_label.pack(anchor="w", pady=5)
        self.error_label = tk.Label(status_frame, text="", font=("Arial", 14), fg="red", bg="#f0f0f0")
        self.error_label.pack(anchor="w", pady=5)
        output_frame = tk.Frame(root, bg="#f0f0f0")
        output_frame.pack(pady=20)
        self.output_text = scrolledtext.ScrolledText(output_frame, width=80, height=10, font=("Arial", 14))
        self.output_text.pack()

    def get_network_range(self):
        """Dynamically calculate the network range based on the active network interface."""
        iface = netifaces.gateways()['default'][netifaces.AF_INET][1]
        addr_info = netifaces.ifaddresses(iface)[netifaces.AF_INET][0]
        ip = addr_info['addr']
        netmask = addr_info['netmask']
        network = ip_interface(f"{ip}/{netmask}").network
        return str(network)

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
        with ThreadPoolExecutor(max_workers=50) as executor:
            results = executor.map(lambda ip: self._check_port(ip, port), [str(ip) for ip in ip_network(network_range)])
            for result in results:
                if result:
                    open_hosts.append(result)
        return open_hosts

    def _check_port(self, ip, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
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

    def request_screenshot(self):
        ip = self.get_ip()
        if not ip:
            return
        try:
            response = requests.post(f"http://{ip}:5000/screenshot")
            if response.ok:
                self.status_label.config(text="Screenshot request sent successfully!", fg="green")
            else:
                self.error_label.config(text=f"Failed: {response.text}", fg="red")
        except Exception as e:
            self.error_label.config(text=f"Error: {e}", fg="red")

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

    def run_command(self):
        ip = self.get_ip()
        command = self.command_input.get("1.0", tk.END).strip()
        if not ip or not command:
            return
        try:
            response = requests.post(f"http://{ip}:5000/run_command", json={"command": command})
            if response.ok:
                result = response.json()
                if result.get("return_code") == 0:
                    self.status_label.config(text="Command executed successfully!", fg="green")
                    self.output_text.delete(1.0, tk.END)
                    self.output_text.insert(tk.END, result.get("output", "No output."))
                else:
                    self.error_label.config(text=f"Command errors: {result.get('error', 'Unknown error')} (Code: {result.get('return_code')})", fg="red")
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
