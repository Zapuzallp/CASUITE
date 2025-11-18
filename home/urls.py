from django.urls import path

from home.customViews import authView, documentsUploadView, clientView
from home.views import HomeView
from home.customViews.serviceViews import (
    ServiceAssignmentStep1View, ServiceAssignmentStep2View, ServiceAssignmentStep3View,
    EditServiceAssignmentView, ClientSuggestionsView, AvailableServicesView
)

urlpatterns = [
    path('', HomeView.as_view(), name='dashboard'),
    path('accounts/login/', authView.LoginView.as_view(), name='login'),
    path('accounts/logout/', authView.LoginView.as_view(), name='logout'),
    # Client Details
    path('client/<int:pk>/details/', clientView.clientDetails, name='client_details'),
    # Documents Upload
    path('dashboard/', documentsUploadView.client_dashboard, name='client_dashboard'),
    path('document-requests/', documentsUploadView.document_requests, name='document_requests'),
    path('upload/<int:requested_document_id>/', documentsUploadView.upload_document, name='upload_document'),
    # Client Details
    path('client/<int:pk>/details/', clientView.clientDetails, name='client_details'),
    # Documents Upload
    path('dashboard/', documentsUploadView.client_dashboard, name='client_dashboard'),
    path('document-requests/', documentsUploadView.document_requests, name='document_requests'),
    path('upload/<int:requested_document_id>/', documentsUploadView.upload_document, name='upload_document'),

    # Service Assignment Wizard URLs
    path('client/<int:client_id>/service/<int:service_id>/add/',
         ServiceAssignmentStep1View.as_view(), name='service_assignment_step1'),
    path('client/<int:client_id>/service/<int:service_id>/add/step2/',
         ServiceAssignmentStep2View.as_view(), name='service_assignment_step2'),
    path('client/<int:client_id>/service/<int:service_id>/add/step3/',
         ServiceAssignmentStep3View.as_view(), name='service_assignment_step3'),
    path('client/<int:client_id>/service/<int:service_id>/add/edit/<str:step>/',
         EditServiceAssignmentView.as_view(), name='edit_service_assignment_step'),

    # AJAX endpoints
    path('api/client/<int:client_id>/available-services/',
         AvailableServicesView.as_view(), name='get_available_services'),
    path('api/client/<int:client_id>/suggestions/',
         ClientSuggestionsView.as_view(), name='get_client_suggestions'),
]
