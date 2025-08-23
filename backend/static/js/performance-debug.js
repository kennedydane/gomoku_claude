/**
 * Client-Side Performance Debugging System
 * Tracks accumulation issues that build up over game moves
 * Key insight: Page reload fixes performance = something accumulating client-side
 */

class PerformanceDebugger {
    constructor() {
        this.startTime = performance.now();
        this.moveCount = 0;
        this.memorySnapshots = [];
        this.eventHandlerCounts = new Map();
        this.webSocketMessages = [];
        this.domNodeCounts = [];
        this.performanceTimings = [];
        this.isActive = false;
        
        // Track original methods for monitoring
        this.originalEventListenerMethods = {};
        this.activeEventListeners = new Map();
        
        // Check for quiet mode
        const urlParams = new URLSearchParams(window.location.search);
        this.quietMode = urlParams.has('debug_quiet');
        
        if (!this.quietMode) {
            console.log('🔧 Performance Debugger initialized');
        }
    }

    /**
     * Start comprehensive performance monitoring
     */
    start() {
        if (this.isActive) return;
        
        this.isActive = true;
        
        if (!this.quietMode) {
            console.log('🚀 Starting performance debugging...');
        }
        
        // Set up all monitoring systems
        this.setupMemoryMonitoring();
        this.setupEventHandlerTracking();
        this.setupWebSocketMonitoring();
        this.setupDOMMonitoring();
        this.setupHTMXMonitoring();
        this.createDebugPanel();
        
        // Take initial baseline snapshot
        this.takePerformanceSnapshot('initial');
        
        if (!this.quietMode) {
            console.log('✅ Performance debugging active');
            console.log('🤫 Use ?debug_quiet=true for minimal logging');
        }
    }

    /**
     * Memory usage and leak detection
     */
    setupMemoryMonitoring() {
        // Track memory usage every move
        this.memoryInterval = setInterval(() => {
            if (performance.memory) {
                const memory = {
                    timestamp: performance.now(),
                    moveCount: this.moveCount,
                    usedJSHeapSize: performance.memory.usedJSHeapSize,
                    totalJSHeapSize: performance.memory.totalJSHeapSize,
                    jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
                };
                
                this.memorySnapshots.push(memory);
                
                // Alert for significant memory increases
                if (this.memorySnapshots.length > 1) {
                    const previous = this.memorySnapshots[this.memorySnapshots.length - 2];
                    const increase = memory.usedJSHeapSize - previous.usedJSHeapSize;
                    const increasePercent = (increase / previous.usedJSHeapSize) * 100;
                    
                    if (increasePercent > 10) { // More than 10% increase
                        console.warn(`🧠 MEMORY SPIKE: ${(increase / 1024 / 1024).toFixed(2)}MB increase (${increasePercent.toFixed(1)}%) after move ${this.moveCount}`);
                        this.logMemoryDetails();
                    }
                }
            }
        }, 1000);
    }

