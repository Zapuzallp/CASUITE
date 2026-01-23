from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Employee,Task,TaskRecurrence
from .scheduler.recurrence import get_next_recurrence_date


@receiver(post_save, sender=User)
def create_employee_profile(sender, instance, created, **kwargs):
    if created:
        Employee.objects.create(user=instance)


from django.db.models.signals import pre_save
from django.dispatch import receiver

from home.models import Client
from home.utils import generate_file_number


@receiver(pre_save, sender=Client)
def client_file_number_handler(sender, instance, **kwargs):
    """
    Generate file number:
    - on first save
    - OR when office_location changes
    """

    # New client (no PK yet)
    if not instance.pk:
        if instance.office_location:
            instance.file_number = generate_file_number(instance.office_location)
        return

    # Existing client → check office_location change
    old_instance = Client.objects.filter(pk=instance.pk).first()

    if not old_instance:
        return

    office_changed = old_instance.office_location != instance.office_location

    if office_changed and instance.office_location:
        instance.file_number = generate_file_number(instance.office_location)


@receiver(post_save, sender=Task)
def sync_task_recurrence(sender, instance, created, **kwargs):
    # NON-RECURRING → delete recurrence
    if instance.recurrence_period == 'None':
        TaskRecurrence.objects.filter(task=instance).delete()
        return
    #Create or update recurrence
    recurrence, _ = TaskRecurrence.objects.update_or_create(
        task=instance,
        defaults={
            "created_at": instance.created_at,
            "last_auto_created_at": instance.last_auto_created_at,
            "recurrence_period": instance.recurrence_period,
            "is_recurring": instance.is_recurring,
        }
    )
    #Set next_run_at ONLY ONCE
    if recurrence.next_run_at is None:
        recurrence.next_run_at = get_next_recurrence_date(recurrence)
        recurrence.save(update_fields=["next_run_at"])
