from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from home.forms import DocumentUploadForm, DocumentRequestForm, RequestedDocument, GSTDetails, GSTDetailsForm
from home.clients.client_access import get_accessible_clients
from home.models import Client, Task  # Import your other models as needed


def get_dynamic_fields(instance):
    """
    Helper function to extract all non-empty fields from a model instance.
    Returns a list of dictionaries: [{'label': 'Field Name', 'value': 'Value'}]
    """
    data = []
    # Exclude technical fields you never want to show
    exclude_fields = ['id', 'password', 'created_by', 'created_at', 'updated_at', 'is_staff', 'is_superuser']

    for field in instance._meta.fields:
        if field.name not in exclude_fields:
            try:
                # Get the value
                val = getattr(instance, field.name)

                # Check if it has a value (is not None or Empty string)
                if val is not None and val != '':

                    # Handle Choices (get_FOO_display)
                    if field.choices:
                        display_val = getattr(instance, f'get_{field.name}_display')()
                    else:
                        display_val = val

                    # Handle ManyToMany or ForeignKeys if needed
                    data.append({
                        'label': field.verbose_name.title(),
                        'value': display_val,
                        'name': field.name
                    })
            except AttributeError:
                continue
    return data


@login_required
def client_details_view(request, client_id):
    """
    View to show detailed information of a specific client.
    Implements Role-Based Access Control similar to ClientView.
    """
    user = request.user
    # --- Role-Based Permission Logic ---
    # Fetch only those clients the current user is allowed to access
    # (based on role, assignment, or admin privileges)
    accessible_clients = get_accessible_clients(user)
    # Ensure the requested client exists AND is within the user's allowed scope
    # This prevents unauthorized users from accessing other clients' data
    client = get_object_or_404(accessible_clients, id=client_id)

    # 1. Dynamic Basic Info & Linked Data
    # Note: Ensure get_dynamic_fields is imported or defined
    client_fields = get_dynamic_fields(client)
    entity_profile_fields = []
    if hasattr(client, 'business_profile'):
        entity_profile_fields = get_dynamic_fields(client.business_profile)
    linked_data = []
    link_type = 'businesses' if client.client_type == 'Individual' else 'associates'

    if client.client_type == 'Individual':
        linked_data = client.associated_entities.select_related('client').all()
    elif hasattr(client, 'business_profile'):
        linked_data = client.business_profile.key_persons.all()

    # 2. Services
    services = Task.objects.filter(client=client).order_by('-created_at')

    # 3. Documents
    unified_documents = []

    # A. Add Entity Constitution Documents (from Profile)
    if hasattr(client, 'business_profile'):
        prof = client.business_profile
        doc_date = getattr(prof, 'updated_at', client.updated_at)

        if prof.constitution_document_1:
            unified_documents.append({
                'name': 'Constitution Document (MOA/Deed)',
                'category': 'Registration',
                'url': prof.constitution_document_1.url,
                'date': doc_date,
                'type': 'system'
            })

        if prof.constitution_document_2:
            unified_documents.append({
                'name': 'Articles / By-Laws (AOA)',
                'category': 'Registration',
                'url': prof.constitution_document_2.url,
                'date': doc_date,
                'type': 'system'
            })

    # B. Add Repository Documents
    uploads = client.document_uploads.select_related('requested_document__document_master').all()

    for upload in uploads:
        if upload.requested_document and upload.requested_document.document_master:
            doc_name = upload.requested_document.document_master.document_name
            category = upload.requested_document.document_master.category
        else:
            doc_name = f"Upload #{upload.id}"
            category = "General"

        unified_documents.append({
            'name': doc_name,
            'category': category,
            'url': upload.uploaded_file.url,
            'date': upload.upload_date,
            'type': 'uploaded'
        })

    # Safe Sort
    unified_documents.sort(
        key=lambda x: x.get('date') or timezone.now(),
        reverse=True
    )

    # Forms and Pending Requests
    upload_form = DocumentUploadForm(client_id=client.id)
    request_form = DocumentRequestForm()
    pending_requests = RequestedDocument.objects.filter(
        document_request__client_id=client_id
    ).exclude(
        uploads__status='Uploaded'
    ).select_related('document_request', 'document_master').order_by('document_request__due_date')

    # === GST LOGIC ===
    gst_details_list = GSTDetails.objects.filter(client=client).order_by('-id')
    gst_form = GSTDetailsForm()
    # =================

    # === INVOICES LOGIC ===
    from django.db.models import Sum
    from decimal import Decimal
    invoices = client.invoices.all().order_by('-invoice_date')
    invoices_data = []
    today = timezone.now().date()

    for inv in invoices:
        # Calculate total_paid from payments
        total_paid = inv.payments.filter(payment_status='PAID').aggregate(
            total=Sum('amount'))['total'] or Decimal('0')

        # Calculate total_amount from invoice items
        total_amount_raw = inv.items.aggregate(total=Sum('net_total'))['total'] or 0
        total_amount = Decimal(str(total_amount_raw))

        balance = total_amount - total_paid

        # Calculate Payment Status (business status)
        if inv.invoice_status == 'DRAFT':
            payment_status = 'DRAFT'
            payment_status_display = 'Draft'
        elif total_paid == 0:
            payment_status = 'OPEN'
            payment_status_display = 'Open'
        elif total_paid >= total_amount:
            payment_status = 'PAID'
            payment_status_display = 'Paid'
        else:
            payment_status = 'PARTIALLY_PAID'
            payment_status_display = 'Partially Paid'

        # Calculate Due Status (time-based status)
        # Only show due status for Open and Partially Paid invoices
        due_status = None
        if payment_status in ['OPEN', 'PARTIALLY_PAID'] and inv.due_date:
            if inv.due_date < today:
                due_status = 'overdue'
            elif inv.due_date == today:
                due_status = 'due_today'
            else:
                due_status = 'not_due'

        # Check if invoice has any payments
        has_payments = inv.payments.filter(payment_status='PAID').exists()

        invoices_data.append({
            'invoice': inv,
            'total_amount': total_amount,
            'total_paid': total_paid,
            'balance': balance,
            'payment_status': payment_status,
            'payment_status_display': payment_status_display,
            'due_status': due_status,
            'has_payments': has_payments,
        })
    # ===================

    # === PORTAL CREDENTIALS LOGIC ===
    from home.models import ClientPortalCredentials
    from home.forms import ClientPortalCredentialsForm
    portal_credentials = ClientPortalCredentials.objects.filter(client=client).select_related('dropdown').order_by('-created_at')
    credential_form = ClientPortalCredentialsForm(client=client)
    # =================================

    # === PHONE CALL LOGS LOGIC ===
    from home.models import PhoneCallLog
    from home.forms import PhoneCallLogForm
    # For server-side pagination, we still need to pass phone_calls for the template structure
    # but DataTables will fetch actual data via AJAX
    phone_calls = PhoneCallLog.objects.filter(client=client).select_related(
        'employee', 'employee__employee'
    ).prefetch_related('services').order_by('-call_date', '-created_at')
    phone_call_form = PhoneCallLogForm(client=client)
    # =============================

    # Check if user is a partner (view-only access)
    is_partner = False
    can_edit_client = True
    if hasattr(user, 'employee'):
        is_partner = user.employee.role == 'PARTNER'
        if is_partner:
            # Partner can edit ONLY IF they onboarded the client OR are assigned to the client
            can_edit_client = (client.created_by == user or client.assigned_ca == user)

    # === STATUS CHOICES FOR SWEETALERT ===
    status_choices = Client.STATUS_CHOICES

    context = {
        'client': client,
        'client_fields': client_fields,
        'entity_profile_fields': entity_profile_fields,
        'linked_data': linked_data,
        'link_type': link_type,
        'services': services,
        'documents': unified_documents,
        'upload_form': upload_form,
        'request_form': request_form,
        'pending_requests': pending_requests,
        'today': timezone.now().date(),
        'gst_details_list': gst_details_list,  # Include List
        'gst_form': gst_form,  # Include Form
        'invoices_data': invoices_data,  # Include Invoices
        'portal_credentials': portal_credentials,  # Include Portal Credentials
        'credential_form': credential_form,  # Include Credential Form
        'phone_calls': phone_calls,  # Include Phone Calls
        'phone_call_form': phone_call_form,  # Include Phone Call Form
        'status_choices': status_choices,
        'is_partner': is_partner,  # Add partner flag
        'can_edit_client': can_edit_client,  # Add edit permission flag
    }

    return render(request, 'client/client-details.html', context)