    /**
     * Event handler multiplication tracking
     */
    setupEventHandlerTracking() {
        const self = this;
        
        // Monkey patch addEventListener to track handler additions
        this.originalEventListenerMethods.addEventListener = EventTarget.prototype.addEventListener;
        EventTarget.prototype.addEventListener = function(type, listener, options) {
            // Track this event listener
            const key = `${this.tagName || 'window'}_${this.id || 'anonymous'}_${type}`;
            if (!self.activeEventListeners.has(key)) {
                self.activeEventListeners.set(key, []);
            }
            self.activeEventListeners.get(key).push({
                listener,
                options,
                timestamp: performance.now(),
                moveCount: self.moveCount,
                element: this
            });
            
            // Call original method
            return self.originalEventListenerMethods.addEventListener.call(this, type, listener, options);
        };

        // Monkey patch removeEventListener to track removals
        this.originalEventListenerMethods.removeEventListener = EventTarget.prototype.removeEventListener;
        EventTarget.prototype.removeEventListener = function(type, listener, options) {
            const key = `${this.tagName || 'window'}_${this.id || 'anonymous'}_${type}`;
            if (self.activeEventListeners.has(key)) {
                const handlers = self.activeEventListeners.get(key);
                const index = handlers.findIndex(h => h.listener === listener);
                if (index > -1) {
                    handlers.splice(index, 1);
                }
            }
            
            return self.originalEventListenerMethods.removeEventListener.call(this, type, listener, options);
        };

        // Track previous handler count to only warn on increases
        this.lastHandlerCount = 0;
        
        // Periodic handler count analysis (less frequent in quiet mode)
        setInterval(() => {
            const totalHandlers = Array.from(this.activeEventListeners.values())
                .reduce((sum, handlers) => sum + handlers.length, 0);
            
            // Only log if not quiet mode OR if handlers increased
            if (!this.quietMode || totalHandlers > this.lastHandlerCount) {
                if (!this.quietMode || totalHandlers > this.lastHandlerCount + 10) {
                    console.log(`📡 Event Handlers: ${totalHandlers} total across ${this.activeEventListeners.size} elements`);
                }
            }
            
            // Check for handler accumulation (only warn if it's actually growing)
            this.activeEventListeners.forEach((handlers, key) => {
                if (handlers.length > 5) {
                    const prevCount = this.eventHandlerCounts.get(key) || 0;
                    if (handlers.length > prevCount || !this.quietMode) {
                        console.warn(`⚠️ HANDLER ACCUMULATION: ${key} has ${handlers.length} handlers (was ${prevCount})`);
                        if (!this.quietMode) {
                            console.log('Handler details:', handlers.map(h => ({
                                moveCount: h.moveCount,
                                timestamp: h.timestamp,
                                type: typeof h.listener
                            })));
                        }
                        this.eventHandlerCounts.set(key, handlers.length);
                    }
                }
            });
            
            this.lastHandlerCount = totalHandlers;
        }, this.quietMode ? 30000 : 5000); // 30s in quiet mode, 5s in verbose mode
    }

    /**
     * WebSocket message and handler monitoring
     */
    setupWebSocketMonitoring() {
        const self = this;
        
        // Monitor global WebSocket if available
        if (window.WebSocket) {
            const OriginalWebSocket = window.WebSocket;
            window.WebSocket = function(...args) {
                const ws = new OriginalWebSocket(...args);
                
                // Track message events
                const originalOnMessage = ws.onmessage;
                ws.onmessage = function(event) {
                    self.trackWebSocketMessage(event);
                    if (originalOnMessage) originalOnMessage.call(this, event);
                };

                // Track addEventListener calls on WebSocket
                const originalAddListener = ws.addEventListener;
                ws.addEventListener = function(type, listener, options) {
                    if (type === 'message') {
                        console.log(`📨 WebSocket message listener added at move ${self.moveCount}`);
                    }
                    return originalAddListener.call(this, type, listener, options);
                };

                return ws;
            };
        }

        // Monitor SSE connections (if any exist despite user saying no SSE)
        if (window.EventSource) {
            const OriginalEventSource = window.EventSource;
            window.EventSource = function(...args) {
                const es = new OriginalEventSource(...args);
                console.log('📡 EventSource created (unexpected - user said no SSE)');
                return es;
            };
        }
    }

    trackWebSocketMessage(event) {
        const messageData = {
            timestamp: performance.now(),
            moveCount: this.moveCount,
            dataSize: event.data ? event.data.length : 0,
            dataType: typeof event.data,
            messagePreview: event.data ? event.data.substring(0, 100) : ''
        };
        
        this.webSocketMessages.push(messageData);
        
        // Log WebSocket messages only in verbose mode
        if (!this.quietMode) {
            console.log(`📨 WebSocket message: ${messageData.dataSize} bytes at move ${this.moveCount}`);
        }
        
        // Alert for large messages (always shown as this indicates a performance issue)
        if (messageData.dataSize > 10000) {
            console.warn(`🚨 LARGE WEBSOCKET MESSAGE: ${(messageData.dataSize / 1024).toFixed(2)}KB`);
            if (!this.quietMode) {
                console.log('Message preview:', messageData.messagePreview);
            }
        }
        
        // Check for message frequency issues
        const recentMessages = this.webSocketMessages.filter(m => 
            performance.now() - m.timestamp < 1000
        );
        
        if (recentMessages.length > 5) {
            console.warn(`⚡ HIGH MESSAGE FREQUENCY: ${recentMessages.length} messages in last 1s`);
        }
    }

