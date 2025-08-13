// Custom JavaScript for Gomoku Game

// Utility Functions
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
    container.className = 'toast-container';
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

// Game Board Functions
function makeMove(gameId, row, col) {
    const cell = document.querySelector(`[data-row="${row}"][data-col="${col}"]`);
    if (cell && !cell.classList.contains('occupied')) {
        // Show loading state
        cell.innerHTML = '<div class="loading-spinner"></div>';
        
        // Make the move via htmx
        htmx.ajax('POST', `/web/games/${gameId}/move/`, {
            values: { row: row, col: col },
            target: '#game-container',
            swap: 'innerHTML'
        });
    }
}

function updateGameBoard(boardData) {
    const board = document.querySelector('.game-board');
    if (!board) return;
    
    const cells = board.querySelectorAll('.board-cell');
    cells.forEach((cell, index) => {
        const row = Math.floor(index / boardData.size);
        const col = index % boardData.size;
        const cellValue = boardData.board[row][col];
        
        cell.className = 'board-cell';
        cell.innerHTML = '';
        
        if (cellValue === 'BLACK') {
            cell.classList.add('occupied', 'black-stone');
            cell.innerHTML = '●';
        } else if (cellValue === 'WHITE') {
            cell.classList.add('occupied', 'white-stone');
            cell.innerHTML = '●';
        }
    });
}

// Friend System Functions
function sendFriendRequest(username) {
    htmx.ajax('POST', '/web/friends/request/', {
        values: { username: username },
        target: '#friend-request-result',
        swap: 'innerHTML'
    });
}

function respondToFriendRequest(requestId, accept) {
    htmx.ajax('POST', `/web/friends/respond/${requestId}/`, {
        values: { accept: accept },
        target: '#friend-requests',
        swap: 'outerHTML'
    });
}

// Challenge System Functions
function createChallenge(userId) {
    htmx.ajax('POST', '/web/challenges/create/', {
        values: { challenged_user: userId },
        target: '#challenge-result',
        swap: 'innerHTML'
    });
}

function respondToChallenge(challengeId, accept) {
    htmx.ajax('POST', `/web/challenges/respond/${challengeId}/`, {
        values: { accept: accept },
        target: '#challenges-container',
        swap: 'outerHTML'
    });
}

// Real-time Updates
function handleGameUpdate(eventData) {
    if (eventData.type === 'move') {
        // Update the game board
        const gameId = eventData.game_id;
        if (window.location.pathname.includes(`/game/${gameId}`)) {
            htmx.trigger('#game-container', 'refresh');
        }
        
        // Show notification if it's not your move
        if (eventData.player_id !== getCurrentUserId()) {
            showToast(`${eventData.player_name} made a move`, 'info');
        }
    } else if (eventData.type === 'game_end') {
        const winner = eventData.winner_name;
        showToast(`Game ended! ${winner ? winner + ' wins!' : 'Draw!'}`, 'success');
        
        // Refresh the page after a short delay
        setTimeout(() => {
            window.location.reload();
        }, 3000);
    }
}

// Utility function to get current user ID (set by Django template)
function getCurrentUserId() {
    return document.body.dataset.userId || null;
}

// HTMX Event Handlers
document.addEventListener('DOMContentLoaded', function() {
    // Add loading indicators to forms
    document.addEventListener('htmx:beforeRequest', function(event) {
        const element = event.target;
        if (element.tagName === 'FORM') {
            const submitBtn = element.querySelector('[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<div class="loading-spinner"></div> Loading...';
                
                // Reset on completion
                document.addEventListener('htmx:afterRequest', function resetBtn() {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                    document.removeEventListener('htmx:afterRequest', resetBtn);
                }, { once: true });
            }
        }
    });
    
    // Handle HTMX errors
    document.addEventListener('htmx:responseError', function(event) {
        console.error('HTMX Error:', event.detail);
        showToast('Something went wrong. Please try again.', 'error');
    });
    
    // Handle successful HTMX responses
    document.addEventListener('htmx:afterSwap', function(event) {
        // Re-initialize any tooltips or popovers
        const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(tooltip => {
            new bootstrap.Tooltip(tooltip);
        });
        
        // Check for success messages in response
        const target = event.target;
        if (target.dataset.successMessage) {
            showToast(target.dataset.successMessage, 'success');
        }
    });
});

// Game Board Click Handler
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('board-cell') && !event.target.classList.contains('occupied')) {
        const row = parseInt(event.target.dataset.row);
        const col = parseInt(event.target.dataset.col);
        const gameId = document.querySelector('.game-board').dataset.gameId;
        
        if (gameId && !isNaN(row) && !isNaN(col)) {
            makeMove(gameId, row, col);
        }
    }
});

// Keyboard Shortcuts
document.addEventListener('keydown', function(event) {
    // Press 'r' to refresh current game
    if (event.key === 'r' && event.ctrlKey && window.location.pathname.includes('/game/')) {
        event.preventDefault();
        htmx.trigger('#game-container', 'refresh');
    }
    
    // Press 'Escape' to close modals
    if (event.key === 'Escape') {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            bootstrap.Modal.getInstance(modal)?.hide();
        });
    }
});

// Auto-refresh for dashboard and game list pages
function startAutoRefresh() {
    const refreshInterval = 30000; // 30 seconds
    const refreshablePages = ['/web/dashboard/', '/web/games/', '/web/challenges/'];
    
    if (refreshablePages.some(page => window.location.pathname.includes(page))) {
        setInterval(() => {
            // Only refresh if page is visible
            if (!document.hidden) {
                const refreshTarget = document.querySelector('[data-auto-refresh]');
                if (refreshTarget) {
                    htmx.trigger(refreshTarget, 'refresh');
                }
            }
        }, refreshInterval);
    }
}

// Initialize auto-refresh on page load
document.addEventListener('DOMContentLoaded', startAutoRefresh);

// Handle visibility changes (pause refresh when tab is hidden)
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('Page hidden - pausing auto-refresh');
    } else {
        console.log('Page visible - resuming auto-refresh');
    }
});

// Sound effects (optional)
const GameSounds = {
    move: () => {
        // Simple click sound using Web Audio API
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.1);
    },
    
    win: () => {
        // Victory sound
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const frequencies = [523, 659, 784]; // C, E, G
        
        frequencies.forEach((freq, index) => {
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(freq, audioContext.currentTime);
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime + index * 0.1);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + index * 0.1 + 0.3);
            
            oscillator.start(audioContext.currentTime + index * 0.1);
            oscillator.stop(audioContext.currentTime + index * 0.1 + 0.3);
        });
    }
};

// Export functions for global access
window.GameSounds = GameSounds;
window.showToast = showToast;
window.makeMove = makeMove;
window.createChallenge = createChallenge;
window.sendFriendRequest = sendFriendRequest;