from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Client,
    ClientBusinessProfile,
    ClientUserEntitle,
    DocumentMaster,
    DocumentRequest,
    RequestedDocument,
    ClientDocumentUpload,
    Task,
    TaskAssignmentStatus,
    TaskStatusLog,
    TaskExtendedAttributes,
    TaskComment,
    TaskDocument,
    GSTDetails,
)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "client_name",
        "primary_contact_name",
        "client_type",
        "business_structure",
        "pan_no",
        "email",
        "phone_number",
        "city",
        "state",
        "status",
        "assigned_ca",
        "created_at",
    )
    list_filter = (
        "client_type",
        "business_structure",
        "status",
        "state",
        "city",
        "assigned_ca",
        "created_at",
    )
    search_fields = (
        "client_name",
        "primary_contact_name",
        "pan_no",
        "aadhar",
        "din_no",
        "tan_no",
        "email",
        "phone_number",
        "city",
        "state",
    )
    date_hierarchy = "created_at"
    autocomplete_fields = ("assigned_ca", "created_by")


@admin.register(ClientBusinessProfile)
class ClientBusinessProfileAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "registration_number",
        "date_of_incorporation",
        "authorised_capital",
        "paid_up_capital",
        "number_of_directors",
        "number_of_shareholders",
        "number_of_members",
        "is_section8_license_obtained",
    )
    list_filter = (
        "client__business_structure",
        "date_of_incorporation",
        "is_section8_license_obtained",
    )
    search_fields = (
        "client__client_name",
        "registration_number",
        "udyam_registration",
        "opc_nominee_name",
    )
    autocomplete_fields = ("client", "karta", "key_persons")


@admin.register(ClientUserEntitle)
class ClientUserEntitleAdmin(admin.ModelAdmin):
    list_display = ("user", "get_clients", "created_at", "updated_at")
    search_fields = ("user__username", "user__email", "clients__client_name")
    filter_horizontal = ("clients",)

    def get_clients(self, obj):
        names = [c.client_name for c in obj.clients.all()[:3]]
        label = ", ".join(names)
        if obj.clients.count() > 3:
            label += f" (+{obj.clients.count() - 3} more)"
        return label

    get_clients.short_description = "Clients"


@admin.register(DocumentMaster)
class DocumentMasterAdmin(admin.ModelAdmin):
    list_display = ("category", "document_name", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("category", "document_name")


@admin.register(DocumentRequest)
class DocumentRequestAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "client",
        "due_date",
        "for_all_clients",
        "created_by",
        "created_at",
        "is_overdue_flag",
    )
    list_filter = (
        "for_all_clients",
        "due_date",
        "created_by",
        "created_at",
        "client__status",
    )
    search_fields = ("title", "description", "client__client_name", "client__pan_no")
    date_hierarchy = "due_date"
    autocomplete_fields = ("client", "created_by")

    def is_overdue_flag(self, obj):
        color = "red" if obj.is_overdue else "green"
        text = "Yes" if obj.is_overdue else "No"
        return format_html('<span style="color:{};">{}</span>', color, text)

    is_overdue_flag.short_description = "Overdue"


@admin.register(RequestedDocument)
class RequestedDocumentAdmin(admin.ModelAdmin):
    list_display = ("document_request", "document_master")
    list_filter = ("document_master__category", "document_request__due_date")
    search_fields = (
        "document_request__title",
        "document_request__client__client_name",
        "document_master__document_name",
    )
    autocomplete_fields = ("document_request", "document_master")


@admin.register(ClientDocumentUpload)
class ClientDocumentUploadAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "requested_document",
        "status",
        "upload_date",
        "uploaded_by",
    )
    list_filter = ("status", "upload_date", "uploaded_by")
    search_fields = (
        "client__client_name",
        "client__pan_no",
        "requested_document__document_master__document_name",
    )
    date_hierarchy = "upload_date"
    autocomplete_fields = ("client", "requested_document", "uploaded_by")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "task_title",
        "client",
        "service_type",
        "status",
        "priority",
        "due_date",
        "is_recurring",
        "recurrence_period",
        "agreed_fee",
        "fee_status",
        "created_by",
        "created_at",
    )
    list_filter = (
        "service_type",
        "status",
        "priority",
        "is_recurring",
        "recurrence_period",
        "fee_status",
        "due_date",
        "created_at",
        "client__status",
    )
    search_fields = (
        "task_title",
        "description",
        "client__client_name",
        "client__pan_no",
        "client__email",
    )
    date_hierarchy = "due_date"
    autocomplete_fields = ("client", "created_by", "assignees")
    filter_horizontal = ("assignees",)


