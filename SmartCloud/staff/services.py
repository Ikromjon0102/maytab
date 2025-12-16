import calendar
from datetime import date, timedelta
from django.db.models import Count
from core.models import Holiday
from attendance.models import DailyAttendance
from .models import Employee

class PayrollCalculator:
    def __init__(self, school, year, month):
        self.school = school
        self.year = year
        self.month = month
        # Oyning oxirgi kuni (masalan 30 yoki 31)
        self.days_in_month = calendar.monthrange(year, month)[1]

    def get_total_work_days(self, work_days_per_week=6):
        """
        Shu oyda jami necha kun ish bo'lishi kerakligini hisoblaydi 
        (Yakshanba va Bayramlarni chiqarib tashlaydi)
        """
        total_days = 0
        holidays = self._get_holidays()

        for day in range(1, self.days_in_month + 1):
            current_date = date(self.year, self.month, day)
            weekday = current_date.weekday() # 0=Dushanba, 6=Yakshanba

            # 1. Yakshanba bo'lsa o'tkazamiz
            if weekday == 6: 
                continue
            
            # 2. Agar 5 kunlik ish bo'lsa, Shanbani (5) ham o'tkazamiz
            if work_days_per_week == 5 and weekday == 5:
                continue

            # 3. Bayram bo'lsa o'tkazamiz
            if self._is_holiday(current_date, holidays):
                continue
            
            total_days += 1
            
        return total_days

    def _get_holidays(self):
        # Barcha bayramlarni olamiz
        return Holiday.objects.all()

    def _is_holiday(self, check_date, holidays):
        for h in holidays:
            # Agar har yili takrorlansa (faqat oy va kunni tekshiramiz)
            if h.is_recurring:
                if h.date.month == check_date.month and h.date.day == check_date.day:
                    return True
            # Agar takrorlanmasa (to'liq sanani tekshiramiz)
            else:
                if h.date == check_date:
                    return True
        return False

    def calculate_all(self):
        """Barcha xodimlar uchun hisobot tayyorlaydi"""
        employees = Employee.objects.filter(school=self.school, is_active=True)
        report = []

        for emp in employees:
            # 1. Shu oy uchun umumiy ish kunlari (Plan)
            plan_days = self.get_total_work_days(work_days_per_week=6) # Standart 6 kunlik deb oldim
            
            if plan_days == 0:
                report.append(self._empty_structure(emp, "Ish kuni yo'q"))
                continue

            # 2. Xodim necha kun kelgan? (Fact)
            # Faqat shu oy va shu xodim uchun
            attended_days = DailyAttendance.objects.filter(
                employee=emp,
                date__year=self.year,
                date__month=self.month
            ).count()

            # 3. Formulani qo'llaymiz
            # Haftalik soat * 4.3 (O'rtacha oy haftasi)
            weekly_load = emp.teaching_hours + emp.pedagogical_load + emp.addition_hours
            monthly_plan_hours = weekly_load * 4.3

            # 1 kunga to'g'ri keladigan o'rtacha soat
            daily_avg_hour = monthly_plan_hours / plan_days
            
            # Haqiqiy ishlagan soati
            actual_worked_hours = daily_avg_hour * attended_days

            # 4. Pullik hisob (Soatbay)
            # base_rate = 1 soatlik narx
            hourly_rate = float(emp.base_salary) 
            
            # Toifa va Sertifikat ustamalari (ixtiyoriy, agar kerak bo'lsa qo'shasiz)
            # if emp.category == 'oliy': hourly_rate *= 1.5 ...
            
            total_salary = actual_worked_hours * hourly_rate

            report.append({
                "full_name": emp.full_name,
                "position": emp.get_position_type_display(),
                "plan_days": plan_days,
                "fact_days": attended_days,
                "plan_hours": round(monthly_plan_hours, 1),
                "fact_hours": round(actual_worked_hours, 1),
                "hourly_rate": f"{hourly_rate:,.0f}",
                "total_salary": f"{total_salary:,.0f}"
            })
        
        return report

    def _empty_structure(self, emp, msg):
        return {
            "full_name": emp.full_name,
            "position": emp.get_position_type_display(),
            "note": msg,
            "total_salary": 0
        }