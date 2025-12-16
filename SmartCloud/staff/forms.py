from django import forms
from .models import Employee

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['full_name', 'phone', 'photo', 'position_type',
                  'start_time', 'end_time', # Vaqt
                  'teaching_hours', 'pedagogical_load', 'base_salary','addition_hours'] # Yuklama
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'teaching_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'pedagogical_load': forms.NumberInput(attrs={'class': 'form-control'}),
            'addition_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'base_salary': forms.NumberInput(attrs={'class': 'form-control'}),
            'position_type': forms.Select(attrs={'class': 'form-select'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }