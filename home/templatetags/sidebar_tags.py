from django import template
from django.db.models import Prefetch

from home.models import (
    ClientUserEntitle,
    Client,
    DocumentRequest,
    RequestedDocument,
    ClientDocumentUpload,
    Task,
)

register = template.Library()


def _get_user_clients(user):
    try:
        mapping = ClientUserEntitle.objects.get(user=user)
        return mapping.clients.all()
    except ClientUserEntitle.DoesNotExist:
        return Client.objects.none()


@register.simple_tag(takes_context=True)
def get_sidebar_counts(context):
    request = context.get("request")
    if not request or not request.user.is_authenticated:
        return {"pending_documents": 0, "pending_tasks": 0}

    user_clients = _get_user_clients(request.user)
    if not user_clients.exists():
        return {"pending_documents": 0, "pending_tasks": 0}

    requests = DocumentRequest.objects.filter(
        client__in=user_clients
    ).prefetch_related(
        Prefetch(
            "required_documents",
            queryset=RequestedDocument.objects.prefetch_related(
                Prefetch(
                    "uploads",
                    queryset=ClientDocumentUpload.objects.order_by("-upload_date"),
                )
            ),
        )
    ).select_related("client")

    total_pending_documents = 0

    for doc_request in requests:
        for requested_doc in doc_request.required_documents.all():
            client_uploads = [u for u in requested_doc.uploads.all() if u.client == doc_request.client]
            upload = client_uploads[0] if client_uploads else None
            if not upload or upload.status != "Uploaded":
                total_pending_documents += 1

    pending_tasks = Task.objects.filter(
        client__in=user_clients,
        status="Pending",
    ).count()

    return {
        "pending_documents": total_pending_documents,
        "pending_tasks": pending_tasks,
    }
