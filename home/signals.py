from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Employee
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from home.models import Notification
from home.services.webpushr import send_webpush

@receiver(post_save, sender=User)
def create_employee_profile(sender, instance, created, **kwargs):
    if created:
        Employee.objects.create(user=instance)

@receiver(post_save, sender=Notification)
def send_push_on_notification_create(sender, instance, created, **kwargs):
    if not created:
        return

    # Optional: only send push for unread notifications
    if instance.is_read:
        return
    BASE_URL = "http://127.0.0.1:8000"
    send_webpush(
        title=instance.title,
        message=instance.message,
        url=BASE_URL + (instance.target_url or "/")
    )
