from .models import Student, Parent, Classroom
from .forms import StudentForm
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import School, Student
from attendance.models import DailyAttendance
from datetime import date
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm

def student_create(request):
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        
        # HTML dan kelgan ota-ona ma'lumotlarini olamiz
        p_phone = request.POST.get('parent_phone')
        p_name = request.POST.get('parent_name')

        if form.is_valid():
            student = form.save(commit=False)
            
            # --- OTA-ONANI ULASTIRISH MANTIG'I ---
            if p_phone:
                # Raqamni tozalash (bo'sh joylarni olib tashlash)
                clean_phone = p_phone.replace(" ", "").replace("-", "")
                
                # 1. Bazadan qidiramiz yoki yaratamiz
                # get_or_create: (object, created_boolean) qaytaradi
                parent, created = Parent.objects.get_or_create(
                    phone=clean_phone,
                    defaults={'full_name': p_name if p_name else "Noma'lum"}
                )
                
                # 2. Agar ota-ona oldin bor bo'lsa, lekin ismi kiritilmagan bo'lsa -> ismini yangilaymiz
                if not created and p_name:
                    # Ixtiyoriy: Agar eski ism "Noma'lum" bo'lsa yoki yangi ism kiritilsa yangilash
                    parent.full_name = p_name
                    parent.save()
                
                # 3. Studentga bog'laymiz
                student.parent = parent
            
            student.save()
            messages.success(request, "O'quvchi saqlandi!")
            return redirect('student_list')
    else:
        form = StudentForm()
    
    return render(request, 'core/student_form.html', {'form': form, 'title': "O'quvchi qo'shish"})

def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        
        p_phone = request.POST.get('parent_phone')
        p_name = request.POST.get('parent_name')

        if form.is_valid():
            student = form.save(commit=False)
            
            if p_phone:
                clean_phone = p_phone.replace(" ", "")
                parent, created = Parent.objects.get_or_create(
                    phone=clean_phone,
                    defaults={'full_name': p_name}
                )
                if not created and p_name:
                    parent.full_name = p_name
                    parent.save()
                student.parent = parent
            
            # Rasm o'zgargan bo'lsa sync statusni o'chirish
            if 'photo' in form.changed_data:
                student.is_synced = False
                
            student.save()
            messages.success(request, "Yangilandi!")
            return redirect('student_list')
    else:
        form = StudentForm(instance=student)
    
    return render(request, 'core/student_form.html', {'form': form, 'title': "Tahrirlash", 'student': student})



@login_required
def dashboard(request):
    today = date.today()

    # 1. AGAR RAYONO (Superuser) BO'LSA
    if request.user.is_superuser:
        total_schools = School.objects.filter(is_active=True).count()
        total_students = Student.objects.count()
        
        # Bugungi umumiy davomat
        present_count = DailyAttendance.objects.filter(date=today).count()
        
        context = {
            'total_schools': total_schools,
            'total_students': total_students,
            'present_today': present_count,
            'schools': School.objects.all() # Jadval uchun
        }
        return render(request, 'dashboard/rayono.html', context)

    # 2. AGAR MAKTAB DIREKTORI BO'LSA
    else:
        # User qaysi maktabga tegishli ekanini topamiz (Profile orqali)
        # school = request.user.profile.school (deb tasavvur qilamiz)
        try:
            school = request.user.profile.school
        except:
            school = None
        if not school:
            return render(request, 'dashboard/empty.html', {'message': "Sizga hali maktab biriktirilmagan!"})

        # Agar maktab topilgan bo'lsa
        total_students = Student.objects.filter(school=school).count()
        present_count = DailyAttendance.objects.filter(
            student__school=school, date=today
        ).count()
        
        absent_count = total_students - present_count

        context = {
            'school': school,
            'total_students': total_students,
            'present': present_count,
            'absent': absent_count,
            'attendance_percent': int((present_count/total_students)*100) if total_students > 0 else 0
        }
        return render(request, 'dashboard/school.html', context)
    


def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Muvaffaqiyatli kirgandan so'ng Dashboardga otamiz
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    
    return render(request, 'login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('user_login')