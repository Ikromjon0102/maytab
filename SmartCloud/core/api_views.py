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

        # Tiriklik belgisi
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

                # 1. Avval O'quvchidan qidiramiz
                student = Student.objects.filter(school=school, hikvision_id=hik_id).first()
                employee = None

                # 2. Agar o'quvchi bo'lmasa, Xodimdan qidiramiz
                if not student:
                    employee = Employee.objects.filter(school=school, hikvision_id=hik_id).first()

                # Hech kim topilmasa -> o'tkazib yuboramiz
                if not student and not employee: continue

                # 3. Log yozamiz
                obj, created = DailyAttendance.objects.get_or_create(
                    student=student,
                    employee=employee,
                    date=dt.date()
                )

                # Faqat birinchi kelgan vaqtini yozamiz (yoki yangilaymiz)
                if created:
                    obj.arrived_at = dt.time()
                    obj.save()
                    saved += 1
                else:
                    # Agar ketish vaqti bo'lsa (keyinroq mantiq qo'shish mumkin)
                    if obj.arrived_at and dt.time() > obj.arrived_at:
                        obj.left_at = dt.time()
                        obj.save()
            except Exception as e:
                print(f"Log Error: {e}")

        return Response({"status": "ok", "saved": saved})


from itertools import chain  # Ro'yxatlarni birlashtirish uchun


class GetNewUsersAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        api_key = request.headers.get('X-School-Key')
        school = get_object_or_404(School, api_key=api_key, is_active=True)

        school.last_activity = timezone.now()
        school.save()

        # 1. Yuklanmagan O'quvchilar
        students = Student.objects.filter(school=school, is_synced=False)[:10]

        # 2. Yuklanmagan Xodimlar
        employees = Employee.objects.filter(school=school, is_synced=False)[:10]

        data = []

        # Ikkala ro'yxatni birlashtirib aylanamiz
        for u in chain(students, employees):
            photo_url = request.build_absolute_uri(u.photo.url) if u.photo else None

            data.append({
                # Bizga endi ID emas, Hikvision ID muhimroq (chunki DB ID takrorlanishi mumkin)
                "db_id": u.id,
                "type": "student" if isinstance(u, Student) else "employee",  # Kimligini bilib olish uchun
                "full_name": u.full_name,
                "hikvision_id": u.hikvision_id,
                "photo_url": photo_url
            })

        return Response({"users": data})


class ConfirmUserSyncAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            api_key = request.headers.get('X-School-Key')
            school = get_object_or_404(School, api_key=api_key)

            # Agent endi bizga hikvision_id larni yuboradi deb kelishamiz
            synced_hik_ids = request.data.get('synced_ids', [])

            if synced_hik_ids:
                # 1. Studentlarni update qilamiz
                Student.objects.filter(school=school, hikvision_id__in=synced_hik_ids).update(is_synced=True)

                # 2. Employeelarni update qilamiz
                Employee.objects.filter(school=school, hikvision_id__in=synced_hik_ids).update(is_synced=True)

                print(f"✅ Sync tasdiqlandi. IDs: {synced_hik_ids}")

            return Response({"status": "ok"})

        except Exception as e:
            return Response({"status": "error", "msg": str(e)}, status=400)