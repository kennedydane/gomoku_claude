/**
 * HTMX SSE Integration Layer
 * Bridges the centralized SSE manager with HTMX's SSE extension functionality
 */

// Wait for both HTMX and SSE Manager to be available
document.addEventListener('DOMContentLoaded', () => {
    if (typeof htmx === 'undefined') {
        console.error('[HTMX SSE Integration] HTMX not loaded');
        return;
    }

    if (typeof sseManager === 'undefined') {
        console.error('[HTMX SSE Integration] SSE Manager not loaded');
        return;
    }

    // Initialize HTMX SSE integration
    initializeHTMXSSEIntegration();
});

function initializeHTMXSSEIntegration() {
    console.log('[HTMX SSE Integration] Initializing...');

    // Store references to elements that need SSE updates
    const sseElements = new Map();

    /**
     * Register SSE elements and their swap configurations
     */
    function registerSSEElements() {
        // Find all elements with sse-swap attributes
        const elements = document.querySelectorAll('[sse-swap]');
        
        elements.forEach(element => {
            const swapEvent = element.getAttribute('sse-swap');
            const target = element.getAttribute('hx-target') || element;
            const swapMethod = element.getAttribute('hx-swap') || 'innerHTML';
            
            if (!sseElements.has(swapEvent)) {
                sseElements.set(swapEvent, []);
            }
            
            sseElements.get(swapEvent).push({
                element: element,
                target: typeof target === 'string' ? document.querySelector(target) : target,
                swapMethod: swapMethod,
                swapEvent: swapEvent
            });
            
            console.log(`[HTMX SSE Integration] Registered element for ${swapEvent}:`, element);
        });
    }

    /**
     * Handle SSE events and trigger HTMX updates
     */
    function handleSSEEvent(eventType, data) {
        const registrations = sseElements.get(eventType) || [];
        
        if (registrations.length === 0) {
            console.log(`[HTMX SSE Integration] No elements registered for ${eventType}`);
            return;
        }

        registrations.forEach(registration => {
            try {
                performHTMXUpdate(registration, data);
            } catch (error) {
                console.error(`[HTMX SSE Integration] Failed to update element for ${eventType}:`, error);
            }
        });
    }

    /**
     * Perform HTMX-style update on element
     */
    function performHTMXUpdate(registration, data) {
        const { element, target, swapMethod, swapEvent } = registration;
        
        // Ensure we have a valid target
        const updateTarget = target || element;
        if (!updateTarget) {
            console.warn(`[HTMX SSE Integration] No valid target for ${swapEvent}`);
            return;
        }

        console.log(`[HTMX SSE Integration] Updating ${swapEvent} via ${swapMethod}:`, updateTarget);

        // Handle different swap methods
        switch (swapMethod) {
            case 'innerHTML':
                updateTarget.innerHTML = data;
                break;
                
            case 'outerHTML':
                updateTarget.outerHTML = data;
                // Re-register elements since DOM changed
                setTimeout(registerSSEElements, 0);
                break;
                
            case 'beforeend':
                updateTarget.insertAdjacentHTML('beforeend', data);
                break;
                
            case 'afterend':
                updateTarget.insertAdjacentHTML('afterend', data);
                break;
                
            case 'beforebegin':
                updateTarget.insertAdjacentHTML('beforebegin', data);
                break;
                
            case 'afterbegin':
                updateTarget.insertAdjacentHTML('afterbegin', data);
                break;
                
            case 'textContent':
                updateTarget.textContent = data;
                break;
                
            default:
                // Default to innerHTML
                updateTarget.innerHTML = data;
        }

        // Trigger HTMX processing for any new elements
        if (typeof htmx.process === 'function') {
            htmx.process(updateTarget);
        }

        // Dispatch custom event for additional processing
        const updateEvent = new CustomEvent('htmx:sse:updated', {
            detail: {
                eventType: swapEvent,
                target: updateTarget,
                element: element,
                data: data
            },
            bubbles: true
        });
        updateTarget.dispatchEvent(updateEvent);
    }

    /**
     * Set up SSE event listeners
     */
    function setupSSEListeners() {
        // Listen for all supported SSE event types
        const eventTypes = ['game_move', 'dashboard_update', 'dashboard_game_update', 'friends_update'];
        
        eventTypes.forEach(eventType => {
            document.addEventListener(`sse:${eventType}`, (event) => {
                const { data } = event.detail;
                handleSSEEvent(eventType, data);
            });
        });

        // Connection status listeners
        document.addEventListener('sse:connected', () => {
            console.log('[HTMX SSE Integration] SSE connected');
            document.body.classList.add('sse-connected');
            document.body.classList.remove('sse-disconnected');
        });

        document.addEventListener('sse:disconnected', () => {
            console.log('[HTMX SSE Integration] SSE disconnected');
            document.body.classList.add('sse-disconnected');
            document.body.classList.remove('sse-connected');
        });

        document.addEventListener('sse:error', (event) => {
            console.error('[HTMX SSE Integration] SSE error:', event.detail);
            document.body.classList.add('sse-error');
        });
    }

    /**
     * Disable default HTMX SSE extension to prevent conflicts
     */
    function disableDefaultHTMXSSE() {
        // Find and remove existing sse-connect attributes to prevent conflicts
        const existingSSEElements = document.querySelectorAll('[sse-connect]');
        existingSSEElements.forEach(element => {
            const sseConnect = element.getAttribute('sse-connect');
            console.log(`[HTMX SSE Integration] Disabling default SSE connection:`, sseConnect);
            
            // Store the original for reference but remove to prevent conflicts
            element.setAttribute('data-original-sse-connect', sseConnect);
            element.removeAttribute('sse-connect');
            
            // Remove hx-ext="sse" if it's the only extension
            const hxExt = element.getAttribute('hx-ext');
            if (hxExt === 'sse') {
                element.removeAttribute('hx-ext');
            } else if (hxExt && hxExt.includes('sse')) {
                // Remove sse from the extension list
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
     * Monitor for dynamic content and re-register elements
     */
    function setupDynamicContentMonitoring() {
        // Watch for HTMX after swap events to re-register SSE elements
        document.addEventListener('htmx:afterSwap', () => {
            setTimeout(registerSSEElements, 0);
        });

        // Watch for general DOM changes
        const observer = new MutationObserver((mutations) => {
            let shouldReregister = false;
            
            mutations.forEach(mutation => {
                if (mutation.type === 'childList') {
                    // Check if any added nodes have sse-swap attributes
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1) { // Element node
                            if (node.hasAttribute && node.hasAttribute('sse-swap')) {
                                shouldReregister = true;
                            }
                            // Check descendants
                            if (node.querySelectorAll && node.querySelectorAll('[sse-swap]').length > 0) {
                                shouldReregister = true;
                            }
                        }
                    });
                }
            });
            
            if (shouldReregister) {
                setTimeout(registerSSEElements, 0);
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // Initialize the integration
    disableDefaultHTMXSSE();
    registerSSEElements();
    setupSSEListeners();
    setupDynamicContentMonitoring();

    console.log('[HTMX SSE Integration] Initialization complete');
    
    // Dispatch ready event
    document.dispatchEvent(new CustomEvent('htmx:sse:ready', {
        detail: { 
            registeredElements: sseElements.size,
            sseManager: window.sseManager
        }
    }));
}