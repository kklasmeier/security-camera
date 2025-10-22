<?php


/**
 * Events List Page - Main page showing all motion detection events
 * Displays thumbnail grid with pagination, motion scores, and smart timestamps
 */

// Include database and functions
require_once 'includes/db.php';
require_once 'includes/functions.php';

// Initialize database
$db = new Database();

// Get and sanitize URL parameters
$page = sanitize_page($_GET['page'] ?? 1);
$per_page = sanitize_per_page($_GET['per_page'] ?? 12);

// Get total event count
$total_events = $db->get_event_count();
$total_pages = ($total_events > 0) ? ceil($total_events / $per_page) : 1;

// If page exceeds total pages, redirect to last valid page
if ($page > $total_pages && $total_pages > 0) {
    header("Location: " . build_pagination_url($total_pages, $per_page));
    exit;
}

// Calculate offset for SQL query
$offset = ($page - 1) * $per_page;

// Get events for current page
$events = $db->get_recent_events($per_page, $offset);

// Calculate display range
$start_num = ($total_events > 0) ? $offset + 1 : 0;
$end_num = min($offset + $per_page, $total_events);

// Page title
$page_title = "Events - Security Camera";

// Include header
include 'includes/header.php';
?>

<div class="container">

        <!-- Page Header -->
        <div class="events-header">
            <h1 class="events-title">Events</h1>
            <span class="events-count">
                Showing <?php echo number_format($start_num); ?>-<?php echo number_format($end_num); ?> 
                of <?php echo number_format($total_events); ?>
            </span>
        </div>

        <!-- Per-Page Selector -->
        <div class="per-page-selector">
            <label for="per-page">Show per page:</label>
            <select id="per-page" onchange="changePerPage(this.value)">
                <option value="12" <?php echo ($per_page == 12) ? 'selected' : ''; ?>>12</option>
                <option value="24" <?php echo ($per_page == 24) ? 'selected' : ''; ?>>24</option>
                <option value="48" <?php echo ($per_page == 48) ? 'selected' : ''; ?>>48</option>
                <option value="100" <?php echo ($per_page == 100) ? 'selected' : ''; ?>>100</option>
            </select>
        </div>

        <?php if (count($events) > 0): ?>
            <!-- Events Grid -->
            <div class="events-grid">
                <?php foreach ($events as $event): ?>
                    <?php
                        // Get motion badge info
                        $badge = get_motion_badge($event['motion_score']);
                        
                        // Get thumbnail URL (with fallback)
                        $thumbnail_url = get_thumbnail_url($event);
                        
                        // Format timestamp
                        $timestamp = format_event_timestamp($event['timestamp']);
                        
                        // Check if video is still processing
                        $is_processing = is_video_processing($event['video_path']);
                        
                        // Format duration (default 30s if not set)
                        # $duration = isset($event['duration']) ? $event['duration'] : 30;
                        $duration = isset($event['duration_seconds']) ? intval($event['duration_seconds']) : 60;
                    ?>
                    
                    <a href="event.php?id=<?php echo $event['id']; ?>" class="event-card">
                        <!-- Thumbnail -->
                        <img 
                            src="<?php echo htmlspecialchars($thumbnail_url); ?>" 
                            alt="Event <?php echo $event['id']; ?>" 
                            class="event-thumbnail"
                            loading="lazy"
                        >
                        
                        <!-- Card Content -->
                        <div class="event-card-content">
                            <!-- Timestamp -->
                            <span class="event-timestamp"><?php echo htmlspecialchars($timestamp); ?></span>
                            
                            <!-- Meta Row: Motion Badge + Duration -->
                            <div class="event-meta">
                                <!-- Motion Score Badge -->
                                <span class="badge badge-<?php echo $badge['color']; ?>">
                                    <span style="font-size: 1.2em;"><?php echo $badge['symbol']; ?></span> Movement Score (<?php echo $event['motion_score']; ?>)
                                </span>
                                
                                <!-- Duration + Processing Indicator -->
                                <div>
                                    <span class="event-duration"><?php echo $duration; ?>s</span>
                                    <?php if ($is_processing): ?>
                                        <span class="processing-badge">⏳ Processing</span>
                                    <?php endif; ?>
                                </div>
                            </div>
                        </div>
                    </a>
                <?php endforeach; ?>
            </div>

            <!-- Pagination Controls -->
            <div class="pagination">
                <!-- Previous Button -->
                <?php if ($page > 1): ?>
                    <a href="<?php echo build_pagination_url($page - 1, $per_page); ?>" class="pagination-btn">
                        « Previous
                    </a>
                <?php else: ?>
                    <span class="pagination-btn disabled">« Previous</span>
                <?php endif; ?>

                <!-- Page Info -->
                <span class="pagination-info">
                    Page <?php echo number_format($page); ?> of <?php echo number_format($total_pages); ?>
                </span>

                <!-- Next Button -->
                <?php if ($page < $total_pages): ?>
                    <a href="<?php echo build_pagination_url($page + 1, $per_page); ?>" class="pagination-btn">
                        Next »
                    </a>
                <?php else: ?>
                    <span class="pagination-btn disabled">Next »</span>
                <?php endif; ?>
            </div>

        <?php else: ?>
            <!-- Empty State -->
            <div class="empty-state">
                <div class="empty-state-icon">📷</div>
                <h2 class="empty-state-title">No Events Yet</h2>
                <p class="empty-state-message">
                    No motion detection events have been recorded. 
                    When motion is detected, events will appear here.
                </p>
            </div>
        <?php endif; ?>
    </main>

    <?php include 'includes/footer.php'; ?>

    <script>
        /**
         * Change events per page
         * Preserves current page when changing per_page setting
         */
        function changePerPage(perPage) {
            const currentPage = <?php echo $page; ?>;
            const currentPerPage = <?php echo $per_page; ?>;
            
            // Calculate which event we're currently looking at (first event on page)
            const currentEventIndex = (currentPage - 1) * currentPerPage;
            
            // Calculate what page that event would be on with new per_page
            const newPage = Math.floor(currentEventIndex / perPage) + 1;
            
            // Build URL
            let url = 'index.php?per_page=' + perPage;
            if (newPage > 1) {
                url += '&page=' + newPage;
            }
            
            // Navigate
            window.location.href = url;
        }
    </script>

</script>

<?php include 'includes/footer.php'; ?>