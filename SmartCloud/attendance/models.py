from django.db import models

class DailyAttendance(models.Model):
    date = models.DateField()
    arrived_at = models.TimeField(null=True, blank=True)
    left_at = models.TimeField(null=True, blank=True)
    
    student = models.ForeignKey('core.Student', on_delete=models.CASCADE, null=True, blank=True)
    employee = models.ForeignKey('staff.Employee', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ['date', 'student', 'employee']