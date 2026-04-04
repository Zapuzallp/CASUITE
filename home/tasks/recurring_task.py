from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User
from home.models import Task, TaskRecurrence, Notification
from home.scheduler.recurrence import get_next_recurrence_date
from .task_copy import copy_task
import logging

logger = logging.getLogger(__name__)


def send_recurrence_notification(original_task, new_task, success=True):
    """
    Send notifications to creator and superusers about recurring task creation.
    
    Args:
        original_task: The original recurring task
        new_task: The newly created task (or None if failed)
        success: Whether the task creation was successful
    """
    # Get recipients: creator + all superusers
    recipients = set()
    
    if original_task.created_by:
        recipients.add(original_task.created_by)
    
    superusers = User.objects.filter(is_superuser=True)
    recipients.update(superusers)
    
    # Prepare notification content
    if success:
        title = f"Recurring Task Created: {new_task.task_title}"
        message = (
            f"A new recurring task has been automatically created.\n\n"
            f"Task: {new_task.task_title}\n"
            f"Client: {new_task.client.client_name}\n"
            f"Service: {new_task.service_type}\n"
            f"Priority: {new_task.priority}\n"
            f"Status: {new_task.status}"
        )
        tag = 'success'
        target_url = f"/tasks/{new_task.id}/"
    else:
        title = f"Recurring Task Creation Failed: {original_task.task_title}"
        message = (
            f"Failed to create recurring task automatically.\n\n"
            f"Original Task: {original_task.task_title}\n"
            f"Client: {original_task.client.client_name}\n"
            f"Please check the task configuration."
        )
        tag = 'error'
        target_url = f"/tasks/{original_task.id}/"
    
    # Create notifications for all recipients
    for user in recipients:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            tag=tag,
            target_url=target_url
        )


def run_recurring_task_job():
    """
    Scheduler job:
    - Scan TaskRecurrence only
    - Use next_run_at as source of truth
    - Create ALL missed recurring tasks
    - Advance next_run_at deterministically
    - Send notifications on success/failure
    """
    now = timezone.now()
    
    logger.info(f"Starting recurring task job at {now}")

    recurrences = (
        TaskRecurrence.objects
        .filter(
            is_recurring=True,
            next_run_at__isnull=False,
            next_run_at__lte=now,
        )
        .select_related("task", "task__client", "task__created_by")
    )
    
    total_created = 0
    total_failed = 0

    for recurrence in recurrences:
        try:
            with transaction.atomic():
                tasks_created = 0
                
                while recurrence.next_run_at <= now:
                    try:
                        # 1️⃣ Create task for this expected occurrence
                        new_task = copy_task(
                            recurrence.task,
                            is_auto=True,
                            next_due_date=recurrence.next_run_at,
                        )
                        
                        # 2️⃣ Track actual creation timestamp
                        created_at = timezone.now()
                        recurrence.last_auto_created_at = created_at
                        recurrence.task.last_auto_created_at = created_at
                        
                        # 3️⃣ Move EXPECTED schedule forward
                        recurrence.next_run_at = get_next_recurrence_date(recurrence)
                        
                        tasks_created += 1
                        
                        # Send success notification
                        send_recurrence_notification(recurrence.task, new_task, success=True)
                        
                        logger.info(
                            f"Created recurring task: {new_task.task_title} "
                            f"(ID: {new_task.id}) for client {new_task.client.client_name}"
                        )
                        
                    except Exception as task_error:
                        logger.error(
                            f"Failed to create recurring task for {recurrence.task.task_title}: {task_error}",
                            exc_info=True
                        )
                        # Send failure notification
                        send_recurrence_notification(recurrence.task, None, success=False)
                        total_failed += 1
                        # Move schedule forward even on failure to avoid infinite retry
                        recurrence.next_run_at = get_next_recurrence_date(recurrence)
                
                # 4️⃣ Persist once per recurrence
                recurrence.save(update_fields=[
                    "last_auto_created_at",
                    "next_run_at",
                ])
                recurrence.task.save(update_fields=[
                    "last_auto_created_at",
                ])
                
                total_created += tasks_created
                
        except Exception as e:
            logger.error(
                f"Failed to process recurrence for task {recurrence.task.id}: {e}",
                exc_info=True
            )
            total_failed += 1
    
    logger.info(
        f"Recurring task job completed. Created: {total_created}, Failed: {total_failed}"
    )
    
    return {
        'created': total_created,
        'failed': total_failed
    }