    /**
     * DOM node accumulation monitoring
     */
    setupDOMMonitoring() {
        let lastDOMElementCount = 0;
        
        setInterval(() => {
            const domStats = {
                timestamp: performance.now(),
                moveCount: this.moveCount,
                totalElements: document.querySelectorAll('*').length,
                gameIntersections: document.querySelectorAll('.board-intersection').length,
                htmxElements: document.querySelectorAll('[data-hx-trigger], [hx-get], [hx-post], [hx-ws]').length,
                dataAttributes: document.querySelectorAll('[data-sse-registered], [data-row], [data-col]').length,
                eventHandlerElements: document.querySelectorAll('[onclick], [onchange], [onsubmit]').length
            };
            
            this.domNodeCounts.push(domStats);
            
            // Check for DOM accumulation
            if (this.domNodeCounts.length > 1) {
                const previous = this.domNodeCounts[this.domNodeCounts.length - 2];
                const growth = domStats.totalElements - previous.totalElements;
                
                if (growth > 50) {
                    console.warn(`🌳 DOM GROWTH: +${growth} elements since last check (now ${domStats.totalElements} total)`);
                }
            }
            
            // Only log DOM stats if not quiet OR if elements changed significantly
            if (!this.quietMode || Math.abs(domStats.totalElements - lastDOMElementCount) > 20) {
                console.log(`🌳 DOM Stats: ${domStats.totalElements} total, ${domStats.gameIntersections} intersections, ${domStats.htmxElements} HTMX elements`);
                lastDOMElementCount = domStats.totalElements;
            }
        }, this.quietMode ? 15000 : 3000); // 15s in quiet mode, 3s in verbose mode
    }

    /**
     * HTMX-specific monitoring
     */
    setupHTMXMonitoring() {
        const self = this;
        
        // Monitor HTMX events if available
        if (typeof htmx !== 'undefined') {
            document.body.addEventListener('htmx:beforeSwap', (e) => {
                if (!self.quietMode) {
                    console.log(`🔄 HTMX beforeSwap: target=${e.target.tagName}#${e.target.id || 'no-id'} at move ${self.moveCount}`);
                }
            });

            document.body.addEventListener('htmx:afterSwap', (e) => {
                if (!self.quietMode) {
                    console.log(`✅ HTMX afterSwap: target=${e.target.tagName}#${e.target.id || 'no-id'}`);
                }
                
                // Check if htmx.process is being called
                const startTime = performance.now();
                if (typeof htmx.process === 'function') {
                    htmx.process(e.target);
                    const processTime = performance.now() - startTime;
                    if (processTime > 50) {
                        console.warn(`⏱️ SLOW HTMX PROCESS: ${processTime.toFixed(2)}ms`);
                    }
                }
            });

            document.body.addEventListener('htmx:afterSettle', (e) => {
                if (!self.quietMode) {
                    self.takePerformanceSnapshot('after-htmx-settle');
                }
            });
        }
    }

    /**
     * Take performance snapshot for comparison
     */
    takePerformanceSnapshot(label) {
        const timing = {
            label,
            timestamp: performance.now(),
            moveCount: this.moveCount,
            memory: performance.memory ? {
                used: performance.memory.usedJSHeapSize,
                total: performance.memory.totalJSHeapSize
            } : null,
            domElements: document.querySelectorAll('*').length,
            eventHandlers: Array.from(this.activeEventListeners.values())
                .reduce((sum, handlers) => sum + handlers.length, 0)
        };
        
        this.performanceTimings.push(timing);
        
        // Only log snapshots for key events or in verbose mode
        if (!this.quietMode || label.includes('move-') || label === 'initial') {
            console.log(`📊 Performance snapshot [${label}]:`, timing);
        }
    }

    /**
     * Called when a game move is made
     */
    onGameMove() {
        this.moveCount++;
        console.log(`🎮 GAME MOVE #${this.moveCount}`);
        
        this.takePerformanceSnapshot(`move-${this.moveCount}`);
        
        // Analyze performance degradation
        if (this.moveCount > 1) {
            this.analyzePerformanceDegradation();
        }
    }

    /**
     * Analyze performance degradation over time
     */
    analyzePerformanceDegradation() {
        if (this.performanceTimings.length < 2) return;
        
        const baseline = this.performanceTimings[0];
        const current = this.performanceTimings[this.performanceTimings.length - 1];
        
        const memoryGrowth = current.memory ? 
            ((current.memory.used - baseline.memory.used) / baseline.memory.used) * 100 : 0;
        
        const domGrowth = ((current.domElements - baseline.domElements) / baseline.domElements) * 100;
        const handlerGrowth = ((current.eventHandlers - baseline.eventHandlers) / Math.max(baseline.eventHandlers, 1)) * 100;
        
        console.log(`📈 ACCUMULATION ANALYSIS after ${this.moveCount} moves:`);
        console.log(`   Memory growth: ${memoryGrowth.toFixed(1)}%`);
        console.log(`   DOM growth: ${domGrowth.toFixed(1)}%`);
        console.log(`   Handler growth: ${handlerGrowth.toFixed(1)}%`);
        
        // Alert for concerning growth
        if (memoryGrowth > 50 || domGrowth > 20 || handlerGrowth > 100) {
            console.error('🚨 SIGNIFICANT ACCUMULATION DETECTED!');
            this.generateDetailedReport();
        }
    }

