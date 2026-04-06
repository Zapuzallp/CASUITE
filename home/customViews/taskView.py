import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.views.decorators.http import require_POST
from django.db.models import Q, Max
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import timedelta,datetime
from home.clients.config import TASK_CONFIG, DEFAULT_WORKFLOW_STEPS
from home.forms import TaskForm, TaskExtendedForm
from home.models import Client, TaskComment, Employee, Task, TaskExtendedAttributes, TaskDocument, TaskAssignmentStatus
from home.clients.client_access import get_accessible_clients
from home.tasks.task_copy import copy_task
from home.tasks.task_visibility import get_visible_tasks
# Import of pagination
from django.core.paginator import  Paginator

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

    # 2. Prepare GST Details for Auto-Population
    gst_details = client.gst_details.all()
    gst_options = []
    default_gst_id = None

    for gst in gst_details:
        gst_options.append({
            'id': gst.id,
            'gst_number': gst.gst_number,
            'state': gst.get_state_display(),
            'label': f"{gst.gst_number} - {gst.get_state_display()}"
        })
        # Set first GST as default for auto-population
        if default_gst_id is None:
            default_gst_id = gst.id

    # Add validation message if no GST details found
    gst_validation_message = None
    if not gst_details.exists():
        gst_validation_message = "No GST details found for this client. Add GST number for this client."

    if request.method == 'POST':
        task_form = TaskForm(request.POST)
        extended_form = TaskExtendedForm(request.POST, request.FILES, client=client)

        # Filter gstin_number field to show only client's GST details
        if hasattr(extended_form.fields, 'gstin_number'):
            extended_form.fields['gstin_number'].queryset = client.gst_details.all()

        if task_form.is_valid() and extended_form.is_valid():
            # Additional validation for GST Return Filing
            if task_form.cleaned_data.get('service_type') == 'GST Return':
                if not client.gst_details.exists():
                    messages.error(
                        request,
                        "Cannot create GST Return Filing task: No GST details found for this client. "
                        "Please add GST number for this client first."
                    )
                    # Re-render form with error
                    context = {
                        'client': client,
                        'task_form': task_form,
                        'extended_form': extended_form,
                        'task_config': TASK_CONFIG,
                        'client_data_json': client_data_map,
                        'gst_options': gst_options,
                        'default_gst_id': default_gst_id,
                        'gst_validation_message': gst_validation_message
                    }
                    return render(request, 'client/create_task.html', context)

            try:
                with transaction.atomic():
                    # Save Task
                    task = task_form.save(commit=False)
                    task.client = client
                    task.created_by = request.user

                    # ✅ ADD THIS BLOCK
                    if not task.due_date:
                        config = TASK_CONFIG.get(task.service_type, {})
                        days = config.get('default_due_days')
                        if days:
                            task.due_date = timezone.now().date() + timedelta(days=days)

                    # Auto Title if empty: "GST Return Task"
                    if not task.task_title:
                        task.task_title = f"{task.get_service_type_display()} Task"

                    task.save()

                    # Save Extended Attributes
                    extended = extended_form.save(commit=False)
                    extended.task = task
                    extended.save()

                    messages.success(request, "Task created successfully!")
                    return redirect('task_list')
            except Exception as e:
                messages.error(request, f"Error: {e}")
        else:
            messages.error(request, "Please check the form for errors.")
    else:
        task_form = TaskForm()
        extended_form = TaskExtendedForm(client=client)

        # Filter gstin_number field to show only client's GST details
        if hasattr(extended_form.fields, 'gstin_number'):
            extended_form.fields['gstin_number'].queryset = client.gst_details.all()

    context = {
        'client': client,
        'task_form': task_form,
        'extended_form': extended_form,

        # Pass Config and Data to Template
        'task_config': TASK_CONFIG,
        'client_data_json': client_data_map,
        'gst_options': gst_options,
        'default_gst_id': default_gst_id,
        'gst_validation_message': gst_validation_message
    }
    return render(request, 'client/create_task.html', context)


