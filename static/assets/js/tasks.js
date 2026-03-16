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

    // Initialize Select2 for client filter (searchable)
    $('#clientFilter').select2({
        placeholder: 'Search Client Name...',
        allowClear: true,
        width: '100%',
        minimumInputLength: 1, // Start searching after 1 character
        ajax: {
            url: '/clients/search/',
            dataType: 'json',
            delay: 300,
            data: function (params) {
                return {
                    q: params.term
                };
            },
            processResults: function (data) {
                // Add "All Clients" option at the beginning
                const allClientsOption = {id: '', text: 'All Clients'};

                // Transform the data based on format
                let results = [];

                if (Array.isArray(data)) {
                    if (data.length > 0) {
                        if (data[0].text !== undefined) {
                            // Format: [{id: 1, text: "Name"}, ...]
                            results = data;
                        } else if (data[0].client_name !== undefined) {
                            // Format: [{id: 1, client_name: "Name"}, ...]
                            results = data.map(item => ({
                                id: item.id,
                                text: item.client_name
                            }));
                        }
                    }
                }

                return {
                    results: [allClientsOption, ...results]
                };
            },
            cache: true
        }
    });

    // Preselect value from URL parameter on page load
    var urlParams = new URLSearchParams(window.location.search);
    var clientParam = urlParams.get('client');
    if (clientParam) {
        // Create a static option for the preselected client
        var option = new Option(
            $('#clientFilter option[value="' + clientParam + '"]').text() || 'Selected Client',
            clientParam,
            true,
            true
        );
        $('#clientFilter').append(option).trigger('change');
    }

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


//Add JS to Show Date Range Inputs
document.addEventListener("DOMContentLoaded", function () {

    const dueFilter = document.getElementById("dueFilter");
    const dueFromWrapper = document.getElementById("dueFromWrapper");
    const dueToWrapper = document.getElementById("dueToWrapper");

    function toggleDueRange() {
        if (!dueFilter) return;

        if (dueFilter.value === "range") {
            dueFromWrapper.style.display = "block";
            dueToWrapper.style.display = "block";
        } else {
            dueFromWrapper.style.display = "none";
            dueToWrapper.style.display = "none";
        }
    }

    toggleDueRange();
    dueFilter.addEventListener("change", toggleDueRange);

});

//Prevent Invalid Date Range (Frontend)
// Custom Validation for Due Date Range (Instant)
document.addEventListener("DOMContentLoaded", function () {

    const dueFrom = document.querySelector("input[name='due_from']");
    const dueTo = document.querySelector("input[name='due_to']");

    if (!dueFrom || !dueTo) return;

    // When user edits Due From
    dueFrom.addEventListener("input", function () {

        if (dueTo.value && dueFrom.value > dueTo.value) {

            const formattedDate = new Date(dueTo.value).toLocaleDateString();

            dueFrom.setCustomValidity(
                "Due From date cannot be after Due To date (" + formattedDate + ")."
            );

            dueFrom.reportValidity(); // show message instantly

        } else {
            dueFrom.setCustomValidity("");
        }

    });

    // When user edits Due To
    dueTo.addEventListener("input", function () {

        if (dueFrom.value && dueTo.value < dueFrom.value) {

            const formattedDate = new Date(dueFrom.value).toLocaleDateString();

            dueTo.setCustomValidity(
                "Due To date cannot be before Due From date (" + formattedDate + ")."
            );

            dueTo.reportValidity(); // show message instantly

        } else {
            dueTo.setCustomValidity("");
        }

    });

});