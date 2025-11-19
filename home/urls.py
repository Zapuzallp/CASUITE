from django.urls import path

from home.customViews import authView, documentsUploadView, clientView
from home.views import (
    HomeView,
    ClientView,
    AddClientView,
    ClientListAPI,
    SaveClientBasicView,
    SaveClientCompleteView,
    SaveIndividualClientView,
    ClearClientSessionView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='dashboard'),
    path('accounts/login/', authView.LoginView.as_view(), name='login'),
    path('accounts/logout/', authView.LoginView.as_view(), name='logout'),
    # Client Details
    path('client/<int:pk>/details/', clientView.clientDetails, name='client_details'),
    # Client Management
    path('clients/', ClientView.as_view(), name='clients'),
    path('clients/onboarding/', AddClientView.as_view(), name='add_client'),
    path('clients/save-basic/', SaveClientBasicView.as_view(), name='save_client_basic'),
    path('clients/save-complete/', SaveClientCompleteView.as_view(), name='save_client_complete'),
    path('clients/save-individual/', SaveIndividualClientView.as_view(), name='save_individual_client'),
    path('clients/clear-session/', ClearClientSessionView.as_view(), name='clear_client_session'),
    path('api/clients/', ClientListAPI.as_view(), name='api_clients'),
    # Documents Upload
    path('dashboard/', documentsUploadView.client_dashboard, name='client_dashboard'),
    path('document-requests/', documentsUploadView.document_requests, name='document_requests'),
    path('upload/<int:requested_document_id>/', documentsUploadView.upload_document, name='upload_document'),
]
