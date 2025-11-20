from django.contrib import admin

from .models import DocumentMaster, DocumentRequest, RequestedDocument, ClientDocumentUpload, Client, PrivateLimitedDetails, ITRDetails, ClientService, ServiceType, GSTDetails, AuditDetails, LLPDetails, OPCDetails

admin.site.site_header = 'CA Suite 2.0 Admin'
admin.site.site_title = 'CA Suite 2.0'
admin.site.index_title = 'Welcome to CA Suite 2.0 Admin'


class RequestedDocumentInline(admin.TabularInline):
    model = RequestedDocument
    extra = 1


class ClientDocumentUploadInline(admin.TabularInline):
    model = ClientDocumentUpload
    readonly_fields = ('upload_date', 'client', 'status')
    extra = 0


@admin.register(DocumentMaster)
class DocumentMasterAdmin(admin.ModelAdmin):
    list_display = ('document_name', 'category', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('document_name', 'category')


@admin.register(DocumentRequest)
class DocumentRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'due_date', 'created_by', 'created_at')
    list_filter = ('due_date', 'created_by')
    search_fields = ('title', 'client__username', 'client__email')
    inlines = (RequestedDocumentInline,)


@admin.register(RequestedDocument)
class RequestedDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_request', 'document_master')
    search_fields = ('document_master__document_name', 'document_request__title')
    inlines = (ClientDocumentUploadInline,)


@admin.register(ClientDocumentUpload)
class ClientDocumentUploadAdmin(admin.ModelAdmin):
    list_display = ('client', 'requested_document', 'status', 'upload_date')
    list_filter = ('status', 'upload_date')
    search_fields = (
        'client__username',
        'client__email',
        'requested_document__document_master__document_name',
    )


admin.site.register(Client)
admin.site.register(PrivateLimitedDetails)
admin.site.register(ClientService)
admin.site.register(ITRDetails)
admin.site.register(ServiceType)
admin.site.register(AuditDetails)
admin.site.register(GSTDetails)
admin.site.register(LLPDetails)
admin.site.register(OPCDetails)