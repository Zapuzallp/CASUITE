from django.contrib import admin
from .models import (
    Client, CompanyDetails, LLPDetails, OPCDetails, Section8CompanyDetails, HUFDetails,
    ServiceType, ClientService, GSTDetails, ITRDetails, AuditDetails,
    Task, TaskActivityLog, IncomeTaxCaseDetails, GSTCaseDetails,
    ClientUserEntitle, DocumentMaster, DocumentRequest, RequestedDocument, ClientDocumentUpload
)

admin.site.site_header = 'CA Suite 2.0 Admin'
admin.site.site_title = 'CA Suite 2.0'
admin.site.index_title = 'Welcome to CA Suite 2.0 Admin'


# -------------------------
# Client Base Admin
# -------------------------
class DocumentRequestInline(admin.TabularInline):
    model = DocumentRequest
    readonly_fields = ('created_at', 'created_by')
    extra = 0
    fields = ('title', 'due_date', 'created_by', 'created_at')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['client_name', 'primary_contact_name', 'pan_no', 'email', 'phone_number', 'client_type',
                    'business_structure', 'status', 'assigned_ca', 'date_of_engagement']
    list_filter = ['client_type', 'business_structure', 'status', 'assigned_ca', 'state', 'country']
    search_fields = ['client_name', 'primary_contact_name', 'pan_no', 'email', 'phone_number']
    list_editable = ['status', 'assigned_ca']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [DocumentRequestInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('client_name', 'primary_contact_name', 'pan_no', 'email', 'phone_number', 'aadhar', 'din_no')
        }),
        ('Address', {
            'fields': ('address_line1', 'city', 'state', 'postal_code', 'country')
        }),
        ('Business Details', {
            'fields': ('client_type', 'business_structure', 'status', 'assigned_ca', 'date_of_engagement')
        }),
        ('Additional Information', {
            'fields': ('remarks',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


# -------------------------
# Entity-Specific Details Admin
# -------------------------
@admin.register(CompanyDetails)
class CompanyDetailsAdmin(admin.ModelAdmin):
    list_display = ['proposed_company_name', 'client', 'company_type', 'cin', 'authorised_share_capital',
                    'paid_up_share_capital', 'number_of_directors', 'date_of_incorporation']
    list_filter = ['company_type', 'date_of_incorporation']
    search_fields = ['proposed_company_name', 'client__client_name', 'cin']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['directors']


@admin.register(LLPDetails)
class LLPDetailsAdmin(admin.ModelAdmin):
    list_display = ['llp_name', 'client', 'llp_registration_no', 'paid_up_capital_llp', 'date_of_registration_llp']
    list_filter = ['date_of_registration_llp']
    search_fields = ['llp_name', 'client__client_name', 'llp_registration_no']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['designated_partners']


@admin.register(OPCDetails)
class OPCDetailsAdmin(admin.ModelAdmin):
    list_display = ['opc_name', 'client', 'opc_cin', 'sole_member_name', 'paid_up_share_capital_opc',
                    'date_of_incorporation_opc']
    list_filter = ['date_of_incorporation_opc']
    search_fields = ['opc_name', 'client__client_name', 'opc_cin']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Section8CompanyDetails)
class Section8CompanyDetailsAdmin(admin.ModelAdmin):
    list_display = ['section8_company_name', 'client', 'registration_no_section8', 'whether_licence_obtained',
                    'date_of_registration_s8']
    list_filter = ['whether_licence_obtained', 'date_of_registration_s8']
    search_fields = ['section8_company_name', 'client__client_name', 'registration_no_section8']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(HUFDetails)
class HUFDetailsAdmin(admin.ModelAdmin):
    list_display = ['huf_name', 'client', 'pan_huf', 'karta_name', 'number_of_coparceners', 'number_of_members',
                    'date_of_creation']
    list_filter = ['date_of_creation']
    search_fields = ['huf_name', 'client__client_name', 'pan_huf', 'karta_name__client_name']
    readonly_fields = ['created_at', 'updated_at']


# -------------------------
# Service Master Admin
# -------------------------
@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ['service_name', 'category', 'frequency', 'default_due_days', 'active']
    list_filter = ['category', 'frequency', 'active']
    search_fields = ['service_name', 'description']
    list_editable = ['active']
    readonly_fields = ['created_at']


@admin.register(ClientService)
class ClientServiceAdmin(admin.ModelAdmin):
    list_display = ['client', 'service', 'start_date', 'end_date', 'billing_cycle', 'agreed_fee', 'is_active']
    list_filter = ['service__category', 'billing_cycle', 'is_active', 'start_date']
    search_fields = ['client__client_name', 'service__service_name']
    list_editable = ['is_active']
    readonly_fields = ['created_at']


# -------------------------
# Financial & Compliance Admin
# -------------------------
@admin.register(GSTDetails)
class GSTDetailsAdmin(admin.ModelAdmin):
    list_display = ['gst_number', 'client_service', 'type_of_registration', 'filing_frequency', 'state_code',
                    'date_of_registration']
    list_filter = ['type_of_registration', 'filing_frequency', 'state_code', 'date_of_registration']
    search_fields = ['gst_number', 'client_service__client__client_name', 'gst_username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ITRDetails)
class ITRDetailsAdmin(admin.ModelAdmin):
    list_display = ['pan_number', 'client_service', 'itr_type', 'assessment_year', 'income_source', 'filing_mode']
    list_filter = ['itr_type', 'assessment_year', 'filing_mode']
    search_fields = ['pan_number', 'client_service__client__client_name', 'aadhaar_number', 'last_itr_ack_no']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AuditDetails)
class AuditDetailsAdmin(admin.ModelAdmin):
    list_display = ['client_service', 'audit_type', 'financial_year', 'auditor_name', 'audit_start_date',
                    'audit_end_date']
    list_filter = ['audit_type', 'financial_year', 'audit_start_date']
    search_fields = ['client_service__client__client_name', 'auditor_name', 'financial_year']
    readonly_fields = ['created_at', 'updated_at']


# -------------------------
# Tasks & Activities Admin
# -------------------------
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['task_title', 'client_service', 'due_date', 'assigned_to', 'task_status', 'recurrence',
                    'completion_date']
    list_filter = ['task_status', 'recurrence', 'due_date', 'assigned_to']
    search_fields = ['task_title', 'client_service__client__client_name', 'assigned_to__username']
    list_editable = ['task_status', 'assigned_to']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'due_date'


@admin.register(TaskActivityLog)
class TaskActivityLogAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'action', 'created_at']
    list_filter = ['action', 'created_at', 'user']
    search_fields = ['task__task_title', 'user__username', 'action']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


# -------------------------
# Legal Cases Admin
# -------------------------
@admin.register(IncomeTaxCaseDetails)
class IncomeTaxCaseDetailsAdmin(admin.ModelAdmin):
    list_display = ['client_service', 'case_type', 'notice_number', 'notice_date', 'ao_name', 'status',
                    'next_hearing_date']
    list_filter = ['case_type', 'status', 'notice_date', 'last_hearing_date', 'next_hearing_date']
    search_fields = ['client_service__client__client_name', 'notice_number', 'ao_name', 'ward_circle']
    list_editable = ['status']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'notice_date'


@admin.register(GSTCaseDetails)
class GSTCaseDetailsAdmin(admin.ModelAdmin):
    list_display = ['client_service', 'case_type', 'gstin', 'case_number', 'date_of_notice', 'officer_name', 'status']
    list_filter = ['case_type', 'status', 'date_of_notice', 'jurisdiction']
    search_fields = ['client_service__client__client_name', 'gstin', 'case_number', 'officer_name']
    list_editable = ['status']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date_of_notice'


class RequestedDocumentInline(admin.TabularInline):
    model = RequestedDocument
    extra = 1


class ClientDocumentUploadInline(admin.TabularInline):
    model = ClientDocumentUpload
    readonly_fields = ('upload_date', 'client', 'status', 'uploaded_by')
    extra = 0

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('client', 'uploaded_by')


@admin.register(DocumentMaster)
class DocumentMasterAdmin(admin.ModelAdmin):
    list_display = ('document_name', 'category', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('document_name', 'category')


# -------------------------
# Client User Entitle Admin
# -------------------------
@admin.register(ClientUserEntitle)
class ClientUserEntitleAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_client_count', 'get_client_names', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'clients__client_name']
    filter_horizontal = ['clients']
    readonly_fields = ['created_at', 'updated_at']

    def get_client_count(self, obj):
        return obj.clients.count()

    get_client_count.short_description = 'Number of Clients'

    def get_client_names(self, obj):
        clients = obj.clients.all()[:3]
        names = [client.client_name for client in clients]
        if obj.clients.count() > 3:
            names.append(f"and {obj.clients.count() - 3} more...")
        return ", ".join(names) if names else "No clients assigned"

    get_client_names.short_description = 'Assigned Clients'


@admin.register(DocumentRequest)
class DocumentRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'due_date', 'created_by', 'created_at')
    list_filter = ('due_date', 'created_by', 'client__client_type', 'client__status')
    search_fields = ('title', 'client__client_name', 'client__email', 'client__pan_no')
    inlines = (RequestedDocumentInline,)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "client":
            kwargs["queryset"] = Client.objects.select_related().order_by('client_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(RequestedDocument)
class RequestedDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_request', 'document_master')
    search_fields = ('document_master__document_name', 'document_request__title')
    inlines = (ClientDocumentUploadInline,)


@admin.register(ClientDocumentUpload)
class ClientDocumentUploadAdmin(admin.ModelAdmin):
    list_display = ('client', 'requested_document', 'status', 'upload_date', 'uploaded_by')
    list_filter = ('status', 'upload_date', 'uploaded_by', 'client__client_type')
    search_fields = (
        'client__client_name',
        'client__email',
        'client__pan_no',
        'uploaded_by__username',
        'requested_document__document_master__document_name',
    )
    readonly_fields = ('upload_date', 'status')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "client":
            kwargs["queryset"] = Client.objects.select_related().order_by('client_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
