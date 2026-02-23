# from django.shortcuts import render, get_object_or_404, redirect
# from django.contrib import messages
# from django.db import transaction
# from django.http import JsonResponse
# from django.views import View
# from django.views.generic import TemplateView
# from django.contrib.auth.mixins import LoginRequiredMixin
# from django.urls import reverse
# from home.models import (
#     Client, ServiceType, ClientService, GSTDetails, ITRDetails,
#     AuditDetails, IncomeTaxCaseDetails, GSTCaseDetails
# )
# from home.forms import (
#     ClientServiceForm, GSTDetailsForm, ITRDetailsForm,
#     AuditDetailsForm, IncomeTaxCaseForm, GSTCaseForm
# )
# import json
#
#
# class ServiceAssignmentStep1View(LoginRequiredMixin, View):
#     """
#     Step 1: Basic service assignment details
#     """
#     template_name = 'home/service_assignment/step1.html'
#
#     def get(self, request, client_id, service_id):
#         try:
#             client = get_object_or_404(Client, id=client_id)
#             service_type = get_object_or_404(ServiceType, id=service_id, active=True)
#
#             # Check if multiple instances are allowed
#             if not service_type.allow_multiple:
#                 existing_service = ClientService.objects.filter(
#                     client=client,
#                     service=service_type,
#                     is_active=True
#                 ).first()
#
#                 if existing_service:
#                     messages.warning(request,
#                                      f"Service '{service_type.service_name}' is already active for this client and multiple instances are not allowed.")
#                     return redirect('dashboard')
#
#             # Get form data from session if available (for editing)
#             form_data = request.session.get('service_assignment_data', {})
#             form = ClientServiceForm(initial=form_data)
#
#             context = {
#                 'client': client,
#                 'service_type': service_type,
#                 'form': form,
#                 'step': 1,
#                 'total_steps': 3,
#             }
#             return render(request, self.template_name, context)
#
#         except Exception as e:
#             messages.error(request, f"Error loading client/service: {str(e)}")
#             return redirect('dashboard')
#
#     def post(self, request, client_id, service_id):
#         try:
#             client = get_object_or_404(Client, id=client_id)
#             service_type = get_object_or_404(ServiceType, id=service_id, active=True)
#
#             form = ClientServiceForm(request.POST)
#             if form.is_valid():
#                 # Store form data in session
#                 request.session['service_assignment_data'] = {
#                     'client_id': client_id,
#                     'service_id': service_id,
#                     'start_date': form.cleaned_data['start_date'].isoformat(),
#                     'end_date': form.cleaned_data['end_date'].isoformat() if form.cleaned_data['end_date'] else None,
#                     'billing_cycle': form.cleaned_data['billing_cycle'],
#                     'agreed_fee': str(form.cleaned_data['agreed_fee']),
#                     'remarks': form.cleaned_data['remarks'] or '',
#                     'is_active': form.cleaned_data['is_active'],
#                 }
#
#                 messages.success(request, "✅ Step 1 completed! Please provide service-specific details.")
#                 return redirect('service_assignment_step2', client_id=client_id, service_id=service_id)
#
#             context = {
#                 'client': client,
#                 'service_type': service_type,
#                 'form': form,
#                 'step': 1,
#                 'total_steps': 3,
#             }
#             return render(request, self.template_name, context)
#
#         except Exception as e:
#             messages.error(request, f"Error processing form: {str(e)}")
#             return redirect('dashboard')
#
#
# class ServiceAssignmentStep2View(LoginRequiredMixin, View):
#     """
#     Step 2: Service-specific details
#     """
#     template_name = 'home/service_assignment/step2.html'
#
#     def get(self, request, client_id, service_id):
#         # Check if step 1 data exists
#         if 'service_assignment_data' not in request.session:
#             messages.error(request, "Please complete Step 1 first.")
#             return redirect('service_assignment_step1', client_id=client_id, service_id=service_id)
#
#         try:
#             client = get_object_or_404(Client, id=client_id)
#             service_type = get_object_or_404(ServiceType, id=service_id, active=True)
#
#             # Get form class dynamically
#             form_class = self.get_service_form_class(service_type)
#             if not form_class:
#                 messages.error(request, f"No specific form available for service: {service_type.service_name}")
#                 return redirect('service_assignment_step1', client_id=client_id, service_id=service_id)
#
#             # Get form data from session if available
#             form_data = request.session.get('service_specific_data', {})
#             form = form_class(initial=form_data)
#
#             context = {
#                 'client': client,
#                 'service_type': service_type,
#                 'form': form,
#                 'step': 2,
#                 'total_steps': 3,
#             }
#             return render(request, self.template_name, context)
#
#         except Exception as e:
#             messages.error(request, f"Error loading form: {str(e)}")
#             return redirect('service_assignment_step1', client_id=client_id, service_id=service_id)
#
#     def post(self, request, client_id, service_id):
#         try:
#             client = get_object_or_404(Client, id=client_id)
#             service_type = get_object_or_404(ServiceType, id=service_id, active=True)
#
#             form_class = self.get_service_form_class(service_type)
#             form = form_class(request.POST, request.FILES)
#
#             if form.is_valid():
#                 # Store service-specific data in session
#                 service_data = {}
#                 for field_name, field_value in form.cleaned_data.items():
#                     if field_value is not None:
#                         if hasattr(field_value, 'isoformat'):  # Date fields
#                             service_data[field_name] = field_value.isoformat()
#                         else:
#                             service_data[field_name] = str(field_value)
#
#                 request.session['service_specific_data'] = service_data
#                 request.session['service_form_type'] = service_type.service_name
#
#                 messages.success(request, "✅ Step 2 completed! Please review and submit.")
#                 return redirect('service_assignment_step3', client_id=client_id, service_id=service_id)
#
#             context = {
#                 'client': client,
#                 'service_type': service_type,
#                 'form': form,
#                 'step': 2,
#                 'total_steps': 3,
#             }
#             return render(request, self.template_name, context)
#
#         except Exception as e:
#             messages.error(request, f"Error processing form: {str(e)}")
#             return redirect('service_assignment_step2', client_id=client_id, service_id=service_id)
#
#     def get_service_form_class(self, service_type_obj):
#         """Get form class dynamically"""
#         if not service_type_obj or not service_type_obj.form_name:
#             return None
#
#         from home import forms
#         try:
#             form_class = getattr(forms, service_type_obj.form_name)
#             return form_class
#         except AttributeError:
#             return None
#
#
# class ServiceAssignmentStep3View(LoginRequiredMixin, View):
#     """
#     Step 3: Review and submit
#     """
#     template_name = 'home/service_assignment/step3.html'
#
#     def get(self, request, client_id, service_id):
#         # Check if previous steps are completed
#         if 'service_assignment_data' not in request.session or 'service_specific_data' not in request.session:
#             messages.error(request, "Please complete all previous steps first.")
#             return redirect('service_assignment_step1', client_id=client_id, service_id=service_id)
#
#         try:
#             client = get_object_or_404(Client, id=client_id)
#             service_type = get_object_or_404(ServiceType, id=service_id, active=True)
#
#             service_assignment_data = request.session['service_assignment_data']
#             service_specific_data = request.session['service_specific_data']
#
#             context = {
#                 'client': client,
#                 'service_type': service_type,
#                 'service_assignment_data': service_assignment_data,
#                 'service_specific_data': service_specific_data,
#                 'step': 3,
#                 'total_steps': 3,
#             }
#             return render(request, self.template_name, context)
#
#         except Exception as e:
#             messages.error(request, f"Error loading preview: {str(e)}")
#             return redirect('service_assignment_step2', client_id=client_id, service_id=service_id)
#
#     def post(self, request, client_id, service_id):
#         # Check if confirmation was provided
#         if not request.POST.get('confirmation'):
#             messages.error(request, "Please confirm that you want to proceed with this service assignment.")
#             return redirect('service_assignment_step3', client_id=client_id, service_id=service_id)
#
#         try:
#             client = get_object_or_404(Client, id=client_id)
#             service_type = get_object_or_404(ServiceType, id=service_id, active=True)
#
#             service_assignment_data = request.session.get('service_assignment_data')
#             service_specific_data = request.session.get('service_specific_data')
#
#             if not service_assignment_data or not service_specific_data:
#                 messages.error(request, "Session data is missing. Please start the process again.")
#                 return redirect('service_assignment_step1', client_id=client_id, service_id=service_id)
#
#             with transaction.atomic():
#                 # Create ClientService record
#                 client_service = ClientService.objects.create(
#                     client=client,
#                     service=service_type,
#                     start_date=service_assignment_data['start_date'],
#                     end_date=service_assignment_data['end_date'] if service_assignment_data['end_date'] else None,
#                     billing_cycle=service_assignment_data['billing_cycle'],
#                     agreed_fee=service_assignment_data['agreed_fee'],
#                     remarks=service_assignment_data['remarks'],
#                     is_active=service_assignment_data['is_active'],
#                 )
#
#                 # Create service-specific record
#                 self.create_service_specific_record(client_service, service_type, service_specific_data)
#
#                 # Clear session data
#                 del request.session['service_assignment_data']
#                 del request.session['service_specific_data']
#                 if 'service_form_type' in request.session:
#                     del request.session['service_form_type']
#
#                 messages.success(
#                     request,
#                     f" Service '{service_type.service_name}' has been successfully assigned to {client.client_name}!"
#                 )
#
#                 context = {
#                     'client': client,
#                     'service_type': service_type,
#                     'service_assignment_data': service_assignment_data,
#                     'service_specific_data': service_specific_data,
#                     'step': 3,
#                     'total_steps': 3,
#                     'success': True,
#                 }
#                 return render(request, self.template_name, context)
#
#         except Exception as e:
#             messages.error(request, f"Error saving service assignment: {str(e)}")
#             return redirect('service_assignment_step3', client_id=client_id, service_id=service_id)
#
#     def create_service_specific_record(self, client_service, service_type_obj, data):
#         """Create service-specific record dynamically"""
#         if not service_type_obj or not service_type_obj.model_name:
#             return
#
#         from home import models
#         try:
#             model_class = getattr(models, service_type_obj.model_name)
#             record_data = {'client_service': client_service}
#
#             for key, value in data.items():
#                 if value is not None and value != '':
#                     record_data[key] = value
#
#             model_class.objects.create(**record_data)
#
#         except Exception as e:
#             raise e
#
#
# class ClientSuggestionsView(LoginRequiredMixin, View):
#     """
#     AJAX endpoint for client data suggestions
#     """
#
#     def get(self, request, client_id):
#         try:
#             client = get_object_or_404(Client, id=client_id)
#
#             suggestions = {
#                 'pan_number': client.pan_no,
#                 'aadhaar_number': client.aadhar,
#                 'email': client.email,
#                 'phone_number': client.phone_number,
#                 'address': client.address_line1,
#                 'city': client.city,
#                 'state': client.state,
#                 'postal_code': client.postal_code,
#                 'client_name': client.client_name,
#                 'primary_contact_name': client.primary_contact_name,
#             }
#
#             # Remove None/empty values
#             suggestions = {k: v for k, v in suggestions.items() if v}
#
#             return JsonResponse({
#                 'success': True,
#                 'suggestions': suggestions
#             })
#
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'error': str(e)
#             })
#
#
# class EditServiceAssignmentView(LoginRequiredMixin, View):
#     """
#     Edit specific steps of service assignment
#     """
#
#     def get(self, request, client_id, service_id, step):
#         if step == '1':
#             view = ServiceAssignmentStep1View()
#             return view.get(request, client_id, service_id)
#         elif step == '2':
#             view = ServiceAssignmentStep2View()
#             return view.get(request, client_id, service_id)
#         else:
#             return redirect('service_assignment_step3', client_id=client_id, service_id=service_id)
#
#     def post(self, request, client_id, service_id, step):
#         """Handle POST requests from edit pages"""
#         if step == '1':
#             view = ServiceAssignmentStep1View()
#             return view.post(request, client_id, service_id)
#         elif step == '2':
#             view = ServiceAssignmentStep2View()
#             return view.post(request, client_id, service_id)
#         else:
#             return redirect('service_assignment_step3', client_id=client_id, service_id=service_id)
#
#
# class AvailableServicesView(LoginRequiredMixin, View):
#     """
#     AJAX endpoint to get available services for a client
#     Returns only the 5 main service types
#     """
#
#     def get(self, request, client_id):
#         client = get_object_or_404(Client, id=client_id)
#
#         # Define the 5 main service types (exact names)
#         main_services = [
#             'GST Services',
#             'ITR Services',
#             'Audit Services',
#             'Income Tax Case',
#             'GST Case'
#         ]
#
#         # Get all active, non-task services that match our main service types
#         active_services = ServiceType.objects.filter(
#             active=True,
#             is_task=False,
#             service_name__in=main_services
#         ).order_by('service_name')
#
#         # Get already assigned services for this client
#         assigned_service_ids = ClientService.objects.filter(
#             client=client,
#             is_active=True
#         ).values_list('service_id', flat=True)
#
#         # Filter out already assigned services (only if service doesn't allow multiple)
#         available_services = []
#         for service in active_services:
#             if service.id not in assigned_service_ids or service.allow_multiple:
#                 available_services.append(service)
#
#         services_data = []
#         for service in available_services:
#             services_data.append({
#                 'id': service.id,
#                 'name': service.service_name,
#                 'category': service.category,
#                 'frequency': service.frequency,
#                 'description': service.description,
#                 'default_due_days': service.default_due_days,
#             })
#
#         return JsonResponse({'services': services_data})
#
#
# class ServiceDetailView(LoginRequiredMixin, View):
#     """
#     View for displaying complete service details with credentials
#     """
#     template_name = 'client/service_detail.html'
#
#     def get(self, request, service_id, detail_id):
#         try:
#             # Get the client service
#             client_service = get_object_or_404(
#                 ClientService.objects.select_related('client', 'service'),
#                 id=service_id
#             )
#
#             client = client_service.client
#             service_type = client_service.service.service_name
#
#             # Get service-specific details based on service type
#             service_detail = None
#
#             if 'GST Services' in service_type:
#                 service_detail = get_object_or_404(
#                     GSTDetails,
#                     gst_id=detail_id,
#                     client_service=client_service
#                 )
#             elif 'ITR' in service_type:
#                 service_detail = get_object_or_404(
#                     ITRDetails,
#                     itr_id=detail_id,
#                     client_service=client_service
#                 )
#             elif 'Audit' in service_type:
#                 service_detail = get_object_or_404(
#                     AuditDetails,
#                     audit_id=detail_id,
#                     client_service=client_service
#                 )
#             elif 'GST Case' in service_type:
#                 service_detail = get_object_or_404(
#                     GSTCaseDetails,
#                     gst_case_id=detail_id,
#                     client_service=client_service
#                 )
#             elif 'Income Tax Case' in service_type:
#                 service_detail = get_object_or_404(
#                     IncomeTaxCaseDetails,
#                     case_id=detail_id,
#                     client_service=client_service
#                 )
#
#             context = {
#                 'client': client,
#                 'client_service': client_service,
#                 'service_type': service_type,
#                 'service_detail': service_detail,
#             }
#
#             return render(request, self.template_name, context)
#
#         except Exception as e:
#             messages.error(request, f"Error loading service details: {str(e)}")
#             return redirect('dashboard')
