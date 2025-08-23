// Service Worker for Gomoku Game
// Provides offline caching, background sync, and performance optimizations

const CACHE_NAME = 'gomoku-v1.0.0';
const STATIC_CACHE_NAME = `${CACHE_NAME}-static`;
const DYNAMIC_CACHE_NAME = `${CACHE_NAME}-dynamic`;
const GAME_DATA_CACHE_NAME = `${CACHE_NAME}-gamedata`;

// Cache duration settings
const CACHE_DURATION = {
    static: 7 * 24 * 60 * 60 * 1000, // 7 days
    dynamic: 24 * 60 * 60 * 1000,    // 24 hours
    gameData: 60 * 60 * 1000,        // 1 hour
    api: 5 * 60 * 1000               // 5 minutes
};

// Static assets to cache immediately
const STATIC_ASSETS = [
    '/',
    '/dashboard/',
    '/static/dist/app.min.css',
    '/static/dist/app.min.js',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/js/sse-manager.js',
    '/static/js/htmx-sse-integration.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.2/font/bootstrap-icons.css',
    'https://unpkg.com/htmx.org@1.9.10',
    'https://unpkg.com/htmx.org@1.9.10/dist/ext/ws.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js'
];

// API endpoints to cache with different strategies
const API_CACHE_PATTERNS = {
    '/api/v1/auth/': 'network-first',
    '/api/v1/games/': 'cache-first',
    '/api/v1/users/': 'network-first',
    '/api/v1/events/': 'network-only' // SSE should never be cached
};

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('[Service Worker] Installing...');
    
    event.waitUntil(
        Promise.all([
            // Cache static assets
            caches.open(STATIC_CACHE_NAME).then(cache => {
                console.log('[Service Worker] Caching static assets');
                return cache.addAll(STATIC_ASSETS.map(url => {
                    return new Request(url, { credentials: 'same-origin' });
                }));
            }),
            
            // Skip waiting to activate immediately
            self.skipWaiting()
        ])
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('[Service Worker] Activating...');
    
    event.waitUntil(
        Promise.all([
            // Clean up old caches
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames
                        .filter(cacheName => cacheName.startsWith('gomoku-') && cacheName !== STATIC_CACHE_NAME)
                        .map(cacheName => {
                            console.log('[Service Worker] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        })
                );
            }),
            
            // Claim all clients immediately
            self.clients.claim()
        ])
    );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip chrome-extension and other non-http requests
    if (!url.protocol.startsWith('http')) {
        return;
    }
    
    // Handle different request types with appropriate strategies
    if (isStaticAsset(request)) {
        event.respondWith(cacheFirstStrategy(request, STATIC_CACHE_NAME));
    } else if (isAPIRequest(request)) {
        event.respondWith(handleAPIRequest(request));
    } else if (isPageRequest(request)) {
        event.respondWith(networkFirstStrategy(request, DYNAMIC_CACHE_NAME));
    } else {
        event.respondWith(staleWhileRevalidateStrategy(request, DYNAMIC_CACHE_NAME));
    }
});

// Background sync for game moves
self.addEventListener('sync', event => {
    console.log('[Service Worker] Background sync:', event.tag);
    
    if (event.tag === 'game-move-sync') {
        event.waitUntil(syncGameMoves());
    }
});

// Push notifications for game updates
self.addEventListener('push', event => {
    console.log('[Service Worker] Push notification received');
    
    const options = {
        body: 'Your opponent made a move!',
        icon: '/static/img/icon-192.png',
        badge: '/static/img/badge-72.png',
        tag: 'game-update',
        data: event.data ? event.data.json() : {},
        actions: [
            { action: 'view', title: 'View Game' },
            { action: 'dismiss', title: 'Dismiss' }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('Gomoku Game Update', options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    if (event.action === 'view') {
        event.waitUntil(
            clients.openWindow('/dashboard/')
        );
    }
});

// Caching strategies
async function cacheFirstStrategy(request, cacheName) {
    try {
        const cache = await caches.open(cacheName);
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse && !isCacheExpired(cachedResponse)) {
            return cachedResponse;
        }
        
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            await cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('[Service Worker] Cache first strategy failed:', error);
        const cache = await caches.open(cacheName);
        return cache.match(request) || new Response('Offline', { status: 503 });
    }
}

async function networkFirstStrategy(request, cacheName) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(cacheName);
            await cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('[Service Worker] Network first strategy failed:', error);
        const cache = await caches.open(cacheName);
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline fallback for pages
        if (isPageRequest(request)) {
            return cache.match('/') || new Response('Offline', { status: 503 });
        }
        
        return new Response('Offline', { status: 503 });
    }
}