    /**
     * Log detailed memory information
     */
    logMemoryDetails() {
        if (!performance.memory) return;
        
        const memory = performance.memory;
        console.log(`🧠 MEMORY DETAILS:
            Used: ${(memory.usedJSHeapSize / 1024 / 1024).toFixed(2)} MB
            Total: ${(memory.totalJSHeapSize / 1024 / 1024).toFixed(2)} MB
            Limit: ${(memory.jsHeapSizeLimit / 1024 / 1024).toFixed(2)} MB
            Usage: ${((memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100).toFixed(1)}%`);
    }

    /**
     * Create debug panel in UI
     */
    createDebugPanel() {
        const panel = document.createElement('div');
        panel.id = 'performance-debug-panel';
        panel.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            width: 350px;
            max-height: 400px;
            overflow-y: auto;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            font-family: monospace;
            font-size: 12px;
            padding: 10px;
            border-radius: 5px;
            z-index: 10000;
            border: 2px solid #ff6b6b;
        `;
        
        panel.innerHTML = `
            <div style="font-weight: bold; color: #ff6b6b; margin-bottom: 5px;">
                🔧 PERFORMANCE DEBUG PANEL
                <button onclick="performanceDebugger.stop()" style="float: right; font-size: 10px;">Stop</button>
            </div>
            <div id="debug-stats">Loading...</div>
        `;
        
        document.body.appendChild(panel);
        
        // Update panel less frequently in quiet mode
        this.panelInterval = setInterval(() => {
            this.updateDebugPanel();
        }, this.quietMode ? 10000 : 2000); // 10s in quiet mode, 2s in verbose mode
    }

    /**
     * Update debug panel with current stats
     */
    updateDebugPanel() {
        const statsDiv = document.getElementById('debug-stats');
        if (!statsDiv) return;
        
        const memory = performance.memory;
        const latestTiming = this.performanceTimings[this.performanceTimings.length - 1];
        
        statsDiv.innerHTML = `
            <div>Moves: ${this.moveCount}</div>
            <div>Memory: ${memory ? (memory.usedJSHeapSize / 1024 / 1024).toFixed(1) + 'MB' : 'N/A'}</div>
            <div>DOM Elements: ${document.querySelectorAll('*').length}</div>
            <div>Event Handlers: ${Array.from(this.activeEventListeners.values()).reduce((sum, h) => sum + h.length, 0)}</div>
            <div>WebSocket Messages: ${this.webSocketMessages.length}</div>
            <div>Game Intersections: ${document.querySelectorAll('.board-intersection').length}</div>
            <div>HTMX Elements: ${document.querySelectorAll('[data-hx-trigger], [hx-get], [hx-post], [hx-ws]').length}</div>
            <div style="margin-top: 5px; color: #ffeb3b;">
                ${this.getPerformanceStatus()}
            </div>
        `;
    }

    getPerformanceStatus() {
        if (this.moveCount === 0) return 'Monitoring...';
        
        const memory = performance.memory;
        if (memory && memory.usedJSHeapSize > 100 * 1024 * 1024) {
            return '🚨 High Memory Usage';
        }
        
        const handlerCount = Array.from(this.activeEventListeners.values())
            .reduce((sum, handlers) => sum + handlers.length, 0);
        
        if (handlerCount > 100) {
            return '⚠️ Many Event Handlers';
        }
        
        return '✅ Monitoring Active';
    }

    /**
     * Generate comprehensive performance report
     */
    generateDetailedReport() {
        console.group('📊 DETAILED PERFORMANCE REPORT');
        
        console.log('🎮 Game State:');
        console.log(`   Moves made: ${this.moveCount}`);
        console.log(`   Session duration: ${((performance.now() - this.startTime) / 1000).toFixed(1)}s`);
        
        if (performance.memory) {
            console.log('🧠 Memory Analysis:');
            this.logMemoryDetails();
            console.log(`   Memory snapshots: ${this.memorySnapshots.length}`);
        }
        
        console.log('📡 Event Handlers:');
        console.log(`   Total active handlers: ${Array.from(this.activeEventListeners.values()).reduce((sum, h) => sum + h.length, 0)}`);
        console.log(`   Elements with handlers: ${this.activeEventListeners.size}`);
        
        // Most problematic elements
        const problematicElements = Array.from(this.activeEventListeners.entries())
            .filter(([key, handlers]) => handlers.length > 3)
            .sort(([, a], [, b]) => b.length - a.length);
            
        if (problematicElements.length > 0) {
            console.log('⚠️ Elements with excessive handlers:');
            problematicElements.slice(0, 5).forEach(([key, handlers]) => {
                console.log(`   ${key}: ${handlers.length} handlers`);
            });
        }
        
        console.log('🌐 WebSocket Messages:');
        console.log(`   Total messages: ${this.webSocketMessages.length}`);
        if (this.webSocketMessages.length > 0) {
            const totalSize = this.webSocketMessages.reduce((sum, msg) => sum + msg.dataSize, 0);
            const avgSize = totalSize / this.webSocketMessages.length;
            console.log(`   Total data: ${(totalSize / 1024).toFixed(2)}KB`);
            console.log(`   Average message size: ${avgSize.toFixed(0)} bytes`);
            
            const largeMessages = this.webSocketMessages.filter(msg => msg.dataSize > 5000);
            if (largeMessages.length > 0) {
                console.log(`   Large messages (>5KB): ${largeMessages.length}`);
            }
        }
        
        console.log('🌳 DOM Analysis:');
        const currentDOM = {
            total: document.querySelectorAll('*').length,
            intersections: document.querySelectorAll('.board-intersection').length,
            htmx: document.querySelectorAll('[data-hx-trigger], [hx-get], [hx-post], [hx-ws]').length,
            tracked: document.querySelectorAll('[data-sse-registered], [data-row]').length
        };
        console.log(`   Total elements: ${currentDOM.total}`);
        console.log(`   Game intersections: ${currentDOM.intersections}`);
        console.log(`   HTMX elements: ${currentDOM.htmx}`);
        console.log(`   Tracked elements: ${currentDOM.tracked}`);
        
        console.groupEnd();
    }

    /**
     * Stop performance monitoring
     */
    stop() {
        if (!this.isActive) return;
        
        this.isActive = false;
        console.log('🛑 Stopping performance monitoring...');
        
        // Restore original methods
        if (this.originalEventListenerMethods.addEventListener) {
            EventTarget.prototype.addEventListener = this.originalEventListenerMethods.addEventListener;
        }
        if (this.originalEventListenerMethods.removeEventListener) {
            EventTarget.prototype.removeEventListener = this.originalEventListenerMethods.removeEventListener;
        }
        
        // Clear intervals
        if (this.memoryInterval) clearInterval(this.memoryInterval);
        if (this.panelInterval) clearInterval(this.panelInterval);
        
        // Remove debug panel
        const panel = document.getElementById('performance-debug-panel');
        if (panel) panel.remove();
        
        // Generate final report
        this.generateDetailedReport();
        
        console.log('✅ Performance monitoring stopped');
    }
}

// Global instance
window.performanceDebugger = new PerformanceDebugger();

// Auto-start if URL contains debug parameter
if (window.location.search.includes('debug_performance=true')) {
    window.performanceDebugger.start();
}

// Expose methods for manual control
window.startPerformanceDebugging = () => window.performanceDebugger.start();
window.stopPerformanceDebugging = () => window.performanceDebugger.stop();
window.debugReport = () => window.performanceDebugger.generateDetailedReport();

// Hook into game moves if move detection is available
document.addEventListener('htmx:afterSwap', (e) => {
    // Detect if this looks like a game move update
    if (e.target.classList.contains('game-board-grid') || 
        e.target.querySelector('.board-intersection')) {
        window.performanceDebugger.onGameMove();
    }
});

if (new URLSearchParams(window.location.search).has('debug_quiet')) {
    console.log('🔧 Performance debugging loaded in QUIET MODE. Minimal logging enabled.');
} else {
    console.log('🔧 Performance debugging system loaded. Use startPerformanceDebugging() to begin monitoring.');
    console.log('💡 Add ?debug_quiet=true for minimal logging mode.');
}