from django.utils import timezone
from home.models import Task
from home.scheduler.recurrence import is_task_due_for_recurrence
from .task_copy import copy_task

def run_recurring_task_job():
    """
    Daily job:
    - Finds recurring tasks
    - Creates new task if due
    - Updates last_auto_created_at
    """

    # tasks = Task.objects.filter(recurrence_period__isnull=False)
    tasks = Task.objects.filter(is_recurring=True)
    for task in tasks:
        if is_task_due_for_recurrence(task):
            copy_task(task, is_auto=True)
            task.last_auto_created_at = timezone.now()
            task.save(update_fields=["last_auto_created_at"])