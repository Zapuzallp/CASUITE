from django.contrib.auth.decorators import login_required
from django.shortcuts import render, HttpResponse
from ..models import Client, PrivateLimitedDetails, LLPDetails, OPCDetails, GSTDetails, AuditDetails, ITRDetails, ClientService
from datetime import datetime, date, time, timedelta
from django.shortcuts import render, get_object_or_404
from home.models import Client, ServiceType, ClientService, Task


@login_required
def clientDetails(request, pk):

    if request.user.is_staff == True:
        try:
            client = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            return HttpResponse("Invalid client - page will render here")

        client_since_year = None
        client_since_month = None
        client_since_date = None


        current_year = datetime.now().year
        client_year = client.created_at.year

        if current_year == client_year:
            current_month = datetime.now().month
            client_month = client.created_at.month
            client_since_month = client_month - current_month

            if current_month == client_month:
                current_date = datetime.now().date().day
                client_date = client.created_at.date().day
                client_since_date = current_date - client_date
        else:
            client_since_year = client_year-current_year


        PVT = PrivateLimitedDetails.objects.filter(directors=client)
        LLP = LLPDetails.objects.filter(client=client)
        OPC = OPCDetails.objects.filter(client=client)

        ClientServices = ClientService.objects.filter(client=client)

        GSTList = []
        AuditList = []
        ITRList = []

        for service in ClientServices:
            GST = GSTDetails.objects.filter(client_service=service)
            Audit = AuditDetails.objects.filter(client_service=service)
            ITR = ITRDetails.objects.filter(client_service=service)

            GSTList += GST
            AuditList += Audit
            ITRList += ITR

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
            "PVT":PVT,
            "LLP":LLP,
            "OPC":OPC,
            "GST":GSTList,
            "Audit":AuditList,
            "ITR":ITRList,
            "client_since_month":client_since_month,
            "client_since_year":client_since_year,
             "client_since_date":client_since_date,
        }
        return render(request, "client/client-details.html", context)
    return HttpResponse("You are not authorized")
