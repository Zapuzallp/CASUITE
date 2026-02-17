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
    Leave,
    Message,
    TaskRecurrence,
    Lead,
    LeadCallLog
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


# =====================================================
# INLINE BUSINESS PROFILE
# =====================================================
class ClientBusinessProfileInline(admin.StackedInline):
    model = ClientBusinessProfile
    fk_name = "client"  # IMPORTANT: required in your case
    extra = 0
    max_num = 1
    can_delete = False
    autocomplete_fields = ("karta", "key_persons")


@admin.register(Client)
class ClientAdmin(ImportExportModelAdmin):
    resource_class = ClientResource
    inlines = [ClientBusinessProfileInline]

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
        "last_auto_created_at",
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

    # -----------------------------------------------------------------
    # Prevent staff users from viewing tasks of unassigned clients.
    # -----------------------------------------------------------------
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


@admin.register(TaskRecurrence)
class TaskRecurrenceAdmin(admin.ModelAdmin):
    list_display = (
        "task",
        "recurrence_period",
        "created_at",
        "is_recurring",
        "next_run_at",
        "last_auto_created_at"

    )


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
    list_display = ("client", "gst_number", "state", "registered_address", "status", "gst_scheme_type")
    list_filter = ("state", "status", "gst_scheme_type")
    search_fields = (
        "client__client_name",
        "client__pan_no",
        "gst_number",
        "state",
    )
    autocomplete_fields = ("client",)

    change_list_template = "admin/gst_details_changelist.html"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('import-gst/', self.admin_site.admin_view(self.import_gst_view), name='gst-import'),
            path('download-template/', self.admin_site.admin_view(self.download_template_view),
                 name='gst-download-template'),
        ]
        return custom_urls + urls

    def download_template_view(self, request):
        """Download Excel template with all GST fields"""
        from django.http import HttpResponse
        import pandas as pd
        from io import BytesIO

        # Create template with all fields and sample data
        template_data = {
            'CLIENT_NAME': ['ABC Traders', 'XYZ Industries', ''],
            'GST_NUMBER': ['27AABCU9603R1ZM', '19AADCS1234F1Z5', ''],
            'REGISTERED_ADDRESS': ['123 Main St, Mumbai', '456 Park Ave, Kolkata', ''],
            'STATE_CODE': ['27', '19', ''],
            'GST_SCHEME_TYPE': ['Regular', 'Composition', ''],
            'STATUS': ['Active', 'Active', ''],
        }

        df = pd.DataFrame(template_data)

        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='GST Details')

            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['GST Details']

            # Add instructions sheet
            instructions_data = {
                'Field Name': [
                    'CLIENT_NAME',
                    'GST_NUMBER',
                    'REGISTERED_ADDRESS',
                    'STATE_CODE',
                    'GST_SCHEME_TYPE',
                    'STATUS'
                ],
                'Required': [
                    'Yes',
                    'Yes',
                    'No',
                    'No (auto-derived from GST)',
                    'No (default: Regular)',
                    'No (default: Active)'
                ],
                'Description': [
                    'Client name (must match existing client)',
                    '15-character GST number',
                    'Registered address (optional)',
                    'State code 01-38 (auto-filled if empty)',
                    'Regular / Composition / QRMP',
                    'Active / Closed'
                ],
                'Example': [
                    'ABC Traders',
                    '27AABCU9603R1ZM',
                    '123 Main Street, Mumbai',
                    '27',
                    'Regular',
                    'Active'
                ]
            }

            df_instructions = pd.DataFrame(instructions_data)
            df_instructions.to_excel(writer, index=False, sheet_name='Instructions')

        output.seek(0)

        # Create response
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=GST_Import_Template.xlsx'

        return response

    def import_gst_view(self, request):
        from django.shortcuts import render, redirect
        from django.contrib import messages
        from django.db import transaction
        from django.db.models import Q
        import pandas as pd
        from home.models import Client, GSTDetails

        if request.method == 'POST':
            excel_file = request.FILES.get('excel_file')

            if not excel_file:
                messages.error(request, 'Please select an Excel file')
                return redirect('..')

            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                messages.error(request, 'Please upload a valid Excel file (.xlsx or .xls)')
                return redirect('..')

            try:
                # Read Excel file
                df = pd.read_excel(excel_file, engine='openpyxl')

                # Check for required columns (flexible naming)
                # Support both old format (PROPRIETOR NAME, GST NO) and new format (CLIENT_NAME, GST_NUMBER)
                client_col = None
                gst_col = None

                for col in df.columns:
                    col_upper = col.upper().strip()
                    if col_upper in ['CLIENT_NAME', 'PROPRIETOR NAME', 'CLIENT NAME']:
                        client_col = col
                    elif col_upper in ['GST_NUMBER', 'GST NO', 'GST NUMBER', 'GSTIN']:
                        gst_col = col

                if not client_col or not gst_col:
                    messages.error(
                        request,
                        'Excel file must contain CLIENT_NAME and GST_NUMBER columns '
                        '(or PROPRIETOR NAME and GST NO)'
                    )
                    return redirect('..')

                # Optional columns
                address_col = None
                state_col = None
                scheme_col = None
                status_col = None

                for col in df.columns:
                    col_upper = col.upper().strip()
                    if col_upper in ['REGISTERED_ADDRESS', 'ADDRESS']:
                        address_col = col
                    elif col_upper in ['STATE_CODE', 'STATE CODE', 'STATE']:
                        state_col = col
                    elif col_upper in ['GST_SCHEME_TYPE', 'SCHEME TYPE', 'SCHEME']:
                        scheme_col = col
                    elif col_upper in ['STATUS']:
                        status_col = col

                total_rows = len(df)

                # Statistics
                stats = {
                    'success': 0,
                    'skipped_missing_name': 0,
                    'skipped_missing_gst': 0,
                    'skipped_no_client': 0,
                    'skipped_multiple_clients': 0,
                    'skipped_duplicate_gst': 0,
                    'skipped_invalid_gst': 0,
                    'skipped_invalid_scheme': 0,
                    'skipped_invalid_status': 0,
                }

                # GST State Code Mapping
                GST_STATE_CODES = {
                    '01': '01', '02': '02', '03': '03', '04': '04', '05': '05',
                    '06': '06', '07': '07', '08': '08', '09': '09', '10': '10',
                    '11': '11', '12': '12', '13': '13', '14': '14', '15': '15',
                    '16': '16', '17': '17', '18': '18', '19': '19', '20': '20',
                    '21': '21', '22': '22', '23': '23', '24': '24', '26': '26',
                    '27': '27', '29': '29', '30': '30', '31': '31', '32': '32',
                    '33': '33', '34': '34', '35': '35', '36': '36', '37': '37',
                    '38': '38', '97': '97',
                }

                # Valid scheme types and statuses
                VALID_SCHEMES = ['Regular', 'Composition', 'QRMP']
                VALID_STATUSES = ['Active', 'Closed']

                # Process each row
                for index, row in df.iterrows():
                    client_name = row.get(client_col)
                    gst_no = row.get(gst_col)

                    # Skip if missing required data
                    if pd.isna(client_name) or str(client_name).strip() == '':
                        stats['skipped_missing_name'] += 1
                        continue

                    if pd.isna(gst_no) or str(gst_no).strip() == '':
                        stats['skipped_missing_gst'] += 1
                        continue

                    # Clean required data
                    client_name = str(client_name).strip()
                    gst_no = str(gst_no).strip().upper()

                    # Validate GST format
                    if len(gst_no) != 15:
                        stats['skipped_invalid_gst'] += 1
                        continue

                    # Extract state code from GST
                    state_code_from_gst = gst_no[:2]
                    if state_code_from_gst not in GST_STATE_CODES:
                        stats['skipped_invalid_gst'] += 1
                        continue

                    # Get optional fields
                    registered_address = None
                    if address_col and not pd.isna(row.get(address_col)):
                        registered_address = str(row.get(address_col)).strip()

                    state_code = state_code_from_gst  # Default from GST
                    if state_col and not pd.isna(row.get(state_col)):
                        provided_state = str(row.get(state_col)).strip()
                        if provided_state in GST_STATE_CODES:
                            state_code = provided_state

                    gst_scheme_type = 'Regular'  # Default
                    if scheme_col and not pd.isna(row.get(scheme_col)):
                        provided_scheme = str(row.get(scheme_col)).strip()
                        if provided_scheme in VALID_SCHEMES:
                            gst_scheme_type = provided_scheme
                        else:
                            stats['skipped_invalid_scheme'] += 1
                            continue

                    status = 'Active'  # Default
                    if status_col and not pd.isna(row.get(status_col)):
                        provided_status = str(row.get(status_col)).strip()
                        if provided_status in VALID_STATUSES:
                            status = provided_status
                        else:
                            stats['skipped_invalid_status'] += 1
                            continue

                    # Find client (case-insensitive)
                    clients = Client.objects.filter(Q(client_name__iexact=client_name))

                    if not clients.exists():
                        stats['skipped_no_client'] += 1
                        continue

                    if clients.count() > 1:
                        stats['skipped_multiple_clients'] += 1
                        continue

                    client = clients.first()

                    # Check if GST already exists
                    if GSTDetails.objects.filter(client=client, gst_number=gst_no).exists():
                        stats['skipped_duplicate_gst'] += 1
                        continue

                    # Use client's address if not provided in Excel
                    if not registered_address and client.address_line1:
                        registered_address = client.address_line1

                    # Create GST Details
                    try:
                        with transaction.atomic():
                            GSTDetails.objects.create(
                                client=client,
                                gst_number=gst_no,
                                gst_scheme_type=gst_scheme_type,
                                state=GST_STATE_CODES[state_code],
                                registered_address=registered_address,
                                status=status,
                                created_by=request.user
                            )
                            stats['success'] += 1
                    except Exception as e:
                        messages.warning(request, f'Error creating GST for {client_name}: {str(e)}')

                # Show summary
                total_skipped = sum([
                    stats['skipped_missing_name'],
                    stats['skipped_missing_gst'],
                    stats['skipped_invalid_gst'],
                    stats['skipped_no_client'],
                    stats['skipped_multiple_clients'],
                    stats['skipped_duplicate_gst'],
                    stats['skipped_invalid_scheme'],
                    stats['skipped_invalid_status'],
                ])

                messages.success(
                    request,
                    f'✅ Import completed! Successfully created: {stats["success"]}, '
                    f'Skipped: {total_skipped} (Total rows: {total_rows})'
                )

                if stats['skipped_missing_name'] > 0:
                    messages.info(request, f'⚠️ Skipped {stats["skipped_missing_name"]} rows with missing CLIENT_NAME')
                if stats['skipped_missing_gst'] > 0:
                    messages.info(request, f'⚠️ Skipped {stats["skipped_missing_gst"]} rows with missing GST_NUMBER')
                if stats['skipped_invalid_gst'] > 0:
                    messages.info(request, f'⚠️ Skipped {stats["skipped_invalid_gst"]} rows with invalid GST format')
                if stats['skipped_no_client'] > 0:
                    messages.warning(request, f'❌ Skipped {stats["skipped_no_client"]} rows - no matching client found')
                if stats['skipped_multiple_clients'] > 0:
                    messages.warning(request,
                                     f'❌ Skipped {stats["skipped_multiple_clients"]} rows - multiple clients found')
                if stats['skipped_duplicate_gst'] > 0:
                    messages.info(request, f'ℹ️ Skipped {stats["skipped_duplicate_gst"]} rows - GST already exists')
                if stats['skipped_invalid_scheme'] > 0:
                    messages.info(request,
                                  f'⚠️ Skipped {stats["skipped_invalid_scheme"]} rows - invalid GST scheme type')
                if stats['skipped_invalid_status'] > 0:
                    messages.info(request, f'⚠️ Skipped {stats["skipped_invalid_status"]} rows - invalid status')

                return redirect('..')

            except Exception as e:
                messages.error(request, f'Error processing Excel file: {str(e)}')
                return redirect('..')

        # GET request - show upload form
        context = {
            'title': 'Import GST Details',
            'site_title': self.admin_site.site_title,
            'site_header': self.admin_site.site_header,
            'has_permission': True,
        }
        return render(request, 'admin/gst_import_form.html', context)


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
        "location_name",
        "remark",
    )
    list_filter = ("status", "date")
    list_editable = ("status",)
    search_fields = ("user__username", "location_name")
    actions = ["clock_out_with_shift_time"]

    def clock_out_with_shift_time(self, request, queryset):
        from django.contrib import messages
        from django.utils import timezone
        from django.db.models import Q
        from datetime import datetime

        success_count = 0
        error_count = 0
        errors = []

        for attendance in queryset:
            try:
                employee_shift = EmployeeShift.objects.filter(
                    user=attendance.user,
                    valid_from__lte=attendance.date
                ).filter(
                    Q(valid_to__isnull=True) | Q(valid_to__gte=attendance.date)
                ).first()

                if employee_shift:
                    shift_end_time = employee_shift.shift.shift_end_time
                else:
                    default_shift = Shift.objects.filter(is_default=True).first()
                    if not default_shift:
                        default_shift = Shift.objects.first()
                    if not default_shift:
                        errors.append(f"{attendance.user.username} ({attendance.date}): No shift configured")
                        error_count += 1
                        continue
                    shift_end_time = default_shift.shift_end_time

                attendance.clock_out = timezone.make_aware(datetime.combine(attendance.date, shift_end_time))
                remark_text = f"Clock-out set to shift time by {request.user.username} on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                if attendance.remark:
                    attendance.remark = f"{attendance.remark}; {remark_text}"
                else:
                    attendance.remark = remark_text
                attendance._skip_auto_status = True
                attendance.save()
                success_count += 1
            except Exception as e:
                errors.append(f"{attendance.user.username} ({attendance.date}): {str(e)}")
                error_count += 1

        if success_count > 0:
            messages.success(request, f"Successfully updated {success_count} attendance record(s) with shift clock-out time.")
        if error_count > 0:
            messages.error(request, f"Failed to update {error_count} record(s). Errors: {'; '.join(errors[:5])}")

    clock_out_with_shift_time.short_description = "Clock out with shift time"


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


