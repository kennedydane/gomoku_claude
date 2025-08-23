/**
 * WebSocket Message and Handler Analysis
 * Focused specifically on WebSocket accumulation issues
 */

class WebSocketAnalyzer {
    constructor() {
        this.messages = [];
        this.handlers = [];
        this.connections = [];
        this.startTime = performance.now();
        this.moveCounter = 0;
        
        console.log('📡 WebSocket Analyzer initialized');
    }

    start() {
        console.log('🔍 Starting WebSocket analysis...');
        this.interceptWebSockets();
        this.monitorHandlers();
        this.trackConnections();
        this.createAnalysisPanel();
    }

    interceptWebSockets() {
        const self = this;
        const OriginalWebSocket = window.WebSocket;

        window.WebSocket = function(url, protocols) {
            const ws = new OriginalWebSocket(url, protocols);
            
            console.log(`🔌 WebSocket connection created: ${url}`);
            self.connections.push({
                url,
                timestamp: performance.now(),
                moveCount: self.moveCounter,
                readyState: ws.readyState
            });

            // Intercept all message handlers
            const originalOnMessage = ws.onmessage;
            ws.onmessage = function(event) {
                self.analyzeMessage(event, 'onmessage');
                if (originalOnMessage) {
                    return originalOnMessage.call(this, event);
                }
            };

            // Intercept addEventListener for message events
            const originalAddEventListener = ws.addEventListener;
            ws.addEventListener = function(type, listener, options) {
                if (type === 'message') {
                    console.log(`📨 Message listener added at move ${self.moveCounter}`);
                    self.handlers.push({
                        type: 'message',
                        timestamp: performance.now(),
                        moveCount: self.moveCounter,
                        listenerType: typeof listener,
                        options: options
                    });
                    
                    // Wrap the listener to analyze messages
                    const wrappedListener = function(event) {
                        self.analyzeMessage(event, 'addEventListener');
                        return listener.call(this, event);
                    };
                    
                    return originalAddEventListener.call(this, type, wrappedListener, options);
                } else {
                    return originalAddEventListener.call(this, type, listener, options);
                }
            };

            return ws;
        };
    }

    analyzeMessage(event, source) {
        const messageAnalysis = {
            timestamp: performance.now(),
            moveCount: this.moveCounter,
            source: source,
            dataSize: event.data ? event.data.length : 0,
            dataType: typeof event.data,
            isJSON: false,
            messageType: 'unknown',
            htmlSize: 0,
            preview: ''
        };

        // Analyze message content
        if (event.data) {
            messageAnalysis.preview = event.data.substring(0, 200);
            
            // Try to parse as JSON
            try {
                const parsed = JSON.parse(event.data);
                messageAnalysis.isJSON = true;
                messageAnalysis.messageType = parsed.type || 'json';
                
                // Check for HTML content in the message
                if (typeof parsed === 'object') {
                    const htmlContent = JSON.stringify(parsed).match(/<[^>]+>/g);
                    if (htmlContent) {
                        messageAnalysis.htmlSize = htmlContent.join('').length;
                    }
                }
                
                console.log(`📨 WebSocket JSON message [${messageAnalysis.messageType}]: ${messageAnalysis.dataSize} bytes (HTML: ${messageAnalysis.htmlSize})`);
                
            } catch (e) {
                // Not JSON, check if it's HTML
                if (event.data.includes('<') && event.data.includes('>')) {
                    messageAnalysis.messageType = 'html';
                    messageAnalysis.htmlSize = event.data.length;
                    console.log(`📨 WebSocket HTML message: ${messageAnalysis.dataSize} bytes`);
                } else {
                    console.log(`📨 WebSocket text message: ${messageAnalysis.dataSize} bytes`);
                }
            }
        }

        this.messages.push(messageAnalysis);

        // Alert for problematic patterns
        this.checkForProblems(messageAnalysis);
    }

    checkForProblems(message) {
        // Large message alert
        if (message.dataSize > 20000) {
            console.warn(`🚨 LARGE WEBSOCKET MESSAGE: ${(message.dataSize / 1024).toFixed(2)}KB`);
            console.log('Message preview:', message.preview);
            
            // If it's HTML, try to identify what's causing the size
            if (message.htmlSize > 10000) {
                console.warn(`   🏗️ Contains ${(message.htmlSize / 1024).toFixed(2)}KB of HTML content`);
                this.analyzeHTMLContent(message.preview);
            }
        }

        // Message frequency analysis
        const recentMessages = this.messages.filter(m => 
            (performance.now() - m.timestamp) < 2000 && m.moveCount === this.moveCounter
        );

        if (recentMessages.length > 3) {
            console.warn(`⚡ HIGH MESSAGE FREQUENCY: ${recentMessages.length} messages in 2 seconds for move ${this.moveCounter}`);
            
            // Show message types
            const messageTypes = recentMessages.reduce((acc, msg) => {
                acc[msg.messageType] = (acc[msg.messageType] || 0) + 1;
                return acc;
            }, {});
            console.log('   Message type breakdown:', messageTypes);
        }

        // Accumulation detection
        if (this.messages.length > 10 && this.moveCounter > 2) {
            const messagesPerMove = this.messages.length / this.moveCounter;
            if (messagesPerMove > 5) {
                console.warn(`📈 MESSAGE ACCUMULATION: Average ${messagesPerMove.toFixed(1)} messages per move`);
            }
        }
    }

