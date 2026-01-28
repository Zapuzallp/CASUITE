import re
from decimal import Decimal

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from home.clients.config import STRUCTURE_CONFIG, REQUIRED_FIELDS_MAP
from home.models import Leave

from .models import (
    Task,
    Client,
    ClientBusinessProfile,
    ClientDocumentUpload,
    RequestedDocument,
    DocumentMaster,
    DocumentRequest,
    TaskExtendedAttributes,
    Message,
    Payment,
    Invoice,
)

# =========================================================
# Document Request Form
# =========================================================
class DocumentRequestForm(forms.ModelForm):
    documents = forms.ModelMultipleChoiceField(
        queryset=DocumentMaster.objects.filter(is_active=True),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'form-select select2-multiple',
                'data-placeholder': 'Select documents'
            }
        ),
        label="Select Documents to Collect"
    )

    class Meta:
        model = DocumentRequest
        fields = ['title', 'due_date', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# =========================================================
# Document Upload Form
# =========================================================
class DocumentUploadForm(forms.ModelForm):
    requested_document = forms.ModelChoiceField(
        queryset=RequestedDocument.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Select Document Type"
    )

    class Meta:
        model = ClientDocumentUpload
        fields = ['requested_document', 'uploaded_file', 'remarks']
        widgets = {
            'uploaded_file': forms.FileInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, client_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if client_id:
            self.fields['requested_document'].queryset = (
                RequestedDocument.objects
                .filter(document_request__client_id=client_id)
                .select_related('document_master', 'document_request')
            )


# =========================================================
# Bootstrap Mixin
# =========================================================
class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.SelectMultiple):
                widget.attrs.setdefault('class', 'form-select select2-multiple')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')


# =========================================================
# Config Validator
# =========================================================
def validate_against_config(form, structure_key):
    if not structure_key or structure_key not in STRUCTURE_CONFIG:
        return

    rules = STRUCTURE_CONFIG[structure_key].get('validation', {})

    for field_name, rule in rules.items():
        value = form.cleaned_data.get(field_name)
        if value:
            value = str(value).upper()
            if rule.get('regex') and not re.match(rule['regex'], value):
                form.add_error(field_name, rule.get('message', 'Invalid format'))
            form.cleaned_data[field_name] = value


# =========================================================
# Client Basic Form
# =========================================================
class ClientForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Client
        exclude = ['created_by', 'created_at', 'updated_at', 'status', 'file_number']
        widgets = {
            'assigned_ca': forms.Select(attrs={'class': 'form-select select2-single'}),
            'date_of_engagement': forms.DateInput(attrs={'type': 'date'}),
            'address_line1': forms.Textarea(attrs={'rows': 2}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
            'state': forms.Select(attrs={'class': 'form-select'}),

        }

    def clean(self):
        cleaned_data = super().clean()
        structure = cleaned_data.get('business_structure')
        client_type = cleaned_data.get('client_type')

        key = structure or ('Individual' if client_type == 'Individual' else None)
        if key:
            validate_against_config(self, key)

        return cleaned_data


# =========================================================
# Business Profile Form
# =========================================================
class ClientBusinessProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ClientBusinessProfile
        exclude = ['client']
        widgets = {
            'date_of_incorporation': forms.DateInput(attrs={'type': 'date'}),
            'registered_office_address': forms.Textarea(attrs={'rows': 2}),
            'object_clause': forms.Textarea(attrs={'rows': 2}),
            'key_persons': forms.SelectMultiple(
                attrs={
                    'class': 'form-select select2-multiple',
                    'data-placeholder': 'Select key persons'
                }
            ),
        }


# =========================================================
# Task Form
# =========================================================
class TaskForm(BootstrapFormMixin, forms.ModelForm):
    assignees = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'form-select select2-multiple',
                'data-placeholder': 'Assign team members'
            }
        ),
        required=False
    )

    class Meta:
        model = Task
        fields = [
            'service_type', 'task_title', 'due_date',
            'priority', 'assignees', 'description', 'recurrence_period'
        ]
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }


# =========================================================
# Leave Form
# =========================================================
class LeaveForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['leave_type', 'reason', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 5}),
        }


# =========================================================
# Message Form
# =========================================================
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content', 'status']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


# =========================================================
# Payment Forms
# =========================================================
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['payment_method', 'amount', 'payment_date', 'transaction_id']
        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PaymentCollectForm(PaymentForm):
    invoice = forms.ModelChoiceField(
        queryset=Invoice.objects.select_related('client').order_by('-id'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta(PaymentForm.Meta):
        fields = ['invoice'] + PaymentForm.Meta.fields



# =========================================================
# Task Extended Attributes Form
# =========================================================
class TaskExtendedForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TaskExtendedAttributes
        exclude = ['task']
        widgets = {
            'period_month': forms.Select(),
            'filing_date': forms.DateInput(attrs={'type': 'date'}),
            'date_of_signing': forms.DateInput(attrs={'type': 'date'}),
            'meeting_date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
            'din_numbers': forms.Textarea(
                attrs={'rows': 2, 'placeholder': 'Enter DINs separated by commas'}
            ),
            'json_file': forms.FileInput(),
            'computation_file': forms.FileInput(),
            'ack_file': forms.FileInput(),
            'audit_report_file': forms.FileInput(),
        }
    def __init__(self, *args, invoice_instance=None, **kwargs):
        """
        invoice_instance: if provided, lock the invoice (hide the field and set initial)
        """
        super().__init__(*args, **kwargs)
        if invoice_instance:
            # set the initial invoice and hide the field so user can't change it
            self.fields['invoice'].initial = invoice_instance
            self.fields['invoice'].widget = forms.HiddenInput()
            self.invoice_instance = invoice_instance
        else:
            self.invoice_instance = None
