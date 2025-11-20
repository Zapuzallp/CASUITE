from django.views.generic import ListView, CreateView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views import View
from django.shortcuts import redirect, render
from django.db import transaction
from .models import Client, RequestedDocument, DocumentMaster, ClientDocumentUpload, DocumentRequest
from .forms import ClientForm, CompanyDetailsForm, LLPDetailsForm, OPCDetailsForm, Section8CompanyDetailsForm, \
    HUFDetailsForm
from datetime import datetime


class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        # 👇 Redirect non-staff users to client dashboard
        if not user.is_staff:
            return redirect('client_dashboard')
        return render(request, "dashboard.html")


class ClientView(LoginRequiredMixin, ListView):
    """View for displaying client list page"""
    model = Client
    template_name = 'client/clients_all.html'
    context_object_name = 'clients'
    paginate_by = 10


class ClientListAPI(LoginRequiredMixin, View):
    """API endpoint for client data with pagination"""

    def get(self, request):
        try:
            clients_data = self._get_paginated_clients(request)
            return JsonResponse({
                'clients': clients_data['clients'],
                'pagination': clients_data['pagination']
            }, status=200)
        except Exception as e:
            return self._handle_error(e)

    def _get_paginated_clients(self, request):
        """Get paginated client data"""
        page = request.GET.get('page', 1)
        per_page = request.GET.get('per_page', 10)

        clients = Client.objects.all().order_by('-created_at')
        paginator = Paginator(clients, per_page)

        try:
            clients_page = paginator.page(page)
        except:
            clients_page = paginator.page(1)

        return {
            'clients': self._serialize_clients(clients_page),
            'pagination': self._get_pagination_data(clients_page, paginator)
        }

    def _serialize_clients(self, clients_page):
        """Serialize client data for JSON response"""
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
        return clients_data

    def _get_pagination_data(self, clients_page, paginator):
        """Get pagination metadata"""
        return {
            'current_page': clients_page.number,
            'total_pages': paginator.num_pages,
            'total_records': paginator.count,
            'has_next': clients_page.has_next(),
            'has_previous': clients_page.has_previous(),
        }

    def _handle_error(self, error):
        """Handle API errors"""
        return JsonResponse({
            'error': 'Failed to fetch clients',
            'message': str(error)
        }, status=500)


class AddClientView(LoginRequiredMixin, TemplateView):
    """View for client onboarding form"""
    template_name = 'client_onboarding/add_client.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self._clear_messages()
        context['client_form'] = ClientForm()
        return context

    def _clear_messages(self):
        """Clear any existing messages"""
        storage = messages.get_messages(self.request)
        for message in storage:
            pass  # This clears the messages


class BaseClientSaveView(LoginRequiredMixin, View):
    """Base class for client save operations with common functionality"""

    BUSINESS_STRUCTURE_MAP = {
        'Private Ltd': ('client_onboarding/company_details_form.html', CompanyDetailsForm),
        'Public Ltd': ('client_onboarding/company_details_form.html', CompanyDetailsForm),
        'LLP': ('client_onboarding/llp_details_form.html', LLPDetailsForm),
        'OPC': ('client_onboarding/opc_details_form.html', OPCDetailsForm),
        'Section 8': ('client_onboarding/section8_details_form.html', Section8CompanyDetailsForm),
        'HUF': ('client_onboarding/huf_details_form.html', HUFDetailsForm),
    }

    def _prepare_post_data(self, post_data):
        """Prepare POST data for form processing"""
        processed_data = post_data.copy()

        # If client type is Individual, remove business_structure requirement
        if processed_data.get('client_type') == 'Individual':
            processed_data['business_structure'] = ''

        return processed_data

    def _store_session_data(self, request, data):
        """Store form data in session"""
        request.session['client_basic_data'] = data
        request.session.modified = True

    def _clear_session_data(self, request):
        """Clear client session data"""
        if 'client_basic_data' in request.session:
            del request.session['client_basic_data']

    def _render_form_to_string(self, request, template_name, context):
        """Render form template to string"""
        from django.template.loader import render_to_string
        return render_to_string(template_name, context, request=request)

    def _handle_individual_client(self):
        """Handle Individual client type response"""
        return JsonResponse({
            'success': True,
            'redirect_to_complete': True,
            'client_type': 'Individual'
        })

    def _handle_entity_client(self, business_structure):
        """Handle Entity client type response"""
        if business_structure in self.BUSINESS_STRUCTURE_MAP:
            return self._get_business_structure_form(business_structure)
        else:
            return self._handle_entity_without_structure(business_structure)

    def _get_business_structure_form(self, business_structure):
        """Get business structure specific form"""
        template_name, form_class = self.BUSINESS_STRUCTURE_MAP[business_structure]
        form_instance = form_class()

        form_html = self._render_form_to_string(self.request, template_name, {
            'form': form_instance,
            'business_structure': business_structure
        })

        return JsonResponse({
            'success': True,
            'form_html': form_html,
            'business_structure': business_structure
        })

    def _handle_entity_without_structure(self, business_structure):
        """Handle Entity client without specific business structure"""
        return JsonResponse({
            'success': True,
            'redirect_to_complete': True,
            'client_type': 'Entity',
            'business_structure': business_structure
        })


