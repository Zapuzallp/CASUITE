from django.db.models.signals import pre_save
from django.dispatch import receiver
from home.models import Attendance

@receiver(pre_save, sender=Attendance)
def update_attendance_remark(sender, instance, **kwargs):
    """Update remark when admin changes status to full_day or half_day"""
    if instance.pk:
        try:
            old_instance = Attendance.objects.get(pk=instance.pk)
            old_status = old_instance.status
            
            # Check if status changed to full_day or half_day
            if old_status != instance.status:
                if instance.status == 'full_day':
                    if instance.remark:
                        if "Marked as full-day present" not in instance.remark:
                            instance.remark += "; Marked as full-day present"
                    else:
                        instance.remark = "Marked as full-day present"
                elif instance.status == 'half_day':
                    if instance.remark:
                        if "Marked as half-day present" not in instance.remark:
                            instance.remark += "; Marked as half-day present"
                    else:
                        instance.remark = "Marked as half-day present"
        except Attendance.DoesNotExist:
            pass
