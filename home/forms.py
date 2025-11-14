from django import forms
from .models import Client, CompanyDetails, LLPDetails, OPCDetails, Section8CompanyDetails, HUFDetails, ClientDocumentUpload
from datetime import date
from django.contrib.auth.models import User
import os

class ClientDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = ClientDocumentUpload
        fields = ('uploaded_file', 'remarks')

    def clean_uploaded_file(self):
        f = self.cleaned_data.get('uploaded_file')
        return f


class ClientForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default values
        self.fields['client_type'].initial = 'Individual'
        self.fields['date_of_engagement'].initial = date.today()
        self.fields['status'].initial = 'Active'
        self.fields['pan_no'].widget.attrs['maxlength'] = '10'

        # Make business_structure NOT required by default - FIXED
        self.fields['business_structure'].required = False
        self.fields['business_structure'].widget.attrs.update({'class': 'form-select'})

        if 'assigned_ca' in self.fields:
            self.fields['assigned_ca'].queryset = User.objects.filter(
                is_staff=True,
                is_active=True
            ).order_by('first_name', 'last_name')

        self.fields['assigned_ca'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name}".strip() or obj.username
        # Add Bootstrap classes to all form fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput) or isinstance(field.widget, forms.EmailInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 1})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control'})

            # Add required attribute for mandatory fields (EXCLUDE business_structure)
            if field_name in ['client_name', 'primary_contact_name', 'pan_no', 'email',
                              'phone_number', 'address_line1', 'aadhar', 'city', 'state',
                              'postal_code', 'country', 'date_of_engagement', 'assigned_ca',
                              'client_type', 'status']:
                field.widget.attrs.update({'required': 'required'})
                field.widget.attrs.update({'data-required': 'true'})
                field.label = f'{field.label} <span class="text-danger">*</span>'

    class Meta:
        model = Client
        fields = [
            'client_name',
            'primary_contact_name',
            'pan_no',
            'email',
            'phone_number',
            'address_line1',
            'aadhar',
            'city',
            'state',
            'postal_code',
            'country',
            'date_of_engagement',
            'assigned_ca',
            'client_type',
            'business_structure',
            'status',
            'remarks',
            'din_no'
        ]
        widgets = {
            'date_of_engagement': forms.DateInput(attrs={'type': 'date'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter complete address'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Enter any additional remarks'}),
            'pan_no': forms.TextInput(attrs={'placeholder': 'e.g., ABCDE1234F', 'style': 'text-transform: uppercase'}),
            'aadhar': forms.TextInput(attrs={'placeholder': 'e.g., 1234-5678-9012', 'max_length': '12'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'e.g., 9876543210', 'max_length': '10'}),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter 6-digit postal code',
                'max_length': '6',
                'pattern': '[0-9]{6}',
                'title': 'Postal code must be exactly 6 digits'
            }),
            'business_structure': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        client_type = cleaned_data.get('client_type')
        business_structure = cleaned_data.get('business_structure')

        # Only validate business_structure for Entity clients
        if client_type == 'Entity' and not business_structure:
            self.add_error('business_structure', 'Business structure is required for Entity clients.')

        # Clear business_structure for Individual clients
        if client_type == 'Individual':
            cleaned_data['business_structure'] = None

        return cleaned_data

    def clean_pan_no(self):
        pan_no = self.cleaned_data.get('pan_no', '').upper().strip()
        if not pan_no:
            raise forms.ValidationError("PAN number is required.")
        if len(pan_no) != 10:
            raise forms.ValidationError("PAN number must be exactly 10 characters long.")
        return pan_no

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number', '').strip()
        if not phone_number:
            raise forms.ValidationError("Phone number is required.")
        # Remove any non-digit characters
        phone_digits = ''.join(filter(str.isdigit, phone_number))
        if len(phone_digits) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits long.")
        return phone_number

    def clean_aadhar(self):
        aadhar = self.cleaned_data.get('aadhar', '').strip()
        if not aadhar:
            raise forms.ValidationError("Aadhar number is required.")
        # Remove any non-digit characters
        aadhar_digits = ''.join(filter(str.isdigit, aadhar))
        if len(aadhar_digits) != 12:
            raise forms.ValidationError("Aadhar number must be exactly 12 digits long.")
        return aadhar

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError("Email is required.")
        return email


class CompanyDetailsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit directors queryset to clients with DIN numbers
        self.fields['directors'].queryset = Client.objects.filter(din_no__isnull=False)

        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput) or isinstance(field.widget, forms.EmailInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'date'})
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs.update({
                    'class': 'form-control select2-multiple',
                    'data-placeholder': 'Select directors...'
                })

            if field_name not in ['moa_file', 'aoa_file']:
                field.widget.attrs.update({'required': 'required'})

    def clean_moa_file(self):
        file = self.cleaned_data.get('moa_file')
        if file:
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 10MB")

            valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError(
                    f"Unsupported file extension. Supported formats: {', '.join(valid_extensions)}"
                )
        return file

    def clean_aoa_file(self):
        file = self.cleaned_data.get('aoa_file')
        if file:
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 10MB")

            valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError(
                    f"Unsupported file extension. Supported formats: {', '.join(valid_extensions)}"
                )
        return file

    class Meta:
        model = CompanyDetails
        fields = [
            'company_type',
            'proposed_company_name',
            'cin',
            'authorised_share_capital',
            'paid_up_share_capital',
            'number_of_directors',
            'number_of_shareholders',
            'registered_office_address',
            'date_of_incorporation',
            'udyam_registration',
            'directors',
            'moa_file',
            'aoa_file'
        ]
        widgets = {
            'registered_office_address': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Enter complete registered office address'}),
            'proposed_company_name': forms.TextInput(attrs={'placeholder': 'Enter proposed company name'}),
            'cin': forms.TextInput(attrs={'placeholder': 'Enter Corporate Identification Number'}),
            'authorised_share_capital': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
            'paid_up_share_capital': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
            'date_of_incorporation': forms.DateInput(attrs={'type': 'date'}),
            'udyam_registration': forms.TextInput(attrs={'placeholder': 'Enter Udyam registration number'}),
            'directors': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'moa_file': forms.FileInput(attrs={
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png',
                'class': 'form-control'
            }),
            'aoa_file': forms.FileInput(attrs={
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png',
                'class': 'form-control'
            }),
        }
        error_messages = {
            'company_type': {'required': 'Company type is required.'},
            'proposed_company_name': {'required': 'Proposed company name is required.'},
            'cin': {'required': 'CIN is required.'},
            'authorised_share_capital': {'required': 'Authorised share capital is required.'},
            'paid_up_share_capital': {'required': 'Paid-up share capital is required.'},
            'number_of_directors': {'required': 'Number of directors is required.'},
            'number_of_shareholders': {'required': 'Number of shareholders is required.'},
            'registered_office_address': {'required': 'Registered office address is required.'},
            'date_of_incorporation': {'required': 'Date of incorporation is required.'},
            'udyam_registration': {'required': 'Udyam registration is required.'},
            'directors': {'required': 'Directors are required.'},
        }


class LLPDetailsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit designated_partners queryset to clients with DIN numbers
        self.fields['designated_partners'].queryset = Client.objects.filter(din_no__isnull=False)

        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'date'})
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.SelectMultiple):
                # Add Select2 class for multi-select
                field.widget.attrs.update({
                    'class': 'form-control select2-multiple',
                    'data-placeholder': 'Select designated partners...'
                })

            # Add required attribute for all fields except file
            if field_name not in ['llp_agreement_file']:
                field.widget.attrs.update({'required': 'required'})

    def clean_llp_agreement_file(self):
        file = self.cleaned_data.get('llp_agreement_file')
        if file:
            # Validate file size (10MB limit)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 10MB")

            # Validate file extension
            valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError(
                    f"Unsupported file extension. Supported formats: {', '.join(valid_extensions)}"
                )

        return file

    class Meta:
        model = LLPDetails
        fields = [
            'llp_name',
            'llp_registration_no',
            'registered_office_address_llp',
            'designated_partners',
            'paid_up_capital_llp',
            'date_of_registration_llp',
            'llp_agreement_file'
        ]
        widgets = {
            'registered_office_address_llp': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Enter complete registered office address'}),
            'llp_name': forms.TextInput(attrs={'placeholder': 'Enter LLP name'}),
            'llp_registration_no': forms.TextInput(attrs={'placeholder': 'Enter LLP registration number'}),
            'paid_up_capital_llp': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
            'date_of_registration_llp': forms.DateInput(attrs={'type': 'date'}),
            'designated_partners': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'llp_agreement_file': forms.FileInput(attrs={
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png',
                'class': 'form-control'
            }),
        }
        error_messages = {
            'llp_name': {'required': 'LLP name is required.'},
            'llp_registration_no': {'required': 'LLP registration number is required.'},
            'registered_office_address_llp': {'required': 'Registered office address is required.'},
            'designated_partners': {'required': 'Designated partners are required.'},
            'paid_up_capital_llp': {'required': 'Paid-up capital is required.'},
            'date_of_registration_llp': {'required': 'Date of registration is required.'},
        }


class OPCDetailsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit sole_member_name queryset to appropriate clients
        self.fields['sole_member_name'].queryset = Client.objects.all()

        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'date'})

            # Add required attribute for all fields
            field.widget.attrs.update({'required': 'required'})

    class Meta:
        model = OPCDetails
        fields = [
            'opc_name',
            'opc_cin',
            'registered_office_address_opc',
            'sole_member_name',
            'nominee_member_name',
            'paid_up_share_capital_opc',
            'date_of_incorporation_opc'
        ]
        widgets = {
            'registered_office_address_opc': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Enter complete registered office address'}),
            'opc_name': forms.TextInput(attrs={'placeholder': 'Enter OPC name'}),
            'opc_cin': forms.TextInput(attrs={'placeholder': 'Enter OPC CIN'}),
            'nominee_member_name': forms.TextInput(attrs={'placeholder': 'Enter nominee member name'}),
            'paid_up_share_capital_opc': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
            'date_of_incorporation_opc': forms.DateInput(attrs={'type': 'date'}),
        }
        error_messages = {
            'opc_name': {'required': 'OPC name is required.'},
            'opc_cin': {'required': 'OPC CIN is required.'},
            'registered_office_address_opc': {'required': 'Registered office address is required.'},
            'sole_member_name': {'required': 'Sole member name is required.'},
            'nominee_member_name': {'required': 'Nominee member name is required.'},
            'paid_up_share_capital_opc': {'required': 'Paid-up share capital is required.'},
            'date_of_incorporation_opc': {'required': 'Date of incorporation is required.'},
        }


