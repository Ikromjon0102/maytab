from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from datetime import datetime
from .models import School, Student
from attendance.models import DailyAttendance
from staff.models import Employee



class ReceiveLogsAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        api_key = request.headers.get('X-School-Key')
        school = get_object_or_404(School, api_key=api_key, is_active=True)

        # --- YANGI QATOR: "Men tirikman" belgisini qo'yish ---
        school.last_activity = timezone.now()
        school.save()
        logs = request.data.get('logs', [])
        
        saved = 0
        for log in logs:
            hik_id = log.get('id')
            time_str = log.get('time')
            if not hik_id: continue
            
            try:
                dt = datetime.fromisoformat(time_str)
                # Odamni topish
                student = Student.objects.filter(school=school, hikvision_id=hik_id).first()
                employee = None
                if not student:
                    employee = Employee.objects.filter(school=school, hikvision_id=hik_id).first()
                
                if not student and not employee: continue

                obj, created = DailyAttendance.objects.get_or_create(
                    student=student, employee=employee, date=dt.date()
                )
                
                if created:
                    obj.arrived_at = dt.time()
                    obj.save()
                    saved += 1

                else:
                    if obj.arrived_at and dt.time() > obj.arrived_at:
                        obj.left_at = dt.time()
                        obj.save()
            except: pass
            
        return Response({"status": "ok", "saved": saved})
    
# ... eski importlar ...

class GetNewUsersAPI(APIView):
    permission_classes = [AllowAny]

    # MUHIM: Bu yerda 'def post' emas, 'def get' bo'lishi SHART!
    def get(self, request):
        api_key = request.headers.get('X-School-Key')
        school = get_object_or_404(School, api_key=api_key, is_active=True)

        # Tiriklik belgisini yangilash
        school.last_activity = timezone.now()
        school.save()

        # ... qolgan kod o'zgarishsiz ...
        users = Student.objects.filter(school=school, is_synced=False)[:10]
        data = []
        for u in users:
            photo_url = request.build_absolute_uri(u.photo.url) if u.photo else None
            data.append({
                "id": u.id,
                "full_name": u.full_name,
                "hikvision_id": u.hikvision_id,
                "photo_url": photo_url
            })

        return Response({"users": data})

class ConfirmUserSyncAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        api_key = request.headers.get('X-School-Key')
        school = get_object_or_404(School, api_key=api_key)
        
        user_ids = request.data.get('synced_ids', [])
        
        if user_ids:
            # Shu ID larni "synced" deb belgilaymiz
            Student.objects.filter(school=school, id__in=user_ids).update(is_synced=True)
            
        return Response({"status": "ok"})