from django.views.generic import ListView, CreateView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views import View
from django.shortcuts import redirect, render
from django.db import transaction
from .models import Client
from .forms import ClientForm, CompanyDetailsForm, LLPDetailsForm, OPCDetailsForm, Section8CompanyDetailsForm, HUFDetailsForm
from datetime import datetime

class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        # 👇 Redirect non-staff users to client dashboard
        if not user.is_staff:
            return redirect('client_dashboard')
        return render(request, "dashboard.html")

class ClientView(LoginRequiredMixin, ListView):
    model = Client
    template_name = 'clients.html'
    context_object_name = 'clients'
    paginate_by = 10

class ClientListAPI(LoginRequiredMixin, View):
    def get(self, request):
        # Get query parameters
        page = request.GET.get('page', 1)
        per_page = request.GET.get('per_page', 10)

        try:
            # Get all clients
            clients = Client.objects.all().order_by('-created_at')

            # Paginate results
            paginator = Paginator(clients, per_page)
            try:
                clients_page = paginator.page(page)
            except:
                clients_page = paginator.page(1)

            # Prepare client data
            clients_data = []
            for client in clients_page:
                clients_data.append({
                    'id': client.id,
                    'client_name': client.client_name,
                    'primary_contact_name': client.primary_contact_name,
                    'pan_no': client.pan_no,
                    'email': client.email,
                    'phone_number': client.phone_number,
                    'address_line1': client.address_line1,
                    'aadhar': client.aadhar,
                    'city': client.city,
                    'state': client.state,
                    'postal_code': client.postal_code,
                    'country': client.country,
                    'date_of_engagement': client.date_of_engagement.isoformat() if client.date_of_engagement else None,
                    'assigned_ca': client.assigned_ca_id,
                    'assigned_ca_name': client.assigned_ca.get_full_name() if client.assigned_ca else '',
                    'client_type': client.client_type,
                    'business_structure': client.business_structure,
                    'status': client.status,
                    'remarks': client.remarks,
                    'din_no': client.din_no,
                    'created_by': client.created_by_id,
                    'created_by_name': client.created_by.get_full_name() if client.created_by else '',
                    'created_at': client.created_at.isoformat() if client.created_at else None,
                    'updated_at': client.updated_at.isoformat() if client.updated_at else None
                })

            # Return JSON response
            return JsonResponse({
                'clients': clients_data,
                'pagination': {
                    'current_page': clients_page.number,
                    'total_pages': paginator.num_pages,
                    'total_records': paginator.count,
                    'has_next': clients_page.has_next(),
                    'has_previous': clients_page.has_previous(),
                }
            }, status=200)

        except Exception as e:
            return JsonResponse({
                'error': 'Failed to fetch clients',
                'message': str(e)
            }, status=500)


class AddClientView(LoginRequiredMixin, TemplateView):
    template_name = 'add_client.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Always start with a fresh form - don't pre-fill from session
        context['client_form'] = ClientForm()
        return context


class SaveClientBasicView(LoginRequiredMixin, View):
    def post(self, request):
        print("SaveClientBasicView called")
        try:
            client_form = ClientForm(request.POST)
            if not client_form.is_valid():
                print("Form errors:", client_form.errors)
                return JsonResponse({'success': False, 'errors': client_form.errors})

            print("Form is valid")
            client_type = client_form.cleaned_data.get('client_type')
            business_structure = client_form.cleaned_data.get('business_structure')
            print(f"Client type: {client_type}, Business structure: {business_structure}")

            # Handle 'Individual' clients - save immediately
            if client_type == 'Individual':
                return self._save_and_redirect(client_form, request)

            # Define form templates mapping for Entity types
            structure_map = {
                'Private Ltd': ('company_details_form.html', CompanyDetailsForm),
                'Public Ltd': ('company_details_form.html', CompanyDetailsForm),
                'LLP': ('llp_details_form.html', LLPDetailsForm),
                'OPC': ('opc_details_form.html', OPCDetailsForm),
                'Section 8': ('section8_details_form.html', Section8CompanyDetailsForm),
                'HUF': ('huf_details_form.html', HUFDetailsForm),
            }

            # If business structure is not in the map → save directly
            if business_structure not in structure_map:
                return self._save_and_redirect(client_form, request)

            # Store form data in session for multi-step process
            # Convert date objects to strings for session storage
            session_data = request.POST.dict().copy()
            for key, value in session_data.items():
                if hasattr(value, 'isoformat'):  # If it's a date object
                    session_data[key] = value.isoformat()

            request.session['client_basic_data'] = session_data
            request.session.modified = True

            # Render the extra form for Entity
            template_name, form_class = structure_map[business_structure]
            form_html = self.render_form_to_string(request, template_name, {
                'form': form_class(),
                'business_structure': business_structure
            })

            return JsonResponse({
                'success': True,
                'form_html': form_html,
                'business_structure': business_structure
            })

        except Exception as e:
            print(f"Unexpected error in SaveClientBasicView: {e}")
            return JsonResponse({'success': False, 'error': f"Unexpected error: {str(e)}"})

    def _save_and_redirect(self, client_form, request):
        """Save individual client and redirect"""
        try:
            with transaction.atomic():
                client = client_form.save(commit=False)
                client.created_by = request.user
                client.save()

                # Clear any existing session data
                self._clear_session_data(request)

                messages.success(request, 'Client added successfully!')
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse_lazy('clients')
                })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    def _clear_session_data(self, request):
        """Clear session data"""
        if 'client_basic_data' in request.session:
            del request.session['client_basic_data']
        if 'client_form_data' in request.session:
            del request.session['client_form_data']

    def render_form_to_string(self, request, template_name, context):
        from django.template.loader import render_to_string
        return render_to_string(template_name, context, request=request)


