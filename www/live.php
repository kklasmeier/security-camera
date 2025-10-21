<?php
require_once 'includes/header.php';
require_once 'includes/db.php';

// Check current streaming status
$db = new Database();
$is_streaming = $db->get_streaming_flag();
?>

<div class="container">
    <div class="live-header">
        <h1 class="live-title">Live Camera View</h1>
        
        <div class="stream-controls">
            <div class="stream-status">
                <div id="stream-status" class="status-indicator <?php echo $is_streaming ? 'status-active' : 'status-inactive'; ?>"></div>
                <span id="stream-status-text" class="status-text">
                    <?php echo $is_streaming ? 'Streaming' : 'Stopped'; ?>
                </span>
            </div>
            
            <button 
                id="stream-button" 
                class="btn <?php echo $is_streaming ? 'btn-error' : 'btn-success'; ?>"
                onclick="<?php echo $is_streaming ? 'stopStream()' : 'startStream()'; ?>"
            >
                <?php echo $is_streaming ? 'Stop Stream' : 'Start Stream'; ?>
            </button>
        </div>
    </div>
    
    <div id="stream-container" class="stream-container">
        <!-- Placeholder (shown when stopped) -->
        <div id="stream-placeholder" class="stream-placeholder" style="<?php echo $is_streaming ? 'display: none;' : 'display: flex;'; ?>">
            <div class="placeholder-content">
                <div class="placeholder-icon">📹</div>
                <div class="placeholder-text">Camera feed will appear here</div>
                <div class="placeholder-subtext">Click "Start Stream" to begin</div>
            </div>
        </div>
        
        <!-- Live stream (shown when streaming) -->
        <img 
            id="stream-image" 
            class="stream-image" 
            src="<?php echo $is_streaming ? 'http://192.168.1.21:8080/stream.mjpg?t=' . time() : ''; ?>"
            alt="Live camera stream"
            style="<?php echo $is_streaming ? 'display: block;' : 'display: none;'; ?>"
        >
    </div>
    
    <div class="stream-info-container">
        <div id="stream-timer" class="stream-timer"></div>
        <div id="stream-info" class="stream-info">
            <?php if ($is_streaming): ?>
                Motion detection: Paused while streaming
            <?php endif; ?>
        </div>
    </div>
</div>

<?php require_once 'includes/footer.php'; ?>