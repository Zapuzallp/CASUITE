from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from home.forms import DocumentUploadForm, DocumentRequestForm, RequestedDocument
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

                    # Handle ManyToMany or ForeignKeys if needed (simplistic approach here)
                    # For FK, it usually prints the __str__ representation automatically

                    data.append({
                        'label': field.verbose_name.title(),
                        'value': display_val,
                        'name': field.name  # internal name if needed for css classes
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
    }

    return render(request, 'client/client-details.html', context)