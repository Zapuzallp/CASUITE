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
        'client_data_json': client_data_map
    }
    return render(request, 'client/create_task.html', context)


@login_required
def task_list_view(request):
    #---------------------------------------------------------------------------------------------------
    #The client list in the task creation form is filtered based on the logged-in user’s assigned client.
    #---------------------------------------------------------------------------------------------------
    user = request.user
    if user.is_superuser:
        tasks = Task.objects.select_related('client') \
            .prefetch_related('assignees') \
            .order_by('-created_at')
        clients = Client.objects.all().order_by('client_name')
    else:
        tasks = Task.objects.select_related('client') \
            .prefetch_related('assignees') \
            .filter(client__assigned_ca=user) \
            .order_by('-created_at')
        clients = Client.objects.filter(assigned_ca=user).order_by('client_name')

    context = {
        'tasks': tasks,
        'clients': clients,  # Pass to template
        'today': timezone.now().date()
    }
    return render(request, 'client/tasks.html', context)

# ---------------------------------------------------------
# HELPER: Initialize Status Sequence
# ---------------------------------------------------------
def initialize_step_for_assignees(task):
    """
    Creates Status rows for the current task status.
    Preserves the order based on the M2M field or ID.
    """
    current_assignees = task.assignees.all()
    # We use a simple counter to set the order (1, 2, 3...)
    for index, user in enumerate(current_assignees):
        TaskAssignmentStatus.objects.get_or_create(
            task=task,
            user=user,
            status_context=task.status,
            defaults={
                'is_completed': False,
                'order': index + 1  # 1-based sequence
            }
        )


