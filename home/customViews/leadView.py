from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import timedelta
from django.contrib.auth.models import User

from home.models import Lead, LeadCallLog
from home.forms import LeadForm


def get_accessible_leads(user):
    """
    Returns leads accessible to the user based on their role:
    - Admin/Superuser: All leads
    - Branch Manager: Leads from their branch + assigned to them + created by them
    - Staff: Leads assigned to them OR created by them
    """
    if user.is_superuser:
        return Lead.objects.all()

    try:
        employee = user.employee
        role = employee.role

        if role == 'ADMIN':
            # Admin can see all leads
            return Lead.objects.all()
        elif role == 'BRANCH_MANAGER':
            # Branch manager can see leads from their branch + assigned to them + created by them
            office = employee.office_location
            if office:
                # Get leads created by users in the same office OR assigned to this manager OR created by this manager
                return Lead.objects.filter(
                    Q(created_by__employee__office_location=office) |
                    Q(assigned_to=user) |
                    Q(created_by=user)
                ).distinct()
            else:
                # If no office, show assigned + created leads
                return Lead.objects.filter(
                    Q(assigned_to=user) |
                    Q(created_by=user)
                ).distinct()
        else:
            # Staff can see leads assigned to them OR created by them
            return Lead.objects.filter(
                Q(assigned_to=user) |
                Q(created_by=user)
            ).distinct()
    except:
        # If no employee profile, only show assigned + created leads
        return Lead.objects.filter(
            Q(assigned_to=user) |
            Q(created_by=user)
        ).distinct()


