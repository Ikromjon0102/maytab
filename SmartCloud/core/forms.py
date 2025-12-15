from django import forms
from .models import Student

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        # 'hikvision_id' ni BU YERDAN OLIB TASHLANG
        fields = ['full_name', 'classroom_name', 'photo'] 
        
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Valiyev Alijon'}),
            'classroom_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '5-A'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }