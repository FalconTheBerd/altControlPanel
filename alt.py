# Full Credit to FalconTheBerd
import subprocess
from flask import Flask, request, jsonify, send_from_directory, render_template_string, Response, abort
import os
from PIL import ImageGrab
from flask_cors import CORS
import time
import cv2
import numpy as np
import ctypes
import platform
import sys
import argparse
from werkzeug.serving import make_server, ThreadedWSGIServer
import socket

if platform.system() != "Windows":
    sys.stderr.write("alt.py is only supported on Windows.\n")
    sys.exit(0)

app = Flask(__name__)

# ---------- Webcam viewer: list + live MJPEG feed ----------
def _probe_cameras(max_index: int = 8):
    """Return a list of available camera indices and labels."""
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # DShow is reliable on Windows
        if cap is not None and cap.isOpened():
            # Try to read one frame to verify it truly works
            ok, _ = cap.read()
            if ok:
                found.append({"index": i, "label": f"Camera {i}"})
        if cap is not None:
            cap.release()
    return found

def _generate_cam_frames(index: int, width: int | None = None, height: int | None = None, fps: int = 15):
    """Yield JPEG frames from a webcam as an MJPEG stream."""
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        # Yield a single tiny JPEG explaining the issue
        err = f"Unable to open camera index {index}".encode("utf-8")
        blank = np.full((80, 600, 3), 255, dtype=np.uint8)
        cv2.putText(blank, err.decode(), (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2, cv2.LINE_AA)
        ok, buf = cv2.imencode(".jpg", blank)
        if ok:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
        return

    try:
        if width:  cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
        if height: cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        delay = max(0.0, 1.0 / max(1, fps))
        while True:
            ok, frame = cap.read()
            if not ok:
                # brief pause then try again
                time.sleep(0.1)
                continue
            ok, buffer = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
            time.sleep(delay)
    finally:
        cap.release()
        
        
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": "*"}})

BASE_DIRECTORY = os.path.expanduser("~")

import tkinter as tk
from tkinter import ttk
from threading import Thread


@app.route("/webcams")
def webcams_page():
    """Landing page: lists available webcams and provides viewers."""
    cams = _probe_cameras()
    # Basic HTML similar spirit to /files
    html = """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Webcams</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .cam { margin: 16px 0; padding: 12px; border: 1px solid #ddd; border-radius: 8px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
        .preview { width: 100%; aspect-ratio: 16/9; object-fit: cover; background:#f7f7f7; }
        a { color: #06c; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .note { color: #555; margin: 8px 0 16px; }
      </style>
    </head>
    <body>
      <h1>Available Webcams</h1>
      <div class="note">Click a camera to open a full feed. You can also view inline previews below.</div>
      {% if cams %}
        <div class="grid">
        {% for cam in cams %}
          <div class="cam">
            <h3>{{ cam.label }} (index {{ cam.index }})</h3>
            <div>
              <a href="/webcam?index={{ cam.index }}">Open viewer</a> |
              <a href="/snapshot?index={{ cam.index }}" target="_blank">Snapshot</a>
            </div>
            <img class="preview" src="/webcam_feed?index={{ cam.index }}&fps=10" />
          </div>
        {% endfor %}
        </div>
      {% else %}
        <p><strong>No cameras detected.</strong> Try plugging one in and refresh.</p>
      {% endif %}
      <hr>
      <p><a href="/files">Go to File Browser</a> · <a href="/interactive_view">Screen Viewer</a></p>
    </body>
    </html>
    """
    return render_template_string(html, cams=cams)

@app.route("/webcam")
def webcam_viewer():
    """Single-camera viewer page, with optional size/fps controls via querystring."""
    try:
        idx = int(request.args.get("index", "0"))
    except ValueError:
        idx = 0
    width  = request.args.get("w")  # e.g. 1280
    height = request.args.get("h")  # e.g. 720
    fps    = request.args.get("fps", "15")

    html = """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Webcam {{ idx }}</title>
      <style>
        body { margin: 0; font-family: Arial, sans-serif; }
        header { padding: 12px 16px; border-bottom: 1px solid #ddd; display:flex; gap:12px; align-items:center; }
        main { display:flex; height: calc(100vh - 56px); }
        img { width: 100%; height: 100%; object-fit: contain; background:#000; }
        input, select, button { padding:6px 8px; }
        label { font-size: 14px; color: #333; }
      </style>
    </head>
    <body>
      <header>
        <strong>Webcam index {{ idx }}</strong>
        <form id="opts" onsubmit="apply(event)">
          <label>W <input type="number" id="w" placeholder="e.g. 1280" value="{{ width or '' }}"></label>
          <label>H <input type="number" id="h" placeholder="e.g. 720" value="{{ height or '' }}"></label>
          <label>FPS <input type="number" id="fps" placeholder="15" value="{{ fps }}"></label>
          <button>Apply</button>
          <a href="/webcams" style="margin-left:8px;">Back</a>
        </form>
      </header>
      <main>
        <img id="feed" src="">
      </main>
      <script>
        function apply(e){
          e && e.preventDefault();
          const w = document.getElementById('w').value;
          const h = document.getElementById('h').value;
          const fps = document.getElementById('fps').value || 15;
          const params = new URLSearchParams({ index: "{{ idx }}", fps });
          if (w) params.set('w', w);
          if (h) params.set('h', h);
          document.getElementById('feed').src = '/webcam_feed?' + params.toString();
        }
        apply();
      </script>
    </body>
    </html>
    """
    return render_template_string(html, idx=idx, width=width, height=height, fps=fps)

@app.route("/webcam_feed")
def webcam_feed():
    """MJPEG stream from a webcam: /webcam_feed?index=0&w=1280&h=720&fps=15"""
    try:
        idx = int(request.args.get("index", "0"))
    except ValueError:
        idx = 0
    width  = request.args.get("w", type=int)
    height = request.args.get("h", type=int)
    fps    = request.args.get("fps", type=int, default=15)
    return Response(_generate_cam_frames(idx, width, height, fps),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/snapshot")
def snapshot():
    """Return a single JPEG snapshot from the selected webcam."""
    try:
        idx = int(request.args.get("index", "0"))
    except ValueError:
        idx = 0
    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        abort(404, description=f"Unable to open camera index {idx}")
    try:
        ok, frame = cap.read()
    finally:
        cap.release()
    if not ok:
        abort(500, description="Failed to capture frame")
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        abort(500, description="Failed to encode JPEG")
    return Response(buf.tobytes(), mimetype="image/jpeg")
# ---------- /Webcam viewer ----------

@app.route('/download', methods=['GET'])
def download():
    # Query params coming from your /files UI
    directory = request.args.get('dir', BASE_DIRECTORY)
    filename = request.args.get('file')

    if not filename:
        return "Missing 'file' parameter.", 400

    # Normalize and harden paths
    directory = os.path.normpath(directory)
    abs_base = os.path.abspath(BASE_DIRECTORY)
    abs_dir = os.path.abspath(directory)

    # Block attempts to escape the allowed base directory
    try:
        if os.path.commonpath([abs_base, abs_dir]) != abs_base:
            return "Access denied.", 403
    except ValueError:
        return "Invalid path.", 400

    # Build the final file path and validate
    file_path = os.path.normpath(os.path.join(abs_dir, filename))
    if not os.path.exists(file_path):
        return "File not found.", 404
    if os.path.isdir(file_path):
        return "Cannot download a directory.", 400
    if not os.access(file_path, os.R_OK):
        return "File is not readable.", 403

    # Serve as an attachment
    # Flask 2.x: send_from_directory(directory, path, **kwargs)
    return send_from_directory(
        directory=abs_dir,
        path=os.path.basename(file_path),
        as_attachment=True,
        download_name=os.path.basename(file_path)  # optional; controls the save-as name
    )

@app.route('/interactive_view')
def interactive_view():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Interactive Screen Control</title>

        <style>
            body, html {
                margin: 0;
                width: 100%;
                height: 100%;
                overflow: hidden;
                background: black;
            }

            #screen {
                width: 100%;
                height: 100%;
                object-fit: contain;
                display: block;
            }
        </style>
    </head>

    <body>
        <img id="screen" src="/video_feed" onclick="sendClick(event)">

        <script>
            async function sendClick(e) {
                const img = e.target;
                const rect = img.getBoundingClientRect();

                // Real image aspect ratio
                const imgAspect = img.naturalWidth / img.naturalHeight;

                // Browser display aspect ratio
                const rectAspect = rect.width / rect.height;

                let displayedWidth, displayedHeight;
                let offsetX, offsetY;

                if (rectAspect > imgAspect) {
                    // Black bars on left/right
                    displayedHeight = rect.height;
                    displayedWidth = displayedHeight * imgAspect;

                    offsetX = (rect.width - displayedWidth) / 2;
                    offsetY = 0;
                } else {
                    // Black bars on top/bottom
                    displayedWidth = rect.width;
                    displayedHeight = displayedWidth / imgAspect;

                    offsetX = 0;
                    offsetY = (rect.height - displayedHeight) / 2;
                }

                // Mouse position relative to image element
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;

                // Ignore clicks outside actual image area
                if (
                    mouseX < offsetX ||
                    mouseX > offsetX + displayedWidth ||
                    mouseY < offsetY ||
                    mouseY > offsetY + displayedHeight
                ) {
                    return;
                }

                // Convert to ratios
                const x_ratio = (mouseX - offsetX) / displayedWidth;
                const y_ratio = (mouseY - offsetY) / displayedHeight;

                await fetch('/mouse_click', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        x_ratio: x_ratio,
                        y_ratio: y_ratio
                    })
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

        # Get real screen resolution
        screen = ImageGrab.grab()
        screen_width, screen_height = screen.size

        # Convert ratios to actual coordinates
        x = int(x_ratio * screen_width)
        y = int(y_ratio * screen_height)

        # Move mouse
        ctypes.windll.user32.SetCursorPos(x, y)

        # Left click
        ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)  # Left down
        ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)  # Left up

        return jsonify({
            "message": f"Clicked at ({x}, {y})"
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

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


class ReusableServer:
    def __init__(self, app, host, port):
        self.server = make_server(host, port, app, ThreadedWSGIServer)
        self.server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def serve_forever(self):
        print("[INFO] Threaded server started on port 5000.")
        self.server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Alt Control Panel server')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    env_debug = os.environ.get('ALT_DEBUG', '0').lower() in {'1', 'true', 'yes'}
    debug_mode = args.debug or env_debug

    try:
        print("[INFO] Starting Flask server with SO_REUSEADDR...")
        server = ReusableServer(app, '0.0.0.0', 5000)
        server.serve_forever()
    except Exception as e:
        print(f"[FATAL ERROR] Failed to bind server: {e}")
