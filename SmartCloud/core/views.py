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
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Student, Parent


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

# --- 1. LIST (RO'YXAT) ---
@login_required
def student_list(request):
    # Userning maktabini olamiz
    school = request.user.profile.school

    # Qidiruv logikasi
    query = request.GET.get('q', '')
    students = Student.objects.filter(school=school).order_by('classroom_name', 'full_name')

    if query:
        students = students.filter(
            Q(full_name__icontains=query) |
            Q(classroom_name__icontains=query) |
            Q(hikvision_id__icontains=query)
        )

    return render(request, 'core/student_list.html', {'students': students, 'query': query})


# --- 2. CREATE (QO'SHISH) ---
@login_required
def student_create(request):
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save(commit=False)
            student.school = request.user.profile.school  # Xavfsizlik: Maktabni majburiy bog'laymiz

            # Parent Logikasi
            p_phone = form.cleaned_data.get('parent_phone')
            p_name = form.cleaned_data.get('parent_name')

            if p_phone:
                clean_phone = p_phone.replace(" ", "").replace("+", "")
                parent, _ = Parent.objects.get_or_create(
                    phone=clean_phone,
                    defaults={'full_name': p_name if p_name else "Noma'lum"}
                )
                student.parent = parent

            student.save()
            messages.success(request, f"{student.full_name} qo'shildi! ID: {student.hikvision_id}")
            return redirect('student_list')
    else:
        form = StudentForm()

    return render(request, 'core/student_form.html', {'form': form, 'title': "O'quvchi Qo'shish"})


# --- 3. EDIT (TAHRIRLASH) ---
@login_required
def student_edit(request, pk):
    school = request.user.profile.school
    # get_object_or_404 da school=school deyish shart (Birov birovni o'quvchisini o'zgartirolmasligi uchun)
    student = get_object_or_404(Student, pk=pk, school=school)

    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            student = form.save(commit=False)

            # Parent update
            p_phone = form.cleaned_data.get('parent_phone')
            if p_phone:
                clean_phone = p_phone.replace(" ", "").replace("+", "")
                parent, _ = Parent.objects.get_or_create(phone=clean_phone)
                student.parent = parent

            # Agar rasm o'zgarsa -> sync o'chadi
            if 'photo' in form.changed_data:
                student.is_synced = False

            student.save()
            messages.success(request, "Ma'lumot yangilandi!")
            return redirect('student_list')
    else:
        # Formani ochganda eski parent telefonini ko'rsatish
        initial_data = {}
        if student.parent:
            initial_data = {'parent_phone': student.parent.phone, 'parent_name': student.parent.full_name}
        form = StudentForm(instance=student, initial=initial_data)

    return render(request, 'core/student_form.html', {'form': form, 'title': "Tahrirlash", 'student': student})


# --- 4. DELETE (O'CHIRISH) ---
@login_required
def student_delete(request, pk):
    school = request.user.profile.school
    student = get_object_or_404(Student, pk=pk, school=school)

    if request.method == 'POST':
        student.delete()
        messages.warning(request, "O'quvchi o'chirildi!")
        return redirect('student_list')

    return render(request, 'core/student_delete.html', {'student': student})
