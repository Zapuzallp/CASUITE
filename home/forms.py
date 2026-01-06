import re

from django import forms
from django.contrib.auth.models import User

from home.clients.config import STRUCTURE_CONFIG, REQUIRED_FIELDS_MAP
from .models import (
    Task,
    ClientDocumentUpload, RequestedDocument, DocumentMaster, DocumentRequest, TaskExtendedAttributes
)
from home.models import Leave


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
        fields = ['service_type', 'task_title', 'due_date', 'priority', 'assignees', 'description','recurrence_period']
        widgets = {
            'task_title': forms.TextInput(attrs={'placeholder': 'Auto-generated if left blank'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }


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

#Leave form
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
                remaining = leave_summary.get(value, {}).get("remaining", 0)
                updated_choices.append(
                    (value, f"{label} ({remaining})")
                )

            self.fields["leave_type"].choices = updated_choices