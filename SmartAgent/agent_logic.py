import time
import requests
import sqlite3
import json
import random
import logging
import os
from datetime import datetime
from requests.auth import HTTPDigestAuth
from hikvision_lib import HikvisionTerminal

# --- 1. LOG TIZIMI (FAYLGA YOZISH) ---
logging.basicConfig(
    filename='agent.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# Konsolga ham chiqarish (Debug paytida ko'rish uchun)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

AGENT_RUNNING = True
CONFIG_FILE = 'config.json'


def log(msg, level="info"):
    """Universal log yozuvchi"""
    if level == "error":
        logging.error(msg)
    else:
        logging.info(msg)


def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        log(f"⚠️ Konfiguratsiya o'qishda xatolik: {e}", "error")
        return None


def normalize_url(raw_url):
    """
    URLni to'g'rilash.
    Kirish: "https://smart.uz" yoki "https://smart.uz/"
    Chiqish: "https://smart.uz/api/"
    """
    if not raw_url: return ""

    url = raw_url.strip()
    if url.endswith("/api/upload-logs/"):  # Eski format bo'lsa
        return url.replace("upload-logs/", "")

    if url.endswith("/"):
        return f"{url}api/"
    else:
        return f"{url}/api/"


# ==========================================
# 2. LOKAL BAZA
# ==========================================
def init_db():
    try:
        conn = sqlite3.connect('storage.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS pending_logs 
                     (id INTEGER PRIMARY KEY, hik_id TEXT, log_time TEXT, is_sent INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS system_state (key TEXT PRIMARY KEY, value TEXT)''')
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"DB Init Error: {e}", "error")


def save_logs_local(logs):
    if not logs: return 0
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    count = 0
    for log_item in logs:
        hik_id = log_item.get('employeeNoString')
        time_str = log_item.get('time')
        if not hik_id: continue
        c.execute("SELECT id FROM pending_logs WHERE hik_id=? AND log_time=?", (hik_id, time_str))
        if not c.fetchone():
            c.execute("INSERT INTO pending_logs (hik_id, log_time) VALUES (?, ?)", (hik_id, time_str))
            count += 1
    conn.commit()
    conn.close()
    return count


def get_last_sync_time(ip):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT value FROM system_state WHERE key=?", (f"last_sync_{ip}",))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def update_last_sync_time(ip, time_str):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO system_state VALUES (?, ?)", (f"last_sync_{ip}", time_str))
    conn.commit()
    conn.close()


# ==========================================
# 3. TERMINALDAN LOG OLISH
# ==========================================
def fetch_from_device(device_conf):
    ip = device_conf.get('ip')
    name = device_conf.get('name', 'Unknown')
    user = device_conf.get('user', 'admin')
    password = device_conf.get('pass', '')

    if not ip or not password: return []

    last_run = get_last_sync_time(ip)
    now = datetime.now()
    start_time = last_run if last_run else now.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S")
    end_time = now.strftime("%Y-%m-%dT%H:%M:%S")

    t_simple_start = start_time.split('+')[0]
    t_simple_end = end_time
    t_tz_start = f"{t_simple_start}+05:00"
    t_tz_end = f"{t_simple_end}+05:00"

    log(f"📡 {name} ({ip}): Log qidirilmoqda...")

    url = f"http://{ip}/ISAPI/AccessControl/AcsEvent?format=json"
    auth = HTTPDigestAuth(user, password)
    rand_id = str(random.randint(1000, 99999))

    all_events = []
    position = 0
    has_more = True

    # Oddiy va TZ variantlarini sinab ko'rish
    strategies = [
        {"startTime": t_simple_start, "endTime": t_simple_end},
        {"startTime": t_tz_start, "endTime": t_tz_end}
    ]

    for strat in strategies:
        try:
            payload = {
                "AcsEventCond": {
                    "searchID": rand_id,
                    "searchResultPosition": position,
                    "maxResults": 30,
                    "major": 0, "minor": 0,
                    **strat
                }
            }
            resp = requests.post(url, json=payload, auth=auth, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                wrapper = data.get('AcsEvent', {})
                current_events = wrapper.get('InfoList', [])
                if current_events:
                    all_events.extend(current_events)
                    update_last_sync_time(ip, t_tz_end)
                    return all_events  # Birinchi ishlagani yetarli
        except:
            continue

    return []


# ==========================================
# 4. CLOUDGA LOG YUBORISH
# ==========================================
def push_to_cloud(api_root, school_key):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, hik_id, log_time FROM pending_logs WHERE is_sent=0 LIMIT 50")
    rows = c.fetchall()

    if not rows:
        conn.close()
        return

    log(f"☁️ Cloudga yuborilmoqda: {len(rows)} ta log...")
    payload = {"logs": [{"id": r[1], "time": r[2]} for r in rows]}

    try:
        url = f"{api_root}upload-logs/"  # api/upload-logs/
        headers = {'X-School-Key': school_key}
        resp = requests.post(url, json=payload, headers=headers, timeout=10)

        if resp.status_code == 200:
            ids = [str(r[0]) for r in rows]
            c.execute(f"DELETE FROM pending_logs WHERE id IN ({','.join(ids)})")
            conn.commit()
            log("   ✅ Loglar muvaffaqiyatli yuborildi!")
        else:
            log(f"   ❌ Cloud Log Xatosi: {resp.status_code} - {resp.text}", "error")

    except Exception as e:
        log(f"   ⚠️ Log yuborishda tarmoq xatosi: {e}", "error")

    conn.close()


# ==========================================
# 5. USERLARNI SINXRONIZATSIYA QILISH
# ==========================================
def sync_users_downstream(api_root, school_key, terminals):
    try:
        url = f"{api_root}get-users/"
        resp = requests.get(url, headers={'X-School-Key': school_key}, timeout=10)

        if resp.status_code != 200: return

        users = resp.json().get('users', [])
        if not users: return

        log(f"📥 {len(users)} ta yangi o'quvchi topildi. Yuklanmoqda...")

        synced_ids = []
        for user in users:
            # Rasmni yuklab olish
            temp_img = f"temp_{user['id']}.jpg"
            has_photo = False
            if user['photo_url']:
                try:
                    img_data = requests.get(user['photo_url'], timeout=10).content
                    with open(temp_img, 'wb') as f:
                        f.write(img_data)
                    has_photo = True
                except:
                    pass

            all_ok = True
            for term in terminals:
                hik = HikvisionTerminal(term['ip'], term['user'], term['pass'])

                # --- O'ZGARISH SHU YERDA ---
                # user['hik_id'] EMAS, user['hikvision_id'] bo'lishi kerak
                res = hik.add_user(user['hikvision_id'], user['full_name'])

                if res['success']:
                    if has_photo:
                        # BU YERDA HAM O'ZGARISH
                        hik.set_user_face(user['hikvision_id'], temp_img)
                else:
                    log(f"   ❌ {term['name']}: User xatosi - {res.get('error')}", "error")
                    all_ok = False

            if has_photo and os.path.exists(temp_img): os.remove(temp_img)

            if all_ok:
                synced_ids.append(user['id'])
                log(f"   ✅ {user['full_name']} yuklandi.")

        if synced_ids:
            requests.post(f"{api_root}confirm-sync/", json={'synced_ids': synced_ids},
                          headers={'X-School-Key': school_key})
            log(f"📤 {len(synced_ids)} ta user serverda tasdiqlandi.")

    except Exception as e:
        log(f"⚠️ User Sync Xatosi: {e}", "error")


# ==========================================
# 6. ASOSIY LOOP
# ==========================================
def run_agent_loop():
    global AGENT_RUNNING
    log("🚀 Agent xizmati ishga tushdi...")
    init_db()

    while True:
        if not AGENT_RUNNING:
            time.sleep(1)
            continue

        conf = load_config()
        if not conf or not conf.get('school_key') or not conf.get('cloud_url'):
            time.sleep(5)
            continue

        # URL ni to'g'irlash
        raw_url = conf.get('cloud_url')
        api_root = normalize_url(raw_url)  # https://site.uz/api/
        school_key = conf.get('school_key')
        terminals = conf.get('terminals', [])

        # 1. Loglar
        for term in terminals:
            logs = fetch_from_device(term)
            if logs: save_logs_local(logs)

        push_to_cloud(api_root, school_key)

        # 2. Userlar
        sync_users_downstream(api_root, school_key, terminals)

        time.sleep(60)