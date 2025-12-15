import requests
from requests.auth import HTTPDigestAuth
import sqlite3
import time
import random
import sys
from datetime import datetime
from config import CLOUD_URL, SCHOOL_API_KEY, TERMINALS

# ==========================================
# 1. LOKAL BAZA BILAN ISHLASH
# ==========================================
def init_db():
    """Baza va jadvallarni yaratish"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    
    # Yuborilishi kerak bo'lgan loglar
    c.execute('''CREATE TABLE IF NOT EXISTS pending_logs 
                 (id INTEGER PRIMARY KEY, hik_id TEXT, log_time TEXT, is_sent INTEGER DEFAULT 0)''')
    
    # Har bir terminalning oxirgi vaqti
    c.execute('''CREATE TABLE IF NOT EXISTS system_state (key TEXT PRIMARY KEY, value TEXT)''')
    
    conn.commit()
    conn.close()

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
# 2. HIKVISION TERMINALIDAN OLISH
# ==========================================
def fetch_from_device(device_conf):
    ip = device_conf['ip']
    name = device_conf['name']
    
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
    t_simple_start = start_time.split('+')[0]
    t_simple_end = end_time
    t_tz_start = f"{t_simple_start}+05:00"
    t_tz_end = f"{t_simple_end}+05:00"

    print(f"📡 {name} ({ip}): {t_simple_start} -> {t_simple_end}")

    url = f"http://{ip}/ISAPI/AccessControl/AcsEvent?format=json"
    auth = HTTPDigestAuth(device_conf['user'], device_conf['pass'])
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
    
    # Muvaffaqiyatli bo'lsa, vaqtni saqlab qo'yamiz (keyingi safar uchun)
    if success:
        update_last_sync_time(ip, t_tz_end)

    return all_events

# ==========================================
# 3. CLOUD SERVERGA YUBORISH
# ==========================================
def push_to_cloud():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    
    # Yuborilmagan loglarni olamiz (Bittada 50 ta)
    c.execute("SELECT id, hik_id, log_time FROM pending_logs WHERE is_sent=0 LIMIT 50")
    rows = c.fetchall()
    
    if not rows:
        conn.close()
        return

    print(f"☁️ Cloudga yuborilmoqda: {len(rows)} ta log...")
    
    # Django kutayotgan format: {"logs": [{"id": "1", "time": "..."}]}
    payload = {
        "logs": [{"id": r[1], "time": r[2]} for r in rows]
    }
    
    try:
        headers = {'X-School-Key': SCHOOL_API_KEY}
        resp = requests.post(CLOUD_URL, json=payload, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            # Muvaffaqiyatli bo'lsa, lokal bazadan o'chiramiz
            ids = [str(r[0]) for r in rows]
            c.execute(f"DELETE FROM pending_logs WHERE id IN ({','.join(ids)})")
            conn.commit()
            print("   ✅ Cloud qabul qildi!")
        else:
            print(f"   ❌ Cloud rad etdi: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"   ⚠️ Internet yo'q (Lokal saqlandi): {e}")
    
    conn.close()

# ==========================================
# 4. ASOSIY UYQUSIZ REJIM (LOOP)
# ==========================================
if __name__ == "__main__":
    print("🚀 SmartAgent ishga tushdi...")
    init_db()
    
    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Ish boshlandi...")
        
        # 1. Barcha terminallardan log yig'ish
        for term in TERMINALS:
            logs = fetch_from_device(term)
            if logs:
                count = save_logs_local(logs)
                print(f"   📥 {term['name']}: {count} ta yangi log saqlandi.")
            else:
                print(f"   ℹ️ {term['name']}: Yangi log yo'q.")
        
        # 2. Cloudga yuborish (Internet bor bo'lsa ketadi, bo'lmasa qoladi)
        push_to_cloud()
        
        # 3. 1 daqiqa dam olish
        time.sleep(60)