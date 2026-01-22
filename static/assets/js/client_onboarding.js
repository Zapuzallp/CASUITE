// Client Onboarding JavaScript

document.addEventListener('DOMContentLoaded', function () {

    /* ================= STATE & ELEMENTS ================= */
    const clientBasicForm = document.getElementById('clientBasicForm');
    const businessStructureForm = document.getElementById('businessStructureForm');
    const businessStructureField = document.getElementById('businessStructureField');
    const submitButtonsContainer = document.getElementById('submitButtons');
    const formTitle = document.getElementById('formTitle');
    const clearButton = document.getElementById('clearButton');
    const confirmClearButton = document.getElementById('confirmClearButton');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

    const clientTypeSelectId = 'id_client_type';
    const clientTypeField = document.getElementById(clientTypeSelectId);

    let currentState = 'basic';
    let requestInFlight = false;

    /* ================= MODALS ================= */
    function showModal(id) {
        const el = document.getElementById(id);
        if (el) new bootstrap.Modal(el).show();
    }

    function hideModal(id) {
        const el = document.getElementById(id);
        const modal = bootstrap.Modal.getInstance(el);
        if (modal) modal.hide();
    }

    /* ================= SELECT2 ================= */
    function initializeSelect2(context = document) {

        /* FIX: remove Bootstrap interference */
        $(context).find('.select2-multiple').each(function () {
            this.classList.remove('form-control');
        });

        $(context).find('.select2-multiple').select2({
            theme: 'bootstrap-5',
            width: '100%',
            placeholder: function () {
                return $(this).data('placeholder');
            },
            allowClear: true,
            closeOnSelect: false
        });

        $(context).find('.form-select:not(.select2-multiple)').select2({
            theme: 'bootstrap-5',
            width: '100%',
            minimumResultsForSearch: 10
        });

        /* Clear error on change */
        $(context).find('.form-select.select2-hidden-accessible')
            .off('change.select2-clear-error')
            .on('change.select2-clear-error', function () {
                clearFieldError.call(this);
            });
    }

    function destroySelect2(context = document) {
        try { $(context).find('.select2-multiple').select2('destroy'); } catch {}
        try { $(context).find('.form-select').select2('destroy'); } catch {}
    }

    /* ================= VALIDATION HELPERS ================= */
    function showFieldError(field, message) {
        field.classList.add('is-invalid');
        let err = document.getElementById(`${field.name}_error`);
        if (!err) {
            err = document.createElement('div');
            err.className = 'invalid-feedback';
            err.id = `${field.name}_error`;
            field.parentNode.appendChild(err);
        }
        err.textContent = message;
    }

    function clearFieldError() {
        this.classList.remove('is-invalid');
        const err = document.getElementById(`${this.name}_error`);
        if (err) err.textContent = '';
    }

    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    /* ================= BASIC FORM VALIDATION ================= */
    function validateForm() {
        let isValid = true;

        const mandatory = [
            'client_name', 'primary_contact_name', 'pan_no', 'email',
            'phone_number', 'address_line1', 'city', 'state',
            'postal_code', 'country', 'date_of_engagement',
            'assigned_ca', 'client_type', 'status'
        ];

        mandatory.forEach(name => {
            const field = document.getElementById(`id_${name}`);
            if (field) {
                field.dispatchEvent(new Event('blur'));
                if (field.classList.contains('is-invalid')) isValid = false;
            }
        });

        if (!isValid) {
            showTemporaryAlert('Please fix validation errors.', 'error');
            document.querySelector('.is-invalid')?.scrollIntoView({ behavior: 'smooth' });
        }

        return isValid;
    }

    /* ================= FLOW CONTROLS ================= */
    function updateSubmitButtons() {
        if (!submitButtonsContainer) return;
        submitButtonsContainer.innerHTML = '';

        const type = clientTypeField?.value?.toLowerCase();
        if (!type) return;

        if (type === 'individual') {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-primary';
            btn.textContent = 'Review Details';
            btn.onclick = showReviewModal;
            submitButtonsContainer.appendChild(btn);
        } else {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-primary';
            btn.textContent = 'Next';
            btn.onclick = handleNextButtonClick;
            submitButtonsContainer.appendChild(btn);
        }
    }

    async function handleNextButtonClick() {
        if (requestInFlight || !validateForm()) return;
        requestInFlight = true;

        try {
            const res = await fetch(URLS.save_client_basic, {
                method: 'POST',
                body: new FormData(clientBasicForm),
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await res.json();
            if (data.success && data.form_html) {
                showBusinessStructureForm(data.form_html);
            }
        } finally {
            requestInFlight = false;
        }
    }

    function showBusinessStructureForm(html) {
        currentState = 'business';
        destroySelect2(clientBasicForm);

        clientBasicForm.style.display = 'none';
        businessStructureForm.innerHTML = html;
        businessStructureForm.style.display = 'block';

        setTimeout(() => {
            initializeSelect2(businessStructureForm);
            updateSubmitButtons();
        }, 100);
    }

    function goBackToBasicForm() {
        currentState = 'basic';
        destroySelect2(businessStructureForm);

        businessStructureForm.innerHTML = '';
        businessStructureForm.style.display = 'none';
        clientBasicForm.style.display = 'block';

        setTimeout(() => {
            initializeSelect2(clientBasicForm);
            updateSubmitButtons();
        }, 80);
    }

    /* ================= ALERT ================= */
    function showTemporaryAlert(msg, type) {
        const html = `
        <div class="alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show">
            ${msg}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>`;
        document.querySelector('main')?.insertAdjacentHTML('afterbegin', html);
    }

    /* ================= INIT ================= */
    function initializeForm() {
        currentState = 'basic';
        clientBasicForm.style.display = 'block';
        businessStructureForm.style.display = 'none';

        setTimeout(() => {
            initializeSelect2(clientBasicForm);
            updateSubmitButtons();
        }, 120);
    }

    clearButton?.addEventListener('click', () => showModal('clearFormModal'));

    confirmClearButton?.addEventListener('click', () => {
        destroySelect2();
        clientBasicForm.reset();
        initializeForm();
        hideModal('clearFormModal');
    });

    initializeForm();
});

<script>
$(document).ready(function () {
    $('.select2-multiple').select2({
        placeholder: "Select key persons",
        allowClear: true,
        width: '100'
    });
});
</script>





//// Client Onboarding JavaScript
//document.addEventListener('DOMContentLoaded', function() {
//    // Elements & state
//    const clientBasicForm = document.getElementById('clientBasicForm');
//    const businessStructureForm = document.getElementById('businessStructureForm');
//    const businessStructureField = document.getElementById('businessStructureField');
//    const submitButtonsContainer = document.getElementById('submitButtons');
//    const formTitle = document.getElementById('formTitle');
//    const clearButton = document.getElementById('clearButton');
//    const confirmClearButton = document.getElementById('confirmClearButton');
//    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
//    const clientTypeSelectId = 'id_client_type';
//    const clientTypeField = document.getElementById(clientTypeSelectId);
//
//    let currentState = 'basic';
//    let requestInFlight = false;
//
//    // --------- Modal Functions ----------
//    function showModal(modalId) {
//        const modalElement = document.getElementById(modalId);
//        if (modalElement) {
//            const modal = new bootstrap.Modal(modalElement);
//            modal.show();
//        }
//    }
//
//    function hideModal(modalId) {
//        const modalElement = document.getElementById(modalId);
//        if (modalElement) {
//            const modal = bootstrap.Modal.getInstance(modalElement);
//            if (modal) {
//                modal.hide();
//            }
//        }
//    }
//
//    // --------- Select2 helpers ----------
//    function initializeSelect2(context = document) {
//        $(context).find('.select2-multiple').select2({
//            theme: 'bootstrap-5',
//            width: '100%',
//            placeholder: function() { return $(this).data('placeholder'); },
//            allowClear: true,
//            closeOnSelect: false
//        });
//
//        $(context).find('.form-select:not(.select2-multiple)').select2({
//            theme: 'bootstrap-5',
//            width: '100%',
//            minimumResultsForSearch: 10
//        });
//
//        // Special handling for assigned_ca field and other Select2 fields
//        $(context).find('.form-select.select2-hidden-accessible').each(function() {
//            const field = this;
//            $(field).off('change.select2-clear-error');
//            $(field).on('change.select2-clear-error', function() {
//                console.log('Select2 field changed:', field.name, 'Value:', this.value);
//                clearFieldError.call(this);
//            });
//        });
//
//        // Special handling for business structure field
//        const businessStructureField = context.querySelector('#id_business_structure');
//        if (businessStructureField) {
//            $(businessStructureField).off('change.select2-business');
//            $(businessStructureField).on('change.select2-business', function(e) {
//                console.log('Business structure Select2 changed to:', this.value);
//                clearFieldError.call(this);
//            });
//        }
//    }
//
//    function destroySelect2(context = document) {
//        try {
//            $(context).find('.select2-multiple').select2('destroy');
//        } catch (e) {}
//        try {
//            $(context).find('.form-select').select2('destroy');
//        } catch (e) {}
//    }
//
//    // --------- Validation helpers ----------
//    function showFieldError(field, message) {
//        field.classList.add('is-invalid');
//        const errorElement = document.getElementById(`${field.name}_error`);
//        if (errorElement) {
//            errorElement.textContent = message;
//        } else {
//            console.warn('Error element not found for:', field.name);
//            const errorDiv = document.createElement('div');
//            errorDiv.className = 'invalid-feedback';
//            errorDiv.id = `${field.name}_error`;
//            errorDiv.textContent = message;
//            field.parentNode.appendChild(errorDiv);
//        }
//    }
//
//    function clearFieldError() {
//        this.classList.remove('is-invalid');
//        const errorElement = document.getElementById(`${this.name}_error`);
//        if (errorElement) {
//            errorElement.textContent = '';
//        }
//    }
//
//    function isValidEmail(email) {
//        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
//        return emailRegex.test(email);
//    }
//
//    function validateField(e) {
//        const field = e.target;
//        const fieldName = field.name;
//        const value = field.value.trim();
//        field.classList.remove('is-invalid');
//
//        const mandatoryFields = [
//            'client_name', 'primary_contact_name', 'pan_no', 'email',
//            'phone_number', 'address_line1', 'city', 'state',
//            'postal_code', 'country', 'date_of_engagement', 'assigned_ca',
//            'client_type', 'status'
//        ];
//
//        // Check if field is in mandatory fields
//        if (mandatoryFields.includes(fieldName) && !value) {
//            showFieldError(field, 'This field is required.');
//            return false;
//        }
//
//        // Get client type for conditional validation
//        const clientTypeField = document.getElementById('id_client_type');
//        const clientType = clientTypeField ? clientTypeField.value.toLowerCase() : '';
//
//        // Special handling for Aadhar and DIN - ONLY for Individual clients
//        if (clientType === 'individual') {
//            if (fieldName === 'aadhar' && !value) {
//                showFieldError(field, 'Aadhar number is required for Individual clients.');
//                return false;
//            }
//            if (fieldName === 'din_no' && !value) {
//                showFieldError(field, 'DIN number is required for Individual clients.');
//                return false;
//            }
//        } else {
//            // For Entity clients, clear any Aadhar/DIN errors if they exist
//            if (fieldName === 'aadhar' || fieldName === 'din_no') {
//                clearFieldError.call(field);
//            }
//        }
//
//        // Existing validation rules for all fields...
//        switch(fieldName) {
//            case 'phone_number':
//                const phoneDigits = value.replace(/\D/g, '');
//                if (phoneDigits.length !== 10) {
//                    showFieldError(field, 'Phone number must be exactly 10 digits.');
//                    return false;
//                }
//                break;
//            case 'pan_no':
//                if (value.length !== 10) {
//                    showFieldError(field, 'PAN number must be exactly 10 characters.');
//                    return false;
//                }
//                break;
//            case 'aadhar':
//                // Only validate format if there's a value (not mandatory for entities)
//                if (value) {
//                    const aadharDigits = value.replace(/\D/g, '');
//                    if (aadharDigits.length !== 12) {
//                        showFieldError(field, 'Aadhar number must be exactly 12 digits.');
//                        return false;
//                    }
//                }
//                break;
//            case 'email':
//                if (value && !isValidEmail(value)) {
//                    showFieldError(field, 'Please enter a valid email address.');
//                    return false;
//                }
//                break;
//            case 'postal_code':
//                if (!/^\d{6}$/.test(value)) {
//                    showFieldError(field, 'Postal code must be exactly 6 digits.');
//                    return false;
//                }
//                break;
//        }
//        return true;
//    }
//
//    function toggleIndividualRequiredFields() {
//        const clientTypeField = document.getElementById('id_client_type');
//        const aadharRequired = document.getElementById('aadhar_required');
//        const dinRequired = document.getElementById('din_required');
//
//        if (clientTypeField && aadharRequired && dinRequired) {
//            const clientType = clientTypeField.value ? clientTypeField.value.toLowerCase() : '';
//
//            if (clientType === 'individual') {
//                aadharRequired.style.display = 'inline';
//                dinRequired.style.display = 'inline';
//            } else {
//                aadharRequired.style.display = 'none';
//                dinRequired.style.display = 'none';
//            }
//        }
//    }
//
//    function setupRealTimeValidation() {
//        const mandatoryFields = [
//            'client_name', 'primary_contact_name', 'pan_no', 'email',
//            'phone_number', 'address_line1', 'city', 'state',
//            'postal_code', 'country', 'date_of_engagement', 'assigned_ca',
//            'client_type', 'status', 'aadhar', 'din_no' // Include them but handle conditionally
//        ];
//
//        mandatoryFields.forEach(fieldName => {
//            const field = document.getElementById(`id_${fieldName}`);
//            if (field) {
//                field.removeEventListener('blur', validateField);
//                field.removeEventListener('input', clearFieldError);
//                field.addEventListener('blur', validateField);
//                field.addEventListener('input', clearFieldError);
//
//                if ($(field).hasClass('select2-hidden-accessible')) {
//                    $(field).off('change.select2-validation');
//                    $(field).on('change.select2-validation', function() {
//                        clearFieldError.call(this);
//                        validateField({ target: this });
//                    });
//                }
//            }
//        });
//
//        const businessStructureField = document.getElementById('id_business_structure');
//        if (businessStructureField) {
//            businessStructureField.removeEventListener('change', handleBusinessStructureChange);
//            businessStructureField.addEventListener('change', handleBusinessStructureChange);
//        }
//
//        const phoneField = document.getElementById('id_phone_number');
//        if (phoneField) {
//            phoneField.addEventListener('input', function(e) {
//                let value = e.target.value.replace(/\D/g, '');
//                if (value.length > 10) value = value.substring(0, 10);
//                e.target.value = value;
//                clearFieldError.call(e.target);
//            });
//        }
//
//        const postalField = document.getElementById('id_postal_code');
//        if (postalField) {
//            postalField.addEventListener('input', function(e) {
//                let value = e.target.value.replace(/\D/g, '');
//                if (value.length > 6) value = value.substring(0,6);
//                e.target.value = value;
//                clearFieldError.call(e.target);
//            });
//            postalField.addEventListener('blur', validateField);
//        }
//
//        const aadharField = document.getElementById('id_aadhar');
//        if (aadharField) {
//            aadharField.addEventListener('input', function(e) {
//                let value = e.target.value.replace(/\D/g, '');
//                if (value.length > 12) value = value.substring(0,12);
//                let formatted = value;
//                if (formatted.length > 4) formatted = formatted.substring(0,4) + '-' + formatted.substring(4);
//                if (formatted.length > 9) formatted = formatted.substring(0,9) + '-' + formatted.substring(9);
//                e.target.value = formatted;
//                clearFieldError.call(e.target);
//            });
//        }
//
//        const panField = document.getElementById('id_pan_no');
//        if (panField) {
//            panField.addEventListener('input', function(e) {
//                e.target.value = e.target.value.toUpperCase();
//                clearFieldError.call(e.target);
//            });
//        }
//    }
//
//    function handleBusinessStructureChange(e) {
//        console.log('Business structure changed to:', this.value);
//        clearFieldError.call(this);
//    }
//
//    function validateForm() {
//        let isValid = true;
//        const mandatoryFields = [
//            'client_name', 'primary_contact_name', 'pan_no', 'email',
//            'phone_number', 'address_line1', 'city', 'state',
//            'postal_code', 'country', 'date_of_engagement', 'assigned_ca',
//            'client_type', 'status'
//        ];
//
//        // Validate all basic mandatory fields
//        mandatoryFields.forEach(fieldName => {
//            const field = document.getElementById(`id_${fieldName}`);
//            if (field) {
//                const event = new Event('blur', { bubbles: true });
//                field.dispatchEvent(event);
//                if (field.classList.contains('is-invalid')) isValid = false;
//            }
//        });
//
//        // Get client type FIRST
//        const clientTypeField = document.getElementById('id_client_type');
//        const clientType = clientTypeField ? clientTypeField.value.toLowerCase() : '';
//
//        console.log('🔍 validateForm - Client type:', clientType);
//
//        // ONLY validate Aadhar and DIN for Individual clients
//        if (clientType === 'individual') {
//            const aadharField = document.getElementById('id_aadhar');
//            const dinField = document.getElementById('id_din_no');
//
//            // Validate Aadhar for Individual clients
//            if (aadharField && !aadharField.value.trim()) {
//                showFieldError(aadharField, 'Aadhar number is required for Individual clients.');
//                isValid = false;
//            }
//
//            // Validate DIN for Individual clients
//            if (dinField && !dinField.value.trim()) {
//                showFieldError(dinField, 'DIN number is required for Individual clients.');
//                isValid = false;
//            }
//        } else {
//            // For Entity clients, CLEAR any existing errors on Aadhar and DIN fields
//            const aadharField = document.getElementById('id_aadhar');
//            const dinField = document.getElementById('id_din_no');
//
//            if (aadharField) {
//                aadharField.classList.remove('is-invalid');
//                const errorElement = document.getElementById('aadhar_error');
//                if (errorElement) errorElement.textContent = '';
//            }
//
//            if (dinField) {
//                dinField.classList.remove('is-invalid');
//                const errorElement = document.getElementById('din_no_error');
//                if (errorElement) errorElement.textContent = '';
//            }
//        }
//
//        // Validate business structure field ONLY for Entity clients
//        const businessStructureField = document.getElementById('id_business_structure');
//        if (businessStructureField) {
//            const businessStructure = businessStructureField.value ? businessStructureField.value.trim() : '';
//
//            console.log('🔍 validateForm - Business structure:', businessStructure, 'for client type:', clientType);
//
//            if (clientType === 'entity' && !businessStructure) {
//                showFieldError(businessStructureField, 'Business structure is required for Entity clients.');
//                isValid = false;
//            } else {
//                // Clear business structure error for non-entity clients or when valid
//                clearFieldError.call(businessStructureField);
//            }
//        }
//
//        if (!isValid) {
//            showTemporaryAlert('Please fix the validation errors before proceeding.', 'error');
//            // Scroll to first error
//            const firstError = document.querySelector('.is-invalid');
//            if (firstError) {
//                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
//            }
//        } else {
//            console.log('✅ Form validation passed');
//        }
//
//        return isValid;
//    }
//
//    // --------- Business Form Validation ----------
//    function setupBusinessFormValidation() {
//        const businessForm = document.querySelector('#businessStructureDetailsForm');
//        if (!businessForm) return;
//
//        const inputs = businessForm.querySelectorAll('input, select, textarea');
//        inputs.forEach(input => {
//            const fieldName = input.name;
//            input.removeEventListener('blur', validateBusinessField);
//            input.removeEventListener('input', clearBusinessFieldError);
//            input.removeEventListener('change', validateBusinessField);
//
//            input.addEventListener('blur', function(e) {
//                validateBusinessField(e);
//            });
//
//            input.addEventListener('input', function(e) {
//                clearBusinessFieldError.call(this);
//            });
//
//            if (input.tagName === 'SELECT') {
//                input.addEventListener('change', function(e) {
//                    validateBusinessField(e);
//                });
//            }
//
//            if (input.type === 'checkbox') {
//                input.addEventListener('change', function(e) {
//                    validateBusinessField(e);
//                });
//            }
//
//            if (input.type === 'file') {
//                input.addEventListener('change', function(e) {
//                    validateBusinessField(e);
//                });
//            }
//        });
//    }
//
//    function getMandatoryFieldsForBusinessStructure() {
//        const businessStructureInput = document.querySelector('input[name="business_structure"]');
//        const businessStructure = businessStructureInput ? businessStructureInput.value : '';
//
//        const mandatoryFields = {
//            'Private Ltd': [
//                'company_type', 'proposed_company_name', 'cin', 'authorised_share_capital',
//                'paid_up_share_capital', 'number_of_directors', 'number_of_shareholders',
//                'registered_office_address', 'date_of_incorporation', 'udyam_registration', 'directors'
//            ],
//            'Public Ltd': [
//                'company_type', 'proposed_company_name', 'cin', 'authorised_share_capital',
//                'paid_up_share_capital', 'number_of_directors', 'number_of_shareholders',
//                'registered_office_address', 'date_of_incorporation', 'udyam_registration', 'directors'
//            ],
//            'LLP': [
//                'llp_name', 'llp_registration_no', 'registered_office_address_llp',
//                'designated_partners', 'paid_up_capital_llp', 'date_of_registration_llp'
//            ],
//            'OPC': [
//                'opc_name', 'opc_cin', 'registered_office_address_opc',
//                'sole_member_name', 'nominee_member_name', 'paid_up_share_capital_opc', 'date_of_incorporation_opc'
//            ],
//            'Section 8': [
//                'section8_company_name', 'registration_no_section8', 'registered_office_address_s8',
//                'object_clause', 'date_of_registration_s8'
//            ],
//            'HUF': [
//                'huf_name', 'pan_huf', 'date_of_creation', 'karta_name',
//                'number_of_coparceners', 'number_of_members', 'residential_address', 'business_activity'
//            ]
//        };
//
//        return mandatoryFields[businessStructure] || [];
//    }
//
//    function validateBusinessField(e) {
//        const field = e.target;
//        const fieldName = field.name;
//        let value;
//
//        if (field.type === 'checkbox') {
//            value = field.checked;
//        } else if (field.type === 'file') {
//            value = field.files.length > 0 ? field.files[0].name : '';
//        } else if (field.tagName === 'SELECT' && field.multiple) {
//            value = Array.from(field.selectedOptions).map(opt => opt.value);
//        } else {
//            value = field.value ? field.value.trim() : '';
//        }
//
//        clearBusinessFieldError.call(field);
//
//        const mandatoryFields = getMandatoryFieldsForBusinessStructure();
//        const isMandatory = mandatoryFields.includes(fieldName);
//
//        if (isMandatory) {
//            let isEmpty = false;
//
//            if (field.type === 'checkbox') {
//                isEmpty = !value;
//            } else if (field.tagName === 'SELECT' && field.multiple) {
//                isEmpty = value.length === 0;
//            } else if (field.type === 'file') {
//                isEmpty = !value;
//            } else {
//                isEmpty = !value || value === '';
//            }
//
//            if (isEmpty) {
//                showBusinessFieldError(field, 'This field is required.');
//                return false;
//            }
//        }
//
//        if (!value || value === '' || (Array.isArray(value) && value.length === 0)) {
//            return true;
//        }
//
//        return validateBusinessFieldSpecificRules(field, fieldName, value);
//    }
//
//    function validateBusinessFieldSpecificRules(field, fieldName, value) {
//        switch(fieldName) {
//            case 'udyam_registration':
//                if (!/^UDYAM-[A-Z]{2}-\d{2}-\d{7}$/.test(value)) {
//                    showBusinessFieldError(field, 'Please enter a valid Udyam registration number (format: UDYAM-XX-XX-XXXXXXX).');
//                    return false;
//                }
//                break;
//
//            case 'authorised_share_capital':
//            case 'paid_up_share_capital':
//            case 'paid_up_capital_llp':
//            case 'paid_up_share_capital_opc':
//                const capitalValue = parseFloat(value);
//                if (isNaN(capitalValue) || capitalValue < 0) {
//                    showBusinessFieldError(field, 'Please enter a valid capital amount (positive number).');
//                    return false;
//                }
//                if (capitalValue > 1000000000) {
//                    showBusinessFieldError(field, 'Capital amount seems too high. Please verify.');
//                    return false;
//                }
//                break;
//
//            case 'number_of_directors':
//            case 'number_of_shareholders':
//            case 'number_of_coparceners':
//            case 'number_of_members':
//                const numValue = parseInt(value);
//                if (isNaN(numValue) || numValue < 1) {
//                    showBusinessFieldError(field, 'Please enter a valid number (at least 1).');
//                    return false;
//                }
//                if (numValue > 100) {
//                    showBusinessFieldError(field, 'Number seems too high. Please verify.');
//                    return false;
//                }
//                break;
//
//            case 'email':
//                if (!isValidEmail(value)) {
//                    showBusinessFieldError(field, 'Please enter a valid email address.');
//                    return false;
//                }
//                break;
//        }
//
//        return true;
//    }
//
//    function showBusinessFieldError(field, message) {
//        field.classList.add('is-invalid');
//        const errorElement = document.getElementById(`${field.name}_error`);
//        if (errorElement) {
//            errorElement.textContent = message;
//        }
//    }
//
//    function clearBusinessFieldError() {
//        this.classList.remove('is-invalid');
//        const errorElement = document.getElementById(`${this.name}_error`);
//        if (errorElement) {
//            errorElement.textContent = '';
//        }
//    }
//
//    function validateBusinessForm() {
//        const businessForm = document.querySelector('#businessStructureDetailsForm');
//        if (!businessForm) {
//            return true;
//        }
//
//        let isValid = true;
//        const mandatoryFields = getMandatoryFieldsForBusinessStructure();
//
//        mandatoryFields.forEach(fieldName => {
//            let field = businessForm.querySelector(`[name="${fieldName}"]`);
//            if (!field) {
//                field = document.getElementById(`id_${fieldName}`);
//            }
//
//            if (field) {
//                const event = new Event('blur', { bubbles: true });
//                field.dispatchEvent(event);
//
//                if (field.classList.contains('is-invalid')) {
//                    isValid = false;
//                }
//            }
//        });
//
//        if (!isValid) {
//            showTemporaryAlert('Please fix the validation errors before submitting.', 'error');
//            const firstError = businessForm.querySelector('.is-invalid');
//            if (firstError) {
//                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
//            }
//        }
//
//        return isValid;
//    }
//
//    // --------- Button / flow helpers ----------
//    function updateSubmitButtons() {
//        console.log('updateSubmitButtons called - currentState:', currentState);
//
//        if (currentState === 'basic') {
//            if (!submitButtonsContainer) return;
//            submitButtonsContainer.innerHTML = '';
//
//            const clientTypeField = document.getElementById('id_client_type');
//            const clientType = clientTypeField ? clientTypeField.value : '';
//
//            if (clientType) {
//                if (clientType.toLowerCase() === 'individual') {
//                    const reviewButton = document.createElement('button');
//                    reviewButton.type = 'button';
//                    reviewButton.className = 'btn btn-primary';
//                    reviewButton.id = 'reviewButton';
//                    reviewButton.textContent = 'Review Details';
//                    reviewButton.onclick = showReviewModal;
//                    submitButtonsContainer.appendChild(reviewButton);
//                } else if (clientType.toLowerCase() === 'entity') {
//                    const nextButton = document.createElement('button');
//                    nextButton.type = 'button';
//                    nextButton.className = 'btn btn-primary';
//                    nextButton.id = 'nextButton';
//                    nextButton.textContent = 'Next';
//                    nextButton.onclick = handleNextButtonClick;
//                    submitButtonsContainer.appendChild(nextButton);
//                }
//            }
//        } else if (currentState === 'business') {
//            const businessForm = document.querySelector('#businessStructureDetailsForm');
//            if (!businessForm) {
//                return;
//            }
//
//            const existingButtons = businessForm.querySelectorAll('.dynamic-form-buttons');
//            existingButtons.forEach(btn => btn.remove());
//
//            const buttonContainer = document.createElement('div');
//            buttonContainer.className = 'dynamic-form-buttons row mt-4';
//            buttonContainer.innerHTML = `
//                <div class="col-12">
//                    <div class="d-flex justify-content-between align-items-center">
//                        <button type="button" id="bizBackBtn" class="btn btn-secondary">Back</button>
//                        <button type="button" id="bizReviewBtn" class="btn btn-primary">Review</button>
//                    </div>
//                </div>
//            `;
//
//            businessForm.appendChild(buttonContainer);
//
//            document.getElementById('bizBackBtn').onclick = goBackToBasicForm;
//            document.getElementById('bizReviewBtn').onclick = function() {
//                if (validateBusinessForm()) {
//                    showBusinessReviewModal();
//                }
//            };
//        }
//    }
//
//    async function handleNextButtonClick() {
//        if (requestInFlight) return;
//
//        if (!validateForm()) {
//            return;
//        }
//
//        requestInFlight = true;
//
//        try {
//            const formData = new FormData(clientBasicForm);
//            const res = await fetch(URLS.save_client_basic, {
//                method: 'POST',
//                body: formData,
//                headers: { 'X-CSRFToken': csrfToken, 'X-Requested-With': 'XMLHttpRequest' }
//            });
//
//            if (!res.ok) {
//                throw new Error('HTTP ' + res.status);
//            }
//
//            const data = await res.json();
//
//            if (data.success) {
//                if (data.form_html) {
//                    showBusinessStructureForm(data);
//                } else if (data.redirect_url) {
//                    window.location.href = data.redirect_url;
//                } else {
//                    showTemporaryAlert('Unexpected response from server.', 'error');
//                }
//            } else {
//                handleFormErrors(data);
//            }
//        } catch (err) {
//            console.error('handleNextButtonClick error:', err);
//            showTemporaryAlert('Network error occurred. Please try again.', 'error');
//        } finally {
//            requestInFlight = false;
//        }
//    }
//
//    function showBusinessStructureForm(data) {
//        console.log('🔄 showBusinessStructureForm called');
//
//        currentState = 'business';
//        destroySelect2(clientBasicForm);
//
//        clientBasicForm.style.display = 'none';
//        businessStructureForm.style.display = 'block';
//        businessStructureForm.innerHTML = data.form_html;
//
//        if (formTitle) formTitle.style.display = 'none';
//
//        // Initialize after ALL DOM operations are complete
//        setTimeout(() => {
//            console.log('Initializing business form components...');
//            initializeSelect2(businessStructureForm);
//            setupBusinessFormValidation();
//            attachBusinessFormHandlers();
//            updateSubmitButtons();
//        }, 100);
//
//        window.scrollTo(0, 0);
//        console.log('✅ Business structure form loaded');
//    }
//
//    function attachBusinessFormHandlers() {
//        const existingBackButton = businessStructureForm.querySelector('#backButton');
//        if (existingBackButton) {
//            existingBackButton.remove();
//        }
//
//        const businessForm = businessStructureForm.querySelector('#businessStructureDetailsForm');
//        if (businessForm) {
//            const existingSubmitButton = businessForm.querySelector('button[type="submit"]');
//            if (existingSubmitButton) {
//                existingSubmitButton.remove();
//            }
//
//            businessForm.addEventListener('submit', function(e) {
//                e.preventDefault();
//                if (validateBusinessForm()) {
//                    submitBusinessStructureForm(businessForm);
//                }
//            });
//
//            const fileInputs = businessForm.querySelectorAll('input[type="file"]');
//            fileInputs.forEach(input => {
//                input.addEventListener('change', function(e) {
//                    const feedback = this.closest('.col-md-6')?.querySelector('.file-upload-feedback');
//                    if (feedback && this.files.length > 0) {
//                        feedback.style.display = 'block';
//                        const fileName = this.files[0].name;
//                        feedback.innerHTML = `<small class="text-success"><i class="bi bi-check-circle"></i> ${fileName}</small>`;
//                    } else if (feedback) {
//                        feedback.style.display = 'none';
//                    }
//                });
//            });
//        }
//
//        updateSubmitButtons();
//    }
//
//    async function submitBusinessStructureForm(form) {
//        try {
//            const formData = new FormData(form);
//
//            const res = await fetch(URLS.save_client_complete, {
//                method: 'POST',
//                body: formData,
//                headers: { 'X-CSRFToken': csrfToken }
//            });
//
//            if (!res.ok) throw new Error('HTTP ' + res.status);
//
//            const data = await res.json();
//
//            if (data.success) {
//                showSuccessModal(data.client_id, data.client_name);
//            } else {
//                handleFormErrors(data);
//            }
//
//        } catch (err) {
//            console.error('submitBusinessStructureForm error:', err);
//            showTemporaryAlert('Network error occurred. Please try again.', 'error');
//        }
//    }
//
//    function goBackToBasicForm() {
//        currentState = 'basic';
//        destroySelect2(businessStructureForm);
//
//        businessStructureForm.style.display = 'none';
//        businessStructureForm.innerHTML = '';
//        clientBasicForm.style.display = 'block';
//
//        if (formTitle) {
//            formTitle.style.display = 'block';
//            formTitle.innerHTML = 'Client Basic Information <small class="text-muted">(<span class="text-danger">*</span> indicates required field)</small>';
//        }
//
//        setTimeout(() => {
//            initializeSelect2(clientBasicForm);
//            setupRealTimeValidation();
//            attachClientTypeChange();
//            updateSubmitButtons();
//        }, 80);
//
//        fetch(URLS.clear_client_session, {
//            method: 'POST',
//            headers: { 'X-CSRFToken': csrfToken, 'X-Requested-With': 'XMLHttpRequest' },
//            keepalive: true
//        }).catch(()=>{});
//
//        updateSubmitButtons();
//        window.scrollTo(0, 0);
//    }
//
//    function showSuccessModal(clientId, clientName) {
//        document.getElementById('successClientId').textContent = clientId;
//        document.getElementById('successClientName').textContent = clientName;
//        showModal('successModal');
//
//        document.getElementById('successOkButton').onclick = function() {
//            hideModal('successModal');
//            window.location.href = URLS.clients;
//        };
//    }
//
//    // --------- form errors helper ----------
//    function handleFormErrors(data) {
//        if (!data) return;
//        if (data.errors) {
//            for (let field in data.errors) {
//                const elem = document.getElementById(`id_${field}`);
//                if (elem) showFieldError(elem, data.errors[field].join(', '));
//            }
//            showTemporaryAlert('Please fix the form errors before reviewing.', 'error');
//        } else if (data.error) {
//            showTemporaryAlert('Error: ' + data.error, 'error');
//        } else {
//            showTemporaryAlert('An unknown error occurred.', 'error');
//        }
//    }
//
//    // --------- temporary alert ----------
//    function showTemporaryAlert(message, type) {
//        const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
//        const alertHtml = `
//            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
//                <i class="bi bi-check-circle-fill"></i>
//                ${message}
//                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
//            </div>
//        `;
//        const main = document.querySelector('main');
//        const existing = main.querySelectorAll('.alert');
//        existing.forEach(e => e.remove());
//        main.insertAdjacentHTML('afterbegin', alertHtml);
//        setTimeout(() => {
//            const alert = main.querySelector('.alert');
//            if (alert) {
//                try { new bootstrap.Alert(alert).close(); } catch (e) {}
//            }
//        }, 5000);
//    }
//
//    // --------- client type change ----------
//    function attachClientTypeChange() {
//        try {
//            $('#'+clientTypeSelectId).off('change.select2-client-type');
//        } catch(e){}
//
//        $('#'+clientTypeSelectId).on('change.select2-client-type', function() {
//            console.log('Client type changed to:', this.value);
//            toggleBusinessStructure();
//            toggleIndividualRequiredFields();
//            updateSubmitButtons();
//
//            const businessStructureField = document.getElementById('id_business_structure');
//            if (businessStructureField) {
//                clearFieldError.call(businessStructureField);
//                const clientType = this.value ? this.value.toLowerCase() : '';
//                if (clientType !== 'entity') {
//                    businessStructureField.value = '';
//                    if ($(businessStructureField).hasClass('select2-hidden-accessible')) {
//                        $(businessStructureField).trigger('change');
//                    }
//                }
//            }
//
//            const aadharField = document.getElementById('id_aadhar');
//            const dinField = document.getElementById('id_din_no');
//            if (aadharField) clearFieldError.call(aadharField);
//            if (dinField) clearFieldError.call(dinField);
//        });
//
//        setTimeout(() => {
//            toggleBusinessStructure();
//            toggleIndividualRequiredFields();
//            updateSubmitButtons();
//        }, 200);
//    }
//
//    function toggleBusinessStructure() {
//        if (!businessStructureField || !clientTypeField) return;
//
//        const clientType = clientTypeField.value ? clientTypeField.value.toLowerCase() : '';
//
//        if (clientType === 'entity') {
//            businessStructureField.style.display = 'block';
//        } else {
//            businessStructureField.style.display = 'none';
//            const businessStructureFieldInput = document.getElementById('id_business_structure');
//            if (businessStructureFieldInput) {
//                businessStructureFieldInput.value = '';
//                clearFieldError.call(businessStructureFieldInput);
//            }
//        }
//    }
//
//    // --------- Review Modal Functions ----------
//    function showReviewModal() {
//        if (!validateForm()) {
//            return;
//        }
//
//        populateReviewContent();
//
//        const clientType = document.getElementById('id_client_type').value;
//        const modalTitle = document.querySelector('#reviewModal .modal-title');
//        const confirmSaveButton = document.getElementById('confirmSaveButton');
//
//        if (clientType.toLowerCase() === 'individual') {
//            if (modalTitle) modalTitle.innerHTML = '<i class="bi bi-eye-fill me-2"></i>Review Individual Client Details';
//            if (confirmSaveButton) confirmSaveButton.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i>Save';
//        } else {
//            if (modalTitle) modalTitle.innerHTML = '<i class="bi bi-eye-fill me-2"></i>Review Basic Information';
//            if (confirmSaveButton) confirmSaveButton.innerHTML = '<i class="bi bi-arrow-right-circle-fill me-1"></i>Proceed to Business Details';
//        }
//
//        showModal('reviewModal');
//    }
//
//    function showBusinessReviewModal() {
//        if (!validateBusinessForm()) {
//            return;
//        }
//
//        populateBusinessReviewWithBasicInfo();
//
//        const modalTitle = document.querySelector('#reviewModal .modal-title');
//        const confirmSaveButton = document.getElementById('confirmSaveButton');
//
//        if (modalTitle) {
//            modalTitle.innerHTML = '<i class="bi bi-eye-fill me-2"></i>Review Entity Client Details';
//        }
//        if (confirmSaveButton) {
//            confirmSaveButton.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i>Save';
//            confirmSaveButton.onclick = submitBusinessStructureFormFromReview;
//        }
//
//        showModal('reviewModal');
//    }
//
//    function populateReviewContent() {
//        const reviewContent = document.getElementById('reviewContent');
//        if (!reviewContent) return;
//
//        const formData = new FormData(clientBasicForm);
//        const clientType = document.getElementById('id_client_type').value;
//
//        const assignedCaField = document.getElementById('id_assigned_ca');
//        const assignedCaDisplay = assignedCaField ? assignedCaField.options[assignedCaField.selectedIndex]?.text || 'N/A' : 'N/A';
//
//        let html = `
//            <div class="col-md-6">
//                <table class="table table-sm table-borderless">
//                    <tr>
//                        <td class="text-muted" style="width: 40%">Client Name:</td>
//                        <td><strong>${formData.get('client_name') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">Primary Contact:</td>
//                        <td><strong>${formData.get('primary_contact_name') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">PAN No:</td>
//                        <td><strong>${formData.get('pan_no') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">Email:</td>
//                        <td><strong>${formData.get('email') || 'N/A'}</strong></td>
//                    </tr>
//                </table>
//            </div>
//            <div class="col-md-6">
//                <table class="table table-sm table-borderless">
//                    <tr>
//                        <td class="text-muted" style="width: 40%">Client Type:</td>
//                        <td><strong>${clientType || 'N/A'}</strong></td>
//                    </tr>
//        `;
//
//        html += `
//                    <tr>
//                        <td class="text-muted">Contact No:</td>
//                        <td><strong>${formData.get('phone_number') || 'N/A'}</strong></td>
//                    </tr>
//        `;
//
//        if (clientType.toLowerCase() === 'individual') {
//            html += `
//                    <tr>
//                        <td class="text-muted">Aadhar No:</td>
//                        <td><strong>${formData.get('aadhar') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">DIN No:</td>
//                        <td><strong>${formData.get('din_no') || 'N/A'}</strong></td>
//                    </tr>
//            `;
//        }
//
//        if (clientType.toLowerCase() === 'entity') {
//            const businessStructure = formData.get('business_structure');
//            if (businessStructure) {
//                html += `
//                    <tr>
//                        <td class="text-muted">Business Structure:</td>
//                        <td><strong>${businessStructure || 'N/A'}</strong></td>
//                    </tr>
//                `;
//            }
//        }
//
//        html += `
//                    <tr>
//                        <td class="text-muted">Assigned CA/Article:</td>
//                        <td><strong>${assignedCaDisplay}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">Status:</td>
//                        <td><strong>${formData.get('status') || 'N/A'}</strong></td>
//                    </tr>
//                </table>
//            </div>
//            <div class="col-12 mt-3">
//                <h6 class="border-bottom pb-2 mb-3">Address Information</h6>
//                <table class="table table-sm table-borderless">
//                    <tr>
//                        <td class="text-muted" style="width: 20%">Address Line 1:</td>
//                        <td><strong>${formData.get('address_line1') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">City:</td>
//                        <td><strong>${formData.get('city') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">State:</td>
//                        <td><strong>${formData.get('state') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">Postal Code:</td>
//                        <td><strong>${formData.get('postal_code') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">Country:</td>
//                        <td><strong>${formData.get('country') || 'N/A'}</strong></td>
//                    </tr>
//                </table>
//            </div>
//        `;
//
//        const remarks = formData.get('remarks');
//        if (remarks) {
//            html += `
//                <div class="col-12 mt-3">
//                    <h6 class="border-bottom pb-2 mb-3">Remarks</h6>
//                    <p><strong>${remarks}</strong></p>
//                </div>
//            `;
//        }
//
//        reviewContent.innerHTML = html;
//
//        const confirmSaveButton = document.getElementById('confirmSaveButton');
//        if (confirmSaveButton) {
//            if (clientType.toLowerCase() === 'individual') {
//                confirmSaveButton.onclick = submitIndividualFormFromReview;
//            } else {
//                confirmSaveButton.onclick = proceedToBusinessFormFromReview;
//            }
//        }
//    }
//
//    function populateBusinessReviewWithBasicInfo() {
//        const reviewContent = document.getElementById('reviewContent');
//        if (!reviewContent) return;
//
//        const basicFormData = new FormData(clientBasicForm);
//        const clientType = document.getElementById('id_client_type').value;
//        const businessStructure = basicFormData.get('business_structure');
//
//        const assignedCaField = document.getElementById('id_assigned_ca');
//        const assignedCaDisplay = assignedCaField ? assignedCaField.options[assignedCaField.selectedIndex]?.text || 'N/A' : 'N/A';
//
//        let html = `
//            <div class="col-12">
//                <h6 class="border-bottom pb-2 mb-3">Basic Information</h6>
//            </div>
//            <div class="col-md-6">
//                <table class="table table-sm table-borderless">
//                    <tr>
//                        <td class="text-muted" style="width: 40%">Client Name:</td>
//                        <td><strong>${basicFormData.get('client_name') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">Primary Contact:</td>
//                        <td><strong>${basicFormData.get('primary_contact_name') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">PAN No:</td>
//                        <td><strong>${basicFormData.get('pan_no') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">Email:</td>
//                        <td><strong>${basicFormData.get('email') || 'N/A'}</strong></td>
//                    </tr>
//                </table>
//            </div>
//            <div class="col-md-6">
//                <table class="table table-sm table-borderless">
//                    <tr>
//                        <td class="text-muted">Client Type:</td>
//                        <td><strong>${clientType || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">Business Structure:</td>
//                        <td><strong>${businessStructure || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">Contact No:</td>
//                        <td><strong>${basicFormData.get('phone_number') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">Assigned CA/Article:</td>
//                        <td><strong>${assignedCaDisplay}</strong></td>
//                    </tr>
//                </table>
//            </div>
//            <div class="col-12 mt-3">
//                <table class="table table-sm table-borderless">
//                    <tr>
//                        <td class="text-muted" style="width: 15%">Address Line 1:</td>
//                        <td><strong>${basicFormData.get('address_line1') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">City:</td>
//                        <td><strong>${basicFormData.get('city') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">State:</td>
//                        <td><strong>${basicFormData.get('state') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">Postal Code:</td>
//                        <td><strong>${basicFormData.get('postal_code') || 'N/A'}</strong></td>
//                    </tr>
//                    <tr>
//                        <td class="text-muted">Country:</td>
//                        <td><strong>${basicFormData.get('country') || 'N/A'}</strong></td>
//                    </tr>
//                </table>
//            </div>
//        `;
//
//        html += populateBusinessStructureDetails();
//
//        const remarks = basicFormData.get('remarks');
//        if (remarks) {
//            html += `
//                <div class="col-12 mt-3">
//                    <h6 class="border-bottom pb-2 mb-3">Remarks</h6>
//                    <p><strong>${remarks}</strong></p>
//                </div>
//            `;
//        }
//
//        reviewContent.innerHTML = html;
//    }
//
//    function populateBusinessStructureDetails() {
//        const businessForm = document.querySelector('#businessStructureDetailsForm');
//        if (!businessForm) return '';
//
//        const businessStructureInput = document.querySelector('input[name="business_structure"]');
//        const businessStructure = businessStructureInput ? businessStructureInput.value : 'Unknown';
//
//        let html = `
//            <div class="col-12 mt-4">
//                <h6 class="border-bottom pb-2 mb-3">${businessStructure} Details</h6>
//            </div>
//        `;
//
//        const fields = businessForm.querySelectorAll('input, select, textarea');
//        let fieldData = [];
//
//        fields.forEach(field => {
//            if (field.name && field.type !== 'file' && field.type !== 'submit' && field.type !== 'button' &&
//                field.name !== 'business_structure' && field.name !== 'csrfmiddlewaretoken') {
//
//                let value = '';
//                let displayName = '';
//
//                if (field.type === 'checkbox') {
//                    value = field.checked ? 'Yes' : 'No';
//                } else if (field.tagName === 'SELECT' && field.multiple) {
//                    value = Array.from(field.selectedOptions).map(opt => opt.text).join(', ');
//                } else if (field.type === 'file') {
//                    value = field.files.length > 0 ? field.files[0].name : 'No file selected';
//                } else {
//                    value = field.value || 'N/A';
//                }
//
//                if (value && value !== 'N/A' && value !== 'No file selected') {
//                    displayName = field.name.replace(/_/g, ' ')
//                        .replace(/(llp|opc|huf|cin|udyam)/gi, match => match.toUpperCase())
//                        .replace(/\b\w/g, l => l.toUpperCase())
//                        .replace(/Id\b/g, 'ID')
//                        .replace(/No\b/g, 'No.')
//                        .replace(/S8\b/g, 'S8')
//                        .replace(/\bUrl\b/g, 'URL');
//
//                    fieldData.push({ name: displayName, value: value });
//                }
//            }
//        });
//
//        if (fieldData.length > 0) {
//            const midPoint = Math.ceil(fieldData.length / 2);
//            const firstColumn = fieldData.slice(0, midPoint);
//            const secondColumn = fieldData.slice(midPoint);
//
//            html += `
//                <div class="col-md-6">
//                    <table class="table table-sm table-borderless">
//            `;
//
//            firstColumn.forEach(field => {
//                html += `
//                    <tr>
//                        <td class="text-muted" style="width: 50%">${field.name}:</td>
//                        <td><strong>${field.value}</strong></td>
//                    </tr>
//                `;
//            });
//
//            html += `
//                    </table>
//                </div>
//                <div class="col-md-6">
//                    <table class="table table-sm table-borderless">
//            `;
//
//            secondColumn.forEach(field => {
//                html += `
//                    <tr>
//                        <td class="text-muted" style="width: 50%">${field.name}:</td>
//                        <td><strong>${field.value}</strong></td>
//                    </tr>
//                `;
//            });
//
//            html += `
//                    </table>
//                </div>
//            `;
//        } else {
//            html += `
//                <div class="col-12">
//                    <div class="alert alert-warning">
//                        <i class="bi bi-exclamation-triangle me-2"></i>
//                        No business details found.
//                    </div>
//                </div>
//            `;
//        }
//
//        return html;
//    }
//
//    // --------- Save functions from review modal ----------
//    async function submitIndividualFormFromReview() {
//        hideModal('reviewModal');
//
//        try {
//            const formData = new FormData(clientBasicForm);
//            const res = await fetch(URLS.save_client_basic, {
//                method: 'POST',
//                body: formData,
//                headers: { 'X-CSRFToken': csrfToken, 'X-Requested-With': 'XMLHttpRequest' }
//            });
//            const data = await res.json();
//            if (data.success) {
//                if (data.redirect_to_complete && data.client_type && data.client_type.toLowerCase() === 'individual') {
//                    await finalizeIndividualClient();
//                } else if (data.redirect_url) {
//                    window.location.href = data.redirect_url;
//                } else {
//                    showTemporaryAlert('Client saved successfully!', 'success');
//                }
//            } else {
//                handleFormErrors(data);
//            }
//        } catch (err) {
//            console.error('submitIndividualFormFromReview error:', err);
//            showTemporaryAlert('Network error occurred. Please try again.', 'error');
//        }
//    }
//
//    async function proceedToBusinessFormFromReview() {
//        hideModal('reviewModal');
//        await handleNextButtonClick();
//    }
//
//    async function submitBusinessStructureFormFromReview() {
//        hideModal('reviewModal');
//
//        const form = businessStructureForm.querySelector('#businessStructureDetailsForm');
//        if (form) {
//            await submitBusinessStructureForm(form);
//        }
//    }
//
//    async function finalizeIndividualClient() {
//        try {
//            const res = await fetch(URLS.save_individual_client, {
//                method: 'POST',
//                headers: {
//                    'X-CSRFToken': csrfToken,
//                    'X-Requested-With': 'XMLHttpRequest'
//                }
//            });
//
//            const data = await res.json();
//
//            if (data.success) {
//                showSuccessModal(data.client_id, data.client_name);
//            } else {
//                handleFormErrors(data);
//            }
//
//        } catch (err) {
//            console.error('finalizeIndividualClient error:', err);
//            showTemporaryAlert('Network error occurred while finalizing.', 'error');
//        }
//    }
//
//    // --------- initialize everything ----------
//    function initializeForm() {
//        currentState = 'basic';
//        clientBasicForm.style.display = 'block';
//        businessStructureForm.style.display = 'none';
//        businessStructureForm.innerHTML = '';
//        if (formTitle) {
//            formTitle.style.display = 'block';
//            formTitle.innerHTML = 'Client Basic Information <small class="text-muted">(<span class="text-danger">*</span> indicates required field)</small>';
//        }
//
//        setTimeout(() => {
//            initializeSelect2(clientBasicForm);
//            setupRealTimeValidation();
//            attachClientTypeChange();
//            toggleIndividualRequiredFields();
//            updateSubmitButtons();
//        }, 120);
//    }
//
//    // --------- clear form flow ----------
//    clearButton.addEventListener('click', function() {
//        showModal('clearFormModal');
//    });
//
//    confirmClearButton.addEventListener('click', function() {
//        destroySelect2();
//        fetch(URLS.clear_client_session, {
//            method: 'POST',
//            headers: { 'X-CSRFToken': csrfToken, 'X-Requested-With': 'XMLHttpRequest' }
//        }).finally(() => {
//            clientBasicForm.reset();
//            const selects = clientBasicForm.querySelectorAll('select');
//            selects.forEach(s => s.selectedIndex = 0);
//            const errorElements = clientBasicForm.querySelectorAll('.invalid-feedback');
//            errorElements.forEach(el => el.textContent = '');
//            const invalidFields = clientBasicForm.querySelectorAll('.is-invalid');
//            invalidFields.forEach(f => f.classList.remove('is-invalid'));
//
//            initializeForm();
//            updateSubmitButtons();
//            showTemporaryAlert('Form cleared successfully!', 'success');
//
//            hideModal('clearFormModal');
//        });
//    });
//
//    // Start
//    initializeForm();
//});