from django.contrib import admin

from . import models

class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'api_key', 'is_active')

admin.site.register(models.School, SchoolAdmin)


admin.site.register(models.Shift)
admin.site.register(models.Parent)
admin.site.register(models.UserProfile)


@admin.register(models.Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name','hikvision_id' ,'is_synced',)
    readonly_fields = ['hikvision_id']
