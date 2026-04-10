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
            
            # Ensure call_date is timezone-aware (Asia/Kolkata)
            if phone_call.call_date and timezone.is_naive(phone_call.call_date):
                import pytz
                kolkata_tz = pytz.timezone('Asia/Kolkata')
                phone_call.call_date = kolkata_tz.localize(phone_call.call_date)
            
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
        if employee.role in ['ADMIN', 'PARTNER']:
            # Admin and Partner see all logs
            pass
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
    else:
        # Users without employee profile: only own logs
        queryset = queryset.filter(employee=user)
    
    # Apply filters
    client_filter = request.GET.get('client')
    if client_filter:
        queryset = queryset.filter(client_id=client_filter)
    
    employee_filter = request.GET.get('employee')
    if employee_filter:
        queryset = queryset.filter(employee_id=employee_filter)
    
    # Date range filter
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        queryset = queryset.filter(call_date__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(call_date__date__lte=date_to)
    
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
    
    # Pagination
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    per_page = request.GET.get('per_page', '25')  # Default to 10
    if per_page == 'all':
        paginator = Paginator(queryset, queryset.count() or 1)
        page_number = 1
    else:
        try:
            per_page = int(per_page)
        except (ValueError, TypeError):
            per_page = 10  # Default to 10
        paginator = Paginator(queryset, per_page)
        page_number = request.GET.get('page', 1)
    
    try:
        phone_calls = paginator.page(page_number)
    except PageNotAnInteger:
        phone_calls = paginator.page(1)
    except EmptyPage:
        phone_calls = paginator.page(paginator.num_pages)
    
    # Get accessible clients for filter dropdown
    if user.is_superuser:
        accessible_clients = Client.objects.all()
    elif hasattr(user, 'employee') and user.employee.role in ['ADMIN', 'PARTNER']:
        # Admin and Partner see all clients
        accessible_clients = Client.objects.all()
    else:
        # Others see clients based on get_accessible_clients
        accessible_clients = get_accessible_clients(user)
    
    # Get unique employees for filter dropdown based on role
    if user.is_superuser:
        employees = Employee.objects.select_related('user').all()
    elif hasattr(user, 'employee'):
        if user.employee.role in ['ADMIN', 'PARTNER']:
            # Admin and Partner see all employees
            employees = Employee.objects.select_related('user').all()
        elif user.employee.role == 'BRANCH_MANAGER':
            # Branch managers see employees in their branch
            employees = Employee.objects.filter(
                office_location=user.employee.office_location
            ).select_related('user')
        else:
            # Staff see only themselves
            employees = Employee.objects.filter(user=user).select_related('user')
    else:
        employees = Employee.objects.filter(user=user).select_related('user')
    
    # Get unique service types for filter
    service_types = Task.SERVICE_TYPE_CHOICES
    
    # Build query params for pagination (exclude page parameter)
    query_params = request.GET.copy()
    query_params.pop('page', None)
    # Remove empty query parameters
    for key in list(query_params.keys()):
        if not query_params.get(key):
            query_params.pop(key)
    
    # Store per_page as string for template comparison
    per_page_str = str(per_page) if per_page != 'all' else 'all'
    
    context = {
        'phone_calls': phone_calls,
        'clients': accessible_clients,
        'employees': employees,
        'service_types': service_types,
        'today': today,
        'per_page': per_page_str,
        'query_params': query_params.urlencode(),
        # Preserve filter values
        'selected_client': client_filter,
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


@login_required
def add_phone_call_from_list(request):
    """
    Add a phone call log from the phone calls list page.
    Includes client selection field.
    """
    if request.method == 'POST':
        client_id = request.POST.get('client')
        
        if not client_id:
            messages.error(request, 'Please select a client.')
            return redirect('phone_calls_list')
        
        # Ensure client exists (no restrictions - anyone can add for any client)
        client = get_object_or_404(Client, id=client_id)
        
        # Create form with client context
        form = PhoneCallLogForm(request.POST, client=client)
        
        if form.is_valid():
            phone_call = form.save(commit=False)
            phone_call.client = client
            phone_call.employee = request.user
            
            # Ensure call_date is timezone-aware (Asia/Kolkata)
            if phone_call.call_date and timezone.is_naive(phone_call.call_date):
                import pytz
                kolkata_tz = pytz.timezone('Asia/Kolkata')
                phone_call.call_date = kolkata_tz.localize(phone_call.call_date)
            
            phone_call.save()
            
            # Save many-to-many relationship for services
            form.save_m2m()
            
            messages.success(request, f'Phone call log added successfully for {client.client_name}!')
            return redirect('phone_calls_list')
        else:
            messages.error(request, 'Please correct the errors in the form.')
            return redirect('phone_calls_list')
    
    return redirect('phone_calls_list')


@login_required
def search_clients_for_phone_call(request):
    """
    AJAX endpoint to search clients for phone call modal.
    Returns clients in format: client_name || file_no || status
    No restrictions - returns all clients.
    """
    search_term = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = 30
    
    # Base queryset - all clients, ordered by name
    queryset = Client.objects.all().order_by('client_name')
    
    # Apply search filter if search term provided
    if search_term:
        queryset = queryset.filter(
            Q(client_name__icontains=search_term) |
            Q(file_number__icontains=search_term) |
            Q(status__icontains=search_term) |
            Q(pan_no__icontains=search_term)
        )
    
    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    total_count = queryset.count()
    clients = queryset[start:end]
    
    # Format results
    results = []
    for client in clients:
        # Format: Client Name || File No || Status
        display_text = client.client_name
        if client.file_number:
            display_text += f" || {client.file_number}"
        if client.status:
            display_text += f" || {client.status}"
            
        results.append({
            'id': client.id,
            'text': display_text,
            'client_name': client.client_name,
            'file_no': client.file_number or 'N/A',
            'status': client.status or 'N/A'
        })
    
    return JsonResponse({
        'results': results,
        'pagination': {
            'more': end < total_count
        }
    })


@login_required
def get_client_services_for_phone_call(request):
    """
    AJAX endpoint to get services/tasks for a selected client.
    Used when adding phone call from list page.
    """
    client_id = request.GET.get('client_id')
    
    if not client_id:
        return JsonResponse({
            'success': False,
            'error': 'Client ID is required'
        }, status=400)
    
    # Get client (no restrictions)
    client = get_object_or_404(Client, id=client_id)
    
    # Get client's tasks/services
    services = Task.objects.filter(
        client=client
    ).order_by('-created_at')
    
    # Format results
    results = []
    for service in services:
        results.append({
            'id': service.id,
            'text': f"{service.service_type} - {service.task_title}"
        })
    
    return JsonResponse({
        'success': True,
        'services': results
    })

