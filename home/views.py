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
        # Clear any existing messages when loading the form
        from django.contrib.messages import get_messages
        storage = get_messages(self.request)
        for message in storage:
            pass  # This clears the messages
        context['client_form'] = ClientForm()
        storage = messages.get_messages(self.request)
        for message in storage:
            pass

        return context


class SaveClientBasicView(LoginRequiredMixin, View):
    def post(self, request):
        print("SaveClientBasicView called")
        try:
            # Create a mutable copy of the POST data
            post_data = request.POST.copy()

            # DEBUG: Print what we're receiving
            print("Received POST data:", dict(post_data))

            # If client type is Individual, remove business_structure requirement
            if post_data.get('client_type') == 'Individual':
                post_data['business_structure'] = ''  # Set to empty

            client_form = ClientForm(post_data)

            if not client_form.is_valid():
                print("Form errors:", client_form.errors)
                return JsonResponse({'success': False, 'errors': client_form.errors})

            print("Form is valid")
            client_type = client_form.cleaned_data.get('client_type')
            business_structure = client_form.cleaned_data.get('business_structure')
            print(f"Client type: {client_type}, Business structure: {business_structure}")

            # Define form templates mapping for Entity types
            structure_map = {
                'Private Ltd': ('company_details_form.html', CompanyDetailsForm),
                'Public Ltd': ('company_details_form.html', CompanyDetailsForm),
                'LLP': ('llp_details_form.html', LLPDetailsForm),
                'OPC': ('opc_details_form.html', OPCDetailsForm),
                'Section 8': ('section8_details_form.html', Section8CompanyDetailsForm),
                'HUF': ('huf_details_form.html', HUFDetailsForm),
            }

            # Store form data in session for multi-step process
            request.session['client_basic_data'] = request.POST.dict()
            request.session.modified = True

            # For Individual clients - redirect to complete save immediately
            if client_type == 'Individual':
                return JsonResponse({
                    'success': True,
                    'redirect_to_complete': True,
                    'client_type': 'Individual'
                })

            # For Entity clients with business structure - show additional form
            if business_structure in structure_map:
                template_name, form_class = structure_map[business_structure]

                # Create form instance with proper queryset filtering
                form_instance = form_class()

                form_html = self.render_form_to_string(request, template_name, {
                    'form': form_instance,
                    'business_structure': business_structure
                })

                return JsonResponse({
                    'success': True,
                    'form_html': form_html,
                    'business_structure': business_structure
                })

            # For Entity clients without specific business structure - save directly
            return JsonResponse({
                'success': True,
                'redirect_to_complete': True,
                'client_type': 'Entity',
                'business_structure': business_structure
            })

        except Exception as e:
            print(f"Unexpected error in SaveClientBasicView: {e}")
            return JsonResponse({'success': False, 'error': f"Unexpected error: {str(e)}"})

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
                    business_structure_result = self._save_business_structure_details(request, business_structure,
                                                                                      client)
                    if business_structure_result is not True:
                        # Rollback transaction if business structure details fail
                        transaction.set_rollback(True)
                        return JsonResponse({'success': False, 'errors': business_structure_result})

                    # Clear session data after successful save
                    self._clear_session_data(request)

                    # Return success with client ID instead of redirecting
                    return JsonResponse({
                        'success': True,
                        'client_id': client.id,
                        'client_name': client.client_name
                    })

                else:
                    return JsonResponse({'success': False, 'errors': client_form.errors})

        except Exception as e:
            print(f"Error in SaveClientCompleteView: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    def _save_business_structure_details(self, request, business_structure, client):
        """Save business structure specific details and create document records"""
        try:
            if business_structure in ['Private Ltd', 'Public Ltd']:
                form = CompanyDetailsForm(request.POST, request.FILES)
                if form.is_valid():
                    company_details = form.save(commit=False)
                    company_details.client = client
                    company_details.save()
                    # Save ManyToMany relationships
                    form.save_m2m()

                    # Create document records for uploaded files
                    if company_details.moa_file:
                        self._create_document_record(
                            client=client,
                            document_name='Memorandum of Association',
                            category='Company Documents',
                            uploaded_file=company_details.moa_file,
                            created_by=request.user
                        )

                    if company_details.aoa_file:
                        self._create_document_record(
                            client=client,
                            document_name='Articles of Association',
                            category='Company Documents',
                            uploaded_file=company_details.aoa_file,
                            created_by=request.user
                        )

                    return True
                return form.errors

            elif business_structure == 'LLP':
                form = LLPDetailsForm(request.POST, request.FILES)
                if form.is_valid():
                    llp_details = form.save(commit=False)
                    llp_details.client = client
                    llp_details.save()
                    # Save ManyToMany relationships
                    form.save_m2m()

                    # Create document record for LLP agreement
                    if llp_details.llp_agreement_file:
                        self._create_document_record(
                            client=client,
                            document_name='LLP Agreement',
                            category='LLP Documents',
                            uploaded_file=llp_details.llp_agreement_file,
                            created_by=request.user
                        )

                    return True
                return form.errors

            elif business_structure == 'OPC':
                form = OPCDetailsForm(request.POST, request.FILES)
                if form.is_valid():
                    opc_details = form.save(commit=False)
                    opc_details.client = client
                    opc_details.save()
                    # OPC doesn't have file fields in your current model
                    return True
                return form.errors

            elif business_structure == 'Section 8':
                form = Section8CompanyDetailsForm(request.POST, request.FILES)
                if form.is_valid():
                    section8_details = form.save(commit=False)
                    section8_details.client = client
                    section8_details.save()
                    # Section 8 doesn't have file fields in your current model
                    return True
                return form.errors

            elif business_structure == 'HUF':
                form = HUFDetailsForm(request.POST, request.FILES)
                if form.is_valid():
                    huf_details = form.save(commit=False)
                    huf_details.client = client
                    huf_details.save()

                    # Create document record for HUF deed
                    if huf_details.deed_of_declaration_file:
                        self._create_document_record(
                            client=client,
                            document_name='HUF Deed of Declaration',
                            category='HUF Documents',
                            uploaded_file=huf_details.deed_of_declaration_file,
                            created_by=request.user
                        )

                    return True
                return form.errors

            return True  # For business structures without additional details

        except Exception as e:
            print(f"Error saving business structure details: {e}")
            return str(e)

    def _create_document_record(self, client, document_name, category, uploaded_file, created_by):
        """Helper method to create document records in the document management system"""
        try:
            # Get or create document master
            document_master, created = DocumentMaster.objects.get_or_create(
                category=category,
                document_name=document_name,
                defaults={'is_active': True}
            )

            # Create a document request for onboarding documents
            document_request = DocumentRequest.objects.create(
                client=client,
                title=f"Onboarding - {document_name}",
                description=f"Automatically created during client onboarding for {client.client_name}",
                due_date=datetime.now().date(),  # Due today since we're uploading now
                created_by=created_by,
                for_all_clients=False
            )

            # Create requested document entry
            requested_document = RequestedDocument.objects.create(
                document_request=document_request,
                document_master=document_master
            )

            # Create the actual upload record
            client_upload = ClientDocumentUpload.objects.create(
                client=client,
                requested_document=requested_document,
                uploaded_file=uploaded_file,
                status='Uploaded',
                remarks=f"Automatically uploaded during client onboarding on {datetime.now().strftime('%Y-%m-%d')}"
            )

            print(f"Created document record: {document_name} for client {client.client_name}")
            return client_upload

        except Exception as e:
            print(f"Error creating document record for {document_name}: {e}")
            # Don't fail the entire process if document record creation fails
            return None

    def _clear_session_data(self, request):
        """Clear session data"""
        if 'client_basic_data' in request.session:
            del request.session['client_basic_data']


class SaveIndividualClientView(LoginRequiredMixin, View):
    """Handle saving individual clients directly (without business structure)"""

    def post(self, request):
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
                            pass

                # Save basic client data
                client_form = ClientForm(processed_basic_data)
                if client_form.is_valid():
                    client = client_form.save(commit=False)
                    client.created_by = request.user
                    client.save()

                    # Clear session data after successful save
                    self._clear_session_data(request)

                    # Return success with client ID instead of redirecting
                    return JsonResponse({
                        'success': True,
                        'client_id': client.id,
                        'client_name': client.client_name
                    })
                else:
                    return JsonResponse({'success': False, 'errors': client_form.errors})

        except Exception as e:
            print(f"Error in SaveIndividualClientView: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

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