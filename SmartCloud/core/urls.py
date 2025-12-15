from django.urls import path
from . import views 



urlpatterns = [
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('', views.dashboard, name='dashboard'), 
    path('student-list/', views.student_edit, name='student_list'),


]       