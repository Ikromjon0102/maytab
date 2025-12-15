import time
import requests
import sqlite3
import json
import random
from datetime import datetime
from requests.auth import HTTPDigestAuth
from hikvision_lib import HikvisionTerminal # Yangi libni chaqiramiz
import os


# Global o'zgaruvchi (Dasturni vaqtincha to'xtatish kerak bo'lsa)
AGENT_RUNNING = True
CONFIG_FILE = 'config.json'

# ==========================================
# 1. SOZLAMALARNI O'QISH
# ==========================================
def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Konfiguratsiya o'qishda xatolik: {e}")
        return None

# ==========================================
# 2. LOKAL BAZA (BUFFER)
# ==========================================
def init_db():
    """Baza va jadvallarni yaratish"""
    try:
        conn = sqlite3.connect('storage.db')
        c = conn.cursor()
        
        # Yuborilishi kerak bo'lgan loglar
        c.execute('''CREATE TABLE IF NOT EXISTS pending_logs 
                     (id INTEGER PRIMARY KEY, hik_id TEXT, log_time TEXT, is_sent INTEGER DEFAULT 0)''')
        
        # Har bir terminalning oxirgi vaqti
        c.execute('''CREATE TABLE IF NOT EXISTS system_state (key TEXT PRIMARY KEY, value TEXT)''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ DB Init Error: {e}")

def save_logs_local(logs):
    """Loglarni vaqtincha saqlash (Dublikat tekshiruvi bilan)"""
    if not logs: return 0
    
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    count = 0
    
    for log in logs:
        hik_id = log.get('employeeNoString')
        time_str = log.get('time')
        
        if not hik_id: continue

        # Agar bu log bazada bo'lmasa -> Yozamiz
        c.execute("SELECT id FROM pending_logs WHERE hik_id=? AND log_time=?", (hik_id, time_str))
        if not c.fetchone():
            c.execute("INSERT INTO pending_logs (hik_id, log_time) VALUES (?, ?)", (hik_id, time_str))
            count += 1
            
    conn.commit()
    conn.close()
    return count

def get_last_sync_time(ip):
    """Terminalning oxirgi yangilangan vaqtini olish"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    key = f"last_sync_{ip}"
    c.execute("SELECT value FROM system_state WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return row[0]
    return None

def update_last_sync_time(ip, time_str):
    """Terminal vaqtini yangilash"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    key = f"last_sync_{ip}"
    c.execute("INSERT OR REPLACE INTO system_state VALUES (?, ?)", (key, time_str))
    conn.commit()
    conn.close()

# ==========================================
# 3. HIKVISION TERMINALIDAN OLISH
# ==========================================
def fetch_from_device(device_conf):
    ip = device_conf.get('ip')
    name = device_conf.get('name', 'Unknown')
    user = device_conf.get('user', 'admin')
    password = device_conf.get('pass', '')

    if not ip or not password:
        return []
    
    # 1. Boshlanish vaqtini aniqlash
    last_run = get_last_sync_time(ip)
    now = datetime.now()
    
    if last_run:
        start_time = last_run
    else:
        # Birinchi marta: Bugun 00:00 dan
        start_time = now.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S")
    
    end_time = now.strftime("%Y-%m-%dT%H:%M:%S")
    
    # Timezone qo'shimchalari (+05:00)
    # Ba'zi terminallar 'Z' yoki '+05:00' talab qiladi, shuning uchun 4 xil variantni sinaymiz
    t_simple_start = start_time.split('+')[0]
    t_simple_end = end_time
    t_tz_start = f"{t_simple_start}+05:00"
    t_tz_end = f"{t_simple_end}+05:00"

    print(f"📡 {name} ({ip}): {t_simple_start} -> {t_simple_end}")

    url = f"http://{ip}/ISAPI/AccessControl/AcsEvent?format=json"
    auth = HTTPDigestAuth(user, password)
    rand_id = str(random.randint(1000, 99999))
    
    all_events = []
    position = 0
    has_more = True
    working_strategy_idx = -1 

    # Pagination Loop
    while has_more:
        # 4 xil strategiya (Timezone muammosini yechish uchun)
        strategies = [
            {"AcsEventCond": {"searchID": rand_id, "searchResultPosition": position, "maxResults": 30, "major": 0, "minor": 0, "startTime": t_simple_start, "endTime": t_simple_end}},
            {"AcsEventCond": {"searchID": rand_id, "searchResultPosition": position, "maxResults": 30, "major": 0, "minor": 0, "startTime": t_tz_start, "endTime": t_tz_end}},
            {"AcsEventCond": {"searchID": rand_id, "searchResultPosition": position, "maxResults": 30, "startTime": t_simple_start, "endTime": t_simple_end}},
            {"AcsEventCond": {"searchID": rand_id, "searchResultPosition": position, "maxResults": 30, "startTime": t_tz_start, "endTime": t_tz_end}}
        ]

        payloads = [strategies[working_strategy_idx]] if working_strategy_idx != -1 else strategies
        success = False
        current_events = []

        for idx, payload in enumerate(payloads):
            real_idx = working_strategy_idx if working_strategy_idx != -1 else idx
            payload["AcsEventCond"]["searchResultPosition"] = position
            
            try:
                resp = requests.post(url, json=payload, auth=auth, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    wrapper = data.get('AcsEvent', {})
                    total = wrapper.get('totalMatches', 0)
                    current_events = wrapper.get('InfoList', [])
                    
                    if working_strategy_idx == -1: working_strategy_idx = real_idx
                    success = True
                    break
            except:
                continue

        if not success:
            print(f"   ❌ {name}: Ulanib bo'lmadi.")
            return []
        
        if not current_events:
            break
            
        all_events.extend(current_events)
        
        # Pagination tekshiruvi
        if len(all_events) >= total:
            has_more = False
        else:
            position += len(current_events)
    
    # Muvaffaqiyatli bo'lsa, vaqtni saqlab qo'yamiz
    if success:
        update_last_sync_time(ip, t_tz_end)

    return all_events

# ==========================================
# 4. CLOUD SERVERGA YUBORISH
# ==========================================
def push_to_cloud(cloud_url, school_key):
    if not cloud_url or not school_key:
        return

    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    
    # Yuborilmagan loglarni olamiz (Bittada 100 ta)
    c.execute("SELECT id, hik_id, log_time FROM pending_logs WHERE is_sent=0 LIMIT 100")
    rows = c.fetchall()
    
    if not rows:
        conn.close()
        return

    print(f"☁️ Cloudga yuborilmoqda: {len(rows)} ta log...")
    
    payload = {
        "logs": [{"id": r[1], "time": r[2]} for r in rows]
    }
    
    try:
        headers = {'X-School-Key': school_key}
        resp = requests.post(cloud_url, json=payload, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            # Muvaffaqiyatli bo'lsa, lokal bazadan o'chiramiz
            ids = [str(r[0]) for r in rows]
            c.execute(f"DELETE FROM pending_logs WHERE id IN ({','.join(ids)})")
            conn.commit()
            print("   ✅ Cloud qabul qildi!")
        else:
            print(f"   ❌ Cloud rad etdi: {resp.status_code}")
            
    except Exception as e:
        print(f"   ⚠️ Internet yo'q (Lokal saqlandi): {e}")
    
    conn.close()

# --- YANGI: CLOUD DAN USERLARNI OLIB TERMINALGA YOZISH ---
def sync_users_downstream(conf):
    cloud_url = conf.get('cloud_url') # http://ip/api/upload-logs/
    # Bizga base url kerak: http://ip/api/
    base_api_url = cloud_url.replace("upload-logs/", "") 
    school_key = conf.get('school_key')
    terminals = conf.get('terminals', [])

    if not terminals: return

    # 1. Cloud dan yangi userlarni so'raymiz
    try:
        resp = requests.get(f"{base_api_url}get-users/", headers={'X-School-Key': school_key}, timeout=10)
        if resp.status_code != 200: return
        
        users = resp.json().get('users', [])
        if not users: return # Yangi user yo'q
        
        print(f"📥 Cloud dan {len(users)} ta yangi o'quvchi keldi. Terminalga yozilmoqda...")

    except Exception as e:
        print(f"⚠️ User Sync Error: {e}")
        return

    synced_ids = []

    # 2. Har bir user uchun rasm yuklab olamiz
    for user in users:
        # Vaqtincha rasm fayli
        temp_img = f"temp_{user['id']}.jpg"
        has_photo = False

        if user['photo_url']:
            try:
                img_data = requests.get(user['photo_url'], timeout=10).content
                with open(temp_img, 'wb') as f:
                    f.write(img_data)
                has_photo = True
            except:
                print(f"   ⚠️ Rasm yuklashda xato: {user['full_name']}")

        # 3. Har bir terminalga yozamiz
        all_terminals_success = True
        
        for term in terminals:
            hik = HikvisionTerminal(term['ip'], term['user'], term['pass'])
            
            # A) User yaratish
            res = hik.add_user(user['hik_id'], user['full_name'])
            if not res['success']:
                print(f"   ❌ {term['name']}: User yaratilmadi ({user['full_name']}) - {res.get('error')}")
                all_terminals_success = False
                continue

            # B) Rasm yuklash (agar bo'lsa)
            if has_photo:
                res_face = hik.set_user_face(user['hik_id'], temp_img)
                if not res_face['success']:
                    print(f"   ⚠️ {term['name']}: Rasm o'tmadi ({user['full_name']})")
                    # Rasmsiz bo'lsa ham mayli, asosiysi user yaratildi
        
        # Temp faylni o'chiramiz
        if has_photo and os.path.exists(temp_img):
            os.remove(temp_img)

        # Agar hamma terminallarda (yoki hech bo'lmasa bittasida) user yaratilsa -> Success
        if all_terminals_success:
            synced_ids.append(user['id'])
            print(f"   ✅ {user['full_name']} yuklandi.")

    # 4. Cloudga hisobot berish
    if synced_ids:
        try:
            requests.post(
                f"{base_api_url}confirm-sync/", 
                json={'synced_ids': synced_ids}, 
                headers={'X-School-Key': school_key}
            )
            print(f"📤 {len(synced_ids)} ta user tasdiqlandi.")
        except:
            pass

# ==========================================
# 5. ASOSIY UYQUSIZ REJIM (LOOP)
# ==========================================
def run_agent_loop():
    global AGENT_RUNNING
    print("🚀 Agent xizmati ishga tushdi...")
    init_db()
    
    while True:
        # Dastur to'xtatilgan bo'lsa kutamiz
        if not AGENT_RUNNING:
            time.sleep(1)
            continue
        
        # Konfiguratsiyani har safar yangilab o'qiymiz
        # (Shunda foydalanuvchi Webdan o'zgartirsa, darhol ishlaydi)
        conf = load_config()
        
        if not conf or not conf.get('school_key') or not conf.get('cloud_url'):
            print("⏳ Sozlamalar yo'q. Kutilmoqda...")
            time.sleep(5)
            continue

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Sinxronizatsiya...")

        terminals = conf.get('terminals', [])
        cloud_url = conf.get('cloud_url')
        school_key = conf.get('school_key')

        # 1. Terminallardan log yig'ish
        for term in terminals:
            logs = fetch_from_device(term)
            if logs:
                count = save_logs_local(logs)
                print(f"   📥 {term.get('name')}: {count} ta yangi log saqlandi.")
        
        # 2. Cloudga yuborish
        push_to_cloud(cloud_url, school_key)

        sync_users_downstream(conf)
        
        # 3. Kutish (1 daqiqa)
        time.sleep(60)