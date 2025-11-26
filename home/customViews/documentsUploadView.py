from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from home.forms import ClientDocumentUploadForm
from home.models import DocumentRequest, RequestedDocument, ClientDocumentUpload, ClientUserEntitle, Client
from django.db.models import Prefetch


def get_user_clients(user):
    """Helper function to get clients associated with a user"""
    try:
        client_user_entitle = ClientUserEntitle.objects.get(user=user)
        return client_user_entitle.clients.all()
    except ClientUserEntitle.DoesNotExist:
        return Client.objects.none()


@login_required
def client_dashboard(request):
    if request.user.is_staff:
        return redirect('admin:index')

    today = timezone.localdate()

    # Get clients associated with this user
    user_clients = get_user_clients(request.user)

    if not user_clients.exists():
        return render(request, 'client/dashboard.html', {
            'clients_with_requests': [],
            'user_clients': user_clients,
            'no_clients_message': 'No clients assigned to you. Please contact your administrator.'
        })

    # Fetch requests for clients under this user
    requests = DocumentRequest.objects.filter(client__in=user_clients).prefetch_related(
        'required_documents__document_master', 'required_documents__uploads'
    ).select_related('client').order_by('client__client_name', '-due_date')

    # Group requests by client
    clients_with_requests = {}

    for req in requests:
        client = req.client

        if client.id not in clients_with_requests:
            clients_with_requests[client.id] = {
                'client': client,
                'requests': [],
                'urgent_count': 0,
                'overdue_count': 0,
                'pending_count': 0,
                'completed_count': 0
            }

        items = []
        urgent_items = 0
        overdue_items = 0
        pending_items = 0
        completed_items = 0

        for rd in req.required_documents.all():
            # Find latest upload by this client for this requested document
            upload = rd.uploads.filter(client=req.client).order_by('-upload_date').first()
            status = 'Pending'
            if upload:
                status = upload.status
                if status == 'Uploaded':
                    completed_items += 1
            else:
                if req.due_date < today:
                    status = 'Overdue'
                    overdue_items += 1
                else:
                    pending_items += 1
                    # Check if due within 3 days
                    days_until_due = (req.due_date - today).days
                    if days_until_due <= 3:
                        urgent_items += 1

            can_upload = (req.due_date >= today)
            items.append({
                'requested_document': rd,
                'document_master': rd.document_master,
                'upload': upload,
                'status': status,
                'can_upload': can_upload,
                'days_until_due': (req.due_date - today).days if req.due_date >= today else None,
                'is_urgent': (req.due_date - today).days <= 3 if req.due_date >= today else False
            })

        request_data = {
            'request': req,
            'items': items,
            'urgent_items': urgent_items,
            'overdue_items': overdue_items,
            'pending_items': pending_items,
            'completed_items': completed_items,
            'total_items': len(items)
        }

        clients_with_requests[client.id]['requests'].append(request_data)
        clients_with_requests[client.id]['urgent_count'] += urgent_items
        clients_with_requests[client.id]['overdue_count'] += overdue_items
        clients_with_requests[client.id]['pending_count'] += pending_items
        clients_with_requests[client.id]['completed_count'] += completed_items

    # Convert to list and sort by client name
    clients_list = list(clients_with_requests.values())
    clients_list.sort(key=lambda x: x['client'].client_name)

    return render(request, 'client/dashboard.html', {
        'clients_with_requests': clients_list,
        'user_clients': user_clients,
        'today': today
    })


@login_required
def upload_document(request, requested_document_id):
    rd = get_object_or_404(RequestedDocument, id=requested_document_id)
    doc_request = rd.document_request

    # Check if user has access to this client
    user_clients = get_user_clients(request.user)
    if not user_clients.exists():
        return HttpResponseForbidden('No clients assigned to you. Please contact your administrator.')

    if doc_request.client not in user_clients:
        return HttpResponseForbidden('Not allowed - client not under your management')

    today = timezone.localdate()
    if doc_request.due_date < today:
        return HttpResponseForbidden('Due date passed — uploads disabled')

    if request.method == 'POST':
        form = ClientDocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload = form.save(commit=False)
            upload.client = doc_request.client  # Use the client from document request
            upload.uploaded_by = request.user  # Track who uploaded it
            upload.requested_document = rd
            upload.save()
            return redirect('client_dashboard')
    else:
        form = ClientDocumentUploadForm()

    return render(request, 'client/upload.html', {
        'form': form,
        'requested_document': rd,
        'client': doc_request.client
    })


