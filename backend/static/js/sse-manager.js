/**
 * Centralized SSE Connection Manager
 * Eliminates multiple SSE connections by routing events through a single connection
 */
class SSEManager {
    constructor() {
        this.eventSource = null;
        this.isConnected = false;
        this.reconnectInterval = 5000; // 5 seconds
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.eventHandlers = new Map();
        this.debugMode = false;
    }

    /**
     * Initialize SSE connection for a user
     * @param {string} userId - The user ID for the channel
     * @param {boolean} debug - Enable debug logging
     */
    connect(userId, debug = false) {
        this.debugMode = debug;
        this.userId = userId;
        
        if (this.isConnected) {
            this.log('SSE already connected, skipping');
            return;
        }

        const channel = `user-${userId}`;
        const url = `/api/v1/events/?channel=${channel}`;
        
        this.log(`Connecting to SSE: ${url}`);
        
        try {
            this.eventSource = new EventSource(url);
            this.setupEventListeners();
        } catch (error) {
            this.log(`SSE connection failed: ${error.message}`, 'error');
            this.scheduleReconnect();
        }
    }

    /**
     * Set up event source listeners
     */
    setupEventListeners() {
        this.eventSource.onopen = () => {
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.log('SSE connection established');
            this.dispatchCustomEvent('sse:connected');
        };

        this.eventSource.onerror = (error) => {
            this.log(`SSE connection error: ${error}`, 'error');
            this.isConnected = false;
            this.dispatchCustomEvent('sse:error', { error });
            
            if (this.eventSource.readyState === EventSource.CLOSED) {
                this.scheduleReconnect();
            }
        };

        // Handle all SSE event types
        this.eventSource.onmessage = (event) => {
            this.handleMessage(event);
        };

        // Add specific event type handlers
        this.addSSEEventHandler('game_move');
        this.addSSEEventHandler('dashboard_update');
        this.addSSEEventHandler('dashboard_game_update');
        this.addSSEEventHandler('friends_update');
    }

    /**
     * Add SSE event type handler
     * @param {string} eventType - The SSE event type to handle
     */
    addSSEEventHandler(eventType) {
        this.eventSource.addEventListener(eventType, (event) => {
            this.handleTypedMessage(eventType, event);
        });
    }

    /**
     * Handle generic SSE messages
     * @param {MessageEvent} event - The SSE message event
     */
    handleMessage(event) {
        try {
            const data = this.parseEventData(event);
            this.log(`SSE message received: ${JSON.stringify(data).substring(0, 100)}...`);
            this.routeEvent('message', data);
        } catch (error) {
            this.log(`Failed to parse SSE message: ${error.message}`, 'error');
        }
    }

    /**
     * Handle typed SSE messages (game_move, dashboard_update, etc.)
     * @param {string} eventType - The event type
     * @param {MessageEvent} event - The SSE message event
     */
    handleTypedMessage(eventType, event) {
        try {
            const data = this.parseEventData(event);
            this.log(`SSE ${eventType} received: ${data.length || 'unknown'} chars`);
            this.routeEvent(eventType, data);
        } catch (error) {
            this.log(`Failed to parse SSE ${eventType}: ${error.message}`, 'error');
        }
    }

    /**
     * Parse event data from SSE message
     * @param {MessageEvent} event - The SSE message event
     * @returns {any} Parsed event data
     */
    parseEventData(event) {
        let data = event.data;
        
        // Try to parse as JSON first
        try {
            return JSON.parse(data);
        } catch {
            // If not JSON, return as string (common for HTML content)
            return data;
        }
    }

    /**
     * Route event to appropriate handlers
     * @param {string} eventType - The event type
     * @param {any} data - The event data
     */
    routeEvent(eventType, data) {
        // Dispatch custom event for HTMX compatibility
        this.dispatchCustomEvent(`sse:${eventType}`, { 
            type: eventType, 
            data: data,
            timestamp: Date.now()
        });

        // Call registered handlers
        const handlers = this.eventHandlers.get(eventType) || [];
        handlers.forEach(handler => {
            try {
                handler(data, eventType);
            } catch (error) {
                this.log(`Event handler error for ${eventType}: ${error.message}`, 'error');
            }
        });
    }

    /**
     * Dispatch custom DOM event
     * @param {string} eventName - The custom event name
     * @param {any} detail - Event detail data
     */
    dispatchCustomEvent(eventName, detail = {}) {
        const customEvent = new CustomEvent(eventName, { 
            detail: detail,
            bubbles: true,
            cancelable: true
        });
        document.dispatchEvent(customEvent);
        this.log(`Custom event dispatched: ${eventName}`);
    }

    /**
     * Register event handler for specific event type
     * @param {string} eventType - The event type to handle
     * @param {Function} handler - The handler function
     */
    on(eventType, handler) {
        if (!this.eventHandlers.has(eventType)) {
            this.eventHandlers.set(eventType, []);
        }
        this.eventHandlers.get(eventType).push(handler);
        this.log(`Handler registered for ${eventType}`);
    }

    /**
     * Remove event handler
     * @param {string} eventType - The event type
     * @param {Function} handler - The handler function to remove
     */
    off(eventType, handler) {
        const handlers = this.eventHandlers.get(eventType) || [];
        const index = handlers.indexOf(handler);
        if (index > -1) {
            handlers.splice(index, 1);
            this.log(`Handler removed for ${eventType}`);
        }
    }

    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.log('Max reconnection attempts reached', 'error');
            this.dispatchCustomEvent('sse:max_reconnects_reached');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1);
        
        this.log(`Scheduling reconnection attempt ${this.reconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            this.disconnect();
            this.connect(this.userId, this.debugMode);
        }, delay);
    }

    /**
     * Disconnect SSE connection
     */
    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.isConnected = false;
        this.log('SSE disconnected');
        this.dispatchCustomEvent('sse:disconnected');
    }

    /**
     * Log message with optional level
     * @param {string} message - The log message
     * @param {string} level - Log level (log, warn, error)
     */
    log(message, level = 'log') {
        if (this.debugMode) {
            console[level](`[SSE Manager] ${message}`);
        }
    }

    /**
     * Get connection status
     * @returns {Object} Connection status information
     */
    getStatus() {
        return {
            isConnected: this.isConnected,
            reconnectAttempts: this.reconnectAttempts,
            userId: this.userId,
            handlerCount: Array.from(this.eventHandlers.values()).reduce((sum, handlers) => sum + handlers.length, 0)
        };
    }
}

// Global SSE Manager instance
window.sseManager = new SSEManager();

// Auto-initialize if user ID is available
document.addEventListener('DOMContentLoaded', () => {
    const userIdElement = document.querySelector('[data-user-id]');
    if (userIdElement) {
        const userId = userIdElement.getAttribute('data-user-id');
        const debug = document.querySelector('[data-sse-debug]') !== null;
        window.sseManager.connect(userId, debug);
    }
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (window.sseManager) {
        window.sseManager.disconnect();
    }
});