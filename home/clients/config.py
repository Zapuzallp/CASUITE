# clients/config.py

# ==============================================================================
# MASTER CONFIGURATION
# Controls Visibility, Labels, Logic, and Validation for the Onboarding Form
# ==============================================================================

STRUCTURE_CONFIG = {
    # --------------------------------------------------------------------------
    # 1. INDIVIDUAL (Freelancers, Students, etc.)
    # --------------------------------------------------------------------------
    'Individual': {
        'client': {
            'include': [],  # Include ALL basic fields
            'exclude': ['tan_no', 'din_no', 'business_structure'],
            'readonly': []
        },
        'profile': {
            'include': ['_none'],  # Explicitly show nothing
            'exclude': []
        },
        'labels': {
            'client_name': 'Full Name',
            'pan_no': 'PAN Card Number',
            'address_line1': 'Residential Address'
        },
        'validation': {
            'pan_no': {
                'regex': r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$',
                'message': 'Invalid PAN format. Example: ABCDE1234F'
            }
        }
    },

    # --------------------------------------------------------------------------
    # 2. PROPRIETORSHIP
    # --------------------------------------------------------------------------
    'Proprietorship': {
        'client': {
            'include': [],
            'exclude': ['tan_no', 'din_no'],
            'readonly': []
        },
        'profile': {
            'include': ['udyam_registration', 'registered_office_address'],
            'exclude': []
        },
        'labels': {
            'client_name': 'Proprietor Name',
            'registered_office_address': 'Shop/Office Address'
        }
    },

    # --------------------------------------------------------------------------
    # 3. PRIVATE LIMITED COMPANY
    # --------------------------------------------------------------------------
    'Private Ltd': {
        'client': {
            'include': [],
            'exclude': ['aadhar'],
            'readonly': ['client_type']
        },
        'profile': {
            'include': [
                'registration_number', 'date_of_incorporation', 'authorised_capital',
                'paid_up_capital', 'number_of_directors', 'number_of_shareholders',
                'key_persons', 'constitution_document_1', 'constitution_document_2',
                'udyam_registration', 'registered_office_address'
            ],
            'exclude': ['aadhar'],
            'readonly': []
        },
        'labels': {
            'client_name': 'Company Name',
            'registration_number': 'CIN',
            'constitution_document_1': 'Certificate of Incorporation / MOA',
            'constitution_document_2': 'AOA'
        },
        'validation': {
            # CIN Validation: 21 Chars (U/L + 5 digits + 2 chars + 4 digits + 3 chars + 6 digits)
            'registration_number': {
                'regex': r'^[LUu]{1}[\d]{5}[A-Z]{2}[\d]{4}[A-Z]{3}[\d]{6}$',
                'message': 'Invalid CIN format. Example: U12345MH2023PTC123456'
            },
            'pan_no': {
                'regex': r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$',
                'message': 'Invalid PAN format.'
            }
        }
    },

    # --------------------------------------------------------------------------
    # 4. LIMITED LIABILITY PARTNERSHIP (LLP)
    # --------------------------------------------------------------------------
    'LLP': {
        'client': {
            'include': [],
            'exclude': ['aadhar', 'din_no']
        },
        'profile': {
            'include': [
                'registration_number', 'date_of_incorporation', 'paid_up_capital',
                'key_persons', 'constitution_document_1', 'registered_office_address'
            ],
            'exclude': ['aadhar'],
        },
        'labels': {
            'client_name': 'LLP Name',
            'registration_number': 'LLPIN',
            'paid_up_capital': 'Total Contribution',
            'constitution_document_1': 'LLP Agreement'
        },
        'validation': {
            'registration_number': {
                'regex': r'^[A-Z]{3}-[\d]{4}$',
                'message': 'Invalid LLPIN format. Example: AAA-1234'
            }
        }
    },

    # --------------------------------------------------------------------------
    # 5. SECTION 8 COMPANY (With Conditional Logic)
    # --------------------------------------------------------------------------
    'Section 8': {
        'client': {
            'include': [],
            'exclude': ['aadhar']
        },
        'profile': {
            'include': [
                'is_section8_license_obtained',
                'registration_number',
                'date_of_incorporation',
                'object_clause',
                'key_persons',
                'constitution_document_1'
            ],
            'exclude': ['aadhar'],
        },
        'conditional_rules': [
            {
                'trigger_field': 'is_section8_license_obtained',
                'trigger_value': 'true',  # Value when Checkbox is Checked
                'targets': ['registration_number']  # Show License Number ONLY if checked
            }
        ],
        'labels': {
            'registration_number': 'License Number'
        }
    },

    # --------------------------------------------------------------------------
    # 6. HUF (Hindu Undivided Family)
    # --------------------------------------------------------------------------
    'HUF': {
        'client': {
            'include': [],
            'exclude': ['tan_no', 'din_no']
        },
        'profile': {
            'include': [
                'karta', 'date_of_incorporation', 'number_of_coparceners',
                'number_of_members', 'constitution_document_1'
            ],
            'exclude': ['aadhar'],
        },
        'labels': {
            'client_name': 'HUF Name',
            'date_of_incorporation': 'Date of Creation',
            'constitution_document_1': 'HUF Deed'
        }
    }
}

