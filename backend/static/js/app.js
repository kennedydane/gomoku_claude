// Minimal HTMX-first JavaScript for Gomoku Game
// Only includes essential functionality that cannot be handled by HTMX

// Toast notification system (for user feedback)
function showToast(message, type = 'info', duration = 5000) {
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();
    const toastId = 'toast-' + Date.now();
    
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `toast align-items-center text-white bg-${getToastClass(type)} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="bi bi-${getToastIcon(type)} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: duration });
    bsToast.show();
    
    // Remove toast element after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1100';
    document.body.appendChild(container);
    return container;
}

function getToastClass(type) {
    const classes = {
        'success': 'success',
        'error': 'danger',
        'warning': 'warning',
        'info': 'primary',
        'danger': 'danger'
    };
    return classes[type] || 'primary';
}

function getToastIcon(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-triangle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle',
        'danger': 'exclamation-triangle'
    };
    return icons[type] || 'info-circle';
}

// HTMX Global Event Handlers (minimal essential functionality)
document.addEventListener('DOMContentLoaded', function() {
    // Enhanced HTMX error handling with user-friendly messages
    document.addEventListener('htmx:responseError', function(event) {
        console.error('HTMX Error:', event.detail);
        
        // Show user-friendly error message
        const status = event.detail.xhr.status;
        let message = 'Something went wrong. Please try again.';
        
        if (status === 403) {
            message = 'Access denied. Please check your permissions.';
        } else if (status === 404) {
            message = 'Resource not found.';
        } else if (status >= 500) {
            message = 'Server error. Please try again later.';
        }
        
        showToast(message, 'error');
    });
    
    // Auto-initialize Bootstrap tooltips after HTMX swaps
    document.addEventListener('htmx:afterSwap', function(event) {
        // Re-initialize any tooltips in the swapped content
        const tooltips = event.target.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(tooltip => {
            new bootstrap.Tooltip(tooltip);
        });
        
        // Check for success messages in response
        const target = event.target;
        if (target.dataset.successMessage) {
            showToast(target.dataset.successMessage, 'success');
        }
        
        // Play click sound for successful move placements
        if (event.target.classList.contains('board-intersection') || 
            event.target.closest('.board-intersection')) {
            // Check if audio function is available (defined in dashboard)
            if (typeof window.playStoneClickSound === 'function') {
                window.playStoneClickSound();
            }
        }
    });
    
    // Loading indicators for form submissions
    document.addEventListener('htmx:beforeRequest', function(event) {
        const element = event.target;
        if (element.tagName === 'FORM' || element.tagName === 'BUTTON') {
            const submitBtn = element.tagName === 'BUTTON' ? element : element.querySelector('[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<div class="spinner-border spinner-border-sm me-1" role="status"><span class="visually-hidden">Loading...</span></div> Loading...';
                
                // Reset on completion
                document.addEventListener('htmx:afterRequest', function resetBtn(resetEvent) {
                    if (resetEvent.target === element) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalText;
                        document.removeEventListener('htmx:afterRequest', resetBtn);
                    }
                }, { once: false });
            }
        }
    });
});

// Keyboard shortcuts (optional enhancement)
document.addEventListener('keydown', function(event) {
    // Press 'Escape' to close modals
    if (event.key === 'Escape') {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) modalInstance.hide();
        });
    }
});

// Export only necessary functions for global access
window.showToast = showToast;