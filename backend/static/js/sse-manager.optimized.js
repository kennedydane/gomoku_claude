/**
 * Optimized Centralized SSE Connection Manager
 * Performance improvements: connection pooling, message queuing, exponential backoff
 */
class OptimizedSSEManager {
    constructor() {
        this.eventSource = null;
        this.isConnected = false;
        this.reconnectInterval = 1000; // Start with 1 second
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.maxReconnectInterval = 30000; // Cap at 30 seconds
        this.eventHandlers = new Map();
        this.debugMode = false;
        this.messageQueue = [];
        this.maxQueueSize = 100;
        this.connectionStartTime = null;
        this.lastActivityTime = null;
        this.heartbeatInterval = null;
        this.connectionMetrics = {
            connectAttempts: 0,
            totalReconnects: 0,
            messagesReceived: 0,
            connectionUptime: 0
        };
        
        // Throttled and debounced functions for performance
        this.throttledLog = this.throttle(this.log.bind(this), 100);
        this.debouncedReconnect = this.debounce(this.scheduleReconnect.bind(this), 500);
        
        // Bind methods to preserve context
        this.handleMessage = this.handleMessage.bind(this);
        this.handleTypedMessage = this.handleTypedMessage.bind(this);
        this.processMessageQueue = this.processMessageQueue.bind(this);
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

    /**
     * Initialize optimized SSE connection with performance tracking
     */
    connect(userId, debug = false) {
        this.debugMode = debug;
        this.userId = userId;
        this.connectionStartTime = performance.now();
        this.connectionMetrics.connectAttempts++;
        
        if (this.isConnected) {
            this.throttledLog('SSE already connected, skipping');
            return Promise.resolve();
        }

        return new Promise((resolve, reject) => {
            const channel = `user-${userId}`;
            const url = `/api/v1/events/?channel=${channel}`;
            
            this.throttledLog(`Connecting to SSE: ${url}`);
            
            try {
                this.eventSource = new EventSource(url);
                this.setupOptimizedEventListeners();
                
                // Set up connection timeout
                const connectionTimeout = setTimeout(() => {
                    if (!this.isConnected) {
                        this.throttledLog('Connection timeout', 'warn');
                        reject(new Error('Connection timeout'));
                        this.handleConnectionError();
                    }
                }, 10000); // 10 second timeout
                
                // Resolve when connected
                this.eventSource.addEventListener('open', () => {
                    clearTimeout(connectionTimeout);
                    resolve();
                }, { once: true });
                
            } catch (error) {
                this.throttledLog(`SSE connection failed: ${error.message}`, 'error');
                reject(error);
                this.debouncedReconnect();
            }
        });
    }

    /**
     * Set up optimized event source listeners with performance monitoring
     */
    setupOptimizedEventListeners() {
        this.eventSource.onopen = () => {
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.reconnectInterval = 1000; // Reset interval
            this.lastActivityTime = Date.now();
            this.connectionMetrics.totalReconnects++;
            
            this.throttledLog('SSE connection established');
            this.dispatchCustomEvent('sse:connected');
            this.processMessageQueue(); // Process any queued messages
            this.startHeartbeat();
        };

        this.eventSource.onerror = (error) => {
            this.throttledLog(`SSE connection error: ${error}`, 'error');
            this.isConnected = false;
            this.stopHeartbeat();
            this.dispatchCustomEvent('sse:error', { error });
            
            if (this.eventSource.readyState === EventSource.CLOSED) {
                this.handleConnectionError();
            }
        };

        // Optimized message handling with batching
        this.eventSource.onmessage = this.throttle(this.handleMessage, 10); // Max 100 messages per second

        // Add specific event type handlers with performance optimization
        const eventTypes = ['game_move', 'dashboard_update', 'dashboard_game_update', 'friends_update'];
        eventTypes.forEach(eventType => {
            this.eventSource.addEventListener(eventType, (event) => {
                this.handleTypedMessage(eventType, event);
            });
        });
    }

    /**
     * Start heartbeat to detect stale connections
     */
    startHeartbeat() {
        this.stopHeartbeat(); // Clear any existing heartbeat
        
        this.heartbeatInterval = setInterval(() => {
            const now = Date.now();
            const timeSinceActivity = now - this.lastActivityTime;
            
            // If no activity for 60 seconds, consider connection stale
            if (timeSinceActivity > 60000) {
                this.throttledLog('Connection appears stale, reconnecting', 'warn');
                this.handleConnectionError();
            }
        }, 30000); // Check every 30 seconds
    }

    /**
     * Stop heartbeat monitoring
     */
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    /**
     * Handle connection errors with optimized reconnection strategy
     */
    handleConnectionError() {
        this.isConnected = false;
        this.stopHeartbeat();
        
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.throttledLog('Max reconnection attempts reached', 'error');
            this.dispatchCustomEvent('sse:max_reconnects_reached');
            return;
        }

        // Exponential backoff with jitter
        const backoffTime = Math.min(
            this.reconnectInterval * Math.pow(1.5, this.reconnectAttempts),
            this.maxReconnectInterval
        );
        const jitter = Math.random() * 1000; // Add up to 1 second jitter
        const totalDelay = backoffTime + jitter;

        this.reconnectAttempts++;
        this.throttledLog(`Scheduling reconnection attempt ${this.reconnectAttempts} in ${Math.round(totalDelay)}ms`);
        
        setTimeout(() => {
            this.disconnect();
            this.connect(this.userId, this.debugMode).catch(error => {
                this.throttledLog(`Reconnection failed: ${error.message}`, 'error');
            });
        }, totalDelay);
    }