async function staleWhileRevalidateStrategy(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cachedResponse = await cache.match(request);
    
    const fetchPromise = fetch(request)
        .then(networkResponse => {
            if (networkResponse.ok) {
                cache.put(request, networkResponse.clone());
            }
            return networkResponse;
        })
        .catch(() => cachedResponse);
    
    return cachedResponse || fetchPromise;
}

async function handleAPIRequest(request) {
    const url = new URL(request.url);
    const pathname = url.pathname;
    
    // Determine strategy based on API endpoint
    let strategy = 'network-first';
    for (const pattern in API_CACHE_PATTERNS) {
        if (pathname.startsWith(pattern)) {
            strategy = API_CACHE_PATTERNS[pattern];
            break;
        }
    }
    
    switch (strategy) {
        case 'cache-first':
            return cacheFirstStrategy(request, GAME_DATA_CACHE_NAME);
        case 'network-only':
            return fetch(request);
        default:
            return networkFirstStrategy(request, DYNAMIC_CACHE_NAME);
    }
}

// Utility functions
function isStaticAsset(request) {
    const url = new URL(request.url);
    return (
        url.pathname.startsWith('/static/') ||
        url.hostname === 'cdn.jsdelivr.net' ||
        url.hostname === 'unpkg.com' ||
        STATIC_ASSETS.some(asset => url.href.endsWith(asset))
    );
}

function isAPIRequest(request) {
    const url = new URL(request.url);
    return url.pathname.startsWith('/api/');
}

function isPageRequest(request) {
    const url = new URL(request.url);
    return (
        request.headers.get('accept').includes('text/html') ||
        url.pathname.endsWith('/')
    );
}

function isCacheExpired(response) {
    const cachedDate = response.headers.get('date');
    if (!cachedDate) return true;
    
    const cacheAge = Date.now() - new Date(cachedDate).getTime();
    const maxAge = CACHE_DURATION.static; // Default to static cache duration
    
    return cacheAge > maxAge;
}

// Background sync for game moves
async function syncGameMoves() {
    try {
        // Get pending moves from IndexedDB or localStorage
        const pendingMoves = await getPendingMoves();
        
        for (const move of pendingMoves) {
            try {
                const response = await fetch(`/api/v1/games/${move.gameId}/move/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Token ${move.token}`
                    },
                    body: JSON.stringify(move.data)
                });
                
                if (response.ok) {
                    await removePendingMove(move.id);
                    console.log('[Service Worker] Synced move:', move.id);
                } else {
                    throw new Error(`HTTP ${response.status}`);
                }
            } catch (error) {
                console.log('[Service Worker] Failed to sync move:', move.id, error);
            }
        }
    } catch (error) {
        console.log('[Service Worker] Background sync failed:', error);
        throw error; // Re-throw to retry later
    }
}

// Placeholder functions for move synchronization
// These would be implemented with IndexedDB in a full version
async function getPendingMoves() {
    // Implementation would use IndexedDB to store pending moves
    return [];
}

async function removePendingMove(moveId) {
    // Implementation would remove move from IndexedDB
    console.log('[Service Worker] Remove pending move:', moveId);
}

// Performance monitoring
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'GET_CACHE_STATUS') {
        caches.keys().then(cacheNames => {
            const status = {
                caches: cacheNames,
                static: STATIC_CACHE_NAME,
                dynamic: DYNAMIC_CACHE_NAME,
                gameData: GAME_DATA_CACHE_NAME
            };
            
            event.ports[0].postMessage(status);
        });
    }
});