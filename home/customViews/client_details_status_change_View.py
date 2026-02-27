from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from home.models import Client


@login_required
def update_single_client_status(request, client_id):
    client = get_object_or_404(Client, id=client_id)

    # Permission check
    if not (request.user.is_superuser or request.user == client.assigned_ca):
        messages.error(request, "You do not have permission to update this client.")
        return redirect('client_details', client_id=client.id)

    if request.method == "POST":
        new_status = request.POST.get("new_status")

        if new_status:
            client.status = new_status
            client.save()
            messages.success(request, "Client status updated successfully.")

    return redirect('client_details', client_id=client.id)