# ---------------------------------------------------------
# NEW: GST Management Views
# ---------------------------------------------------------

@login_required
def add_gst_details_view(request, client_id):
    client = get_object_or_404(Client, id=client_id)

    # Check if user is a partner - deny access
    if hasattr(request.user, 'employee') and request.user.employee.role == 'PARTNER':
        messages.error(request, 'You do not have permission to add GST details.')
        return redirect('client_details', client_id=client.id)

    if request.method == 'POST':
        form = GSTDetailsForm(request.POST)
        if form.is_valid():
            gst_instance = form.save(commit=False)
            gst_instance.client = client

            # --- AUTO-FILL LOGGED-IN USER ---
            gst_instance.created_by = request.user
            # --------------------------------

            gst_instance.save()
            return redirect('client_details', client_id=client.id)

    return redirect('client_details', client_id=client.id)


@login_required
def edit_gst_details_view(request, gst_id):
    gst_instance = get_object_or_404(GSTDetails, id=gst_id)
    client_id = gst_instance.client.id

    # Check if user is a partner - deny access
    if hasattr(request.user, 'employee') and request.user.employee.role == 'PARTNER':
        messages.error(request, 'You do not have permission to edit GST details.')
        return redirect('client_details', client_id=client_id)

    # Permission Check
    if not (request.user.is_superuser or request.user == gst_instance.client.assigned_ca):
        pass  # Handle permission error if needed

    if request.method == 'POST':
        form = GSTDetailsForm(request.POST, instance=gst_instance)
        if form.is_valid():
            form.save()
            return redirect('client_details', client_id=client_id)
    else:
        form = GSTDetailsForm(instance=gst_instance)

    return render(request, 'client/edit_gst_form.html', {'form': form, 'client': gst_instance.client})