    analyzeHTMLContent(htmlContent) {
        if (!htmlContent || !htmlContent.includes('<')) return;

        // Count different types of HTML elements
        const patterns = {
            'board intersections': /<div[^>]*board-intersection/g,
            'stones': /<div[^>]*stone-(black|white)/g,
            'HTMX attributes': /hx-[a-z]+=/g,
            'data attributes': /data-[a-z-]+=/g,
            'CSS classes': /class="[^"]*"/g,
            'inline styles': /style="[^"]*"/g
        };

        console.group('🏗️ HTML Content Analysis:');
        Object.entries(patterns).forEach(([name, pattern]) => {
            const matches = htmlContent.match(pattern) || [];
            if (matches.length > 0) {
                console.log(`   ${name}: ${matches.length} occurrences`);
            }
        });
        console.groupEnd();
    }

    monitorHandlers() {
        setInterval(() => {
            console.log(`📡 WebSocket Handlers: ${this.handlers.length} registered`);
            
            // Check for handler accumulation
            const handlersByMove = this.handlers.reduce((acc, handler) => {
                acc[handler.moveCount] = (acc[handler.moveCount] || 0) + 1;
                return acc;
            }, {});

            const moveKeys = Object.keys(handlersByMove);
            if (moveKeys.length > 1) {
                console.log('   Handlers per move:', handlersByMove);
                
                // Check if handlers are accumulating without cleanup
                const latestMove = Math.max(...moveKeys.map(Number));
                const earlierMoves = moveKeys.filter(move => Number(move) < latestMove);
                
                if (earlierMoves.length > 0) {
                    const oldHandlers = earlierMoves.reduce((sum, move) => sum + handlersByMove[move], 0);
                    if (oldHandlers > 0) {
                        console.warn(`⚠️ HANDLER LEAK: ${oldHandlers} handlers from previous moves still registered`);
                    }
                }
            }
        }, 5000);
    }

    trackConnections() {
        setInterval(() => {
            console.log(`🔌 WebSocket Connections: ${this.connections.length} created`);
            
            if (this.connections.length > 3) {
                console.warn(`⚠️ MULTIPLE CONNECTIONS: ${this.connections.length} WebSocket connections created`);
                console.log('Connection details:', this.connections.map(conn => ({
                    url: conn.url,
                    moveCount: conn.moveCount,
                    age: ((performance.now() - conn.timestamp) / 1000).toFixed(1) + 's'
                })));
            }
        }, 10000);
    }

    onMove() {
        this.moveCounter++;
        console.log(`🎮 MOVE ${this.moveCounter} - Starting WebSocket analysis`);
        
        // Take snapshot of current state
        const snapshot = {
            moveCount: this.moveCounter,
            timestamp: performance.now(),
            totalMessages: this.messages.length,
            totalHandlers: this.handlers.length,
            totalConnections: this.connections.length
        };

        console.log(`📊 WebSocket state at move ${this.moveCounter}:`, snapshot);

        // Analyze message patterns for this move
        setTimeout(() => {
            this.analyzeMoveMessages();
        }, 2000); // Wait 2 seconds for messages to come in
    }

    analyzeMoveMessages() {
        const moveMessages = this.messages.filter(m => m.moveCount === this.moveCounter);
        
        if (moveMessages.length === 0) {
            console.log(`📭 No WebSocket messages for move ${this.moveCounter}`);
            return;
        }

        console.group(`📨 Move ${this.moveCounter} Message Analysis:`);
        
        const totalSize = moveMessages.reduce((sum, msg) => sum + msg.dataSize, 0);
        const htmlSize = moveMessages.reduce((sum, msg) => sum + msg.htmlSize, 0);
        
        console.log(`   Messages: ${moveMessages.length}`);
        console.log(`   Total size: ${(totalSize / 1024).toFixed(2)}KB`);
        console.log(`   HTML content: ${(htmlSize / 1024).toFixed(2)}KB`);
        
        // Message type breakdown
        const typeBreakdown = moveMessages.reduce((acc, msg) => {
            acc[msg.messageType] = (acc[msg.messageType] || 0) + 1;
            return acc;
        }, {});
        console.log('   Message types:', typeBreakdown);

        // Size breakdown
        const sizeCategories = {
            'small (<1KB)': moveMessages.filter(m => m.dataSize < 1024).length,
            'medium (1-10KB)': moveMessages.filter(m => m.dataSize >= 1024 && m.dataSize < 10240).length,
            'large (10-50KB)': moveMessages.filter(m => m.dataSize >= 10240 && m.dataSize < 51200).length,
            'huge (>50KB)': moveMessages.filter(m => m.dataSize >= 51200).length
        };
        console.log('   Size categories:', sizeCategories);

        console.groupEnd();

        // Performance warnings
        if (totalSize > 50000) {
            console.error(`🚨 EXCESSIVE DATA: ${(totalSize / 1024).toFixed(2)}KB sent for one move!`);
        }

        if (moveMessages.length > 5) {
            console.warn(`⚡ HIGH MESSAGE COUNT: ${moveMessages.length} messages for one move`);
        }
    }

    createAnalysisPanel() {
        const panel = document.createElement('div');
        panel.id = 'websocket-analysis-panel';
        panel.style.cssText = `
            position: fixed;
            top: 10px;
            left: 10px;
            width: 300px;
            max-height: 300px;
            overflow-y: auto;
            background: rgba(0, 50, 100, 0.95);
            color: white;
            font-family: monospace;
            font-size: 11px;
            padding: 8px;
            border-radius: 5px;
            z-index: 10001;
            border: 2px solid #00bcd4;
        `;
        
        panel.innerHTML = `
            <div style="font-weight: bold; color: #00bcd4; margin-bottom: 5px;">
                📡 WEBSOCKET ANALYZER
                <button onclick="webSocketAnalyzer.stop()" style="float: right; font-size: 10px;">Stop</button>
            </div>
            <div id="websocket-stats">Loading...</div>
        `;
        
        document.body.appendChild(panel);
        
        setInterval(() => {
            this.updatePanel();
        }, 1000);
    }

    updatePanel() {
        const statsDiv = document.getElementById('websocket-stats');
        if (!statsDiv) return;

        const totalSize = this.messages.reduce((sum, msg) => sum + msg.dataSize, 0);
        const recentMessages = this.messages.filter(m => 
            (performance.now() - m.timestamp) < 5000
        );

        statsDiv.innerHTML = `
            <div>Move: ${this.moveCounter}</div>
            <div>Total Messages: ${this.messages.length}</div>
            <div>Total Data: ${(totalSize / 1024).toFixed(1)}KB</div>
            <div>Handlers: ${this.handlers.length}</div>
            <div>Connections: ${this.connections.length}</div>
            <div>Recent (5s): ${recentMessages.length}</div>
            <div style="margin-top: 3px; color: #ffeb3b; font-size: 10px;">
                ${this.getStatus()}
            </div>
        `;
    }

    getStatus() {
        const avgMsgSize = this.messages.length > 0 ? 
            this.messages.reduce((sum, msg) => sum + msg.dataSize, 0) / this.messages.length : 0;

        if (avgMsgSize > 20000) return '🚨 Large Messages';
        if (this.handlers.length > 10) return '⚠️ Many Handlers';
        if (this.connections.length > 2) return '🔌 Multiple Connections';
        return '✅ Monitoring';
    }

    stop() {
        const panel = document.getElementById('websocket-analysis-panel');
        if (panel) panel.remove();
        
        console.log('📊 WebSocket Analysis Final Report:');
        console.log(`   Total messages: ${this.messages.length}`);
        console.log(`   Total handlers: ${this.handlers.length}`);
        console.log(`   Total connections: ${this.connections.length}`);
        
        if (this.messages.length > 0) {
            const totalSize = this.messages.reduce((sum, msg) => sum + msg.dataSize, 0);
            console.log(`   Total data transferred: ${(totalSize / 1024).toFixed(2)}KB`);
            console.log(`   Average message size: ${(totalSize / this.messages.length).toFixed(0)} bytes`);
        }
    }
}

// Global instance
window.webSocketAnalyzer = new WebSocketAnalyzer();

// Hook into game moves
document.addEventListener('htmx:afterSwap', (e) => {
    if (e.target.classList.contains('game-board-grid') || 
        e.target.querySelector('.board-intersection')) {
        window.webSocketAnalyzer.onMove();
    }
});

console.log('📡 WebSocket analyzer loaded. Call webSocketAnalyzer.start() to begin analysis.');