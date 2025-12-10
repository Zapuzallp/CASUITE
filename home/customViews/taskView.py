import json

from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction

from home.clients.config import TASK_CONFIG, DEFAULT_WORKFLOW_STEPS
from home.forms import TaskForm, TaskExtendedForm
from home.models import Client, TaskComment, Task, TaskExtendedAttributes, TaskDocument, TaskAssignmentStatus
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone

@login_required
def create_task_view(request, client_id):
    client = get_object_or_404(Client, id=client_id)

    # 1. Prepare Client Data for Auto-Population
    client_data_map = {
        'pan_no': client.pan_no,
        'email': client.email,
        'phone': client.phone_number,
        'din_no': client.din_no,
        # Add other client fields you want to auto-fill here
    }

    if request.method == 'POST':
        task_form = TaskForm(request.POST)
        extended_form = TaskExtendedForm(request.POST, request.FILES)

        if task_form.is_valid() and extended_form.is_valid():
            try:
                with transaction.atomic():
                    # Save Task
                    task = task_form.save(commit=False)
                    task.client = client
                    task.created_by = request.user

                    # Auto Title if empty: "GST Return Task"
                    if not task.task_title:
                        task.task_title = f"{task.get_service_type_display()} Task"

                    task.save()

                    # Save Extended Attributes
                    extended = extended_form.save(commit=False)
                    extended.task = task
                    extended.save()

                    messages.success(request, "Task created successfully!")
                    return redirect('client_details', client_id=client.id)
            except Exception as e:
                messages.error(request, f"Error: {e}")
        else:
            messages.error(request, "Please check the form for errors.")
    else:
        task_form = TaskForm()
        extended_form = TaskExtendedForm()

    context = {
        'client': client,
        'task_form': task_form,
        'extended_form': extended_form,

        # Pass Config and Data to Template
        'task_config': TASK_CONFIG,
        'client_data_json': json.dumps(client_data_map, cls=DjangoJSONEncoder)
    }
    return render(request, 'client/create_task.html', context)


@login_required
def task_list_view(request):
    tasks = Task.objects.select_related('client') \
        .prefetch_related('assignees') \
        .order_by('-created_at')

    clients = Client.objects.all().order_by('client_name')

    context = {
        'tasks': tasks,
        'clients': clients,  # Pass to template
        'today': timezone.now().date()
    }
    return render(request, 'client/tasks.html', context)


# ---------------------------------------------------------
# HELPER: Initialize Status for Assignees
# ---------------------------------------------------------
def initialize_step_for_assignees(task):
    """Creates TaskAssignmentStatus rows for all current assignees for the CURRENT task status."""
    for user in task.assignees.all():
        TaskAssignmentStatus.objects.get_or_create(
            task=task,
            user=user,
            status_context=task.status,
            defaults={'is_completed': False}
        )