@login_required
def delete_gst_details_view(request, gst_id):
    gst_instance = get_object_or_404(GSTDetails, id=gst_id)
    client_id = gst_instance.client.id

    # Permission Check
    if not (request.user.is_superuser or request.user == gst_instance.client.assigned_ca):
        return redirect('client_details', client_id=client_id)

    if request.method == "POST":
        gst_instance.delete()
        messages.success(request, "GST details deleted successfully.")
        return redirect('client_details', client_id=client_id)

    return redirect('client_details', client_id=client_id)

@login_required
def update_single_client_status(request, client_id):

    client = get_object_or_404(Client, id=client_id)

    user = request.user
    employee = getattr(user, "employee", None)

    # ---- PERMISSION LOGIC ----

    allowed = False

    # Superuser always allowed
    if user.is_superuser:
        allowed = True

    # Branch Manager logic
    elif employee and employee.role == "BRANCH_MANAGER" and employee.office_location == client.office_location:
        allowed = True

    if not allowed:
        messages.error(request, "You do not have permission to update this client.")
        return redirect("client_details", client_id=client.id)

    if request.method == "POST":
        new_status = request.POST.get("new_status")

        if new_status:
            client.status = new_status
            client.save()

            messages.success(request, "Client status updated successfully.")

    return redirect("client_details", client_id=client.id)


@login_required
def bulk_update_client_status(request):

    if request.method != "POST":
        return redirect("clients")

    client_ids = request.POST.getlist("client_ids")
    new_status = request.POST.get("new_status")

    if not client_ids:
        messages.error(request, "No clients selected.")
        return redirect("clients")

    if not new_status:
        messages.error(request, "Please select a status.")
        return redirect("clients")

    valid_statuses = [choice[0] for choice in Client.STATUS_CHOICES]

    if new_status not in valid_statuses:
        messages.error(request, "Invalid status selected.")
        return redirect("clients")

    user = request.user
    employee = getattr(user, "employee", None)

    clients = Client.objects.filter(id__in=client_ids)

    updated_count = 0

    for client in clients:

        allowed = False

        if user.is_superuser:
            allowed = True


        elif employee and employee.role == "BRANCH_MANAGER" and employee.office_location == client.office_location:
            allowed = True

        if allowed:
            client.status = new_status
            client.save()
            updated_count += 1

    if updated_count == 0:
        messages.warning(request, "No clients were updated.")

    else:
        messages.success(request, f"{updated_count} client(s) updated successfully.")

    return redirect("clients")



