from django.shortcuts import render
from datetime import datetime
from .services import PayrollCalculator

def payroll_report(request):
    # Hozirgi oy yoki tanlangan oy
    today = datetime.now()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # Maktabni aniqlash (Login qilgan userga qarab)
    # Hozircha statik 1-maktab deb olamiz
    from core.models import School
    school = School.objects.first() 

    calculator = PayrollCalculator(school, year, month)
    report_data = calculator.calculate_all()
    
    context = {
        'report': report_data,
        'year': year,
        'month': month,
        'month_name': today.strftime('%B')
    }
    return render(request, 'staff/payroll.html', context)


