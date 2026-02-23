from django.db.models.signals import pre_save
from django.dispatch import receiver
from home.models import Attendance
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

from django.db.models import Sum, Q
from decimal import Decimal

from home.models import Payment, Invoice


@receiver(post_save, sender=Payment)
def update_invoice_status_on_payment_change(sender, instance, **kwargs):
    invoice = instance.invoice

    # Calculate totals dynamically
    total_amount = invoice.items.aggregate(
        total=Sum('net_total')
    )['total'] or Decimal('0.00')

    total_paid = invoice.payments.filter(
        payment_status='PAID',
        approval_status='APPROVED'
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    # Decide status
    if total_amount > 0 and total_paid >= total_amount:
        new_status = 'PAID'
    elif total_paid > 0:
        new_status = 'PARTIALLY_PAID'
    else:
        new_status = 'OPEN'

    # Avoid unnecessary DB writes
    if invoice.invoice_status != new_status:
        invoice.invoice_status = new_status
        invoice.save(update_fields=['invoice_status'])
        
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