class SaveClientCompleteView(LoginRequiredMixin, View):
    def post(self, request):
        business_structure = request.POST.get('business_structure')
        client_basic_data = request.session.get('client_basic_data')

        if not client_basic_data:
            return JsonResponse({'success': False, 'error': 'Session expired. Please start over.'})

        try:
            with transaction.atomic():
                # Convert string dates back to date objects for form validation
                processed_basic_data = client_basic_data.copy()
                for key, value in processed_basic_data.items():
                    if isinstance(value, str) and ('date' in key.lower() or 'engagement' in key.lower()):
                        try:
                            processed_basic_data[key] = datetime.strptime(value, '%Y-%m-%d').date()
                        except (ValueError, TypeError):
                            # If date parsing fails, keep the original value
                            pass

                # Save basic client data
                client_form = ClientForm(processed_basic_data)
                if client_form.is_valid():
                    client = client_form.save(commit=False)
                    client.created_by = request.user
                    client.save()

                    # Save business structure specific details
                    success = self._save_business_structure_details(request, business_structure, client)
                    if not success:
                        return JsonResponse({'success': False, 'errors': 'Failed to save business structure details'})

                    # Clear session data after successful save
                    self._clear_session_data(request)

                    messages.success(request, 'Client added successfully!')
                    return JsonResponse({'success': True, 'redirect_url': reverse_lazy('clients')})

                else:
                    return JsonResponse({'success': False, 'errors': client_form.errors})

        except Exception as e:
            print(f"Error in SaveClientCompleteView: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    def _save_business_structure_details(self, request, business_structure, client):
        """Save business structure specific details"""
        try:
            if business_structure in ['Private Ltd', 'Public Ltd']:
                form = CompanyDetailsForm(request.POST, request.FILES)
                if form.is_valid():
                    company_details = form.save(commit=False)
                    company_details.client = client
                    company_details.save()
                    form.save_m2m()
                    return True
                return False

            elif business_structure == 'LLP':
                form = LLPDetailsForm(request.POST, request.FILES)
                if form.is_valid():
                    llp_details = form.save(commit=False)
                    llp_details.client = client
                    llp_details.save()
                    return True
                return False

            elif business_structure == 'OPC':
                form = OPCDetailsForm(request.POST, request.FILES)
                if form.is_valid():
                    opc_details = form.save(commit=False)
                    opc_details.client = client
                    opc_details.save()
                    return True
                return False

            elif business_structure == 'Section 8':
                form = Section8CompanyDetailsForm(request.POST, request.FILES)
                if form.is_valid():
                    section8_details = form.save(commit=False)
                    section8_details.client = client
                    section8_details.save()
                    return True
                return False

            elif business_structure == 'HUF':
                form = HUFDetailsForm(request.POST, request.FILES)
                if form.is_valid():
                    huf_details = form.save(commit=False)
                    huf_details.client = client
                    huf_details.save()
                    return True
                return False

            return True  # For business structures without additional details

        except Exception as e:
            print(f"Error saving business structure details: {e}")
            return False

    def _clear_session_data(self, request):
        """Clear session data"""
        if 'client_basic_data' in request.session:
            del request.session['client_basic_data']


class ClearClientSessionView(LoginRequiredMixin, View):
    """View to clear session data when user wants to start over completely"""

    def post(self, request):
        self._clear_all_session_data(request)
        return JsonResponse({'success': True})

    def _clear_all_session_data(self, request):
        """Clear all client-related session data"""
        session_keys = ['client_basic_data', 'client_form_data', 'current_client_id']
        for key in session_keys:
            if key in request.session:
                del request.session[key]