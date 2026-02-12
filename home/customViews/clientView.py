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
    }

    return render(request, 'client/client-details.html', context)


# ---------------------------------------------------------
# NEW: GST Management Views
# ---------------------------------------------------------

@login_required
def add_gst_details_view(request, client_id):
    client = get_object_or_404(Client, id=client_id)

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