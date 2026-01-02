from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Employee


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