@login_required
def task_list_view(request):
    """
    Displays a list of tasks with role-based visibility and filtering.
    """
    user = request.user
    # 1. Get visible tasks (core logic)
    # Order by latest created
    tasks_qs = get_visible_tasks(user).order_by('-created_at')

    # 2. Get clients (UI support)
    clients_qs = get_accessible_clients(user)

    # 3. Apply UI Filters (GET parameters)
    search_query = request.GET.get('q')
    filter_client = request.GET.get('client')
    filter_service = request.GET.get('service_type')
    filter_consultancy_type = request.GET.get('consultancy_type')
    filter_status = request.GET.get('status')
    filter_invoice_status = request.GET.get('invoice_status')
    filter_due = request.GET.get('due_filter')
    due_from = request.GET.get('due_from')
    due_to = request.GET.get('due_to')

    if search_query:
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

    if filter_consultancy_type:
        tasks_qs = tasks_qs.filter(consultancy_type=filter_consultancy_type)
    # Invoice Status Filter
    if filter_invoice_status:
        if filter_invoice_status == 'invoiced':
            # Tasks that have at least one invoice
            tasks_qs = tasks_qs.filter(tagged_invoices__isnull=False).distinct()
        elif filter_invoice_status == 'not_invoiced':
            # Tasks that have no invoices
            tasks_qs = tasks_qs.filter(tagged_invoices__isnull=True)

        # Due Date Filter
    if filter_due:
        # today = timezone.now().date()
        # tomorrow = today + timedelta(days=1)
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)

        if filter_due == "overdue":
            # Overdue but NOT completed
            tasks_qs = tasks_qs.filter(
                due_date__lt=today,
                due_date__isnull=False,
            ).exclude(status="Completed")

        elif filter_due == "today":
            tasks_qs = tasks_qs.filter(
                due_date=today
            ).exclude(status="Completed")

        elif filter_due == "tomorrow":
            tasks_qs = tasks_qs.filter(
                due_date=tomorrow
            ).exclude(status="Completed")

        elif filter_due == "no_due":
            tasks_qs = tasks_qs.filter(
                due_date__isnull=True
            )

        elif filter_due == "range" :
            try:
                due_from_date = datetime.strptime(due_from, "%Y-%m-%d").date() if due_from else None
                due_to_date = datetime.strptime(due_to, "%Y-%m-%d").date()  if due_to else None

                # Case 1: Both dates provided
                if due_from_date and due_to_date:
                    if due_to_date < due_from_date:
                        # invalid range → return no results
                        tasks_qs = tasks_qs.none()
                        messages.error(request, "End date cannot be before start date.")
                    else:
                        tasks_qs = tasks_qs.filter(
                            due_date__range=[due_from_date, due_to_date],
                            due_date__isnull=False
                        )

                # Case 2: Only FROM date
                elif due_from_date:
                    tasks_qs = tasks_qs.filter(
                        due_date__gte=due_from_date,
                        due_date__isnull=False
                    )

                # Case 3: Only TO date
                elif due_to_date:
                    tasks_qs = tasks_qs.filter(
                        due_date__lte=due_to_date,
                        due_date__isnull=False
                    )
            except ValueError:
                messages.error(request, "Invalid date format.")

    # Records per page dropdown value
    per_page = request.GET.get('per_page', '25')

    if per_page == "all":
        per_page_value = tasks_qs.count() or 1
    else:
        try:
            per_page_value = int(per_page)
        except ValueError:
            per_page = "25"
            per_page_value = 25

    tasks_qs = tasks_qs.order_by('-created_at')
    # Pagination
    paginator = Paginator(tasks_qs, per_page_value)
    page = request.GET.get('page')
    tasks_qs = paginator.get_page(page)


    # Remove page parameter from query string
    query_params = request.GET.copy()
    query_params.pop('page', None)
    # Remove empty query parameters
    for key in list(query_params.keys()):
        if not query_params.get(key):
            query_params.pop(key)
    has_filters = any([
        search_query,
        filter_client,
        filter_service,
        filter_consultancy_type,
        filter_status,
        filter_invoice_status,
        filter_due,
        due_from,
        due_to,
    ])
    # Check if user is a partner (view-only access)
    is_partner = False
    if hasattr(user, 'employee'):
        is_partner = user.employee.role == 'PARTNER'

    context = {
        'tasks': tasks_qs,
        'query_params': query_params.urlencode(),
        'per_page': per_page,
        'has_filters': has_filters,
        'clients': clients_qs.order_by('client_name'),  # For the "Add Task" modal
        'filter_clients': clients_qs.order_by('client_name'),  # For the Filter dropdown
        'today': timezone.now().date(),
        'tomorrow': timezone.now().date() + timedelta(days=1),
        'service_type_choices': Task.SERVICE_TYPE_CHOICES,
        'consultancy_type_choices': sorted(
            Task.CONSULTANCY_TYPE_CHOICES,
            key=lambda x: x[1]
        ),

        'status_choices': Task.STATUS_CHOICES,
        'is_partner': is_partner,
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

    # Check if user is a partner (view-only access)
    is_partner = False
    if hasattr(user, 'employee'):
        is_partner = user.employee.role == 'PARTNER'

    # Universal client visibility
    #(Admin → all, Branch Manager → branch + assigned, Staff → assigned only)
    # accessible_clients = get_accessible_clients(user)

    # NOTE:
    # Task visibility is controlled via get_visible_tasks()
    # Ensures consistency with task_list_view and prevents access mismatch

    task = get_object_or_404(
        get_visible_tasks(user),
        id=task_id
    )
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

        # Check if Partner has edit access to this task
        partner_can_edit = False
        if hasattr(user, 'employee') and user.employee.role == 'PARTNER':
            is_creator = task.created_by == user
            is_assignee = user in task.assignees.all()
            is_client_ca = task.client.assigned_ca == user
            is_in_sequence = assignee_statuses.filter(user=user).exists()
            partner_can_edit = (is_creator or is_assignee or is_client_ca or is_in_sequence)

        # Allow comments and document uploads for Partners with edit access
        if action in ['add_comment', 'upload_document']:
            if hasattr(user, 'employee') and user.employee.role == 'PARTNER' and not partner_can_edit:
                messages.error(request, 'You do not have permission to modify this task.')
                return redirect('task_detail', task_id=task.id)
        # Block other actions for Partners without edit access
        elif hasattr(user, 'employee') and user.employee.role == 'PARTNER' and not partner_can_edit:
            messages.error(request, 'You do not have permission to modify this task.')
            return redirect('task_detail', task_id=task.id)

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

    # Check if user is a partner and determine edit permissions
    is_partner = False
    can_edit_task = True
    if hasattr(user, 'employee'):
        is_partner = user.employee.role == 'PARTNER'
        if is_partner:
            # Partner can edit ONLY IF any of the following is true:
            is_creator = task.created_by == user
            is_assignee = user in task.assignees.all()
            is_client_ca = task.client.assigned_ca == user
            is_in_sequence = assignee_statuses.filter(user=user).exists()
            can_edit_task = (is_creator or is_assignee or is_client_ca or is_in_sequence)

    context = {
        'task': task,
        'assignee_statuses': assignee_statuses,  # Full sequence
        'active_step': active_step,
        'user_action_needed': user_action_needed,
        'my_status_entry': my_status_entry,
        'waiting_for_previous': waiting_for_previous,
        'is_admin': is_admin,
        'is_partner': is_partner,
        'can_edit_task': can_edit_task,
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
    # task = get_object_or_404(Task, id=task_id)
    task = get_object_or_404(
        get_visible_tasks(request.user),
        id=task_id
    )
    # Check if user is a partner - apply restricted edit permissions
    if hasattr(request.user, 'employee') and request.user.employee.role == 'PARTNER':
        # Partner can edit ONLY IF any of the following is true:
        # 1. Partner created the task
        # 2. Partner is assigned to the task
        # 3. Partner is assigned CA of the client related to the task
        # 4. Partner is in manage sequence (TaskAssignmentStatus) of the task
        from home.models import TaskAssignmentStatus

        is_creator = task.created_by == request.user
        is_assignee = request.user in task.assignees.all()
        is_client_ca = task.client.assigned_ca == request.user
        is_in_sequence = TaskAssignmentStatus.objects.filter(task=task, user=request.user).exists()

        if not (is_creator or is_assignee or is_client_ca or is_in_sequence):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You are not allowed to perform this action")
    # Task visibility enforced using centralized logic

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
            return redirect('task_list')
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

@login_required
@require_POST
def copy_task_view(request, task_id):
    """
    Manual task copy handler.
    Uses shared copy logic.
    """

    # Enforce task visibility before allowing copy
    original_task = get_object_or_404(
        get_visible_tasks(request.user),
        id=task_id
    )

    #
    # # Optional: permission check (keep simple, same as edit/view)
    # if not request.user.has_perm('home.add_task'):
    #     messages.error(request, "You do not have permission to copy tasks.")
    #     return redirect('task_detail', task_id=task_id)

    # Reusable copy logic
    new_task = copy_task(
        original_task=original_task,
        created_by=request.user
    )

    # messages.success(request, "Task copied successfully.")

    return redirect('task_list')

# Delete Function for  tasks
@login_required
@require_POST
def delete_task_view(request, task_id):

    user = request.user
    if not user.is_superuser:
        messages.error(request, "Only administrators can delete tasks.")
        return redirect('task_list')

    task = get_object_or_404(Task, id=task_id)
    task.delete()
    messages.success(request, "Task deleted successfully.")

    return redirect('task_list')