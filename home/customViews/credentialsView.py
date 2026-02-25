from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import IntegrityError
from home.models import Client, ClientPortalCredentials, Dropdown
from home.forms import ClientPortalCredentialsForm
from home.clients.client_access import get_accessible_clients


@login_required
def add_portal_credential(request, client_id):
    """Add new portal credential for a client"""
    # Check if user is a partner - deny access
    if hasattr(request.user, 'employee') and request.user.employee.role == 'PARTNER':
        messages.error(request, 'You do not have permission to add portal credentials.')
        return redirect('client_details', client_id=client_id)

    client = get_object_or_404(Client, id=client_id)

    # Check access
    if not request.user.is_superuser:
        accessible_clients = get_accessible_clients(request.user)
        if client not in accessible_clients:
            messages.error(request, "You don't have permission to access this client.")
            return redirect('dashboard')

    if request.method == 'POST':
        form = ClientPortalCredentialsForm(request.POST, client=client)
        if form.is_valid():
            try:
                credential = form.save(commit=False)
                credential.client = client
                credential.save()
                messages.success(request, f"Portal credential for {credential.dropdown.label} added successfully.")
                return redirect('client_details', client_id=client.id)
            except IntegrityError:
                # Handle duplicate portal credential error (backup in case form validation is bypassed)
                portal_type = form.cleaned_data.get('dropdown')
                messages.error(
                    request,
                    f"A credential for '{portal_type.label}' already exists for this client. "
                    f"Please update the existing credential or choose a different portal type."
                )
                return redirect('client_details', client_id=client.id)
        else:
            # If form has errors, redirect back with error messages
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, error)
            for field, errors in form.errors.items():
                for error in errors:
                    if field != '__all__':
                        messages.error(request, f"{field}: {error}")
            return redirect('client_details', client_id=client.id)

    # If GET request, redirect to client details
    return redirect('client_details', client_id=client.id)


@login_required
def view_portal_credential(request, credential_id):
    """View decrypted portal credential"""
    credential = get_object_or_404(ClientPortalCredentials, id=credential_id)

    # Check access
    if not request.user.is_superuser:
        accessible_clients = get_accessible_clients(request.user)
        if credential.client not in accessible_clients:
            messages.error(request, "You don't have permission to view this credential.")
            return redirect('dashboard')

    # Decrypt password
    decrypted_password = credential.get_decrypted_password()

    # Check if user is a partner (view-only access)
    is_partner = False
    if hasattr(request.user, 'employee'):
        is_partner = request.user.employee.role == 'PARTNER'

    return render(request, 'client/view_portal_credential.html', {
        'credential': credential,
        'decrypted_password': decrypted_password,
        'is_partner': is_partner,
    })


@login_required
def delete_portal_credential(request, credential_id):
    """Delete portal credential"""
    credential = get_object_or_404(ClientPortalCredentials, id=credential_id)
    client_id = credential.client.id

    # Check if user is a partner - deny access
    if hasattr(request.user, 'employee') and request.user.employee.role == 'PARTNER':
        messages.error(request, 'You do not have permission to delete portal credentials.')
        return redirect('client_details', client_id=client_id)

    # Check access
    if not request.user.is_superuser:
        accessible_clients = get_accessible_clients(request.user)
        if credential.client not in accessible_clients:
            messages.error(request, "You don't have permission to delete this credential.")
            return redirect('dashboard')

    if request.method == 'POST':
        portal_name = credential.dropdown.label
        credential.delete()
        messages.success(request, f"Portal credential for {portal_name} deleted successfully.")
        return redirect('client_details', client_id=client_id)

    return render(request, 'client/delete_portal_credential.html', {
        'credential': credential
    })
