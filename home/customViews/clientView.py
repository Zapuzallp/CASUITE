from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from home.forms import DocumentRequestForm
from home.models import DocumentRequest, RequestedDocument
from django.shortcuts import render, get_object_or_404
from home.models import Client, ServiceType, ClientService, Task


@login_required
def clientDetails(request, pk):
    # This remains your original client lookup logic (by Django User ID)
    client = User.objects.get(id=pk)

    if request.method == "POST":
        form = DocumentRequestForm(request.POST)
        if form.is_valid():
            doc_req = form.save(commit=False)
            doc_req.client = client
            # 💡 FIX: Correctly set the creator to the logged-in user (request.user)
            doc_req.created_by = request.user
            doc_req.save()

            # Save selected documents
            for doc in form.cleaned_data['documents']:
                RequestedDocument.objects.create(
                    document_request=doc_req,
                    document_master=doc
                )

            messages.success(request, "Document Request created successfully!")
            # UX FIX: Redirect back with the tab anchor
            return redirect(request.path + '#documents')
    else:
        form = DocumentRequestForm()

    return render(request, "client/client-details.html", {
        "client": client,
        "form": form
    })
    client = get_object_or_404(Client, pk=pk)
    available_services = ServiceType.objects.filter(active=True, is_task=False).order_by('service_name')

    # Get client's actual services with related data
    client_services = ClientService.objects.filter(
        client=client,
        is_active=True,
        service__is_task=False
    ).select_related('service').prefetch_related(
        'gst_details',
        'itr_details',
        'audit_details',
        'gst_case_details',
        'incometax_case_details'
    ).order_by('service__service_name')

    # Group services by service type
    grouped_services = {}
    for service in client_services:
        service_name = service.service.service_name
        if service_name not in grouped_services:
            grouped_services[service_name] = []
        grouped_services[service_name].append(service)

    # Service types that are marked as task-only
    task_services = ServiceType.objects.filter(active=True, is_task=True).order_by('service_name')

    # Status filter for tasks
    status_filter = request.GET.get('status', 'all')

    # All tasks for this client
    all_tasks_qs = Task.objects.filter(
        client_service__client=client
    )

    # Filter tasks for display based on status
    if status_filter != 'all':
        tasks_qs = all_tasks_qs.filter(task_status=status_filter)
    else:
        tasks_qs = all_tasks_qs

    # Calculate counts for all statuses
    status_counts = {
        'all': all_tasks_qs.count(),
        'Pending': all_tasks_qs.filter(task_status='Pending').count(),
        'In_Progress': all_tasks_qs.filter(task_status='In Progress').count(),
        'Submitted': all_tasks_qs.filter(task_status='Submitted').count(),
        'Completed': all_tasks_qs.filter(task_status='Completed').count(),
        'Delayed': all_tasks_qs.filter(task_status='Delayed').count(),
        'Cancelled': all_tasks_qs.filter(task_status='Cancelled').count(),
    }

    # Group filtered tasks by service
    grouped_tasks_dict = {}
    for task in tasks_qs.select_related('client_service__service', 'assigned_to').order_by('client_service__service__service_name', 'due_date'):
        service_name = task.client_service.service.service_name
        if service_name not in grouped_tasks_dict:
            grouped_tasks_dict[service_name] = []
        grouped_tasks_dict[service_name].append(task)

    grouped_tasks = []
    for service_name, service_tasks in grouped_tasks_dict.items():
        pending_count_for_service = sum(1 for t in service_tasks if t.task_status == 'Pending')
        grouped_tasks.append({
            'service_name': service_name,
            'tasks': service_tasks,
            'pending_count': pending_count_for_service,
            'total_count': len(service_tasks),
        })
    grouped_tasks.sort(key=lambda g: g['service_name'])

    context = {
        'client': client,
        'available_services': available_services,
        'client_services': client_services,
        'grouped_services': grouped_services,
        'task_services': task_services,
        'grouped_tasks': grouped_tasks,
        'total_tasks': status_counts['all'],
        'pending_tasks': status_counts['Pending'],
        'completed_tasks': status_counts['Completed'],
        'status_counts': status_counts,
        'status_filter': status_filter,
    }
    return render(request, "client/client-details.html", context)
