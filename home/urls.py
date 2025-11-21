from django.urls import path
from home.customViews import authView, documentsUploadView, clientView
from home.views import HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='dashboard'),
    path('accounts/login/', authView.LoginView.as_view(), name='login'),
    path('accounts/logout/', authView.LoginView.as_view(), name='logout'),
    # Client Details
    path('client/<int:pk>/details/', clientView.clientDetails, name='client_details'),
    # Documents Upload
    path('dashboard/', documentsUploadView.client_dashboard, name='client_dashboard'),
    path('document-requests/', documentsUploadView.document_requests, name='document_requests'),
    path('upload/<int:requested_document_id>/', documentsUploadView.upload_document, name='upload_document')
]
