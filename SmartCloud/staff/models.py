from django.db import models
from core.models import School
from core.utils import generate_hikvision_id
from core.models import Student, Shift

# from SmartCloud.core.models import Shift


class Employee(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="employees")
    full_name = models.CharField(max_length=255)
    hikvision_id = models.CharField(max_length=20, editable=False)
    employee_id = models.CharField(max_length=50, editable=False)
    phone = models.CharField(max_length=20)
    photo = models.ImageField(upload_to='staff/', blank=True, null=True)

    POSITION_CHOICES = [('teacher', "O'qituvchi"), ('admin', "Ma'muriyat")]
    position_type = models.CharField(max_length=20, choices=POSITION_CHOICES, default='teacher')

    # --- YANGI QISM: ISH VAQTI VA YUKLAMA ---
    start_time = models.TimeField(verbose_name="Ish boshlanishi", default="08:00")
    end_time = models.TimeField(verbose_name="Ish tugashi", default="17:00")

    # 1. O'quv soati (Dars o'tadigan soati)
    teaching_hours = models.FloatField(default=0, verbose_name="O'quv soati")
    # 2. Pedagogik yuklama (Daftar tekshirish, to'garak va h.k.)
    pedagogical_load = models.FloatField(default=0, verbose_name="Pedagogik yuklama")

    addition_hours = models.FloatField(default=0, verbose_name="Qo'shimcha dars soati")

    # 3. Asosiy Stavka summasi (Masalan: 1 soat uchun yoki oylik oklad)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="1 soat narxi")

    is_synced = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['school', 'hikvision_id']


    def __str__(self): 
        return self.full_name

    @property
    def total_weekly_hours(self):
        return self.teaching_hours + self.pedagogical_load + self.addition_hours

    def save(self, *args, **kwargs):
        if not self.hikvision_id:
            from core.models import Student
            new_id = generate_hikvision_id(self.school, Employee, start_range=90000)
            while Student.objects.filter(school=self.school, hikvision_id=new_id).exists():
                new_id = str(int(new_id) + 1)
            self.hikvision_id = new_id
        super().save(*args, **kwargs)
