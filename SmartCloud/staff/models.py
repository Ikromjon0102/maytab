from django.db import models
from core.models import School
from core.utils import generate_hikvision_id
from core.models import Student

class Employee(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="employees")
    full_name = models.CharField(max_length=255)
    hikvision_id = models.CharField(
        max_length=20, 
        editable=False, 
        verbose_name="Terminal ID"
    )
    phone = models.CharField(max_length=20)
    photo = models.ImageField(upload_to='staff/', blank=True, null=True)
    
    # Lavozim
    POSITION_CHOICES = [('teacher', "O'qituvchi"), ('admin', "Ma'muriyat")]
    position_type = models.CharField(max_length=20, choices=POSITION_CHOICES, default='teacher')
    
    # Oylik (Payroll)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Stavka")
    teaching_hours = models.FloatField(default=0, verbose_name="Dars soati")
    
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['school', 'hikvision_id']


    def __str__(self): 
        return self.full_name
    
    def save(self, *args, **kwargs):
        if not self.hikvision_id:
            # Xodimlar 90000 dan boshlanadi
            new_id = generate_hikvision_id(self.school, Employee, start_range=90000)
            
            # PARANOYA TEKSHIRUVI (Ikkita qatlamli himoya):
            # Mabodo 100000 ga yetib borib, Student ID bilan to'qnashib ketmasligi uchun
            # Studentlar ichida ham bunday ID yo'qligini tekshiramiz.
            while Student.objects.filter(school=self.school, hikvision_id=new_id).exists():
                new_id = str(int(new_id) + 1)
                
            self.hikvision_id = new_id

        super().save(*args, **kwargs)