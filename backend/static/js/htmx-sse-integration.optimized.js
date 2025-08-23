/**
 * Optimized HTMX SSE Integration Layer
 * Performance improvements: element caching, batched operations, efficient DOM updates
 */

// Performance optimization utilities
const htmxOptimizations = {
    // Element cache to avoid repeated DOM queries
    elementCache: new Map(),
    
    // Batch DOM operations for better performance
    pendingUpdates: new Map(),
    updateScheduled: false,
    
    // Throttled functions
    throttledReregistration: null,
    throttledMutationHandling: null,
    
    // Performance counters
    metrics: {
        elementsRegistered: 0,
        updatesProcessed: 0,
        cacheHits: 0,
        cacheMisses: 0
    }
};

// Wait for dependencies with timeout
function waitForDependencies() {
    return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            reject(new Error('Timeout waiting for HTMX/SSE Manager'));
        }, 10000);
        
        const checkDependencies = () => {
            if (typeof htmx !== 'undefined' && typeof sseManager !== 'undefined') {
                clearTimeout(timeout);
                resolve();
            } else {
                setTimeout(checkDependencies, 100);
            }
        };
        
        checkDependencies();
    });
}

// Initialize optimized HTMX SSE integration
async function initializeOptimizedHTMXSSEIntegration() {
    try {
        await waitForDependencies();
        console.log('[Optimized HTMX SSE Integration] Initializing...');
        
        const integration = new OptimizedHTMXSSEIntegration();
        await integration.initialize();
        
    } catch (error) {
        console.error('[Optimized HTMX SSE Integration] Initialization failed:', error);
    }
}

class OptimizedHTMXSSEIntegration {
    constructor() {
        this.sseElements = new Map();
        this.mutationObserver = null;
        this.intersectionObserver = null;
        this.reregistrationTimeout = null;
        this.lastRegistration = 0;
        
        // Performance constants
        this.REREGISTRATION_DELAY = 100;
        this.MUTATION_THROTTLE = 250;
        this.UPDATE_BATCH_SIZE = 10;
        this.CACHE_TTL = 60000; // 1 minute cache TTL
        
        // Bind methods
        this.registerSSEElements = this.registerSSEElements.bind(this);
        this.handleSSEEvent = this.handleSSEEvent.bind(this);
        this.throttledReregistration = this.throttle(this.registerSSEElements, this.REREGISTRATION_DELAY);
        this.throttledMutationHandling = this.throttle(this.handleMutations.bind(this), this.MUTATION_THROTTLE);
    }

    // Performance utility functions
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    async initialize() {
        this.disableDefaultHTMXSSE();
        await this.registerSSEElements();
        this.setupSSEListeners();
        this.setupOptimizedContentMonitoring();
        
        console.log('[Optimized HTMX SSE Integration] Initialization complete');
        
        // Dispatch ready event with metrics
        document.dispatchEvent(new CustomEvent('htmx:sse:ready', {
            detail: { 
                registeredElements: this.sseElements.size,
                sseManager: window.sseManager,
                metrics: htmxOptimizations.metrics
            }
        }));
    }

    /**
     * Optimized SSE element registration with caching and batching
     */
    async registerSSEElements() {
        const registrationStart = performance.now();
        
        // Clear existing registrations
        this.sseElements.clear();
        htmxOptimizations.elementCache.clear();
        
        // Find elements in batches for better performance
        const elements = document.querySelectorAll('[sse-swap]');
        
        if (elements.length === 0) {
            console.log(`[Optimized HTMX SSE Integration] No SSE elements found`);
            return;
        }
        
        const batches = this.createBatches(Array.from(elements), this.UPDATE_BATCH_SIZE);
        let registeredCount = 0;
        
        // Process batches with requestAnimationFrame for better performance
        for (const batch of batches) {
            await new Promise(resolve => {
                requestAnimationFrame(() => {
                    batch.forEach(element => {
                        if (this.registerSingleElement(element)) {
                            registeredCount++;
                        }
                    });
                    resolve();
                });
            });
        }
        
        const registrationTime = performance.now() - registrationStart;
        htmxOptimizations.metrics.elementsRegistered += registeredCount;
        this.lastRegistration = Date.now();
        
        console.log(`[Optimized HTMX SSE Integration] Registered ${registeredCount} elements in ${registrationTime.toFixed(2)}ms`);
    }

    /**
     * Register a single element with caching
     */
    registerSingleElement(element) {
        try {
            const swapEvent = element.getAttribute('sse-swap');
            if (!swapEvent) return false;
            
            const target = element.getAttribute('hx-target') || element;
            const swapMethod = element.getAttribute('hx-swap') || 'innerHTML';
            
            // Cache element reference
            const elementId = element.id || `sse-element-${Math.random().toString(36).substr(2, 9)}`;
            if (!element.id) element.id = elementId;
            
            htmxOptimizations.elementCache.set(elementId, {
                element,
                timestamp: Date.now()
            });
            
            // Mark as registered
            element.setAttribute('data-sse-registered', 'true');
            
            if (!this.sseElements.has(swapEvent)) {
                this.sseElements.set(swapEvent, []);
            }
            
            const targetElement = typeof target === 'string' ? document.querySelector(target) : target;
            
            this.sseElements.get(swapEvent).push({
                elementId,
                element,
                target: targetElement,
                swapMethod,
                swapEvent,
                lastUpdate: 0
            });
            
            return true;
        } catch (error) {
            console.error('[Optimized HTMX SSE Integration] Failed to register element:', error);
            return false;
        }
    }

