from django.shortcuts import render
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import Student
from staff.models import Employee
from .models import DailyAttendance


def attendance_report(request):
    school = request.user.profile.school

    # 1. Sana filtri (Default: Bugun)
    date_str = request.GET.get('date', timezone.now().strftime('%Y-%m-%d'))
    selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()

    # 2. Kimlarni ko'rsatamiz? (Tab: 'student' yoki 'staff')
    tab = request.GET.get('tab', 'student')

    context = {
        'selected_date': date_str,
        'tab': tab,
        'school': school
    }

    if tab == 'staff':
        # Xodimlar Davomati
        employees = Employee.objects.filter(school=school)
        report = []
        for emp in employees:
            log = DailyAttendance.objects.filter(employee=emp, date=selected_date).first()
            status = 'absent'
            arrival = '-'
            left = '-'

            if log:
                status = 'present'
                arrival = log.arrived_at.strftime('%H:%M') if log.arrived_at else '-'
                left = log.left_at.strftime('%H:%M') if log.left_at else '-'

                # Kechikishni tekshirish
                if log.arrived_at and emp.start_time:
                    if log.arrived_at > emp.start_time:
                        status = 'late'

            report.append({
                'name': emp.full_name,
                'id': emp.hikvision_id,
                'status': status,
                'arrival': arrival,
                'left': left,
                'plan_start': emp.start_time
            })
        context['report_data'] = report

    else:
        # O'quvchilar Davomati
        students = Student.objects.filter(school=school).select_related('parent')
        report = []
        for stu in students:
            log = DailyAttendance.objects.filter(student=stu, date=selected_date).first()
            status = 'absent'
            arrival = '-'

            if log:
                status = 'present'
                arrival = log.arrived_at.strftime('%H:%M') if log.arrived_at else '-'

            report.append({
                'name': stu.full_name,
                'class': stu.classroom,
                'status': status,
                'arrival': arrival
            })
        context['report_data'] = report

    return render(request, 'attendance/report.html', context)