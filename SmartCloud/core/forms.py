from django import forms
from .models import Student

class StudentForm(forms.ModelForm):
    # Modelda yo'q, lekin formaga kerak bo'lgan maydonlar
    parent_phone = forms.CharField(label="Ota-ona Telefoni", required=False,
                                 widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+998...'}))
    parent_name = forms.CharField(label="Ota-ona Ismi", required=False,
                                widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Student
        fields = ['full_name', 'classroom', 'photo'] # ID va School avtomat
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            # 'classroom_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '5-A'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }

from .models import Classroom, Shift
from staff.models import Employee

class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ['name', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ClassroomForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ['name', 'head_teacher', 'shift']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'head_teacher': forms.Select(attrs={'class': 'form-select'}),
            'shift': forms.Select(attrs={'class': 'form-select'}),
        }

    # "Maktab" filteri (Birovning o'qituvchisi chiqib qolmasligi uchun)
    def __init__(self, school, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['head_teacher'].queryset = Employee.objects.filter(school=school, position_type='teacher')
        self.fields['shift'].queryset = Shift.objects.filter(school=school)