    /**
     * Create batches from array for better performance
     */
    createBatches(array, batchSize) {
        const batches = [];
        for (let i = 0; i < array.length; i += batchSize) {
            batches.push(array.slice(i, i + batchSize));
        }
        return batches;
    }

    /**
     * Handle SSE events with batching and performance optimization
     */
    handleSSEEvent(eventType, data) {
        const registrations = this.sseElements.get(eventType) || [];
        
        if (registrations.length === 0) {
            return;
        }

        // Batch updates for better performance
        const updateBatches = this.createBatches(registrations, this.UPDATE_BATCH_SIZE);
        
        updateBatches.forEach((batch, index) => {
            // Stagger batch processing to avoid blocking
            setTimeout(() => {
                requestAnimationFrame(() => {
                    batch.forEach(registration => {
                        if (this.shouldUpdateElement(registration)) {
                            this.performOptimizedHTMXUpdate(registration, data);
                        }
                    });
                });
            }, index * 10); // 10ms stagger
        });
    }

    /**
     * Check if element should be updated (rate limiting, visibility)
     */
    shouldUpdateElement(registration) {
        const now = Date.now();
        
        // Rate limiting: max 10 updates per second per element
        if (now - registration.lastUpdate < 100) {
            return false;
        }
        
        // Check if element is still in DOM
        if (!document.contains(registration.element)) {
            return false;
        }
        
        // Check if element is visible (basic optimization)
        if (registration.element.offsetParent === null && 
            registration.element.style.display !== 'none') {
            // Element might be hidden, skip update
            return false;
        }
        
        registration.lastUpdate = now;
        return true;
    }

    /**
     * Perform optimized HTMX update with error handling and performance monitoring
     */
    performOptimizedHTMXUpdate(registration, data) {
        const { elementId, element, target, swapMethod, swapEvent } = registration;
        const updateStart = performance.now();
        
        try {
            // Get cached element or refresh cache
            let cachedElement = htmxOptimizations.elementCache.get(elementId);
            if (!cachedElement || Date.now() - cachedElement.timestamp > this.CACHE_TTL) {
                htmxOptimizations.metrics.cacheMisses++;
                cachedElement = { element, timestamp: Date.now() };
                htmxOptimizations.elementCache.set(elementId, cachedElement);
            } else {
                htmxOptimizations.metrics.cacheHits++;
            }
            
            const updateTarget = target || element;
            if (!updateTarget || !document.contains(updateTarget)) {
                console.warn(`[Optimized HTMX SSE Integration] No valid target for ${swapEvent}`);
                return;
            }

            // Perform DOM update with optimizations
            this.performDOMUpdate(updateTarget, data, swapMethod);
            
            // Update metrics
            htmxOptimizations.metrics.updatesProcessed++;
            const updateTime = performance.now() - updateStart;
            
            if (updateTime > 16) { // Warn if update takes longer than 1 frame (16ms)
                console.warn(`[Optimized HTMX SSE Integration] Slow update detected: ${updateTime.toFixed(2)}ms for ${swapEvent}`);
            }
            
        } catch (error) {
            console.error(`[Optimized HTMX SSE Integration] Failed to update element:`, error);
        }
    }

    /**
     * Optimized DOM update with requestAnimationFrame
     */
    performDOMUpdate(target, data, swapMethod) {
        // Use requestAnimationFrame for smooth updates
        requestAnimationFrame(() => {
            try {
                switch (swapMethod) {
                    case 'innerHTML':
                        target.innerHTML = data;
                        break;
                        
                    case 'outerHTML':
                        target.outerHTML = data;
                        this.throttledReregistration();
                        break;
                        
                    case 'beforeend':
                        target.insertAdjacentHTML('beforeend', data);
                        break;
                        
                    case 'afterend':
                        target.insertAdjacentHTML('afterend', data);
                        break;
                        
                    case 'beforebegin':
                        target.insertAdjacentHTML('beforebegin', data);
                        break;
                        
                    case 'afterbegin':
                        target.insertAdjacentHTML('afterbegin', data);
                        break;
                        
                    case 'textContent':
                        target.textContent = data;
                        break;
                        
                    default:
                        target.innerHTML = data;
                }

                // Process HTMX elements in new content
                if (typeof htmx.process === 'function') {
                    htmx.process(target);
                }

                // Dispatch update event
                target.dispatchEvent(new CustomEvent('htmx:sse:updated', {
                    detail: { target, data },
                    bubbles: true
                }));
                
            } catch (error) {
                console.error(`[Optimized HTMX SSE Integration] DOM update failed:`, error);
            }
        });
    }

