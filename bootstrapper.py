import os
import requests
import subprocess
import time
import platform
import sys
import socket
import psutil

if platform.system() != "Windows":
    sys.stderr.write("bootstrapper.py can only run on Windows.\n")
    sys.exit(0)

# === CONFIGURATION ===
DOWNLOAD_URL = "https://github.com/FalconTheBerd/altControlPanel/releases/download/v1.x/alt.exe"


def find_alt_process():
    """
    Find the running alt.exe process and return:
    - process object
    - full executable path
    """
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            name = proc.info['name']

            if name and name.lower() == "alt.exe":
                exe_path = proc.info['exe']

                if exe_path and os.path.exists(exe_path):
                    return proc, exe_path

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return None, None


def wait_for_port_close(port=5000, timeout=30):
    print(f"[INFO] Waiting for port {port} to close...")

    start = time.time()

    while time.time() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)

            # connect_ex returns 0 if port is OPEN
            if s.connect_ex(("127.0.0.1", port)) != 0:
                print(f"[INFO] Port {port} is now free.")
                return True

        time.sleep(1)

    print(f"[WARN] Timeout: Port {port} still in use.")
    return False


def download_new_version(dest_path):
    tmp_path = dest_path + ".tmp"

    print("[INFO] Downloading latest alt.exe...")

    r = requests.get(DOWNLOAD_URL, stream=True)

    if r.status_code != 200:
        raise Exception(f"Download failed: HTTP {r.status_code}")

    with open(tmp_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print("[INFO] Download complete.")

    return tmp_path


def replace_and_restart():
    try:
        print("[INFO] Searching for alt.exe...")

        proc, dest_path = find_alt_process()

        if not dest_path:
            print("[ERROR] Could not locate running alt.exe")
            return

        print(f"[INFO] Found alt.exe at:")
        print(f"       {dest_path}")

        tmp_path = download_new_version(dest_path)

        print("[INFO] Killing alt.exe...")

        try:
            proc.kill()
            proc.wait(timeout=10)
        except Exception as e:
            print(f"[WARN] Failed to kill process cleanly: {e}")

        if not wait_for_port_close(5000, timeout=30):
            print("[WARN] Port 5000 still active, continuing anyway...")

        print("[INFO] Replacing alt.exe...")

        os.replace(tmp_path, dest_path)

        print("[INFO] Launching updated alt.exe...")

        subprocess.Popen(
            [dest_path],
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        print("[INFO] Update complete.")

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == '__main__':
    replace_and_restart()