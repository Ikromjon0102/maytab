import requests
from requests.auth import HTTPDigestAuth
import json
import os
import uuid

class HikvisionTerminal:
    def __init__(self, ip, username, password, port=80):
        self.ip = ip
        self.base_url = f"http://{ip}:{port}"
        self.auth = HTTPDigestAuth(username, password)
        self.headers_json = {'Content-Type': 'application/json'}

    def _request(self, method, endpoint, data=None, files=None, json_payload=True):
        url = f"{self.base_url}{endpoint}"
        try:
            if data and json_payload:
                data = json.dumps(data)
            
            response = requests.request(
                method, 
                url, 
                data=data, 
                files=files, 
                auth=self.auth, 
                headers=self.headers_json if json_payload and not files else None,
                timeout=15
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"Status: {response.status_code}", "raw": response.text}
        
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_user(self, user_id, name, start_date="2024-01-01", end_date="2035-12-31"):
        endpoint = "/ISAPI/AccessControl/UserInfo/Record?format=json"
        payload = {
            "UserInfo": {
                "employeeNo": str(user_id),
                "name": name,
                "userType": "normal",
                "Valid": {
                    "enable": True,
                    "beginTime": f"{start_date}T00:00:00",
                    "endTime": f"{end_date}T23:59:59",
                    "timeType": "local"
                },
                "doorRight": "1",
                "RightPlan": [{"doorNo": 1, "planTemplateNo": "1"}]
            }
        }
        return self._request("POST", endpoint, data=payload)

    def set_user_face(self, user_id, image_path):
        if not os.path.exists(image_path):
            return {"success": False, "error": "Fayl topilmadi"}

        endpoint = "/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json"
        face_info = {
            "faceLibType": "blackFD",
            "FDID": "1",
            "FPID": str(user_id)
        }
        
        try:
            files = {
                'FaceDataRecord': (None, json.dumps(face_info), 'application/json'),
                'img': ('face.jpg', open(image_path, 'rb'), 'image/jpeg')
            }
            # Fayl yuborishda header avtomatik bo'lishi kerak, shuning uchun json_payload=False
            url = f"{self.base_url}{endpoint}"
            res = requests.post(url, files=files, auth=self.auth, timeout=30)
            
            if res.status_code == 200:
                resp_json = res.json()
                if resp_json.get("statusCode") == 1 or resp_json.get("statusString") == "OK":
                    return {"success": True, "msg": "Rasm yuklandi"}
                return {"success": False, "raw": res.text}
            return {"success": False, "error": res.status_code}
            
        except Exception as e:
            return {"success": False, "error": str(e)}