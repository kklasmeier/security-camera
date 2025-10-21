// ========================================
// HAMBURGER MENU TOGGLE
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('navMenu');
    
    if (hamburger && navMenu) {
        hamburger.addEventListener('click', function() {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
        });
        
        // Close menu when clicking a link (mobile)
        const navLinks = navMenu.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth < 768) {
                    hamburger.classList.remove('active');
                    navMenu.classList.remove('active');
                }
            });
        });
        
        // Close menu when clicking outside (mobile)
        document.addEventListener('click', function(event) {
            if (window.innerWidth < 768) {
                const isClickInsideNav = navMenu.contains(event.target);
                const isClickOnHamburger = hamburger.contains(event.target);
                
                if (!isClickInsideNav && !isClickOnHamburger && navMenu.classList.contains('active')) {
                    hamburger.classList.remove('active');
                    navMenu.classList.remove('active');
                }
            }
        });
    }
});

/* ========================================
   LIGHTBOX FOR EVENT DETAIL PAGE
   ======================================== */

/**
 * Open lightbox with full-screen image
 * @param {string} imageSrc - URL of the image to display
 */
function openLightbox(imageSrc) {
    const lightbox = document.getElementById('lightbox');
    const lightboxImage = document.getElementById('lightbox-image');
    
    if (!lightbox || !lightboxImage) {
        console.error('Lightbox elements not found');
        return;
    }
    
    lightboxImage.src = imageSrc;
    lightbox.style.display = 'flex';
    
    // Prevent body scrolling when lightbox is open
    document.body.style.overflow = 'hidden';
}

/**
 * Close the lightbox and restore page scrolling
 */
function closeLightbox() {
    const lightbox = document.getElementById('lightbox');
    
    if (!lightbox) {
        return;
    }
    
    lightbox.style.display = 'none';
    
    // Restore body scrolling
    document.body.style.overflow = 'auto';
}

/**
 * Close lightbox when Escape key is pressed
 */
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' || e.key === 'Esc') {
        closeLightbox();
    }
});

/**
 * Prevent lightbox from closing when clicking on the image itself
 * (only close when clicking the dark background)
 */
document.addEventListener('DOMContentLoaded', function() {
    const lightboxImage = document.getElementById('lightbox-image');
    
    if (lightboxImage) {
        lightboxImage.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }
});

/* ========================================
   LOGS PAGE - AJAX FUNCTIONALITY
   ======================================== */

/**
 * Get More Logs - AJAX function
 * Fetches new logs since last loaded timestamp
 */
