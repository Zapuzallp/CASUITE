from django.db import transaction
from django.utils import timezone
from home.models import Task, TaskExtendedAttributes,TaskAssignmentStatus

# function for title name of the recurrence task
def build_auto_task_title(original_task, next_due_date):
    base_title = original_task.task_title.replace(' (Copied)', '')
    period = original_task.recurrence_period

    month_label = next_due_date.strftime('%b')
    year = next_due_date.year

    if period == 'Monthly':
        return f"{base_title} - {month_label} {year}"

    if period == 'Quarterly':
        quarter = (next_due_date.month - 1) // 3 + 1
        return f"{base_title} - Q{quarter} {year} ({month_label})"

    if period == 'Yearly':
        return f"{base_title} - {year} ({month_label})"

    # fallback (non-standard recurrence)
    return f"{base_title} - {month_label} {year}"

@transaction.atomic
def copy_task(original_task, created_at= None,created_by=None, is_auto=False,next_due_date=None):
    """
    Deep copy Task + TaskExtendedAttributes
    Used by:
    - Manual copy (is_auto=False)
    - Recurrence scheduler (is_auto=True)
    """
    # If created_at not provided → use current time
    created_at = created_at or timezone.now()
    # Generate title based on copy type
    if is_auto:
        # For auto-recurring tasks, use a cleaner title, and also avoid recurring task
        title = build_auto_task_title(original_task, next_due_date)
        recurrence_period = 'None'
        is_recurring = False
    else:
        title = f"{original_task.task_title} (Copied)"
        recurrence_period = original_task.recurrence_period
        is_recurring = original_task.is_recurring

    new_task = Task.objects.create(
        client=original_task.client,
        created_by=created_by or original_task.created_by,
        service_type=original_task.service_type,
        task_title=title,
        description=original_task.description,
        due_date=None,
        completed_date=None,
        priority=original_task.priority,
        status='Pending',
        agreed_fee=original_task.agreed_fee,
        fee_status='Unbilled',
        created_at=created_at,
        recurrence_period = recurrence_period,
        is_recurring=is_recurring,
    )

    # Copy assignees
    new_task.assignees.set(original_task.assignees.all())

    # Copy extended attributes(if exist)
    try:
        old_ext = original_task.extended_attributes
    except TaskExtendedAttributes.DoesNotExist:
        old_ext = None

    if old_ext:
        data = {
            field.name: getattr(old_ext, field.name)
            for field in old_ext._meta.fields
            if field.name not in ('id', 'task')
        }
        TaskExtendedAttributes.objects.create(task=new_task, **data)

    # Copy workflow sequence (TaskAssignmentStatus)
    sequence_qs = TaskAssignmentStatus.objects.filter(task=original_task).order_by('order')

    for seq in sequence_qs:
        TaskAssignmentStatus.objects.create(
            task=new_task,
            user=seq.user,
            status_context=seq.status_context,
            order=seq.order,
            is_completed=False # IMPORTANT: reset for new task
        )

    return new_task