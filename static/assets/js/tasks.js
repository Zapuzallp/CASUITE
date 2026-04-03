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
// Due Date Filter Validations
document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("taskFilterForm");
    if (!form) return;

    form.addEventListener("submit", function (e) {

        const dueFilter = document.getElementById("dueFilter").value;
        const fromDate = document.querySelector("[name='due_from']").value;
        const toDate = document.querySelector("[name='due_to']").value;

        //only when range selected
        if (dueFilter === "range") {

            if(fromDate  && toDate && fromDate > toDate ) {
                e.preventDefault();

                Swal.fire({
                    icon: 'error',
                    title: 'Invalid Date Range',
                    text: 'From Date cannot be greater than To Date',
                    confirmButtonColor: '#d33'
                });

                return
            }
            // both empty
            if (!fromDate && !toDate)  {
                e.preventDefault();

                Swal.fire({
                    icon: 'warning',
                    title: 'Missing Dates',
                    text: 'Please select at least one date'
                });

                return
            }
            // only one date (THIS WAS MISSING)
            if ((fromDate && !toDate) || (!fromDate && toDate)) {
                e.preventDefault();
                Swal.fire({
                    icon: 'warning',
                    title: 'Incomplete Date Range',
                    text: 'Please select both From Date and To Date'
                });
                return;
            }

            // invalid range
            if (fromDate > toDate) {
                e.preventDefault();
                Swal.fire({
                    icon: 'error',
                    title: 'Invalid Date Range',
                    text: 'From Date cannot be greater than To Date',
                    confirmButtonColor: '#d33'
                });
                return;
            }
        }
    });
});

// Delete Task Modal Handler
document.addEventListener("DOMContentLoaded", function () {

    const deleteModal = document.getElementById("deleteTaskModal");

    if (deleteModal) {

        deleteModal.addEventListener("show.bs.modal", function (event) {

            const button = event.relatedTarget;

            const deleteUrl = button.getAttribute("data-url");
            const taskTitle = button.getAttribute("data-title");

            const form = document.getElementById("deleteTaskForm");
            const title = document.getElementById("deleteTaskTitle");

            form.action = deleteUrl;
            title.textContent = taskTitle;

        });

    }

});