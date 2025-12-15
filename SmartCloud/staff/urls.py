
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import path
from . import views

urlpatterns = [
    path('payroll/', views.payroll_report, name='payroll_report'),
]