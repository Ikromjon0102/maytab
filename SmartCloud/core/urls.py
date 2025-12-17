from django.urls import path
from . import views
from . import api_views # API uchun

urlpatterns = [
    # --- AUTH & DASHBOARD ---
    path('', views.dashboard, name='dashboard'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),

    # --- STUDENT CRUD ---
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.student_create, name='student_create'),
    path('students/<int:pk>/edit/', views.student_edit, name='student_edit'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'), # Yangi

    # --- CLASSROOM (SINF) CRUD ---
    path('classrooms/', views.classroom_list, name='classroom_list'),
    path('classrooms/add/', views.classroom_create, name='classroom_create'),
    # Edit/Delete keyinchalik qo'shilishi mumkin

    # --- SHIFT (SMENA) CRUD ---
    path('shifts/', views.shift_list, name='shift_list'),
    path('shifts/add/', views.shift_create, name='shift_create'),

    # --- API (AGENT UCHUN) ---
    path('api/upload-logs/', api_views.ReceiveLogsAPI.as_view()),
    path('api/get-users/', api_views.GetNewUsersAPI.as_view()),
    path('api/confirm-sync/', api_views.ConfirmUserSyncAPI.as_view()),
]