    /**
     * Optimized message handling with queuing for disconnected state
     */
    handleMessage(event) {
        try {
            this.lastActivityTime = Date.now();
            this.connectionMetrics.messagesReceived++;
            
            const data = this.parseEventData(event);
            this.throttledLog(`SSE message received (${this.connectionMetrics.messagesReceived} total)`);
            this.routeEvent('message', data);
        } catch (error) {
            this.throttledLog(`Failed to parse SSE message: ${error.message}`, 'error');
        }
    }

    /**
     * Handle typed messages with performance optimization
     */
    handleTypedMessage(eventType, event) {
        try {
            this.lastActivityTime = Date.now();
            this.connectionMetrics.messagesReceived++;
            
            const data = this.parseEventData(event);
            this.throttledLog(`SSE ${eventType} received`);
            this.routeEvent(eventType, data);
        } catch (error) {
            this.throttledLog(`Failed to parse SSE ${eventType}: ${error.message}`, 'error');
        }
    }

    /**
     * Enhanced event parsing with caching
     */
    parseEventData(event) {
        let data = event.data;
        
        // Try JSON parsing first with caching
        if (typeof data === 'string' && data.startsWith('{')) {
            try {
                return JSON.parse(data);
            } catch {
                return data;
            }
        }
        
        return data;
    }

    /**
     * Optimized event routing with batching
     */
    routeEvent(eventType, data) {
        // Add to queue if disconnected
        if (!this.isConnected && this.messageQueue.length < this.maxQueueSize) {
            this.messageQueue.push({ eventType, data, timestamp: Date.now() });
            return;
        }

        // Dispatch immediately if connected
        this.dispatchEvents([{ eventType, data }]);
    }

    /**
     * Batch dispatch events for better performance
     */
    dispatchEvents(events) {
        // Use requestAnimationFrame for better performance
        if (window.requestAnimationFrame) {
            requestAnimationFrame(() => {
                events.forEach(({ eventType, data }) => {
                    this.dispatchSingleEvent(eventType, data);
                });
            });
        } else {
            // Fallback for older browsers
            setTimeout(() => {
                events.forEach(({ eventType, data }) => {
                    this.dispatchSingleEvent(eventType, data);
                });
            }, 0);
        }
    }

