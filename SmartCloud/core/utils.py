from django.db.models import Max
import random

def generate_hikvision_id(school, model_class, start_range=10000):
    """
    Berilgan maktab va model uchun navbatdagi bo'sh ID ni topadi.
    """
    # 1. Shu maktabdagi eng katta ID ni topamiz (faqat raqamlarni hisobga olib)
    # Hikvision ID string bo'lgani uchun uni int qilib sort qilish kerak,
    # lekin SQLite/Postgres da oddiy MAX ishlataveramiz, agar formatimiz 5 xonali bo'lsa.
    
    last_obj = model_class.objects.filter(school=school).order_by('-hikvision_id').first()
    
    if not last_obj:
        return str(start_range)
    
    try:
        last_id = int(last_obj.hikvision_id)
        new_id = last_id + 1
        return str(new_id)
    except ValueError:
        # Agar kimdir qo'lda "AB123" deb yozgan bo'lsa, xatolik chiqmasligi uchun
        return str(start_range + random.randint(1, 999))