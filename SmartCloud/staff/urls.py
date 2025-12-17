from django.urls import path
from . import views

urlpatterns = [
    # --- EMPLOYEE CRUD ---
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/add/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),   # Yangi
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'), # Yangi

    # --- PAYROLL (OYLIK) ---
    path('payroll/', views.payroll_report, name='payroll_report'),
]