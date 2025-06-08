# Alt Control Panel

## Overview

Alt Control Panel is a Python-based remote control application designed for managing a secondary computer (referred to as "Alt") over a network. It provides functionalities such as file management, task management, terminal command execution, and screenshot capture via a Flask web interface.

> **Warning**
> The server-side scripts (`alt.py`, `bootstrapper.py`, and the utilities in
> `secondaryPrograms/`) rely on Windows-specific APIs. These programs will exit
> immediately on non-Windows systems.

## Features

- **File Management**:
  - Browse files and directories.
  - Upload files to Alt.
  - Download files from Alt.
  - Delete files on Alt.
  - Execute `.exe` files remotely.

- **Task Management**:
  - View a list of all running tasks on Alt in a clean HTML table.
  - Kill specific tasks by name or PID (Process ID).

- **Terminal Command Execution**:
  - Send commands to Alt's terminal remotely.
  - Receive output or error messages from executed commands.

- **Screenshot Capture**:
  - Capture screenshots of Alt's desktop.
  - Automatically upload screenshots to a configured Discord webhook.
- **Keystroke Simulation**:
  - Send keystrokes to Alt directly from the control panel using the Windows API.
  - System shortcuts like `Alt+Tab` work correctly for window switching.
  - Separate commands with commas to send them sequentially, e.g., `Alt+Tab, Alt+Tab`.
  - You can repeat keys within a combo, such as `Alt+Tab+Tab` to move two windows ahead.
  - Plain words can be typed normally without commas (e.g., `hello`).
  - If a plus sign is used with no special keys (e.g., `peg+cat`), the `+` is typed as a normal character.


## Requirements

1. **Alt Machine**:
   - Windows operating system.
   - Python 3.8 or later installed.
   - `pip` to install required dependencies.

2. **Control Machine**:
   - Web browser for accessing the control panel.

3. **Python Dependencies**:
   - Flask
   - Flask-Cors
   - Pillow (for screenshots)
   - Requests

Install these dependencies with:
```bash
pip install flask flask-cors pillow requests
```

4. **Optional**:
   - Use [PyInstaller](https://pyinstaller.org/) to convert the Python script into an executable for easier deployment.

## Usage

  - Separate multiple combinations with commas, e.g., `Alt+Tab, Alt+Tab` to switch twice.
  - Plain text like `hello` will be typed character by character.
  - A plus sign is typed normally when no special keys are present (e.g., `peg+cat`).
  - You can chain commands with commas, such as `Alt+Tab, Alt+Tab` to cycle twice.
  - Plain strings like `test` are typed normally.
  - "peg+cat" will type the plus sign since no special keys are present.
### 1. Running the Program on Alt
1. Clone or copy the repository to the Alt machine.
2. Start the script by running:
   ```bash
   python alt.py
   ```
   Or, if using an executable:
   ```bash
   alt.exe
   ```

### 2. Accessing the Control Panel
1. On your control machine, open a web browser.
2. Open `controlpanel.html`
3. Enter Alt's local IP address.

### 3. Available Endpoints

- `/files`: Browse files and directories.
- `/run_command`: Execute terminal commands.
- `/list_tasks`: View running tasks.
- `/kill_task`: Kill tasks by name or PID.
- `/screenshot`: Capture and upload screenshots.
- `/run_file`: Execute files remotely.
- `/keystroke`: Simulate keystrokes on Alt.
  - Use input like `Alt+Tab` to change windows remotely. System shortcuts are supported.


### 4. Control Panel Interface
Use the web interface to:
- Perform file operations.
- View and manage running tasks.
- Execute terminal commands.
- Request screenshots.
- Send keystrokes to Alt.
  - e.g., type `Alt+Tab` to switch windows using the native API.


## How It Works

1. **Web Interface**: The control panel provides an intuitive interface for sending commands to Alt.
2. **Flask API**: Alt runs a Flask-based API server to process requests and perform tasks.
3. **Discord Integration**: Screenshots are automatically sent to a Discord webhook for review.

## Example Commands

### Running a Terminal Command
1. Navigate to the terminal section of the control panel.
2. Enter a valid command (e.g., `dir` or `tasklist`) and submit.
3. View the output directly in the control panel.

### Killing a Task
1. View the task list.
2. Enter the PID of the task to kill.
3. Confirm the action.

### File Management
1. Browse files in the `/files` endpoint.
2. Upload, download, delete, or execute files as needed.

## Limitations

- **Windows-Only**: The server components run solely on Windows. Other
  operating systems are not supported and the scripts will exit immediately on
  those systems.
- **Permissions**: Some directories or files may be inaccessible due to permission restrictions.
- **Network Access**: Requires both machines to be on the same network or have proper port forwarding configured.

## Security Considerations

- **Firewall Rules**: Ensure that the port used (default: 5000) is open for communication.
- **Access Control**: Restrict access to trusted devices by securing the network and avoiding public exposure of the API.
- **Executable Trust**: Be cautious about executing remote `.exe` files.

## Notes

This program is intended for personal use and should not be deployed in environments with sensitive data unless properly secured. It is designed for education and utility purposes. Misuse may lead to unintended consequences.