@login_required
def client_phone_calls_ajax(request, client_id):
    """
    AJAX endpoint for server-side DataTables pagination of phone call logs.
    Returns JSON data for DataTables with server-side processing.
    """
    from django.http import JsonResponse
    from django.db.models import Q
    
    user = request.user
    accessible_clients = get_accessible_clients(user)
    client = get_object_or_404(accessible_clients, id=client_id)
    
    # DataTables parameters
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 25))
    search_value = request.GET.get('search[value]', '')
    order_column_index = int(request.GET.get('order[0][column]', 0))
    order_direction = request.GET.get('order[0][dir]', 'desc')
    
    # Base queryset
    queryset = PhoneCallLog.objects.filter(client=client).select_related(
        'employee', 'employee__employee'
    ).prefetch_related('services')
    
    # Search functionality
    if search_value:
        queryset = queryset.filter(
            Q(employee__first_name__icontains=search_value) |
            Q(employee__last_name__icontains=search_value) |
            Q(employee__username__icontains=search_value) |
            Q(remarks__icontains=search_value) |
            Q(feedback__icontains=search_value) |
            Q(services__service_type__icontains=search_value)
        ).distinct()
    
    # Total records before filtering
    total_records = PhoneCallLog.objects.filter(client=client).count()
    filtered_records = queryset.count()
    
    # Ordering
    order_columns = ['call_date', 'employee__first_name', 'services', 'remarks', 'next_follow_up_date', 'feedback']
    if 0 <= order_column_index < len(order_columns):
        order_field = order_columns[order_column_index]
        # For call_date, add created_at as secondary sort
        if order_field == 'call_date':
            if order_direction == 'desc':
                queryset = queryset.order_by('-call_date', '-created_at')
            else:
                queryset = queryset.order_by('call_date', 'created_at')
        else:
            if order_direction == 'desc':
                order_field = f'-{order_field}'
            queryset = queryset.order_by(order_field, '-call_date', '-created_at')
    else:
        # Default: Latest records first
        queryset = queryset.order_by('-call_date', '-created_at')
    
    # Pagination
    phone_calls = queryset[start:start + length]
    
    # Prepare data
    data = []
    today = timezone.now().date()
    
    for call in phone_calls:
        # Get services
        services_list = list(call.services.all()[:3])
        services_html = ''.join([
            f'<span class="badge bg-light text-dark border me-1">{s.service_type}</span>'
            for s in services_list
        ])
        if call.services.count() > 3:
            services_html += f'<span class="badge bg-secondary">+{call.services.count() - 3}</span>'
        
        # Next follow-up
        if call.next_follow_up_date:
            is_overdue = call.next_follow_up_date < today
            is_today = call.next_follow_up_date == today
            follow_up_class = 'text-danger fw-bold' if is_overdue else ('text-warning fw-bold' if is_today else '')
            follow_up_icon = '<i class="bi bi-exclamation-triangle-fill text-danger"></i>' if is_overdue else (
                '<i class="bi bi-clock-fill text-warning"></i>' if is_today else ''
            )
            follow_up_html = f'<span class="{follow_up_class}">{call.next_follow_up_date.strftime("%b %d, %Y")} {follow_up_icon}</span>'
        else:
            follow_up_html = '<span class="text-muted">-</span>'
        
        # Feedback badge
        if call.feedback == 'positive':
            feedback_html = '<span class="badge bg-success"><i class="bi bi-hand-thumbs-up me-1"></i>Positive</span>'
        else:
            feedback_html = '<span class="badge bg-danger"><i class="bi bi-hand-thumbs-down me-1"></i>Negative</span>'
        
        data.append([
            call.call_date.strftime("%b %d, %Y %I:%M %p"),
            f'<small>{call.employee.get_full_name() or call.employee.username}</small>',
            services_html,
            f'<span class="text-truncate d-inline-block" style="max-width: 200px;" title="{call.remarks}">{call.remarks[:50]}...</span>' if len(call.remarks) > 50 else call.remarks,
            follow_up_html,
            feedback_html
        ])
    
    response = {
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': data
    }
    
    return JsonResponse(response)
