from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from home.forms import ClientDocumentUploadForm
from home.models import DocumentRequest, RequestedDocument, ClientDocumentUpload
from django.db.models import Prefetch


@login_required
def client_dashboard(request):
    if request.user.is_staff:
        return redirect('admin:index')

    today = timezone.localdate()
    # Fetch requests for this client
    requests = DocumentRequest.objects.filter(client=request.user).prefetch_related(
        'required_documents__document_master', 'required_documents__uploads')

    # Build context with per-required-document upload status
    request_list = []
    for req in requests:
        items = []
        for rd in req.required_documents.all():
            # Find latest upload by this client for this requested document
            upload = rd.uploads.filter(client=request.user).order_by('-upload_date').first()
            status = 'Pending'
            if upload:
                status = upload.status
            else:
                if req.due_date < today:
                    status = 'Overdue'
            can_upload = (req.due_date >= today)
            items.append({
                'requested_document': rd,
                'document_master': rd.document_master,
                'upload': upload,
                'status': status,
                'can_upload': can_upload,
            })
        request_list.append({
            'request': req,
            'items': items,
        })

    return render(request, 'client/dashboard.html', {'request_list': request_list})


@login_required
def upload_document(request, requested_document_id):
    rd = get_object_or_404(RequestedDocument, id=requested_document_id)
    doc_request = rd.document_request
    if request.user.is_staff:
        return HttpResponseForbidden('Staff users cannot upload here')
    if doc_request.client != request.user:
        return HttpResponseForbidden('Not allowed')

    today = timezone.localdate()
    if doc_request.due_date < today:
        return HttpResponseForbidden('Due date passed — uploads disabled')

    if request.method == 'POST':
        form = ClientDocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload = form.save(commit=False)
            upload.client = request.user
            upload.requested_document = rd
            upload.save()
            return redirect('client_dashboard')
    else:
        form = ClientDocumentUploadForm()

    return render(request, 'client/upload.html', {'form': form, 'requested_document': rd})


@login_required
def document_requests(request):
    user = request.user

    # Get all document requests with optimized related data fetching
    requests = DocumentRequest.objects.filter(
        client=user
    ).prefetch_related(
        Prefetch(
            'required_documents',  # Changed from 'requesteddocument_set' to 'required_documents' (related_name)
            queryset=RequestedDocument.objects.select_related(
                'document_master'
            ).prefetch_related(
                Prefetch(
                    'uploads',  # Use the related_name 'uploads' from ClientDocumentUpload
                    queryset=ClientDocumentUpload.objects.filter(
                        client=user
                    ).order_by('-upload_date')
                )
            )
        )
    ).order_by('-due_date')

    # Build the request list with items
    request_list = []
    total_pending = 0

    for doc_request in requests:
        items = []
        uploaded_count = 0

        for requested_doc in doc_request.required_documents.all():
            # Get the latest upload for this document by the current user
            user_uploads = [u for u in requested_doc.uploads.all() if u.client == user]
            upload = user_uploads[0] if user_uploads else None

            item = {
                'requested_document': requested_doc,
                'document_master': requested_doc.document_master,
                'upload': upload,
                'status': upload.status if upload else 'Pending',
                'can_upload': True,  # You can add logic here if needed
            }
            items.append(item)

            if upload and upload.status == 'Uploaded':
                uploaded_count += 1
            else:
                total_pending += 1

        # Determine overall status
        total_items = len(items)
        if total_items == 0:
            status = 'pending'
        elif uploaded_count == total_items:
            status = 'completed'
        elif uploaded_count > 0:
            status = 'partial'
        else:
            status = 'pending'

        request_list.append({
            'request': doc_request,
            'items': items,
            'status': status,
            'uploaded_count': uploaded_count,
            'total_count': total_items,
        })

    context = {
        'request_list': request_list,
        'pending_documents': total_pending,
    }
    return render(request, 'client/document-request.html', context)