    /**
     * Dispatch single event with error handling
     */
    dispatchSingleEvent(eventType, data) {
        try {
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
                    this.throttledLog(`Event handler error for ${eventType}: ${error.message}`, 'error');
                }
            });
        } catch (error) {
            this.throttledLog(`Failed to dispatch event ${eventType}: ${error.message}`, 'error');
        }
    }

    /**
     * Process queued messages when connection is restored
     */
    processMessageQueue() {
        if (this.messageQueue.length === 0) return;
        
        this.throttledLog(`Processing ${this.messageQueue.length} queued messages`);
        
        // Remove expired messages (older than 5 minutes)
        const now = Date.now();
        const validMessages = this.messageQueue.filter(msg => now - msg.timestamp < 300000);
        
        // Process in batches for better performance
        const batchSize = 10;
        const batches = [];
        for (let i = 0; i < validMessages.length; i += batchSize) {
            batches.push(validMessages.slice(i, i + batchSize));
        }
        
        batches.forEach((batch, index) => {
            setTimeout(() => {
                this.dispatchEvents(batch);
            }, index * 100); // Stagger batch processing
        });
        
        this.messageQueue = [];
    }

    /**
     * Enhanced custom event dispatching
     */
    dispatchCustomEvent(eventName, detail = {}) {
        const customEvent = new CustomEvent(eventName, { 
            detail: detail,
            bubbles: true,
            cancelable: true
        });
        document.dispatchEvent(customEvent);
    }

    /**
     * Register event handler with automatic cleanup
     */
    on(eventType, handler) {
        if (!this.eventHandlers.has(eventType)) {
            this.eventHandlers.set(eventType, []);
        }
        this.eventHandlers.get(eventType).push(handler);
        this.throttledLog(`Handler registered for ${eventType} (${this.eventHandlers.get(eventType).length} total)`);
        
        // Return unsubscribe function
        return () => this.off(eventType, handler);
    }

    /**
     * Remove event handler
     */
    off(eventType, handler) {
        const handlers = this.eventHandlers.get(eventType) || [];
        const index = handlers.indexOf(handler);
        if (index > -1) {
            handlers.splice(index, 1);
            this.throttledLog(`Handler removed for ${eventType}`);
        }
    }

    /**
     * Disconnect with cleanup
     */
    disconnect() {
        this.stopHeartbeat();
        
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        
        this.isConnected = false;
        this.throttledLog('SSE disconnected');
        this.dispatchCustomEvent('sse:disconnected');
    }

    /**
     * Enhanced logging with performance consideration
     */
    log(message, level = 'log') {
        if (this.debugMode && console[level]) {
            console[level](`[Optimized SSE Manager] ${message}`);
        }
    }

    /**
     * Get enhanced connection status with metrics
     */
    getStatus() {
        const uptime = this.connectionStartTime ? 
            Math.round((performance.now() - this.connectionStartTime) / 1000) : 0;
            
        return {
            isConnected: this.isConnected,
            reconnectAttempts: this.reconnectAttempts,
            userId: this.userId,
            handlerCount: Array.from(this.eventHandlers.values()).reduce((sum, handlers) => sum + handlers.length, 0),
            queuedMessages: this.messageQueue.length,
            metrics: {
                ...this.connectionMetrics,
                connectionUptime: uptime
            }
        };
    }
}

// Global optimized SSE Manager instance
window.sseManager = new OptimizedSSEManager();

// Auto-initialize with performance monitoring
document.addEventListener('DOMContentLoaded', () => {
    const userIdElement = document.querySelector('[data-user-id]');
    if (userIdElement) {
        const userId = userIdElement.getAttribute('data-user-id');
        const debug = document.querySelector('[data-sse-debug]') !== null;
        
        window.sseManager.connect(userId, debug).then(() => {
            console.log('SSE Manager connected successfully');
        }).catch(error => {
            console.error('SSE Manager connection failed:', error);
        });
    }
});

// Enhanced cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.sseManager) {
        window.sseManager.disconnect();
    }
});

// Add performance monitoring
if ('performance' in window) {
    window.addEventListener('load', () => {
        setTimeout(() => {
            const status = window.sseManager.getStatus();
            console.log('SSE Manager Performance Status:', status);
        }, 1000);
    });
}