    /**
     * Setup optimized SSE event listeners
     */
    setupSSEListeners() {
        const eventTypes = ['game_move', 'dashboard_update', 'dashboard_game_update', 'friends_update'];
        
        eventTypes.forEach(eventType => {
            document.addEventListener(`sse:${eventType}`, (event) => {
                const { data } = event.detail;
                this.handleSSEEvent(eventType, data);
            });
        });

        // Connection status listeners with UI updates
        document.addEventListener('sse:connected', () => {
            console.log('[Optimized HTMX SSE Integration] SSE connected');
            document.body.classList.add('sse-connected');
            document.body.classList.remove('sse-disconnected', 'sse-error');
        });

        document.addEventListener('sse:disconnected', () => {
            console.log('[Optimized HTMX SSE Integration] SSE disconnected');
            document.body.classList.add('sse-disconnected');
            document.body.classList.remove('sse-connected');
        });

        document.addEventListener('sse:error', (event) => {
            console.error('[Optimized HTMX SSE Integration] SSE error:', event.detail);
            document.body.classList.add('sse-error');
        });
    }

    /**
     * Disable default HTMX SSE to prevent conflicts
     */
    disableDefaultHTMXSSE() {
        const existingSSEElements = document.querySelectorAll('[sse-connect]');
        existingSSEElements.forEach(element => {
            const sseConnect = element.getAttribute('sse-connect');
            console.log(`[Optimized HTMX SSE Integration] Disabling default SSE connection:`, sseConnect);
            
            element.setAttribute('data-original-sse-connect', sseConnect);
            element.removeAttribute('sse-connect');
            
            // Remove hx-ext="sse" 
            const hxExt = element.getAttribute('hx-ext');
            if (hxExt === 'sse') {
                element.removeAttribute('hx-ext');
            } else if (hxExt && hxExt.includes('sse')) {
                const newExt = hxExt.split(',')
                    .map(ext => ext.trim())
                    .filter(ext => ext !== 'sse')
                    .join(',');
                if (newExt) {
                    element.setAttribute('hx-ext', newExt);
                } else {
                    element.removeAttribute('hx-ext');
                }
            }
        });
    }

    /**
     * Setup optimized content monitoring with IntersectionObserver
     */
    setupOptimizedContentMonitoring() {
        // HTMX after swap monitoring
        document.addEventListener('htmx:afterSwap', (event) => {
            const target = event.target;
            if (this.hasSSEElements(target)) {
                this.throttledReregistration();
            }
        });

        // Optimized MutationObserver with IntersectionObserver
        if (window.IntersectionObserver) {
            this.setupIntersectionObserver();
        }

        this.setupMutationObserver();
    }

    /**
     * Check if target has SSE elements
     */
    hasSSEElements(target) {
        if (target.hasAttribute && target.hasAttribute('sse-swap')) {
            return true;
        }
        if (target.querySelectorAll && target.querySelectorAll('[sse-swap]').length > 0) {
            return true;
        }
        return false;
    }

    /**
     * Setup intersection observer for viewport-based optimizations
     */
    setupIntersectionObserver() {
        this.intersectionObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const element = entry.target;
                if (entry.isIntersecting) {
                    element.classList.add('sse-visible');
                } else {
                    element.classList.remove('sse-visible');
                }
            });
        }, { rootMargin: '50px' });
    }

    /**
     * Setup optimized mutation observer
     */
    setupMutationObserver() {
        this.mutationObserver = new MutationObserver(this.throttledMutationHandling);
        this.mutationObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    /**
     * Handle mutations efficiently
     */
    handleMutations(mutations) {
        let shouldReregister = false;
        
        mutations.forEach(mutation => {
            if (mutation.type === 'childList' && !shouldReregister) {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1) { // Element node
                        if (this.hasSSEElements(node)) {
                            shouldReregister = true;
                            
                            // Add to intersection observer if available
                            if (this.intersectionObserver && node.hasAttribute('sse-swap')) {
                                this.intersectionObserver.observe(node);
                            }
                        }
                    }
                });
            }
        });
        
        if (shouldReregister) {
            this.throttledReregistration();
        }
    }

    /**
     * Cleanup resources
     */
    destroy() {
        if (this.mutationObserver) {
            this.mutationObserver.disconnect();
        }
        if (this.intersectionObserver) {
            this.intersectionObserver.disconnect();
        }
        if (this.reregistrationTimeout) {
            clearTimeout(this.reregistrationTimeout);
        }
        
        this.sseElements.clear();
        htmxOptimizations.elementCache.clear();
    }
}

// Initialize when dependencies are ready
document.addEventListener('DOMContentLoaded', initializeOptimizedHTMXSSEIntegration);

// Export for potential external use
window.OptimizedHTMXSSEIntegration = OptimizedHTMXSSEIntegration;