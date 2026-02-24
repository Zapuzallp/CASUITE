from django.urls import path

from home.customViews import authView, documentsUploadView, clientView, taskView, clientOnboardingView, leaveView, leave_views,messageView , ReApplyLeaveViews
from home.customViews import resetPassword, leadView
from home.customViews import authView, documentsUploadView, clientView, taskView, clientOnboardingView, leaveView, \
    leave_views, messageView, ReApplyLeaveViews, invoiceView, profileView, credentialsView, clientExportView
from home.customViews import resetPassword
from home.customViews.attendanceView import (
    ClockInView,
    ClockOutView,
    AttendanceLogsView,
)
from home.customViews.adminReportsView import AdminAttendanceReportView
from home.customViews.notificationView import dashboard
from home.customViews.services import list_services, delete_service
from home.customViews.searchbarView import global_search
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
    HomeView, due_tasks_ajax
)
from home.customViews.payment_views import (
    payment_list, payment_collect, approve_payment,
    reject_payment, payment_detail, cancel_payment, bulk_payment_action
)
from home.views import client_search
urlpatterns = [
    path('', HomeView.as_view(), name='dashboard'),
    path('api/due-tasks/', due_tasks_ajax, name='due_tasks_ajax'),
    path('accounts/login/', authView.LoginView.as_view(), name='login'),
    path('accounts/logout/', authView.LoginView.as_view(), name='logout'),
    # Client Details
    path('client/<int:client_id>/details/', clientView.client_details_view, name='client_details'),
    path('client/<int:client_id>/upload-document/', documentsUploadView.upload_document_view,
         name='upload_client_document'),
    path('client/<int:client_id>/create-request/', documentsUploadView.create_document_request_view,
         name='create_client_doc_request'),
    path('client/<int:client_id>/create-task/', taskView.create_task_view, name='create_service_task'),

    # GST Management
    path('client/<int:client_id>/add-gst/', clientView.add_gst_details_view, name='add_gst_details'),
    path('gst/<int:gst_id>/edit/', clientView.edit_gst_details_view, name='edit_gst_details'),
    path('gst/<int:gst_id>/delete/', clientView.delete_gst_details_view, name='delete_gst_details'),

    # Client Management
    path('clients/', clientOnboardingView.ClientView.as_view(), name='clients'),
    path('client/<int:client_id>/edit/', clientOnboardingView.edit_client_view, name='edit_client'),
    path('onboard/', clientOnboardingView.onboard_client_view, name='onboard_client'),

    # Client Export
    path('clients/export/', clientExportView.client_export_select_columns, name='client_export_select_columns'),
    path('clients/export/generate/', clientExportView.client_export_generate, name='client_export_generate'),
    path('tasks/', taskView.task_list_view, name='task_list'),
    path('tasks/<int:task_id>/', taskView.task_detail_view, name='task_detail'),
    path('tasks/<int:task_id>/edit/', taskView.edit_task_view, name='edit_task'),
    path('tasks/<int:task_id>/copy/', taskView.copy_task_view, name='task_copy'),
    path('clients/search/', client_search, name='client_search'),

    # reset password
    path('password/change/', resetPassword.CustomPasswordChangeView.as_view(), name='password_change'),
    path('password/change/done/', resetPassword.CustomPasswordChangeDoneView.as_view(), name='password_change_done'),
    path("attendance/clock-in/", ClockInView.as_view(), name="clock_in"),
    path("attendance/clock-out/", ClockOutView.as_view(), name="clock_out"),
    path("attendance/logs/", AttendanceLogsView.as_view(), name="attendance_logs"),
    path('', dashboard, name='dashboard'),
    # NOTIFICATIONS
    path("notifications/read-all/", read_all_notifications, name="read_all_notifications"),
    path("notifications/<int:notification_id>/", view_notification, name="view_notification"),
    path("notifications/", all_notifications, name="all_notifications"),

    # Attendance
    path("attendance/clock-in/", ClockInView.as_view(), name="clock_in"),
    path("attendance/clock-out/", ClockOutView.as_view(), name="clock_out"),
    path("attendance/logs/", AttendanceLogsView.as_view(), name="attendance_logs"),
    path("admin-report/attendance/", AdminAttendanceReportView.as_view(), name="admin_attendance_report"),

    # apply-leave
    path('leave/apply/', leaveView.LeaveCreateView.as_view(), name='leave-apply'),
    # delete-leave
    path('leave/<int:leave_id>/', leaveView.LeaveDeleteView.as_view(), name='leave-delete'),
    # Leave re-apply URL
    path('leave/reapply/<int:pk>/', ReApplyLeaveViews.leave_reapply, name='leave-reapply'),
    # list services
    path('services/', list_services, name='list_services'),
    # delete service
    path('services/delete/<int:service_id>/', delete_service, name='delete_service'),
    # manage_leaves
    path('manage-leaves/', leave_views.ManageLeavesView.as_view(), name='manage-leaves'),
    # chat message
    path('chat/', messageView.chat_view, name='chat_base'),
    path('chat/<int:user_id>/', messageView.chat_view, name='chat_with_user'),

    # Payments
    path('payments/', payment_list, name='payment_list'),
    path('payment/<int:invoice_id>/collect/', payment_collect, name='payment_collect'),
    path('payments/<int:payment_id>/approve/', approve_payment, name='approve_payment'),
    path('payments/<int:payment_id>/reject/', reject_payment, name='reject_payment'),
    path('payments/<int:payment_id>/cancel/', cancel_payment, name='cancel_payment'),
    path('payments/<int:payment_id>/', payment_detail, name='payment_detail'),
    path('payments/bulk-action/', bulk_payment_action, name='bulk_payment_action'),

    #search-bar
    path('global-search/', global_search, name='global_search'),

    # Lead Management
    path('leads/', leadView.lead_list_view, name='lead_list'),
    path('leads/add/', leadView.add_lead_view, name='add_lead'),
    path('leads/<int:lead_id>/', leadView.lead_detail_view, name='lead_detail'),
    path('leads/<int:lead_id>/edit/', leadView.edit_lead_view, name='edit_lead'),
    path('leads/<int:lead_id>/mark-contacted/', leadView.mark_lead_contacted, name='mark_lead_contacted'),
    path('leads/<int:lead_id>/mark-qualified/', leadView.mark_lead_qualified, name='mark_lead_qualified'),
    path('leads/<int:lead_id>/mark-lost/', leadView.mark_lead_lost, name='mark_lead_lost'),
    path('leads/<int:lead_id>/convert/', leadView.convert_lead_view, name='convert_lead'),
    path('leads/<int:lead_id>/add-call-log/', leadView.add_lead_call_log, name='add_lead_call_log'),
    # Invoice URLs (using invoiceView)
    path('invoices/', invoiceView.InvoiceListCreateView.as_view(), name='invoice_list'),
    path('invoice/', invoiceView.InvoiceListCreateView.as_view(), name='invoice_all'),
    path('ajax/load-tasks/', invoiceView.load_tasks, name='load_tasks'),
    path('invoice/<int:invoice_id>/details/', invoiceView.invoice_details, name='invoice_details'),
    path('invoice/<int:pk>/items/add/', invoiceView.add_invoice_item_ajax, name='add-invoice-item'),
    path('invoice/<int:item_id>/delete/', invoiceView.invoice_item_delete, name='invoice_delete-item'),
    path('invoice/<int:invoice_id>/approve/', invoiceView.approve_invoice, name="invoice_approve"),
    path('invoice/<int:invoice_id>/change-status/', invoiceView.change_invoice_status, name="invoice_change_status"),
    path('invoices/bulk-status-update/', invoiceView.invoice_bulk_status_update, name="invoice_bulk_status_update"),
    #profile url
    path('upload-profile-pic/', profileView.upload_profile_pic, name='upload_profile_pic'),
    # Portal Credentials
    path('client/<int:client_id>/credentials/add/', credentialsView.add_portal_credential,name='add_portal_credential'),
    path('credentials/<int:credential_id>/view/', credentialsView.view_portal_credential,name='view_portal_credential'),
    path('credentials/<int:credential_id>/delete/', credentialsView.delete_portal_credential,name='delete_portal_credential'),


]
