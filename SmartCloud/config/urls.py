from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from core.api_views import ReceiveLogsAPI, ConfirmUserSyncAPI, GetNewUsersAPI



urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('', include('staff.urls')),
    path('', include('attendance.urls')),
    path('api/upload-logs/', ReceiveLogsAPI.as_view(), name='receive-logs'),
    path('api/get-users/', GetNewUsersAPI.as_view()),
    path('api/confirm-sync/', ConfirmUserSyncAPI.as_view()),
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)