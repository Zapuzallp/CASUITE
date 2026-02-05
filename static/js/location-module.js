/**
 * Location Module - Shared between Web and Mobile Apps
 * Handles geolocation capture and reverse geocoding
 */

const LocationModule = {
    /**
     * Get user location and populate form fields
     * @param {string} latInput - ID of latitude input field
     * @param {string} longInput - ID of longitude input field  
     * @param {string} locationInput - ID of location name input field
     * @param {function} callback - Optional callback function
     */
    loadLocation: function(latInput, longInput, locationInput, callback) {
        if (!navigator.geolocation) {
            console.log("Geolocation not supported");
            if (callback) callback(false);
            return;
        }

        navigator.geolocation.getCurrentPosition(
            async function(pos) {
                const lat = pos.coords.latitude;
                const lng = pos.coords.longitude;

                // Only fill fields if we have valid coordinates
                if (lat && lng && !isNaN(lat) && !isNaN(lng)) {
                    document.getElementById(latInput).value = lat;
                    document.getElementById(longInput).value = lng;

                    try {
                        const res = await fetch(
                            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`
                        );
                        const data = await res.json();
                        document.getElementById(locationInput).value =
                            data.display_name || "Unknown Location";
                    } catch {
                        document.getElementById(locationInput).value = "Unknown Location";
                    }
                    
                    if (callback) callback(true);
                } else {
                    console.log("Invalid coordinates received");
                    if (callback) callback(false);
                }
            },
            function(error) {
                console.log("Location permission denied:", error);
                if (callback) callback(false);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000
            }
        );
    },

    /**
     * Setup form submission with location capture
     * @param {string} formId - ID of the form
     * @param {string} latInput - ID of latitude input field
     * @param {string} longInput - ID of longitude input field
     * @param {string} locationInput - ID of location name input field
     * @param {number} timeout - Timeout in milliseconds (default: 3000)
     */
    setupFormWithLocation: function(formId, latInput, longInput, locationInput, timeout = 3000) {
        const form = document.getElementById(formId);
        if (!form) return;

        let isProcessing = false;

        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Prevent multiple submissions
            if (isProcessing) return;
            isProcessing = true;
            
            // Disable the submit button to prevent multiple clicks
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.style.opacity = '0.6';
            }
            
            const latField = document.getElementById(latInput);
            const longField = document.getElementById(longInput);
            const locationField = document.getElementById(locationInput);
            
            let locationProcessed = false;
            
            // Set a timeout first
            const timeoutId = setTimeout(() => {
                if (!locationProcessed) {
                    locationProcessed = true;
                    // Remove empty fields and submit
                    if (latField && !latField.value) latField.remove();
                    if (longField && !longField.value) longField.remove();
                    if (locationField && !locationField.value) locationField.remove();
                    form.submit();
                }
            }, timeout);
            
            // Try to get location
            LocationModule.loadLocation(latInput, longInput, locationInput, function(success) {
                if (!locationProcessed) {
                    locationProcessed = true;
                    clearTimeout(timeoutId);
                    
                    // If location failed, remove empty fields
                    if (!success) {
                        if (latField && !latField.value) latField.remove();
                        if (longField && !longField.value) longField.remove();
                        if (locationField && !locationField.value) locationField.remove();
                    }
                    
                    form.submit();
                }
            });
        });
    }
};

// Make it available globally
window.LocationModule = LocationModule;