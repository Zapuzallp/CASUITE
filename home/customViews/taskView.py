import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q, Max
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from home.clients.config import TASK_CONFIG, DEFAULT_WORKFLOW_STEPS
from home.forms import TaskForm, TaskExtendedForm
from home.models import Client, TaskComment, Employee, Task, TaskExtendedAttributes, TaskDocument, TaskAssignmentStatus, TaskType
from home.utils import is_gst_number


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
    """
    Displays a list of tasks with role-based visibility and filtering.
    Supports GST number search pattern detection and custom client filters.
    """
    user = request.user

    # 1. Initialize Base QuerySets
    # We select related fields to optimize database queries
    tasks_qs = Task.objects.select_related('client', 'created_by', 'task_type').prefetch_related('assignees')
    clients_qs = Client.objects.only('id', 'client_name', 'status', 'office_location', 'assigned_ca')

    # 2. Role-Based Visibility Logic
    if user.is_superuser:
        # Superuser sees everything
        pass
    else:
        try:
            employee = user.employee
            if employee.role == 'ADMIN':
                # Admin sees everything
                pass


            elif employee.role == 'BRANCH_MANAGER':
                if employee.office_location:
                    # Show tasks if:
                    # 1. Client is in the manager's office
                    # OR 2. Manager is the Client's CA
                    # OR 3. Manager is directly assigned (Assignee)

                    tasks_qs = tasks_qs.filter(
                        Q(client__office_location=employee.office_location) |
                        Q(client__assigned_ca=user) |
                        Q(assignees=user)
                    ).distinct()

                    clients_qs = clients_qs.filter(
                        Q(office_location=employee.office_location) |
                        Q(assigned_ca=user)

                    ).distinct()

                else:
                    tasks_qs = tasks_qs.filter(
                        Q(client__assigned_ca=user) |
                        Q(assignees=user)
                    ).distinct()

                    clients_qs = clients_qs.filter(assigned_ca=user)

            else:
                # Staff sees only tasks for clients assigned to them
                tasks_qs = tasks_qs.filter(Q(client__assigned_ca=user) | Q(assignees=user))
                clients_qs = clients_qs.filter(assigned_ca=user)

        except Employee.DoesNotExist:
            # Fallback for users without an employee profile
            tasks_qs = tasks_qs.filter(client__assigned_ca=user)
            clients_qs = clients_qs.filter(assigned_ca=user)

    # 3. Apply UI Filters (GET parameters)
    search_query = request.GET.get('q')
    filter_client = request.GET.get('client')
    filter_service = request.GET.get('service_type')
    filter_status = request.GET.get('status')
    filter_task_type = request.GET.get('task_type')
    
    if search_query:
        # Check if search query is a GST number pattern
        if is_gst_number(search_query):
            # Search in GSTDetails for this GST number
            gst_clients = Client.objects.filter(gst_details__gst_number__icontains=search_query)
            tasks_qs = tasks_qs.filter(
                Q(task_title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(client__in=gst_clients) |
                Q(client__client_name__icontains=search_query) |
                Q(client__file_number__icontains=search_query)
            )
        else:
            # Standard text search
            tasks_qs = tasks_qs.filter(
                Q(task_title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(client__client_name__icontains=search_query) |
                Q(client__file_number__icontains=search_query)
            )

    if filter_client:
        tasks_qs = tasks_qs.filter(client_id=filter_client)

    if filter_service:
        tasks_qs = tasks_qs.filter(service_type=filter_service)

    if filter_status:
        tasks_qs = tasks_qs.filter(status=filter_status)
    
    if filter_task_type:
        tasks_qs = tasks_qs.filter(task_type_id=filter_task_type)
    
    context = {
        'tasks': tasks_qs.order_by('-created_at'),
        'clients': clients_qs.order_by('client_name'),  # For the "Add Task" modal
        'filter_clients': clients_qs.order_by('client_name'),  # For the Filter dropdown
        'today': timezone.now().date(),
        'service_type_choices': Task.SERVICE_TYPE_CHOICES,
        'status_choices': Task.STATUS_CHOICES,
        'task_types': TaskType.objects.all().order_by('task_type_name'),  # For the Task Type dropdown
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
    """
    Detailed view with Sequence-Driven Workflow Logic.
    Assignments define the status flow.
    """
    user = request.user
    is_admin = user.is_superuser

    # --- Role-Based Permission Logic ---
    if user.is_superuser:
        task = get_object_or_404(Task, id=task_id)
    else:
        try:
            employee = user.employee
            if employee.role == 'ADMIN':
                task = get_object_or_404(Task, id=task_id)
                is_admin = True
            elif employee.role == 'BRANCH_MANAGER':
                if employee.office_location:
                    # Manager sees task if:
                    # 1. It matches their Office
                    # OR 2. They are the Client's CA
                    # OR 3. They are explicitly assigned
                    task = get_object_or_404(
                        Task.objects.distinct(),  # Important: Prevents duplicates from OR logic
                        Q(client__office_location=employee.office_location) |
                        Q(client__assigned_ca=user) |
                        Q(assignees=user),
                        id=task_id
                    )
                else:
                    # Fallback: Manager has no office, show only directly assigned
                    task = get_object_or_404(
                        Task.objects.distinct(),
                        Q(client__assigned_ca=user) | Q(assignees=user),
                        id=task_id
                    )
            else:
                task = get_object_or_404(
                    Task,
                    Q(client__assigned_ca=user) | Q(assignees=user),
                    id=task_id
                )
        except Employee.DoesNotExist:
            task = get_object_or_404(Task, id=task_id, client__assigned_ca=user)

    # 1. Load Config & Steps
    config = TASK_CONFIG.get(task.service_type, {})
    workflow_steps = config.get('workflow_steps', DEFAULT_WORKFLOW_STEPS)

    # 2. Get Team Sequence (Strict Order)
    # We fetch ALL assignments, not just for current status, because the sequence defines the future
    assignee_statuses = TaskAssignmentStatus.objects.filter(task=task).select_related('user').order_by('order')

    # 3. Determine Active Step & User State
    user_action_needed = False
    waiting_for_previous = False
    my_status_entry = None

    # The "Active Step" is the FIRST incomplete step in the sequence
    active_step = assignee_statuses.filter(is_completed=False).first()

    # Self-Healing: Ensure Task Status matches the Active Step's status context
    if active_step and task.status != active_step.status_context and task.status != 'Completed':
        # If the sequence says we are at 'Review' but task says 'Pending', update task
        task.log_status_change(task.status, active_step.status_context, user, "Auto-sync with sequence")
        task.status = active_step.status_context
        task.save()

    if active_step:
        if active_step.user == user:
            user_action_needed = True
            my_status_entry = active_step
        elif is_admin:
            user_action_needed = True
            my_status_entry = active_step
        elif assignee_statuses.filter(user=user, is_completed=False).exists():
            waiting_for_previous = True

    # ==========================================================================
    # HANDLE POST ACTIONS
    # ==========================================================================
    if request.method == 'POST':
        action = request.POST.get('action_type')

        # --- A. UPDATE SEQUENCE (Define User + Status Flow) ---
        if action == 'update_sequence':
            # Inputs are arrays of user IDs and Status Labels
            user_ids = request.POST.getlist('seq_users')
            status_labels = request.POST.getlist('seq_statuses')

            if user_ids and status_labels and len(user_ids) == len(status_labels):
                # 1. Determine starting order index (preserve completed history)
                max_order = TaskAssignmentStatus.objects.filter(
                    task=task, is_completed=True
                ).aggregate(Max('order'))['order__max'] or 0

                start_order = max_order + 1

                # 2. Wipe ALL future/incomplete steps
                TaskAssignmentStatus.objects.filter(task=task, is_completed=False).delete()

                # 3. Create new steps
                new_users = []
                for i, uid in enumerate(user_ids):
                    status_label = status_labels[i]
                    try:
                        u_obj = User.objects.get(id=uid)
                        new_users.append(u_obj)

                        TaskAssignmentStatus.objects.create(
                            task=task,
                            user=u_obj,
                            status_context=status_label,
                            order=start_order + i,
                            is_completed=False
                        )
                    except User.DoesNotExist:
                        continue

                # Update ManyToMany for easy querying
                # Note: This is additive logic for the M2M field
                current_assignees = list(task.assignees.all())
                for u in new_users:
                    if u not in current_assignees:
                        task.assignees.add(u)

                # 4. Trigger Immediate Status Update if needed
                # If we just defined the sequence, and the task was 'Pending' or empty,
                # we should snap the task status to the first step of this new sequence.
                first_new_step = TaskAssignmentStatus.objects.filter(
                    task=task, is_completed=False
                ).order_by('order').first()

                if first_new_step:
                    if task.status != first_new_step.status_context:
                        task.log_status_change(task.status, first_new_step.status_context, user, "Sequence Updated")
                        task.status = first_new_step.status_context
                        task.save()

                messages.success(request, "Workflow sequence updated successfully.")
            else:
                messages.error(request, "Invalid sequence data.")

        # --- B. COMPLETE STEP (Advance Sequence) ---
        elif action == 'complete_my_part':
            target_id = request.POST.get('target_entry_id')

            if is_admin and target_id:
                entry = get_object_or_404(TaskAssignmentStatus, id=target_id)
            else:
                entry = my_status_entry

            if entry:
                # Strict Order Check
                prev_pending = TaskAssignmentStatus.objects.filter(
                    task=task,
                    order__lt=entry.order,
                    is_completed=False
                ).exists()

                if prev_pending and not is_admin:
                    messages.error(request, "Previous steps must be completed first.")
                else:
                    # Mark Done
                    entry.is_completed = True
                    entry.completed_at = timezone.now()
                    entry.save()

                    actor = "Admin" if (is_admin and entry.user != user) else user.first_name
                    TaskComment.objects.create(
                        task=task, author=user,
                        text=f"Step #{entry.order} ({entry.status_context}) completed by {actor}."
                    )

                    # --- ADVANCE WORKFLOW LOGIC ---
                    # Check what is next
                    next_step = TaskAssignmentStatus.objects.filter(
                        task=task, is_completed=False
                    ).order_by('order').first()

                    if next_step:
                        # If the next step has a different status, move the task status
                        if next_step.status_context != task.status:
                            task.log_status_change(
                                task.status, next_step.status_context, None,
                                "Sequence Advanced"
                            )
                            task.status = next_step.status_context
                            task.save()
                            messages.success(request, f"Step Done. Task moved to '{task.status}'.")
                        else:
                            messages.success(request, "Step Done. Remaining in current stage.")
                    else:
                        # No more steps? Task is Completed.
                        task.status = 'Completed'
                        task.completed_date = timezone.now().date()
                        task.save()
                        messages.success(request, "All steps finished. Task Completed!")

        # --- C. OTHER ACTIONS ---
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
    # CONTEXT
    # ==========================================================================

    # Aging
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

    # Extended Attributes
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
        'assignee_statuses': assignee_statuses,  # Full sequence
        'active_step': active_step,
        'user_action_needed': user_action_needed,
        'my_status_entry': my_status_entry,
        'waiting_for_previous': waiting_for_previous,
        'is_admin': is_admin,
        'workflow_steps': workflow_steps,
        'aging_timeline': aging_timeline,
        'extended_fields': extended_fields,
        'all_users': User.objects.filter(is_active=True).order_by('first_name'),
        'comments': task.comments.select_related('author').order_by('-created_at'),
        'documents': task.documents.select_related('uploaded_by').order_by('-uploaded_at'),
        # Progress Calculation:
        'progress_percent': (assignee_statuses.filter(
            is_completed=True).count() / assignee_statuses.count() * 100) if assignee_statuses.exists() else 0
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