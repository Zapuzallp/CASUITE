from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from home.models import Client, ServiceType, ClientService, ClientUserEntitle, Task
from home.forms import TaskForm


@login_required
def add_task(request, client_id):
    client = get_object_or_404(Client, pk=client_id)

    task_service_types = ServiceType.objects.filter(active=True, is_task=True).order_by("service_name")
    base_client_services = ClientService.objects.filter(
        client=client,
        is_active=True,
        service__is_task=False,
    ).select_related("service").order_by("service__service_name")

    if not base_client_services.exists():
        messages.error(request, "Please assign at least one base service to this client before adding tasks.")
        return redirect("client_details", pk=client.id)

    service_type_id = request.GET.get("service_type") or request.POST.get("service_type")
    client_service_id = request.GET.get("client_service") or request.POST.get("client_service")

    selected_service_type = None
    selected_client_service = None

    if service_type_id and client_service_id:
        try:
            selected_service_type = ServiceType.objects.get(
                pk=service_type_id,
                active=True,
                is_task=True,
            )
            selected_client_service = ClientService.objects.select_related("service").get(
                pk=client_service_id,
                client=client,
                is_active=True,
                service__is_task=False,
            )
        except (ServiceType.DoesNotExist, ClientService.DoesNotExist):
            messages.error(request, "Invalid task type or related service selection.")
            return redirect("add_task", client_id=client.id)

    if request.method == "POST" and selected_service_type and selected_client_service:
        task_form = TaskForm(request.POST, request.FILES)
        details_form = _get_task_details_form(
            selected_service_type,
            selected_client_service,
            data=request.POST,
            files=request.FILES,
        )

        if task_form.is_valid() and (details_form is None or details_form.is_valid()):
            task = task_form.save(commit=False)
            task.client_service = selected_client_service
            task.save()

            if details_form is not None:
                details_instance = details_form.save(commit=False)
                details_instance.client_service = selected_client_service
                details_instance.save()

            messages.success(
                request,
                f"Task '{task.task_title}' has been created under {selected_client_service.service.service_name}.",
            )
            # Instead of redirecting, render the same page with success flag to show modal
            context = {
                "client": client,
                "task_service_types": task_service_types,
                "client_services_for_tasks": base_client_services,
                "stage": 2,
                "selected_service_type": selected_service_type,
                "selected_client_service": selected_client_service,
                "task_form": TaskForm(),  # Reset form
                "details_form": _get_task_details_form(selected_service_type, selected_client_service),
                # Reset details form
                "success": True,
                "created_task_title": task.task_title
            }
            return render(request, "client/add-task.html", context)

        context = {
            "client": client,
            "task_service_types": task_service_types,
            "client_services_for_tasks": base_client_services,
            "stage": 2,
            "selected_service_type": selected_service_type,
            "selected_client_service": selected_client_service,
            "task_form": task_form,
            "details_form": details_form,
        }
        return render(request, "client/add-task.html", context)

    # Step 2 GET: show task form and optional details form with preview
    if selected_service_type and selected_client_service:
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta

        # Get the last task if it exists
        last_task = Task.objects.filter(
            client_service=selected_client_service
        ).order_by('-period_to').first()

        # Calculate the next period start date
        if last_task:
            next_period_start = last_task.period_to + timedelta(days=1)
        else:
            next_period_start = selected_client_service.start_date

        # Calculate period end based on frequency
        frequency = selected_client_service.service.frequency
        if frequency == 'Monthly':
            period_end = next_period_start + relativedelta(months=1) - timedelta(days=1)
        elif frequency == 'Quarterly':
            period_end = next_period_start + relativedelta(months=3) - timedelta(days=1)
        elif frequency == 'Yearly':
            period_end = next_period_start + relativedelta(years=1) - timedelta(days=1)
        else:  # Default for 'One-time' or other cases, a one-month period
            period_end = next_period_start + relativedelta(months=1) - timedelta(days=1)

        # Calculate due date based on period_end and default_due_days
        due_date = period_end + timedelta(days=selected_client_service.service.default_due_days)

        # Prepare initial form data
        initial_data = {
            'period_from': next_period_start,
            'period_to': period_end,
            'due_date': due_date,
            'recurrence': frequency if frequency != 'One-time' else 'None',
        }

        task_form = TaskForm(initial=initial_data)
        details_form = _get_task_details_form(selected_service_type, selected_client_service)

        context = {
            "client": client,
            "task_service_types": task_service_types,
            "client_services_for_tasks": base_client_services,
            "stage": 2,
            "selected_service_type": selected_service_type,
            "selected_client_service": selected_client_service,
            "task_form": task_form,
            "details_form": details_form,
            "due_days_meta": selected_client_service.service.default_due_days,  # Pass for JS auto-calculation
            "frequency": frequency,  # Pass frequency for any frontend calculations
        }
        return render(request, "client/add-task.html", context)

    # Step 1: select task type and related service
    context = {
        "client": client,
        "task_service_types": task_service_types,
        "client_services_for_tasks": base_client_services,
        "stage": 1,
    }
    return render(request, "client/add-task.html", context)