class Section8CompanyDetailsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'date'})

            # Add required attribute for all fields except checkbox
            if field_name != 'whether_licence_obtained':
                field.widget.attrs.update({'required': 'required'})

    class Meta:
        model = Section8CompanyDetails
        fields = [
            'section8_company_name',
            'registration_no_section8',
            'registered_office_address_s8',
            'object_clause',
            'whether_licence_obtained',
            'date_of_registration_s8'
        ]
        widgets = {
            'registered_office_address_s8': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Enter complete registered office address'}),
            'section8_company_name': forms.TextInput(attrs={'placeholder': 'Enter Section 8 company name'}),
            'registration_no_section8': forms.TextInput(attrs={'placeholder': 'Enter registration number'}),
            'object_clause': forms.Textarea(
                attrs={'rows': 4, 'placeholder': 'Describe the main objectives and purposes of the company'}),
            'date_of_registration_s8': forms.DateInput(attrs={'type': 'date'}),  # This fixes the issue
        }
        error_messages = {
            'section8_company_name': {'required': 'Company name is required.'},
            'registration_no_section8': {'required': 'Registration number is required.'},
            'registered_office_address_s8': {'required': 'Registered office address is required.'},
            'object_clause': {'required': 'Object clause is required.'},
            'date_of_registration_s8': {'required': 'Date of registration is required.'},
        }

class HUFDetailsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit karta_name queryset to individual clients
        self.fields['karta_name'].queryset = Client.objects.filter(client_type='Individual')

        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'date'})
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class': 'form-control'})

            if field_name not in ['deed_of_declaration_file', 'remarks', 'bank_account_details']:
                field.widget.attrs.update({'required': 'required'})

    class Meta:
        model = HUFDetails
        fields = [
            'huf_name',
            'pan_huf',
            'date_of_creation',
            'karta_name',
            'number_of_coparceners',
            'number_of_members',
            'residential_address',
            'bank_account_details',
            'deed_of_declaration_file',
            'business_activity',
            'remarks'
        ]
        widgets = {
            'residential_address': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Enter complete residential address'}),
            'huf_name': forms.TextInput(attrs={'placeholder': 'Enter HUF name'}),
            'pan_huf': forms.TextInput(attrs={'placeholder': 'e.g., ABCDE1234F', 'style': 'text-transform: uppercase'}),
            'date_of_creation': forms.DateInput(attrs={'type': 'date'}),
            'bank_account_details': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter bank details in JSON format: {"bank_name": "", "account_number": "", "ifsc_code": ""}'
            }),
            'business_activity': forms.TextInput(attrs={'placeholder': 'Enter main business activity'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Enter any additional remarks'}),
            'number_of_coparceners': forms.NumberInput(attrs={'min': '1'}),
            'number_of_members': forms.NumberInput(attrs={'min': '1'}),
        }
        error_messages = {
            'huf_name': {'required': 'HUF name is required.'},
            'pan_huf': {'required': 'HUF PAN number is required.'},
            'date_of_creation': {'required': 'Date of creation is required.'},
            'karta_name': {'required': 'Karta name is required.'},
            'number_of_coparceners': {'required': 'Number of coparceners is required.'},
            'number_of_members': {'required': 'Number of members is required.'},
            'residential_address': {'required': 'Residential address is required.'},
            'business_activity': {'required': 'Business activity is required.'},
        }

    def clean_deed_of_declaration_file(self):
        file = self.cleaned_data.get('deed_of_declaration_file')
        if file:
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 10MB")

            valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError(
                    f"Unsupported file extension. Supported formats: {', '.join(valid_extensions)}"
                )
        return file

    def clean_pan_huf(self):
        pan_huf = self.cleaned_data.get('pan_huf', '').upper().strip()
        if len(pan_huf) != 10:
            raise forms.ValidationError("HUF PAN number must be exactly 10 characters long.")
        return pan_huf

    def clean_bank_account_details(self):
        bank_details = self.cleaned_data.get('bank_account_details', '').strip()
        # Basic JSON validation
        if bank_details:
            try:
                import json
                parsed = json.loads(bank_details)
                if not isinstance(parsed, dict):
                    raise forms.ValidationError("Bank details must be a valid JSON object.")
            except json.JSONDecodeError:
                raise forms.ValidationError("Please enter valid JSON format for bank details.")
        return bank_details