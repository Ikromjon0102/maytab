from flask import Flask, render_template, request, jsonify
import json
import webbrowser
import threading
from agent_logic import run_agent_loop # Mantiqni import qilamiz
import time

app = Flask(__name__)

CONFIG_FILE = 'config.json'

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"cloud_url": "", "school_key": "", "terminals": []}

@app.route('/')
def index():
    config = load_config()
    return render_template('index.html', config=config)

@app.route('/save', methods=['POST'])
def save():
    data = request.json
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    return jsonify({"status": "success", "message": "Saqlandi! Agent yangi sozlamalar bilan ishlaydi."})

def start_browser():
    """Dastur yonganda avtomatik brauzerni ochish"""
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    # 1. Agentni alohida potokda ishga tushiramiz
    agent_thread = threading.Thread(target=run_agent_loop, daemon=True)
    agent_thread.start()

    # 2. Brauzerni ochish
    threading.Thread(target=start_browser).start()

    # 3. Web serverni yoqish
    app.run(port=5000, debug=False)
