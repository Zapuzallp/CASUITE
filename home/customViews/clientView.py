from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from home.models import Client, ServiceType, ClientService


@login_required
def clientDetails(request, pk):
    client = get_object_or_404(Client, pk=pk)
    available_services = ServiceType.objects.filter(active=True).order_by('service_name')

    # Get client's actual services with related data
    client_services = ClientService.objects.filter(
        client=client,
        is_active=True
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

    context = {
        'client': client,
        'available_services': available_services,
        'client_services': client_services,
        'grouped_services': grouped_services,
    }
    return render(request, "client/client-details.html", context)