# ==============================================================================
# BACKEND REQUIRED FIELDS MAP
# Fields listed here will raise a "This field is required" error on submit
# ==============================================================================
REQUIRED_FIELDS_MAP = {
    'Private Ltd': ['registration_number', 'authorised_capital', 'paid_up_capital'],
    'Public Ltd': ['registration_number', 'authorised_capital', 'paid_up_capital'],
    'LLP': ['registration_number', 'paid_up_capital', 'constitution_document_1'],
    'HUF': ['karta', 'date_of_incorporation'],
    'Section 8': ['date_of_incorporation', 'object_clause'],
    'OPC': ['opc_nominee_name']
}

# ==============================================================================
# CONFIGURATION DOCUMENTATION
# ==============================================================================
#
# 1. 'workflow_steps': A list of strings defining the sequential stages of the task.
#    e.g., ['Pending', 'Draft', 'Review', 'Completed']
#
# 2. 'fields':
#    - 'include': Liszt of field names from TaskExtendedAttributes to show in the form.
#    - 'readonly': List of field names that should be visible but not editable.
#
# 3. 'labels': Dictionary to rename fields on the UI.
#    e.g., {'gstin_number': 'Select GSTIN'}
#
# 4. 'dynamic_defaults': (1-to-1 Mapping)
#    Auto-populates a field from a direct attribute of the Client model.
#    e.g., {'pan_number': 'pan_no'} -> Sets Task.pan_number = Client.pan_no
#
# ==============================================================================

DEFAULT_WORKFLOW_STEPS = ['Pending', 'In Progress', 'Review', 'Completed']

TASK_CONFIG = {
    # --------------------------------------------------------------------------
    # 1. GST RETURN (Uses Dynamic Dropdown)
    # --------------------------------------------------------------------------
    'GST Return': {
        'default_due_days': 20,
        'workflow_steps': ['Documents collect', 'Accounts Ready', 'Complete', 'GSTR Submit'],
        'fields': {
            'include': [
                'gstin_number', 'period_month', 'period_year', 'total_turnover',
                'tax_payable', 'arn_number', 'filing_date', 'json_file'
            ],
            'readonly': []
        },
        'labels': {
            'gstin_number': 'Select GSTIN',
            'total_turnover': 'Taxable Value'
        },

        # LOGIC: Look at client.gst_details.all(), take 'gst_number', show "GST - State"
        'data_sources': {
            'gstin_number': {
                'relation': 'gst_details',
                'value_field': 'gst_number',
                'label_field': 'gst_number',
                'extra_label': 'state'
            }
        }
    },

    # --------------------------------------------------------------------------
    # 2. ITR FILING (Uses Simple Auto-Fill)
    # --------------------------------------------------------------------------
    'ITR Filing': {
        'default_due_days': 120,
        'workflow_steps': ['Phone Call', 'Documents collection in progress', 'Documents collection complete', 'Manual', 'Account Ready', 'Form Fill up & Submit','EVC', 'Documents ready & billing', 'Delivered'],
        'fields': {
            'include': ['pan_number', 'assessment_year', 'gross_total_income', 'tax_payable', 'refund_amount',
                        'ack_number', 'computation_file'],
            'readonly': ['pan_number']
        },
        'labels': {'pan_number': 'Client PAN'},

        # LOGIC: Set pan_number = client.pan_no
        'dynamic_defaults': {
            'pan_number': 'pan_no'
        }
    },

    # --------------------------------------------------------------------------
    # 3. AUDIT
    # --------------------------------------------------------------------------
    'Audit': {
        'default_due_days': 180,
        'workflow_steps': ['Phone Call', 'Documents collection in progress', 'Documents collection complete', 'Manual', 'Account Ready', 'Send to Auditor','Accepts 3CB-3CD', 'Return Submit & Billing', 'Delivered'],
        'fields': {
            'include': ['financial_year', 'audit_fee', 'turnover_audited', 'udin_number', 'date_of_signing',
                        'audit_report_file']
        },
        'dynamic_defaults': {}
    },

    # --------------------------------------------------------------------------
    # 4. ROC COMPLIANCE
    # --------------------------------------------------------------------------
    'ROC Compliance': {
        'default_due_days': 30,
        'workflow_steps': ['Pending', 'Drafting', 'Signatures', 'Filed', 'Completed'],
        'fields': {
            'include': ['srn_number', 'din_numbers', 'meeting_date', 'remarks']
        },
        # LOGIC: Set din_numbers = client.din_no
        'dynamic_defaults': {
            'din_numbers': 'din_no'
        }
    }
}