@admin.register(TaskAssignmentStatus)
class TaskAssignmentStatusAdmin(admin.ModelAdmin):
    list_display = (
        "task",
        "user",
        "status_context",
        "is_completed",
        "completed_at",
        "order",
    )
    list_filter = ("status_context", "is_completed", "completed_at")
    search_fields = (
        "task__task_title",
        "task__client__client_name",
        "user__username",
        "user__email",
    )
    autocomplete_fields = ("task", "user")


@admin.register(TaskStatusLog)
class TaskStatusLogAdmin(admin.ModelAdmin):
    list_display = ("task", "old_status", "new_status", "changed_by", "created_at")
    list_filter = ("old_status", "new_status", "changed_by", "created_at")
    search_fields = (
        "task__task_title",
        "task__client__client_name",
        "changed_by__username",
    )
    date_hierarchy = "created_at"
    autocomplete_fields = ("task", "changed_by")


@admin.register(TaskExtendedAttributes)
class TaskExtendedAttributesAdmin(admin.ModelAdmin):
    list_display = (
        "task",
        "period_month",
        "period_year",
        "financial_year",
        "assessment_year",
        "gst_return_type",
        "total_turnover",
        "tax_payable",
        "refund_amount",
    )
    list_filter = (
        "period_month",
        "period_year",
        "financial_year",
        "assessment_year",
        "gst_return_type",
        "task__service_type",
    )
    search_fields = (
        "task__task_title",
        "task__client__client_name",
        "pan_number",
        "gstin_number",
        "ack_number",
        "arn_number",
        "udin_number",
        "srn_number",
    )
    autocomplete_fields = ("task",)


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ("task", "author", "short_text", "created_at")
    list_filter = ("author", "created_at")
    search_fields = (
        "task__task_title",
        "task__client__client_name",
        "author__username",
        "text",
    )
    date_hierarchy = "created_at"
    autocomplete_fields = ("task", "author")

    def short_text(self, obj):
        return (obj.text[:75] + "...") if len(obj.text) > 75 else obj.text

    short_text.short_description = "Comment"


@admin.register(TaskDocument)
class TaskDocumentAdmin(admin.ModelAdmin):
    list_display = ("task", "uploaded_by", "description", "uploaded_at")
    list_filter = ("uploaded_at", "uploaded_by")
    search_fields = (
        "task__task_title",
        "task__client__client_name",
        "uploaded_by__username",
        "description",
    )
    date_hierarchy = "uploaded_at"
    autocomplete_fields = ("task", "uploaded_by")


@admin.register(GSTDetails)
class GSTDetailsAdmin(admin.ModelAdmin):
    list_display = ("client", "gst_number", "state", "registered_address")
    list_filter = ("state",)
    search_fields = (
        "client__client_name",
        "client__pan_no",
        "gst_number",
        "state",
    )
    autocomplete_fields = ("client",)



# Register your models here.
# office/admin.py

from .models import Shift, EmployeeShift, OfficeDetails


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('shift_name', 'shift_start_time',
                    'shift_end_time', 'maximum_allowed_duration', 'days_off')


@admin.register(EmployeeShift)
class EmployeeShiftAdmin(admin.ModelAdmin):
    list_display = ('user', 'shift', 'valid_from', 'valid_to')
    list_filter = ('shift', 'valid_from', 'valid_to')


@admin.register(OfficeDetails)
class OfficeDetailsAdmin(admin.ModelAdmin):
    list_display = ('office_name', 'contact_person_name',
                    'office_contact_no', 'latitude', 'longitude')
    search_fields = ('office_name', 'contact_person_name')