class SaveClientBasicView(BaseClientSaveView):
    """Handle basic client data saving and determine next steps"""

    def post(self, request):
        print("SaveClientBasicView called")
        try:
            post_data = self._prepare_post_data(request.POST)
            client_form = ClientForm(post_data)

            if not client_form.is_valid():
                print("Form errors:", client_form.errors)
                return JsonResponse({'success': False, 'errors': client_form.errors})

            client_type = client_form.cleaned_data.get('client_type')
            business_structure = client_form.cleaned_data.get('business_structure')
            print(f"Client type: {client_type}, Business structure: {business_structure}")

            # Store form data in session for multi-step process
            self._store_session_data(request, request.POST.dict())

            # Route based on client type
            if client_type == 'Individual':
                return self._handle_individual_client()
            else:
                return self._handle_entity_client(business_structure)

        except Exception as e:
            print(f"Unexpected error in SaveClientBasicView: {e}")
            return JsonResponse({'success': False, 'error': f"Unexpected error: {str(e)}"})


class BaseClientCompleteView(BaseClientSaveView):
    """Base class for complete client saving operations"""

    def _process_basic_data(self, client_basic_data):
        """Process basic client data including date conversion"""
        processed_data = client_basic_data.copy()
        for key, value in processed_data.items():
            if isinstance(value, str) and ('date' in key.lower() or 'engagement' in key.lower()):
                try:
                    processed_data[key] = datetime.strptime(value, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    # If date parsing fails, keep the original value
                    pass
        return processed_data

    def _save_client(self, processed_data, request):
        """Save client with basic data"""
        client_form = ClientForm(processed_data)
        if client_form.is_valid():
            client = client_form.save(commit=False)
            client.created_by = request.user
            client.save()
            return client, None
        return None, client_form.errors

    def _save_business_structure_details(self, request, business_structure, client):
        """Save business structure specific details WITHOUT creating document records"""
        try:
            if business_structure in ['Private Ltd', 'Public Ltd']:
                return self._save_company_details(request, client)
            elif business_structure == 'LLP':
                return self._save_llp_details(request, client)
            elif business_structure == 'OPC':
                return self._save_opc_details(request, client)
            elif business_structure == 'Section 8':
                return self._save_section8_details(request, client)
            elif business_structure == 'HUF':
                return self._save_huf_details(request, client)
            return True  # For business structures without additional details

        except Exception as e:
            print(f"Error saving business structure details: {e}")
            return str(e)

    def _save_company_details(self, request, client):
        """Save company details (Private Ltd, Public Ltd)"""
        form = CompanyDetailsForm(request.POST, request.FILES)
        if form.is_valid():
            company_details = form.save(commit=False)
            company_details.client = client
            company_details.save()
            form.save_m2m()
            print(f"Company details saved for {client.client_name}. Files uploaded locally.")
            return True
        return form.errors

    def _save_llp_details(self, request, client):
        """Save LLP details"""
        form = LLPDetailsForm(request.POST, request.FILES)
        if form.is_valid():
            llp_details = form.save(commit=False)
            llp_details.client = client
            llp_details.save()
            form.save_m2m()
            print(f"LLP details saved for {client.client_name}. Files uploaded locally.")
            return True
        return form.errors

    def _save_opc_details(self, request, client):
        """Save OPC details"""
        form = OPCDetailsForm(request.POST, request.FILES)
        if form.is_valid():
            opc_details = form.save(commit=False)
            opc_details.client = client
            opc_details.save()
            return True
        return form.errors

    def _save_section8_details(self, request, client):
        """Save Section 8 company details"""
        form = Section8CompanyDetailsForm(request.POST, request.FILES)
        if form.is_valid():
            section8_details = form.save(commit=False)
            section8_details.client = client
            section8_details.save()
            return True
        return form.errors

    def _save_huf_details(self, request, client):
        """Save HUF details"""
        form = HUFDetailsForm(request.POST, request.FILES)
        if form.is_valid():
            huf_details = form.save(commit=False)
            huf_details.client = client
            huf_details.save()
            print(f"HUF details saved for {client.client_name}. Files uploaded locally.")
            return True
        return form.errors

    def _success_response(self, client):
        """Return success response with client data"""
        return JsonResponse({
            'success': True,
            'client_id': client.id,
            'client_name': client.client_name
        })


class SaveClientCompleteView(BaseClientCompleteView):
    """Handle complete client saving with business structure details"""

    def post(self, request):
        business_structure = request.POST.get('business_structure')
        client_basic_data = request.session.get('client_basic_data')

        if not client_basic_data:
            return JsonResponse({'success': False, 'error': 'Session expired. Please start over.'})

        try:
            with transaction.atomic():
                processed_basic_data = self._process_basic_data(client_basic_data)
                client, form_errors = self._save_client(processed_basic_data, request)

                if client:
                    # Save business structure specific details
                    business_structure_result = self._save_business_structure_details(
                        request, business_structure, client
                    )

                    if business_structure_result is not True:
                        transaction.set_rollback(True)
                        return JsonResponse({'success': False, 'errors': business_structure_result})

                    # Clear session data after successful save
                    self._clear_session_data(request)
                    return self._success_response(client)
                else:
                    return JsonResponse({'success': False, 'errors': form_errors})

        except Exception as e:
            print(f"Error in SaveClientCompleteView: {e}")
            return JsonResponse({'success': False, 'error': str(e)})


class SaveIndividualClientView(BaseClientCompleteView):
    """Handle saving individual clients directly (without business structure)"""

    def post(self, request):
        client_basic_data = request.session.get('client_basic_data')

        if not client_basic_data:
            return JsonResponse({'success': False, 'error': 'Session expired. Please start over.'})

        try:
            with transaction.atomic():
                processed_basic_data = self._process_basic_data(client_basic_data)
                client, form_errors = self._save_client(processed_basic_data, request)

                if client:
                    # Clear session data after successful save
                    self._clear_session_data(request)
                    return self._success_response(client)
                else:
                    return JsonResponse({'success': False, 'errors': form_errors})

        except Exception as e:
            print(f"Error in SaveIndividualClientView: {e}")
            return JsonResponse({'success': False, 'error': str(e)})


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