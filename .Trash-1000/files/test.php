<?php
$page_title = "System Test Page - Security Camera";
require_once __DIR__ . '/includes/header.php';
require_once __DIR__ . '/includes/db.php';

// Initialize database
$db = new Database();

// Get system stats
$php_version = phpversion();
$db_connected = $db->isConnected();
$event_count = $db->get_event_count();
$log_count = $db->get_log_count();
$streaming_status = $db->get_streaming_flag();

// Get one recent event for testing
$recent_events = $db->get_recent_events(1, 0);
$recent_event = !empty($recent_events) ? $recent_events[0] : null;
?>

<div class="container">
    <h1>System Test Page</h1>
    <p class="text-secondary">Verify that all components are working correctly</p>
    
    <!-- System Status Card -->
    <div class="card mt-lg">
        <h2 class="card-title">System Status</h2>
        <div class="card-content">
            <div style="display: grid; gap: 1rem;">
                <div class="flex-between" style="padding: 0.75rem; background: var(--color-bg-tertiary); border-radius: var(--border-radius);">
                    <span>nginx Configuration</span>
                    <span class="text-success" style="font-weight: 600;">✓ Working</span>
                </div>
                
                <div class="flex-between" style="padding: 0.75rem; background: var(--color-bg-tertiary); border-radius: var(--border-radius);">
                    <span>PHP Processing</span>
                    <span class="text-success" style="font-weight: 600;">✓ PHP <?php echo $php_version; ?></span>
                </div>
                
                <div class="flex-between" style="padding: 0.75rem; background: var(--color-bg-tertiary); border-radius: var(--border-radius);">
                    <span>Database Connection</span>
                    <?php if ($db_connected): ?>
                        <span class="text-success" style="font-weight: 600;">✓ Connected</span>
                    <?php else: ?>
                        <span class="text-error" style="font-weight: 600;">✗ Failed</span>
                    <?php endif; ?>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Database Stats Card -->
    <?php if ($db_connected): ?>
    <div class="card mt-lg">
        <h2 class="card-title">Database Statistics</h2>
        <div class="card-content">
            <div style="display: grid; gap: 1rem;">
                <div class="flex-between" style="padding: 0.75rem; background: var(--color-bg-tertiary); border-radius: var(--border-radius);">
                    <span>Total Events</span>
                    <span style="font-weight: 600; color: var(--color-primary);"><?php echo number_format($event_count); ?></span>
                </div>
                
                <div class="flex-between" style="padding: 0.75rem; background: var(--color-bg-tertiary); border-radius: var(--border-radius);">
                    <span>Total Logs</span>
                    <span style="font-weight: 600; color: var(--color-primary);"><?php echo number_format($log_count); ?></span>
                </div>
                
                <div class="flex-between" style="padding: 0.75rem; background: var(--color-bg-tertiary); border-radius: var(--border-radius);">
                    <span>Streaming Status</span>
                    <?php if ($streaming_status == 1): ?>
                        <span class="text-success" style="font-weight: 600;">Active</span>
                    <?php else: ?>
                        <span class="text-muted" style="font-weight: 600;">Inactive</span>
                    <?php endif; ?>
                </div>
            </div>
        </div>
    </div>
    <?php endif; ?>
    
    <!-- Recent Event Test Card -->
    <?php if ($db_connected && $recent_event): ?>
    <div class="card mt-lg">
        <h2 class="card-title">Recent Event Test</h2>
        <div class="card-content">
            <div style="display: grid; gap: 0.75rem;">
                <div>
                    <span class="text-muted">Event ID:</span>
                    <span style="margin-left: 1rem; font-weight: 600;"><?php echo $recent_event['id']; ?></span>
                </div>
                
                <div>
                    <span class="text-muted">Timestamp:</span>
                    <span style="margin-left: 1rem; font-weight: 600;"><?php echo date('M j, Y g:i A', strtotime($recent_event['timestamp'])); ?></span>
                </div>
                
                <div>
                    <span class="text-muted">Motion Score:</span>
                    <?php 
                    $score = $recent_event['motion_score'];
                    $color_class = 'motion-low';
                    if ($score >= 250) {
                        $color_class = 'motion-high';
                    } elseif ($score >= 150) {
                        $color_class = 'motion-medium';
                    }
                    ?>
                    <span style="margin-left: 1rem; font-weight: 600;" class="<?php echo $color_class; ?>"><?php echo $score; ?></span>
                </div>
                
                <div>
                    <span class="text-muted">Video File:</span>
                    <span style="margin-left: 1rem; font-family: var(--font-mono); font-size: var(--font-size-sm);"><?php echo basename($recent_event['video_path']); ?></span>
                </div>
                
                <div>
                    <span class="text-muted">Duration:</span>
                    <span style="margin-left: 1rem; font-weight: 600;"><?php echo $recent_event['duration_seconds']; ?> seconds</span>
                </div>
                
                <?php if ($recent_event['thumbnail_path']): ?>
                <div style="margin-top: 1rem;">
                    <p class="text-muted mb-sm">Thumbnail Preview:</p>
                    <img src="<?php echo $recent_event['thumbnail_path']; ?>" 
                         alt="Event thumbnail" 
                         style="max-width: 300px; border-radius: var(--border-radius); border: 1px solid var(--color-border);">
                </div>
                <?php endif; ?>
            </div>
        </div>
    </div>
    <?php elseif ($db_connected): ?>
    <div class="card mt-lg">
        <h2 class="card-title">Recent Event Test</h2>
        <div class="card-content">
            <p class="text-muted">No events found in database. Camera system may not have captured any motion events yet.</p>
        </div>
    </div>
    <?php endif; ?>
    
    <!-- Navigation Test Card -->
    <div class="card mt-lg">
        <h2 class="card-title">Navigation Test</h2>
        <div class="card-content">
            <p class="text-secondary mb-md">Test the navigation links:</p>
            <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                <a href="/index.php" class="btn btn-primary">Go to Events</a>
                <a href="/live.php" class="btn btn-secondary">Go to Live View</a>
                <a href="/logs.php" class="btn btn-secondary">Go to Logs</a>
            </div>
        </div>
    </div>
    
    <!-- Responsive Test -->
    <div class="card mt-lg mb-xl">
        <h2 class="card-title">Responsive Design Test</h2>
        <div class="card-content">
            <p class="text-secondary mb-md">Resize your browser window to test responsive behavior:</p>
            <ul style="list-style: none; padding-left: 0;">
                <li style="padding: 0.5rem 0;">
                    <span class="text-success">✓</span> Desktop (≥1200px): Full navigation bar with "Security Camera System"
                </li>
                <li style="padding: 0.5rem 0;">
                    <span class="text-success">✓</span> Tablet (768px-1199px): Full navigation bar with "Security Camera"
                </li>
                <li style="padding: 0.5rem 0;">
                    <span class="text-success">✓</span> Mobile (&lt;768px): "Sec Cam" with hamburger menu
                </li>
            </ul>
        </div>
    </div>
</div>

<?php require_once __DIR__ . '/includes/footer.php'; ?>