@login_required
def task_detail_view(request, task_id):
    user = request.user
    is_admin = user.is_superuser
    if user.is_superuser:
        task = get_object_or_404(Task, id=task_id)
    else:
        task = get_object_or_404(
            Task,
            id=task_id,
            client__assigned_ca=user
        )

    # 1. Load Workflow Config
    config = TASK_CONFIG.get(task.service_type, {})
    workflow_steps = config.get('workflow_steps', DEFAULT_WORKFLOW_STEPS)

    # 2. Get Team Status (Ordered by Sequence)
    assignee_statuses = TaskAssignmentStatus.objects.filter(
        task=task, status_context=task.status
    ).select_related('user').order_by('order')

    # 3. Determine User State (Active, Locked, or Admin)
    user_action_needed = False
    waiting_for_previous = False
    my_status_entry = None

    # Identify the "Active Step" (The first uncompleted step in the sequence)
    active_step = assignee_statuses.filter(is_completed=False).first()

    if active_step:
        # Scenario A: It is MY turn
        if active_step.user == user:
            user_action_needed = True
            my_status_entry = active_step

        # Scenario B: I am an Admin (I can act on the active step regardless of owner)
        elif is_admin:
            user_action_needed = True
            my_status_entry = active_step  # Admin acts on the active bottleneck

        # Scenario C: I am assigned later in the sequence (Locked)
        elif assignee_statuses.filter(user=user, is_completed=False).exists():
            waiting_for_previous = True

    # ==========================================================================
    # HANDLE POST ACTIONS
    # ==========================================================================
    if request.method == 'POST':
        action = request.POST.get('action_type')

        # --- A. COMPLETE PART (Sequential Check) ---
        if action == 'complete_my_part':
            target_id = request.POST.get('target_entry_id')

            # Select the entry to complete
            if is_admin and target_id:
                entry_to_complete = get_object_or_404(TaskAssignmentStatus, id=target_id)
            else:
                entry_to_complete = my_status_entry

            if entry_to_complete:
                # Security: Ensure no LOWER order is pending (unless Admin override)
                previous_pending = TaskAssignmentStatus.objects.filter(
                    task=task, status_context=task.status,
                    order__lt=entry_to_complete.order, is_completed=False
                ).exists()

                if previous_pending and not is_admin:
                    messages.error(request, "Cannot complete yet. Previous team member must finish first.")
                else:
                    # Mark Done
                    entry_to_complete.is_completed = True
                    entry_to_complete.completed_at = timezone.now()
                    entry_to_complete.save()

                    # Log Action
                    actor_name = "Admin" if (is_admin and entry_to_complete.user != user) else user.first_name
                    TaskComment.objects.create(
                        task=task, author=user,
                        text=f"[{task.status}] Step {entry_to_complete.order} ({entry_to_complete.user.first_name}) marked DONE by {actor_name}."
                    )

                    # Check for Workflow Advancement
                    remaining_pending = TaskAssignmentStatus.objects.filter(
                        task=task, status_context=task.status, is_completed=False
                    ).count()

                    if remaining_pending == 0:
                        # Advance Workflow
                        try:
                            if task.status in workflow_steps:
                                idx = workflow_steps.index(task.status)
                                if idx < len(workflow_steps) - 1:
                                    next_status = workflow_steps[idx + 1]
                                    task.log_status_change(task.status, next_status, None,
                                                           "Auto-advanced: Sequence complete.")
                                    task.status = next_status
                                    task.save()
                                    initialize_step_for_assignees(task)  # Create rows for new status
                                    messages.success(request, f"Stage Complete! Moving to {next_status}.")
                                else:
                                    task.status = 'Completed'
                                    task.completed_date = timezone.now().date()
                                    task.save()
                                    messages.success(request, "Task Fully Completed!")
                        except ValueError:
                            pass
                    else:
                        messages.success(request, "Step completed. Passing to next in sequence.")

        # --- B. UPDATE ASSIGNEES (Preserve Order) ---
        elif action == 'update_assignees':
            user_ids = request.POST.getlist('assignees')  # Gets IDs in selection order
            if user_ids:
                new_users = User.objects.filter(id__in=user_ids)
                task.assignees.set(new_users)

                # Update Sequence for CURRENT Status
                current_context = task.status

                # We wipe pending statuses and recreate them to ensure the new order is applied
                # Completed statuses are kept for history
                TaskAssignmentStatus.objects.filter(
                    task=task, status_context=current_context, is_completed=False
                ).delete()

                for index, uid in enumerate(user_ids):
                    u_obj = new_users.get(id=uid)
                    # Get or Create (Use update_defaults to set new order)
                    obj, created = TaskAssignmentStatus.objects.get_or_create(
                        task=task, user=u_obj, status_context=current_context
                    )
                    if not obj.is_completed:
                        obj.order = index + 1
                        obj.save()

                messages.success(request, "Team sequence updated.")

        # --- C. OTHER ACTIONS (Comments, Uploads, Financials) ---
        elif action == 'add_comment':
            txt = request.POST.get('comment_text')
            if txt: TaskComment.objects.create(task=task, author=user, text=txt)

        elif action == 'upload_document':
            f = request.FILES.get('document_file')
            d = request.POST.get('document_desc')
            if f: TaskDocument.objects.create(task=task, uploaded_by=user, file=f, description=d)

        elif action == 'update_financials':
            task.agreed_fee = request.POST.get('agreed_fee', 0)
            task.fee_status = request.POST.get('fee_status')
            task.save()

        return redirect('task_detail', task_id=task.id)

    # ==========================================================================
    # CONTEXT PREPARATION
    # ==========================================================================

    # 1. Aging Calculation
    logs = task.status_logs.select_related('changed_by').order_by('created_at')
    aging_timeline = []
    last_time = task.created_at
    for log in logs:
        duration = log.created_at - last_time
        aging_timeline.append({
            'status': log.old_status, 'changed_by': log.changed_by,
            'timestamp': log.created_at, 'duration': duration, 'remarks': log.remarks
        })
        last_time = log.created_at

    if task.status != 'Completed':
        aging_timeline.append({
            'status': task.status, 'is_current': True,
            'timestamp': timezone.now(), 'duration': timezone.now() - last_time
        })

    # 2. Calculate Progress %
    total_assignees = assignee_statuses.count()
    completed_count = assignee_statuses.filter(is_completed=True).count()
    progress_percent = (completed_count / total_assignees * 100) if total_assignees > 0 else 0

    # 3. Extended Fields
    extended_fields = []
    if hasattr(task, 'extended_attributes'):
        attr = task.extended_attributes
        exclude = ['id', 'task', 'task_id']
        for field in attr._meta.fields:
            if field.name not in exclude:
                val = getattr(attr, field.name)
                if val: extended_fields.append(
                    {'label': field.verbose_name.title(), 'value': val, 'is_file': 'file' in field.name})

    context = {
        'task': task,
        'assignee_statuses': assignee_statuses,  # Ordered list
        'user_action_needed': user_action_needed,
        'my_status_entry': my_status_entry,
        'waiting_for_previous': waiting_for_previous,
        'is_admin': is_admin,
        'active_step': active_step,  # For template highlighting
        'workflow_steps': workflow_steps,
        'progress_percent': progress_percent,
        'aging_timeline': aging_timeline,
        'extended_fields': extended_fields,
        'all_users': User.objects.filter(is_active=True),
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