from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.views.generic import ListView
from home.models import Client

class ClientView(LoginRequiredMixin, ListView):
    """View for displaying client list page"""
    model = Client
    template_name = 'client/clients_all.html'
    context_object_name = 'clients'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Client.objects.all()
        return Client.objects.filter(assigned_ca=user)