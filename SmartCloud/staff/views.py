from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
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

# ... importlar ...
from .models import Employee
from .forms import EmployeeForm

@login_required
def employee_list(request):
    school = request.user.profile.school
    employees = Employee.objects.filter(school=school)
    return render(request, 'staff/employee_list.html', {'employees': employees})

@login_required
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.school = request.user.profile.school
            emp.save()
            messages.success(request, "Xodim qo'shildi")
            return redirect('employee_list')
    else:
        form = EmployeeForm()
    return render(request, 'staff/employee_form.html', {'form': form, 'title': "Xodim Qo'shish"})

# Edit va Delete ni Studentdagi kabi o'zingiz yozasiz (Copy-Paste va Modelni o'zgartirish)


