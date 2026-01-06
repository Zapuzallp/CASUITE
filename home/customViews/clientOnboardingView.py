from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView

from home.clients.config import STRUCTURE_CONFIG
from home.forms import ClientForm, ClientBusinessProfileForm
# Import your models and forms
from home.models import Client, ClientBusinessProfile, OfficeDetails, Task


# -------------------------------------------------------------------
# Helper: Generate File Number (Only for new clients)
# -------------------------------------------------------------------
def generate_file_number(office_location):
    state_name = office_location.office_name
    office_code = state_name[:2].upper()
    existing_count = Client.objects.filter(office_location=office_location).count()
    next_number = existing_count + 1
    return f"{office_code}{str(next_number).zfill(6)}"


# -------------------------------------------------------------------
# View 1: Onboard New Client (Create)
# -------------------------------------------------------------------
@login_required
def onboard_client_view(request):
    if request.method == 'POST':
        client_form = ClientForm(request.POST)
        profile_form = ClientBusinessProfileForm(request.POST, request.FILES)

        if client_form.is_valid() and profile_form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Save Client
                    client = client_form.save(commit=False)
                    client.created_by = request.user

                    # Generate File Number only if office is selected and file number is empty
                    if client.office_location and not client.file_number:
                        client.file_number = generate_file_number(client.office_location)

                    client.save()

                    # 2. Save Profile
                    profile = profile_form.save(commit=False)
                    profile.client = client
                    profile.save()
                    profile_form.save_m2m()  # Important for ManyToMany

                    messages.success(request, f"Client {client.client_name} onboarded successfully!")
                    return redirect('clients')

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
        'structure_config': STRUCTURE_CONFIG,
        'page_title': 'Onboard New Client',
        'btn_text': 'Complete Onboarding'
    }

    return render(request, 'onboard_client.html', context)


# -------------------------------------------------------------------
# View 2: Edit Existing Client (Update)
# -------------------------------------------------------------------
@login_required
def edit_client_view(request, client_id):
    client = get_object_or_404(Client, id=client_id)

    # Try to get profile, if it doesn't exist (legacy data), create a dummy one in memory
    try:
        profile = client.business_profile
    except ClientBusinessProfile.DoesNotExist:
        profile = ClientBusinessProfile(client=client)

    if request.method == 'POST':
        client_form = ClientForm(request.POST, instance=client)
        profile_form = ClientBusinessProfileForm(request.POST, request.FILES, instance=profile)

        if client_form.is_valid() and profile_form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Update Client
                    client_obj = client_form.save()

                    # 2. Update Profile
                    profile_obj = profile_form.save(commit=False)
                    profile_obj.client = client_obj
                    profile_obj.save()
                    profile_form.save_m2m()  # Update ManyToMany selections

                    messages.success(request, f"Client {client.client_name} updated successfully!")
                    return redirect('clients')

            except Exception as e:
                messages.error(request, f"Error updating client: {e}")
        else:
            messages.error(request, "Please correct the errors below.")

    else:
        client_form = ClientForm(instance=client)
        profile_form = ClientBusinessProfileForm(instance=profile)

    context = {
        'client_form': client_form,
        'profile_form': profile_form,
        'structure_config': STRUCTURE_CONFIG,
        'page_title': f'Edit Client: {client.client_name}',
        'btn_text': 'Update Client Details'
    }

    # Reuse the exact same template
    return render(request, 'onboard_client.html', context)


# -------------------------------------------------------------------
# View 3: Client List View with Accordion Filters
# -------------------------------------------------------------------
class ClientView(LoginRequiredMixin, ListView):
    """View for displaying client list page with filters"""
    model = Client
    template_name = 'client/clients_all.html'
    context_object_name = 'clients'
    paginate_by = 50

    def get_queryset(self):
        user = self.request.user

        # 1. Base Queryset
        if user.is_superuser:
            qs = Client.objects.all().select_related('office_location', 'assigned_ca', 'business_profile')
        else:
            qs = Client.objects.filter(assigned_ca=user).select_related('office_location', 'assigned_ca',
                                                                        'business_profile')

        # 2. Extract GET parameters
        search_query = self.request.GET.get('q')
        filter_status = self.request.GET.get('status')
        filter_type = self.request.GET.get('client_type')
        filter_structure = self.request.GET.get('business_structure')
        filter_office = self.request.GET.get('office')
        filter_service = self.request.GET.get('service_type')  # Task Service Type

        # 3. Apply Filters
        if search_query:
            qs = qs.filter(
                Q(client_name__icontains=search_query) |
                Q(pan_no__icontains=search_query) |
                Q(file_number__icontains=search_query) |
                Q(primary_contact_name__icontains=search_query)
            )

        if filter_status:
            qs = qs.filter(status=filter_status)

        if filter_type:
            qs = qs.filter(client_type=filter_type)

        if filter_structure:
            qs = qs.filter(business_structure=filter_structure)

        if filter_office:
            qs = qs.filter(office_location_id=filter_office)

        # 4. Filter by Task Service Type (Reverse Relationship)
        if filter_service:
            # Filters clients who have *at least one* task of this service type
            qs = qs.filter(tasks__service_type=filter_service).distinct()

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Pass choices to template for the dropdowns
        context['client_type_choices'] = Client.CLIENT_TYPE_CHOICES
        context['business_structure_choices'] = Client.BUSINESS_STRUCTURE_CHOICES
        context['status_choices'] = Client.STATUS_CHOICES
        context['offices'] = OfficeDetails.objects.all()

        # Get Service Choices from Task model
        context['service_type_choices'] = Task.SERVICE_TYPE_CHOICES

        return context
