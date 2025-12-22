from django.urls import path

from home.customViews import authView, documentsUploadView, clientView, taskView, clientOnboardingView
# from home.customViews.serviceViews import (
#     ServiceAssignmentStep1View, ServiceAssignmentStep2View, ServiceAssignmentStep3View,
#     EditServiceAssignmentView, ClientSuggestionsView, AvailableServicesView, ServiceDetailView,
# )
from home.views import (
    HomeView,
    ClientView
)

from django.urls import path
from home.customViews.notificationView import dashboard
from home.customViews.notificationView import (
    read_all_notifications,
    view_notification,
    all_notifications,
)

urlpatterns = [
    path('', HomeView.as_view(), name='dashboard'),
    path('accounts/login/', authView.LoginView.as_view(), name='login'),
    path('accounts/logout/', authView.LoginView.as_view(), name='logout'),
    # Client Details
    path('client/<int:client_id>/details/', clientView.client_details_view, name='client_details'),
    path('client/<int:client_id>/upload-document/', documentsUploadView.upload_document_view,
         name='upload_client_document'),
    path('client/<int:client_id>/create-request/', documentsUploadView.create_document_request_view,
         name='create_client_doc_request'),
    path('client/<int:client_id>/create-task/', taskView.create_task_view, name='create_service_task'),
    # Client Management
    path('clients/', ClientView.as_view(), name='clients'),
    path('onboard/', clientOnboardingView.onboard_client_view, name='onboard_client'),
    path('tasks/', taskView.task_list_view, name='task_list'),
    path('tasks/<int:task_id>/', taskView.task_detail_view, name='task_detail'),
    path('tasks/<int:task_id>/edit/', taskView.edit_task_view, name='edit_task'),
    path('', dashboard, name='dashboard'),
    #NOTIFICATIONS
    path("notifications/read-all/", read_all_notifications, name="read_all_notifications"),
    path("notifications/<int:notification_id>/", view_notification, name="view_notification"),
    path("notifications/", all_notifications, name="all_notifications"),
]
