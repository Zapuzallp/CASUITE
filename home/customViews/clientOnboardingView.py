from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect

from home.clients.config import STRUCTURE_CONFIG
from home.forms import ClientForm, ClientBusinessProfileForm


# -------------------------------------------------------------------
# Generate the unique file number with respect to the office location
# -------------------------------------------------------------------

def generate_file_number(office_location):
    """
    Generates a unique file number based on office location.
    like KO000001, OD000002
    """

    from home.models import Client

    #Get office code (first 2 letters of state)
    state_name = office_location.get_state_display()
    office_code = state_name[:2].upper()

    #Count existing clients for this office
    existing_count = Client.objects.filter(
        office_location=office_location
    ).count()

    #Next sequence number
    next_number = existing_count + 1

    #Zero-pad to 6 digits
    return f"{office_code}{str(next_number).zfill(6)}"


@login_required
def onboard_client_view(request):
    # 1. Handle POST (Form Submission)
    if request.method == 'POST':
        client_form = ClientForm(request.POST)
        profile_form = ClientBusinessProfileForm(request.POST, request.FILES)

        if client_form.is_valid() and profile_form.is_valid():
            try:
                with transaction.atomic():
                    # Save Client
                    client = client_form.save(commit=False)
                    client.created_by = request.user
                    # ---- FILE NUMBER GENERATION BEFORE SAVING THE CLIENT INFORMATION----
                    if not client.file_number:
                        client.file_number = generate_file_number(client.office_location)
                    client.save()

                    # Save Profile
                    profile = profile_form.save(commit=False)
                    profile.client = client
                    profile.save()
                    profile_form.save_m2m()

                    messages.success(request, f"Client {client.client_name} onboarded successfully!")
                    return redirect('clients')  # Ensure this URL name exists in urls.py

            except Exception as e:
                messages.error(request, f"Error saving client: {e}")
        else:
            messages.error(request, "Please correct the errors below.")

    else:
        client_form = ClientForm()
        profile_form = ClientBusinessProfileForm()

    context = {
        'client_form': client_form,
        'profile_form': profile_form,
        'structure_config': STRUCTURE_CONFIG
    }

    return render(request, 'onboard_client.html', context)
