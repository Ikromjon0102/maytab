# --- CLOUD SERVER SOZLAMALARI ---
# Serveringiz IP manzili yoki Domeni
CLOUD_URL = "http://127.0.0.1:8000/api/upload-logs/"

# Har bir maktab uchun Admin paneldan olingan alohida UUID kalit
SCHOOL_API_KEY = "92992c7b-d847-43a5-9aa8-4b723f69bec7"

# --- TERMINALLAR RO'YXATI ---
# Maktabda nechta terminal bo'lsa, hammasini yozib chiqing
TERMINALS = [
    {
        "name": "Kirish (Asosiy)",
        "ip": "192.168.0.9",
        "user": "admin",
        "pass": "uchk2025"
    },
    # {
    #     "name": "Orqa eshik",
    #     "ip": "192.168.0.12",
    #     "user": "admin",
    #     "pass": "uchk2025"
    # }
]