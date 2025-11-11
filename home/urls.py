from django.urls import path

from home.customViews import authView
from home.views import HomeView, ClientView, AddClientView, ClientListAPI

urlpatterns = [
    path('', HomeView.as_view(), name='dashboard'),
    path('accounts/login/', authView.LoginView.as_view(), name='login'),
    path('accounts/logout/', authView.LoginView.as_view(), name='logout'),
    path('clients/', ClientView.as_view(), name='clients'),
    path('clients/add/', AddClientView.as_view(), name='add_client'),
    path('api/clients/', ClientListAPI.as_view(), name='api_clients'),
]