def _get_task_details_form(service_type_obj, client_service, data=None, files=None):
    if not service_type_obj or not service_type_obj.form_name:
        return None

    from home import forms as forms_module

    try:
        form_class = getattr(forms_module, service_type_obj.form_name)
    except AttributeError:
        return None

    initial = {}

    if service_type_obj.form_name == "GSTCaseForm":
        gst_detail = client_service.gst_details.first()
        if gst_detail:
            initial["gstin"] = gst_detail.gst_number

    if data is not None or files is not None:
        return form_class(data=data or None, files=files or None, initial=initial)

    return form_class(initial=initial)


def _get_user_clients(user):
    try:
        mapping = ClientUserEntitle.objects.get(user=user)
        return mapping.clients.all()
    except ClientUserEntitle.DoesNotExist:
        return Client.objects.none()


@login_required
def tasks_dashboard(request):
    user_clients = _get_user_clients(request.user)

    selected_client_id = request.GET.get("client_id")
    if selected_client_id:
        try:
            client = user_clients.get(pk=selected_client_id)
            return redirect("add_task", client_id=client.id)
        except Client.DoesNotExist:
            pass

    if not user_clients.exists():
        return render(request, "client/tasks.html", {
            "clients_with_tasks": [],
            "pending_tasks": 0,
            "user_clients": user_clients,
            "no_clients_message": "No clients assigned to you. Please contact your administrator.",
            "status_counts": {},
        })

    # Get status filter from query parameters
    status_filter = request.GET.get("status", "all")

    tasks_qs = Task.objects.filter(
        client_service__client__in=user_clients
    ).select_related(
        "client_service__client",
        "client_service__service",
        "assigned_to",
    ).order_by(
        "client_service__client__client_name",
        "client_service__service__service_name",
        "due_date",
    )

    # Apply status filter if not "all"
    if status_filter != "all":
        tasks_qs = tasks_qs.filter(task_status=status_filter)

    # Calculate status counts for filter buttons
    all_tasks = Task.objects.filter(client_service__client__in=user_clients)
    status_counts = {
        'all': all_tasks.count(),
        'Pending': all_tasks.filter(task_status='Pending').count(),
        'In_Progress': all_tasks.filter(task_status='In Progress').count(),
        'Submitted': all_tasks.filter(task_status='Submitted').count(),
        'Completed': all_tasks.filter(task_status='Completed').count(),
        'Delayed': all_tasks.filter(task_status='Delayed').count(),
        'Cancelled': all_tasks.filter(task_status='Cancelled').count(),
    }

    clients_with_tasks = {}
    total_pending = 0

    for task in tasks_qs:
        client = task.client_service.client
        service_name = task.client_service.service.service_name

        if client.id not in clients_with_tasks:
            clients_with_tasks[client.id] = {
                "client": client,
                "groups": {},
            }

        client_entry = clients_with_tasks[client.id]

        if service_name not in client_entry["groups"]:
            client_entry["groups"][service_name] = {
                "service_name": service_name,
                "tasks": [],
                "pending_count": 0,
                "total_count": 0,
            }

        group = client_entry["groups"][service_name]
        group["tasks"].append(task)
        group["total_count"] += 1
        if task.task_status == "Pending":
            group["pending_count"] += 1
            total_pending += 1

    clients_list = []
    for client_data in clients_with_tasks.values():
        groups = list(client_data["groups"].values())
        groups.sort(key=lambda g: g["service_name"])
        total_tasks_client = sum(g["total_count"] for g in groups)
        pending_tasks_client = sum(g["pending_count"] for g in groups)

        clients_list.append({
            "client": client_data["client"],
            "groups": groups,
            "total_tasks": total_tasks_client,
            "pending_tasks": pending_tasks_client,
        })

    clients_list.sort(key=lambda x: x["client"].client_name)

    context = {
        "clients_with_tasks": clients_list,
        "pending_tasks": total_pending,
        "user_clients": user_clients,
        "status_filter": status_filter,
        "status_counts": status_counts,
    }
    return render(request, "client/tasks.html", context)


@login_required
def task_detail(request, task_id):
    task = get_object_or_404(
        Task.objects.select_related(
            "client_service__client",
            "client_service__service",
            "assigned_to",
        ),
        pk=task_id,
    )

    client_service = task.client_service
    client = client_service.client

    user_clients = _get_user_clients(request.user)
    if not request.user.is_staff and client not in user_clients:
        return HttpResponseForbidden("Not allowed")

    service_type_obj = client_service.service

    gst_detail = client_service.gst_details.first() if hasattr(client_service, "gst_details") else None
    itr_detail = client_service.itr_details.first() if hasattr(client_service, "itr_details") else None
    audit_detail = client_service.audit_details.first() if hasattr(client_service, "audit_details") else None
    income_tax_case = client_service.incometax_case_details.first() if hasattr(client_service,
                                                                               "incometax_case_details") else None
    gst_case = client_service.gst_case_details.first() if hasattr(client_service, "gst_case_details") else None

    context = {
        "task": task,
        "client": client,
        "client_service": client_service,
        "service_type_obj": service_type_obj,
        "gst_detail": gst_detail,
        "itr_detail": itr_detail,
        "audit_detail": audit_detail,
        "income_tax_case": income_tax_case,
        "gst_case": gst_case,
    }
    return render(request, "client/task-detail.html", context)
