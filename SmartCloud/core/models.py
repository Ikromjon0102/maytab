import uuid
import random
from django.db import models
import sys
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import FileExtensionValidator
from PIL import Image  
from .utils import generate_hikvision_id
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

class School(models.Model):
    name = models.CharField(max_length=255, verbose_name="Maktab nomi")
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_active = models.BooleanField(default=True)

    # YANGI MAYDON: Agent oxirgi marta qachon "signal" bergan?
    last_activity = models.DateTimeField(null=True, blank=True, verbose_name="Oxirgi aloqa")

    def __str__(self):
        return self.name

    # AQLLI XUSUSIYAT (Property)
    @property
    def is_online(self):
        if not self.last_activity:
            return False

        # Hozirgi vaqt
        now = timezone.now()

        # Farqni hisoblaymiz
        diff = now - self.last_activity

        # Agar farq 5 daqiqadan (300 soniya) kam bo'lsa -> Online
        return diff.total_seconds() < 600

class Shift(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=50) 
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    def __str__(self): return f"{self.name} ({self.school.name})"

class Parent(models.Model):
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True) # Unikal (Global)
    telegram_id = models.CharField(max_length=50, blank=True, null=True)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)
    connect_code = models.CharField(max_length=6, blank=True, null=True, unique=True)

    def save(self, *args, **kwargs):
        if not self.connect_code:
            self.connect_code = str(random.randint(100000, 999999))
        super().save(*args, **kwargs)

    def __str__(self): return self.full_name

class Classroom(models.Model):
    name = models.CharField(max_length=50)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    lesson_time = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name="lesson_time", null=True, blank=True)
    
    def __str__(self): return self.name 


class Student(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, related_name="students")
    full_name = models.CharField(max_length=255)
    hikvision_id = models.CharField(
        max_length=20, 
        editable=False, # Admin panelda o'zgartirib bo'lmaydi (READONLY)
        verbose_name="Terminal ID"
    )
    parent = models.ForeignKey('Parent', on_delete=models.SET_NULL, null=True, related_name="children")
    
    # Rasm maydoni
    photo = models.ImageField(
        upload_to='students/', 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        verbose_name="Yuz rasmi"
    )
    
    classroom_name = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name="classrooms")
    # classroom_name = models.CharField(max_length=50, blank=True, null=True)
    is_synced = models.BooleanField(default=False) # Terminalga yuklanganmi?

    class Meta:
        unique_together = ['school', 'hikvision_id']

    def __str__(self): 
        return f"{self.full_name} ({self.school.name})"

    def save(self, *args, **kwargs):
        # 1. ID generatsiya (faqat yangi yaratilayotganda va ID bo'sh bo'lsa)
        if not self.hikvision_id:
            # O'quvchilar 10000 dan boshlanadi
            self.hikvision_id = generate_hikvision_id(self.school, Student, start_range=10000)
            
        if self.photo:
            # 1. Rasmni ochamiz
            img = Image.open(self.photo)
            
            # 2. Formatni to'g'irlash (PNG -> JPG)
            # Hikvision PNG bilan yaxshi chiqishmaydi, RGB (JPG) ga o'tkazamiz
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 3. O'lchamni kichraytirish (Resize)
            # Terminal ekraniga 600-800px yetib ortadi. 4K rasm shart emas.
            if img.height > 800 or img.width > 800:
                output_size = (800, 800)
                img.thumbnail(output_size)

            # 4. Siqish (Compression Loop)
            output_io = BytesIO()
            quality = 90 # Boshlang'ich sifat
            
            # Avval xotiraga yozib ko'ramiz
            img.save(output_io, format='JPEG', quality=quality)
            
            # Agar rasm 150KB dan katta bo'lsa, sifatni tushiraveramiz
            # (200KB limit uchun 150KB xavfsiz chegara)
            while output_io.tell() > 150 * 1024 and quality > 10:
                output_io.seek(0)
                output_io.truncate()
                quality -= 10
                img.save(output_io, format='JPEG', quality=quality)

            # 5. Yangi siqilgan rasmni faylga aylantiramiz
            new_image = InMemoryUploadedFile(
                output_io,
                'ImageField',
                f"{self.photo.name.split('.')[0]}.jpg", # Nomini saqlab, ext ni jpg qilamiz
                'image/jpeg',
                sys.getsizeof(output_io),
                None
            )
            
            # Eski fayl o'rniga yangisini qo'yamiz
            self.photo = new_image

        # Agar rasm o'zgargan bo'lsa, uni terminalga qayta yuklash kerak
        # (Bu mantiqni views da ham nazorat qilsa bo'ladi, lekin bu yerda ham is_synced=False qilish foydali)
        # self.is_synced = False 

        super().save(*args, **kwargs)
    

class Holiday(models.Model):
    name = models.CharField(max_length=100, verbose_name="Bayram nomi")
    date = models.DateField(verbose_name="Sana")
    is_recurring = models.BooleanField(default=True, verbose_name="Har yili takrorlanadimi?")

    def __str__(self):
        return f"{self.date.strftime('%d-%m')} - {self.name}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Maktab")
    
    # Qo'shimcha (ixtiyoriy)
    phone = models.CharField(max_length=20, blank=True, null=True)
    telegram_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.school.name if self.school else 'RayONO'})"

# --- SIGNAL: User yaratilganda avtomatik Profile ham yaratish ---
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


