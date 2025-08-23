// Optimized HTMX-first JavaScript for Gomoku Game
// Performance optimizations: debouncing, throttling, lazy loading

// Performance utilities
const perf = {
    // Debounce function calls to prevent excessive executions
    debounce: (func, wait, immediate) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func(...args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func(...args);
        };
    },

    // Throttle function calls to limit execution frequency
    throttle: (func, limit) => {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // Batch DOM operations using requestAnimationFrame
    batchDOMUpdates: (callback) => {
        if (window.requestAnimationFrame) {
            requestAnimationFrame(callback);
        } else {
            setTimeout(callback, 16); // fallback for older browsers
        }
    },

    // Check if element is in viewport (for lazy loading)
    isInViewport: (element) => {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }
};

// Optimized toast notification system with queuing and batching
const toastSystem = {
    queue: [],
    isProcessing: false,
    maxConcurrent: 3,
    
    show: (message, type = 'info', duration = 5000) => {
        toastSystem.queue.push({ message, type, duration });
        toastSystem.processQueue();
    },
    
    processQueue: perf.throttle(() => {
        if (toastSystem.isProcessing || toastSystem.queue.length === 0) return;
        
        toastSystem.isProcessing = true;
        const toastsToShow = toastSystem.queue.splice(0, toastSystem.maxConcurrent);
        
        perf.batchDOMUpdates(() => {
            toastsToShow.forEach(toast => {
                toastSystem.createToast(toast.message, toast.type, toast.duration);
            });
            toastSystem.isProcessing = false;
            
            // Continue processing queue if there are more items
            if (toastSystem.queue.length > 0) {
                setTimeout(() => toastSystem.processQueue(), 100);
            }
        });
    }, 100),
    
    createToast: (message, type, duration) => {
        const toastContainer = document.querySelector('.toast-container') || toastSystem.createContainer();
        const toastId = 'toast-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast align-items-center text-white bg-${toastSystem.getToastClass(type)} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-${toastSystem.getToastIcon(type)} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { delay: duration });
        bsToast.show();
        
        // Clean up after toast is hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    },
    
    createContainer: () => {
        const container = document.createElement('div');
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1100';
        document.body.appendChild(container);
        return container;
    },
    
    getToastClass: (type) => {
        const classes = {
            'success': 'success',
            'error': 'danger',
            'warning': 'warning',
            'info': 'primary',
            'danger': 'danger'
        };
        return classes[type] || 'primary';
    },
    
    getToastIcon: (type) => {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle',
            'danger': 'exclamation-triangle'
        };
        return icons[type] || 'info-circle';
    }
};

// Optimized HTMX event handlers with performance improvements
const htmxOptimizations = {
    init: () => {
        // Throttled error handler to prevent spam
        const throttledErrorHandler = perf.throttle((event) => {
            console.error('HTMX Error:', event.detail);
            
            const status = event.detail.xhr.status;
            let message = 'Something went wrong. Please try again.';
            
            if (status === 403) {
                message = 'Access denied. Please check your permissions.';
            } else if (status === 404) {
                message = 'Resource not found.';
            } else if (status >= 500) {
                message = 'Server error. Please try again later.';
            }
            
            toastSystem.show(message, 'error');
        }, 1000); // Throttle to max 1 error toast per second
        
        document.addEventListener('htmx:responseError', throttledErrorHandler);
        
        // Optimized after-swap handler with batched operations
        document.addEventListener('htmx:afterSwap', perf.throttle((event) => {
            perf.batchDOMUpdates(() => {
                // Re-initialize tooltips in swapped content
                const tooltips = event.target.querySelectorAll('[data-bs-toggle="tooltip"]');
                tooltips.forEach(tooltip => {
                    if (!tooltip.hasAttribute('data-tooltip-initialized')) {
                        new bootstrap.Tooltip(tooltip);
                        tooltip.setAttribute('data-tooltip-initialized', 'true');
                    }
                });
                
                // Check for success messages
                const target = event.target;
                if (target.dataset.successMessage) {
                    toastSystem.show(target.dataset.successMessage, 'success');
                }
                
                // Optimized stone click sound with audio object reuse
                if (event.target.classList.contains('board-intersection') || 
                    event.target.closest('.board-intersection')) {
                    if (typeof window.playStoneClickSound === 'function') {
                        window.playStoneClickSound();
                    }
                }
            });
        }, 50)), // Throttle to max 20 times per second
        
        // Optimized loading indicators with debounced reset
        document.addEventListener('htmx:beforeRequest', (event) => {
            const element = event.target;
            if (element.tagName === 'FORM' || element.tagName === 'BUTTON') {
                const submitBtn = element.tagName === 'BUTTON' ? element : element.querySelector('[type="submit"]');
                if (submitBtn && !submitBtn.hasAttribute('data-loading')) {
                    submitBtn.setAttribute('data-loading', 'true');
                    submitBtn.disabled = true;
                    const originalText = submitBtn.innerHTML;
                    submitBtn.innerHTML = '<div class="spinner-border spinner-border-sm me-1" role="status"><span class="visually-hidden">Loading...</span></div> Loading...';
                    
                    // Debounced reset function to prevent flickering on fast responses
                    const debouncedReset = perf.debounce(() => {
                        if (submitBtn.hasAttribute('data-loading')) {
                            submitBtn.removeAttribute('data-loading');
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = originalText;
                        }
                    }, 100);
                    
                    const resetHandler = (resetEvent) => {
                        if (resetEvent.target === element) {
                            debouncedReset();
                            document.removeEventListener('htmx:afterRequest', resetHandler);
                        }
                    };
                    document.addEventListener('htmx:afterRequest', resetHandler);
                }
            }
        })
    }
};