@login_required
def document_requests(request):
    user = request.user

    # Get clients associated with this user
    user_clients = get_user_clients(user)

    if not user_clients.exists():
        return render(request, 'client/document-request.html', {
            'clients_with_requests': [],
            'pending_documents': 0,
            'user_clients': user_clients,
            'no_clients_message': 'No clients assigned to you. Please contact your administrator.'
        })

    # Get all document requests for clients under this user with optimized related data fetching
    requests = DocumentRequest.objects.filter(
        client__in=user_clients
    ).prefetch_related(
        Prefetch(
            'required_documents',
            queryset=RequestedDocument.objects.select_related(
                'document_master'
            ).prefetch_related(
                Prefetch(
                    'uploads',
                    queryset=ClientDocumentUpload.objects.order_by('-upload_date')
                )
            )
        )
    ).select_related('client').order_by('client__client_name', '-due_date')

    # Group requests by client
    clients_with_requests = {}
    total_pending = 0

    for doc_request in requests:
        client = doc_request.client

        if client.id not in clients_with_requests:
            clients_with_requests[client.id] = {
                'client': client,
                'requests': [],
                'total_pending': 0,
                'total_completed': 0,
                'total_documents': 0
            }

        items = []
        uploaded_count = 0
        request_pending = 0

        for requested_doc in doc_request.required_documents.all():
            # Get the latest upload for this document by the client
            client_uploads = [u for u in requested_doc.uploads.all() if u.client == doc_request.client]
            upload = client_uploads[0] if client_uploads else None

            item = {
                'requested_document': requested_doc,
                'document_master': requested_doc.document_master,
                'upload': upload,
                'status': upload.status if upload else 'Pending',
                'can_upload': True,
            }
            items.append(item)

            if upload and upload.status == 'Uploaded':
                uploaded_count += 1
            else:
                request_pending += 1
                total_pending += 1

        # Determine overall status for this request
        total_items = len(items)
        if total_items == 0:
            status = 'pending'
        elif uploaded_count == total_items:
            status = 'completed'
        elif uploaded_count > 0:
            status = 'partial'
        else:
            status = 'pending'

        request_data = {
            'request': doc_request,
            'items': items,
            'status': status,
            'uploaded_count': uploaded_count,
            'total_count': total_items,
            'pending_count': request_pending
        }

        clients_with_requests[client.id]['requests'].append(request_data)
        clients_with_requests[client.id]['total_pending'] += request_pending
        clients_with_requests[client.id]['total_completed'] += uploaded_count
        clients_with_requests[client.id]['total_documents'] += total_items

    # Convert to list and add client-level statistics
    clients_list = []
    for client_data in clients_with_requests.values():
        # Calculate client-level completion percentage
        total_docs = client_data['total_documents']
        completed_docs = client_data['total_completed']

        if total_docs > 0:
            completion_percentage = round((completed_docs / total_docs) * 100)
        else:
            completion_percentage = 0

        client_data['completion_percentage'] = completion_percentage

        # Determine client overall status
        if completion_percentage == 100:
            client_data['overall_status'] = 'completed'
        elif completion_percentage > 0:
            client_data['overall_status'] = 'partial'
        else:
            client_data['overall_status'] = 'pending'

        clients_list.append(client_data)

    # Sort clients by name
    clients_list.sort(key=lambda x: x['client'].client_name)

    context = {
        'clients_with_requests': clients_list,
        'pending_documents': total_pending,
        'user_clients': user_clients,
        'total_clients_with_requests': len(clients_list)
    }
    return render(request, 'client/document-request.html', context)
