from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from home.forms import DocumentUploadForm, DocumentRequestForm
from home.models import RequestedDocument, Client


@require_POST
@login_required
def upload_document_view(request, client_id):
    # Check if user is a partner - deny access
    if hasattr(request.user, 'employee') and request.user.employee.role == 'PARTNER':
        messages.error(request, 'You do not have permission to upload documents.')
        return redirect('client_details', client_id=client_id)

    client = get_object_or_404(Client, id=client_id)
    form = DocumentUploadForm(client_id, request.POST, request.FILES)

    if form.is_valid():
        upload = form.save(commit=False)
        upload.client = client
        upload.uploaded_by = request.user
        upload.status = 'Uploaded'
        upload.save()

        messages.success(request,
                         f"Document '{upload.requested_document.document_master.document_name}' uploaded successfully!")
    else:
        # Pass form errors back to the user via messages
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"Upload Error ({field}): {error}")

    return redirect('client_details', client_id=client.id)


@require_POST
@login_required
def create_document_request_view(request, client_id):
    # Check if user is a partner - deny access
    if hasattr(request.user, 'employee') and request.user.employee.role == 'PARTNER':
        messages.error(request, 'You do not have permission to create document requests.')
        return redirect('client_details', client_id=client_id)

    client = get_object_or_404(Client, id=client_id)
    form = DocumentRequestForm(request.POST)

    if form.is_valid():
        try:
            with transaction.atomic():
                # 1. Save Parent Request
                doc_request = form.save(commit=False)
                doc_request.client = client
                doc_request.created_by = request.user
                doc_request.save()

                # 2. Save Child Items (The Documents)
                selected_docs = form.cleaned_data['documents']

                # Check if documents were actually selected
                if not selected_docs:
                    raise ValueError("No documents were selected.")

                for doc_master in selected_docs:
                    RequestedDocument.objects.create(
                        document_request=doc_request,
                        document_master=doc_master
                    )

                messages.success(request, f"Request '{doc_request.title}' created successfully!")

        except Exception as e:
            # Catch DB or Logic errors
            messages.error(request, f"System Error: {str(e)}")
            print(f"❌ DB/Logic Error: {e}")  # Check your server console/terminal

    else:
        # 3. Catch Validation Errors (The likely cause)
        print(f"❌ Form Validation Failed: {form.errors}")  # Check your server console/terminal

        # Loop through errors and send them to the UI
        for field, errors in form.errors.items():
            error_msg = errors[0]  # Get the first error
            messages.error(request, f"Could not save - {field.title()}: {error_msg}")

    return redirect('client_details', client_id=client.id)
