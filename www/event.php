<?php
/**
 * Event Detail Page
 * Displays full details of a single motion detection event including:
 * - Event metadata (timestamp, motion score, duration, files)
 * - Auto-playing video
 * - Two images (Picture A and Picture B)
 * - Previous/Next navigation
 */

require_once 'includes/db.php';
require_once 'includes/functions.php';

// Get and validate event ID
$event_id = isset($_GET['id']) ? (int)$_GET['id'] : 0;

if ($event_id <= 0) {
    header("Location: index.php?error=invalid_event_id");
    exit;
}

// Initialize database
$db = new Database();

// Get event details
$event = $db->get_event_by_id($event_id);

if (!$event) {
    header("Location: index.php?error=event_not_found");
    exit;
}

// Get navigation (previous and next event IDs)
$prev_id = $db->get_previous_event_id($event_id);
$next_id = $db->get_next_event_id($event_id);

// Check if video is still processing
$video_processing = is_video_processing($event['video_path']);

// Get URLs for media files
$video_url = get_video_url($event);
$image_a_url = get_image_url($event['image_a_path']);
$image_b_url = get_image_url($event['image_b_path']);

// Get motion badge info
$badge = get_motion_badge($event['motion_score']);

// Page title
$page_title = "Event #" . $event_id;

// Include header
include 'includes/header.php';
?>

<div class="container">
    <!-- Event Details Card -->
    <div class="event-details-card">
        <div class="event-details-header">
            <h1 class="event-id">Event #<?php echo $event_id; ?></h1>
            
            <div class="event-navigation">
                <?php if ($prev_id): ?>
                    <a href="event.php?id=<?php echo $prev_id; ?>" class="btn btn-secondary">
                        ← Previous
                    </a>
                <?php else: ?>
                    <button class="btn btn-secondary" disabled>
                        ← Previous
                    </button>
                <?php endif; ?>
                
                <a href="index.php" class="btn btn-secondary">
                    Back to Events
                </a>
                
                <?php if ($next_id): ?>
                    <a href="event.php?id=<?php echo $next_id; ?>" class="btn btn-secondary">
                        Next →
                    </a>
                <?php else: ?>
                    <button class="btn btn-secondary" disabled>
                        Next →
                    </button>
                <?php endif; ?>
            </div>
        </div>
        
        <!-- Event Metadata -->
        <div class="detail-item">
            <span class="detail-label">Timestamp:</span>
            <span class="detail-value"><?php echo format_event_timestamp($event['timestamp']); ?></span>
        </div>
        
        <div class="detail-item">
            <span class="detail-label">Motion Score:</span>
            <span class="detail-value">
                <span class="badge badge-<?php echo $badge['color']; ?>">
                    <?php echo $badge['symbol']; ?> <?php echo $badge['label']; ?> (<?php echo $event['motion_score']; ?>)
                </span>
            </span>
        </div>
        
        <div class="detail-item">
            <span class="detail-label">Duration:</span>
            <span class="detail-value"><?php echo $event['duration_seconds']; ?> seconds</span>
        </div>
        
        <?php if (!empty($event['video_path'])): ?>
        <div class="detail-item">
            <span class="detail-label">Video File:</span>
            <span class="detail-value">
                <?php echo basename($event['video_path']); ?>
                <?php if (file_exists($event['video_path'])): ?>
                    (<?php echo get_file_size($event['video_path']); ?>)
                <?php endif; ?>
            </span>
        </div>
        <?php endif; ?>
        
        <?php if (!empty($event['image_a_path'])): ?>
        <div class="detail-item">
            <span class="detail-label">Picture A:</span>
            <span class="detail-value">
                <?php echo basename($event['image_a_path']); ?>
                <?php if (file_exists($event['image_a_path'])): ?>
                    (<?php echo get_file_size($event['image_a_path']); ?>)
                <?php endif; ?>
            </span>
        </div>
        <?php endif; ?>

        <?php if (!empty($event['image_b_path'])): ?>
        <div class="detail-item">
            <span class="detail-label">Picture B:</span>
            <span class="detail-value">
                <?php echo basename($event['image_b_path']); ?>
                <?php if (file_exists($event['image_b_path'])): ?>
                    (<?php echo get_file_size($event['image_b_path']); ?>)
                <?php endif; ?>
            </span>
        </div>
        <?php endif; ?>
    </div>
    
    <!-- Video Player or Processing Status -->
    <?php if ($video_processing): ?>
        <div class="processing-status">
            <div class="processing-status-icon">⏳</div>
            <div class="processing-status-title">Video Processing</div>
            <div class="processing-status-message">
                This video is still being converted to MP4 format.<br>
                Please check back in a few moments.
            </div>
        </div>
    <?php elseif ($video_url): ?>
        <video 
            class="event-video" 
            controls 
            autoplay 
            preload="auto"
            src="<?php echo $video_url; ?>"
        >
            Your browser does not support the video tag.
        </video>
    <?php else: ?>
        <div class="processing-status">
            <div class="processing-status-icon">❌</div>
            <div class="processing-status-title">Video Not Available</div>
            <div class="processing-status-message">
                The video file for this event could not be found.
            </div>
        </div>
    <?php endif; ?>
    
    <!-- Event Images -->
    <div class="event-images">
        <!-- Picture A (Motion Detection) -->
        <div class="event-image-container">
            <h3 class="image-label">Picture A (Motion Detection)</h3>
            <?php if ($image_a_url): ?>
                <img 
                    src="<?php echo $image_a_url; ?>" 
                    alt="Picture A - Motion Detection"
                    class="event-image"
                    onclick="openLightbox('<?php echo $image_a_url; ?>')"
                >
            <?php else: ?>
                <div class="image-placeholder">Image not available</div>
            <?php endif; ?>
        </div>
        
        <!-- Picture B (T+4 seconds) -->
        <div class="event-image-container">
            <h3 class="image-label">Picture B (T+4 seconds)</h3>
            <?php if ($image_b_url): ?>
                <img 
                    src="<?php echo $image_b_url; ?>" 
                    alt="Picture B - T+4 seconds"
                    class="event-image"
                    onclick="openLightbox('<?php echo $image_b_url; ?>')"
                >
            <?php else: ?>
                <div class="image-placeholder">Image not available</div>
            <?php endif; ?>
        </div>
    </div>
    
    <!-- Bottom Navigation -->
    <div class="event-navigation">
        <?php if ($prev_id): ?>
            <a href="event.php?id=<?php echo $prev_id; ?>" class="btn btn-secondary">
                ← Previous Event
            </a>
        <?php else: ?>
            <button class="btn btn-secondary" disabled>
                ← Previous Event
            </button>
        <?php endif; ?>
        
        <a href="index.php" class="btn btn-secondary">
            Back to Events
        </a>
        
        <?php if ($next_id): ?>
            <a href="event.php?id=<?php echo $next_id; ?>" class="btn btn-secondary">
                Next Event →
            </a>
        <?php else: ?>
            <button class="btn btn-secondary" disabled>
                Next Event →
            </button>
        <?php endif; ?>
    </div>
</div>

<!-- Lightbox for full-screen images -->
<div id="lightbox" class="lightbox" onclick="closeLightbox()">
    <span class="lightbox-close" onclick="closeLightbox()">✕</span>
    <img id="lightbox-image" src="" alt="Full size image">
</div>

<?php include 'includes/footer.php'; ?>