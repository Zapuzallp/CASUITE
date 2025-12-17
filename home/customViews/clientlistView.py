from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from home.models import Client, ClientUserEntitle

class ClientView(LoginRequiredMixin, ListView):
    model = Client
    template_name = 'client/clients_all.html'
    context_object_name = 'clients'
    paginate_by = 10


    def get_queryset(self):
        if self.request.user.is_superuser:
            return Client.objects.all()
        else:
            return Client.objects.filter(
                user_mappings__user=self.request.user
                ).distinct().order_by('client_name')