function getMoreLogs() {
    const btn = document.getElementById('get-more-btn');
    const tbody = document.getElementById('logs-tbody');
    const lastTimestamp = document.getElementById('last-timestamp').value;
    const status = document.getElementById('logs-status');
    
    // Get filter state
    const filterInfo = document.getElementById('filter-info').value;
    const filterWarning = document.getElementById('filter-warning').value;
    const filterError = document.getElementById('filter-error').value;
    
    // Disable button and show loading
    btn.disabled = true;
    btn.textContent = 'Loading...';
    
    // Build query string
    const params = new URLSearchParams({
        since: lastTimestamp,
        info: filterInfo,
        warning: filterWarning,
        error: filterError
    });
    
    // Fetch new logs
    fetch(`api/get_new_logs.php?${params.toString()}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.logs.length > 0) {
                // Append new logs to table
                data.logs.forEach(log => {
                    const row = createLogRow(log);
                    tbody.appendChild(row);
                });
                
                // Update last timestamp
                document.getElementById('last-timestamp').value = data.logs[0].timestamp;
                
                // Update status
                status.textContent = `Showing logs (${data.logs.length} new logs loaded)`;
                
                // Scroll to bottom
                const container = document.querySelector('.logs-container');
                container.scrollTop = container.scrollHeight;
            } else {
                status.textContent = 'No new logs';
            }
            
            // Re-enable button
            btn.disabled = false;
            btn.textContent = 'Get More Logs';
        })
        .catch(error => {
            console.error('Error fetching logs:', error);
            status.textContent = 'Error loading logs';
            btn.disabled = false;
            btn.textContent = 'Get More Logs';
        });
}

/**
 * Helper function to create log row element
 * @param {Object} log - Log object with id, timestamp, level, message
 * @returns {HTMLElement} Table row element
 */
function createLogRow(log) {
    const tr = document.createElement('tr');
    tr.className = `log-row log-${log.level.toLowerCase()}`;
    
    tr.innerHTML = `
        <td class="log-id">${log.id}</td>
        <td class="log-timestamp">${formatLogTimestamp(log.timestamp)}</td>
        <td class="log-level">
            <span class="level-badge level-${log.level.toLowerCase()}">
                ${log.level}
            </span>
        </td>
        <td class="log-message">${escapeHtml(log.message)}</td>
    `;
    
    return tr;
}

/**
 * Helper to format timestamp in JavaScript
 * Format: Oct 19, 2025 8:43:15 PM
 * @param {string} timestamp - ISO format timestamp
 * @returns {string} Formatted timestamp
 */
function formatLogTimestamp(timestamp) {
    const date = new Date(timestamp);
    const options = { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric', 
        hour: 'numeric', 
        minute: '2-digit', 
        second: '2-digit',
        hour12: true 
    };
    return date.toLocaleString('en-US', options);
}

/**
 * Helper to escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/* ========================================
   LIVE STREAMING CONTROL
   ======================================== */

let streamInterval = null;
let streamStartTime = null;

async function startStream() {
    const statusIndicator = document.getElementById('stream-status');
    const statusText = document.getElementById('stream-status-text');
    const streamButton = document.getElementById('stream-button');
    const streamImage = document.getElementById('stream-image');
    const streamPlaceholder = document.getElementById('stream-placeholder');
    const streamInfo = document.getElementById('stream-info');
    
    try {
        // Disable button and show loading
        streamButton.disabled = true;
        streamButton.textContent = 'Starting...';
        statusText.textContent = 'Starting';
        
        // Set streaming flag via AJAX
        const response = await fetch('api/set_streaming.php?action=start');
        const data = await response.json();
        
        if (data.success) {
            // Wait 2 seconds for MJPEG server to start
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // Show stream
            streamPlaceholder.style.display = 'none';
            streamImage.style.display = 'block';
            streamImage.src = 'http://192.168.1.21:8080/stream.mjpg?t=' + Date.now();
            
            // Update status
            statusIndicator.classList.add('status-active');
            statusIndicator.classList.remove('status-inactive');
            statusText.textContent = 'Streaming';
            
            // Update button
            streamButton.textContent = 'Stop Stream';
            streamButton.disabled = false;
            streamButton.classList.remove('btn-success');
            streamButton.classList.add('btn-error');
            streamButton.onclick = stopStream;
            
            // Start timer
            streamStartTime = Date.now();
            startStreamTimer();
            
            // Show stream info
            streamInfo.textContent = 'Motion detection: Paused while streaming';
            
        } else {
            throw new Error(data.message || 'Failed to start stream');
        }
        
    } catch (error) {
        console.error('Error starting stream:', error);
        statusText.textContent = 'Error';
        streamButton.textContent = 'Retry';
        streamButton.disabled = false;
        alert('Failed to start stream: ' + error.message);
    }
}

async function stopStream() {
    const statusIndicator = document.getElementById('stream-status');
    const statusText = document.getElementById('stream-status-text');
    const streamButton = document.getElementById('stream-button');
    const streamImage = document.getElementById('stream-image');
    const streamPlaceholder = document.getElementById('stream-placeholder');
    const streamInfo = document.getElementById('stream-info');
    
    try {
        // Disable button
        streamButton.disabled = true;
        streamButton.textContent = 'Stopping...';
        
        // Stop timer
        stopStreamTimer();
        
        // Set streaming flag to 0
        const response = await fetch('api/set_streaming.php?action=stop');
        const data = await response.json();
        
        if (data.success) {
            // Hide stream
            streamImage.style.display = 'none';
            streamImage.src = '';
            streamPlaceholder.style.display = 'flex';
            
            // Update status
            statusIndicator.classList.remove('status-active');
            statusIndicator.classList.add('status-inactive');
            statusText.textContent = 'Stopped';
            
            // Update button
            streamButton.textContent = 'Start Stream';
            streamButton.disabled = false;
            streamButton.classList.remove('btn-error');
            streamButton.classList.add('btn-success');
            streamButton.onclick = startStream;
            
            // Clear info
            streamInfo.textContent = '';
            
        } else {
            throw new Error(data.message || 'Failed to stop stream');
        }
        
    } catch (error) {
        console.error('Error stopping stream:', error);
        streamButton.textContent = 'Stop Stream';
        streamButton.disabled = false;
        alert('Error stopping stream: ' + error.message);
    }
}

function startStreamTimer() {
    stopStreamTimer(); // Clear any existing timer
    
    streamInterval = setInterval(() => {
        if (!streamStartTime) return;
        
        const elapsed = Date.now() - streamStartTime;
        const minutes = Math.floor(elapsed / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        
        const timerElement = document.getElementById('stream-timer');
        if (timerElement) {
            timerElement.textContent = `Stream running for: ${minutes}m ${seconds}s`;
        }
    }, 1000);
}

function stopStreamTimer() {
    if (streamInterval) {
        clearInterval(streamInterval);
        streamInterval = null;
    }
    streamStartTime = null;
    
    const timerElement = document.getElementById('stream-timer');
    if (timerElement) {
        timerElement.textContent = '';
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', function(e) {
    // Stop stream if active
    const streamImage = document.getElementById('stream-image');
    if (streamImage && streamImage.style.display !== 'none') {
        // Use synchronous request for cleanup
        const xhr = new XMLHttpRequest();
        xhr.open('GET', 'api/set_streaming.php?action=stop', false); // false = synchronous
        xhr.send();
    }
});

// Auto-start stream on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the live view page
    if (document.getElementById('stream-container')) {
        startStream();
    }
});