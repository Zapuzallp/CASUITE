from django.urls import path

from home.customViews import authView, documentsUploadView, clientView, taskView, clientOnboardingView, leaveView
from home.customViews import resetPassword
from home.customViews.attendanceView import (
    ClockInView,
    ClockOutView,
    AttendanceLogsView,
)
from home.customViews.notificationView import dashboard
from home.customViews.services import list_services, delete_service
from home.customViews.notificationView import (
    read_all_notifications,
    view_notification,
    all_notifications,
)
# from home.customViews.serviceViews import (
#     ServiceAssignmentStep1View, ServiceAssignmentStep2View, ServiceAssignmentStep3View,
#     EditServiceAssignmentView, ClientSuggestionsView, AvailableServicesView, ServiceDetailView,
# )
from home.views import (
    HomeView
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
    path('clients/', clientOnboardingView.ClientView.as_view(), name='clients'),
    path('client/<int:client_id>/edit/', clientOnboardingView.edit_client_view, name='edit_client'),
    path('onboard/', clientOnboardingView.onboard_client_view, name='onboard_client'),
    path('tasks/', taskView.task_list_view, name='task_list'),
    path('tasks/<int:task_id>/', taskView.task_detail_view, name='task_detail'),
    path('tasks/<int:task_id>/edit/', taskView.edit_task_view, name='edit_task'),

    # reset password
    path('password/change/', resetPassword.CustomPasswordChangeView.as_view(), name='password_change'),
    path('password/change/done/', resetPassword.CustomPasswordChangeDoneView.as_view(), name='password_change_done'),
    path("attendance/clock-in/", ClockInView.as_view(), name="clock_in"),
    path("attendance/clock-out/", ClockOutView.as_view(), name="clock_out"),
    path("attendance/logs/", AttendanceLogsView.as_view(), name="attendance_logs"),
    path('', dashboard, name='dashboard'),
    #NOTIFICATIONS
    path("notifications/read-all/", read_all_notifications, name="read_all_notifications"),
    path("notifications/<int:notification_id>/", view_notification, name="view_notification"),
    path("notifications/", all_notifications, name="all_notifications"),
    #apply-leave
    path('leave/apply/', leaveView.LeaveCreateView.as_view(), name='leave-apply'),
    #delete-leave
    path('leave/<int:leave_id>/',leaveView.LeaveDeleteView.as_view(), name='leave-delete'),
    #list services
    path('services/', list_services, name='list_services'),
    #delete service
    path('services/delete/<int:service_id>/', delete_service, name='delete_service'),

]