@login_required
def task_detail_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    # 1. Get Workflow from Config
    config = TASK_CONFIG.get(task.service_type, {})
    workflow_steps = config.get('workflow_steps', DEFAULT_WORKFLOW_STEPS)

    # 2. Get Current Assignee Statuses (Who is pending?)
    assignee_statuses = TaskAssignmentStatus.objects.filter(
        task=task,
        status_context=task.status
    ).select_related('user')

    # Calculate overall progress for this stage
    total_assignees = assignee_statuses.count()
    completed_assignees = assignee_statuses.filter(is_completed=True).count()

    # Determine if Current User has a pending action
    user_action_needed = False
    my_status_entry = assignee_statuses.filter(user=request.user).first()
    if my_status_entry and not my_status_entry.is_completed:
        user_action_needed = True

    # ----------------------------------------------------------------------
    # HANDLE POST ACTIONS
    # ----------------------------------------------------------------------
    if request.method == 'POST':
        action = request.POST.get('action_type')

        # --- A. MARK MY PART COMPLETE ---
        if action == 'complete_my_part':
            if my_status_entry:
                my_status_entry.is_completed = True
                my_status_entry.completed_at = timezone.now()
                my_status_entry.save()

                # Log comment
                TaskComment.objects.create(
                    task=task, author=request.user,
                    text=f"Marked their part for '{task.status}' as DONE."
                )

                # CHECK IF ALL ARE DONE -> ADVANCE STAGE
                # We re-count because database just updated
                pending_count = TaskAssignmentStatus.objects.filter(
                    task=task, status_context=task.status, is_completed=False
                ).count()

                if pending_count == 0:
                    # All assignees are done. Find next step.
                    try:
                        if task.status in workflow_steps:
                            current_index = workflow_steps.index(task.status)

                            # If there is a next step
                            if current_index < len(workflow_steps) - 1:
                                next_status = workflow_steps[current_index + 1]
                                old_status = task.status

                                # Log the transition
                                task.log_status_change(
                                    old_status, next_status, None,  # System change
                                    "Auto-advanced: All assignees completed their part."
                                )

                                # Update Task
                                task.status = next_status
                                task.save()

                                # Reset tracking for new stage
                                initialize_step_for_assignees(task)

                                messages.success(request, f"Stage complete! Task moved to {next_status}.")
                            else:
                                # End of workflow
                                task.completed_date = timezone.now().date()
                                task.save()
                                messages.success(request, "Task fully completed! No further steps.")
                        else:
                            # Fallback if current status isn't in config list (maybe manually set)
                            messages.warning(request,
                                             "Current status not found in workflow configuration. Cannot auto-advance.")
                    except ValueError:
                        messages.warning(request, "Workflow configuration error.")
                else:
                    messages.success(request, "Your part is done. Waiting for other assignees.")

        # --- B. UPDATE ASSIGNEES (Multi-Select) ---
        elif action == 'update_assignees':
            user_ids = request.POST.getlist('assignees')  # Get list of IDs
            if user_ids:
                new_users = User.objects.filter(id__in=user_ids)
                task.assignees.set(new_users)  # Update M2M

                # Re-initialize tracking for current step
                # (Existing completions are kept, new users added as Pending)
                initialize_step_for_assignees(task)

                # Cleanup: Remove tracking for users who were removed from assignment
                TaskAssignmentStatus.objects.filter(
                    task=task, status_context=task.status
                ).exclude(user__in=new_users).delete()

                messages.success(request, "Team updated.")

        # --- C. ADD COMMENT ---
        elif action == 'add_comment':
            text = request.POST.get('comment_text')
            if text:
                TaskComment.objects.create(task=task, author=request.user, text=text)
                messages.success(request, "Comment posted.")

        # --- D. UPLOAD DOCUMENT ---
        elif action == 'upload_document':
            file = request.FILES.get('document_file')
            desc = request.POST.get('document_desc')
            if file:
                TaskDocument.objects.create(
                    task=task, uploaded_by=request.user, file=file, description=desc
                )
                messages.success(request, "Document uploaded.")

        return redirect('task_detail', task_id=task.id)

    # ----------------------------------------------------------------------
    # CONTEXT PREPARATION
    # ----------------------------------------------------------------------
    all_users = User.objects.filter(is_active=True)

    # Aging & History
    logs = task.status_logs.select_related('changed_by').order_by('created_at')
    aging_timeline = []
    last_time = task.created_at

    for log in logs:
        duration = log.created_at - last_time
        aging_timeline.append({
            'status': log.old_status,
            'changed_by': log.changed_by,
            'timestamp': log.created_at,
            'duration': duration,
            'remarks': log.remarks
        })
        last_time = log.created_at

    if task.status != 'Completed':
        current_duration = timezone.now() - last_time
        aging_timeline.append({
            'status': task.status,
            'is_current': True,
            'timestamp': timezone.now(),
            'duration': current_duration
        })

    # Extended Fields
    extended_fields = []
    if hasattr(task, 'extended_attributes'):
        attr = task.extended_attributes
        exclude = ['id', 'task', 'task_id']
        for field in attr._meta.fields:
            if field.name not in exclude:
                val = getattr(attr, field.name)
                if val:
                    extended_fields.append(
                        {'label': field.verbose_name.title(), 'value': val, 'is_file': 'file' in field.name})

    context = {
        'task': task,
        'assignee_statuses': assignee_statuses,
        'user_action_needed': user_action_needed,
        'progress_percent': (completed_assignees / total_assignees * 100) if total_assignees > 0 else 0,
        'all_users': all_users,
        'workflow_steps': workflow_steps,
        'aging_timeline': aging_timeline,
        'extended_fields': extended_fields,
        'comments': task.comments.select_related('author').order_by('-created_at'),
        'documents': task.documents.select_related('uploaded_by').order_by('-uploaded_at')
    }
    return render(request, 'client/task-detail.html', context)


# ==============================================================================
# 2. NEW EDIT VIEW (Handles Full Editing)
# ==============================================================================

@login_required()
def edit_task_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    client = task.client  # <--- 1. GET CLIENT FROM TASK

    # 2. PREPARE CLIENT DATA (Needed for the JS Auto-fill to not crash)
    client_data_map = {
        'pan_no': client.pan_no,
        'email': client.email,
        'phone': client.phone_number,
        'din_no': client.din_no,
        # 'gst_number': client.gst_details.first().gst_number if ...
    }

    if not hasattr(task, 'extended_attributes'):
        TaskExtendedAttributes.objects.create(task=task)

    if request.method == 'POST':
        task_form = TaskForm(request.POST, instance=task)
        extended_form = TaskExtendedForm(request.POST, request.FILES, instance=task.extended_attributes)

        if task_form.is_valid() and extended_form.is_valid():
            task_form.save()
            extended_form.save()
            messages.success(request, "Task updated successfully.")
            return redirect('task_detail', task_id=task.id)
    else:
        task_form = TaskForm(instance=task)
        extended_form = TaskExtendedForm(instance=task.extended_attributes)

    context = {
        'task': task,
        'client': client,  # <--- 3. PASS CLIENT TO TEMPLATE (Fixes NoReverseMatch)
        'task_form': task_form,
        'extended_form': extended_form,
        'task_config': TASK_CONFIG,
        'client_data_json': json.dumps(client_data_map, cls=DjangoJSONEncoder)  # <--- 4. PASS JSON DATA
    }
    return render(request, 'client/create_task.html', context)