from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from home.clients.client_access import get_accessible_clients
from home.models import Client


@login_required
def bulk_update_client_status(request):
    if request.method == "POST":
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

        accessible_clients = get_accessible_clients(request.user)

        updated_count = accessible_clients.filter(
            id__in=client_ids
        ).update(status=new_status)

        if updated_count == 0:
            messages.warning(request, "No clients were updated.")
        else:
            messages.success(request, f"{updated_count} client(s) updated successfully.")

    return redirect("clients")