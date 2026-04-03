from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Q, Prefetch
from django.utils import timezone
from datetime import timedelta

from home.models import Client, PhoneCallLog, Task, Employee
from home.forms import PhoneCallLogForm
from home.clients.client_access import get_accessible_clients


@login_required
def add_phone_call_log(request, client_id):
    """
    Add a phone call log for a specific client.
    Only accessible via POST from client details page.
    Partners can add logs for their assigned clients.
    """
    # Ensure client exists and user has access
    accessible_clients = get_accessible_clients(request.user)
    client = get_object_or_404(accessible_clients, id=client_id)
    
    if request.method == 'POST':
        form = PhoneCallLogForm(request.POST, client=client)
        if form.is_valid():
            phone_call = form.save(commit=False)
            phone_call.client = client
            phone_call.employee = request.user
            phone_call.save()
            
            # Save many-to-many relationship for services
            form.save_m2m()
            
            messages.success(request, 'Phone call log added successfully!')
            return redirect('client_details', client_id=client.id)
        else:
            # Return errors as JSON for AJAX handling
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
            else:
                messages.error(request, 'Please correct the errors below.')
    
    return redirect('client_details', client_id=client_id)


@login_required
def phone_call_logs_list(request):
    """
    Main page showing all phone call logs with filters.
    Implements role-based access control.
    """
    user = request.user
    
    # Base queryset with optimizations
    queryset = PhoneCallLog.objects.select_related(
        'client', 'employee', 'employee__employee'
    ).prefetch_related(
        Prefetch('services', queryset=Task.objects.only('id', 'service_type', 'task_title'))
    )
    
    # Role-based filtering
    if user.is_superuser:
        # Superuser sees all logs
        pass
    elif hasattr(user, 'employee'):
        employee = user.employee
        if employee.role == 'PARTNER':
            # Partners see logs for their assigned clients only
            accessible_clients = get_accessible_clients(user)
            queryset = queryset.filter(client__in=accessible_clients)
        elif employee.role == 'BRANCH_MANAGER':
            # Branch managers see logs from their branch employees
            branch_users = Employee.objects.filter(
                office_location=employee.office_location
            ).values_list('user_id', flat=True)
            queryset = queryset.filter(employee_id__in=branch_users)
        elif employee.role == 'STAFF':
            # Staff see only their own logs
            queryset = queryset.filter(employee=user)
    else:
        # Default: only own logs
        queryset = queryset.filter(employee=user)
    
    # Apply filters
    employee_filter = request.GET.get('employee')
    if employee_filter:
        queryset = queryset.filter(employee_id=employee_filter)
    
    # Date range filter
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        queryset = queryset.filter(call_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(call_date__lte=date_to)
    
    # Service type filter
    service_type = request.GET.get('service_type')
    if service_type:
        queryset = queryset.filter(services__service_type=service_type).distinct()
    
    # Feedback filter
    feedback = request.GET.get('feedback')
    if feedback:
        queryset = queryset.filter(feedback=feedback)
    
    # Follow-up status filter
    follow_up_status = request.GET.get('follow_up_status')
    today = timezone.now().date()
    
    if follow_up_status == 'overdue':
        queryset = queryset.filter(
            next_follow_up_date__lt=today,
            next_follow_up_date__isnull=False
        )
    elif follow_up_status == 'today':
        queryset = queryset.filter(next_follow_up_date=today)
    elif follow_up_status == 'tomorrow':
        tomorrow = today + timedelta(days=1)
        queryset = queryset.filter(next_follow_up_date=tomorrow)
    elif follow_up_status == 'next_7_days':
        next_week = today + timedelta(days=7)
        queryset = queryset.filter(
            next_follow_up_date__range=(today, next_week),
            next_follow_up_date__isnull=False
        )
    
    # Order by latest first
    queryset = queryset.order_by('-call_date', '-created_at')
    
    # Get unique employees for filter dropdown based on role
    if user.is_superuser:
        employees = Employee.objects.select_related('user').all()
    elif hasattr(user, 'employee'):
        if user.employee.role == 'PARTNER':
            # Partners see only employees assigned to their accessible clients
            accessible_clients = get_accessible_clients(user)
            assigned_user_ids = accessible_clients.values_list('assigned_ca_id', flat=True).distinct()
            employees = Employee.objects.filter(
                user_id__in=assigned_user_ids
            ).select_related('user')
        elif user.employee.role == 'BRANCH_MANAGER':
            employees = Employee.objects.filter(
                office_location=user.employee.office_location
            ).select_related('user')
        else:
            employees = Employee.objects.filter(user=user).select_related('user')
    else:
        employees = Employee.objects.filter(user=user).select_related('user')
    
    # Get unique service types for filter
    service_types = Task.SERVICE_TYPE_CHOICES
    
    context = {
        'phone_calls': queryset,
        'employees': employees,
        'service_types': service_types,
        'today': today,
        # Preserve filter values
        'selected_employee': employee_filter,
        'selected_service_type': service_type,
        'selected_feedback': feedback,
        'selected_follow_up_status': follow_up_status,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'phone_calls/phone_calls_list.html', context)


@login_required
def get_client_phone_calls_ajax(request, client_id):
    """
    AJAX endpoint to get phone call logs for a specific client.
    Used for DataTables server-side processing in client details page.
    """
    # Ensure client exists and user has access
    accessible_clients = get_accessible_clients(request.user)
    client = get_object_or_404(accessible_clients, id=client_id)
    
    # Get phone calls for this client
    phone_calls = PhoneCallLog.objects.filter(
        client=client
    ).select_related(
        'employee', 'employee__employee'
    ).prefetch_related(
        'services'
    ).order_by('-call_date', '-created_at')
    
    # Build response data
    data = []
    for call in phone_calls:
        services_list = [f"{s.service_type}" for s in call.services.all()[:3]]
        if call.services.count() > 3:
            services_list.append(f"+{call.services.count() - 3} more")
        
        # Determine follow-up status
        follow_up_status = ''
        if call.next_follow_up_date:
            if call.is_follow_up_overdue():
                follow_up_status = 'overdue'
            elif call.is_follow_up_today():
                follow_up_status = 'today'
            else:
                follow_up_status = 'scheduled'
        
        data.append({
            'id': call.id,
            'call_date': call.call_date.strftime('%b %d, %Y'),
            'employee': call.employee.get_full_name() or call.employee.username,
            'services': ', '.join(services_list),
            'remarks': call.remarks[:100] + '...' if len(call.remarks) > 100 else call.remarks,
            'feedback': call.feedback,
            'next_follow_up_date': call.next_follow_up_date.strftime('%b %d, %Y') if call.next_follow_up_date else '-',
            'follow_up_status': follow_up_status,
            'created_at': call.created_at.strftime('%b %d, %Y %I:%M %p'),
        })
    
    return JsonResponse({
        'success': True,
        'data': data
    })
