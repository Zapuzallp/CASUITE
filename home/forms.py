import re

from django import forms
from django.contrib.auth.models import User

from home.clients.config import STRUCTURE_CONFIG, REQUIRED_FIELDS_MAP
from .models import (
    Task,
    ClientDocumentUpload, RequestedDocument, DocumentMaster, DocumentRequest, TaskExtendedAttributes, Message, Invoice,
    InvoiceItem, GSTDetails
    # Added GSTDetails to imports
)
from home.models import Leave
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Payment, Invoice, Lead
from .models import Payment
from django.utils import timezone


class DocumentRequestForm(forms.ModelForm):
    # Explicitly define the multi-select widget
    documents = forms.ModelMultipleChoiceField(
        queryset=DocumentMaster.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'style': 'height: 150px;'}),
        # Added height for visibility
        label="Select Documents to Collect",
        help_text="Hold Ctrl (Windows) or Cmd (Mac) to select multiple."
    )

    class Meta:
        model = DocumentRequest
        fields = ['title', 'due_date', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., FY 2023-24 Tax Documents'}),
            # 'type': 'date' ensures a date picker appears
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Instructions for client...'})
        }


class DocumentUploadForm(forms.ModelForm):
    # We will filter this queryset dynamically in the view based on the client
    requested_document = forms.ModelChoiceField(
        queryset=RequestedDocument.objects.none(),
        label="Select Document Type",
        empty_label="-- Select Document Request --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = ClientDocumentUpload
        fields = ['requested_document', 'uploaded_file', 'remarks']
        widgets = {
            'uploaded_file': forms.FileInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes...'})
        }

    def __init__(self, client_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter: Only show pending document requests for THIS client
        if client_id:
            self.fields['requested_document'].queryset = RequestedDocument.objects.filter(
                document_request__client_id=client_id
            ).select_related('document_master', 'document_request')

            # Custom label for the dropdown options
            self.fields['requested_document'].label_from_instance = lambda obj: \
                f"{obj.document_master.document_name} (Due: {obj.document_request.due_date})"


from django import forms
from .models import Client, ClientBusinessProfile


# ---------------------------------------------------------
# Helper: Bootstrap Styling Mixin
# ---------------------------------------------------------
class BootstrapFormMixin:
    """
    Automatically applies Bootstrap 5 classes to all form fields.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(widget, forms.Select):
                widget.attrs.update({'class': 'form-select'})
            elif isinstance(widget, forms.SelectMultiple):
                widget.attrs.update({'class': 'form-select', 'size': '4'})
            else:
                widget.attrs.update({'class': 'form-control'})


# ---------------------------------------------------------
# Helper: Config Regex Validator
# ---------------------------------------------------------
def validate_against_config(form, structure_key):
    """
    Validates form fields based on the 'validation' key in STRUCTURE_CONFIG.
    Checks regex patterns defined in config.py.
    """
    if not structure_key or structure_key not in STRUCTURE_CONFIG:
        return

    config = STRUCTURE_CONFIG[structure_key]
    validation_rules = config.get('validation', {})
    cleaned_data = form.cleaned_data

    for field_name, rules in validation_rules.items():
        # Only validate if field exists in this specific form and has a value
        if field_name in cleaned_data:
            value = cleaned_data.get(field_name)

            if value:
                pattern = rules.get('regex')
                error_msg = rules.get('message', 'Invalid format.')

                # Check Regex Match
                if pattern and not re.match(pattern, str(value)):
                    form.add_error(field_name, error_msg)


# ---------------------------------------------------------
# 1. Client Basic Information Form
# ---------------------------------------------------------
# ---------------------------------------------------------
# Helper: Config Validator
# ---------------------------------------------------------
def validate_against_config(form, structure_key):
    if not structure_key or structure_key not in STRUCTURE_CONFIG:
        return

    config = STRUCTURE_CONFIG[structure_key]
    validation_rules = config.get('validation', {})
    cleaned_data = form.cleaned_data

    for field_name, rules in validation_rules.items():
        if field_name in cleaned_data:
            value = cleaned_data.get(field_name)

            if value:
                # FIX 1: Convert to string and UPPERCASE before validating
                # This ensures 'abcde...' is validated as 'ABCDE...'
                value_str = str(value).upper()

                pattern = rules.get('regex')
                error_msg = rules.get('message', 'Invalid format.')

                if pattern and not re.match(pattern, value_str):
                    form.add_error(field_name, error_msg)

                # OPTIONAL: Save the uppercased version back to cleaned_data
                cleaned_data[field_name] = value_str


# ---------------------------------------------------------
# 1. Client Basic Form
# ---------------------------------------------------------
class ClientForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Client
        exclude = ['created_by', 'created_at', 'updated_at', 'status', 'file_number']
        widgets = {
            'assigned_ca': forms.Select(
                attrs={
                    'class': 'form-control select2'
                }
            ),
            'date_of_engagement': forms.DateInput(attrs={'type': 'date'}),
            'address_line1': forms.Textarea(attrs={'rows': 2}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['office_location'].required = True

    def clean(self):
        cleaned_data = super().clean()

        structure = cleaned_data.get('business_structure')
        client_type = cleaned_data.get('client_type')

        # FIX 2: Determine the correct Config Key
        # If structure is empty (e.g. Individual), fallback to 'Individual' config
        config_key = None
        if structure:
            config_key = structure
        elif client_type == 'Individual':
            config_key = 'Individual'

        # Run validation if we found a key
        if config_key:
            validate_against_config(self, config_key)

        return cleaned_data


# ---------------------------------------------------------
# 2. Entity Profile Form
# ---------------------------------------------------------
class ClientBusinessProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ClientBusinessProfile
        exclude = ['client']
        widgets = {
            'date_of_incorporation': forms.DateInput(attrs={'type': 'date'}),
            'registered_office_address': forms.Textarea(attrs={'rows': 2}),
            'object_clause': forms.Textarea(attrs={'rows': 2}),
            'key_persons': forms.SelectMultiple(),
        }

    def clean(self):
        cleaned_data = super().clean()

        # Access 'business_structure' from the POST data directly
        # (since it belongs to the ClientForm, not this form)
        structure = self.data.get('business_structure')

        if structure:
            # 1. Check Required Fields based on Config
            if structure in REQUIRED_FIELDS_MAP:
                for field_name in REQUIRED_FIELDS_MAP[structure]:
                    value = cleaned_data.get(field_name)
                    # Check if empty (handles None, '', [], etc.)
                    if not value:
                        # Get human readable label
                        field_obj = self.fields.get(field_name)
                        label = field_obj.label if field_obj else field_name
                        self.add_error(field_name, f"{label} is required for {structure}.")

            # 2. Check Regex Validation based on Config
            validate_against_config(self, structure)

        return cleaned_data


# ---------------------------------------------------------
# 1. Base Task Form (Core Details)
# ---------------------------------------------------------
class TaskForm(BootstrapFormMixin, forms.ModelForm):
    # Explicitly define assignees to ensure we only get active users
    assignees = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={'style': 'height: 100px;'}),  # Taller box for multiple selection
        required=False,
        label="Assign Team Members",
        help_text="Hold Ctrl (Windows) or Cmd (Mac) to select multiple users."
    )

    class Meta:
        model = Task
        # CHANGED: 'assigned_to' -> 'assignees'
        fields = ['service_type', 'task_title', 'due_date', 'priority', 'assignees', 'description', 'recurrence_period',
                  'consultancy_type']
        widgets = {
            'task_title': forms.TextInput(attrs={'placeholder': 'Auto-generated if left blank'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'consultancy_type': forms.Select(attrs={'class': 'form-select'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Sort consultancy_type choices alphabetically by label
        self.fields['consultancy_type'].choices = sorted(
            self.fields['consultancy_type'].choices,
            key=lambda x: x[1].lower()
        )


# ---------------------------------------------------------
# 2. Extended Attributes Form (The Superset)
# ---------------------------------------------------------
class TaskExtendedForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TaskExtendedAttributes
        exclude = ['task']
        widgets = {
            # --- Dropdowns ---
            'period_month': forms.Select(choices=[
                ('January', 'January'), ('February', 'February'), ('March', 'March'),
                ('April', 'April'), ('May', 'May'), ('June', 'June'),
                ('July', 'July'), ('August', 'August'), ('September', 'September'),
                ('October', 'October'), ('November', 'November'), ('December', 'December')
            ]),

            # --- Date Pickers ---
            'filing_date': forms.DateInput(attrs={'type': 'date'}),
            'date_of_signing': forms.DateInput(attrs={'type': 'date'}),
            'meeting_date': forms.DateInput(attrs={'type': 'date'}),

            # --- Text Areas ---
            'remarks': forms.Textarea(attrs={'rows': 3}),
            'din_numbers': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Enter DINs separated by commas'}),

            # --- File Inputs ---
            'json_file': forms.FileInput(),
            'computation_file': forms.FileInput(),
            'ack_file': forms.FileInput(),
            'audit_report_file': forms.FileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['total_turnover'].widget.attrs.update({'placeholder': '0.00'})
        self.fields['tax_payable'].widget.attrs.update({'placeholder': '0.00'})


# Leave form
class LeaveForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['leave_type', 'reason', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        leave_summary = kwargs.pop("leave_summary", None)
        super().__init__(*args, **kwargs)

        if leave_summary:
            updated_choices = []
            for value, label in self.fields["leave_type"].choices:
                if value == "" or value is None:

                    updated_choices.append(
                        (value, label))
                else:
                    remaining = leave_summary.get(value, {}).get("remaining", 0)
                    if remaining == 0:
                        display_text = f"{label} (-)"
                    else:
                        display_text = f"{label} ({remaining})"
                        updated_choices.append((value, display_text))

            self.fields["leave_type"].choices = updated_choices

    def clean(self):
        """Validate dates"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            # Check if end date is before start date
            if end_date < start_date:
                raise forms.ValidationError(
                    "End date cannot be before start date."
                )

            # Check if dates are in the past
            from datetime import date
            if start_date < date.today():
                raise forms.ValidationError(
                    "Cannot apply for leaves in the past."
                )

        return cleaned_data


# Message form
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content', 'status']
        widgets = {
            'content': forms.Textarea(attrs={
                'id': 'summernote',  # Required for JS initialization
                'class': 'form-control',
            }),
            'status': forms.Select(attrs={'class': 'form-control', 'style': 'width: auto; display: inline-block;'}),
        }


# Invoice Form
class InvoiceForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['client', 'services', 'invoice_date', 'due_date', 'subject']
        widgets = {
            'invoice_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            "client": forms.Select(attrs={
                "class": "form-control",
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Default:no tasks
        self.fields['services'].queryset = Task.objects.none()

        if 'client' in self.data:
            client_id = self.data.get('client')
            self.fields['services'].queryset = Task.objects.filter(
                client_id=client_id,
                tagged_invoices__isnull=True
            )
        else:
            self.fields['services'].queryset = Task.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        invoice_date = cleaned_data.get('invoice_date')
        due_date = cleaned_data.get('due_date')

        if invoice_date and due_date:
            # invoice_date is DateTimeField, due_date is DateField
            if due_date < invoice_date.date():
                self.add_error(
                    'due_date',
                    'Due date cannot be earlier than invoice date.'
                )

        return cleaned_data


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['product', 'unit_cost', 'discount', 'gst_percentage', ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'unit_cost': forms.NumberInput(attrs={'class': "form-control"}),
            'discount': forms.NumberInput(attrs={'class': "form-control"}),
            'gst_percentage': forms.Select(attrs={'class': "form-select"}),
        }


# ---------------------------------------------------------
# Dedicated PaymentForm And PaymentCollectForm
# ---------------------------------------------------------
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['payment_method', 'amount', 'payment_date', 'transaction_id']
        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_amount(self):
        amt = self.cleaned_data.get('amount')
        if amt is None:
            raise forms.ValidationError("Amount is required.")
        dec_amt = Decimal(str(amt))
        if dec_amt <= Decimal('0.00'):
            raise forms.ValidationError("Amount must be greater than zero.")
        return dec_amt

    def clean_payment_date(self):
        payment_date = self.cleaned_data.get('payment_date')
        if not payment_date:
            return payment_date
        today = timezone.localdate()
        if payment_date > today:
            raise forms.ValidationError("Payment date cannot be in the future.")
        return payment_date


class PaymentCollectForm(PaymentForm):
    invoice = forms.ModelChoiceField(
        queryset=Invoice.objects.select_related('client').order_by('-id'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta(PaymentForm.Meta):
        fields = ['invoice'] + PaymentForm.Meta.fields

    def __init__(self, *args, invoice_instance=None, balance_amount=None, **kwargs):
        """
        invoice_instance: if provided, lock the invoice (hide the field and set initial)
        """
        super().__init__(*args, **kwargs)
        self.invoice_instance = invoice_instance
        self.balance_amount = balance_amount

        if invoice_instance:
            self.fields['invoice'].initial = invoice_instance
            self.fields['invoice'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()

        amount = cleaned_data.get('amount')
        invoice = self.invoice_instance or cleaned_data.get('invoice')

        if not amount or not invoice:
            return cleaned_data

        balance = self.balance_amount

        if balance is not None and amount > balance:
            self.add_error('amount', 'Amount cannot be greater than remaining balance.')

        return cleaned_data


# ---------------------------------------------------------
# 3. GST Details Form (NEW)
# ---------------------------------------------------------
class GSTDetailsForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = GSTDetails
        fields = ['gst_number', 'registered_address', 'state', 'gst_scheme_type', 'status']
        widgets = {
            'registered_address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gst_number'].widget.attrs.update({'placeholder': 'e.g., 29ABCDE1234F1Z5'})


# ---------------------------------------------------------
# 4. Lead Form
# ---------------------------------------------------------
class LeadForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Lead
        fields = [
            'lead_name', 'full_name', 'email', 'phone_number',
            'requirements', 'lead_value', 'expected_closure_date'
        ]
        widgets = {
            'lead_name': forms.TextInput(attrs={
                'placeholder': 'e.g., ABC Traders',
                'required': 'required'
            }),
            'full_name': forms.TextInput(attrs={
                'placeholder': 'e.g., Rajesh Kumar',
                'required': 'required'
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'e.g., rajesh@example.com',
                'type': 'email'
            }),
            'phone_number': forms.TextInput(attrs={
                'placeholder': 'e.g., 9876543210',
                'pattern': '[0-9]{10}',
                'title': 'Please enter a valid 10-digit phone number',
                'required': 'required'
            }),
            'requirements': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe the lead requirements...',
                'required': 'required'
            }),
            'lead_value': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
                'required': 'required'
            }),
            'expected_closure_date': forms.DateInput(attrs={'type': 'date', 'required': 'required'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set required fields
        self.fields['lead_name'].required = True
        self.fields['full_name'].required = True
        self.fields['phone_number'].required = True
        self.fields['requirements'].required = True
        self.fields['email'].required = False
        self.fields['lead_value'].required = True
        self.fields['expected_closure_date'].required = True

    def clean_phone_number(self):
        """Validate phone number - must be 10 digits"""
        phone = self.cleaned_data.get('phone_number', '').strip()

        # Remove any spaces or dashes
        phone = phone.replace(' ', '').replace('-', '')

        # Check if it contains only digits
        if not phone.isdigit():
            raise forms.ValidationError('Phone number must contain only digits.')

        # Check if it's exactly 10 digits
        if len(phone) != 10:
            raise forms.ValidationError('Phone number must be exactly 10 digits.')

        return phone

    def clean_lead_value(self):
        """Validate lead value - must not be negative"""
        value = self.cleaned_data.get('lead_value')

        if value is not None and value < 0:
            raise forms.ValidationError('Lead value cannot be negative.')

        return value


# ---------------------------------------------------------
# 5. Client Portal Credentials Form
# ---------------------------------------------------------
from home.models import ClientPortalCredentials, Dropdown


class ClientPortalCredentialsForm(BootstrapFormMixin, forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter client portal password'
        }),
        help_text="Password will be encrypted before storage",
        required=True
    )

    class Meta:
        model = ClientPortalCredentials
        fields = ['dropdown', 'portal_url', 'username', 'password']
        widgets = {
            'dropdown': forms.Select(attrs={'class': 'form-select'}),
            'portal_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter client username for this portal'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.client = kwargs.pop('client', None)
        super().__init__(*args, **kwargs)
        # Only show active password-type dropdowns
        self.fields['dropdown'].queryset = Dropdown.objects.filter(
            type='password',
            is_active=True
        )
        self.fields['dropdown'].label = "Portal Type"

        # Ensure fields start blank (no initial values)
        if not self.instance.pk:
            self.fields['username'].initial = ''
            self.fields['password'].initial = ''

        # If editing existing credential, show masked password
        if self.instance and self.instance.pk:
            self.fields['password'].required = False
            self.fields['password'].help_text = "Leave blank to keep current password"

    def clean(self):
        cleaned_data = super().clean()
        dropdown = cleaned_data.get('dropdown')

        # Check for duplicate portal type for this client
        if self.client and dropdown:
            # Exclude current instance if editing
            existing = ClientPortalCredentials.objects.filter(
                client=self.client,
                dropdown=dropdown
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise forms.ValidationError(
                    f"A credential for '{dropdown.label}' already exists for this client. "
                    f"Please update the existing credential or choose a different portal type."
                )

        return cleaned_data