@login_required
def lead_list_view(request):
    """List all leads with filtering based on user role"""
    leads = get_accessible_leads(request.user).select_related('created_by').prefetch_related('assigned_to')

    # Apply filters
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    assigned_filter = request.GET.get('assigned_to', '').strip()

    if search_query:
        leads = leads.filter(
            Q(lead_name__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    if status_filter:
        leads = leads.filter(status=status_filter)

    if assigned_filter:
        leads = leads.filter(assigned_to__id=assigned_filter)

    # Get filter choices
    from django.contrib.auth.models import User
    assigned_users = User.objects.filter(is_active=True).order_by('username')

    context = {
        'leads': leads,
        'status_choices': Lead.STATUS_CHOICES,
        'assigned_users': assigned_users,
        'search_query': search_query,
        'status_filter': status_filter,
        'assigned_filter': assigned_filter,
    }

    return render(request, 'leads/lead_list.html', context)


@login_required
def add_lead_view(request):
    """Add a new lead and auto-assign to creator"""
    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.created_by = request.user
            lead.save()
            # Auto-assign the lead to the creator
            lead.assigned_to.add(request.user)
            messages.success(request, f'Lead "{lead.lead_name}" created successfully!')
            return redirect('lead_list')
    else:
        form = LeadForm()

    context = {
        'form': form,
        'page_title': 'Add New Lead',
    }
    return render(request, 'leads/add_lead.html', context)


@login_required
def edit_lead_view(request, lead_id):
    """Edit an existing lead (only if status is New, Contacted, or Qualified)"""
    lead = get_object_or_404(Lead, id=lead_id)

    # Check if user has access to this lead
    accessible_leads = get_accessible_leads(request.user)
    if not accessible_leads.filter(id=lead.id).exists():
        messages.error(request, 'You do not have permission to edit this lead.')
        return redirect('lead_list')

    # Check if lead is editable
    if not lead.is_editable():
        messages.error(request, f'Cannot edit lead in "{lead.status}" status.')
        return redirect('lead_detail', lead_id=lead.id)

    if request.method == 'POST':
        form = LeadForm(request.POST, instance=lead)
        if form.is_valid():
            form.save()
            messages.success(request, f'Lead "{lead.lead_name}" updated successfully!')
            return redirect('lead_detail', lead_id=lead.id)
    else:
        form = LeadForm(instance=lead)

    context = {
        'form': form,
        'lead': lead,
        'page_title': 'Edit Lead',
    }
    return render(request, 'leads/edit_lead.html', context)


@login_required
def lead_detail_view(request, lead_id):
    """View lead details"""
    lead = get_object_or_404(Lead.objects.select_related('created_by', 'client').prefetch_related('assigned_to'),
                             id=lead_id)

    # Check if user has access to this lead
    accessible_leads = get_accessible_leads(request.user)
    if not accessible_leads.filter(id=lead.id).exists():
        messages.error(request, 'You do not have permission to view this lead.')
        return redirect('lead_list')

    # Get call logs for this lead
    call_logs = lead.call_logs.select_related('called_by_user', 'called_to_user', 'created_by').all()

    # Check if user can add call logs (creator, assigned users, branch manager, or admin)
    can_add_call_log = False
    if request.user.is_superuser:
        can_add_call_log = True
    elif lead.created_by == request.user or request.user in lead.assigned_to.all():
        can_add_call_log = True
    else:
        try:
            employee = request.user.employee
            if employee.role in ['ADMIN', 'BRANCH_MANAGER']:
                # Branch manager can add if lead is from their office
                if employee.role == 'BRANCH_MANAGER' and employee.office_location:
                    if lead.created_by and hasattr(lead.created_by, 'employee'):
                        if lead.created_by.employee.office_location == employee.office_location:
                            can_add_call_log = True
                else:
                    can_add_call_log = True
        except:
            pass

    # Get authorized users for dropdown (creator + assigned users + branch manager if applicable)
    authorized_users = set()
    if lead.created_by:
        authorized_users.add(lead.created_by)
    authorized_users.update(lead.assigned_to.all())

    # Add branch manager if applicable
    if lead.created_by and hasattr(lead.created_by, 'employee'):
        office = lead.created_by.employee.office_location
        if office:
            from django.contrib.auth.models import User
            branch_managers = User.objects.filter(
                employee__role='BRANCH_MANAGER',
                employee__office_location=office
            )
            authorized_users.update(branch_managers)

    context = {
        'lead': lead,
        'call_logs': call_logs,
        'can_add_call_log': can_add_call_log,
        'authorized_users': sorted(authorized_users, key=lambda u: u.get_full_name() or u.username),
    }
    return render(request, 'leads/lead_detail.html', context)


@login_required
@require_POST
def mark_lead_contacted(request, lead_id):
    """Mark lead as Contacted"""
    lead = get_object_or_404(Lead, id=lead_id)

    # Check if user has access to this lead
    accessible_leads = get_accessible_leads(request.user)
    if not accessible_leads.filter(id=lead.id).exists():
        messages.error(request, 'You do not have permission to update this lead.')
        return redirect('lead_list')

    if lead.status != 'New':
        messages.error(request, 'Can only mark New leads as Contacted.')
        return redirect('lead_detail', lead_id=lead.id)

    lead.status = 'Contacted'
    lead.save()
    messages.success(request, f'Lead "{lead.lead_name}" marked as Contacted.')
    return redirect('lead_detail', lead_id=lead.id)


@login_required
@require_POST
def mark_lead_qualified(request, lead_id):
    """Mark lead as Qualified"""
    lead = get_object_or_404(Lead, id=lead_id)

    # Check if user has access to this lead
    accessible_leads = get_accessible_leads(request.user)
    if not accessible_leads.filter(id=lead.id).exists():
        messages.error(request, 'You do not have permission to update this lead.')
        return redirect('lead_list')

    if lead.status != 'Contacted':
        messages.error(request, 'Can only mark Contacted leads as Qualified.')
        return redirect('lead_detail', lead_id=lead.id)

    lead.status = 'Qualified'
    lead.save()
    messages.success(request, f'Lead "{lead.lead_name}" marked as Qualified.')
    return redirect('lead_detail', lead_id=lead.id)


@login_required
@require_POST
def mark_lead_lost(request, lead_id):
    """Mark lead as Lost with reason"""
    lead = get_object_or_404(Lead, id=lead_id)

    # Check if user has access to this lead
    accessible_leads = get_accessible_leads(request.user)
    if not accessible_leads.filter(id=lead.id).exists():
        messages.error(request, 'You do not have permission to update this lead.')
        return redirect('lead_list')

    # Can mark as Lost from New, Contacted, or Qualified
    if lead.status not in ['New', 'Contacted', 'Qualified']:
        messages.error(request, f'Cannot mark lead as Lost from "{lead.status}" status.')
        return redirect('lead_detail', lead_id=lead.id)

    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, 'Please provide a reason for marking the lead as Lost.')
        return redirect('lead_detail', lead_id=lead.id)

    lead.status = 'Lost'
    lead.remarks = reason
    lead.actual_closure_date = timezone.now().date()
    lead.save()

    messages.success(request, f'Lead "{lead.lead_name}" marked as Lost.')
    return redirect('lead_detail', lead_id=lead.id)


@login_required
def convert_lead_view(request, lead_id):
    """Convert lead to client - redirect to onboarding with prefilled data"""
    lead = get_object_or_404(Lead, id=lead_id)

    # Check if user has access to this lead
    accessible_leads = get_accessible_leads(request.user)
    if not accessible_leads.filter(id=lead.id).exists():
        messages.error(request, 'You do not have permission to convert this lead.')
        return redirect('lead_list')

    # Check if lead is qualified
    if lead.status != 'Qualified':
        messages.error(request, 'Can only convert Qualified leads.')
        return redirect('lead_detail', lead_id=lead.id)

    # Check if already converted
    if lead.client:
        messages.warning(request, f'This lead has already been converted to client: {lead.client.client_name}')
        return redirect('client_details', client_id=lead.client.id)

    # Redirect to onboarding form with lead_id
    messages.info(request, f'Converting lead "{lead.lead_name}" to client. Please complete the onboarding form.')
    return redirect(f'/onboard/?lead_id={lead.id}')


@login_required
@require_POST
def add_lead_call_log(request, lead_id):
    """Add a new call log for a lead"""
    lead = get_object_or_404(Lead, id=lead_id)

    # Check if user has access to this lead
    accessible_leads = get_accessible_leads(request.user)
    if not accessible_leads.filter(id=lead.id).exists():
        return JsonResponse({'success': False, 'error': 'You do not have permission to add call logs for this lead.'},
                            status=403)

    # Verify user can add call logs
    can_add = False
    if request.user.is_superuser:
        can_add = True
    elif lead.created_by == request.user or request.user in lead.assigned_to.all():
        can_add = True
    else:
        try:
            employee = request.user.employee
            if employee.role in ['ADMIN', 'BRANCH_MANAGER']:
                if employee.role == 'BRANCH_MANAGER' and employee.office_location:
                    if lead.created_by and hasattr(lead.created_by, 'employee'):
                        if lead.created_by.employee.office_location == employee.office_location:
                            can_add = True
                else:
                    can_add = True
        except:
            pass

    if not can_add:
        return JsonResponse({'success': False, 'error': 'You do not have permission to add call logs.'}, status=403)

    # Get form data
    called_by = request.POST.get('called_by')
    called_to = request.POST.get('called_to')
    duration_minutes = request.POST.get('duration_minutes')
    description = request.POST.get('description', '').strip()

    # Validate inputs
    if not called_by or not called_to:
        return JsonResponse({'success': False, 'error': 'Please select both caller and receiver.'}, status=400)

    if not duration_minutes:
        return JsonResponse({'success': False, 'error': 'Please enter call duration.'}, status=400)

    if not description:
        return JsonResponse({'success': False, 'error': 'Please provide a description of the call.'}, status=400)

    try:
        duration_minutes = int(duration_minutes)
        if duration_minutes <= 0:
            return JsonResponse({'success': False, 'error': 'Duration must be greater than 0.'}, status=400)
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid duration value.'}, status=400)

    # Determine direction
    called_by_user = None
    called_to_user = None

    if called_by == 'lead':
        # Lead called an employee
        if called_to == 'lead':
            return JsonResponse({'success': False, 'error': 'Invalid selection: Lead cannot call Lead.'}, status=400)
        try:
            called_to_user = User.objects.get(id=int(called_to))
        except (ValueError, User.DoesNotExist):
            return JsonResponse({'success': False, 'error': 'Invalid employee selection.'}, status=400)
    else:
        # Employee called the lead
        try:
            called_by_user = User.objects.get(id=int(called_by))
        except (ValueError, User.DoesNotExist):
            return JsonResponse({'success': False, 'error': 'Invalid employee selection.'}, status=400)

        if called_to != 'lead':
            return JsonResponse({'success': False, 'error': 'When employee calls, the receiver must be the Lead.'},
                                status=400)

    # Create call log
    try:
        call_log = LeadCallLog.objects.create(
            lead=lead,
            called_by_user=called_by_user,
            called_to_user=called_to_user,
            call_duration=timedelta(minutes=duration_minutes),
            description=description,
            created_by=request.user
        )

        messages.success(request, 'Call log added successfully!')
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error creating call log: {str(e)}'}, status=500)
