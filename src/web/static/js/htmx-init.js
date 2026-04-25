/**
 * HTMX initialization and configuration for CGM Insights.
 */

// Configure HTMX defaults
document.addEventListener('DOMContentLoaded', function() {
    // Show loading indicator on requests
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'flex';
        }
    });

    // Hide loading indicator after requests
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
    });

    // Handle errors
    document.body.addEventListener('htmx:responseError', function(evt) {
        const errorContainer = document.getElementById('error-container');
        const errorText = document.getElementById('error-text');

        if (errorContainer && errorText) {
            try {
                const response = JSON.parse(evt.detail.xhr.responseText);
                errorText.textContent = response.detail || 'An error occurred. Please try again.';
            } catch (e) {
                errorText.textContent = 'An error occurred. Please try again.';
            }
            errorContainer.style.display = 'block';
        }
    });

    // Hide errors before new requests
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        const errorContainer = document.getElementById('error-container');
        if (errorContainer) {
            errorContainer.style.display = 'none';
        }
    });
});

// Show loading indicator on form submit
function showLoading() {
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'flex';
    }
}

// Hide loading indicator
function hideLoading() {
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
    }
}

// Show error message
function showError(message) {
    const errorContainer = document.getElementById('error-container');
    const errorText = document.getElementById('error-text');

    if (errorContainer && errorText) {
        errorText.textContent = message;
        errorContainer.style.display = 'block';
    }
}

// Clear error message
function clearError() {
    const errorContainer = document.getElementById('error-container');
    if (errorContainer) {
        errorContainer.style.display = 'none';
    }
}