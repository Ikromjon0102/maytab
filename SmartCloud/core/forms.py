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
        fields = ['full_name', 'classroom_name', 'photo'] # ID va School avtomat
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            # 'classroom_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '5-A'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }