import socket
import ipaddress
from concurrent.futures import ThreadPoolExecutor
import requests
import webbrowser


class ControlPanelCLI:
    def __init__(self):
        self.ip = None

    @staticmethod
    def scan_ip(ip, port=5000):
        """Check if a specific IP is active on the given port."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)  # 0.5-second timeout
                s.connect((str(ip), port))
                return str(ip), "Active"
        except (socket.timeout, socket.error):
            return str(ip), None

    def scan_network(self, network, port=5000):
        """Scan the network for devices with the specified port open."""
        print(f"Scanning network: {network} on port {port}")
        devices = []
        try:
            with ThreadPoolExecutor(max_workers=50) as executor:
                results = executor.map(
                    lambda ip: self.scan_ip(ip, port),
                    ipaddress.IPv4Network(network, strict=False).hosts(),
                )
                for ip, status in results:
                    if status:
                        devices.append((ip, status))
            if devices:
                print("\nDevices found on the network:")
                for ip, status in devices:
                    print(f"IP: {ip}, Status: {status}")
            else:
                print("No active devices found.")
        except ValueError as e:
            print(f"Invalid network range: {e}")
        except Exception as e:
            print(f"Error during scan: {e}")
        return devices

    def set_ip(self, ip):
        self.ip = ip
        print(f"IP address set to {self.ip}")

    def browse_files(self, ip=None):
        ip = ip or self.ip
        if not ip:
            print("IP address is not set.")
            return
        webbrowser.open(f"http://{ip}:5000/files")
        print(f"Opening file browser for {ip}...")

    def list_tasks(self, ip=None):
        ip = ip or self.ip
        if not ip:
            print("IP address is not set.")
            return
        webbrowser.open(f"http://{ip}:5000/list_tasks")
        print(f"Listing tasks for {ip}...")

    def run_command(self, ip=None, command=""):
        ip = ip or self.ip
        if not ip:
            print("IP address is not set.")
            return
        if not command:
            print("No command provided.")
            return
        try:
            response = requests.post(f"http://{ip}:5000/run_command", json={"command": command})
            if response.ok:
                result = response.json()
                if result.get("return_code") == 0:
                    print("Command executed successfully!")
                    print(result.get("output", "No output."))
                else:
                    print(f"Command errors: {result.get('error', 'Unknown error')} (Code: {result.get('return_code')})")
            else:
                print(f"Error from {ip}: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

    def display_message(self, ip=None, message=""):
        ip = ip or self.ip
        if not ip:
            print("IP address is not set.")
            return
        if not message:
            print("No message provided.")
            return
        try:
            response = requests.post(f"http://{ip}:5000/display_message", json={"message": message})
            if response.ok:
                print(f"Message displayed on {ip} successfully!")
            else:
                print(f"Error from {ip}: {response.text}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    app = ControlPanelCLI()

    while True:
        print("\nControl Panel CLI")
        print("1. Scan Network")
        print("2. Set IP Address")
        print("3. Browse Files")
        print("4. List Tasks")
        print("5. Run Command")
        print("6. Display Message")
        print("7. Exit")
        choice = input("Select an option: ")

        if choice == "1":
            network_range = input("Enter the network range (e.g., 192.168.1.0/24): ")
            port = input("Enter the port to scan (default 5000): ") or "5000"
            devices = app.scan_network(network_range, int(port))
        elif choice == "2":
            ip = input("Enter the IP address: ")
            app.set_ip(ip)
        elif choice == "3":
            app.browse_files()
        elif choice == "4":
            app.list_tasks()
        elif choice == "5":
            command = input("Enter the command to run: ")
            app.run_command(command=command)
        elif choice == "6":
            message = input("Enter the message to display: ")
            app.display_message(message=message)
        elif choice == "7":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")