// Optimized keyboard shortcuts with event delegation
const keyboardOptimizations = {
    init: () => {
        // Use a single event listener with delegation for better performance
        document.addEventListener('keydown', perf.throttle((event) => {
            switch (event.key) {
                case 'Escape':
                    keyboardOptimizations.closeModals();
                    break;
                case 'r':
                    if (event.ctrlKey || event.metaKey) {
                        event.preventDefault();
                        keyboardOptimizations.refreshCurrentGame();
                    }
                    break;
            }
        }, 100)); // Throttle keyboard events
    },
    
    closeModals: () => {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) modalInstance.hide();
        });
    },
    
    refreshCurrentGame: () => {
        // Refresh current game board if available
        const gameBoard = document.querySelector('[sse-swap="game_move"]');
        if (gameBoard) {
            htmx.trigger(gameBoard, 'refresh');
        }
    }
};

// Lazy loading for non-critical elements
const lazyLoader = {
    init: () => {
        if ('IntersectionObserver' in window) {
            lazyLoader.setupIntersectionObserver();
        } else {
            // Fallback for older browsers
            lazyLoader.loadAllLazy();
        }
    },
    
    setupIntersectionObserver: () => {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    lazyLoader.loadElement(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { rootMargin: '50px' });
        
        document.querySelectorAll('[data-lazy-load]').forEach(element => {
            observer.observe(element);
        });
    },
    
    loadElement: (element) => {
        const src = element.dataset.lazySrc;
        if (src && element.tagName === 'IMG') {
            element.src = src;
            element.removeAttribute('data-lazy-src');
        }
        
        const bgImage = element.dataset.lazyBgImage;
        if (bgImage) {
            element.style.backgroundImage = `url(${bgImage})`;
            element.removeAttribute('data-lazy-bg-image');
        }
        
        element.removeAttribute('data-lazy-load');
    },
    
    loadAllLazy: () => {
        document.querySelectorAll('[data-lazy-load]').forEach(element => {
            lazyLoader.loadElement(element);
        });
    }
};

// Initialize optimizations when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    htmxOptimizations.init();
    keyboardOptimizations.init();
    lazyLoader.init();
    
    // Performance monitoring
    if ('performance' in window) {
        window.addEventListener('load', () => {
            setTimeout(() => {
                const perfData = performance.getEntriesByType('navigation')[0];
                if (perfData) {
                    console.log('Page load performance:', {
                        domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
                        loadComplete: perfData.loadEventEnd - perfData.loadEventStart,
                        totalLoadTime: perfData.loadEventEnd - perfData.navigationStart
                    });
                }
            }, 0);
        });
    }
});

// Export optimized toast system for global use
window.showToast = toastSystem.show;
window.perf = perf;