# notification
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username')


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('shift_name', 'shift_start_time',
                    'shift_end_time', 'maximum_allowed_duration', 'days_off', 'is_default')
    list_editable = ('is_default',)


@admin.register(EmployeeShift)
class EmployeeShiftAdmin(admin.ModelAdmin):
    list_display = ('user', 'shift', 'valid_from', 'valid_to')
    list_filter = ('shift', 'valid_from', 'valid_to')


@admin.register(OfficeDetails)
class OfficeDetailsAdmin(admin.ModelAdmin):
    list_display = ('office_name', 'contact_person_name',
                    'office_contact_no', 'latitude', 'longitude')
    # search_fields = ('office_name', 'contact_person_name')


@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "leave_type",
        "status",
        "start_date",
        "end_date",
    )
    list_filter = ("status", "leave_type")
    actions = ["approve_leave", "reject_leave"]

    def approve_leave(self, request, queryset):
        queryset.exclude(status="approved").update(status="approved")

    def reject_leave(self, request, queryset):
        queryset.update(status="rejected")


from .models import Client, Product, Invoice, InvoiceItem, Payment


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'short_code', 'unit', 'hsn_code')
    search_fields = ('item_name', 'short_code', 'hsn_code')
    list_filter = ('unit',)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    # These fields are auto-calculated, so we make them read-only in UI
    readonly_fields = ('taxable_value', 'net_total')
    fields = ('product', 'unit_cost', 'discount', 'taxable_value', 'gst_percentage', 'net_total')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'subject', 'invoice_date', 'due_date', 'invoice_status')
    list_filter = ('invoice_date', 'due_date', 'client', 'invoice_status')
    search_fields = ('subject', 'client__client_name', 'id')
    inlines = [InvoiceItemInline]
    filter_horizontal = ('services',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
    'invoice', 'amount', 'payment_method', 'payment_date', 'created_by', 'payment_status', 'approval_status')
    list_filter = ('payment_method', 'payment_date', 'payment_status', 'approval_status')
    search_fields = ('invoice__id', 'transaction_id')
    readonly_fields = ('created_at', 'created_by')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Superusers see everything
        if request.user.is_superuser:
            return qs
        # If the user has an Employee profile, limit to their branch.
        try:
            office = request.user.employee.office_location
        except Exception:
            return qs.none()

        # Return payments created by users in the same office
        return qs.filter(created_by__employee__office_location=office)

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'status', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('content', 'sender__username', 'receiver__username')
    ordering = ('-timestamp',)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        'lead_name',
        'full_name',
        'phone_number',
        'email',
        'status',
        'lead_value',
        'expected_closure_date',
        'created_by',
        'created_at',
    )
    list_filter = (
        'status',
        'created_at',
        'expected_closure_date',
        'created_by',
    )
    search_fields = (
        'lead_name',
        'full_name',
        'phone_number',
        'email',
        'requirements',
    )
    date_hierarchy = 'created_at'
    autocomplete_fields = ('created_by', 'assigned_to', 'client')
    filter_horizontal = ('assigned_to',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('lead_name', 'full_name', 'email', 'phone_number', 'requirements')
        }),
        ('Value & Dates', {
            'fields': ('lead_value', 'expected_closure_date', 'actual_closure_date')
        }),
        ('Status & Assignment', {
            'fields': ('status', 'remarks', 'assigned_to', 'created_by')
        }),
        ('Conversion', {
            'fields': ('client',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        """Filter leads based on user role"""
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        try:
            employee = request.user.employee
            role = employee.role

            if role == 'ADMIN':
                return qs
            elif role == 'BRANCH_MANAGER':
                office = employee.office_location
                if office:
                    from django.db.models import Q
                    return qs.filter(
                        Q(created_by__employee__office_location=office) |
                        Q(assigned_to=request.user) |
                        Q(created_by=request.user)
                    ).distinct()
                else:
                    from django.db.models import Q
                    return qs.filter(
                        Q(assigned_to=request.user) |
                        Q(created_by=request.user)
                    ).distinct()
            else:
                # Staff can see leads assigned to them OR created by them
                from django.db.models import Q
                return qs.filter(
                    Q(assigned_to=request.user) |
                    Q(created_by=request.user)
                ).distinct()
        except:
            from django.db.models import Q
            return qs.filter(
                Q(assigned_to=request.user) |
                Q(created_by=request.user)
            ).distinct()


@admin.register(LeadCallLog)
class LeadCallLogAdmin(admin.ModelAdmin):
    list_display = (
        'lead',
        'get_direction',
        'get_employee',
        'call_duration',
        'created_at',
        'created_by',
    )
    list_filter = (
        'created_at',
        'created_by',
        'lead__status',
    )
    search_fields = (
        'lead__lead_name',
        'lead__full_name',
        'lead__phone_number',
        'called_by_user__username',
        'called_by_user__first_name',
        'called_by_user__last_name',
        'called_to_user__username',
        'called_to_user__first_name',
        'called_to_user__last_name',
        'description',
    )
    date_hierarchy = 'created_at'
    autocomplete_fields = ('lead', 'called_by_user', 'called_to_user', 'created_by')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Call Information', {
            'fields': ('lead', 'called_by_user', 'called_to_user', 'call_duration')
        }),
        ('Discussion Details', {
            'fields': ('description',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at'),
        }),
    )

    def get_direction(self, obj):
        return obj.get_direction_display()
    get_direction.short_description = 'Direction'

    def get_employee(self, obj):
        employee = obj.get_employee()
        if employee:
            return employee.get_full_name() or employee.username
        return '-'
    get_employee.short_description = 'Employee'

    def get_queryset(self, request):
        """Filter call logs based on user role - same as Lead access"""
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        try:
            employee = request.user.employee
            role = employee.role

            if role == 'ADMIN':
                return qs
            elif role == 'BRANCH_MANAGER':
                office = employee.office_location
                if office:
                    from django.db.models import Q
                    return qs.filter(
                        Q(lead__created_by__employee__office_location=office) |
                        Q(lead__assigned_to=request.user) |
                        Q(lead__created_by=request.user)
                    ).distinct()
                else:
                    from django.db.models import Q
                    return qs.filter(
                        Q(lead__assigned_to=request.user) |
                        Q(lead__created_by=request.user)
                    ).distinct()
            else:
                # Staff can see call logs for leads assigned to them OR created by them
                from django.db.models import Q
                return qs.filter(
                    Q(lead__assigned_to=request.user) |
                    Q(lead__created_by=request.user)
                ).distinct()
        except:
            from django.db.models import Q
            return qs.filter(
                Q(lead__assigned_to=request.user) |
                Q(lead__created_by=request.user)
            ).distinct()