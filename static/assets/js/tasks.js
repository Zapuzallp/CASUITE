$(document).ready(function () {
    // Client Select Model Select2
    $('#clientSelector').empty();

    $('#clientSelector').select2({
        dropdownParent: $('#selectClientModal'),
        placeholder: 'Client Name || PAN Number || Prospect',
        width: '100%',
        minimumInputLength: 0,
        ajax: {
            url: '/clients/search/',
            dataType: 'json',
            delay: 300,
            data: function (params) {
                return { q: params.term };
            },
            processResults: function (data) {
                return { results: data };
            }
        }
    });

    // Listen for change event on Select2
    $('#clientSelector').on('change', function () {
        const clientId = $(this).val();
        if (clientId) {
            $('#btnProceedTask').prop('disabled', false);
        } else {
            $('#btnProceedTask').prop('disabled', true);
        }
    });

    // Handle Proceed Button Click
    $('#btnProceedTask').on('click', function () {
        const clientId = $('#clientSelector').val();
        if (clientId) {
            // Construct URL: /client/ID/create-task/
            // Note: Ensure this matches your urls.py pattern exactly
            const url = `/client/${clientId}/create-task/`;
            window.location.href = url;
        }
    });

    // Reset modal when closed
    $('#selectClientModal').on('hidden.bs.modal', function () {
        $('#clientSelector').val(null).trigger('change');
        $('#btnProceedTask').prop('disabled', true);
    });

    // Initialize Select2 for consultancy filter
    $('.js-consultancy-select').select2({
    width: '100%',
    placeholder: "Select Consultancy Type",
    allowClear: true
    });

    function toggleConsultancyFilter() {
        const serviceType = $('select[name="service_type"]').val();

        if (serviceType === "Consultancy") {   //    your actual DB value
        $('#consultancyFilterWrapper').show();
        } else {
           $('#consultancyFilterWrapper').hide();
           $('#consultancyFilter').val(null).trigger('change');
        }
    }

    // Run on page load
    toggleConsultancyFilter();

    // Run when service type changes
    $('select[name="service_type"]').on('change', function () {
        toggleConsultancyFilter();
    });

});