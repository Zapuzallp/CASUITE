from django.utils.html import format_html
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin

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
    Employee,
    Shift, EmployeeShift, OfficeDetails,
    Message
)


class ClientResource(resources.ModelResource):
    # ===============================
    # Business Profile Fields
    # ===============================
    registration_number = fields.Field(column_name='registration_number')
    date_of_incorporation = fields.Field(column_name='date_of_incorporation')
    registered_office_address = fields.Field(column_name='registered_office_address')
    udyam_registration = fields.Field(column_name='udyam_registration')
    authorised_capital = fields.Field(column_name='authorised_capital')
    paid_up_capital = fields.Field(column_name='paid_up_capital')
    number_of_directors = fields.Field(column_name='number_of_directors')
    number_of_shareholders = fields.Field(column_name='number_of_shareholders')
    number_of_members = fields.Field(column_name='number_of_members')
    object_clause = fields.Field(column_name='object_clause')
    is_section8_license_obtained = fields.Field(column_name='is_section8_license_obtained')

    # Add key_persons explicitly if you want to use widgets,
    # otherwise we handle it manually in after_import_row
    key_persons = fields.Field(column_name='key_persons')

    class Meta:
        model = Client
        import_id_fields = ('pan_no',)
        fields = (
            # Client fields
            'client_name',
            'primary_contact_name',
            'pan_no',
            'aadhar',
            'din_no',
            'tan_no',
            'email',
            'phone_number',
            'city',
            'state',
            'postal_code',
            'country',
            'date_of_engagement',
            'assigned_ca',
            'client_type',
            'business_structure',
            'status',
            'father_name',
            'office_location',
            'remarks',
            'created_by',
            'created_at',
            'updated_at',

            # Business profile fields
            'registration_number',
            'date_of_incorporation',
            'registered_office_address',
            'udyam_registration',
            'authorised_capital',
            'paid_up_capital',
            'number_of_directors',
            'number_of_shareholders',
            'number_of_members',
            'number_of_coparceners',
            'opc_nominee_name',
            'object_clause',
            'is_section8_license_obtained',
            'key_persons',  # Ensure this is in fields
        )

    def after_import_row(self, row, row_result, **kwargs):
        # 1. Get the Main Client Instance
        try:
            # Strip whitespace just in case the PAN has spaces
            pan = str(row.get('pan_no', '')).strip()
            client = Client.objects.get(pan_no=pan)
        except Client.DoesNotExist:
            return

        # --- HELPER FUNCTION TO CLEAN DATA ---
        def clean_val(value):
            """
            Converts empty strings, 'None', 'nan' (from pandas), or whitespace
            into a proper Python None object.
            """
            if value is None:
                return None
            # If it's already a date/number object, return it
            if not isinstance(value, str):
                return value

            # Check string values
            cleaned = value.strip()
            if not cleaned or cleaned.lower() in ['none', 'null', 'nan']:
                return None
            return cleaned

        # 2. Extract Many-to-Many data separately
        key_persons_raw = row.get('key_persons')

        # 3. Create or Update Profile
        # We wrap fields in clean_val() to ensure no bad strings get passed to Date/Decimal fields
        ClientBusinessProfile.objects.update_or_create(
            client=client,
            defaults={
                'registration_number': clean_val(row.get('registration_number')),

                # DATE FIELDS: Crucial to use clean_val here
                'date_of_incorporation': clean_val(row.get('date_of_incorporation')),

                'registered_office_address': row.get('registered_office_address'),
                'udyam_registration': row.get('udyam_registration'),

                # DECIMAL/INTEGER FIELDS: prevent "ValueError" on empty strings
                'authorised_capital': clean_val(row.get('authorised_capital')),
                'paid_up_capital': clean_val(row.get('paid_up_capital')),
                'number_of_directors': clean_val(row.get('number_of_directors')),
                'number_of_shareholders': clean_val(row.get('number_of_shareholders')),
                'number_of_members': clean_val(row.get('number_of_members')),
                'number_of_coparceners': clean_val(row.get('number_of_coparceners')),

                'opc_nominee_name': row.get('opc_nominee_name'),
                'object_clause': row.get('object_clause'),

                # BOOLEAN FIELD HANDLING
                'is_section8_license_obtained': str(row.get('is_section8_license_obtained')).lower() in ['1', 'true',
                                                                                                         'yes'],
            }
        )

        # 4. Handle Many-to-Many assignment
        if key_persons_raw:
            # Fetch the profile again to be safe
            profile = client.business_profile

            # Logic assuming input is "1, 2, 3" (IDs)
            try:
                # Ensure we are splitting a string
                raw_str = str(key_persons_raw)
                ids = [int(x.strip()) for x in raw_str.split(',') if x.strip().isdigit()]
                if ids:
                    profile.key_persons.set(ids)
            except Exception:
                pass

from django.contrib import admin
from .models import Notification

@admin.register(Client)
class ClientAdmin(ImportExportModelAdmin):
    resource_class = ClientResource

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
    # Restrict client list in admin
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(assigned_ca=request.user)


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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(client__assigned_ca=request.user)


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
    #-----------------------------------------------------------------
    # Prevent staff users from viewing tasks of unassigned clients.
    #-----------------------------------------------------------------
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(client__assigned_ca=request.user)


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

    # Restrict admin visibility so staff users see only records linked to their assigned clients
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(task__client__assigned_ca=request.user)


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


from .models import Attendance

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "date",
        "clock_in",
        "clock_out",
        "duration",
        "status",
        "requires_approval",
        "location_name",
    )
    list_filter = ("status", "requires_approval", "date")
    search_fields = ("user__username", "location_name")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "designation",
        "created_at",
    )

    list_filter = (
        "designation",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "personal_email",
        "personal_phone",
        "work_phone",
    )

    autocomplete_fields = ("user",)

    date_hierarchy = "created_at"

#notification
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username')

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
    # search_fields = ('office_name', 'contact_person_name')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver','status','timestamp')
    list_filter = ('status','timestamp')
    search_fields = ('content','sender__username','receiver__username')
    ordering = ('-timestamp',)
