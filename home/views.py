from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from .models import Client
from .forms import ClientForm
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views import View

class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        return render(request, "dashboard.html")


class ClientView(ListView):
    model = Client
    template_name = 'clients.html'
    context_object_name = 'clients'
    paginate_by = 10


class AddClientView(LoginRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'add_client.html'
    success_url = reverse_lazy('clients')

    def form_valid(self, form):
        # Set the created_by field to the current user
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Client added successfully!')
        return super().form_valid(form)


class ClientListAPI(View):
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